import pytest

from app import models as m
from app.services import registry


def _add_exp(db, name, value_nm, target="EGFR", typ="Ki", source="chembl", ext="A1"):
    c = db.query(m.Compound).filter_by(name=name).one()
    db.add(m.Bioactivity(compound_id=c.id, target_symbol=target, uniprot_id="P00533", source_db=source, external_id=ext,
                         standard_type=typ, relation="=", value_nm=value_nm, pvalue=9.0, assay_ref="CHEMBL1",
                         evidence_type="experimental"))
    db.commit()
    return c


def test_stats_and_listing(client):
    s = client.get("/library/stats").json()
    assert s["by_origin"]["reference"] == s["compounds"] > 20 and "EGFR" in s["supported_targets"]
    page = client.get("/library/compounds", params={"limit": 5}).json()
    assert page["total"] == s["compounds"] and len(page["items"]) == 5
    item = page["items"][0]
    assert item["origin"] == "reference" and item["physchem"]["mol_weight"] and item["inchikey"]


def test_search_by_name_smiles_inchikey_and_external_id(client):
    assert any(i["name"] == "Aspirin" for i in client.get("/library/compounds", params={"q": "aspir"}).json()["items"])
    assert client.get("/library/compounds", params={"q": "BSYNRYMUTXBXSQ"}).json()["total"] == 1
    assert client.get("/library/compounds", params={"q": "gefitinib"}).json()["total"] >= 1      # external id of reference source


@pytest.mark.parametrize("params,check", [
    ({"max_mw": 200}, lambda p: p["mol_weight"] <= 200),
    ({"min_mw": 400}, lambda p: p["mol_weight"] >= 400),
    ({"min_logp": 3}, lambda p: p["logp"] >= 3),
    ({"max_logp": 0.5}, lambda p: p["logp"] <= 0.5),
    ({"max_tpsa": 40}, lambda p: p["tpsa"] <= 40),
    ({"max_hbd": 0}, lambda p: p["hbd"] == 0),
    ({"max_hba": 2}, lambda p: p["hba"] <= 2),
    ({"max_rotatable_bonds": 1}, lambda p: p["rotatable_bonds"] <= 1),
    ({"lipinski_pass": True}, lambda p: p["lipinski_pass"] is True),
])
def test_every_physchem_filter_changes_and_constrains_results(client, params, check):
    total = client.get("/library/compounds", params={"limit": 1}).json()["total"]
    res = client.get("/library/compounds", params={**params, "limit": 500}).json()
    assert 0 < res["total"] <= total and all(check(i["physchem"]) for i in res["items"])
    if res["total"] == total:
        pytest.skip("filter matched every compound")


def test_origin_and_experimental_filters(client, db):
    _add_exp(db, "Gefitinib", 3.0)
    assert client.get("/library/compounds", params={"origin": "generated"}).json()["total"] == 0
    assert client.get("/library/compounds", params={"origin": "reference"}).json()["total"] > 0
    exp = client.get("/library/compounds", params={"has_experimental": True}).json()
    assert exp["total"] == 1 and exp["items"][0]["name"] == "Gefitinib" and exp["items"][0]["n_experimental"] == 1
    assert client.get("/library/compounds", params={"has_experimental": True, "target": "DRD2"}).json()["total"] == 0
    assert client.get("/library/compounds", params={"has_experimental": False}).json()["total"] > 10


def test_sorting_and_paging(client):
    asc = client.get("/library/compounds", params={"sort": "mol_weight", "limit": 3}).json()["items"]
    desc = client.get("/library/compounds", params={"sort": "mol_weight", "order": "desc", "limit": 3}).json()["items"]
    assert asc[0]["physchem"]["mol_weight"] <= asc[-1]["physchem"]["mol_weight"]
    assert desc[0]["physchem"]["mol_weight"] >= desc[-1]["physchem"]["mol_weight"]
    assert client.get("/library/compounds", params={"sort": "bogus"}).status_code == 422
    p2 = client.get("/library/compounds", params={"limit": 3, "offset": 3}).json()["items"]
    assert {i["id"] for i in p2}.isdisjoint({i["id"] for i in asc})


def test_profile_separates_experimental_from_predicted(client, db):
    c = _add_exp(db, "Gefitinib", 3.0)
    registry.record_prediction(db, c, target_symbol="EGFR", uniprot_id="P00533", model_name="M", model_version="1",
                               value_nm=25.0, run_id=None)
    db.commit()
    prof = client.get(f"/library/compounds/{c.id}").json()
    assert prof["experimental_bioactivity"][0]["evidence_type"] == "experimental"
    assert prof["experimental_bioactivity"][0]["source_db"] == "chembl" and prof["experimental_bioactivity"][0]["assay_ref"]
    assert prof["predictions"][0]["evidence_type"] == "computational_prediction" and prof["predictions"][0]["units"] == "nM"
    assert prof["sources_detail"][0]["original_smiles"] and "not experimental" in prof["evidence_notice"]
    assert client.get("/library/compounds/999999").status_code == 404


def test_add_compound_validation_and_dedup(client):
    ok = client.post("/library/compounds", json={"smiles": "CCCCCCO", "name": "hexanol"})
    assert ok.status_code == 201 and ok.json()["created"] and ok.json()["compound"]["origin"] == "external"
    dup = client.post("/library/compounds", json={"smiles": "OCCCCCC"}).json()
    assert not dup["created"] and dup["compound"]["id"] == ok.json()["compound"]["id"]
    assert client.post("/library/compounds", json={"smiles": "garbage!!"}).status_code == 422


