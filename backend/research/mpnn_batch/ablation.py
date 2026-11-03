"""Research-only ensemble ablation on the FROZEN benchmark run (read-only on the run directory).

Ensembles compared with the production ensemble (5 stock members, Kd-mean), identical test sets, bootstrap seed and metrics:
  no_mpnn_kd_mean   4 order-invariant members, mean Kd (same aggregation as production)
  no_mpnn_pkd_mean  4 members, mean pKd
  fixed_mpnn_kd_mean  all 5 members, MPNN rescored with the bond-offset patch (research patch, not production)
Exploratory: variants were defined after the order-dependence finding, not before seeing test results of this run.
"""
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

from app.benchmarks import dti_benchmark as B
from app.benchmarks import metrics as M
from app.services.targets import resolve_target
from research.mpnn_batch.mpnn_repro import fixed_forward

INV = [m for m in B.MEMBERS if m != "MPNN_CNN"]
kd_mean = lambda P: 9.0 - np.log10(np.maximum(np.mean(10.0 ** (9.0 - P), axis=0), 1e-6))


def fixed_mpnn(preds, groups, seq_of, out_cache: Path):
    if out_cache.exists():
        return pd.read_csv(out_cache).set_index(["target", "inchikey"])["fixed_mpnn"]
    from DeepPurpose import encoders
    encoders.MPNN.forward = fixed_forward
    ik2smi = groups.drop_duplicates("ik_std").set_index("ik_std")["smiles_std"]
    rows = []
    for tgt, g in preds.groupby("target"):
        iks = sorted(g["inchikey"].unique())
        t0 = time.time()
        vals = B.deeppurpose_members([ik2smi[i] for i in iks], seq_of[tgt], 1000, ["MPNN_CNN"])["MPNN_CNN"]
        rows += [(tgt, i, float(v)) for i, v in zip(iks, vals)]
        print(tgt, len(iks), f"{time.time()-t0:.0f}s", flush=True)
    df = pd.DataFrame(rows, columns=["target", "inchikey", "fixed_mpnn"])
    df.to_csv(out_cache, index=False)
    return df.set_index(["target", "inchikey"])["fixed_mpnn"]


def main(run_dir: Path, out: Path):
    res = json.loads((run_dir / "results.json").read_text(encoding="utf-8"))
    cfg = B.BenchConfig(**{k: (tuple(v) if isinstance(v, list) else v) for k, v in res["config"].items()})
    preds = pd.read_csv(run_dir / "predictions.csv.gz")
    groups = pd.read_csv(Path(cfg.derived_dir) / "groups.csv.gz", low_memory=False)
    seq_of = {t: resolve_target(t).sequence for t in preds["target"].unique()}
    fx = fixed_mpnn(preds, groups, seq_of, out.with_name("fixed_mpnn_cache.csv"))
    report = {}
    for (bench, tgt, tset), g in preds.groupby(["bench", "target", "test_set"], sort=False):
        wide = g.pivot(index="inchikey", columns="model", values="pred_pvalue")
        order = g[g.model == B.DP_PRODUCTION]["inchikey"].tolist()
        wide = wide.loc[order]
        y = g[g.model == B.DP_PRODUCTION].set_index("inchikey").loc[order, "measured_pvalue"].to_numpy(float)
        mem = {m: wide[f"dp_{m}"].to_numpy(float) for m in B.MEMBERS}
        fmp = np.array([fx[(tgt, i)] for i in order])
        cols = {k: wide[k].to_numpy(float) for k in B.BASELINES + [B.DP_PRODUCTION]}
        cols["no_mpnn_kd_mean"] = kd_mean(np.vstack([mem[m] for m in INV]))
        cols["no_mpnn_pkd_mean"] = np.vstack([mem[m] for m in INV]).mean(axis=0)
        cols["fixed_mpnn_kd_mean"] = kd_mean(np.vstack([fmp] + [mem[m] for m in INV]))
        cols["mpnn_stock"], cols["mpnn_fixed"] = mem["MPNN_CNN"], fmp
        ev = M.evaluate_models(y, cols, cfg.bootstrap, cfg.seed)
        variants = ["no_mpnn_kd_mean", "no_mpnn_pkd_mean", "fixed_mpnn_kd_mean"]
        report.setdefault(bench, {}).setdefault(tgt, {})[tset] = {
            "n": int(len(y)),
            "metrics": {k: ev["models"][k] for k in [B.DP_PRODUCTION, *variants, "mpnn_stock", "mpnn_fixed", "mw_linear", "rf_morgan_counts", "tanimoto_knn5"]},
            "paired_minus_production": {v: {m: M.paired_difference(ev["_boot"], v, B.DP_PRODUCTION, m) for m in ("spearman", "rmse")} for v in variants},
            "paired_vs_best_baselines": {v: {r: M.paired_difference(ev["_boot"], v, r, "spearman") for r in ("mw_linear", "rf_morgan_counts", "tanimoto_knn5")} for v in variants}}
    out.write_text(json.dumps(B._round(report), indent=1), encoding="utf-8")
    print("wrote", out)


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(__file__).with_name("ablation_results.json"))
