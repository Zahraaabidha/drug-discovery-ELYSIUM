"""Stage 2 (research-only): MOLECULAR QUALITY of the generated sets, computed WITHOUT any activity prediction.

Everything here is computed from structure (RDKit descriptors, QED, Ertl SA score, PAINS/Brenk/NIH alert catalogs): these are heuristics,
not experimental properties. Novelty is reported at separate levels: exact (InChIKey) vs the registry, vs ALL BindingDB-derived
compounds, and similarity-based (nearest-neighbour Tanimoto). Retrospective matches against BindingDB are listed as supporting evidence only.

Run from backend/:  PYTHONPATH=. venv/Scripts/python.exe -m research.generation_eval.run_quality
"""
import json
import logging
import time

import numpy as np
import pandas as pd
from rdkit import DataStructs
from rdkit.Chem.Scaffolds import MurckoScaffold
from rdkit.ML.Cluster import Butina
from scipy.stats import wasserstein_distance

from app.data.candidate_library import CANDIDATE_LIBRARY
from research.generation_eval import common as C

log = logging.getLogger(__name__)
PROPS = ["mw", "logp", "tpsa", "hbd", "hba", "rotb", "rings", "fsp3", "qed", "sa_score"]
RATES = ["lipinski_pass", "veber_pass", "pains", "brenk", "nih"]


def diversity(smiles, rng, max_n=1000):
    smiles = list(smiles)
    if len(smiles) > max_n:
        smiles = [smiles[i] for i in rng.choice(len(smiles), max_n, replace=False)]
    fps = [C.chem.morgan_fp(s) for s in smiles]
    n = len(fps)
    if n < 3:
        return {"n": n}
    sims = np.vstack([DataStructs.BulkTanimotoSimilarity(f, fps) for f in fps])
    iu = np.triu_indices(n, 1)
    scaf = []
    generic = []
    for s in smiles:
        m = C.chem.parse(s)
        sc = MurckoScaffold.GetScaffoldForMol(m)
        scaf.append(C.chem.Chem.MolToSmiles(sc) if sc.GetNumAtoms() else "")
        try:
            generic.append(C.chem.Chem.MolToSmiles(MurckoScaffold.MakeScaffoldGeneric(sc)) if sc.GetNumAtoms() else "")
        except Exception:
            generic.append("")
    dists = [1 - sims[i, :i].tolist()[j] for i in range(1, n) for j in range(i)]
    clusters = Butina.ClusterData(dists, n, 0.4, isDistData=True)      # similarity >= 0.6 within a cluster's centroid radius
    return {"n": n, "internal_diversity_1_minus_mean_tanimoto": float(1 - sims[iu].mean()),
            "unique_murcko_scaffolds_fraction": len(set(scaf)) / n, "unique_generic_scaffolds_fraction": len(set(generic)) / n,
            "butina_clusters_sim0.6_per_molecule": len(clusters) / n, "mean_nearest_neighbour_tanimoto_within_set": float(np.mean(np.sort(sims, axis=1)[:, -2]))}


def max_sims(query_fps, ref_fps):
    return np.array([max(DataStructs.BulkTanimotoSimilarity(q, ref_fps)) for q in query_fps])


def frac(x, thr):
    return {f">={t}": float(np.mean(x >= t)) for t in thr} | {"<0.4": float(np.mean(x < 0.4))}


