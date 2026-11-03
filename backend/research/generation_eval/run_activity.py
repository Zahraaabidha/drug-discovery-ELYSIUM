"""Stage 3 (research-only): PREDICTED target relevance of the generated molecules, kept separate from the quality stage.

ALL activity numbers here are COMPUTATIONAL PREDICTIONS from the corrected zero-shot DeepPurpose ensemble (model_version recorded) and, as a
second opinion, a Morgan kNN trained on the target's pre-cutoff BindingDB data. Neither is experimental validation. Before interpreting any
generated-molecule score the predictor is calibrated on measured BindingDB test compounds (per benchmark, Ki/Kd and IC50 never pooled).
Retrospective matches to later BindingDB measurements are reported as supporting evidence only.

Run from backend/:  PYTHONPATH=. venv/Scripts/python.exe -m research.generation_eval.run_activity
"""
import json
import logging
import time

import numpy as np
import pandas as pd
from rdkit import DataStructs
from scipy.stats import rankdata, spearmanr

from app.benchmarks import metrics as M
from app.data.candidate_library import CANDIDATE_LIBRARY
from app.services.dti_deeppurpose import DeepPurposeScreeningModel
from app.services.targets import resolve_target
from research.generation_eval import common as C

log = logging.getLogger(__name__)
CHUNK = 2000


def auc(pos, neg):
    s = np.concatenate([pos, neg])
    r = rankdata(s)
    return float((r[:len(pos)].sum() - len(pos) * (len(pos) + 1) / 2) / (len(pos) * len(neg)))


def auc_ci(pos, neg, B=1000, seed=0):
    rng = np.random.default_rng(seed)
    v = [auc(rng.choice(pos, len(pos)), rng.choice(neg, len(neg))) for _ in range(B)]
    return [float(np.quantile(v, .025)), float(np.quantile(v, .975))]


def score_all(model, smiles, seq, tgt):
    out = {}
    uniq = list(dict.fromkeys(smiles))
    for i in range(0, len(uniq), CHUNK):
        part = uniq[i:i + CHUNK]
        out.update({s: r.pkd for s, r in zip(part, model.predict(part, seq, tgt))})
        log.info("%s scored %d/%d", tgt, min(i + CHUNK, len(uniq)), len(uniq))
    return out


