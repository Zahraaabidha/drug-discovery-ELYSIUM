"""Compound Library API: registry search, profiles, import, similarity, comparison,
collections, annotations and evaluation."""
from __future__ import annotations

import logging
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import exists, func, or_
from sqlalchemy.orm import Session

from .. import models as m
from ..db import get_db
from ..services import chem, evaluation, registry
from ..services.similarity_index import index as similarity_index
from ..services.sources import ingest
from ..services.targets import resolve_target, supported_targets

log = logging.getLogger(__name__)
router = APIRouter(prefix="/library", tags=["library"])


# ── serialisation ─────────────────────────────────────────────────────────
def _physchem(c: m.Compound) -> Dict:
    return {"mol_weight": c.mol_weight, "logp": c.logp, "tpsa": c.tpsa, "hbd": c.hbd, "hba": c.hba,
            "rotatable_bonds": c.rotatable_bonds, "heavy_atoms": c.heavy_atoms, "ring_count": c.ring_count,
            "lipinski_violations": c.lipinski_violations, "lipinski_pass": c.lipinski_pass}


def _summary(c: m.Compound, n_exp: int = 0, n_pred: int = 0) -> Dict:
    return {
        "id": c.id, "name": c.name, "inchikey": c.inchikey, "canonical_smiles": c.canonical_smiles,
        "origin": c.origin, "formula": c.formula, "physchem": _physchem(c),
        "n_experimental": n_exp, "n_predictions": n_pred,
        "sources": [{"source_db": s.source_db, "external_id": s.external_id} for s in c.sources],
        "generation_method": c.generation_method, "generation_run_id": c.generation_run_id,
    }


def _counts(db: Session, ids: List[int]) -> Dict[int, Dict[str, int]]:
    out = {i: {"exp": 0, "pred": 0} for i in ids}
    if not ids:
        return out
    for cid, n in db.query(m.Bioactivity.compound_id, func.count()).filter(m.Bioactivity.compound_id.in_(ids)).group_by(m.Bioactivity.compound_id):
        out[cid]["exp"] = n
    for cid, n in db.query(m.Prediction.compound_id, func.count()).filter(m.Prediction.compound_id.in_(ids)).group_by(m.Prediction.compound_id):
        out[cid]["pred"] = n
    return out


def _get(db: Session, compound_id: int) -> m.Compound:
    c = db.get(m.Compound, compound_id)
    if c is None:
        raise HTTPException(404, f"Compound {compound_id} not found")
    return c


# ── list / search / filter ────────────────────────────────────────────────
SORTS = {"id": m.Compound.id, "name": m.Compound.name, "mol_weight": m.Compound.mol_weight, "logp": m.Compound.logp,
         "tpsa": m.Compound.tpsa, "created_at": m.Compound.created_at, "lipinski_violations": m.Compound.lipinski_violations}


