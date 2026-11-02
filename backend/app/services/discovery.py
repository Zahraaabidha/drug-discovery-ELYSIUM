"""ELYSIUM discovery pipeline (registry-backed, reproducible).

1. Resolve the target (unsupported targets are rejected, never substituted).
2. Generate NEW molecules from registry seed compounds (validity/uniqueness/novelty tracked).
3. Apply physicochemical filters to candidates.
4. Predict drug-target interaction with DeepPurpose (failure => error, no placeholder scores).
5. Register the selected molecules (origin = generated) and store predictions with units/model info.
6. Compare with known compounds (Morgan fingerprints / FAISS, ChemBERTa).
7. Persist the run with its parameters, seed, models, data sources and metrics.
8. Sync relationships to the ArangoDB knowledge graph (status recorded on the run).
"""
from __future__ import annotations

import logging
import random
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from .. import models as m
from ..schemas import ADMETProperties, DiscoveryRequest, DiscoveryResponse, Molecule, NearestKnown, SimilarDrug
from ..similarity import find_combined_similar_drugs
from . import chem, registry
from .generation import get_generator
from .kg import attach_run_to_kg
from .scoring import ScoringError, get_scorer
from .similarity_index import index as similarity_index
from .targets import resolve_target

log = logging.getLogger(__name__)

OVERSAMPLE = 3          # candidates generated per requested molecule
MAX_SEED_COMPOUNDS = 400


def _req_to_dict(req) -> Dict:
    if isinstance(req, dict):
        return DiscoveryRequest(**req).model_dump()
    if isinstance(req, DiscoveryRequest):
        return req.model_dump()
    return DiscoveryRequest(**dict(req)).model_dump()


def passes_filters(pc: chem.PhysChem, p: Dict) -> bool:
    """Physicochemical filters from the request. Every supplied filter is enforced."""
    if p.get("lipinski_only") and not pc.lipinski_pass:
        return False
    checks = [
        (p.get("min_mw"), lambda v: pc.mol_weight >= v), (p.get("max_mw"), lambda v: pc.mol_weight <= v),
        (p.get("min_logp"), lambda v: pc.logp >= v), (p.get("max_logp"), lambda v: pc.logp <= v),
        (p.get("max_tpsa"), lambda v: pc.tpsa <= v), (p.get("max_hbd"), lambda v: pc.hbd <= v),
        (p.get("max_hba"), lambda v: pc.hba <= v), (p.get("max_rotatable_bonds"), lambda v: pc.rotatable_bonds <= v),
    ]
    return all(ok(v) for v, ok in checks if v is not None)


def _physchem_schema(pc: chem.PhysChem) -> ADMETProperties:
    return ADMETProperties(
        molecular_weight=pc.mol_weight, logp=pc.logp, hbd=pc.hbd, hba=pc.hba, rotatable_bonds=pc.rotatable_bonds,
        tpsa=pc.tpsa, lipinski_violations=pc.lipinski_violations, lipinski_pass=pc.lipinski_pass,
    )


def _nearest_known(db: Session, smiles: str, own_id: Optional[int], k: int = 3) -> List[NearestKnown]:
    out = []
    for n in similarity_index.search_fingerprint(smiles, k=k + 1, exclude_id=own_id)[:k]:
        c = db.get(m.Compound, n.compound_id)
        if c is not None:
            out.append(NearestKnown(compound_id=c.id, name=c.name, origin=c.origin, tanimoto=round(n.similarity, 4)))
    return out


