"""Research evaluation: generation quality, similarity retrieval and DTI prediction.

Every evaluation records its parameters, the dataset it used and its limitations, and is stored
in the `evaluation_reports` table so results can be reproduced and audited. These are SANITY
and PERFORMANCE checks on specific, documented data - they are not claims of real-world
effectiveness.
"""
from __future__ import annotations

import logging
import random
import statistics
from typing import Dict, List, Optional

import numpy as np
from rdkit import DataStructs
from rdkit.Chem import QED
from sqlalchemy.orm import Session

from .. import models as m
from . import chem
from .generation import MutationGenerator
from .scoring import get_scorer
from .similarity_index import index as similarity_index
from .targets import resolve_target

log = logging.getLogger(__name__)


class EvaluationError(RuntimeError):
    pass


def _save(db: Session, kind: str, parameters: Dict, dataset: Dict, metrics: Dict, limitations: str) -> m.EvaluationReport:
    rep = m.EvaluationReport(kind=kind, parameters=parameters, dataset=dataset, metrics=metrics, limitations=limitations)
    db.add(rep)
    db.commit()
    db.refresh(rep)
    return rep


def _dist(values: List[float]) -> Dict:
    if not values:
        return {"n": 0}
    return {"n": len(values), "mean": float(np.mean(values)), "std": float(np.std(values)),
            "min": float(np.min(values)), "max": float(np.max(values))}


def _internal_diversity(smiles: List[str]) -> Optional[float]:
    fps = [chem.morgan_fp(s) for s in smiles]
    fps = [f for f in fps if f is not None]
    if len(fps) < 2:
        return None
    sims = []
    for i in range(len(fps)):
        sims.extend(DataStructs.BulkTanimotoSimilarity(fps[i], fps[i + 1:]))
    return float(1.0 - np.mean(sims))


# ── 1. generation ─────────────────────────────────────────────────────────
def evaluate_generation(db: Session, num_molecules: int = 100, seed: int = 0) -> m.EvaluationReport:
    seeds = [s for (s,) in db.query(m.Compound.canonical_smiles)
             .filter(m.Compound.origin.in_([m.ORIGIN_REFERENCE, m.ORIGIN_EXTERNAL])).all()]
    if len(seeds) < 5:
        raise EvaluationError("Registry has fewer than 5 reference/external compounds; import reference data first.")
    known = {ik for (ik,) in db.query(m.Compound.inchikey).all()}
    gen = MutationGenerator(seeds[:400]).generate("eval", num_molecules, seed=seed, known_inchikeys=known)
    qeds, mws, logps = [], [], []
    for s in gen.smiles:
        pc = chem.physchem(s)
        mws.append(pc.mol_weight)
        logps.append(pc.logp)
        try:
            qeds.append(QED.qed(chem.parse(s)))
        except Exception:
            pass
    ref = [chem.physchem(s) for s in seeds[:400]]
    metrics = {
        **{k: v for k, v in gen.stats.as_dict().items() if k in (
            "requested", "attempted", "valid", "unique", "novel", "returned", "validity", "uniqueness", "novelty", "exhausted")},
        "internal_diversity_1_minus_mean_tanimoto": _internal_diversity(gen.smiles),
        "generated_properties": {"mol_weight": _dist(mws), "logp": _dist(logps), "qed": _dist(qeds)},
        "seed_set_properties": {"mol_weight": _dist([p.mol_weight for p in ref]), "logp": _dist([p.logp for p in ref])},
    }
    return _save(
        db, "generation", {"num_molecules": num_molecules, "seed": seed, "method": gen.stats.method},
        {"seed_compounds": len(seeds[:400]), "novelty_reference_set": len(known), "novelty_reference": "all registry compounds (InChIKey)"},
        metrics,
        "Validity counts candidate strings that RDKit can standardise. Novelty is relative to the compounds in THIS registry "
        "only (not all known chemistry). Property distributions describe the molecules, not their activity or synthesisability. "
        "QED is a drug-likeness heuristic.",
    )


