"""Tests for the DTI benchmark: metric maths, paired-bootstrap verdicts, MW analysis, baselines, and an end-to-end
run on a synthetic derived dataset with an injected, clearly-labelled test double for DeepPurpose.
The synthetic compounds/labels are test fixtures only and carry no scientific meaning."""
import hashlib
import itertools
import json
import math

import numpy as np
import pandas as pd
import pytest
from scipy.stats import pearsonr, spearmanr

from app.benchmarks import metrics as M
from app.benchmarks import dti_benchmark as B
from app.services import chem


# ── metric maths ──────────────────────────────────────────────────────────
def test_point_metrics_match_scipy():
    rng = np.random.default_rng(0)
    y = rng.normal(size=200)
    p = 0.5 * y + rng.normal(size=200)
    m = M.point_metrics(y, p)
    assert m["spearman"] == pytest.approx(spearmanr(y, p).statistic, abs=1e-9)
    assert m["pearson"] == pytest.approx(pearsonr(y, p)[0], abs=1e-9)
    assert m["rmse"] == pytest.approx(math.sqrt(np.mean((p - y) ** 2)))
    assert m["mae"] == pytest.approx(np.mean(np.abs(p - y)))
    assert m["bias"] == pytest.approx(np.mean(p - y))


def test_constant_prediction_has_undefined_correlation_not_zero():
    y = np.arange(50.0)
    m = M.point_metrics(y, np.full(50, 3.0))
    assert math.isnan(m["spearman"]) and math.isnan(m["pearson"]) and math.isnan(m["enrichment_top10"])
    assert m["rmse"] > 0


def test_enrichment_perfect_random_and_inverted():
    y = np.arange(100.0)
    assert M.enrichment_top_fraction(y, y) == pytest.approx(10.0)            # perfect = 1/0.1
    assert M.enrichment_top_fraction(y, -y) == pytest.approx(0.0)
    rng = np.random.default_rng(1)
    vals = [M.enrichment_top_fraction(y, rng.permutation(y)) for _ in range(300)]
    assert np.mean(vals) == pytest.approx(1.0, abs=0.25)                     # random ~ 1


def test_vectorised_bootstrap_matches_loop_and_ci_brackets_point():
    rng = np.random.default_rng(2)
    y = rng.normal(size=120)
    p = y + rng.normal(scale=1.0, size=120)
    idx = M.bootstrap_indices(len(y), 200, np.random.default_rng(3))
    bs = M.bootstrap_metrics(y, p, idx)
    loop = [M.point_metrics(y[i], p[i]) for i in idx[:20]]
    for k in ("spearman", "pearson", "rmse", "mae"):
        assert np.allclose(bs[k][:20], [l[k] for l in loop], atol=1e-9)
    ev = M.evaluate_models(y, {"m": p}, 500, 7)
    lo, hi = ev["models"]["m"]["spearman_ci"]
    assert lo < ev["models"]["m"]["spearman"] < hi and hi - lo < 0.5


def test_bootstrap_is_reproducible_with_seed():
    y = np.random.default_rng(0).normal(size=80)
    p = y + np.random.default_rng(1).normal(size=80)
    a = M.evaluate_models(y, {"m": p}, 300, 11)["models"]["m"]["rmse_ci"]
    b = M.evaluate_models(y, {"m": p}, 300, 11)["models"]["m"]["rmse_ci"]
    assert a == b


def test_paired_verdicts_only_when_interval_excludes_zero():
    rng = np.random.default_rng(4)
    y = rng.normal(size=400)
    good = y + rng.normal(scale=0.3, size=400)
    bad = y + rng.normal(scale=2.0, size=400)
    twin = good + rng.normal(scale=0.01, size=400)
    boot = M.evaluate_models(y, {"good": good, "bad": bad, "twin": twin}, 500, 5)["_boot"]
    assert M.paired_difference(boot, "good", "bad", "spearman")["verdict"] == "better"
    assert M.paired_difference(boot, "bad", "good", "spearman")["verdict"] == "worse"
    assert M.paired_difference(boot, "good", "bad", "rmse")["verdict"] == "better"          # lower RMSE is better
    assert M.paired_difference(boot, "good", "twin", "spearman")["verdict"] == "no_significant_difference"