def run_discovery(req, db: Session) -> DiscoveryResponse:
    p = _req_to_dict(req)
    target = resolve_target(p["target_id"])          # raises UnsupportedTarget
    seed = p["seed"] if p.get("seed") is not None else random.SystemRandom().randrange(2**31)
    n = p["num_molecules"]

    # Registry must contain the reference library before we generate / compare.
    if db.query(m.Compound).count() == 0:
        registry.import_reference_collections(db)

    scorer = get_scorer()
    scorer_info = scorer.model_info()
    models_used = {
        "dti": scorer_info,
        "embedding": None,
        "fingerprint": {"type": "morgan", "radius": chem.FP_RADIUS, "bits": chem.FP_BITS},
    }
    try:
        from .embeddings import embedding_model_name
        models_used["embedding"] = {"model_name": embedding_model_name()}
    except Exception:  # pragma: no cover
        pass

    known_keys = {ik for (ik,) in db.query(m.Compound.inchikey).all()}
    seed_rows = (db.query(m.Compound.canonical_smiles)
                 .filter(m.Compound.origin.in_([m.ORIGIN_REFERENCE, m.ORIGIN_EXTERNAL]))
                 .order_by(m.Compound.id).limit(MAX_SEED_COMPOUNDS).all())
    generator = get_generator([s for (s,) in seed_rows])

    run = m.DiscoveryRun(
        target_id=target.symbol, num_molecules=0, status="running", seed=seed,
        params={**{k: v for k, v in p.items() if k != "seed"}, "oversample": OVERSAMPLE},
        models=models_used,
        data_sources={
            "target_sequence": {"source": "UniProt", "accession": target.uniprot_id},
            "seed_compounds": len(seed_rows), "registry_compounds": len(known_keys),
            "reference_library": registry.REFERENCE_SOURCE,
        },
    )
    db.add(run)
    db.flush()

    def fail(reason: str, exc: Exception):
        run.status, run.error = "failed", reason
        db.commit()
        raise exc

    # 2) generate
    gen = generator.generate(target.symbol, n * OVERSAMPLE, seed=seed, known_inchikeys=known_keys)
    run.params = {**run.params, "generation": gen.params}

    # 3) physicochemical filters
    candidates: List[str] = []
    rejected = 0
    for smi in gen.smiles:
        if passes_filters(chem.physchem(smi), p):
            candidates.append(smi)
        else:
            rejected += 1
    metrics: Dict = {"generation": gen.stats.as_dict(), "filtered_out_by_physchem": rejected,
                     "candidates_scored": len(candidates)}

    if not candidates:
        run.status, run.metrics = "completed", metrics
        run.num_molecules = 0
        db.commit()
        return _response(run, [])

    # 4) DTI prediction - failures propagate (no placeholder scores)
    try:
        preds = scorer.predict(candidates, target.sequence, target.symbol)
    except ScoringError as exc:
        fail(str(exc), exc)
    ranked = sorted(zip(candidates, preds), key=lambda x: x[1].kd_nm)[:n]     # lowest predicted Kd first

    # 5) register + store predictions
    selected: List[Dict] = []
    for idx, (smi, pred) in enumerate(ranked):
        comp, _ = registry.register_compound(
            db, smi, origin=m.ORIGIN_GENERATED, source_db=registry.GENERATOR_SOURCE, external_id=f"{run.id}:{idx}",
            generation_method=gen.stats.method, generation_run_id=run.id, note=f"seed={seed}",
        )
        pred_row = registry.record_prediction(
            db, comp, target_symbol=target.symbol, uniprot_id=target.uniprot_id,
            model_name=scorer_info["model_name"], model_version=scorer_info.get("model_version"),
            value_nm=pred.kd_nm, run_id=run.id, params={"aggregation": scorer_info.get("aggregation")},
        )
        selected.append({"index": idx, "smiles": comp.canonical_smiles, "comp": comp, "pred": pred, "row": pred_row})

    similarity_index.ensure_current(db)

    # 6) comparison + persistence
    response_mols: List[Molecule] = []
    kg_items: List[Dict] = []
    for item in selected:
        comp, pred = item["comp"], item["pred"]
        pc = chem.physchem(comp.canonical_smiles)
        fp_neighbor, semantic_neighbor = find_combined_similar_drugs(comp.canonical_smiles)
        note = [f"Computational DTI prediction for {target.symbol}: Kd ~ {pred.kd_nm:.3g} nM (pKd {pred.pkd:.2f})."]
        if fp_neighbor is not None:
            note.append(f"Closest named reference drug (Morgan Tanimoto): {fp_neighbor.name} ({fp_neighbor.similarity:.2f}).")
        if semantic_neighbor is not None and semantic_neighbor.semantic_similarity is not None and (
                fp_neighbor is None or semantic_neighbor.name != fp_neighbor.name):
            note.append(f"ChemBERTa nearest: {semantic_neighbor.name} (cosine {semantic_neighbor.semantic_similarity:.2f}).")
        note.append(f"Lipinski {'pass' if pc.lipinski_pass else 'fail'} ({pc.lipinski_violations} violations).")

        db.add(m.MoleculeRecord(
            run_id=run.id, compound_id=comp.id, smiles=comp.canonical_smiles, score=pred.normalised,
            source="generated", notes=" ".join(note), scorer_used=scorer.name,
            admet_mw=pc.mol_weight, admet_logp=pc.logp, admet_hbd=pc.hbd, admet_hba=pc.hba, admet_tpsa=pc.tpsa,
            admet_rotatable_bonds=pc.rotatable_bonds, admet_lipinski_pass=int(pc.lipinski_pass),
            admet_lipinski_violations=pc.lipinski_violations,
            similar_drug_fp=fp_neighbor.name if fp_neighbor else None,
            tanimoto_fp=fp_neighbor.similarity if fp_neighbor else None,
            similar_drug_semantic=semantic_neighbor.name if semantic_neighbor else None,
            tanimoto_semantic=semantic_neighbor.semantic_similarity if semantic_neighbor else None,
        ))
        response_mols.append(Molecule(
            smiles=comp.canonical_smiles, score=pred.normalised, source=scorer.name, notes=" ".join(note),
            similar_drug=fp_neighbor, similar_drug_semantic=semantic_neighbor, admet=_physchem_schema(pc),
            compound_id=comp.id, origin=comp.origin, predicted_kd_nm=pred.kd_nm, pkd=pred.pkd,
            model=scorer_info["model_name"], nearest_known=_nearest_known(db, comp.canonical_smiles, comp.id),
        ))
        kg_items.append({
            "index": item["index"], "compound_id": comp.id, "smiles": comp.canonical_smiles, "kd_nm": pred.kd_nm,
            "pkd": pred.pkd, "score": pred.normalised,
            "similar_drug": fp_neighbor.name if fp_neighbor else None,
            "tanimoto_fp": fp_neighbor.similarity if fp_neighbor else None,
            "semantic": semantic_neighbor.semantic_similarity if semantic_neighbor else None,
        })

    run.num_molecules = len(response_mols)
    run.status = "completed"
    metrics["returned"] = len(response_mols)
    run.metrics = metrics
    db.flush()

    # legacy SQL knowledge graph (kept for existing pages)
    try:
        attach_run_to_kg(db, run, response_mols)
    except Exception:
        log.exception("Legacy SQL KG attach failed")
    db.commit()

    # 8) ArangoDB: failure is recorded on the run, never silent
    from . import kg_sync
    try:
        arango = kg_sync.get_arango()
        kg_sync.sync_target(arango, target.symbol, with_pathways=False)
        kg_sync.sync_run(db, arango, run, kg_items)
        run.metrics = {**run.metrics, "knowledge_graph": {"status": "ok"}}
    except kg_sync.KGDisabled as exc:
        run.metrics = {**run.metrics, "knowledge_graph": {"status": "disabled", "reason": str(exc)}}
    except Exception as exc:
        log.exception("ArangoDB sync failed for run %s", run.id)
        run.metrics = {**run.metrics, "knowledge_graph": {"status": "failed", "error": str(exc)}}
    db.commit()
    return _response(run, response_mols)


def _response(run: m.DiscoveryRun, molecules: List[Molecule]) -> DiscoveryResponse:
    return DiscoveryResponse(
        run_id=run.id, target_id=run.target_id, num_molecules=len(molecules), molecules=molecules,
        status=run.status, seed=run.seed, params=run.params, models=run.models,
        data_sources=run.data_sources, metrics=run.metrics,
    )
