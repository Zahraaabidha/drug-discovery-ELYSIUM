import io, json, sys
from pathlib import Path
import pandas as pd
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
D = Path("C:/ResearchDatasets/BindingDB/derived")
fr = json.loads((D / "benchmark_runs/dti-20261102-183553/results.json").read_text("utf-8"))
co = json.loads((D / "benchmark_runs_corrected/dti-20261103-065311/results.json").read_text("utf-8"))
ab = json.loads(Path("ablation_results.json").read_text("utf-8"))
P = "dp_ensemble_production"
BASE = ["mean_baseline", "mw_linear", "heavy_atoms_linear", "physchem_ridge", "ridge_morgan_counts", "rf_morgan_counts", "tanimoto_knn5"]
pa = pd.read_csv(D / "benchmark_runs/dti-20261102-183553/predictions.csv.gz"); pb = pd.read_csv(D / "benchmark_runs_corrected/dti-20261103-065311/predictions.csv.gz")
pa["d"] = (pa.pred_pvalue - pb.pred_pvalue).abs()
print("max |frozen-corrected| by model:"); print(pa.groupby("model").d.max().to_string())
agree = max(abs(co["results"][b][t]["test_sets"]["test_primary"]["metrics"][P]["spearman"] - ab[b][t]["test_primary"]["metrics"]["fixed_mpnn_kd_mean"]["spearman"]) for b in ab for t in ab[b] if "test_primary" in ab[b][t])
print("corrected-run vs ablation fixed-MPNN rho max diff:", agree)
print("\n| bench | target | n | original ρ | corrected ρ | Δ [95% CI] | best baseline (ρ) | corrected − best baseline (CI, verdict) | original − best baseline verdict | RMSE orig → corr |")
print("|---|---|---|---|---|---|---|---|---|---|")
for b in co["results"]:
    for t, e in co["results"][b].items():
        if "test_primary" not in e["test_sets"]: continue
        s = e["test_sets"]["test_primary"]; m = s["metrics"]; o = fr["results"][b][t]["test_sets"]["test_primary"]
        bb = max(BASE, key=lambda k: -9 if m[k]["spearman"] is None else m[k]["spearman"])
        pc = s["paired_dp_ensemble_production_minus"][bb]["spearman"]; po = o["paired_dp_ensemble_production_minus"][bb]["spearman"]
        d = ab[b][t]["test_primary"]["paired_minus_production"]["fixed_mpnn_kd_mean"]["spearman"]
        print(f"| {b} | {t} | {s['n']} | {o['metrics'][P]['spearman']:.3f} | {m[P]['spearman']:.3f} | {d['difference_boot_mean']:+.2f} [{d['ci'][0]:+.2f}, {d['ci'][1]:+.2f}] | {bb} ({m[bb]['spearman']:.3f}) | {pc['difference_boot_mean']:+.2f} [{pc['ci'][0]:+.2f}, {pc['ci'][1]:+.2f}] {pc['verdict']} | {po['verdict']} | {o['metrics'][P]['rmse']:.2f} → {m[P]['rmse']:.2f} |")
