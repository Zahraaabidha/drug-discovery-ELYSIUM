from .arangodb_client import get_arango_db
from .core.config import known_targets
from .fda_library import FDA_LIKE_DRUGS
from .init_arango import init_arango_schema

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

DISEASES = {
    "nsclc": "Non-small cell lung cancer",
    "breast_cancer": "Breast cancer",
    "parkinsons": "Parkinson's disease",
    "alzheimers": "Alzheimer's disease",
    "cml": "Chronic myeloid leukemia",
    "melanoma": "Melanoma",
    "hiv": "HIV/AIDS",
}

TARGET_DISEASE = [("EGFR", "nsclc"), ("HER2", "breast_cancer"), ("ESR1", "breast_cancer"),
                  ("DRD2", "parkinsons"), ("BACE1", "alzheimers"), ("ABL1", "cml"),
                  ("BRAF", "melanoma"), ("HIV1_PROTEASE", "hiv")]
DRUG_DISEASE = [("gefitinib", "nsclc"), ("erlotinib", "nsclc"), ("tamoxifen", "breast_cancer"),
                ("levodopa", "parkinsons"), ("donepezil", "alzheimers")]
DRUG_TARGET = [("gefitinib", "EGFR"), ("erlotinib", "EGFR"), ("tamoxifen", "ESR1"), ("levodopa", "DRD2")]


def _upsert(col, key, doc):
    if col.has(key):
        col.update({"_key": key, **doc})
    else:
        col.insert({"_key": key, **doc})


def _edge(col, a, b, **props):
    if not list(col.find({"_from": a, "_to": b}, limit=1)):
        col.insert({"_from": a, "_to": b, **props})


def seed_basic_kg():
    init_arango_schema()
    db = get_arango_db()

    for tid, entry in known_targets().items():
        _upsert(db.collection("targets"), tid, {
            "symbol": tid, "name": TARGET_NAMES.get(tid, tid),
            "uniprot_id": entry["uniprot_id"],
        })
    for d in FDA_LIKE_DRUGS:
        _upsert(db.collection("drugs"), d["name"].lower(), {
            "name": d["name"], "smiles": d["smiles"], "indication": d.get("indication"),
        })
    for key, name in DISEASES.items():
        _upsert(db.collection("diseases"), key, {"name": name})

    for t, dis in TARGET_DISEASE:
        _edge(db.collection("associated_with"), f"targets/{t}", f"diseases/{dis}", source="curated")
    for drug, dis in DRUG_DISEASE:
        _edge(db.collection("treats"), f"drugs/{drug}", f"diseases/{dis}", source="curated")
    for drug, t in DRUG_TARGET:
        _edge(db.collection("binds"), f"drugs/{drug}", f"targets/{t}", source="curated")


if __name__ == "__main__":
    seed_basic_kg()
    print("ArangoDB knowledge graph seeded")
