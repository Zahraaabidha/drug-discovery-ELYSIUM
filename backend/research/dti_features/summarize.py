import io, json, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
R = json.load(open(sys.argv[1] + "/results.json", encoding="utf-8"))["results"]
FS = ["morgan_counts", "rdkit_desc", "morgan+desc", "chemberta", "morgan+chemberta"]
def row(tgt, ts):
    s = R[tgt]["test_sets"].get(ts)
    if not s: return None
    m = s["metrics"]; pr = s["paired_minus_rf_morgan_counts"]; pk = s["paired_minus_knn"]
    return s, m, pr, pk
for ts, title in (("test_primary", "temporal test_primary"), ("scaffold_test", "scaffold_test (only DRD2 and CDK2 are scaffold-eligible per the manifest; VEGFR2 and ESR1 rows have n=33/39 and are uninformative)"), ("test_strict", "temporal test_strict")):
    print(f"\n### {title}: Spearman ρ (Δ vs Morgan-RF [95% CI]; * = CI excludes 0)\n")
    print("| target (n) | ref: Morgan-RF | ref: kNN | learner | " + " | ".join(FS) + " |")
    print("|---|---|---|---|" + "---|" * len(FS))
    for t in R:
        r = row(t, ts)
        if not r: continue
        s, m, pr, pk = r
        for lrn in ("rf", "hgb"):
            cells = []
            for f in FS:
                k = f"{lrn}:{f}"; d = pr[k]["spearman"]; star = "*" if d["ci"][0] > 0 or d["ci"][1] < 0 else ""
                cells.append(f"{m[k]['spearman']:.3f} ({d['difference_boot_mean']:+.2f} [{d['ci'][0]:+.2f},{d['ci'][1]:+.2f}]{star})")
            first = lrn == "rf"
            print(f"| {t} ({s['n']}) | {m['rf_morgan_counts']['spearman']:.3f} | {m['tanimoto_knn5']['spearman']:.3f} | {lrn} | " + " | ".join(cells) + " |")
print("\n### RMSE (test_primary): ref Morgan-RF / kNN / best new\n")
for t in R:
    s, m, pr, pk = row(t, "test_primary")
    new = {k: v["rmse"] for k, v in m.items() if ":" in k}; b = min(new, key=new.get)
    print(f"{t}: {m['rf_morgan_counts']['rmse']:.2f} / {m['tanimoto_knn5']['rmse']:.2f} / {b} {new[b]:.2f}; mw_linear {m['mw_linear']['rmse']:.2f}")
print("\n### vs kNN (test_primary), best new model per target by Spearman")
for t in R:
    s, m, pr, pk = row(t, "test_primary")
    new = {k: v["spearman"] for k, v in m.items() if ":" in k}; b = max(new, key=new.get); d = pk[b]["spearman"]
    print(f"{t}: best {b} ρ={new[b]:.3f}; Δ vs kNN {d['difference_boot_mean']:+.2f} [{d['ci'][0]:+.2f},{d['ci'][1]:+.2f}] {d['verdict']}")
