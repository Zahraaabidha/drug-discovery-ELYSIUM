from .arangodb_client import get_arango_db

def seed_basic_kg():
    db = get_arango_db()

    targets = db.collection("targets")
    drugs = db.collection("drugs")
    binds = db.collection("binds")
    diseases = db.collection("diseases")
    treats = db.collection("treats")

    # Upsert helper
    def upsert(col, key, doc):
        if col.has(key):
            col.update({ "_key": key, **doc })
        else:
            col.insert({ "_key": key, **doc })

    # EGFR example
    upsert(
        targets,
        "EGFR",
        {
            "symbol": "EGFR",
            "name": "Epidermal growth factor receptor",
            "uniprot_id": "P00533",
            "sequence": "...optional..."
        },
    )

    # Drugs
    upsert(
        drugs,
        "ibuprofen",
        {
            "name": "Ibuprofen",
            "smiles": "CC(C)CC1=CC=C(C=C1)C(C)C(=O)O",
            "indication": "Pain relief, anti-inflammatory",
        },
    )
    # paracetamol, aspirin, caffeine, lidocaine … same pattern

    # Example disease
    upsert(
        diseases,
        "nsclc",
        {"name": "Non-small cell lung cancer"}
    )

    # Relationships
    binds.insert({
        "_from": "drugs/ibuprofen",
        "_to": "targets/EGFR",
        "source": "literature_stub",
    })

    # Eg. some EGFR-targeted real TKIs if you later add them:
    # binds.insert({"_from": "drugs/gefitinib", "_to": "targets/EGFR", ...})

if __name__ == "__main__":
    seed_basic_kg()
