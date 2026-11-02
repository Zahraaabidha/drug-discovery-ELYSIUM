"""Write registry knowledge into the ArangoDB graph, keeping evidence types distinct.

Edge evidence_type values:
  experimental              - measured activity from ChEMBL / BindingDB (never produced by a model)
  computational_prediction  - DeepPurpose predictions from a discovery run
  database_annotation       - curated membership from an external DB (Reactome pathways)

All writes use deterministic keys with overwrite, so retrying a sync is idempotent.
"""
from __future__ import annotations

import datetime as dt
import logging
import os
from typing import Dict, List

from sqlalchemy.orm import Session

from .. import models as m
from ..arangodb_client import get_arango_db
from ..init_arango import init_arango_schema
from .sources import reactome
from .sources.http import ExternalServiceError
from .targets import resolve_target

log = logging.getLogger(__name__)

MAX_EVIDENCE_PER_EDGE = 10


class KGSyncError(RuntimeError):
    pass


class KGDisabled(KGSyncError):
    """ArangoDB integration switched off via ELYSIUM_DISABLE_ARANGO=1 (tests / offline use)."""


def _db():
    if os.getenv("ELYSIUM_DISABLE_ARANGO") == "1":
        raise KGDisabled("ArangoDB integration disabled (ELYSIUM_DISABLE_ARANGO=1)")
    try:
        return init_arango_schema()
    except Exception as exc:
        raise KGSyncError(f"ArangoDB unavailable: {exc}") from exc


def _upsert(col, doc: Dict) -> None:
    col.insert(doc, overwrite=True)


def sync_target(arango, target_symbol: str, with_pathways: bool = True) -> Dict:
    t = resolve_target(target_symbol)
    now = dt.datetime.utcnow().isoformat()
    targets = arango.collection("targets")
    if not targets.has(t.symbol):
        targets.insert({"_key": t.symbol, "symbol": t.symbol, "name": t.symbol, "uniprot_id": t.uniprot_id,
                        "source": "UniProt", "type": "targets"})
    result = {"target": t.symbol, "pathways": 0, "pathway_error": None}
    if with_pathways:
        try:
            paths = reactome.fetch_pathways(t.uniprot_id)
        except ExternalServiceError as exc:
            result["pathway_error"] = str(exc)
            return result
        for p in paths:
            _upsert(arango.collection("pathways"), {"_key": p.st_id, "name": p.name, "source": "Reactome",
                                                      "url": p.url, "type": "pathways"})
            _upsert(arango.collection("participates_in"), {
                "_key": f"{t.symbol}__{p.st_id}", "_from": f"targets/{t.symbol}", "_to": f"pathways/{p.st_id}",
                "evidence_type": "database_annotation", "source": "Reactome", "external_id": p.st_id,
                "url": p.url, "retrieved_at": now, "type": "participates_in",
            })
        result["pathways"] = len(paths)
    return result


def sync_experimental(db: Session, arango, target_symbol: str) -> Dict:
    """One `binds` edge per (compound, target) summarising measured activities; the individual
    measurements (source db, external id, assay reference) are stored on the edge as evidence."""
    t = resolve_target(target_symbol)
    rows = (db.query(m.Bioactivity, m.Compound).join(m.Compound, m.Bioactivity.compound_id == m.Compound.id)
            .filter(m.Bioactivity.target_symbol == t.symbol).all())
    by_compound: Dict[int, Dict] = {}
    for act, comp in rows:
        entry = by_compound.setdefault(comp.id, {"compound": comp, "acts": []})
        entry["acts"].append(act)

    now = dt.datetime.utcnow().isoformat()
    edges = 0
    for entry in by_compound.values():
        comp: m.Compound = entry["compound"]
        acts: List[m.Bioactivity] = sorted(entry["acts"], key=lambda a: a.value_nm)
        _upsert(arango.collection("compounds"), {
            "_key": comp.inchikey, "inchikey": comp.inchikey, "smiles": comp.canonical_smiles,
            "name": comp.name, "origin": comp.origin, "compound_id": comp.id, "type": "compounds",
        })
        best = acts[0]
        _upsert(arango.collection("binds"), {
            "_key": f"exp__{comp.inchikey}__{t.symbol}",
            "_from": f"compounds/{comp.inchikey}", "_to": f"targets/{t.symbol}",
            "evidence_type": "experimental", "relationship": "measured_activity",
            "best_value_nm": best.value_nm, "best_type": best.standard_type, "n_measurements": len(acts),
            "evidence": [{"source_db": a.source_db, "external_id": a.external_id, "type": a.standard_type,
                          "relation": a.relation, "value_nm": a.value_nm, "assay_ref": a.assay_ref}
                         for a in acts[:MAX_EVIDENCE_PER_EDGE]],
            "retrieved_at": now, "type": "binds",
        })
        edges += 1
    return {"target": t.symbol, "compounds": len(by_compound), "experimental_edges": edges}


def sync_run(db: Session, arango, run: m.DiscoveryRun, molecules: List[Dict]) -> Dict:
    """Predicted interactions for the generated molecules of a run.

    `molecules` items: {index, compound_id, smiles, kd_nm, pkd, score, tanimoto_fp, similar_drug}
    """
    now = dt.datetime.utcnow().isoformat()
    model_name = (run.models or {}).get("dti", {}).get("model_name")
    for item in molecules:
        key = f"{run.id}_{item['index']}"
        _upsert(arango.collection("molecules"), {
            "_key": key, "run_id": run.id, "index": item["index"], "target_id": run.target_id,
            "smiles": item["smiles"], "score": item["score"], "compound_id": item["compound_id"],
            "origin": "generated", "type": "molecules",
        })
        _upsert(arango.collection("binds"), {
            "_key": f"pred__{key}__{run.target_id}",
            "_from": f"molecules/{key}", "_to": f"targets/{run.target_id}",
            "evidence_type": "computational_prediction", "relationship": "predicted_binding",
            "predicted_kd_nm": item["kd_nm"], "pkd": item["pkd"], "score": item["score"], "units": "nM",
            "model": model_name, "run_id": run.id, "source": "ELYSIUM/DeepPurpose",
            "retrieved_at": now, "type": "binds",
        })
        if item.get("similar_drug"):
            _upsert(arango.collection("similar_to"), {
                "_key": f"sim__{key}__{item['similar_drug'].lower()}",
                "_from": f"molecules/{key}", "_to": f"drugs/{item['similar_drug'].lower()}",
                "tanimoto": item.get("tanimoto_fp"), "semantic": item.get("semantic"),
                "evidence_type": "computational_prediction", "method": "morgan_r2_2048_tanimoto",
                "run_id": run.id, "type": "similar_to",
            })
    return {"run_id": run.id, "molecules": len(molecules)}


def sync_all(db: Session, target_symbol: str) -> Dict:
    arango = _db()
    out = {"target": sync_target(arango, target_symbol)}
    out["experimental"] = sync_experimental(db, arango, target_symbol)
    return out


def get_arango():
    return _db()