def test_partial_spearman_removes_mw_confounding():
    rng = np.random.default_rng(6)
    mw = rng.uniform(200, 600, 600)
    y = 0.02 * mw + rng.normal(scale=0.5, size=600)           # activity driven only by size
    size_only = mw + rng.normal(scale=5, size=600)             # a model that just predicts size
    assert spearmanr(y, size_only).statistic > 0.7
    assert abs(M.partial_spearman(y, size_only, mw)) < 0.15
    real = (y - 0.02 * mw) + rng.normal(scale=0.2, size=600)
    assert M.partial_spearman(y, real, mw) > 0.5


def test_mw_bands_cover_all_compounds():
    mw = np.random.default_rng(0).uniform(100, 700, 300)
    bands = M.mw_bands(mw, 3)
    counts = [(((mw > lo) & (mw <= hi)).sum()) for lo, hi in bands]
    assert sum(counts) == 300 and min(counts) > 80


# ── DeepPurpose ensemble arithmetic (production vs variant) ───────────────
def test_production_ensemble_formula_matches_service_conversion():
    from app.services.dti_deeppurpose import kd_to_result
    rng = np.random.default_rng(0)
    members = {m: rng.uniform(4, 9, 25) for m in B.MEMBERS}
    ens = B.ensembles_from_members(members)
    kd_mean = np.mean([10 ** (9 - members[m]) for m in B.MEMBERS], axis=0)
    prod = np.array([kd_to_result("x", k).pkd for k in kd_mean])
    assert np.allclose(ens[B.DP_PRODUCTION], prod, atol=1e-9)
    assert np.allclose(ens[B.DP_LOGSPACE], np.mean([members[m] for m in B.MEMBERS], axis=0))
    assert not np.allclose(ens[B.DP_PRODUCTION], ens[B.DP_LOGSPACE])      # they really are different methods


# ── synthetic end-to-end ──────────────────────────────────────────────────
def synthetic_derived(tmp_path, with_test_in_train=False):
    prefixes = ["", "C", "CC", "CCC", "CO", "CN", "CCl", "CF", "COC", "CCO", "CCN", "CC(C)", "CBr", "C(=O)", "CS"]
    suffixes = ["", "C", "O", "N", "F", "Cl", "CC", "CO", "CN", "C(=O)O", "C(F)(F)F", "OC", "OCC", "Br", "S"]
    smiles = []
    for pre, suf in itertools.product(prefixes, suffixes):
        smi = f"{pre}c1ccccc1{suf}"
        if chem.is_valid(smi):
            smiles.append(smi)
    seen, rows = set(), []
    for smi in smiles:
        s = chem.standardise(smi)
        if s.inchikey in seen:
            continue
        seen.add(s.inchikey)
        pc = chem.physchem(s.canonical_smiles)
        rows.append((s.inchikey, s.canonical_smiles, pc.mol_weight, pc.heavy_atoms, chem.murcko_scaffold(s.canonical_smiles) or ""))
    rng = np.random.default_rng(0)
    rows = [rows[i] for i in rng.permutation(len(rows))]
    n = len(rows)
    n_train, n_test = int(n * 0.6), int(n * 0.3)
    recs, grp = [], []
    for i, (ik, smi, mw, ha, scaf) in enumerate(rows):
        if i < n_train:
            window, role, tier = "pre", "train", "A"
        elif i < n_train + n_test:
            window, role, tier = "post", ("test_strict" if i % 2 == 0 else "test_primary"), ("E" if i % 2 == 0 else "D")
        else:
            window, role, tier = "post", "test_possible_overlap", "C"
        pv = 3 + 0.03 * mw + rng.normal(scale=0.6)
        grp.append(dict(bench="KiKd", sym="DRD2", ik_std=ik, window=window, pvalue=pv, n_records=2, n_publications=2, pvalue_min=pv - .3,
                        pvalue_max=pv + .3, pvalue_sd=.3, types="Ki", first_date="2015-01-01", last_date="2015-01-01", pubs="1;2",
                        sources="ChEMBL", smiles_std=smi, heavy_atoms=ha, mol_weight=mw, scaffold=scaf, noisy=False, tier=tier,
                        temporal_role=role, scaffold_split=("train" if i < n_train * 0.8 else "test") if window == "pre" else ""))
        for k in range(2):
            recs.append(dict(bench="KiKd", target="DRD2", inchikey=ik, window=window, pvalue=pv + (-0.3 if k else 0.3), pmid=1000 + k,
                             doi=None, patent=None, rid=f"{i}_{k}"))
    if with_test_in_train:   # inject a leak to prove the guard sees it
        leak = next(g for g in grp if g["temporal_role"] == "test_primary").copy()
        leak.update(temporal_role="train", window="pre", tier="A")
        grp.append(leak)
    d = tmp_path / "derived"
    d.mkdir()
    pd.DataFrame(grp).to_csv(d / "groups.csv.gz", index=False)
    pd.DataFrame(recs).to_csv(d / "records.csv.gz", index=False)
    elig = {"train_compounds": n_train, "eligible_temporal": True}
    (d / "manifest.json").write_text(json.dumps({"source": {"sha256": "x" * 64, "bytes": 1}, "config": {"cutoff": "2021-05-31"},
                                                 "created_utc": "t", "summary": {"KiKd": {"DRD2": elig}, "IC50": {}}}))
    return d


