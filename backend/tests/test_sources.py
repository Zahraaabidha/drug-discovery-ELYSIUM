"""External-source parsing and ingestion.

The payloads below are small samples in the documented response FORMAT of each service, used to
test our parsers and provenance handling offline. Live calls to the real services are in
test_live_services.py (marked `network`).
"""
import pytest

from app import models as m
from app.services.sources import bindingdb, chembl, ingest, pubchem, reactome
from app.services.sources.http import ExternalServiceError

PUBCHEM_PAYLOAD = {"PropertyTable": {"Properties": [
    {"CID": 2244, "MolecularFormula": "C9H8O4", "SMILES": "CC(=O)OC1=CC=CC=C1C(=O)O",
     "InChIKey": "BSYNRYMUTXBXSQ-UHFFFAOYSA-N", "Title": "Aspirin"}]}}

CHEMBL_RAW = {"activity_id": 32260, "molecule_chembl_id": "CHEMBL68920", "canonical_smiles": "CCO",
              "standard_type": "IC50", "standard_value": "41.0", "standard_units": "nM", "standard_relation": "=",
              "pchembl_value": "7.39", "assay_chembl_id": "CHEMBL674637", "document_chembl_id": "CHEMBL1134862"}


def test_pubchem_parser():
    [c] = pubchem.parse_properties(PUBCHEM_PAYLOAD)
    assert c.cid == "2244" and c.title == "Aspirin" and c.url.endswith("/2244")
    assert pubchem.parse_properties(None) == []


def test_chembl_parser_accepts_nm_and_rejects_others():
    act = chembl.parse_activity(CHEMBL_RAW, "CHEMBL203")
    assert act.value_nm == 41.0 and act.pvalue == pytest.approx(7.39) and act.assay_ref == "CHEMBL1134862"
    assert chembl.parse_activity({**CHEMBL_RAW, "standard_units": "ug.mL-1"}, "T") is None
    assert chembl.parse_activity({**CHEMBL_RAW, "standard_value": None}, "T") is None
    assert chembl.parse_activity({**CHEMBL_RAW, "canonical_smiles": None}, "T") is None


@pytest.mark.parametrize("text,expected", [("12.5", ("=", 12.5)), (">10000", (">", 10000.0)),
                                           ("<0.5", ("<", 0.5)), (">=5", (">", 5.0)), ("n/a", None), (None, None)])
def test_bindingdb_affinity_parser(text, expected):
    assert bindingdb.parse_affinity(text) == expected


def test_bindingdb_response_parser_keeps_valid_rows():
    payload = {"getLindsByUniprotsResponse": {"affinities": [
        {"monomerid": "1", "smile": "CCO", "affinity_type": "Ki", "affinity": "0.5", "pmid": "123"},
        {"monomerid": "2", "smile": "CCN", "affinity_type": "Ki", "affinity": ">1000"},
        {"monomerid": "3", "smile": "", "affinity_type": "Kd", "affinity": "5"},
        {"monomerid": "4", "smile": "CCC", "affinity_type": "pH", "affinity": "5"}]}}
    acts = bindingdb.parse_response(payload)
    assert [a.monomer_id for a in acts] == ["1", "2"]
    assert acts[0].assay_ref == "PMID:123" and acts[0].pvalue == pytest.approx(9.30103, abs=1e-4)


def test_reactome_parser():
    paths = reactome.parse_pathways([{"stId": "R-HSA-1", "displayName": "X", "speciesName": "Homo sapiens"}, {}])
    assert len(paths) == 1 and paths[0].url.endswith("R-HSA-1")


def _stub_chembl(monkeypatch, rows):
    monkeypatch.setattr(chembl, "fetch_activities", lambda uniprot, max_records=200: ("CHEMBL203", rows))


def test_ingest_stores_bioactivity_with_provenance_and_is_idempotent(db, monkeypatch):
    rows = [chembl.parse_activity({**CHEMBL_RAW, "canonical_smiles": "CC(=O)Nc1ccc(O)cc1"}, "CHEMBL203"),   # paracetamol (reference)
            chembl.parse_activity({**CHEMBL_RAW, "activity_id": 2, "molecule_chembl_id": "CHEMBL999",
                                   "canonical_smiles": "CCCCCCN1CCOCC1"}, "CHEMBL203")]
    _stub_chembl(monkeypatch, rows)
    monkeypatch.setattr(ingest.bindingdb, "fetch_activities",
                        lambda *a, **k: (_ for _ in ()).throw(ExternalServiceError("BindingDB", "down")))
    rep = ingest.ingest_target_bioactivity(db, "EGFR", ["chembl", "bindingdb"])
    assert rep["sources"]["chembl"]["new_bioactivities"] == 2 and rep["sources"]["chembl"]["new_compounds"] == 1
    assert "bindingdb" in rep["errors"]                        # one failing source does not hide the other
    acts = db.query(m.Bioactivity).all()
    assert all(a.evidence_type == "experimental" and a.source_db == "chembl" and a.target_symbol == "EGFR" for a in acts)
    para = db.query(m.Compound).filter_by(name="Paracetamol").one()
    assert para.origin == m.ORIGIN_REFERENCE and any(s.source_db == "chembl" for s in para.sources)
    again = ingest.ingest_target_bioactivity(db, "EGFR", ["chembl"])
    assert again["sources"]["chembl"]["new_bioactivities"] == 0 and db.query(m.Bioactivity).count() == 2


def test_ingest_rejects_unsupported_target(db):
    from app.services.targets import UnsupportedTarget
    with pytest.raises(UnsupportedTarget):
        ingest.ingest_target_bioactivity(db, "NOT_A_TARGET")


def test_ingest_skips_invalid_structures(db, monkeypatch):
    bad = chembl.ChemblActivity("9", "CHEMBLX", "this is not smiles", "Ki", "=", 5.0, 8.3, "D", "CHEMBL203")
    _stub_chembl(monkeypatch, [bad])
    rep = ingest.ingest_target_bioactivity(db, "EGFR", ["chembl"])
    assert rep["sources"]["chembl"]["invalid_structures"] == 1 and db.query(m.Bioactivity).count() == 0


def test_duplicate_records_within_one_batch_are_not_double_inserted(db, monkeypatch):
    """Regression: real BindingDB/ChEMBL payloads repeat records; sessions run with autoflush off."""
    act = chembl.parse_activity({**CHEMBL_RAW, "canonical_smiles": "CCCCCCN1CCOCC1"}, "CHEMBL203")
    _stub_chembl(monkeypatch, [act, act, act])
    rep = ingest.ingest_target_bioactivity(db, "EGFR", ["chembl"])
    assert rep["sources"]["chembl"]["records"] == 3 and rep["sources"]["chembl"]["new_bioactivities"] == 1
    assert db.query(m.Bioactivity).count() == 1
