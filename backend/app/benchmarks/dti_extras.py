"""Follow-up analyses on a finished DTI benchmark run.

Motivation: the MPNN_CNN member of DeepPurpose's pretrained ensemble was found to return different values for the
same molecule depending on which other molecules are scored in the same call and in which order (the other four
members are invariant). This module quantifies that, evaluates labelled ensemble variants WITHOUT the MPNN member,
and verifies the benchmark against the production method on an identical ordered batch. The production scoring
method itself is not modified.
"""
from __future__ import annotations

import argparse
import json
import logging
import time
from pathlib import Path
from typing import Dict, List

import numpy as np
import pandas as pd

from . import dti_benchmark as B
from . import metrics as M
from ..services.targets import resolve_target

log = logging.getLogger(__name__)
NO_MPNN_PROD = "dp_ensemble_no_mpnn_kd_mean_variant"
NO_MPNN_LOG = "dp_ensemble_no_mpnn_logspace_variant"
INVARIANT = [m for m in B.MEMBERS if m != "MPNN_CNN"]


def _no_mpnn(members: Dict[str, np.ndarray]) -> Dict[str, np.ndarray]:
    P = np.vstack([members[m] for m in INVARIANT])
    return {NO_MPNN_PROD: 9.0 - np.log10(np.maximum(np.mean(10.0 ** (9.0 - P), axis=0), 1e-6)), NO_MPNN_LOG: P.mean(axis=0)}


def variants_without_mpnn(run_dir: Path, cfg: B.BenchConfig) -> Dict:
    preds = pd.read_csv(run_dir / "predictions.csv.gz")
    out: Dict = {}
    for (bench, tgt, tset), g in preds.groupby(["bench", "target", "test_set"], sort=False):
        wide = g.pivot(index="inchikey", columns="model", values="pred_pvalue")
        order = g[g.model == B.DP_PRODUCTION]["inchikey"].tolist()           # original compound order
        wide = wide.loc[order]
        y = g[g.model == B.DP_PRODUCTION].set_index("inchikey").loc[order, "measured_pvalue"].to_numpy(float)
        members = {m: wide[f"dp_{m}"].to_numpy(float) for m in B.MEMBERS}
        cols = {k: wide[k].to_numpy(float) for k in B.BASELINES + [f"dp_{m}" for m in B.MEMBERS] + [B.DP_PRODUCTION, B.DP_LOGSPACE]}
        cols.update(_no_mpnn(members))
        ev = M.evaluate_models(y, cols, cfg.bootstrap, cfg.seed)
        keep = [B.DP_PRODUCTION, B.DP_LOGSPACE, NO_MPNN_PROD, NO_MPNN_LOG, "dp_MPNN_CNN", "mw_linear", "rf_morgan_counts", "tanimoto_knn5"]
        paired = {}
        for v in (NO_MPNN_PROD, NO_MPNN_LOG):
            paired[v] = {ref: {m: M.paired_difference(ev["_boot"], v, ref, m) for m in ("spearman", "rmse")}
                         for ref in (B.DP_PRODUCTION, "mw_linear", "rf_morgan_counts", "tanimoto_knn5")}
        out.setdefault(bench, {}).setdefault(tgt, {})[tset] = {"n": int(len(y)), "metrics": {k: ev["models"][k] for k in keep},
                                                               "paired_variants_minus": paired}
    return out


def order_sensitivity(run_dir: Path, cfg: B.BenchConfig, groups: pd.DataFrame, repeats: int = 5) -> Dict:
    """Re-score the test_primary compounds with the MPNN member in `repeats` random orders."""
    from DeepPurpose import DTI as models  # noqa: F401  (imported lazily inside deeppurpose_members)
    preds = pd.read_csv(run_dir / "predictions.csv.gz")
    out: Dict = {}
    rng = np.random.default_rng(cfg.seed + 1)
    for (bench, tgt), g in preds[preds.test_set == "test_primary"].groupby(["bench", "target"]):
        tinfo = resolve_target(tgt)
        sub = g[g.model == B.DP_PRODUCTION][["inchikey", "measured_pvalue"]].reset_index(drop=True)
        ik2smi = groups[(groups.bench == bench) & (groups.sym == tgt)].drop_duplicates("ik_std").set_index("ik_std")["smiles_std"]
        smiles = [ik2smi[ik] for ik in sub["inchikey"]]
        y = sub["measured_pvalue"].to_numpy(float)
        wide = g.pivot(index="inchikey", columns="model", values="pred_pvalue").loc[sub["inchikey"]]
        fixed = {m: wide[f"dp_{m}"].to_numpy(float) for m in INVARIANT}
        canonical = {"MPNN_CNN": wide["dp_MPNN_CNN"].to_numpy(float)}
        t0 = time.time()
        mpnn_runs, ens_runs = [], []
        for _ in range(repeats):
            perm = rng.permutation(len(smiles))
            res = B.deeppurpose_members_subset([smiles[i] for i in perm], tinfo.sequence, cfg.dp_batch, ["MPNN_CNN"])["MPNN_CNN"]
            back = np.empty(len(smiles))
            back[perm] = res
            mpnn_runs.append(back)
            ens_runs.append(B.ensembles_from_members({**fixed, "MPNN_CNN": back})[B.DP_PRODUCTION])
        M_arr, E_arr = np.vstack(mpnn_runs), np.vstack(ens_runs)

        def summ(arrs: np.ndarray, canon: np.ndarray) -> Dict:
            sp = [M.point_metrics(y, a)["spearman"] for a in arrs]
            rm = [M.point_metrics(y, a)["rmse"] for a in arrs]
            return {"spearman_by_order": sp, "spearman_mean": float(np.mean(sp)), "spearman_sd": float(np.std(sp)),
                    "spearman_min": float(np.min(sp)), "spearman_max": float(np.max(sp)),
                    "rmse_mean": float(np.mean(rm)), "rmse_sd": float(np.std(rm)),
                    "spearman_canonical_run": M.point_metrics(y, canon)["spearman"],
                    "per_compound_sd_across_orders_median": float(np.median(arrs.std(axis=0))),
                    "per_compound_sd_across_orders_p90": float(np.quantile(arrs.std(axis=0), 0.9)),
                    "per_compound_range_across_orders_median": float(np.median(arrs.max(axis=0) - arrs.min(axis=0)))}
        out.setdefault(bench, {})[tgt] = {"n": int(len(y)), "orders": repeats, "seconds": round(time.time() - t0),
                                          "mpnn_member": summ(M_arr, canonical["MPNN_CNN"]),
                                          "production_ensemble": summ(E_arr, wide[B.DP_PRODUCTION].to_numpy(float))}
        log.info("order sensitivity %s/%s done (%.0fs)", bench, tgt, time.time() - t0)
    return out