def fake_dp(smiles, sequence, batch):
    """TEST DOUBLE for the five pretrained members (deterministic, meaningless numbers)."""
    out = {}
    for j, m in enumerate(B.MEMBERS):
        out[m] = np.array([5 + (int(hashlib.sha256(f"{m}{s}".encode()).hexdigest()[:6], 16) % 300) / 100 for s in smiles])
    return out


@pytest.fixture()
def synthetic_run(tmp_path, monkeypatch):
    d = synthetic_derived(tmp_path)
    monkeypatch.setattr(B, "production_equivalence_check", lambda *a, **k: {"skipped": "test double in use"})
    cfg = B.BenchConfig(derived_dir=str(d), primary_targets=("DRD2",), exploratory_targets=(), bootstrap=200, partial_bootstrap=50,
                        rf_trees=30, include_scaffold_split=True)
    payload = B.run(cfg, dp_predict=fake_dp, out_root=tmp_path / "runs", store_db=False)
    return payload, tmp_path / "runs", d


def test_all_models_scored_on_identical_compounds(synthetic_run):
    payload, runs, _ = synthetic_run
    preds = pd.read_csv(next(runs.glob("*/predictions.csv.gz")))
    assert set(B.BASELINES) | {f"dp_{m}" for m in B.MEMBERS} | {B.DP_PRODUCTION, B.DP_LOGSPACE} == set(preds["model"])
    for (_, _, _), g in preds.groupby(["bench", "target", "test_set"]):
        sets = [frozenset(x["inchikey"]) for _, x in g.groupby("model")]
        assert len(set(sets)) == 1                                                # every model saw the same compounds
        assert g.groupby("model").size().nunique() == 1


def test_results_contain_required_metrics_and_cis(synthetic_run):
    payload, _, _ = synthetic_run
    ts = payload["results"]["KiKd"]["DRD2"]["test_sets"]
    assert {"test_primary", "test_strict", "test_possible_overlap", "scaffold_test"} <= set(ts)
    row = ts["test_primary"]["metrics"][B.DP_PRODUCTION]
    for k in ("spearman", "pearson", "rmse", "mae", "enrichment_top10", "bias"):
        assert k in row
    for k in ("spearman_ci", "pearson_ci", "rmse_ci", "mae_ci", "enrichment_top10_ci"):
        assert len(row[k]) == 2 and row[k][0] <= row[k][1]
    assert len(ts["test_primary"]["metrics"]) == len(B.BASELINES) + len(B.MEMBERS) + 2
    assert ts["test_primary"]["n"] > ts["test_strict"]["n"] > 0
    assert "mw_analysis" in ts["test_primary"] and len(ts["test_primary"]["mw_analysis"]["bands"]) == 3


def test_mw_baseline_recovers_synthetic_size_effect_and_beats_noise_model(synthetic_run):
    payload, _, _ = synthetic_run
    m = payload["results"]["KiKd"]["DRD2"]["test_sets"]["test_primary"]["metrics"]
    assert m["mw_linear"]["spearman"] > 0.6                       # labels were generated from MW
    assert m["mw_linear"]["spearman"] > m[B.DP_PRODUCTION]["spearman"]   # the random test double has no signal
    assert abs(m[B.DP_PRODUCTION]["spearman"]) < 0.3
    v = payload["results"]["KiKd"]["DRD2"]["test_sets"]["test_primary"]["paired_dp_ensemble_production_minus"]["mw_linear"]["spearman"]["verdict"]
    assert v in ("worse", "no_significant_difference")            # never 'better' without evidence


