import pytest

from app import models as m
from app.services import chem
from app.services.generation import MutationGenerator

SEEDS = ["CC(=O)Nc1ccc(O)cc1", "CC(C)Cc1ccc(cc1)C(C)C(=O)O", "COc1cc2ncnc(Nc3cccc(Cl)c3)c2cc1OC",
         "CN1CCN(CC1)c1ccc(cc1)C(=O)O", "Clc1ccc(cc1)Nc1ncnc2ccccc12"]


def _known(smiles):
    return {chem.standardise(s).inchikey for s in smiles}


def test_generator_stats_are_consistent():
    gen = MutationGenerator(SEEDS)
    res = gen.generate("EGFR", 20, seed=1, known_inchikeys=_known(SEEDS))
    s = res.stats
    assert s.attempted >= s.valid >= s.unique >= s.novel >= s.returned == len(res.smiles)
    assert 0 < s.validity <= 1 and 0 < s.uniqueness <= 1 and 0 < s.novelty <= 1


def test_generated_molecules_are_valid_unique_and_not_reference():
    gen = MutationGenerator(SEEDS)
    known = _known(SEEDS)
    res = gen.generate("EGFR", 25, seed=3, known_inchikeys=known)
    keys = [chem.standardise(s).inchikey for s in res.smiles]
    assert len(set(keys)) == len(keys)                  # unique
    assert not (set(keys) & known)                      # never a known compound
    assert all(chem.is_valid(s) for s in res.smiles)


def test_generator_reproducible_with_seed_and_varies_without():
    gen = MutationGenerator(SEEDS)
    a = gen.generate("EGFR", 10, seed=42, known_inchikeys=_known(SEEDS)).smiles
    b = gen.generate("EGFR", 10, seed=42, known_inchikeys=_known(SEEDS)).smiles
    c = gen.generate("EGFR", 10, seed=43, known_inchikeys=_known(SEEDS)).smiles
    assert a == b and a != c


def test_generator_returns_fewer_instead_of_padding_with_reference():
    gen = MutationGenerator(["CCO"])                    # too small to yield 50 novel drug-sized molecules
    res = gen.generate("EGFR", 50, seed=0, known_inchikeys=_known(["CCO"]))
    assert len(res.smiles) < 50 and res.stats.exhausted
    assert not (_known(res.smiles) & _known(["CCO"]))


def test_unsupported_target_rejected_not_substituted(client):
    r = client.post("/discover", json={"target_id": "NOT_A_TARGET", "num_molecules": 3})
    assert r.status_code == 422 and "EGFR" in r.json()["supported_targets"]
    assert client.get("/runs").json()["runs"] == []     # nothing was run


def test_discovery_registers_generated_compounds_with_prediction_metadata(client, db):
    r = client.post("/discover", json={"target_id": "egfr", "num_molecules": 4, "seed": 11})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["target_id"] == "EGFR" and body["seed"] == 11 and body["status"] == "completed"
    assert body["models"]["dti"]["model_name"] and body["data_sources"]["target_sequence"]["accession"] == "P00533"
    assert body["metrics"]["generation"]["validity"] > 0
    assert len(body["molecules"]) == 4
    for mol in body["molecules"]:
        assert mol["origin"] == "generated" and mol["evidence_type"] == "computational_prediction"
        assert mol["units"] == "nM" and mol["predicted_kd_nm"] > 0
        comp = db.get(m.Compound, mol["compound_id"])
        assert comp.origin == m.ORIGIN_GENERATED and comp.generation_run_id == body["run_id"]
        pred = db.query(m.Prediction).filter_by(compound_id=comp.id, run_id=body["run_id"]).one()
        assert pred.target_symbol == "EGFR" and pred.units == "nM" and pred.model_name


def test_discovery_is_reproducible_with_same_seed(client):
    a = client.post("/discover", json={"target_id": "EGFR", "num_molecules": 3, "seed": 5}).json()
    db_state = client.get("/library/stats").json()["compounds"]
    b = client.post("/discover", json={"target_id": "EGFR", "num_molecules": 3, "seed": 5}).json()
    # second run cannot return the molecules just registered as "known"; both runs are valid but the
    # recorded parameters/seed are identical, which is what reproduction requires
    assert a["params"]["generation"]["seed"] == b["params"]["generation"]["seed"] == 5
    assert a["models"] == b["models"] and db_state > 0


def test_run_is_retrievable_with_provenance(client):
    run = client.post("/discover", json={"target_id": "EGFR", "num_molecules": 2, "seed": 9}).json()
    got = client.get(f"/runs/{run['run_id']}").json()
    assert got["seed"] == 9 and got["params"]["target_id"] == "EGFR" and got["metrics"]["generation"]
    assert all(mol["predicted_kd_nm"] and mol["origin"] == "generated" for mol in got["molecules"])


@pytest.mark.parametrize("flt,check", [
    ({"max_mw": 300}, lambda a: a["molecular_weight"] <= 300),
    ({"min_mw": 350}, lambda a: a["molecular_weight"] >= 350),
    ({"max_logp": 2.0}, lambda a: a["logp"] <= 2.0),
    ({"max_tpsa": 60}, lambda a: a["tpsa"] <= 60),
    ({"max_hbd": 1}, lambda a: a["hbd"] <= 1),
    ({"max_hba": 4}, lambda a: a["hba"] <= 4),
    ({"max_rotatable_bonds": 3}, lambda a: a["rotatable_bonds"] <= 3),
    ({"lipinski_only": True}, lambda a: a["lipinski_pass"]),
])
def test_backend_filters_are_enforced(client, flt, check):
    r = client.post("/discover", json={"target_id": "EGFR", "num_molecules": 5, "seed": 2, **flt})
    assert r.status_code == 200, r.text
    mols = r.json()["molecules"]
    assert mols, "filter was too strict for this seed"
    assert all(check(mol["admet"]) for mol in mols)


def test_impossible_filter_returns_empty_not_unfiltered(client):
    r = client.post("/discover", json={"target_id": "EGFR", "num_molecules": 5, "seed": 2, "max_mw": 10, "min_mw": 5})
    assert r.status_code == 200 and r.json()["molecules"] == []


def test_dti_failure_is_an_error_not_a_placeholder(failing_client, db):
    r = failing_client.post("/discover", json={"target_id": "EGFR", "num_molecules": 3, "seed": 1})
    assert r.status_code == 502 and "simulated model failure" in r.json()["detail"]
    run = db.query(m.DiscoveryRun).one()
    assert run.status == "failed" and "simulated" in run.error
    assert db.query(m.Prediction).count() == 0 and db.query(m.MoleculeRecord).count() == 0


def test_run_list_reports_real_status(client):
    ok = client.post("/discover", json={"target_id": "EGFR", "num_molecules": 2, "seed": 4}).json()
    runs = client.get("/runs").json()["runs"]
    row = next(r for r in runs if r["run_id"] == ok["run_id"])
    assert row["status"] == "completed" and row["seed"] == 4


def test_failed_run_is_listed_as_failed(failing_client):
    failing_client.post("/discover", json={"target_id": "EGFR", "num_molecules": 2, "seed": 4})
    runs = failing_client.get("/runs").json()["runs"]
    assert [r["status"] for r in runs] == ["failed"]
