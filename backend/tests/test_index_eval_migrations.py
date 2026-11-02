import sqlite3

import pytest
from sqlalchemy import create_engine, inspect, text

from app import models as m
from app.migrate import upgrade_to_head
from app.services import chem, evaluation, scoring
from app.services.similarity_index import index
from tests.conftest import FakeDTI


def test_faiss_fingerprint_matches_exact_tanimoto_ranking(db):
    index.rebuild(db)
    assert index.size == db.query(m.Compound).count()
    for smi in ["CC(=O)Nc1ccc(O)cc1", "COc1cc2ncnc(Nc3cccc(Cl)c3)c2cc1OC"]:
        exact = index.exact_tanimoto(smi, 5)
        approx = index.search_fingerprint(smi, 5)
        assert approx[0].compound_id == exact[0].compound_id
        assert approx[0].similarity == pytest.approx(exact[0].similarity, abs=1e-6)     # Tanimoto from popcounts is exact


def test_identical_molecule_has_similarity_one(db):
    index.rebuild(db)
    top = index.search_fingerprint("CC(=O)OC1=CC=CC=C1C(=O)O", 1)[0]
    assert top.similarity == pytest.approx(1.0)


def test_similarity_evaluation_report(db):
    rep = evaluation.evaluate_similarity(db, n_queries=15, k=5, seed=1)
    assert rep.kind == "similarity" and rep.metrics["n_queries"] == 15
    assert 0.0 <= rep.metrics["faiss_vs_exact_tanimoto_recall_at_k"] <= 1.0
    assert rep.metrics["fingerprint_identity_retrieval_under_smiles_randomisation"] == pytest.approx(1.0)
    assert "approximation fidelity" in rep.limitations


def test_generation_evaluation_report(db):
    rep = evaluation.evaluate_generation(db, num_molecules=30, seed=2)
    mt = rep.metrics
    assert rep.kind == "generation" and mt["returned"] == 30 and 0 < mt["validity"] <= 1 and mt["novelty"] == 1.0
    assert mt["generated_properties"]["qed"]["n"] == 30 and "registry" in rep.limitations.lower()
    assert rep.dataset["novelty_reference"].startswith("all registry compounds")


def test_dti_evaluation_requires_real_measurements(db):
    scoring.set_scorer(FakeDTI())
    try:
        with pytest.raises(evaluation.EvaluationError, match="import experimental data"):
            evaluation.evaluate_dti(db, "EGFR")
    finally:
        scoring.set_scorer(None)


def test_dti_evaluation_metric_pipeline_with_test_fixture_measurements(db):
    """Exercises the metric computation on TEST-FIXTURE measurements (not real data) using the test double."""
    scoring.set_scorer(FakeDTI())
    try:
        comps = db.query(m.Compound).limit(25).all()
        for i, c in enumerate(comps):
            db.add(m.Bioactivity(compound_id=c.id, target_symbol="EGFR", uniprot_id="P00533", source_db="chembl",
                                 external_id=f"fx{i}", standard_type="Ki", relation="=", value_nm=10.0 + i,
                                 pvalue=8.0 - i * 0.05, evidence_type="experimental"))
        db.commit()
        rep = evaluation.evaluate_dti(db, "EGFR")
        mt = rep.metrics
        assert mt["n_compounds"] == 25 and -1 <= mt["spearman_rho"] <= 1 and mt["rmse_pkd"] >= 0
        assert "LEAKAGE" in rep.limitations.upper() and rep.dataset["model"]["model_name"] == "FakeDTI test double"
    finally:
        scoring.set_scorer(None)


def test_evaluation_endpoints(client):
    r = client.post("/evaluation/generation", json={"num_molecules": 10, "seed": 1})
    assert r.status_code == 200 and r.json()["metrics"]["returned"] == 10
    assert client.post("/evaluation/dti", json={"target": "EGFR"}).status_code == 409
    reps = client.get("/evaluation/reports", params={"kind": "generation"}).json()
    assert reps and reps[0]["kind"] == "generation" and reps[0]["limitations"]


def test_migration_fresh_database(tmp_path):
    url = f"sqlite:///{(tmp_path / 'fresh.db').as_posix()}"
    upgrade_to_head(url)
    tables = set(inspect(create_engine(url)).get_table_names())
    assert {"compounds", "compound_sources", "bioactivities", "predictions", "collections", "annotations",
            "evaluation_reports", "discovery_runs", "molecules", "alembic_version"} <= tables


def test_migration_preserves_legacy_data(tmp_path):
    path = tmp_path / "legacy.db"
    con = sqlite3.connect(path)
    con.executescript("""
        CREATE TABLE discovery_runs (id VARCHAR PRIMARY KEY, target_id VARCHAR NOT NULL, num_molecules INTEGER NOT NULL, created_at DATETIME);
        CREATE TABLE molecules (id INTEGER PRIMARY KEY AUTOINCREMENT, run_id VARCHAR NOT NULL, smiles VARCHAR NOT NULL,
            score FLOAT NOT NULL, source VARCHAR NOT NULL, notes TEXT, admet_mw FLOAT, admet_logp FLOAT, admet_hbd INTEGER,
            admet_hba INTEGER, admet_tpsa FLOAT, admet_rotatable_bonds INTEGER, admet_lipinski_pass INTEGER,
            admet_lipinski_violations INTEGER, similar_drug_fp VARCHAR, tanimoto_fp FLOAT, similar_drug_semantic VARCHAR,
            tanimoto_semantic FLOAT, scorer_used VARCHAR);
        INSERT INTO discovery_runs VALUES ('r1','EGFR',1,'2026-01-01 00:00:00');
        INSERT INTO molecules (run_id, smiles, score, source) VALUES ('r1','CCO',0.5,'old');
    """)
    con.commit()
    con.close()
    url = f"sqlite:///{path.as_posix()}"
    upgrade_to_head(url)
    upgrade_to_head(url)                                    # idempotent
    eng = create_engine(url)
    with eng.connect() as c:
        assert c.execute(text("select count(*) from discovery_runs")).scalar() == 1
        assert c.execute(text("select smiles, compound_id from molecules")).one() == ("CCO", None)
        assert c.execute(text("select status from discovery_runs")).scalar() == "legacy_unverified"
        assert c.execute(text("select version_num from alembic_version")).scalar() == "0003"
    assert "seed" in {col["name"] for col in inspect(eng).get_columns("discovery_runs")}