def summarize_props(q: pd.DataFrame, ref: pd.DataFrame):
    out = {"n": int(len(q))}
    for p in PROPS:
        out[p] = {"mean": float(q[p].mean()), "median": float(q[p].median()), "p5": float(q[p].quantile(.05)), "p95": float(q[p].quantile(.95))}
        if ref is not None and len(ref):
            sd = float(ref[p].std()) or 1.0
            lo, hi = ref[p].quantile(.05), ref[p].quantile(.95)
            out[p]["wasserstein_vs_ref_in_ref_sd"] = float(wasserstein_distance(q[p], ref[p]) / sd)
            out[p]["fraction_inside_ref_5_95"] = float(((q[p] >= lo) & (q[p] <= hi)).mean())
    for r in RATES:
        out[r + "_rate"] = float(q[r].mean())
    out["any_alert_pains_or_brenk_rate"] = float(((q["pains"] + q["brenk"]) > 0).mean())
    return out


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    t0 = time.time()
    cfg, groups = C.load_cfg_groups()
    run = C.OUT_ROOT / "genexp1"
    gen = pd.read_csv(run / "generated.csv.gz")
    gstats = json.loads((run / "generation_stats.json").read_text(encoding="utf-8"))
    reg_seeds, reg_keys, _ = C.registry_snapshot()
    rng = np.random.default_rng(cfg.seed)

    allb = groups.drop_duplicates("ik_std")[["ik_std", "smiles_std"]].reset_index(drop=True)
    log.info("BindingDB-derived unique compounds: %d", len(allb))
    ik_all = set(allb["ik_std"])
    skel_all = {k[:14] for k in ik_all}
    # sanity: is generator InChIKey form comparable with the benchmark's ik_std?
    sample = allb.sample(300, random_state=1)
    comparable = float(np.mean([C.chem.standardise(s).inchikey == k for s, k in zip(sample["smiles_std"], sample["ik_std"])]))
    all_fps = [C.chem.morgan_fp(s) for s in allb["smiles_std"]]
    log.info("fingerprints done (%.0fs); inchikey comparability %.3f", time.time() - t0, comparable)
    rand_ref = allb.sample(2000, random_state=2)["smiles_std"].tolist()
    drugs = [d["smiles"] for d in CANDIDATE_LIBRARY if d.get("smiles")]

    result = {"inchikey_form_comparable_fraction": comparable, "bindingdb_unique_compounds": int(len(allb)), "targets": {}}
    mol_tables = []
    for tgt in C.TARGETS:
        frames = C.target_frames(cfg, groups, tgt)
        primary = C.BENCHES[tgt][0]
        train = frames[primary]["train"]
        potent = train[train["pvalue"] >= C.POTENT]
        weak = train[train["pvalue"] < C.WEAK]
        refs = {"seeds_A_registry": reg_seeds, f"seeds_B_potent_train[{primary}]": pd.read_csv(run / f"seeds_B_{tgt}.csv")["smiles"].tolist(),
                f"target_potent_train[{primary}]": potent["smiles_std"].tolist(), f"target_weak_train[{primary}]": weak["smiles_std"].tolist(),
                "bindingdb_random_2000": rand_ref, "drug_library_50": drugs}
        refq = {k: C.mol_quality(v) for k, v in refs.items()}
        ref_potent = refq[f"target_potent_train[{primary}]"]
        tres = {"primary_benchmark": primary, "references": {k: summarize_props(v, ref_potent) for k, v in refq.items()},
                "reference_diversity": {k: diversity(v, rng) for k, v in refs.items()}, "conditions": {}}
        train_fps = [C.chem.morgan_fp(s) for s in train["smiles_std"]]
        potent_fps = [C.chem.morgan_fp(s) for s in potent["smiles_std"]]
        for cond in C.CONDITIONS:
            sub = gen[(gen.target == tgt) & (gen.condition == cond)]
            seeds = reg_seeds if cond == "A" else refs[f"seeds_B_potent_train[{primary}]"]
            seed_fps = [C.chem.morgan_fp(s) for s in seeds]
            per_seed = []
            for r in [x for x in gstats["per_run"] if x["target"] == tgt and x["condition"] == cond]:
                ss = sub[sub.seed == r["seed"]]
                d = diversity(ss["smiles"], rng)
                per_seed.append({"seed": r["seed"], "requested": r["requested"], "attempted": r["attempted"], "valid": r["valid"], "valid_in_mw_window_and_unique": r["unique"],
                                 "novel_vs_registry_or_known_set": r["novel"], "returned": r["returned"], "returned_distinct_inchikeys": int(ss["inchikey"].nunique()),
                                 "validity_rate": r["validity"], "uniqueness_rate": r["uniqueness"], "novelty_rate_vs_known_set": r["novelty"], "exhausted": r["exhausted"], "diversity": d})
            union = sub.drop_duplicates("inchikey").reset_index(drop=True)
            qu = C.mol_quality(union["smiles"].tolist())
            qu["inchikey"] = union["inchikey"]
            qu["target"], qu["condition"] = tgt, cond
            fps = [C.chem.morgan_fp(s) for s in union["smiles"]]
            ms_seed, ms_all, ms_train, ms_potent = max_sims(fps, seed_fps), max_sims(fps, all_fps), max_sims(fps, train_fps), max_sims(fps, potent_fps)
            qu["max_tanimoto_to_own_seeds"], qu["max_tanimoto_to_bindingdb_all"] = ms_seed, ms_all
            qu["max_tanimoto_to_target_train"], qu["max_tanimoto_to_target_potent_train"] = ms_train, ms_potent
            exact_all = union["inchikey"].isin(ik_all).to_numpy()
            skel = union["inchikey"].str[:14].isin(skel_all).to_numpy()
            qu["exact_in_bindingdb"], qu["skeleton_in_bindingdb"] = exact_all, skel
            mol_tables.append(qu)
            # retrospective: exact / near matches to measured BindingDB records of THIS target, per benchmark (never pooled)
            retro = {}
            for bench, fr in frames.items():
                for role, df in (("train", fr["train"]), ("test_primary", fr["test_primary"])):
                    if not len(df):
                        continue
                    ikset = set(df["ik_std"])
                    exact_hits = union[union["inchikey"].isin(ikset)]
                    dfps = [C.chem.morgan_fp(s) for s in df["smiles_std"]]
                    near = [i for i, f in enumerate(fps) if max(DataStructs.BulkTanimotoSimilarity(f, dfps)) >= 0.9]
                    retro[f"{bench}/{role}"] = {"reference_compounds": int(len(df)), "generated_exact_matches": int(len(exact_hits)),
                                                "generated_with_tanimoto_ge_0.9_to_a_measured_compound": len(near),
                                                "exact_match_inchikeys": exact_hits["inchikey"].tolist()[:50]}
            tres["conditions"][cond] = {
                "per_seed": per_seed,
                "union_distinct_molecules": int(len(union)),
                "exact_novelty": {"fraction_exact_inchikey_in_any_bindingdb_compound": float(exact_all.mean()), "fraction_2d_skeleton_in_bindingdb": float(skel.mean()),
                                  "fraction_not_in_registry": 1.0 if cond == "A" else None, "note": "A: known set = registry only (as in production). B: known set = registry + the target's training compounds."},
                "similarity_novelty_nearest_tanimoto": {
                    "to_own_seeds": {"mean": float(ms_seed.mean()), "median": float(np.median(ms_seed)), **frac(ms_seed, (0.9, 0.8, 0.6))},
                    "to_all_bindingdb": {"mean": float(ms_all.mean()), "median": float(np.median(ms_all)), **frac(ms_all, (0.9, 0.8, 0.6))},
                    "to_target_train": {"mean": float(ms_train.mean()), **frac(ms_train, (0.9, 0.8, 0.6))},
                    "to_target_potent_train": {"mean": float(ms_potent.mean()), **frac(ms_potent, (0.9, 0.8, 0.6))}},
                "diversity_union": diversity(union["smiles"], rng),
                "quality_vs_target_potent_train": summarize_props(qu, ref_potent),
                "retrospective_bindingdb_matches": retro}
            log.info("%s/%s quality done (%.0fs)", tgt, cond, time.time() - t0)
        result["targets"][tgt] = tres
    pd.concat(mol_tables).to_csv(run / "quality_molecules.csv.gz", index=False, compression="gzip")
    (run / "quality.json").write_text(json.dumps(C.B._round(result), indent=1), encoding="utf-8")
    print("done", f"{time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
