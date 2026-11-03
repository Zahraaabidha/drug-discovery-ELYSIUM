"""Research-only Priority 3 experiment 1: feature sets x learners on the frozen Ki/Kd benchmark data.

Targets DRD2, CDK2, VEGFR2, ESR1 (Ki/Kd only; IC50 is not touched). Sets, training frames, metrics, bootstrap seed and
pairing are exactly those of app.benchmarks.dti_benchmark (build_sets / evaluate_models). All hyperparameters are fixed
defaults chosen BEFORE seeing results; nothing is tuned on any test set. Output goes outside the repository; no DB writes.

Run from backend/:  PYTHONPATH=. venv/Scripts/python.exe -m research.dti_features.run_experiment <out_root>
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import logging
import sys
import time
from pathlib import Path
from typing import Dict, List

import numpy as np
import pandas as pd
from rdkit import RDLogger
from rdkit.Chem import Descriptors
from sklearn.ensemble import HistGradientBoostingRegressor, RandomForestRegressor

from app.benchmarks import dti_benchmark as B
from app.benchmarks import metrics as M
from app.services import chem

log = logging.getLogger(__name__)
RDLogger.DisableLog("rdApp.*")

FROZEN = Path(r"C:\ResearchDatasets\BindingDB\derived\benchmark_runs\dti-20261102-183553")
TARGETS = ["DRD2", "CDK2", "VEGFR2", "ESR1"]
BENCH = "KiKd"
CHEMBERTA = "seyonec/ChemBERTa-zinc-base-v1"
FEATURE_SETS = ["morgan_counts", "rdkit_desc", "morgan+desc", "chemberta", "morgan+chemberta"]
LEARNERS = ["rf", "hgb"]
REF = "rf_morgan_counts"            # existing benchmark reference
KNN = "tanimoto_knn5"


# ── features ──────────────────────────────────────────────────────────────
def rdkit_descriptors(smiles: str) -> np.ndarray:
    mol = chem.parse(smiles)
    out = np.full(len(Descriptors._descList), np.nan)
    for i, (_, fn) in enumerate(Descriptors._descList):
        try:
            v = float(fn(mol))
            out[i] = v if np.isfinite(v) and abs(v) < 1e9 else np.nan
        except Exception:
            pass
    return out


def chemberta_embeddings(smiles: List[str], cache: Path, batch: int = 64) -> Dict[str, np.ndarray]:
    """Frozen ChemBERTa CLS vector (unit-normalised, as in app.services.embeddings), computed in batches and cached by SMILES."""
    import torch
    from transformers import AutoModel, AutoTokenizer
    store: Dict[str, np.ndarray] = {}
    if cache.exists():
        z = np.load(cache, allow_pickle=True)
        store = dict(zip(z["smiles"].tolist(), z["emb"]))
    todo = [s for s in dict.fromkeys(smiles) if s not in store]
    if todo:
        tok, model = AutoTokenizer.from_pretrained(CHEMBERTA), AutoModel.from_pretrained(CHEMBERTA).eval()
        todo.sort(key=len)                                       # similar lengths per batch -> little padding
        for i in range(0, len(todo), batch):
            chunk = todo[i:i + batch]
            enc = tok(chunk, return_tensors="pt", padding=True, truncation=True, max_length=128)
            with torch.no_grad():
                cls = model(**enc).last_hidden_state[:, 0, :].numpy()
            cls = cls / np.maximum(np.linalg.norm(cls, axis=1, keepdims=True), 1e-12)
            store.update(zip(chunk, cls))
            if (i // batch) % 20 == 0:
                log.info("ChemBERTa %d/%d", i, len(todo))
        np.savez(cache, smiles=np.array(list(store), dtype=object), emb=np.vstack(list(store.values())))
    return store


class FeatureStore:
    def __init__(self, feats: B.Features, emb: Dict[str, np.ndarray]) -> None:
        self.f, self.emb, self._desc = feats, emb, {}

    def desc(self, s: str) -> np.ndarray:
        if s not in self._desc:
            self._desc[s] = rdkit_descriptors(s)
        return self._desc[s]

    def raw(self, name: str, smiles: pd.Series) -> np.ndarray:
        if name == "morgan_counts":
            return self.f.matrix(smiles, 1)
        if name == "rdkit_desc":
            return np.vstack([self.desc(s) for s in smiles])
        if name == "chemberta":
            return np.vstack([self.emb[s] for s in smiles])
        parts = name.split("+")
        return np.hstack([self.raw({"morgan": "morgan_counts", "desc": "rdkit_desc", "chemberta": "chemberta"}[p], smiles) for p in parts])


def prep(Xtr: np.ndarray, Xte: np.ndarray, learner: str):
    """Train-only preprocessing: drop columns constant/all-NaN in train; for RF impute train medians. No scaling needed for trees."""
    ok = np.nanstd(Xtr, axis=0) > 0
    Xtr, Xte = Xtr[:, ok], Xte[:, ok]
    if learner == "rf":
        med = np.nanmedian(Xtr, axis=0)
        Xtr = np.where(np.isnan(Xtr), med, Xtr)
        Xte = np.where(np.isnan(Xte), med, Xte)
    return Xtr, Xte


def fit_predict(learner: str, Xtr, ytr, Xte, seed: int, trees: int) -> np.ndarray:
    Xtr, Xte = prep(Xtr, Xte, learner)
    if learner == "rf":
        m = RandomForestRegressor(trees, random_state=seed, n_jobs=-1)
    else:
        m = HistGradientBoostingRegressor(random_state=seed)       # sklearn defaults, no tuning
    return m.fit(Xtr, ytr).predict(Xte)


def main(out_root: Path) -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    t0 = time.time()
    frozen = json.loads((FROZEN / "results.json").read_text(encoding="utf-8"))
    cfg = B.BenchConfig(**{k: (tuple(v) if isinstance(v, list) else v) for k, v in frozen["config"].items()})
    groups = pd.read_csv(Path(cfg.derived_dir) / "groups.csv.gz", low_memory=False)
    run_id = "dtifeat1-" + dt.datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    out = out_root / run_id
    out.mkdir(parents=True, exist_ok=True)

    sets = {t: B.build_sets(groups, BENCH, t, cfg) for t in TARGETS}
    all_smiles = sorted({s for t in TARGETS for df in [sets[t][0], *sets[t][3].values(), sets[t][1], sets[t][2]] for s in df["smiles_std"]})
    log.info("unique molecules: %d", len(all_smiles))
    emb = chemberta_embeddings(all_smiles, out_root / "chemberta_cls_cache.npz")
    fs = FeatureStore(B.Features(), emb)

    results: Dict = {}
    pred_rows: List[pd.DataFrame] = []
    for tgt in TARGETS:
        train_t, scaf_train, scaf_test, eval_sets, sets_train = sets[tgt]
        entry = {"n_train_temporal": int(len(train_t)), "n_train_scaffold": int(len(scaf_train)), "test_sets": {}}
        # reference baselines exactly as in the benchmark, once per training frame
        ref_cache = {}
        for fam, trf in (("temporal", train_t), ("scaffold", scaf_train)):
            members = [df for k, df in eval_sets.items() if sets_train[k] is trf]
            if members:
                union = pd.concat(members).drop_duplicates("ik_std").reset_index(drop=True)
                ref_cache[fam] = (B.baseline_predictions(trf, union, fs.f, cfg), {ik: i for i, ik in enumerate(union["ik_std"])}, union)
        # new models: one fit per (training frame, feature set, learner) predicting the union of its test compounds
        new_cache: Dict = {}
        for fam, (_, pos, union) in ref_cache.items():
            trf = train_t if fam == "temporal" else scaf_train
            ytr = trf["pvalue"].to_numpy(float)
            preds = {}
            for fset in FEATURE_SETS:
                Xtr, Xte = fs.raw(fset, trf["smiles_std"]), fs.raw(fset, union["smiles_std"])
                for lrn in LEARNERS:
                    preds[f"{lrn}:{fset}"] = fit_predict(lrn, Xtr, ytr, Xte, cfg.seed, cfg.rf_trees)
            new_cache[fam] = preds
            log.info("%s %s fitted (%.0fs)", tgt, fam, time.time() - t0)
        for set_name, test_df in eval_sets.items():
            if len(test_df) < 10:
                continue
            fam = "scaffold" if set_name == "scaffold_test" else "temporal"
            base, pos, _ = ref_cache[fam]
            idx = [pos[ik] for ik in test_df["ik_std"]]
            preds = {REF: base[REF][idx], KNN: base[KNN][idx], "mw_linear": base["mw_linear"][idx], "physchem_ridge": base["physchem_ridge"][idx]}
            preds.update({k: v[idx] for k, v in new_cache[fam].items()})
            y = test_df["pvalue"].to_numpy(float)
            ev = M.evaluate_models(y, preds, cfg.bootstrap, cfg.seed)
            new = [k for k in preds if ":" in k]
            entry["test_sets"][set_name] = {
                "n": int(len(y)), "train_n": int(len(train_t if fam == "temporal" else scaf_train)),
                "metrics": ev["models"],
                "paired_minus_rf_morgan_counts": {k: {m: M.paired_difference(ev["_boot"], k, REF, m) for m in ("spearman", "rmse")} for k in new},
                "paired_minus_knn": {k: {m: M.paired_difference(ev["_boot"], k, KNN, m) for m in ("spearman", "rmse")} for k in new}}
            for name, p in preds.items():
                pred_rows.append(pd.DataFrame({"target": tgt, "test_set": set_name, "inchikey": test_df["ik_std"], "model": name, "pred_pvalue": p, "measured_pvalue": y}))
        results[tgt] = entry
        log.info("%s evaluated (%.0fs)", tgt, time.time() - t0)

    # sanity: the reference baselines must equal the frozen run
    check = {}
    for tgt in TARGETS:
        for sn, s in results[tgt]["test_sets"].items():
            fz = frozen["results"][BENCH][tgt]["test_sets"].get(sn)
            if fz:
                check[f"{tgt}/{sn}"] = {k: abs(s["metrics"][k]["spearman"] - fz["metrics"][k]["spearman"]) for k in (REF, KNN)}
    payload = B._round({
        "run_id": run_id, "created_utc": dt.datetime.utcnow().isoformat(timespec="seconds"),
        "design": {"bench": BENCH, "targets": TARGETS, "feature_sets": FEATURE_SETS, "learners": LEARNERS,
                   "hyperparameters": f"rf: {cfg.rf_trees} trees, sklearn defaults otherwise (identical to rf_morgan_counts); hgb: sklearn HistGradientBoostingRegressor defaults; no tuning",
                   "chemberta": CHEMBERTA + " frozen, CLS token, unit-normalised, max_length 128",
                   "rdkit_descriptors": f"{len(Descriptors._descList)} rdkit.Chem.Descriptors._descList values; non-finite/|v|>=1e9 -> NaN; train-only constant-column removal; RF: train-median imputation, HGB: native NaN",
                   "splits": "benchmark build_sets: temporal train vs test_primary/test_strict/test_possible_overlap; scaffold split where eligible", "seed": cfg.seed, "bootstrap": cfg.bootstrap,
                   "frozen_reference_run": FROZEN.name},
        "reference_reproduction_max_abs_spearman_diff_vs_frozen": max(max(v.values()) for v in check.values()) if check else None,
        "results": results, "runtime_seconds": round(time.time() - t0, 1),
        "software": {"sklearn": __import__("sklearn").__version__, "numpy": np.__version__, "pandas": pd.__version__,
                     "code_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}})
    (out / "results.json").write_text(json.dumps(payload, indent=1), encoding="utf-8")
    pd.concat(pred_rows, ignore_index=True).to_csv(out / "predictions.csv.gz", index=False, compression="gzip")
    print(json.dumps({"run": run_id, "dir": str(out), "reference_reproduction": payload["reference_reproduction_max_abs_spearman_diff_vs_frozen"], "seconds": payload["runtime_seconds"]}))


if __name__ == "__main__":
    main(Path(sys.argv[1]))