def dist(x):
    x = np.asarray(x, float)
    return {"n": int(len(x)), "mean": float(x.mean()), "median": float(np.median(x)), "p10": float(np.quantile(x, .1)), "p90": float(np.quantile(x, .9))}


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    t0 = time.time()
    cfg, groups = C.load_cfg_groups()
    run = C.OUT_ROOT / "genexp1"
    gen = pd.read_csv(run / "generated.csv.gz")
    qual = pd.read_csv(run / "quality_molecules.csv.gz")
    reg_seeds, _, _ = C.registry_snapshot()
    frozen = json.loads((C.FROZEN / "results.json").read_text(encoding="utf-8"))
    model = DeepPurposeScreeningModel()
    info = model.model_info()
    rng = np.random.default_rng(cfg.seed)
    rand_ref = groups.drop_duplicates("ik_std").sample(1000, random_state=3)["smiles_std"].tolist()
    drugs = [d["smiles"] for d in CANDIDATE_LIBRARY if d.get("smiles")]
    result = {"LABEL": "ALL VALUES IN THIS FILE ARE COMPUTATIONAL PREDICTIONS UNLESS TAGGED 'measured' (BindingDB)",
              "model": info, "targets": {}}
    rows = []
    for tgt in C.TARGETS:
        T = resolve_target(tgt)
        frames = C.target_frames(cfg, groups, tgt)
        primary = C.BENCHES[tgt][0]
        train = frames[primary]["train"]
        potent = train[train["pvalue"] >= C.POTENT]
        weak = train[train["pvalue"] < C.WEAK]
        seeds_B = pd.read_csv(run / f"seeds_B_{tgt}.csv")["smiles"].tolist()
        pot_s = potent.sample(min(1000, len(potent)), random_state=4)["smiles_std"].tolist()
        weak_s = weak.sample(min(1000, len(weak)), random_state=5)["smiles_std"].tolist()
        U = qual[(qual.target == tgt)]
        to_score = list(U["smiles"]) + reg_seeds + seeds_B + pot_s + weak_s + rand_ref + drugs
        for bench, fr in frames.items():
            to_score += fr["test_primary"]["smiles_std"].tolist()
        sc = score_all(model, to_score, T.sequence, tgt)
        tres = {"primary_benchmark": primary, "calibration_on_measured_test_primary": {}}

        # --- calibration of the predictor on MEASURED later-published compounds (per benchmark) ---
        for bench, fr in frames.items():
            te = fr["test_primary"]
            if len(te) < 20:
                tres["calibration_on_measured_test_primary"][bench] = {"n": int(len(te)), "note": "too few compounds"}
                continue
            y = te["pvalue"].to_numpy(float)
            p = np.array([sc[s] for s in te["smiles_std"]])
            pos, neg = p[y >= C.POTENT], p[y < C.WEAK]
            cal = {"n": int(len(te)), "n_potent_ge7": int(len(pos)), "n_weak_lt6": int(len(neg)),
                   "spearman_predicted_vs_measured": M.point_metrics(y, p)["spearman"],
                   "spearman_predicted_vs_molecular_weight": float(spearmanr(p, te["mol_weight"]).statistic),
                   "spearman_measured_vs_molecular_weight": float(spearmanr(y, te["mol_weight"]).statistic)}
            boot = M.bootstrap_metrics(y, p, np.random.default_rng(0).integers(0, len(y), size=(1000, len(y))))["spearman"]
            cal["spearman_ci"] = [float(np.nanquantile(boot, .025)), float(np.nanquantile(boot, .975))]
            if len(pos) >= 10 and len(neg) >= 10:
                cal["auc_potent_vs_weak"] = auc(pos, neg)
                cal["auc_ci"] = auc_ci(pos, neg)
            tres["calibration_on_measured_test_primary"][bench] = cal
        tres["frozen_benchmark_reference_spearman_test_primary"] = {
            b: {"dp_ensemble_stock_mpnn": frozen["results"][b][tgt]["test_sets"]["test_primary"]["metrics"]["dp_ensemble_production"]["spearman"],
                "tanimoto_knn5": frozen["results"][b][tgt]["test_sets"]["test_primary"]["metrics"]["tanimoto_knn5"]["spearman"]} for b in frames if tgt in frozen["results"].get(b, {})}

        # --- predicted pKd of references and generated sets ---
        refs = {"seeds_A_registry": reg_seeds, "seeds_B_potent_train": seeds_B, "potent_train_sample[measured>=7]": pot_s,
                "weak_train_sample[measured<6]": weak_s, "bindingdb_random_1000": rand_ref, "drug_library_50": drugs}
        tres["predicted_pkd_distributions"] = {k: dist([sc[s] for s in v]) for k, v in refs.items()}
        knn_fps = [C.chem.morgan_fp(s) for s in train["smiles_std"]]
        ytr = train["pvalue"].to_numpy(float)
        for cond in C.CONDITIONS:
            u = U[U.condition == cond].reset_index(drop=True)
            pred = np.array([sc[s] for s in u["smiles"]])
            seeds = reg_seeds if cond == "A" else seeds_B
            sfps = [C.chem.morgan_fp(s) for s in seeds]
            fps = [C.chem.morgan_fp(s) for s in u["smiles"]]
            nn = [int(np.argmax(DataStructs.BulkTanimotoSimilarity(f, sfps))) for f in fps]
            seed_pred = np.array([sc[seeds[i]] for i in nn])
            delta = pred - seed_pred
            knn = np.zeros(len(u))
            for j, f in enumerate(fps):
                sims = np.asarray(DataStructs.BulkTanimotoSimilarity(f, knn_fps))
                top = np.argsort(sims)[-5:]
                knn[j] = np.average(ytr[top], weights=sims[top] + 1e-6)
            u["pred_pkd"], u["delta_vs_nearest_seed"], u["knn5_pvalue"] = pred, delta, knn
            cut = np.quantile(pred, .9)
            top = u[u.pred_pkd >= cut]
            rest = u[u.pred_pkd < cut]
            cols = ["mw", "logp", "qed", "sa_score", "max_tanimoto_to_own_seeds"]
            tres[f"condition_{cond}"] = {
                "n_distinct_scored": int(len(u)),
                "predicted_pkd": dist(pred),
                "fraction_above_median_of_potent_train_sample_predictions": float(np.mean(pred > np.median([sc[s] for s in pot_s]))),
                "fraction_above_median_of_weak_train_sample_predictions": float(np.mean(pred > np.median([sc[s] for s in weak_s]))),
                "delta_vs_nearest_seed_prediction": {**dist(delta), "fraction_abs_lt_0.1": float(np.mean(np.abs(delta) < 0.1)), "fraction_abs_gt_0.5": float(np.mean(np.abs(delta) > 0.5))},
                "spearman_predicted_pkd_vs_mw": float(spearmanr(pred, u["mw"]).statistic),
                "spearman_predicted_pkd_vs_qed": float(spearmanr(pred, u["qed"]).statistic),
                "selection_effect_top10pct_by_predicted_pkd_vs_rest": {c: {"top10": float(top[c].mean()), "rest": float(rest[c].mean())} for c in cols} | {
                    "brenk_alert_rate": {"top10": float(top["brenk"].mean()), "rest": float(rest["brenk"].mean())}},
                "independent_knn5_pvalue": {**dist(knn), "note": "Morgan kNN on the target's pre-cutoff primary-benchmark data; a second computational prediction, bounded by the training labels of near neighbours"},
                "spearman_dp_vs_knn5_on_generated": float(spearmanr(pred, knn).statistic)}
            u["target"], u["condition"] = tgt, cond
            rows.append(u[["target", "condition", "inchikey", "smiles", "pred_pkd", "delta_vs_nearest_seed", "knn5_pvalue"]])

        # --- retrospective: generated molecules matching / close to MEASURED later records (supporting evidence only) ---
        retro = {}
        allgen = U.drop_duplicates("inchikey").reset_index(drop=True)
        gfps = [C.chem.morgan_fp(s) for s in allgen["smiles"]]
        for bench, fr in frames.items():
            te = fr["test_primary"]
            if not len(te):
                continue
            tfps = [C.chem.morgan_fp(s) for s in te["smiles_std"]]
            pairs = []
            for i, f in enumerate(gfps):
                sims = np.asarray(DataStructs.BulkTanimotoSimilarity(f, tfps))
                j = int(np.argmax(sims))
                if sims[j] >= 0.9:
                    pairs.append({"generated_smiles": allgen["smiles"][i], "matched_measured_smiles": te["smiles_std"].iloc[j], "tanimoto": float(sims[j]),
                                  "exact": bool(allgen["inchikey"][i] == te["ik_std"].iloc[j]), "measured_pValue": float(te["pvalue"].iloc[j]),
                                  "predicted_pkd_generated": float(sc[allgen["smiles"][i]]), "predicted_pkd_matched_compound": float(sc[te["smiles_std"].iloc[j]])})
            retro[bench] = {"n_test_primary_compounds": int(len(te)), "n_generated_with_tanimoto_ge_0.9": len(pairs), "n_exact": int(sum(p["exact"] for p in pairs)),
                            "pairs_first_30": pairs[:30]}
            if len(pairs) >= 5:
                m = np.array([p["measured_pValue"] for p in pairs]); g = np.array([p["predicted_pkd_generated"] for p in pairs])
                retro[bench]["spearman_predicted_generated_vs_measured_neighbour"] = float(spearmanr(g, m).statistic)
        tres["retrospective_matches_to_measured_test_primary"] = retro
        result["targets"][tgt] = tres
        log.info("%s done (%.0fs)", tgt, time.time() - t0)
    pd.concat(rows).to_csv(run / "predicted_generated.csv.gz", index=False, compression="gzip")
    (run / "activity.json").write_text(json.dumps(C.B._round(result), indent=1), encoding="utf-8")
    print("done", f"{time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