@router.get("/compounds")
def list_compounds(
    q: Optional[str] = Query(None, description="name, SMILES, InChIKey or external id (substring)"),
    origin: Optional[str] = Query(None, pattern="^(reference|external|generated)$"),
    source_db: Optional[str] = None,
    min_mw: Optional[float] = None, max_mw: Optional[float] = None,
    min_logp: Optional[float] = None, max_logp: Optional[float] = None,
    max_tpsa: Optional[float] = None, max_hbd: Optional[int] = None, max_hba: Optional[int] = None,
    max_rotatable_bonds: Optional[int] = None,
    lipinski_pass: Optional[bool] = None,
    has_experimental: Optional[bool] = None,
    has_prediction: Optional[bool] = None,
    target: Optional[str] = Query(None, description="restrict experimental/prediction filters to this target"),
    collection_id: Optional[int] = None,
    sort: str = "id", order: str = Query("asc", pattern="^(asc|desc)$"),
    limit: int = Query(50, ge=1, le=500), offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    qry = db.query(m.Compound)
    if q:
        like = f"%{q.strip()}%"
        qry = qry.filter(or_(
            m.Compound.name.ilike(like), m.Compound.canonical_smiles.ilike(like), m.Compound.inchikey.ilike(like),
            exists().where((m.CompoundSource.compound_id == m.Compound.id) & (m.CompoundSource.external_id.ilike(like))),
        ))
    if origin:
        qry = qry.filter(m.Compound.origin == origin)
    if source_db:
        qry = qry.filter(exists().where((m.CompoundSource.compound_id == m.Compound.id) & (m.CompoundSource.source_db == source_db)))
    for col, lo, hi in ((m.Compound.mol_weight, min_mw, max_mw), (m.Compound.logp, min_logp, max_logp)):
        if lo is not None:
            qry = qry.filter(col >= lo)
        if hi is not None:
            qry = qry.filter(col <= hi)
    for col, hi in ((m.Compound.tpsa, max_tpsa), (m.Compound.hbd, max_hbd), (m.Compound.hba, max_hba),
                    (m.Compound.rotatable_bonds, max_rotatable_bonds)):
        if hi is not None:
            qry = qry.filter(col <= hi)
    if lipinski_pass is not None:
        qry = qry.filter(m.Compound.lipinski_pass == lipinski_pass)
    if has_experimental is not None:
        cond = (m.Bioactivity.compound_id == m.Compound.id)
        if target:
            cond = cond & (m.Bioactivity.target_symbol == target.upper())
        qry = qry.filter(exists().where(cond) if has_experimental else ~exists().where(cond))
    if has_prediction is not None:
        cond = (m.Prediction.compound_id == m.Compound.id)
        if target:
            cond = cond & (m.Prediction.target_symbol == target.upper())
        qry = qry.filter(exists().where(cond) if has_prediction else ~exists().where(cond))
    if collection_id is not None:
        qry = qry.filter(exists().where((m.CollectionItem.compound_id == m.Compound.id) & (m.CollectionItem.collection_id == collection_id)))

    total = qry.count()
    col = SORTS.get(sort)
    if col is None:
        raise HTTPException(422, f"Unknown sort {sort!r}; choose from {sorted(SORTS)}")
    qry = qry.order_by(col.desc() if order == "desc" else col.asc(), m.Compound.id)
    items = qry.offset(offset).limit(limit).all()
    counts = _counts(db, [c.id for c in items])
    return {"total": total, "limit": limit, "offset": offset,
            "items": [_summary(c, counts[c.id]["exp"], counts[c.id]["pred"]) for c in items]}


@router.get("/stats")
def stats(db: Session = Depends(get_db)):
    by_origin = dict(db.query(m.Compound.origin, func.count()).group_by(m.Compound.origin).all())
    by_source = dict(db.query(m.CompoundSource.source_db, func.count(func.distinct(m.CompoundSource.compound_id)))
                     .group_by(m.CompoundSource.source_db).all())
    return {
        "compounds": db.query(m.Compound).count(), "by_origin": by_origin, "by_source": by_source,
        "bioactivities": db.query(m.Bioactivity).count(), "predictions": db.query(m.Prediction).count(),
        "collections": db.query(m.Collection).count(), "annotations": db.query(m.Annotation).count(),
        "supported_targets": supported_targets(),
        "index": {"size": similarity_index.size, "embeddings": similarity_index.has_embeddings},
    }


@router.get("/targets")
def targets(db: Session = Depends(get_db)):
    out = []
    for sym in supported_targets():
        t = resolve_target(sym)
        out.append({
            "symbol": sym, "uniprot_id": t.uniprot_id,
            "experimental_measurements": db.query(m.Bioactivity).filter_by(target_symbol=sym).count(),
            "predictions": db.query(m.Prediction).filter_by(target_symbol=sym).count(),
        })
    return out


# ── profile ───────────────────────────────────────────────────────────────
@router.get("/compounds/{compound_id}")
def compound_profile(compound_id: int, db: Session = Depends(get_db)):
    c = _get(db, compound_id)
    exp = db.query(m.Bioactivity).filter_by(compound_id=c.id).order_by(m.Bioactivity.target_symbol, m.Bioactivity.value_nm).all()
    preds = db.query(m.Prediction).filter_by(compound_id=c.id).order_by(m.Prediction.created_at.desc()).all()
    cols = (db.query(m.Collection).join(m.CollectionItem, m.CollectionItem.collection_id == m.Collection.id)
            .filter(m.CollectionItem.compound_id == c.id).all())
    prof = _summary(c, len(exp), len(preds))
    prof.update({
        "original_smiles": c.original_smiles, "created_at": c.created_at,
        "sources_detail": [{"source_db": s.source_db, "external_id": s.external_id, "original_smiles": s.original_smiles,
                            "url": s.url, "retrieved_at": s.retrieved_at, "note": s.note} for s in c.sources],
        "experimental_bioactivity": [{
            "id": a.id, "target": a.target_symbol, "uniprot_id": a.uniprot_id, "source_db": a.source_db,
            "external_id": a.external_id, "type": a.standard_type, "relation": a.relation, "value_nm": a.value_nm,
            "pvalue": a.pvalue, "assay_ref": a.assay_ref, "evidence_type": a.evidence_type, "retrieved_at": a.retrieved_at,
        } for a in exp],
        "predictions": [{
            "id": p.id, "run_id": p.run_id, "target": p.target_symbol, "uniprot_id": p.uniprot_id, "model": p.model_name,
            "model_version": p.model_version, "predicted_kd": p.value, "units": p.units, "pkd": p.pkd,
            "evidence_type": p.evidence_type, "created_at": p.created_at,
        } for p in preds],
        "annotations": [{"id": a.id, "author": a.author, "text": a.text, "created_at": a.created_at} for a in c.annotations],
        "collections": [{"id": x.id, "name": x.name} for x in cols],
        "evidence_notice": "experimental_bioactivity = measured values from external databases; "
                           "predictions = computational estimates, not experimental confirmation.",
    })
    return prof


@router.delete("/compounds/{compound_id}")
def delete_compound(compound_id: int, db: Session = Depends(get_db)):
    c = _get(db, compound_id)
    if c.origin != m.ORIGIN_GENERATED:
        raise HTTPException(409, "Only generated compounds can be deleted; reference/external records are provenance-tracked.")
    if db.query(m.MoleculeRecord).filter_by(compound_id=c.id).first():
        raise HTTPException(409, "Compound belongs to a discovery run; delete the run first.")
    db.delete(c)
    db.commit()
    return {"deleted": compound_id}


# ── create / import ───────────────────────────────────────────────────────
class NewCompound(BaseModel):
    smiles: str = Field(..., min_length=1)
    name: Optional[str] = None
    note: Optional[str] = None


@router.post("/compounds", status_code=201)
def add_compound(body: NewCompound, db: Session = Depends(get_db)):
    try:
        c, created = registry.register_compound(db, body.smiles, origin=m.ORIGIN_EXTERNAL, source_db="user_upload",
                                                external_id="", name=body.name, note=body.note)
    except chem.InvalidMolecule as exc:
        raise HTTPException(422, str(exc))
    db.commit()
    return {"created": created, "compound": _summary(c)}


@router.post("/import/reference")
def import_reference(db: Session = Depends(get_db)):
    return registry.import_reference_collections(db)


class PubChemImport(BaseModel):
    name: str = Field(..., min_length=1)


@router.post("/import/pubchem")
def import_pubchem(body: PubChemImport, db: Session = Depends(get_db)):
    res = ingest.ingest_pubchem_by_name(db, body.name)     # ExternalServiceError -> 502 via handler
    if not res["found"]:
        raise HTTPException(404, f"PubChem has no compound named {body.name!r}")
    return res


class TargetImport(BaseModel):
    target: str
    sources: List[str] = Field(default_factory=lambda: ["chembl", "bindingdb"])
    max_records: int = Field(200, ge=1, le=2000)


@router.post("/import/target")
def import_target(body: TargetImport, db: Session = Depends(get_db)):
    bad = [s for s in body.sources if s not in ("chembl", "bindingdb")]
    if bad:
        raise HTTPException(422, f"Unknown sources {bad}")
    rep = ingest.ingest_target_bioactivity(db, body.target, body.sources, body.max_records)
    if rep["errors"] and not rep["sources"]:
        raise HTTPException(502, {"message": "All requested sources failed", **rep})
    return rep


# ── similarity ────────────────────────────────────────────────────────────
class SimilarityQuery(BaseModel):
    smiles: Optional[str] = None
    compound_id: Optional[int] = None
    k: int = Field(10, ge=1, le=100)
    method: str = Field("fingerprint", pattern="^(fingerprint|embedding|both)$")
    origin: Optional[str] = Field(None, pattern="^(reference|external|generated)$")


@router.post("/similarity")
def similarity(body: SimilarityQuery, db: Session = Depends(get_db)):
    if body.compound_id is not None:
        query = _get(db, body.compound_id).canonical_smiles
        exclude = body.compound_id
    elif body.smiles:
        query, exclude = body.smiles, None
        try:
            std = chem.standardise(body.smiles)
        except chem.InvalidMolecule as exc:
            raise HTTPException(422, str(exc))
        query = std.canonical_smiles
        found = registry.get_by_inchikey(db, std.inchikey)
        exclude = found.id if found else None
    else:
        raise HTTPException(422, "Provide smiles or compound_id")

    want_emb = body.method in ("embedding", "both")
    similarity_index.ensure_current(db, with_embeddings=want_emb)
    results: Dict[str, List[Dict]] = {}
    fetch_k = body.k * 4 if body.origin else body.k

    def pack(neigh):
        rows = []
        ids = [n.compound_id for n in neigh]
        comps = {c.id: c for c in db.query(m.Compound).filter(m.Compound.id.in_(ids)).all()} if ids else {}
        counts = _counts(db, ids)
        for n in neigh:
            c = comps.get(n.compound_id)
            if c is None or (body.origin and c.origin != body.origin):
                continue
            rows.append({"similarity": round(n.similarity, 4), "method": n.method,
                         "compound": _summary(c, counts[c.id]["exp"], counts[c.id]["pred"])})
        return rows[:body.k]

    if body.method in ("fingerprint", "both"):
        results["fingerprint"] = pack(similarity_index.search_fingerprint(query, fetch_k, exclude_id=exclude))
    if want_emb:
        from ..services.embeddings import EmbeddingUnavailable
        try:
            results["embedding"] = pack(similarity_index.search_embedding(query, fetch_k, exclude_id=exclude))
        except EmbeddingUnavailable as exc:
            raise HTTPException(503, f"Embedding similarity unavailable: {exc}")
    return {"query_smiles": query, "k": body.k, "registry_size": similarity_index.size, "results": results,
            "notes": {"fingerprint": "Morgan r=2 2048-bit, FAISS binary index re-ranked by exact Tanimoto",
                      "embedding": "ChemBERTa CLS embedding, cosine similarity (FAISS inner product)"}}


@router.post("/index/rebuild")
def rebuild_index(with_embeddings: bool = False, db: Session = Depends(get_db)):
    from ..services.embeddings import EmbeddingUnavailable
    try:
        return similarity_index.rebuild(db, with_embeddings=with_embeddings)
    except EmbeddingUnavailable as exc:
        raise HTTPException(503, f"Embedding index unavailable: {exc}")


class CompareBody(BaseModel):
    compound_ids: List[int] = Field(..., min_length=2, max_length=8)


@router.post("/compare")
def compare(body: CompareBody, db: Session = Depends(get_db)):
    comps = [_get(db, i) for i in body.compound_ids]
    counts = _counts(db, [c.id for c in comps])
    matrix = [[1.0 if a.id == b.id else round(chem.tanimoto(a.canonical_smiles, b.canonical_smiles) or 0.0, 4)
               for b in comps] for a in comps]
    best = {}
    for c in comps:
        for a in db.query(m.Bioactivity).filter_by(compound_id=c.id).all():
            key = (c.id, a.target_symbol)
            if key not in best or a.value_nm < best[key]["value_nm"]:
                best[key] = {"type": a.standard_type, "value_nm": a.value_nm, "source_db": a.source_db}
    preds = {}
    for p in db.query(m.Prediction).filter(m.Prediction.compound_id.in_([c.id for c in comps])).order_by(m.Prediction.created_at).all():
        preds[(p.compound_id, p.target_symbol)] = {"predicted_kd_nm": p.value, "pkd": p.pkd, "model": p.model_name}
    targets = sorted({t for (_, t) in list(best) + list(preds)})
    return {
        "compounds": [_summary(c, counts[c.id]["exp"], counts[c.id]["pred"]) for c in comps],
        "tanimoto_matrix": matrix,
        "per_target": {t: {str(c.id): {"experimental_best": best.get((c.id, t)), "latest_prediction": preds.get((c.id, t))}
                           for c in comps} for t in targets},
    }


# ── collections ───────────────────────────────────────────────────────────
class CollectionBody(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    description: Optional[str] = None


def _col(db: Session, cid: int) -> m.Collection:
    c = db.get(m.Collection, cid)
    if c is None:
        raise HTTPException(404, "Collection not found")
    return c


@router.get("/collections")
def list_collections(db: Session = Depends(get_db)):
    return [{"id": c.id, "name": c.name, "description": c.description, "size": len(c.items), "created_at": c.created_at}
            for c in db.query(m.Collection).order_by(m.Collection.name).all()]


@router.post("/collections", status_code=201)
def create_collection(body: CollectionBody, db: Session = Depends(get_db)):
    if db.query(m.Collection).filter(func.lower(m.Collection.name) == body.name.strip().lower()).first():
        raise HTTPException(409, "A collection with that name already exists")
    c = m.Collection(name=body.name.strip(), description=body.description)
    db.add(c)
    db.commit()
    return {"id": c.id, "name": c.name, "description": c.description, "size": 0}


@router.delete("/collections/{collection_id}")
def delete_collection(collection_id: int, db: Session = Depends(get_db)):
    db.delete(_col(db, collection_id))
    db.commit()
    return {"deleted": collection_id}


class ItemBody(BaseModel):
    compound_id: int


@router.post("/collections/{collection_id}/items", status_code=201)
def add_item(collection_id: int, body: ItemBody, db: Session = Depends(get_db)):
    col = _col(db, collection_id)
    _get(db, body.compound_id)
    if db.query(m.CollectionItem).filter_by(collection_id=col.id, compound_id=body.compound_id).first():
        return {"collection_id": col.id, "compound_id": body.compound_id, "added": False}
    db.add(m.CollectionItem(collection_id=col.id, compound_id=body.compound_id))
    db.commit()
    return {"collection_id": col.id, "compound_id": body.compound_id, "added": True}


@router.delete("/collections/{collection_id}/items/{compound_id}")
def remove_item(collection_id: int, compound_id: int, db: Session = Depends(get_db)):
    item = db.query(m.CollectionItem).filter_by(collection_id=collection_id, compound_id=compound_id).first()
    if item is None:
        raise HTTPException(404, "Item not in collection")
    db.delete(item)
    db.commit()
    return {"removed": compound_id}


# ── annotations ───────────────────────────────────────────────────────────
class AnnotationBody(BaseModel):
    text: str = Field(..., min_length=1, max_length=4000)
    author: Optional[str] = Field(None, max_length=120)


@router.post("/compounds/{compound_id}/annotations", status_code=201)
def add_annotation(compound_id: int, body: AnnotationBody, db: Session = Depends(get_db)):
    c = _get(db, compound_id)
    a = m.Annotation(compound_id=c.id, text=body.text.strip(), author=body.author)
    db.add(a)
    db.commit()
    return {"id": a.id, "author": a.author, "text": a.text, "created_at": a.created_at}


@router.delete("/annotations/{annotation_id}")
def delete_annotation(annotation_id: int, db: Session = Depends(get_db)):
    a = db.get(m.Annotation, annotation_id)
    if a is None:
        raise HTTPException(404, "Annotation not found")
    db.delete(a)
    db.commit()
    return {"deleted": annotation_id}


# ── knowledge graph sync ──────────────────────────────────────────────────
class KGSyncBody(BaseModel):
    target: str


@router.post("/kg/sync")
def kg_sync_target(body: KGSyncBody, db: Session = Depends(get_db)):
    from ..services import kg_sync
    try:
        return kg_sync.sync_all(db, body.target)
    except kg_sync.KGSyncError as exc:
        raise HTTPException(503, str(exc))


# ── evaluation ────────────────────────────────────────────────────────────
eval_router = APIRouter(prefix="/evaluation", tags=["evaluation"])


def _report(r: m.EvaluationReport) -> Dict:
    return {"id": r.id, "kind": r.kind, "created_at": r.created_at, "parameters": r.parameters,
            "dataset": r.dataset, "metrics": r.metrics, "limitations": r.limitations}


class GenEval(BaseModel):
    num_molecules: int = Field(100, ge=10, le=1000)
    seed: int = 0


class SimEval(BaseModel):
    n_queries: int = Field(50, ge=5, le=500)
    k: int = Field(10, ge=1, le=50)
    seed: int = 0
    with_embeddings: bool = False


class DTIEval(BaseModel):
    target: str
    max_compounds: int = Field(200, ge=10, le=1000)


def _run_eval(fn, *a, **kw):
    try:
        return _report(fn(*a, **kw))
    except evaluation.EvaluationError as exc:
        raise HTTPException(409, str(exc))


@eval_router.post("/generation")
def eval_generation(body: GenEval, db: Session = Depends(get_db)):
    return _run_eval(evaluation.evaluate_generation, db, body.num_molecules, body.seed)


@eval_router.post("/similarity")
def eval_similarity(body: SimEval, db: Session = Depends(get_db)):
    return _run_eval(evaluation.evaluate_similarity, db, body.n_queries, body.k, body.seed, body.with_embeddings)


@eval_router.post("/dti")
def eval_dti(body: DTIEval, db: Session = Depends(get_db)):
    return _run_eval(evaluation.evaluate_dti, db, body.target, body.max_compounds)


@eval_router.get("/reports")
def eval_reports(kind: Optional[str] = None, limit: int = Query(20, ge=1, le=100), db: Session = Depends(get_db)):
    q = db.query(m.EvaluationReport)
    if kind:
        q = q.filter(m.EvaluationReport.kind == kind)
    return [_report(r) for r in q.order_by(m.EvaluationReport.created_at.desc()).limit(limit).all()]
