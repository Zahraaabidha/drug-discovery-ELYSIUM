"""Seed the ArangoDB knowledge graph with entities that have a verifiable source.

Only structural entities are seeded here: supported targets (UniProt) and the bundled reference
drugs. Relationships are NOT hand-written: experimental links come from ChEMBL / BindingDB
ingestion, predicted links from discovery runs, pathway links from Reactome (see services/kg_sync.py).
Hand-written ("curated") relationships created by earlier versions are removed because they carried
no citable evidence.
"""
import logging

from .arangodb_client import get_arango_db
from .fda_library import FDA_LIKE_DRUGS
from .init_arango import init_arango_schema
from .services.targets import all_targets

log = logging.getLogger(__name__)

TARGET_NAMES = {
    "EGFR": "Epidermal growth factor receptor",
    "DRD2": "D(2) dopamine receptor",
    "VEGFR2": "Vascular endothelial growth factor receptor 2",
    "ABL1": "Tyrosine-protein kinase ABL1",
    "BRAF": "Serine/threonine-protein kinase B-raf",
    "HER2": "Receptor tyrosine-protein kinase erbB-2",
    "ESR1": "Estrogen receptor alpha",
    "CDK2": "Cyclin-dependent kinase 2",
    "BACE1": "Beta-secretase 1",
    "HIV1_PROTEASE": "HIV-1 Gag-Pol polyprotein / protease",
}


def _upsert(col, key, doc):
    if col.has(key):
        col.update({"_key": key, **doc})
    else:
        col.insert({"_key": key, **doc})


def _purge_unsourced(db) -> int:
    """Delete relationships/diseases that earlier versions hand-wrote without evidence."""
    removed = 0
    for edge_col in ("binds", "treats", "associated_with"):
        if db.has_collection(edge_col):
            cur = db.aql.execute(
                "FOR e IN @@c FILTER e.source IN ['curated','literature_stub'] REMOVE e IN @@c RETURN 1",
                bind_vars={"@c": edge_col})
            removed += len(list(cur))
    # relationships/molecules written by the pre-registry pipeline carry no evidence type or provenance
    for edge_col in ("binds", "similar_to"):
        if db.has_collection(edge_col):
            removed += len(list(db.aql.execute(
                "FOR e IN @@c FILTER e.evidence_type == null REMOVE e IN @@c RETURN 1", bind_vars={"@c": edge_col})))
    if db.has_collection("molecules"):
        removed += len(list(db.aql.execute("FOR m IN molecules FILTER m.origin == null REMOVE m IN molecules RETURN 1")))
    if db.has_collection("diseases"):
        removed += len(list(db.aql.execute("FOR d IN diseases REMOVE d IN diseases RETURN 1")))
    return removed


def seed_basic_kg():
    init_arango_schema()
    db = get_arango_db()
    purged = _purge_unsourced(db)
    if purged:
        log.info("Removed %d unsourced hand-written KG documents", purged)

    for sym, t in all_targets().items():
        _upsert(db.collection("targets"), sym, {
            "symbol": sym, "name": TARGET_NAMES.get(sym, sym), "uniprot_id": t.uniprot_id,
            "source": "UniProt", "type": "targets",
        })
    for d in FDA_LIKE_DRUGS:
        _upsert(db.collection("drugs"), d["name"].lower(), {
            "name": d["name"], "smiles": d["smiles"], "indication": d.get("indication"),
            "origin": "reference", "source": "elysium_reference", "type": "drugs",
        })


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    seed_basic_kg()
    print("ArangoDB knowledge graph seeded")
