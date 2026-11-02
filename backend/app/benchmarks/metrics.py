"""Evaluation metrics with paired bootstrap confidence intervals (vectorised, seeded).

All models are evaluated on the SAME test compounds and the SAME bootstrap resamples, so differences between
models can be assessed with paired intervals.
"""
from __future__ import annotations

from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np
from scipy.stats import rankdata

METRICS = ("spearman", "pearson", "rmse", "mae", "enrichment_top10")


def _corr_rows(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Pearson correlation along the last axis (rows)."""
    a = a - a.mean(axis=-1, keepdims=True)
    b = b - b.mean(axis=-1, keepdims=True)
    den = np.sqrt((a * a).sum(axis=-1) * (b * b).sum(axis=-1))
    with np.errstate(invalid="ignore", divide="ignore"):
        return (a * b).sum(axis=-1) / den


def enrichment_top_fraction(y: np.ndarray, p: np.ndarray, frac: float = 0.10) -> float:
    """Of the compounds the model ranks in its top `frac`, the fraction that are truly in the top `frac` of the
    measured values, divided by `frac` (1.0 = random, 1/frac = perfect). NaN if predictions are constant."""
    y = np.asarray(y, float)
    p = np.asarray(p, float)
    if np.ptp(p) == 0:
        return float("nan")
    k = max(1, int(np.ceil(frac * len(y))))
    top_y = set(np.argsort(-y, kind="stable")[:k])
    top_p = np.argsort(-p, kind="stable")[:k]
    hit = sum(1 for i in top_p if i in top_y)
    return (hit / k) / frac


def point_metrics(y: np.ndarray, p: np.ndarray) -> Dict[str, float]:
    y = np.asarray(y, float)
    p = np.asarray(p, float)
    const = np.ptp(p) == 0
    return {
        "spearman": float("nan") if const else float(_corr_rows(rankdata(y), rankdata(p))),
        "pearson": float("nan") if const else float(_corr_rows(y, p)),
        "rmse": float(np.sqrt(np.mean((p - y) ** 2))),
        "mae": float(np.mean(np.abs(p - y))),
        "bias": float(np.mean(p - y)),
        "enrichment_top10": enrichment_top_fraction(y, p, 0.10),
    }


def bootstrap_indices(n: int, B: int, rng: np.random.Generator) -> np.ndarray:
    return rng.integers(0, n, size=(B, n))


def bootstrap_metrics(y: np.ndarray, p: np.ndarray, idx: np.ndarray, frac: float = 0.10) -> Dict[str, np.ndarray]:
    """Vectorised metrics for every bootstrap resample (rows of `idx`)."""
    y = np.asarray(y, float)
    p = np.asarray(p, float)
    yb, pb = y[idx], p[idx]
    out: Dict[str, np.ndarray] = {
        "rmse": np.sqrt(np.mean((pb - yb) ** 2, axis=1)),
        "mae": np.mean(np.abs(pb - yb), axis=1),
    }
    if np.ptp(p) == 0:
        out["spearman"] = out["pearson"] = out["enrichment_top10"] = np.full(len(idx), np.nan)
        return out
    out["pearson"] = _corr_rows(yb, pb)
    out["spearman"] = _corr_rows(rankdata(yb, axis=1), rankdata(pb, axis=1))
    n = yb.shape[1]
    k = max(1, int(np.ceil(frac * n)))
    ry = rankdata(-yb, axis=1, method="ordinal")
    rp = rankdata(-pb, axis=1, method="ordinal")
    hits = ((ry <= k) & (rp <= k)).sum(axis=1)
    out["enrichment_top10"] = (hits / k) / frac
    return out


def ci(values: np.ndarray, level: float = 0.95) -> Tuple[float, float]:
    v = values[np.isfinite(values)]
    if len(v) < 20:
        return (float("nan"), float("nan"))
    a = (1 - level) / 2
    return (float(np.quantile(v, a)), float(np.quantile(v, 1 - a)))


def evaluate_models(y: np.ndarray, preds: Dict[str, np.ndarray], B: int, seed: int) -> Dict:
    """Point estimates + 95% bootstrap CIs for every model on identical compounds/resamples.
    Returns {"models": {name: {metric: value, metric_ci: [lo, hi]}}, "_boot": {name: {metric: array}}}."""
    y = np.asarray(y, float)
    rng = np.random.default_rng(seed)
    idx = bootstrap_indices(len(y), B, rng)
    models: Dict[str, Dict] = {}
    boot: Dict[str, Dict[str, np.ndarray]] = {}
    for name, p in preds.items():
        pt = point_metrics(y, p)
        bs = bootstrap_metrics(y, p, idx)
        row = dict(pt)
        for m in METRICS:
            lo, hi = ci(bs[m])
            row[m + "_ci"] = [lo, hi]
        models[name] = row
        boot[name] = bs
    return {"models": models, "_boot": boot}


def paired_difference(boot: Dict[str, Dict[str, np.ndarray]], a: str, b: str, metric: str,
                      higher_is_better: Optional[bool] = None) -> Dict:
    """a - b with a paired bootstrap 95% CI and a verdict that is only 'better'/'worse' when the CI excludes 0."""
    if higher_is_better is None:
        higher_is_better = metric not in ("rmse", "mae")
    d = boot[a][metric] - boot[b][metric]
    lo, hi = ci(d)
    fin = d[np.isfinite(d)]
    point = float(fin.mean()) if len(fin) else float("nan")
    if not np.isfinite(lo):
        verdict = "undefined"
    elif lo > 0 or hi < 0:
        positive = lo > 0
        verdict = "better" if positive == higher_is_better else "worse"
    else:
        verdict = "no_significant_difference"
    return {"metric": metric, "difference_boot_mean": point, "ci": [lo, hi], "verdict": verdict}


def partial_spearman(y: np.ndarray, p: np.ndarray, z: np.ndarray) -> float:
    """Spearman correlation of y and p after linearly removing the rank-dependence on z (e.g. molecular weight)."""
    ry, rp, rz = rankdata(y), rankdata(p), rankdata(z)
    def resid(r):
        A = np.vstack([rz, np.ones_like(rz)]).T
        coef, *_ = np.linalg.lstsq(A, r, rcond=None)
        return r - A @ coef
    a, b = resid(ry), resid(rp)
    if np.ptp(b) < 1e-12 or np.ptp(a) < 1e-12:
        return float("nan")
    return float(np.corrcoef(a, b)[0, 1])


def partial_spearman_ci(y, p, z, B: int, seed: int) -> Tuple[float, List[float]]:
    y, p, z = (np.asarray(v, float) for v in (y, p, z))
    point = partial_spearman(y, p, z)
    rng = np.random.default_rng(seed)
    vals = []
    for _ in range(B):
        i = rng.integers(0, len(y), len(y))
        vals.append(partial_spearman(y[i], p[i], z[i]))
    lo, hi = ci(np.array(vals))
    return point, [lo, hi]


def mw_bands(mw: np.ndarray, n_bands: int = 3) -> List[Tuple[float, float]]:
    qs = np.quantile(mw, np.linspace(0, 1, n_bands + 1))
    qs[0], qs[-1] = -np.inf, np.inf
    return [(float(a), float(b)) for a, b in zip(qs[:-1], qs[1:])]
