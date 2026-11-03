import json,sys,io
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding='utf-8')
r=json.load(open('ablation_results.json'))
keys=list(r['KiKd']['DRD2']['test_primary']['metrics'])
P=[k for k in keys if 'production' in k][0]
print("| bench | target | n | production ρ | no-MPNN (Kd-mean) ρ, Δ vs prod [95% CI] | no-MPNN (pKd-mean) ρ | fixed-MPNN ρ, Δ vs prod [95% CI] | stock MPNN ρ | fixed MPNN ρ | RMSE prod / no-MPNN / fixed |")
print("|---|---|---|---|---|---|---|---|---|---|")
for b in r:
  for t,d in r[b].items():
    if 'test_primary' not in d: continue
    e=d['test_primary']; m=e['metrics']; pm=e['paired_minus_production']
    c=lambda v:f"{pm[v]['spearman']['difference_boot_mean']:+.2f} [{pm[v]['spearman']['ci'][0]:+.2f}, {pm[v]['spearman']['ci'][1]:+.2f}]"
    print(f"| {b} | {t} | {e['n']} | {m[P]['spearman']:.3f} | {m['no_mpnn_kd_mean']['spearman']:.3f}, {c('no_mpnn_kd_mean')} | {m['no_mpnn_pkd_mean']['spearman']:.3f} | {m['fixed_mpnn_kd_mean']['spearman']:.3f}, {c('fixed_mpnn_kd_mean')} | {m['mpnn_stock']['spearman']:.3f} | {m['mpnn_fixed']['spearman']:.3f} | {m[P]['rmse']:.2f} / {m['no_mpnn_kd_mean']['rmse']:.2f} / {m['fixed_mpnn_kd_mean']['rmse']:.2f} |")
print("\nBaselines (Spearman, KiKd test_primary):")
for t,d in r['KiKd'].items():
    if 'test_primary' in d:
        m=d['test_primary']['metrics']; print(t,{k:round(m[k]['spearman'],3) for k in ('mw_linear','rf_morgan_counts','tanimoto_knn5')})
