"""Research-only similarity/retrieval experiment 1 (Morgan vs ChemBERTa vs fusion) on the frozen BindingDB benchmark data.

Retrieval setup (mirrors real use, prevents leakage): QUERIES = post-cutoff temporal `test_primary` compounds of one
benchmark/target; INDEX = the pre-cutoff training compounds measured on the SAME target in the SAME benchmark (Ki/Kd and IC50 never
mixed). A query is never in its index (asserted). `test_strict` (no 2-D-skeleton match before the cutoff, so no stereoisomer
duplicates) is analysed as a sensitivity subset of the same per-query results.

Three separate questions:
  A  structural fidelity: FAISS (production search logic, replicated and cross-checked against production code) vs exact Tanimoto;
     FAISS cosine vs exact cosine.
  B  structural agreement of Morgan and ChemBERTa neighbours, judged also by structural measures neither method uses.
  C  activity similarity: do neighbours have a similar measured pValue on the target (|dpValue| <= 1 log unit; graded nDCG).

No parameter is fitted or tuned on query data. Production code, DB and frozen benchmarks are not written.
Run from backend/:  PYTHONPATH=. venv/Scripts/python.exe -m research.similarity_eval.run_experiment <out_root>
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import logging
import os
import sys
import tempfile
import time
from pathlib import Path
from typing import Dict, List, Optional

import faiss
import numpy as np
import pandas as pd
from rdkit import DataStructs, RDLogger
from rdkit.Chem import rdMolDescriptors
from scipy.stats import rankdata

os.environ.setdefault("DATABASE_URL", "sqlite:///" + (Path(tempfile.mkdtemp(prefix="simeval_")) / "unused.db").as_posix())
os.environ.setdefault("ELYSIUM_DISABLE_ARANGO", "1")

from app.benchmarks import dti_benchmark as B  # noqa: E402
from app.benchmarks import metrics as M  # noqa: E402
from app.services import chem  # noqa: E402
from research.dti_features.run_experiment import FROZEN, chemberta_embeddings  # noqa: E402
from research.similarity_eval.embed import PLAN, all_smiles  # noqa: E402

RDLogger.DisableLog("rdApp.*")
log = logging.getLogger(__name__)
KS = (1, 5, 10, 50)
KMAX = 50
THRESH = 1.0                      # exploratory activity-similarity threshold (log units), approved
GRADE_MAX = 3.0                   # graded relevance = clip(3 - |dp|, 0, 3)
RRF_K = 60                        # fixed a priori
METHODS = ["morgan_exact", "morgan_faiss", "chemberta", "fusion_rrf", "fusion_zmean", "ctrl_random", "ctrl_scaffold", "ctrl_mw"]
POOL_FACTORS = (1, 3, 10, 30)


# ── similarity matrices ────────────────────────────────────────────────────
def bit_matrix(smiles) -> np.ndarray:
    return np.vstack([chem.fp_to_numpy(chem.morgan_fp(s)) for s in smiles]).astype(np.float32)


def tanimoto_matrix(Q: np.ndarray, T: np.ndarray) -> np.ndarray:
    inter = Q @ T.T
    union = Q.sum(1)[:, None] + T.sum(1)[None, :] - inter
    return np.where(union > 0, inter / np.maximum(union, 1), 0.0)


def order_of(S: np.ndarray) -> np.ndarray:
    return np.argsort(-S, axis=1, kind="stable")


def ranks_of(order: np.ndarray) -> np.ndarray:
    r = np.empty_like(order)
    rows = np.arange(order.shape[0])[:, None]
    r[rows, order] = np.arange(order.shape[1])[None, :]
    return r + 1


def faiss_binary_topk(Tq: np.ndarray, Qb: np.ndarray, S_exact: np.ndarray, k: int, pool_factor: int) -> np.ndarray:
    """Production logic: Hamming candidate pool (max(k*factor, k+1)) from IndexBinaryFlat, re-ranked by exact Tanimoto (stable)."""
    index = faiss.IndexBinaryFlat(2048)
    index.add(np.packbits(Tq.astype(np.uint8), axis=1))
    pool = min(index.ntotal, max(k * pool_factor, k + 1))
    _, idx = index.search(np.packbits(Qb.astype(np.uint8), axis=1), pool)
    out = np.full((len(Qb), k), -1, dtype=np.int64)
    for i in range(len(Qb)):
        cand = idx[i][idx[i] >= 0]
        sims = S_exact[i, cand]
        o = np.argsort(-sims, kind="stable")[:k]
        out[i, :len(o)] = cand[o]
    return out


# ── metrics ───────────────────────────────────────────────────────────────
def per_query_metrics(nbr: np.ndarray, yq: np.ndarray, yi: np.ndarray, rel_sorted: np.ndarray, n_rel: np.ndarray) -> Dict[str, np.ndarray]:
    """nbr: (nq, KMAX) index rows (-1 = undefined). Returns {metric@K: (nq,)} with NaN where fewer than K neighbours exist."""
    out: Dict[str, np.ndarray] = {}
    valid = nbr >= 0
    d = np.where(valid, np.abs(yq[:, None] - yi[np.maximum(nbr, 0)]), np.nan)
    rel = np.where(valid, np.clip(GRADE_MAX - d, 0, GRADE_MAX), np.nan)
    disc = 1.0 / np.log2(np.arange(2, KMAX + 2))
    for k in KS:
        ok = valid[:, :k].all(axis=1)
        hit = (d[:, :k] <= THRESH)
        prec = np.where(ok, hit.mean(axis=1), np.nan)
        out[f"precision@{k}"] = prec
        out[f"mean_abs_dp@{k}"] = np.where(ok, d[:, :k].mean(axis=1), np.nan)
        dcg = np.nansum(rel[:, :k] * disc[:k], axis=1)
        idcg = (rel_sorted[:, :k] * disc[:k]).sum(axis=1)
        out[f"ndcg@{k}"] = np.where(ok & (idcg > 0), dcg / np.maximum(idcg, 1e-12), np.nan)
        out[f"recall@{k}"] = np.where(ok & (n_rel > 0), hit.sum(axis=1) / np.minimum(k, np.maximum(n_rel, 1)), np.nan)
    ok10 = valid[:, :10].all(axis=1)
    out["nbr_mean@10"] = np.where(ok10, yi[np.maximum(nbr[:, :10], 0)].mean(axis=1), np.nan)
    return out


def boot_idx(n: int, B_: int, seed: int) -> np.ndarray:
    return np.random.default_rng(seed).integers(0, n, size=(B_, n))


def mean_ci(v: np.ndarray, B_: int, seed: int) -> Dict:
    v = v[np.isfinite(v)]
    if len(v) < 5:
        return {"mean": float(v.mean()) if len(v) else None, "ci": None, "n": int(len(v))}
    means = v[boot_idx(len(v), B_, seed)].mean(axis=1)
    return {"mean": float(v.mean()), "ci": [float(np.quantile(means, .025)), float(np.quantile(means, .975))], "n": int(len(v))}


def diff_ci(a: np.ndarray, b: np.ndarray, B_: int, seed: int) -> Optional[Dict]:
    ok = np.isfinite(a) & np.isfinite(b)
    if ok.sum() < 5:
        return None
    d = (a - b)[ok]
    means = d[boot_idx(len(d), B_, seed)].mean(axis=1)
    lo, hi = float(np.quantile(means, .025)), float(np.quantile(means, .975))
    return {"diff": float(d.mean()), "ci": [lo, hi], "n": int(ok.sum()), "verdict": "higher" if lo > 0 else "lower" if hi < 0 else "no_significant_difference"}


def estimator_summary(yq: np.ndarray, p: np.ndarray, B_: int, seed: int) -> Dict:
    ok = np.isfinite(p)
    y, p = yq[ok], p[ok]
    if len(y) < 10 or np.ptp(p) == 0:
        return {"n": int(len(y)), "spearman": None}
    boot = M.bootstrap_metrics(y, p, boot_idx(len(y), B_, seed))
    pm = M.point_metrics(y, p)
    return {"n": int(len(y)), "spearman": pm["spearman"], "spearman_ci": [float(np.nanquantile(boot["spearman"], .025)), float(np.nanquantile(boot["spearman"], .975))],
            "rmse": pm["rmse"], "rmse_ci": [float(np.quantile(boot["rmse"], .025)), float(np.quantile(boot["rmse"], .975))]}


def spearman_diff(yq, pa, pb, B_, seed) -> Optional[Dict]:
    ok = np.isfinite(pa) & np.isfinite(pb)
    if ok.sum() < 10 or np.ptp(pa[ok]) == 0 or np.ptp(pb[ok]) == 0:
        return None
    y, a, b = yq[ok], pa[ok], pb[ok]
    idx = boot_idx(len(y), B_, seed)
    d = M.bootstrap_metrics(y, a, idx)["spearman"] - M.bootstrap_metrics(y, b, idx)["spearman"]
    lo, hi = float(np.nanquantile(d, .025)), float(np.nanquantile(d, .975))
    return {"diff": float(M.point_metrics(y, a)["spearman"] - M.point_metrics(y, b)["spearman"]), "ci": [lo, hi], "n": int(ok.sum()),
            "verdict": "higher" if lo > 0 else "lower" if hi < 0 else "no_significant_difference"}


# ── one benchmark/target ──────────────────────────────────────────────────
def run_target(bench: str, tgt: str, cfg: B.BenchConfig, groups: pd.DataFrame, emb: Dict[str, np.ndarray], boot_n: int) -> Dict:
    t0 = time.time()
    train, _, _, evals, _ = B.build_sets(groups, bench, tgt, cfg)
    qdf = evals["test_primary"].reset_index(drop=True)
    strict = set(evals["test_strict"]["ik_std"]) if "test_strict" in evals else set()
    idf = train.reset_index(drop=True)
    assert not (set(qdf["ik_std"]) & set(idf["ik_std"])), "query compound present in its index (leakage)"
    nq, ni = len(qdf), len(idf)
    yq, yi = qdf["pvalue"].to_numpy(float), idf["pvalue"].to_numpy(float)
    rng = np.random.default_rng(cfg.seed)

    Qb, Tb = bit_matrix(qdf["smiles_std"]), bit_matrix(idf["smiles_std"])
    St = tanimoto_matrix(Qb, Tb)
    Qe = np.vstack([emb[s] for s in qdf["smiles_std"]]).astype(np.float32)
    Te = np.vstack([emb[s] for s in idf["smiles_std"]]).astype(np.float32)
    Sc = Qe @ Te.T
    ot, oc = order_of(St), order_of(Sc)
    rt, rc = ranks_of(ot), ranks_of(oc)
    z = lambda S: (S - S.mean(1, keepdims=True)) / np.maximum(S.std(1, keepdims=True), 1e-9)
    rrf = 1.0 / (RRF_K + rt) + 1.0 / (RRF_K + rc)
    zmean = (z(St) + z(Sc)) / 2

    nbr: Dict[str, np.ndarray] = {
        "morgan_exact": ot[:, :KMAX], "chemberta": oc[:, :KMAX],
        "fusion_rrf": order_of(rrf)[:, :KMAX], "fusion_zmean": order_of(zmean)[:, :KMAX],
        "morgan_faiss": faiss_binary_topk(Tb, Qb, St, KMAX, 10)}
    # controls: random; same Murcko scaffold (random among them; undefined if < K); K nearest in molecular weight
    nbr["ctrl_random"] = np.vstack([rng.permutation(ni)[:KMAX] for _ in range(nq)])
    sc_i = idf["scaffold"].fillna("").to_numpy(str)
    by_scaf: Dict[str, np.ndarray] = {}
    for s in np.unique(sc_i):
        if s:
            by_scaf[s] = np.where(sc_i == s)[0]
    ns = np.full((nq, KMAX), -1, dtype=np.int64)
    for i, s in enumerate(qdf["scaffold"].fillna("").to_numpy(str)):
        c = by_scaf.get(s)
        if s and c is not None:
            c = rng.permutation(c)[:KMAX]
            ns[i, :len(c)] = c
    nbr["ctrl_scaffold"] = ns
    mw_q, mw_i = qdf["mol_weight"].to_numpy(float), idf["mol_weight"].to_numpy(float)
    jitter = rng.random((nq, ni)) * 1e-6
    nbr["ctrl_mw"] = np.argsort(np.abs(mw_q[:, None] - mw_i[None, :]) + jitter, axis=1, kind="stable")[:, :KMAX]

    # graded ideal ordering and relevant counts over the whole index
    dall = np.abs(yq[:, None] - yi[None, :])
    rel_sorted = np.sort(np.clip(GRADE_MAX - dall, 0, GRADE_MAX), axis=1)[:, ::-1][:, :KMAX]
    n_rel = (dall <= THRESH).sum(1)
    pq = {m: per_query_metrics(nbr[m], yq, yi, rel_sorted, n_rel) for m in METHODS}

    in_strict = qdf["ik_std"].isin(strict).to_numpy()
    sets = {"test_primary": np.ones(nq, bool), "test_strict": in_strict}
    result: Dict = {"n_queries": int(nq), "n_index": int(ni), "n_queries_strict": int(in_strict.sum()),
                    "index_prior": {"fraction_pairs_within_1_log": float((dall <= THRESH).mean()), "mean_abs_dp_random_pair": float(dall.mean()),
                                    "mean_relevant_per_query": float(n_rel.mean())},
                    "top1_tanimoto_equals_1_fraction": float((St.max(1) >= 0.9999).mean()), "sets": {}}

    # --- part C: activity ---
    for sname, mask in sets.items():
        sec: Dict = {"n": int(mask.sum()), "retrieval": {}, "knn_estimator_k10": {}, "paired_vs_morgan_exact": {}}
        for m in METHODS:
            sec["retrieval"][m] = {k: mean_ci(v[mask], boot_n, cfg.seed) for k, v in pq[m].items() if k != "nbr_mean@10"}
            sec["knn_estimator_k10"][m] = estimator_summary(yq[mask], pq[m]["nbr_mean@10"][mask], boot_n, cfg.seed)
        for m in METHODS:
            if m == "morgan_exact":
                continue
            sec["paired_vs_morgan_exact"][m] = {k: diff_ci(v[mask], pq["morgan_exact"][k][mask], boot_n, cfg.seed) for k, v in pq[m].items() if k != "nbr_mean@10"}
            sec["paired_vs_morgan_exact"][m]["knn_estimator_spearman"] = spearman_diff(yq[mask], pq[m]["nbr_mean@10"][mask], pq["morgan_exact"]["nbr_mean@10"][mask], boot_n, cfg.seed)
        # paired fusion / chemberta vs the better single method is also in paired_vs_morgan_exact; controls vs morgan likewise
        result["sets"][sname] = sec

    # --- part B: structural agreement and independent structural judges ---
    ap = np.vstack([np.array(list(rdMolDescriptors.GetHashedAtomPairFingerprintAsBitVect(chem.parse(s), nBits=2048)), dtype=np.uint8) for s in pd.concat([qdf["smiles_std"], idf["smiles_std"]])])
    from rdkit.Chem import AllChem
    fc = np.vstack([np.array(list(AllChem.GetMorganFingerprintAsBitVect(chem.parse(s), 2, nBits=2048, useFeatures=True)), dtype=np.uint8) for s in pd.concat([qdf["smiles_std"], idf["smiles_std"]])])
    judges = {"atom_pair_tanimoto": ap, "fcfp4_tanimoto": fc}

    def judge_mean(name: str, nb: np.ndarray, k: int = 10) -> np.ndarray:
        A = judges[name].astype(np.float32)
        Aq, Ai = A[:nq], A[nq:]
        v = np.full(nq, np.nan)
        for i in range(nq):
            if (nb[i, :k] < 0).any():
                continue
            N = Ai[nb[i, :k]]
            inter = N @ Aq[i]
            union = N.sum(1) + Aq[i].sum() - inter
            v[i] = np.mean(inter / np.maximum(union, 1))
        return v

    rank_corr = []
    for i in range(0, nq, max(1, nq // 300)):                      # Spearman of Tanimoto vs cosine over the whole index, sampled queries
        rank_corr.append(float(np.corrcoef(rt[i], rc[i])[0, 1]))
    same_scaf_q = qdf["scaffold"].fillna("").to_numpy(str)
    struct: Dict = {"overlap_at_k_morgan_vs_chemberta": {str(k): float(np.mean([len(set(ot[i, :k]) & set(oc[i, :k])) / k for i in range(nq)])) for k in (5, 10, 50)},
                    "overlap_at_10_morgan_vs_fusion_rrf": float(np.mean([len(set(ot[i, :10]) & set(nbr["fusion_rrf"][i, :10])) / 10 for i in range(nq)])),
                    "mean_rank_correlation_tanimoto_vs_cosine_over_index": float(np.mean(rank_corr)),
                    "median_cosine_of_all_pairs": float(np.median(Sc)), "cosine_p5_p95": [float(np.quantile(Sc, .05)), float(np.quantile(Sc, .95))],
                    "median_tanimoto_of_all_pairs": float(np.median(St)), "judges_top10": {}}
    for m in ("morgan_exact", "morgan_faiss", "chemberta", "fusion_rrf", "fusion_zmean", "ctrl_random", "ctrl_mw"):
        row = {j: mean_ci(judge_mean(j, nbr[m]), boot_n, cfg.seed) for j in judges}
        row["morgan_tanimoto"] = mean_ci(np.array([St[i, nbr[m][i, :10]].mean() for i in range(nq)]), boot_n, cfg.seed)
        row["same_murcko_scaffold_rate"] = mean_ci(np.array([float(np.mean(sc_i[nbr[m][i, :10]] == same_scaf_q[i])) if same_scaf_q[i] else np.nan for i in range(nq)]), boot_n, cfg.seed)
        struct["judges_top10"][m] = row
    result["structure_agreement"] = struct

    # --- similarity -> activity-difference curves on the top-10 pairs ---
    curve = {}
    for name, S, nb in (("morgan_tanimoto", St, nbr["morgan_exact"]), ("chemberta_cosine", Sc, nbr["chemberta"])):
        sims = np.take_along_axis(S, nb[:, :10], axis=1).ravel()
        dp = np.abs(yq[:, None] - yi[nb[:, :10]]).ravel()
        edges = [0, .3, .4, .5, .7, 1.0001] if name == "morgan_tanimoto" else list(np.quantile(sims, [0, .2, .4, .6, .8, 1.0]))
        bins = []
        for lo, hi in zip(edges[:-1], edges[1:]):
            sel = (sims >= lo) & (sims < hi if hi != edges[-1] else sims <= hi)
            bins.append({"range": [round(float(lo), 3), round(float(hi), 3)], "pairs": int(sel.sum()),
                         "mean_abs_dp": float(dp[sel].mean()) if sel.sum() else None, "within_1_log": float((dp[sel] <= THRESH).mean()) if sel.sum() else None,
                         "cliff_rate_dp_ge_2": float((dp[sel] >= 2).mean()) if sel.sum() else None})
        curve[name] = bins
    result["similarity_vs_activity_difference_top10_pairs"] = curve

    # --- sanity: Morgan top-5 similarity-weighted kNN reproduces the frozen benchmark's tanimoto_knn5 ---
    top5 = ot[:, :5]
    w = np.take_along_axis(St, top5, axis=1) + 1e-6
    knn5 = (yi[top5] * w).sum(1) / w.sum(1)
    result["sanity_knn5_spearman_here"] = float(M.point_metrics(yq, knn5)["spearman"])
    result["seconds"] = round(time.time() - t0, 1)

    # --- part A: FAISS fidelity (per target, test_primary queries) ---
    result["faiss_fidelity"] = faiss_fidelity(Tb, Qb, St, Sc, Te, Qe, ot)
    result["_keep"] = {"Tb": Tb, "Qb": Qb, "St": St, "idf_smiles": idf["smiles_std"].tolist(), "qdf_smiles": qdf["smiles_std"].tolist()}
    return result


def faiss_fidelity(Tb, Qb, St, Sc, Te, Qe, ot) -> Dict:
    out: Dict = {"binary_pool_sweep": {}}
    kth_cache = {k: np.take_along_axis(St, ot[:, :k], axis=1) for k in (1, 10, 50)}
    for k in (1, 10, 50):
        for f in POOL_FACTORS:
            got = faiss_binary_topk(Tb, Qb, St, k, f)
            strict, tie, gap = [], [], []
            for i in range(len(Qb)):
                ex = set(ot[i, :k]); g = [x for x in got[i] if x >= 0]
                strict.append(len(ex & set(g)) / k)
                thr = kth_cache[k][i, -1]
                tie.append(sum(St[i, x] >= thr - 1e-9 for x in g) / k)
                gap.append(float(kth_cache[k][i].mean() - np.mean(St[i, g])) if len(g) == k else np.nan)
            out["binary_pool_sweep"][f"k={k},pool_factor={f}"] = {
                "recall_set_overlap": float(np.mean(strict)), "recall_tie_aware": float(np.mean(tie)),
                "mean_similarity_shortfall_vs_exact": float(np.nanmean(gap)), "queries_with_perfect_recall_tie_aware": float(np.mean(np.array(tie) >= 0.9999))}
    ip = faiss.IndexFlatIP(Te.shape[1]); ip.add(Te)
    _, idx = ip.search(Qe, 50)
    ex = order_of(Sc)[:, :50]
    out["cosine_flat_ip_vs_exact_matmul"] = {f"recall@{k}_tie_aware": float(np.mean([
        sum(Sc[i, x] >= Sc[i, ex[i, k - 1]] - 1e-6 for x in idx[i, :k]) / k for i in range(len(Qe))])) for k in (1, 10, 50)}
    return out


def production_crosscheck(keep: Dict, n_queries: int = 100) -> Dict:
    """Run the actual production SimilarityIndex.search_fingerprint on an in-memory index (no DB) and compare with the replicated logic."""
    from app.services.similarity_index import SimilarityIndex
    Tb, St = keep["Tb"], keep["St"]
    si = SimilarityIndex()
    si._ids = list(range(len(Tb)))
    si._inchikeys = [str(i) for i in range(len(Tb))]
    si._smiles = keep["idf_smiles"]
    packed = np.packbits(Tb.astype(np.uint8), axis=1)
    si._fp_bits = faiss.IndexBinaryFlat(2048)
    si._fp_bits.add(packed)
    si._popcount = np.unpackbits(packed, axis=1).sum(axis=1).astype("int32")
    out = {}
    for k in (10, 50):
        same, maxdiff = 0, 0.0
        sel = list(range(0, len(keep["qdf_smiles"]), max(1, len(keep["qdf_smiles"]) // n_queries)))[:n_queries]
        mine = faiss_binary_topk(Tb, keep["Qb"][sel], St[sel], k, 10)
        for j, i in enumerate(sel):
            prod = si.search_fingerprint(keep["qdf_smiles"][i], k)
            same += int([n.compound_id for n in prod] == mine[j].tolist())
            maxdiff = max(maxdiff, max(abs(n.similarity - St[i, n.compound_id]) for n in prod))
        out[f"k={k}"] = {"queries": len(sel), "identical_id_lists": same, "max_similarity_difference": maxdiff}
    return out


def pooled_kikd_fidelity(cfg, groups, emb) -> Dict:
    """Part A on one pooled Ki/Kd index (union of the four targets' training compounds) with all their test_primary queries."""
    tr, qs = {}, {}
    for bench, tgt in PLAN:
        if bench != "KiKd":
            continue
        train, _, _, evals, _ = B.build_sets(groups, bench, tgt, cfg)
        tr.update(dict(zip(train["ik_std"], train["smiles_std"])))
        qs.update(dict(zip(evals["test_primary"]["ik_std"], evals["test_primary"]["smiles_std"])))
    assert not (set(tr) & set(qs)), "pooled leakage"
    T, Q = list(tr.values()), list(qs.values())
    Tb, Qb = bit_matrix(T), bit_matrix(Q)
    St = tanimoto_matrix(Qb, Tb)
    Te, Qe = np.vstack([emb[s] for s in T]).astype(np.float32), np.vstack([emb[s] for s in Q]).astype(np.float32)
    res = faiss_fidelity(Tb, Qb, St, Qe @ Te.T, Te, Qe, order_of(St))
    res.update({"n_index": len(T), "n_queries": len(Q)})
    return res


def main(out_root: Path) -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    t0 = time.time()
    frozen = json.loads((FROZEN / "results.json").read_text(encoding="utf-8"))
    cfg = B.BenchConfig(**{k: (tuple(v) if isinstance(v, list) else v) for k, v in frozen["config"].items()})
    groups = pd.read_csv(Path(cfg.derived_dir) / "groups.csv.gz", low_memory=False)
    emb = chemberta_embeddings(all_smiles(cfg, groups), out_root / "chemberta_cls_cache.npz")
    run_id = "simeval1-" + dt.datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    out = out_root / run_id
    out.mkdir(parents=True, exist_ok=True)
    results: Dict = {}
    crosscheck = None
    for bench, tgt in PLAN:
        r = run_target(bench, tgt, cfg, groups, emb, cfg.bootstrap)
        if crosscheck is None:
            crosscheck = {"target": f"{bench}/{tgt}", **production_crosscheck(r["_keep"])}
        r.pop("_keep")
        results.setdefault(bench, {})[tgt] = r
        log.info("%s/%s done (%.0fs)", bench, tgt, time.time() - t0)
    frozen_knn = {f"{b}/{t}": frozen["results"][b][t]["test_sets"]["test_primary"]["metrics"]["tanimoto_knn5"]["spearman"] for b, t in PLAN}
    payload = B._round({
        "run_id": run_id, "created_utc": dt.datetime.utcnow().isoformat(timespec="seconds"),
        "design": {"queries": "temporal test_primary (test_strict analysed as subset)", "index": "pre-cutoff training compounds of the same target and benchmark",
                   "activity_similar": f"|dpValue| <= {THRESH}", "graded_relevance": f"clip({GRADE_MAX} - |dp|, 0, {GRADE_MAX}), linear gain, log2 discount",
                   "recall@K": "capped: hits / min(K, number of relevant index compounds)", "K": list(KS), "fusion": {"rrf_k": RRF_K, "zmean": "mean of per-query z-scored Tanimoto and cosine over the index"},
                   "controls": "random; random same-Murcko-scaffold (undefined if < K); K nearest molecular weight", "bootstrap": cfg.bootstrap, "seed": cfg.seed,
                   "chemberta": "seyonec/ChemBERTa-zinc-base-v1 frozen CLS, unit-normalised", "morgan": "radius 2, 2048 bits (production settings)"},
        "production_crosscheck_morgan_faiss": crosscheck,
        "frozen_benchmark_tanimoto_knn5_spearman": frozen_knn,
        "pooled_kikd_faiss_fidelity": pooled_kikd_fidelity(cfg, groups, emb),
        "results": results, "runtime_seconds": round(time.time() - t0, 1),
        "code_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()})
    (out / "results.json").write_text(json.dumps(payload, indent=1), encoding="utf-8")
    print(json.dumps({"run": run_id, "dir": str(out), "seconds": payload["runtime_seconds"]}))


if __name__ == "__main__":
    main(Path(sys.argv[1]))