def test_distribution_shift_and_noise_reported(synthetic_run):
    payload, _, _ = synthetic_run
    e = payload["results"]["KiKd"]["DRD2"]
    sh = e["distribution_shift"]["temporal_train_vs_test_primary"]
    assert {"pvalue", "mol_weight", "nearest_train_tanimoto", "test_scaffolds_seen_in_train"} <= set(sh)
    assert e["noise"]["pre_cutoff_labels"]["pooled_within_compound_sd"] > 0


def test_reproducible_artifacts_and_hashes(synthetic_run):
    payload, runs, d = synthetic_run
    run_dir = next(runs.glob("*"))
    assert (run_dir / "results.json").exists() and (run_dir / "predictions.csv.gz").exists()
    assert payload["artifacts"]["predictions_sha256"] == B.file_sha256(run_dir / "predictions.csv.gz")
    assert payload["dataset_files_sha256"]["groups.csv.gz"] == B.file_sha256(d / "groups.csv.gz")
    assert payload["config"]["seed"] and payload["software_versions"]["numpy"] and payload["code_sha256"]
    again = B.run(B.BenchConfig(**{**payload["config"], "primary_targets": ("DRD2",), "exploratory_targets": ()}), dp_predict=fake_dp,
                  out_root=runs / "again", store_db=False)
    a = payload["results"]["KiKd"]["DRD2"]["test_sets"]["test_primary"]["metrics"]
    b = again["results"]["KiKd"]["DRD2"]["test_sets"]["test_primary"]["metrics"]
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)


def test_no_test_compound_in_training_data_of_synthetic_set(synthetic_run):
    _, _, d = synthetic_run
    g = pd.read_csv(d / "groups.csv.gz")
    train = set(g[g.temporal_role == "train"]["ik_std"])
    test = set(g[g.temporal_role.str.startswith("test_")]["ik_std"])
    assert not train & test


def test_report_is_stored_in_database_without_touching_other_tables(tmp_path, monkeypatch, db):
    from app import models as m
    before = (db.query(m.Prediction).count(), db.query(m.DiscoveryRun).count(), db.query(m.Compound).count())
    d = synthetic_derived(tmp_path)
    monkeypatch.setattr(B, "production_equivalence_check", lambda *a, **k: {"skipped": "test double"})
    cfg = B.BenchConfig(derived_dir=str(d), primary_targets=("DRD2",), exploratory_targets=(), bootstrap=100, partial_bootstrap=20, rf_trees=10)
    B.run(cfg, dp_predict=fake_dp, out_root=tmp_path / "runs", store_db=True)
    db.expire_all()
    rep = db.query(m.EvaluationReport).filter_by(kind="dti_benchmark").one()
    assert rep.parameters["config"]["seed"] == cfg.seed and rep.parameters["predictions"]["predictions_sha256"]
    assert "overlap" in rep.limitations.lower() and "unverified" in rep.limitations.lower()
    assert (db.query(m.Prediction).count(), db.query(m.DiscoveryRun).count(), db.query(m.Compound).count()) == before


@pytest.mark.slow
def test_benchmark_ensemble_equals_production_method_on_real_model(monkeypatch):
    monkeypatch.setattr(B, "CORRECTED_MPNN", True)       # production runs the corrected MPNN
    """The benchmark must evaluate exactly what the application runs."""
    from app.services.dti_deeppurpose import DeepPurposeScreeningModel
    from app.services.targets import resolve_target
    smiles = ["COc1cc2ncnc(Nc3ccc(F)c(Cl)c3)c2cc1OCCCN1CCOCC1", "CC(=O)Nc1ccc(O)cc1", "CCCCN", "c1ccc2[nH]ccc2c1"]
    t = resolve_target("EGFR")
    mine = B.ensembles_from_members(B.deeppurpose_members(smiles, t.sequence, 1000))[B.DP_PRODUCTION]
    prod = np.array([r.pkd for r in DeepPurposeScreeningModel().predict(smiles, t.sequence, "EGFR")])
    assert np.max(np.abs(mine - prod)) < 1e-5