def same_order_equivalence(run_dir: Path, groups: pd.DataFrame, cfg: B.BenchConfig) -> Dict:
    """Production class vs. the benchmark's ensemble on the SAME ordered batch (the first benchmark/target processed)."""
    from ..services.dti_deeppurpose import DeepPurposeScreeningModel
    preds = pd.read_csv(run_dir / "predictions.csv.gz")
    bench, tgt = "KiKd", "ABL1"
    _, _, _, eval_sets, _ = B.build_sets(groups, bench, tgt, cfg)
    batch = B.canonical_batch(eval_sets)
    prod = DeepPurposeScreeningModel().predict(batch, resolve_target(tgt).sequence, tgt)
    prod_pkd = pd.Series([p.pkd for p in prod], index=batch)
    ik2smi = groups[(groups.bench == bench) & (groups.sym == tgt)].drop_duplicates("ik_std").set_index("smiles_std")["ik_std"]
    stored = preds[(preds.bench == bench) & (preds.target == tgt) & (preds.model == B.DP_PRODUCTION)].drop_duplicates("inchikey").set_index("inchikey")["pred_pvalue"]
    diff = np.array([abs(prod_pkd[s] - stored[ik2smi[s]]) for s in batch if ik2smi[s] in stored.index])   # compounds that were evaluated
    return {"benchmark": bench, "target": tgt, "batch_size": len(batch), "compared": int(len(diff)), "max_abs_difference_pkd": float(diff.max()),
            "identical_within_1e-5": bool(diff.max() < 1e-5),
            "note": "identical when production scores the same compounds in the same order; see order_sensitivity for why this matters"}


def run_extras(run_dir: Path, cfg: B.BenchConfig, repeats: int = 5, store_db: bool = True) -> Dict:
    t0 = time.time()
    groups = pd.read_csv(Path(cfg.derived_dir) / "groups.csv.gz", low_memory=False)
    payload = {
        "run_id": run_dir.name, "kind": "dti_benchmark_extras",
        "same_order_equivalence": same_order_equivalence(run_dir, groups, cfg),
        "order_sensitivity": order_sensitivity(run_dir, cfg, groups, repeats),
        "variants_without_mpnn": variants_without_mpnn(run_dir, cfg),
    }
    payload["runtime_seconds"] = round(time.time() - t0, 1)
    payload = B._round(payload)
    (run_dir / "extras.json").write_text(json.dumps(payload, indent=1), encoding="utf-8")
    if store_db:
        from ..db import SessionLocal
        from .. import models as m
        with SessionLocal() as db:
            db.add(m.EvaluationReport(kind="dti_benchmark_extras", parameters={"run_id": run_dir.name, "orders": repeats, "seed": cfg.seed},
                                      dataset={"extras_file": str(run_dir / "extras.json")},
                                      metrics={"same_order_equivalence": payload["same_order_equivalence"],
                                               "order_sensitivity": {b: {t: {"mpnn_spearman_sd": v["mpnn_member"]["spearman_sd"],
                                                                             "ensemble_spearman_sd": v["production_ensemble"]["spearman_sd"],
                                                                             "ensemble_median_per_compound_sd": v["production_ensemble"]["per_compound_sd_across_orders_median"]}
                                                                         for t, v in d.items()} for b, d in payload["order_sensitivity"].items()}},
                                      limitations=B.LIMITATIONS))
            db.commit()
    return payload


def main(argv=None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", required=True, type=Path)
    ap.add_argument("--repeats", type=int, default=5)
    a = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    res = json.loads((a.run_dir / "results.json").read_text(encoding="utf-8"))
    cfg = B.BenchConfig(**{k: (tuple(v) if isinstance(v, list) else v) for k, v in res["config"].items()})
    p = run_extras(a.run_dir, cfg, a.repeats)
    print(json.dumps({"same_order_equivalence": p["same_order_equivalence"], "runtime_seconds": p["runtime_seconds"]}, indent=1))


if __name__ == "__main__":
    main()