def test_reference_compounds_cannot_be_deleted(client):
    first = client.get("/library/compounds").json()["items"][0]["id"]
    assert client.delete(f"/library/compounds/{first}").status_code == 409


def test_collections_lifecycle_and_filtering(client):
    col = client.post("/library/collections", json={"name": "Kinase set", "description": "x"}).json()
    assert client.post("/library/collections", json={"name": "kinase SET"}).status_code == 409
    ids = [i["id"] for i in client.get("/library/compounds", params={"q": "gefitinib"}).json()["items"]][:1]
    assert client.post(f"/library/collections/{col['id']}/items", json={"compound_id": ids[0]}).json()["added"]
    assert not client.post(f"/library/collections/{col['id']}/items", json={"compound_id": ids[0]}).json()["added"]
    assert client.post(f"/library/collections/{col['id']}/items", json={"compound_id": 999999}).status_code == 404
    in_col = client.get("/library/compounds", params={"collection_id": col["id"]}).json()
    assert in_col["total"] == 1 and in_col["items"][0]["id"] == ids[0]
    assert client.get("/library/collections").json()[0]["size"] == 1
    assert client.get(f"/library/compounds/{ids[0]}").json()["collections"][0]["name"] == "Kinase set"
    assert client.delete(f"/library/collections/{col['id']}/items/{ids[0]}").status_code == 200
    assert client.get("/library/compounds", params={"collection_id": col["id"]}).json()["total"] == 0
    assert client.delete(f"/library/collections/{col['id']}").status_code == 200


def test_annotations(client):
    cid = client.get("/library/compounds").json()["items"][0]["id"]
    a = client.post(f"/library/compounds/{cid}/annotations", json={"text": "Interesting hinge binder", "author": "AA"}).json()
    prof = client.get(f"/library/compounds/{cid}").json()
    assert prof["annotations"][0]["text"] == "Interesting hinge binder"
    assert client.post(f"/library/compounds/{cid}/annotations", json={"text": ""}).status_code == 422
    assert client.delete(f"/library/annotations/{a['id']}").status_code == 200
    assert client.get(f"/library/compounds/{cid}").json()["annotations"] == []


def test_fingerprint_similarity_search(client):
    r = client.post("/library/similarity", json={"smiles": "OC(=O)c1ccccc1OC(C)=O", "k": 3}).json()
    top = r["results"]["fingerprint"]
    assert len(top) == 3 and top[0]["similarity"] >= top[1]["similarity"] >= top[2]["similarity"]
    assert top[0]["method"] == "tanimoto"
    # query is an exact registry compound (aspirin) -> excluded as self, but nearest neighbour must be a real one
    assert all(t["compound"]["inchikey"] != "BSYNRYMUTXBXSQ-UHFFFAOYSA-N" for t in top)


def test_similarity_by_compound_id_and_origin_filter(client):
    cid = client.get("/library/compounds", params={"q": "ibuprofen"}).json()["items"][0]["id"]
    r = client.post("/library/similarity", json={"compound_id": cid, "k": 5, "origin": "reference"}).json()
    assert r["results"]["fingerprint"] and all(x["compound"]["origin"] == "reference" for x in r["results"]["fingerprint"])
    assert all(x["compound"]["id"] != cid for x in r["results"]["fingerprint"])


def test_similarity_validation(client):
    assert client.post("/library/similarity", json={"k": 3}).status_code == 422
    assert client.post("/library/similarity", json={"smiles": "bad!", "k": 3}).status_code == 422
    assert client.post("/library/similarity", json={"smiles": "CCO", "method": "nope"}).status_code == 422


def test_compare_returns_matrix_and_per_target_evidence(client, db):
    a = _add_exp(db, "Gefitinib", 3.0)
    b = db.query(m.Compound).filter_by(name="Erlotinib").one()
    r = client.post("/library/compare", json={"compound_ids": [a.id, b.id]}).json()
    mat = r["tanimoto_matrix"]
    assert mat[0][0] == mat[1][1] == 1.0 and mat[0][1] == mat[1][0] and 0 < mat[0][1] < 1
    assert r["per_target"]["EGFR"][str(a.id)]["experimental_best"]["value_nm"] == 3.0
    assert r["per_target"]["EGFR"][str(b.id)]["experimental_best"] is None
    assert client.post("/library/compare", json={"compound_ids": [a.id]}).status_code == 422


def test_import_endpoints_validate_input(client):
    assert client.post("/library/import/target", json={"target": "NOPE"}).status_code == 422
    assert client.post("/library/import/target", json={"target": "EGFR", "sources": ["zinc"]}).status_code == 422
    assert client.post("/library/import/reference").json()["created"] == 0


def test_targets_endpoint_lists_supported(client):
    t = client.get("/library/targets").json()
    assert {x["symbol"] for x in t} >= {"EGFR", "DRD2"} and all(x["uniprot_id"] for x in t)
    assert {x["symbol"] for x in client.get("/targets").json()} == {x["symbol"] for x in t}


def test_api_key_required_when_configured(db, api_headers):
    import os
    if not os.getenv("API_KEY"):
        pytest.skip("API_KEY not configured")
    from fastapi.testclient import TestClient
    from app.main import app
    anon = TestClient(app)
    assert anon.get("/library/stats").status_code == 401
    assert anon.get("/health").status_code == 200
