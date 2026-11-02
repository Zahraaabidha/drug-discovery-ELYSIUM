"""Integration tests against a real ArangoDB (database `elysium_test`, dropped afterwards)."""
import pytest

from app import models as m

pytestmark = pytest.mark.arango


@pytest.fixture()
def arango(monkeypatch):
    monkeypatch.delenv("ELYSIUM_DISABLE_ARANGO", raising=False)
    monkeypatch.setenv("ARANGO_DB_NAME", "elysium_test")
    try:
        from arango import ArangoClient
        from app.arangodb_client import _settings
        cfg = _settings()
        sys_db = ArangoClient(hosts=cfg["url"]).db("_system", username=cfg["username"], password=cfg["password"])
        sys_db.version()
    except Exception as exc:
        pytest.skip(f"ArangoDB not reachable: {exc}")
    from app.services import kg_sync
    db = kg_sync.get_arango()
    yield db
    sys_db.delete_database("elysium_test", ignore_missing=True)


def test_schema_has_named_graph_with_evidence_aware_edges(arango):
    graph = arango.graph("elysium_graph")
    defs = {d["edge_collection"]: d for d in graph.edge_definitions()}
    assert {"binds", "participates_in", "similar_to"} <= set(defs)
    assert "compounds" in defs["binds"]["from_vertex_collections"]
    assert "pathways" in defs["participates_in"]["to_vertex_collections"]


def test_experimental_and_predicted_edges_are_distinct_and_idempotent(arango, db):
    from app.services import kg_sync, registry
    gef = db.query(m.Compound).filter_by(name="Gefitinib").one()
    db.add(m.Bioactivity(compound_id=gef.id, target_symbol="EGFR", uniprot_id="P00533", source_db="chembl",
                         external_id="a1", standard_type="IC50", relation="=", value_nm=33.0, pvalue=7.48,
                         assay_ref="CHEMBL1", evidence_type="experimental"))
    db.commit()
    kg_sync.sync_target(arango, "EGFR", with_pathways=False)
    for _ in range(2):                                                  # second pass must not duplicate
        out = kg_sync.sync_experimental(db, arango, "EGFR")
    assert out["experimental_edges"] == 1
    exp = list(arango.collection("binds").find({"evidence_type": "experimental"}))
    assert len(exp) == 1 and exp[0]["_to"] == "targets/EGFR" and exp[0]["best_value_nm"] == 33.0
    assert exp[0]["evidence"][0]["source_db"] == "chembl" and exp[0]["evidence"][0]["assay_ref"] == "CHEMBL1"

    run = m.DiscoveryRun(id="run-x", target_id="EGFR", num_molecules=1, status="completed",
                         models={"dti": {"model_name": "TestModel"}})
    comp, _ = registry.register_compound(db, "CCCCCCCCN", origin=m.ORIGIN_GENERATED, source_db="elysium_generator")
    kg_sync.sync_run(db, arango, run, [{"index": 0, "compound_id": comp.id, "smiles": comp.canonical_smiles,
                                        "kd_nm": 12.0, "pkd": 7.9, "score": 0.79, "similar_drug": "Ibuprofen",
                                        "tanimoto_fp": 0.2, "semantic": None}])
    pred = list(arango.collection("binds").find({"evidence_type": "computational_prediction"}))
    assert len(pred) == 1 and pred[0]["_from"] == "molecules/run-x_0" and pred[0]["predicted_kd_nm"] == 12.0
    assert pred[0]["units"] == "nM" and pred[0]["model"] == "TestModel" and "best_value_nm" not in pred[0]
    assert arango.collection("binds").count() == 2


def test_graph_traversal_returns_experimental_evidence(arango, db):
    from app.services import kg_sync
    gef = db.query(m.Compound).filter_by(name="Gefitinib").one()
    db.add(m.Bioactivity(compound_id=gef.id, target_symbol="EGFR", uniprot_id="P00533", source_db="bindingdb",
                         external_id="b1", standard_type="Ki", relation="=", value_nm=0.4, pvalue=9.4,
                         evidence_type="experimental"))
    db.commit()
    kg_sync.sync_target(arango, "EGFR", with_pathways=False)
    kg_sync.sync_experimental(db, arango, "EGFR")
    rows = list(arango.aql.execute(
        "FOR v, e IN 1..1 INBOUND 'targets/EGFR' GRAPH 'elysium_graph' RETURN {v: v._id, ev: e.evidence_type}"))
    assert {"v": "compounds/" + gef.inchikey, "ev": "experimental"} in rows


def test_disabled_flag_prevents_connection(monkeypatch):
    monkeypatch.setenv("ELYSIUM_DISABLE_ARANGO", "1")
    from app.services import kg_sync
    with pytest.raises(kg_sync.KGDisabled):
        kg_sync.get_arango()
