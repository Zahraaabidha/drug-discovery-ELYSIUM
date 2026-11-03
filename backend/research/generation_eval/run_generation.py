"""Stage 1 (research-only): run the UNMODIFIED production MutationGenerator in memory.

Condition A = target-agnostic registry seeds exactly as discovery selects them (reference + external, first 400 by id; known set = registry).
Condition B = 400 random potent TRAINING compounds of the target (primary benchmark, pValue >= 7, pre-cutoff data only; known set = registry +
all training compounds of that benchmark/target). 5 fixed seeds x 1000 requested molecules per target and condition. Per-edit operator
diagnostics run the generator's own private operators one SMARTS at a time (no new algorithm).

Run from backend/:  PYTHONPATH=. venv/Scripts/python.exe -m research.generation_eval.run_generation
"""
import json
import logging
import random
import time

import numpy as np
import pandas as pd
from rdkit.Chem import Descriptors

from app.services.generation import MutationGenerator
from research.generation_eval import common as C

log = logging.getLogger(__name__)


def operator_diagnostics(seeds, known, n=4000, seed=1):
    out = {}
    gen = MutationGenerator(seeds)
    all_rxns, edits = list(gen._rxns), list(gen._EDITS)
    for edit, rxn in zip(edits, all_rxns):
        gen._rxns = [rxn]
        rng = random.Random(seed)
        n_prod = n_valid = n_size = novel = 0
        keys = set()
        for _ in range(n):
            cand = gen._mutate(rng.choice(gen._seeds), rng)
            if not cand:
                continue
            n_prod += 1
            try:
                std = C.chem.standardise(cand)
            except C.chem.InvalidMolecule:
                continue
            n_valid += 1
            if not (gen.mw_min <= Descriptors.MolWt(C.chem.parse(std.canonical_smiles)) <= gen.mw_max):
                n_size += 1
                continue
            keys.add(std.inchikey)
            novel += std.inchikey not in known
        out[edit] = {"attempts": n, "produced_a_product": n_prod, "valid_after_standardise": n_valid, "mw_filtered": n_size,
                     "unique_in_window_per_attempt_batch": len(keys), "unique_in_window_and_not_in_registry": novel}
    gen._rxns = all_rxns
    rng = random.Random(seed)
    random.seed(seed)
    produced = valid = novel = 0
    keys = set()
    for _ in range(max(1, n // 100)):
        for cand in gen._recombine(2, rng):
            produced += 1
            if not cand:
                continue
            try:
                std = C.chem.standardise(cand)
            except C.chem.InvalidMolecule:
                continue
            valid += 1
            keys.add(std.inchikey)
            novel += std.inchikey not in known
    out["BRICS_recombination"] = {"strings_returned": produced, "valid_after_standardise": valid, "unique": len(keys), "unique_and_not_in_registry": novel}
    return out


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    t0 = time.time()
    cfg, groups = C.load_cfg_groups()
    reg_seeds, reg_keys, origins = C.registry_snapshot()
    rows, stats, diag, seeds_used = [], [], {}, {}
    for tgt in C.TARGETS:
        frames = C.target_frames(cfg, groups, tgt)
        primary = C.BENCHES[tgt][0]
        train = frames[primary]["train"]
        potent = train[train["pvalue"] >= C.POTENT].sort_values("ik_std").reset_index(drop=True)
        rs = np.random.default_rng(cfg.seed)
        seeds_B = potent.iloc[rs.permutation(len(potent))[:C.MAX_SEED_COMPOUNDS]]["smiles_std"].tolist()
        known_B = set(reg_keys) | set(train["ik_std"])
        seeds_used[tgt] = {"A": reg_seeds, "B": seeds_B, "B_source": f"{primary} training frame, pValue>={C.POTENT}, n_potent_available={len(potent)}"}
        for cond, seeds, known in (("A", reg_seeds, reg_keys), ("B", seeds_B, known_B)):
            gen = MutationGenerator(seeds)
            diag[f"{tgt}/{cond}"] = operator_diagnostics(seeds, known)
            for s in C.SEEDS:
                res = gen.generate(tgt, C.N_REQUESTED, seed=s, known_inchikeys=known)
                st = res.stats.as_dict()
                st.update(target=tgt, condition=cond, seed=s, n_returned_distinct_smiles=len(set(res.smiles)))
                stats.append(st)
                rows += [{"target": tgt, "condition": cond, "seed": s, "smiles": smi} for smi in res.smiles]
                log.info("%s/%s seed %d: attempted %d valid %d unique %d novel %d returned %d (%.0fs)", tgt, cond, s, st["attempted"], st["valid"],
                         st["unique"], st["novel"], st["returned"], time.time() - t0)
    gen_df = pd.DataFrame(rows)
    gen_df["inchikey"] = [C.chem.standardise(s).inchikey for s in gen_df["smiles"]]
    run = C.OUT_ROOT / "genexp1"
    run.mkdir(parents=True, exist_ok=True)
    gen_df.to_csv(run / "generated.csv.gz", index=False, compression="gzip")
    (run / "generation_stats.json").write_text(json.dumps({
        "per_run": stats, "operator_diagnostics": diag, "registry_origins": origins, "n_registry_seeds_A": len(reg_seeds),
        "seeds_B": {t: {"n": len(v["B"]), "source": v["B_source"]} for t, v in seeds_used.items()},
        "generator_params": {"mw_window": [150, 650], "max_attempts_per_molecule": 60, "n_requested": C.N_REQUESTED, "seeds": C.SEEDS}}, indent=1), encoding="utf-8")
    pd.DataFrame({"smiles": reg_seeds}).to_csv(run / "seeds_A.csv", index=False)
    for t, v in seeds_used.items():
        pd.DataFrame({"smiles": v["B"]}).to_csv(run / f"seeds_B_{t}.csv", index=False)
    print("done", len(gen_df), f"{time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