# ── 2. similarity retrieval ───────────────────────────────────────────────
def evaluate_similarity(db: Session, n_queries: int = 50, k: int = 10, seed: int = 0, with_embeddings: bool = False) -> m.EvaluationReport:
    similarity_index.rebuild(db, with_embeddings=with_embeddings)
    if similarity_index.size < k + 2:
        raise EvaluationError(f"Registry has only {similarity_index.size} compounds; need more than k+1={k + 1}.")
    rng = random.Random(seed)
    comps = db.query(m.Compound).all()
    queries = rng.sample(comps, min(n_queries, len(comps)))

    recalls, identity_hits, identity_total, emb_hits = [], 0, 0, 0
    for c in queries:
        exact = {n.compound_id for n in similarity_index.exact_tanimoto(c.canonical_smiles, k, exclude_id=c.id)}
        approx = {n.compound_id for n in similarity_index.search_fingerprint(c.canonical_smiles, k, exclude_id=c.id)}
        recalls.append(len(exact & approx) / k)
        alt = chem.randomised_smiles(c.canonical_smiles, rng)
        if alt:
            identity_total += 1
            top = similarity_index.search_fingerprint(alt, 5)
            # tie-aware: stereoisomers share a Morgan fingerprint, so any compound tied at the top similarity counts
            identity_hits += int(bool(top) and top[0].similarity > 0.9999 and
                                 c.id in {n.compound_id for n in top if abs(n.similarity - top[0].similarity) < 1e-9})
            if with_embeddings:
                top_e = similarity_index.search_embedding(alt, 1)
                emb_hits += int(bool(top_e) and top_e[0].compound_id == c.id)
    metrics = {
        "faiss_vs_exact_tanimoto_recall_at_k": float(np.mean(recalls)),
        "fingerprint_identity_retrieval_under_smiles_randomisation": identity_hits / identity_total if identity_total else None,
        "n_queries": len(queries), "k": k,
    }
    if with_embeddings:
        metrics["embedding_identity_top1_under_smiles_randomisation_raw_query"] = emb_hits / identity_total if identity_total else None
    return _save(
        db, "similarity", {"n_queries": n_queries, "k": k, "seed": seed, "with_embeddings": with_embeddings},
        {"registry_compounds": similarity_index.size, "queries": "random registry compounds (self excluded)"},
        metrics,
        "Recall@k measures how well the FAISS binary-index + Tanimoto re-rank approximates exact brute-force Tanimoto search "
        "(approximation fidelity). Identity retrieval with a re-written SMILES string is a sanity check that the pipeline is "
        "invariant to SMILES notation (ties between stereoisomers sharing a fingerprint count as hits). The embedding variant queries ChemBERTa with the re-written string WITHOUT canonicalising it, so it measures how sensitive the language model is to SMILES notation (the API canonicalises queries before embedding). Neither metric shows that similar compounds share biological activity.",
    )


# ── 3. DTI prediction vs. measured activity ───────────────────────────────
def evaluate_dti(db: Session, target_id: str, max_compounds: int = 200, standard_types=("Ki", "Kd")) -> m.EvaluationReport:
    from scipy.stats import pearsonr, spearmanr

    target = resolve_target(target_id)
    rows = (db.query(m.Bioactivity, m.Compound).join(m.Compound, m.Bioactivity.compound_id == m.Compound.id)
            .filter(m.Bioactivity.target_symbol == target.symbol, m.Bioactivity.standard_type.in_(list(standard_types)),
                    m.Bioactivity.relation == "=").all())
    per_compound: Dict[int, List[float]] = {}
    smiles_of: Dict[int, str] = {}
    sources: Dict[int, set] = {}
    for act, comp in rows:
        per_compound.setdefault(comp.id, []).append(act.pvalue)
        smiles_of[comp.id] = comp.canonical_smiles
        sources.setdefault(comp.id, set()).add(act.source_db)
    ids = sorted(per_compound)[:max_compounds]
    if len(ids) < 10:
        raise EvaluationError(
            f"Only {len(ids)} compounds with exact Ki/Kd measurements for {target.symbol} in the registry; "
            "import experimental data first (POST /library/import/target). At least 10 are required.")

    scorer = get_scorer()
    preds = scorer.predict([smiles_of[i] for i in ids], target.sequence, target.symbol)
    y_true = np.array([float(np.median(per_compound[i])) for i in ids])
    y_pred = np.array([p.pkd for p in preds])
    rho = spearmanr(y_pred, y_true)
    r = pearsonr(y_pred, y_true)
    rmse = float(np.sqrt(np.mean((y_pred - y_true) ** 2)))
    baseline = float(np.sqrt(np.mean((y_true.mean() - y_true) ** 2)))
    metrics = {
        "n_compounds": len(ids), "spearman_rho": float(rho.statistic), "spearman_p": float(rho.pvalue),
        "pearson_r": float(r.statistic), "rmse_pkd": rmse, "rmse_mean_baseline_pkd": baseline,
        "measured_pkd": _dist(list(y_true)), "predicted_pkd": _dist(list(y_pred)),
    }
    return _save(
        db, "dti", {"target": target.symbol, "max_compounds": max_compounds, "standard_types": list(standard_types)},
        {"target_uniprot": target.uniprot_id, "measurements": "exact (=) Ki/Kd from registry bioactivities (ChEMBL/BindingDB)",
         "source_dbs": sorted({s for i in ids for s in sources[i]}), "model": scorer.model_info()},
        metrics,
        "DeepPurpose's pretrained weights were trained on BindingDB, which overlaps with the public measurements used here, so "
        "these numbers are OPTIMISTIC (train/test leakage) and must not be read as prospective accuracy. Measurements come from "
        "different assays and labs (median taken per compound). pKd predicted by the model is compared with pKi/pKd measured. "
        "A prospective, time- or scaffold-split benchmark on data absent from BindingDB is required for any accuracy claim.",
    )
