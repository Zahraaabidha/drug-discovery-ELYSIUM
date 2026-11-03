"""DTI benchmark: DeepPurpose (members + the production ensemble) vs. baselines on the prepared BindingDB data.

Everything is evaluated on identical test compounds with identical bootstrap resamples. Nothing here changes the
production scoring method, stored predictions or discovery history; DeepPurpose is used exactly as shipped
(pretrained, not retrained). Results and predictions are written next to the prepared dataset (outside the repo)
and a summary report row is stored in `evaluation_reports` (kind = "dti_benchmark").
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import logging
import os
import platform
import shutil
import tempfile
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Callable, Dict, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd
from rdkit import DataStructs
from rdkit.Chem import Descriptors, rdMolDescriptors
from scipy.stats import ks_2samp, spearmanr
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression, RidgeCV
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from ..services import chem
from ..services.targets import resolve_target
from . import metrics as M

log = logging.getLogger(__name__)

MEMBERS = ["MPNN_CNN", "CNN_CNN", "Morgan_CNN", "Morgan_AAC", "Daylight_AAC"]
BASELINES = ["mean_baseline", "mw_linear", "heavy_atoms_linear", "physchem_ridge", "tanimoto_knn5",
             "ridge_morgan_counts", "rf_morgan_counts"]
DP_PRODUCTION = "dp_ensemble_production"          # arithmetic mean of Kd (nM) - what the application does
DP_LOGSPACE = "dp_ensemble_logspace_variant"      # mean of pKd - a LABELLED VARIANT, not used in production
TEST_SETS = {"test_primary": ("test_primary", "test_strict"), "test_strict": ("test_strict",),
             "test_possible_overlap": ("test_possible_overlap",)}


@dataclass
class BenchConfig:
    derived_dir: str = r"C:\ResearchDatasets\BindingDB\derived"
    primary_targets: Tuple[str, ...] = ("DRD2", "CDK2", "VEGFR2", "ESR1")
    exploratory_targets: Tuple[str, ...] = ("EGFR", "ABL1")
    min_train: int = 200
    min_test: int = 100
    bootstrap: int = 1000
    partial_bootstrap: int = 300
    seed: int = 20261103
    knn_k: int = 5
    rf_trees: int = 300
    include_scaffold_split: bool = True
    dp_batch: int = 1000
    ic50_targets: Optional[Tuple[str, ...]] = None     # default: every target eligible for IC50 in the manifest


# ── features ──────────────────────────────────────────────────────────────
class Features:
    """Per-SMILES feature cache: Morgan bit vector + hashed counts + physicochemical descriptors."""

    def __init__(self) -> None:
        self._cache: Dict[str, tuple] = {}

    def get(self, smiles: str):
        if smiles not in self._cache:
            mol = chem.parse(smiles)
            bv = rdMolDescriptors.GetMorganFingerprintAsBitVect(mol, chem.FP_RADIUS, nBits=chem.FP_BITS)
            cnt = np.zeros(chem.FP_BITS, dtype=np.float32)
            for k, c in rdMolDescriptors.GetHashedMorganFingerprint(mol, chem.FP_RADIUS, nBits=chem.FP_BITS).GetNonzeroElements().items():
                cnt[k] = c
            pc = chem.physchem(smiles)
            desc = np.array([pc.mol_weight, pc.logp, pc.tpsa, pc.hbd, pc.hba, pc.rotatable_bonds, pc.heavy_atoms, pc.ring_count,
                             rdMolDescriptors.CalcNumAromaticRings(mol), rdMolDescriptors.CalcFractionCSP3(mol),
                             rdMolDescriptors.CalcNumHeteroatoms(mol)], dtype=np.float64)
            self._cache[smiles] = (bv, cnt, desc)
        return self._cache[smiles]

    def matrix(self, smiles: Sequence[str], which: int) -> np.ndarray:
        return np.vstack([self.get(s)[which] for s in smiles])

    def bitvects(self, smiles: Sequence[str]):
        return [self.get(s)[0] for s in smiles]


# ── baselines ─────────────────────────────────────────────────────────────
def baseline_predictions(train: pd.DataFrame, test: pd.DataFrame, feats: Features, cfg: BenchConfig) -> Dict[str, np.ndarray]:
    ytr = train["pvalue"].to_numpy(float)
    out: Dict[str, np.ndarray] = {}
    out["mean_baseline"] = np.full(len(test), ytr.mean())
    out["mw_linear"] = LinearRegression().fit(train[["mol_weight"]], ytr).predict(test[["mol_weight"]])
    out["heavy_atoms_linear"] = LinearRegression().fit(train[["heavy_atoms"]], ytr).predict(test[["heavy_atoms"]])
    Dtr, Dte = feats.matrix(train["smiles_std"], 2), feats.matrix(test["smiles_std"], 2)
    out["physchem_ridge"] = make_pipeline(StandardScaler(), RidgeCV(alphas=np.logspace(-2, 3, 12))).fit(Dtr, ytr).predict(Dte)
    Ctr, Cte = feats.matrix(train["smiles_std"], 1), feats.matrix(test["smiles_std"], 1)
    out["ridge_morgan_counts"] = make_pipeline(StandardScaler(with_mean=False), RidgeCV(alphas=np.logspace(0, 4, 9))).fit(Ctr, ytr).predict(Cte)
    out["rf_morgan_counts"] = RandomForestRegressor(cfg.rf_trees, random_state=cfg.seed, n_jobs=-1).fit(Ctr, ytr).predict(Cte)
    fp_tr = feats.bitvects(train["smiles_std"])
    knn = np.zeros(len(test))
    for j, fp in enumerate(feats.bitvects(test["smiles_std"])):
        sims = np.asarray(DataStructs.BulkTanimotoSimilarity(fp, fp_tr))
        top = np.argsort(sims)[-cfg.knn_k:]
        knn[j] = np.average(ytr[top], weights=sims[top] + 1e-6)
    out["tanimoto_knn5"] = knn
    return out


# ── DeepPurpose ───────────────────────────────────────────────────────────
# False reproduces the frozen run (stock, batch-dependent MPNN_CNN). True evaluates what production now runs
# (app.services.mpnn_fix bond-offset correction). Process-global: it cannot be switched back inside a process.
CORRECTED_MPNN = False


def deeppurpose_members(smiles: Sequence[str], sequence: str, batch: int, members: Optional[Sequence[str]] = None) -> Dict[str, np.ndarray]:
    """Raw pretrained member outputs (pKd scale) for each ensemble member. Uses the production model files."""
    from DeepPurpose import DTI as models
    from ..services.dti_deeppurpose import PRETRAINED_DIR
    if CORRECTED_MPNN:
        from ..services import mpnn_fix
        mpnn_fix.ensure_corrected()
    out: Dict[str, np.ndarray] = {}
    tmp = tempfile.mkdtemp(prefix="elysium_bm_")
    try:
        for nm in (members or MEMBERS):
            model = models.model_pretrained(str(PRETRAINED_DIR / f"model_{nm}"))
            vals: List[float] = []
            for i in range(0, len(smiles), batch):
                chunk = list(smiles[i:i + batch])
                res = models.virtual_screening(chunk, [sequence] * len(chunk), model, [f"d{j}" for j in range(len(chunk))],
                                               ["T"] * len(chunk), convert_y=False, result_folder=tmp + os.sep, verbose=False)
                vals.extend(float(v) for v in np.asarray(res, float).reshape(-1))
            if len(vals) != len(smiles) or not np.all(np.isfinite(vals)):
                raise RuntimeError(f"DeepPurpose member {nm} returned {len(vals)} finite-checked values for {len(smiles)} molecules")
            out[nm] = np.asarray(vals)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return out


def deeppurpose_members_subset(smiles: Sequence[str], sequence: str, batch: int, members: Sequence[str]) -> Dict[str, np.ndarray]:
    return deeppurpose_members(smiles, sequence, batch, members)


def ensembles_from_members(member_pkd: Dict[str, np.ndarray]) -> Dict[str, np.ndarray]:
    """production: pKd = 9 - log10(mean of member Kd in nM)  (identical to services.dti_deeppurpose);
    variant: plain mean of member pKd (NOT used in production)."""
    P = np.vstack([member_pkd[m] for m in MEMBERS])
    kd_mean = np.mean(10.0 ** (9.0 - P), axis=0)
    return {DP_PRODUCTION: 9.0 - np.log10(np.maximum(kd_mean, 1e-6)), DP_LOGSPACE: P.mean(axis=0)}


# ── analyses ──────────────────────────────────────────────────────────────
def distribution_shift(train: pd.DataFrame, test: pd.DataFrame, feats: Features) -> Dict:
    def ks(a, b):
        r = ks_2samp(a, b)
        return {"ks_statistic": float(r.statistic), "ks_p": float(r.pvalue)}
    fp_tr = feats.bitvects(train["smiles_std"])
    nn = np.array([max(DataStructs.BulkTanimotoSimilarity(fp, fp_tr)) for fp in feats.bitvects(test["smiles_std"])])
    scaf_tr = set(train["scaffold"].fillna(""))
    return {
        "pvalue": {"train_mean": float(train.pvalue.mean()), "train_sd": float(train.pvalue.std()),
                   "test_mean": float(test.pvalue.mean()), "test_sd": float(test.pvalue.std()), **ks(train.pvalue, test.pvalue)},
        "mol_weight": {"train_median": float(train.mol_weight.median()), "test_median": float(test.mol_weight.median()),
                       **ks(train.mol_weight, test.mol_weight)},
        "heavy_atoms": {"train_median": float(train.heavy_atoms.median()), "test_median": float(test.heavy_atoms.median())},
        "nearest_train_tanimoto": {"median": float(np.median(nn)), "p10": float(np.quantile(nn, .1)), "p90": float(np.quantile(nn, .9)),
                                   "fraction_ge_0.7": float((nn >= 0.7).mean()), "fraction_ge_0.5": float((nn >= 0.5).mean())},
        "test_scaffolds_seen_in_train": float(np.mean([s in scaf_tr for s in test["scaffold"].fillna("")])),
        "spearman_mw_vs_pvalue": {"train": float(spearmanr(train.mol_weight, train.pvalue).statistic),
                                  "test": float(spearmanr(test.mol_weight, test.pvalue).statistic)},
    }


def replicate_noise(records: pd.DataFrame, bench: str, target: str, window: str) -> Dict:
    """Within-compound disagreement between repeated measurements (one value per distinct publication) and the
    resulting upper bound on achievable correlation (reliability of the aggregated label)."""
    r = records[(records.bench == bench) & (records.target == target) & (records.window == window)].copy()
    pub = r["pmid"].astype(str).where(r["pmid"].notna(), r["doi"].astype(str).where(r["doi"].notna(), r["patent"].astype(str).where(
        r["patent"].notna(), "row:" + r["rid"].astype(str))))
    r["pub"] = pub
    per_pub = r.groupby(["inchikey", "pub"], as_index=False)["pvalue"].mean()      # one value per publication
    pubs = per_pub.groupby("inchikey")["pvalue"]
    stats = pubs.agg(["count", "var", "mean"]).reset_index()
    labels = pubs.median()
    total_var = float(labels.var()) if len(labels) > 1 else float("nan")
    rep = stats[stats["count"] > 1]
    if len(rep) < 10 or not np.isfinite(total_var):
        return {"compounds_with_replicates": int(len(rep)), "note": "too few replicated compounds to estimate noise"}
    within_var = float(np.average(rep["var"].fillna(0), weights=rep["count"] - 1))
    n_i = stats["count"].to_numpy(float)
    label_noise_var = float(np.mean(within_var / n_i))
    reliability = max(0.0, 1.0 - label_noise_var / total_var)
    return {
        "compounds": int(len(stats)), "compounds_with_replicates": int(len(rep)),
        "median_within_compound_sd": float(np.median(np.sqrt(rep["var"].fillna(0)))),
        "pooled_within_compound_sd": float(np.sqrt(within_var)), "label_variance": total_var,
        "estimated_label_noise_variance": label_noise_var, "reliability": reliability,
        "max_achievable_pearson_r": float(np.sqrt(reliability)),
        "caveat": "replicates are a non-random subset (often the best-studied compounds); measurements come from different assays/labs",
    }


def mw_analysis(y: np.ndarray, preds: Dict[str, np.ndarray], mw: np.ndarray, cfg: BenchConfig, seed: int, with_ci: bool) -> Dict:
    out: Dict = {"spearman_mw_vs_measured": float(spearmanr(mw, y).statistic), "models": {}, "bands": []}
    for name, p in preds.items():
        rho = float("nan") if np.ptp(p) == 0 else float(spearmanr(mw, p).statistic)
        entry = {"spearman_prediction_vs_mw": rho}
        if np.ptp(p) > 0:
            if with_ci:
                pt, ci = M.partial_spearman_ci(y, p, mw, cfg.partial_bootstrap, seed)
            else:
                pt, ci = M.partial_spearman(y, p, mw), [float("nan")] * 2
            entry["partial_spearman_given_mw"], entry["partial_spearman_given_mw_ci"] = pt, ci
        out["models"][name] = entry
    for lo, hi in M.mw_bands(mw, 3):
        sel = (mw > lo) & (mw <= hi)
        band = {"mw_range": [None if np.isinf(lo) else round(lo, 1), None if np.isinf(hi) else round(hi, 1)], "n": int(sel.sum()), "models": {}}
        if sel.sum() >= 15:
            ev = M.evaluate_models(y[sel], {k: v[sel] for k, v in preds.items()}, 300, seed)
            band["models"] = {k: {"spearman": v["spearman"], "spearman_ci": v["spearman_ci"], "rmse": v["rmse"]} for k, v in ev["models"].items()}
        out["bands"].append(band)
    return out


# ── orchestration ─────────────────────────────────────────────────────────
def _round(o):
    if isinstance(o, dict):
        return {k: _round(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_round(v) for v in o]
    if isinstance(o, (float, np.floating)):
        return None if not np.isfinite(o) else round(float(o), 4)
    if isinstance(o, np.integer):
        return int(o)
    return o


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 24), b""):
            h.update(b)
    return h.hexdigest()


def build_sets(groups: pd.DataFrame, bench: str, tgt: str, cfg: BenchConfig):
    """Training frames and evaluation sets for one benchmark/target (shared by the run and the follow-up analyses)."""
    gb = groups[(groups.bench == bench) & (groups.sym == tgt)]
    train_t = gb[gb.temporal_role == "train"].reset_index(drop=True)
    tests = {name: gb[gb.temporal_role.isin(roles)].reset_index(drop=True) for name, roles in TEST_SETS.items()}
    scaf_train = gb[(gb.window == "pre") & (gb.scaffold_split == "train")].reset_index(drop=True)
    scaf_test = gb[(gb.window == "pre") & (gb.scaffold_split == "test")].reset_index(drop=True)
    eval_sets = {k: v for k, v in tests.items() if len(v)}
    sets_train = {k: train_t for k in eval_sets}
    if cfg.include_scaffold_split and len(scaf_test) and bench == "KiKd":
        eval_sets["scaffold_test"], sets_train["scaffold_test"] = scaf_test, scaf_train
    return train_t, scaf_train, scaf_test, eval_sets, sets_train


def canonical_batch(eval_sets: Dict[str, pd.DataFrame]) -> List[str]:
    """The exact ordered compound list that was handed to DeepPurpose for one benchmark/target."""
    return sorted({s for df in eval_sets.values() for s in df["smiles_std"]})


def run(cfg: BenchConfig, dp_predict: Callable = deeppurpose_members, out_root: Optional[Path] = None,
        store_db: bool = True, targets_override: Optional[Dict[str, List[str]]] = None) -> Dict:
    t_start = time.time()
    d = Path(cfg.derived_dir)
    manifest = json.loads((d / "manifest.json").read_text(encoding="utf-8"))
    groups = pd.read_csv(d / "groups.csv.gz", low_memory=False)
    records = pd.read_csv(d / "records.csv.gz", low_memory=False)
    feats = Features()

    plan: Dict[str, List[Tuple[str, str]]] = {"KiKd": [], "IC50": []}
    for bench in ("KiKd", "IC50"):
        summ = manifest["summary"][bench]
        for tgt in sorted(summ):
            v = summ[tgt]
            if bench == "KiKd":
                if tgt in cfg.primary_targets:
                    tier = "primary"
                elif tgt in cfg.exploratory_targets:
                    tier = "exploratory_underpowered"
                else:
                    continue
            else:
                wanted = cfg.ic50_targets if cfg.ic50_targets is not None else tuple(k for k, x in summ.items() if x["eligible_temporal"])
                if tgt not in wanted:
                    continue
                tier = "secondary_ic50"
            plan[bench].append((tgt, tier))
    if targets_override:
        plan = {b: [(t, tier) for t, tier in lst if t in targets_override.get(b, [t])] for b, lst in plan.items()}

    run_id = "dti-" + dt.datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    out_dir = (out_root or d / "benchmark_runs") / run_id
    out_dir.mkdir(parents=True, exist_ok=True)

    dp_cache: Dict[Tuple[str, str], Dict[str, float]] = {}
    pred_rows: List[pd.DataFrame] = []
    results: Dict = {"KiKd": {}, "IC50": {}}
    equivalence: Dict = {}

    for bench, lst in plan.items():
        for tgt, tier in lst:
            tinfo = resolve_target(tgt)
            train_t, scaf_train, scaf_test, eval_sets, sets_train = build_sets(groups, bench, tgt, cfg)

            # DeepPurpose predictions once per unique test compound
            need = [s for s in canonical_batch(eval_sets) if (tgt, s) not in dp_cache]
            if need:
                log.info("%s/%s: DeepPurpose on %d compounds", bench, tgt, len(need))
                t0 = time.time()
                mem = dp_predict(need, tinfo.sequence, cfg.dp_batch)
                ens = ensembles_from_members(mem)
                for i, s in enumerate(need):
                    dp_cache[(tgt, s)] = {**{f"dp_{m}": float(mem[m][i]) for m in MEMBERS}, **{k: float(v[i]) for k, v in ens.items()}}
                log.info("   done in %.0fs", time.time() - t0)

            entry = {"tier": tier, "eligibility": manifest["summary"][bench][tgt],
                     "n": {"train": int(len(train_t)), **{k: int(len(v)) for k, v in eval_sets.items()}},
                     "distribution_shift": {}, "noise": {}, "test_sets": {}}
            if len(eval_sets.get("test_primary", [])) > 5:
                entry["distribution_shift"]["temporal_train_vs_test_primary"] = distribution_shift(train_t, eval_sets["test_primary"], feats)
            if "scaffold_test" in eval_sets:
                entry["distribution_shift"]["scaffold_train_vs_test"] = distribution_shift(scaf_train, scaf_test, feats)
            entry["noise"] = {"pre_cutoff_labels": replicate_noise(records, bench, tgt, "pre"),
                              "post_cutoff_labels": replicate_noise(records, bench, tgt, "post")}

            # baselines are fitted ONCE per training frame and predict the union of its test compounds
            base_cache: Dict[str, Tuple[Dict[str, np.ndarray], Dict[str, int]]] = {}
            for fam, trf in (("temporal", train_t), ("scaffold", scaf_train)):
                members = [df for k, df in eval_sets.items() if sets_train[k] is trf]
                if not members:
                    continue
                union = pd.concat(members).drop_duplicates("ik_std").reset_index(drop=True)
                base_cache[fam] = (baseline_predictions(trf, union, feats, cfg), {ik: i for i, ik in enumerate(union["ik_std"])})

            for set_name, test_df in eval_sets.items():
                if len(test_df) < 10:
                    continue
                tr = sets_train[set_name]
                bp, pos = base_cache["scaffold" if set_name == "scaffold_test" else "temporal"]
                rows_idx = [pos[ik] for ik in test_df["ik_std"]]
                preds = {k: v[rows_idx] for k, v in bp.items()}
                for k in [f"dp_{m}" for m in MEMBERS] + [DP_PRODUCTION, DP_LOGSPACE]:
                    preds[k] = np.array([dp_cache[(tgt, s)][k] for s in test_df["smiles_std"]])
                y = test_df["pvalue"].to_numpy(float)
                ev = M.evaluate_models(y, preds, cfg.bootstrap, cfg.seed)
                paired = {}
                for ref in [DP_LOGSPACE, *[f"dp_{m}" for m in MEMBERS], *BASELINES]:
                    paired[ref] = {m: M.paired_difference(ev["_boot"], DP_PRODUCTION, ref, m) for m in ("spearman", "rmse")}
                set_entry = {"n": int(len(test_df)), "train_n": int(len(tr)), "metrics": ev["models"],
                             "paired_dp_ensemble_production_minus": paired,
                             "mw_analysis": mw_analysis(y, preds, test_df["mol_weight"].to_numpy(float), cfg, cfg.seed,
                                                        with_ci=set_name == "test_primary")}
                entry["test_sets"][set_name] = set_entry
                for name, p in preds.items():
                    pred_rows.append(pd.DataFrame({"bench": bench, "target": tgt, "test_set": set_name, "inchikey": test_df["ik_std"],
                                                   "model": name, "pred_pvalue": p, "measured_pvalue": y,
                                                   "mol_weight": test_df["mol_weight"]}))
            results[bench][tgt] = entry
            log.info("%s/%s evaluated (%d test sets, %.0fs elapsed)", bench, tgt, len(entry["test_sets"]), time.time() - t_start)
            if not equivalence and len(eval_sets.get("test_primary", [])):
                equivalence = production_equivalence_check(tgt, eval_sets["test_primary"], dp_cache)

    preds_df = pd.concat(pred_rows, ignore_index=True)
    pred_path = out_dir / "predictions.csv.gz"
    preds_df.to_csv(pred_path, index=False, compression="gzip")

    versions = {"python": platform.python_version(), "numpy": np.__version__, "pandas": pd.__version__}
    try:
        import sklearn, scipy
        from rdkit import rdBase
        from importlib.metadata import version
        versions.update(sklearn=sklearn.__version__, scipy=scipy.__version__, rdkit=rdBase.rdkitVersion, deeppurpose=version("DeepPurpose"))
    except Exception:  # pragma: no cover
        pass
    from ..services.dti_deeppurpose import DeepPurposeScreeningModel
    code_hash = hashlib.sha256(Path(__file__).read_bytes() + Path(M.__file__).read_bytes()).hexdigest()
    payload = {
        "run_id": run_id, "created_utc": dt.datetime.utcnow().isoformat(timespec="seconds"),
        "config": asdict(cfg), "dataset": {"manifest_sha256_of_source": manifest["source"]["sha256"], "source_bytes": manifest["source"]["bytes"],
                                           "prep_config": manifest["config"], "prep_created_utc": manifest["created_utc"],
                                           "role_definitions": manifest.get("role_definitions"), "assumptions": manifest.get("assumptions")},
        "dataset_files_sha256": {n: file_sha256(d / n) for n in ("groups.csv.gz", "records.csv.gz", "manifest.json")},
        "models": {"deeppurpose": DeepPurposeScreeningModel().model_info(), "baselines": BASELINES,
                   "variant_note": f"{DP_LOGSPACE} averages members in pKd space; it is a labelled variant and is NOT the production method"},
        "software_versions": versions, "code_sha256": code_hash, "production_equivalence_check": equivalence,
        "results": results, "runtime_seconds": round(time.time() - t_start, 1),
        "artifacts": {"predictions": str(pred_path), "predictions_sha256": file_sha256(pred_path)},
    }
    payload = _round(payload)
    (out_dir / "results.json").write_text(json.dumps(payload, indent=1), encoding="utf-8")
    if store_db:
        store_report(payload, out_dir)
    return payload


def production_equivalence_check(target: str, test_df: pd.DataFrame, dp_cache, n: int = 12) -> Dict:
    """Proves the benchmark evaluates the SAME method the application uses: compare against the production class."""
    from ..services.dti_deeppurpose import DeepPurposeScreeningModel
    smiles = list(test_df["smiles_std"].head(n))
    prod = DeepPurposeScreeningModel().predict(smiles, resolve_target(target).sequence, target)
    mine = np.array([dp_cache[(target, s)][DP_PRODUCTION] for s in smiles])
    prod_pkd = np.array([p.pkd for p in prod])
    return {"target": target, "n": len(smiles), "max_abs_difference_pkd": float(np.max(np.abs(prod_pkd - mine))),
            "identical_within_1e-5": bool(np.max(np.abs(prod_pkd - mine)) < 1e-5)}


LIMITATIONS = (
    "Overlap with DeepPurpose's pretrained weights is unverified: the package does not record its training data. 'test_primary'/'test_strict' "
    "mean no evidence of overlap (exact structure not recorded in BindingDB before 2021-05-31), not proof of being unseen. "
    "Ki/Kd and IC50 measurements come from different assays and labs; DeepPurpose predicts Kd, so IC50 comparisons are indirect. "
    "About 42% of records are from patents and about half pass through BindingDB's ChEMBL imports. Baselines are trained on pre-cutoff "
    "target-specific data while DeepPurpose is zero-shot per target; this is a comparison of practical methods, not of architectures. "
    "Test sets are later publications and differ in potency and size from the training data (see distribution_shift). "
    "Bootstrap CIs resample compounds and ignore assay/series clustering, so they are optimistic. Paired verdicts are exploratory: many "
    "comparisons were made without multiplicity correction."
)


def store_report(payload: Dict, out_dir: Path) -> int:
    from ..db import SessionLocal
    from .. import models as m
    summary = {}
    for bench, tg in payload["results"].items():
        for t, e in tg.items():
            tp = e["test_sets"].get("test_primary")
            if tp:
                summary[f"{bench}/{t}"] = {"n_test": tp["n"], "tier": e["tier"],
                                           "spearman": {k: v["spearman"] for k, v in tp["metrics"].items()},
                                           "rmse": {k: v["rmse"] for k, v in tp["metrics"].items()}}
    with SessionLocal() as db:
        rep = m.EvaluationReport(
            kind="dti_benchmark",
            parameters={"run_id": payload["run_id"], "config": payload["config"], "models": payload["models"],
                        "software_versions": payload["software_versions"], "code_sha256": payload["code_sha256"],
                        "results_file": str(out_dir / "results.json"), "predictions": payload["artifacts"]},
            dataset={"source_sha256": payload["dataset"]["manifest_sha256_of_source"], "files_sha256": payload["dataset_files_sha256"],
                     "prep_config": payload["dataset"]["prep_config"]},
            metrics={"summary_test_primary": summary, "production_equivalence_check": payload["production_equivalence_check"]},
            limitations=LIMITATIONS)
        db.add(rep)
        db.commit()
        return rep.id


def main(argv=None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--derived", default=BenchConfig.derived_dir)
    ap.add_argument("--bootstrap", type=int, default=BenchConfig.bootstrap)
    ap.add_argument("--no-db", action="store_true")
    a = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    cfg = BenchConfig(derived_dir=a.derived, bootstrap=a.bootstrap)
    p = run(cfg, store_db=not a.no_db)
    print(json.dumps({"run_id": p["run_id"], "runtime_seconds": p["runtime_seconds"], "equivalence": p["production_equivalence_check"]}, indent=1))


if __name__ == "__main__":
    main()
