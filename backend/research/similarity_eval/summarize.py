import io, json, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
R = json.load(open(sys.argv[1] + "/results.json", encoding="utf-8"))
SET = sys.argv[2] if len(sys.argv) > 2 else "test_primary"
M = ["morgan_exact", "morgan_faiss", "chemberta", "fusion_rrf", "fusion_zmean", "ctrl_mw", "ctrl_scaffold", "ctrl_random"]
def f(x, nd=3):
    return "–" if x is None else f"{x:.{nd}f}"
def ci(d, nd=3):
    return "–" if not d or d.get("mean") is None else (f"{d['mean']:.{nd}f} [{d['ci'][0]:.{nd}f}, {d['ci'][1]:.{nd}f}]" if d.get("ci") else f"{d['mean']:.{nd}f}")
for b in R["results"]:
    for t, r in R["results"][b].items():
        s = r["sets"][SET]; ret = s["retrieval"]; pr = s["paired_vs_morgan_exact"]
        print(f"\n### {b} {t} ({SET}; n queries {s['n']}, index {r['n_index']}; random-pair within-1-log rate {r['index_prior']['fraction_pairs_within_1_log']:.2f})\n")
        print("| method | Precision@10 (≤1 log) | mean abs ΔpValue@10 | nDCG@10 | capped Recall@10 | kNN-10 ρ | n | Δ Prec@10 vs Morgan [CI] | Δ nDCG@10 vs Morgan [CI] | Δ kNN ρ vs Morgan [CI] |")
        print("|---|---|---|---|---|---|---|---|---|---|")
        for m in M:
            e = ret[m]; k = s["knn_estimator_k10"][m]
            if m == "morgan_exact":
                d1 = d2 = d3 = "(reference)"
            else:
                g = lambda d: "–" if not d else f"{d['diff']:+.3f} [{d['ci'][0]:+.3f}, {d['ci'][1]:+.3f}]" + ("*" if d["verdict"] != "no_significant_difference" else "")
                d1, d2, d3 = g(pr[m]["precision@10"]), g(pr[m]["ndcg@10"]), g(pr[m]["knn_estimator_spearman"])
            print(f"| {m} | {ci(e['precision@10'])} | {ci(e['mean_abs_dp@10'], 2)} | {ci(e['ndcg@10'])} | {ci(e['recall@10'])} | {f(k.get('spearman'))} | {e['precision@10']['n']} | {d1} | {d2} | {d3} |")
print("\n\n## Structure agreement (test_primary queries)\n")
print("| target | overlap@10 Morgan∩ChemBERTa | overlap@50 | mean rank corr (Tanimoto vs cosine, whole index) | cosine p5–p95 | top-10 same-scaffold rate: Morgan / ChemBERTa / RRF / random | atom-pair Tanimoto top-10: Morgan / ChemBERTa / RRF / random | FCFP4 top-10: Morgan / ChemBERTa / RRF / random |")
print("|---|---|---|---|---|---|---|---|")
for b in R["results"]:
    for t, r in R["results"][b].items():
        a = r["structure_agreement"]; j = a["judges_top10"]
        q = lambda key, ms=("morgan_exact", "chemberta", "fusion_rrf", "ctrl_random"): " / ".join(f(j[m][key]["mean"], 2) for m in ms)
        print(f"| {b} {t} | {a['overlap_at_k_morgan_vs_chemberta']['10']:.3f} | {a['overlap_at_k_morgan_vs_chemberta']['50']:.3f} | {a['mean_rank_correlation_tanimoto_vs_cosine_over_index']:.3f} | {a['cosine_p5_p95'][0]:.2f}–{a['cosine_p5_p95'][1]:.2f} | {q('same_murcko_scaffold_rate')} | {q('atom_pair_tanimoto')} | {q('fcfp4_tanimoto')} |")
print("\n## Similarity vs activity difference (top-10 pairs): within-1-log rate / mean |Δ| / cliff rate (|Δ|≥2) by bin\n")
for b in R["results"]:
    for t, r in R["results"][b].items():
        for name, bins in r["similarity_vs_activity_difference_top10_pairs"].items():
            print(f"{b} {t} {name}: " + "; ".join(f"[{x['range'][0]},{x['range'][1]}) n={x['pairs']} {f(x['within_1_log'],2)}/{f(x['mean_abs_dp'],2)}/{f(x['cliff_rate_dp_ge_2'],2)}" for x in bins))
