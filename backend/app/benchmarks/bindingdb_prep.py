"""Prepare a compact, provenance-preserving DTI benchmark dataset from a BindingDB TSV dump.

Nothing here touches the application database, predictions or scoring. Inputs and outputs live outside
the repository (default output: <dataset dir>/derived).

Design (see the manifest written next to the outputs for the exact counts):

* Records: every Ki / Kd / IC50 value for the supported targets, matched by UniProt primary ID of target
  chain 1; compounds matched by the InChIKey of the RDKit-standardised structure. Only exact ("=")
  measurements in nM are kept; inequalities and EC50 are dropped (counted).
* Duplicates: identical (target, compound, type, value, publication) rows - typically the same article
  imported through several channels - are collapsed; all source row IDs are kept in the provenance column.
* Replicates: repeated measurements of one (target, compound, type-group) are aggregated per time window
  (median pValue, n, number of distinct publications, range). Ki and Kd form the primary group "KiKd";
  IC50 is a separate secondary benchmark.
* Time windows use BindingDB's "Date in BindingDB". A record entered on or before CUTOFF is "pre-snapshot".
  CUTOFF is the end of the month of the BindingDB release that DeepPurpose's data helper points to
  (2021m5). That DeepPurpose's pretrained weights were trained on that release is an ASSUMPTION; the
  package does not record training data. Records after the cutoff are therefore labelled
  "no evidence of overlap" - never "unseen".
* Overlap tiers for post-cutoff groups (conservative, based only on pre-cutoff BindingDB content):
    B  compound already measured/recorded for this target before the cutoff  -> excluded from tests
    C  exact structure recorded before the cutoff for another target          -> test, possible overlap
    D  no exact match, but the same 2-D skeleton (InChIKey block 1) recorded  -> test, primary
    E  neither exact structure nor skeleton recorded before the cutoff        -> test, primary + strict
* Splits: temporal (train = pre-cutoff groups; test = tiers C/D/E, with test compounds absent from the
  target's pre-cutoff data) and scaffold (Bemis-Murcko groups inside the pre-cutoff data; whole scaffold
  groups go to one fold). Splitting is by compound, so replicates can never straddle train and test.
"""
from __future__ import annotations

import argparse
import datetime as dt
import gzip
import hashlib
import json
import logging
import math
import platform
import random
import sys
import time
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

import numpy as np
import pandas as pd

from ..services import chem
from ..services.targets import all_targets

log = logging.getLogger(__name__)

SCHEMA_VERSION = 1
PREP_COLUMNS = {
    "BindingDB Reactant_set_id": "rid",
    "Ligand SMILES": "smiles",
    "Ligand InChI Key": "ik_raw",
    "Target Source Organism According to Curator or DataSource": "org",
    "Ki (nM)": "Ki",
    "IC50 (nM)": "IC50",
    "Kd (nM)": "Kd",
    "Curation/DataSource": "src",
    "Article DOI": "doi",
    "PMID": "pmid",
    "Patent Number": "patent",
    "Date of publication": "date_pub",
    "Date in BindingDB": "date_bdb",
    "ChEMBL ID of Ligand": "chembl",
    "UniProt (SwissProt) Primary ID of Target Chain 1": "acc",
}
TYPES = ("Ki", "Kd", "IC50")
# organism the curated target must belong to (substring of BindingDB's organism field); default human
ORGANISM_KEYWORD = {"HIV1_PROTEASE": "immunodeficiency virus"}
DEFAULT_ORGANISM = "Homo sapiens"
ROLE_DEFINITIONS = {
    "train": "records entered on or before the cutoff (pre-snapshot); used for training baselines",
    "test_primary": "entered after the cutoff; exact structure (standardised InChIKey) never recorded before the cutoff for ANY target, "
                    "but its 2-D skeleton was (no exact match). No evidence of overlap - not proof of being unseen",
    "test_strict": "entered after the cutoff; neither exact structure nor 2-D skeleton recorded before the cutoff for any target. "
                   "No evidence of overlap - not proof of being unseen",
    "test_possible_overlap": "entered after the cutoff, but the exact structure was recorded before the cutoff for ANOTHER target; "
                             "kept as a separate test set to quantify possible memorisation",
    "excluded_compound_in_pre_cutoff_data": "compound already recorded for this target before the cutoff -> cannot be a test compound",
    "excluded_noisy_replicates": "replicate measurements disagree by more than max_replicate_range pValue units",
}
GROUP_OF = {"Ki": "KiKd", "Kd": "KiKd", "IC50": "IC50"}


@dataclass
class PrepConfig:
    cutoff: str = "2021-05-31"            # last day assumed covered by the 2021m5 snapshot
    min_value_nm: float = 1e-3            # 1 pM
    max_value_nm: float = 1e7             # 10 mM
    min_heavy_atoms: int = 6
    max_heavy_atoms: int = 120
    max_replicate_range: float = 2.0      # pValue units; wider groups are excluded from test sets
    scaffold_fractions: Tuple[float, float, float] = (0.8, 0.1, 0.1)
    scaffold_seed: int = 20261102
    min_train_compounds: int = 200        # eligibility thresholds (per benchmark and target)
    min_test_compounds: int = 100
    chunksize: int = 40000
    workers: int = 6


# ── helpers ───────────────────────────────────────────────────────────────
def sha256_file(path: Path, block: int = 64 * 1024 * 1024) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            b = f.read(block)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def _std_one(smiles: str):
    try:
        s = chem.standardise(smiles)
        mol = chem.parse(s.canonical_smiles)
        return smiles, (s.inchikey, s.canonical_smiles, int(mol.GetNumHeavyAtoms()),
                        round(float(chem.physchem(s.canonical_smiles).mol_weight), 3),
                        chem.murcko_scaffold(s.canonical_smiles) or "")
    except Exception:
        return smiles, None


def standardise_many(smiles: Iterable[str], workers: int) -> Dict[str, Optional[tuple]]:
    uniq = sorted(set(smiles))
    if workers <= 1 or len(uniq) < 2000:
        return dict(_std_one(s) for s in uniq)
    with ProcessPoolExecutor(max_workers=workers) as ex:
        return dict(ex.map(_std_one, uniq, chunksize=500))


def parse_value(text) -> Optional[Tuple[str, float]]:
    """'12.5' -> ('=', 12.5); '>10000' -> ('>', 10000.0); None if not numeric."""
    if text is None or (isinstance(text, float) and math.isnan(text)):
        return None
    t = str(text).strip()
    rel = "="
    if t[:1] in "<>":
        rel, t = t[0], t[1:].strip()
        if t.startswith("="):
            t = t[1:].strip()
    try:
        v = float(t)
    except ValueError:
        return None
    return (rel, v) if math.isfinite(v) else None


class StageCounter:
    """Counts records per target after every filtering stage (+ 'ALL')."""

    def __init__(self) -> None:
        self.stages: List[str] = []
        self.counts: Dict[str, Dict[str, int]] = {}

    def add(self, stage: str, per_target: Dict[str, int], total: Optional[int] = None) -> None:
        self.stages.append(stage)
        d = dict(per_target)
        d["ALL"] = total if total is not None else int(sum(per_target.values()))
        self.counts[stage] = d

    def as_dict(self) -> Dict:
        return {"stages": self.stages, "counts": self.counts}


def _per_target(df: pd.DataFrame) -> Dict[str, int]:
    return {k: int(v) for k, v in df.groupby("sym").size().items()}


# ── pass 1: stream the whole file ─────────────────────────────────────────
def stream_source(path: Path, cfg: PrepConfig, acc2sym: Dict[str, str]):
    cutoff = pd.Timestamp(cfg.cutoff)
    pre_ik: set = set()
    pre_skel: set = set()
    n_rows = 0
    n_date_unparsed = 0
    min_d, max_d = None, None
    frames: List[pd.DataFrame] = []
    usecols = list(PREP_COLUMNS)
    t0 = time.time()
    for ch in pd.read_csv(path, sep="\t", usecols=usecols, dtype=str, chunksize=cfg.chunksize, quoting=3,
                          low_memory=False, on_bad_lines="error"):
        ch = ch.rename(columns=PREP_COLUMNS)
        n_rows += len(ch)
        d = pd.to_datetime(ch["date_bdb"], format="%m/%d/%Y", errors="coerce")
        n_date_unparsed += int(ch["date_bdb"].notna().sum() - d.notna().sum())
        if d.notna().any():
            lo, hi = d.min(), d.max()
            min_d = lo if min_d is None else min(min_d, lo)
            max_d = hi if max_d is None else max(max_d, hi)
        pre = ch[(d <= cutoff) & ch["ik_raw"].notna()]
        pre_ik.update(pre["ik_raw"])
        pre_skel.update(pre["ik_raw"].str[:14])
        t = ch[ch["acc"].isin(acc2sym)].copy()
        if len(t):
            t["date"] = d[t.index]
            frames.append(t)
        if (n_rows // cfg.chunksize) % 10 == 0:
            log.info("pass 1: %d rows (%.0fs)", n_rows, time.time() - t0)
    tgt = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=list(PREP_COLUMNS.values()) + ["date"])
    return tgt, pre_ik, pre_skel, {"rows": n_rows, "date_unparsed": n_date_unparsed,
                                   "date_bdb_min": str(min_d.date()) if min_d is not None else None,
                                   "date_bdb_max": str(max_d.date()) if max_d is not None else None}


# ── main preparation ──────────────────────────────────────────────────────
def prepare(source: Path, out_dir: Path, cfg: Optional[PrepConfig] = None, compute_sha: bool = True,
            expected_sha256: Optional[str] = None) -> Dict:
    cfg = cfg or PrepConfig()
    out_dir.mkdir(parents=True, exist_ok=True)
    cutoff = pd.Timestamp(cfg.cutoff)
    targets = all_targets()
    acc2sym = {t.uniprot_id: sym for sym, t in targets.items()}
    sc = StageCounter()
    t_start = time.time()

    sha = sha256_file(source) if compute_sha else None
    if expected_sha256 and sha and sha != expected_sha256:
        raise RuntimeError(f"SHA-256 mismatch: expected {expected_sha256}, got {sha}")

    tgt, pre_ik, pre_skel, file_info = stream_source(source, cfg, acc2sym)
    tgt["sym"] = tgt["acc"].map(acc2sym)
    sc.add("s0_rows_in_file", {}, total=file_info["rows"])
    sc.add("s1_rows_matching_supported_target_uniprot", _per_target(tgt))

    kw = tgt["sym"].map(lambda sym: ORGANISM_KEYWORD.get(sym, DEFAULT_ORGANISM))
    human = tgt[[k in (o or "") for k, o in zip(kw, tgt["org"].fillna(""))]].copy()
    sc.add("s2_rows_with_expected_organism", _per_target(human))

    # standardise every distinct structure of the matched rows (also rows without activity values:
    # they are needed to know which compounds were recorded for a target before the cutoff)
    tgt = tgt[tgt["smiles"].notna() & tgt["ik_raw"].notna()].copy()
    std = standardise_many(tgt["smiles"], cfg.workers)
    tgt["std"] = tgt["smiles"].map(std)
    n_invalid_all = int(tgt["std"].isna().sum())
    tgt["ik"] = tgt["std"].map(lambda s: s[0] if s else None)

    # pre-cutoff knowledge per target (ANY value type / relation, incl. EC50 and inequalities)
    pre_rows = tgt[(tgt["date"] <= cutoff) & tgt["ik"].notna()]
    target_pre_ik = {sym: set(g["ik"]) | set(g["ik_raw"]) for sym, g in pre_rows.groupby("sym")}

    human = human.loc[human.index.intersection(tgt.index)]
    valid = tgt.loc[tgt.index.isin(human.index) & tgt["ik"].notna()].copy()
    sc.add("s3_valid_standardised_structure_rows", _per_target(valid))

    # expand into one record per measured value
    recs: List[pd.DataFrame] = []
    for typ in TYPES:
        sub = valid[valid[typ].notna()].copy()
        sub["type"] = typ
        sub["raw_value"] = sub[typ]
        recs.append(sub)
    meas = pd.concat(recs, ignore_index=True)
    sc.add("s4_measurement_records_ki_kd_ic50", _per_target(meas))

    parsed = meas["raw_value"].map(parse_value)
    meas = meas[parsed.notna()].copy()
    parsed = parsed[parsed.notna()]
    meas["relation"] = parsed.map(lambda x: x[0])
    meas["value_nm"] = parsed.map(lambda x: x[1])
    sc.add("s5_parseable_value", _per_target(meas))
    meas = meas[meas["relation"] == "="].copy()
    sc.add("s6_exact_relation_only", _per_target(meas))
    meas = meas[(meas["value_nm"] >= cfg.min_value_nm) & (meas["value_nm"] <= cfg.max_value_nm)].copy()
    sc.add("s7_value_in_range", _per_target(meas))

    meas["ik_std"] = meas["ik"]
    meas["smiles_std"] = meas["std"].map(lambda s: s[1])
    meas["heavy_atoms"] = meas["std"].map(lambda s: s[2])
    meas["mol_weight"] = meas["std"].map(lambda s: s[3])
    meas["scaffold"] = meas["std"].map(lambda s: s[4])
    meas = meas[(meas["heavy_atoms"] >= cfg.min_heavy_atoms) & (meas["heavy_atoms"] <= cfg.max_heavy_atoms)].copy()
    sc.add("s8_heavy_atom_range", _per_target(meas))

    meas["pvalue"] = 9.0 - np.log10(meas["value_nm"])
    meas["bench"] = meas["type"].map(GROUP_OF)
    meas["pubkey"] = meas["pmid"].fillna(meas["doi"]).fillna(meas["patent"])
    meas["pubkey"] = meas["pubkey"].fillna("row:" + meas["rid"].astype(str))

    # exact duplicates (same value reported for the same publication through different channels)
    meas["_vkey"] = meas["value_nm"].map(lambda v: f"{v:.6g}")
    meas = meas.sort_values(["date", "rid"]).reset_index(drop=True)
    dkey = ["sym", "ik_std", "type", "_vkey", "pubkey"]
    meas["dup_count"] = meas.groupby(dkey)["rid"].transform("size")
    meas["merged_rids"] = meas.groupby(dkey)["rid"].transform(lambda s: ";".join(s.astype(str).tolist()[:20]))
    meas["merged_sources"] = meas.groupby(dkey)["src"].transform(lambda s: ";".join(sorted(set(s.fillna("NA")))))
    recs_df = meas.drop_duplicates(dkey, keep="first").copy()
    sc.add("s9_after_exact_duplicate_removal", _per_target(recs_df))
    recs_df["window"] = np.where(recs_df["date"] <= cutoff, "pre", "post")

    keep_cols = ["sym", "acc", "bench", "type", "ik_std", "ik_raw", "smiles_std", "chembl", "relation", "value_nm", "pvalue",
                 "rid", "merged_rids", "dup_count", "merged_sources", "src", "pmid", "doi", "patent", "date_pub", "date",
                 "window", "heavy_atoms", "mol_weight", "scaffold"]
    records_out = recs_df[keep_cols].rename(columns={"sym": "target", "acc": "uniprot", "date": "date_in_bindingdb",
                                                     "ik_std": "inchikey", "smiles_std": "smiles"})
    records_out.to_csv(out_dir / "records.csv.gz", index=False, compression="gzip")

    # ── aggregate replicates per (benchmark, target, compound, window) ───
    def agg(g: pd.DataFrame) -> pd.Series:
        p = g["pvalue"].to_numpy()
        return pd.Series({
            "pvalue": float(np.median(p)), "n_records": len(g), "n_publications": g["pubkey"].nunique(),
            "pvalue_min": float(p.min()), "pvalue_max": float(p.max()), "pvalue_sd": float(p.std()) if len(p) > 1 else 0.0,
            "types": "+".join(sorted(set(g["type"]))), "first_date": g["date"].min().date().isoformat(),
            "last_date": g["date"].max().date().isoformat(),
            "pubs": ";".join(sorted(set(g["pubkey"]))[:10]),
            "sources": ";".join(sorted(set(";".join(g["merged_sources"]).split(";")))),
        })
    gkey = ["bench", "sym", "ik_std", "window"]
    groups = recs_df.groupby(gkey).apply(agg, include_groups=False).reset_index()
    static = recs_df.drop_duplicates("ik_std").set_index("ik_std")[["smiles_std", "heavy_atoms", "mol_weight", "scaffold"]]
    groups = groups.join(static, on="ik_std")
    raw_keys = recs_df.groupby("ik_std")["ik_raw"].agg(lambda s: set(s))
    groups["noisy"] = (groups["pvalue_max"] - groups["pvalue_min"]) > cfg.max_replicate_range

    # ── overlap tiers for post-cutoff groups ──────────────────────────────
    def tier(row) -> str:
        if row["window"] == "pre":
            return "A"
        ik, sym = row["ik_std"], row["sym"]
        raws = raw_keys.get(ik, set())
        if ik in target_pre_ik.get(sym, set()) or (raws & target_pre_ik.get(sym, set())):
            return "B"
        if ik in pre_ik or (raws & pre_ik):
            return "C"
        skel = {ik[:14]} | {r[:14] for r in raws}
        return "D" if skel & pre_skel else "E"
    groups["tier"] = groups.apply(tier, axis=1)
    sc_post = groups[groups["window"] == "post"]
    sc.add("s10_aggregated_groups_post_cutoff", {k: int(v) for k, v in sc_post.groupby("sym").size().items()})

    # compounds that also appear pre-cutoff for the target (any type) cannot be test compounds
    def role(row) -> str:
        if row["window"] == "pre":
            return "train"
        if row["tier"] == "B":
            return "excluded_compound_in_pre_cutoff_data"
        if row["noisy"]:
            return "excluded_noisy_replicates"
        return {"C": "test_possible_overlap", "D": "test_primary", "E": "test_strict"}[row["tier"]]
    groups["temporal_role"] = groups.apply(role, axis=1)

    # scaffold split within pre-cutoff data (per benchmark & target, whole scaffold groups)
    groups["scaffold_split"] = ""
    rng_master = cfg.scaffold_seed
    for (bench, sym), g in groups[groups["window"] == "pre"].groupby(["bench", "sym"]):
        key = np.where(g["scaffold"].fillna("") == "", "acyclic:" + g["ik_std"], g["scaffold"])
        by: Dict[str, List[int]] = defaultdict(list)
        for idx, k in zip(g.index, key):
            by[k].append(idx)
        keys = sorted(by)
        random.Random(f"{rng_master}:{bench}:{sym}").shuffle(keys)
        n = len(g)
        t_train, t_val = cfg.scaffold_fractions[0] * n, (cfg.scaffold_fractions[0] + cfg.scaffold_fractions[1]) * n
        cum = 0
        for k in keys:
            fold = "train" if cum < t_train else ("val" if cum < t_val else "test")
            groups.loc[by[k], "scaffold_split"] = fold
            cum += len(by[k])

    groups.to_csv(out_dir / "groups.csv.gz", index=False, compression="gzip")

    # ── integrity checks ──────────────────────────────────────────────────
    checks = leakage_checks(groups)

    # ── summary / eligibility ─────────────────────────────────────────────
    summary: Dict = {}
    for (bench, sym), g in groups.groupby(["bench", "sym"]):
        tr = g[g["temporal_role"] == "train"]
        roles = g["temporal_role"].value_counts().to_dict()
        n_test_primary = int(roles.get("test_primary", 0) + roles.get("test_strict", 0))
        sp = g[g["window"] == "pre"]["scaffold_split"].value_counts().to_dict()
        summary.setdefault(bench, {})[sym] = {
            "train_compounds": int(len(tr)), "train_records": int(recs_df[(recs_df["bench"] == bench) & (recs_df["sym"] == sym) & (recs_df["window"] == "pre")].shape[0]),
            "test_primary_compounds": n_test_primary, "test_strict_compounds": int(roles.get("test_strict", 0)),
            "test_possible_overlap_compounds": int(roles.get("test_possible_overlap", 0)),
            "excluded_compound_in_pre_cutoff_data": int(roles.get("excluded_compound_in_pre_cutoff_data", 0)),
            "excluded_noisy_replicates": int(roles.get("excluded_noisy_replicates", 0)),
            "post_records_in_primary_test": int(recs_df[(recs_df["bench"] == bench) & (recs_df["sym"] == sym) & (recs_df["window"] == "post")
                                                         & recs_df["ik_std"].isin(g[g["temporal_role"].isin(["test_primary", "test_strict"])]["ik_std"])].shape[0]),
            "scaffold_split_compounds": {k: int(v) for k, v in sp.items()},
            "scaffold_groups": int(g[g["window"] == "pre"]["scaffold"].nunique()),
            "eligible_temporal": bool(len(tr) >= cfg.min_train_compounds and n_test_primary >= cfg.min_test_compounds),
            "eligible_scaffold": bool(sp.get("train", 0) >= cfg.min_train_compounds and sp.get("test", 0) >= 50),
        }

    manifest = {
        "schema_version": SCHEMA_VERSION, "created_utc": dt.datetime.utcnow().isoformat(timespec="seconds"),
        "source": {"path": str(source), "bytes": source.stat().st_size, "sha256": sha, "expected_sha256": expected_sha256, **file_info},
        "config": asdict(cfg),
        "assumptions": [
            f"Snapshot cutoff {cfg.cutoff} approximates the BindingDB 2021m5 release that DeepPurpose's data helper references.",
            "Whether DeepPurpose's pretrained weights used that release, which targets/types and which split is NOT recorded by the package: all overlap labels are 'possible' or 'no evidence', never proof.",
            "'Date in BindingDB' is the date a record was entered; it is not the publication date.",
            "Only the first target chain's UniProt ID is used; multi-chain complexes are matched by that chain only.",
        ],
        "stage_counts": sc.as_dict(), "invalid_structures_all_target_rows": n_invalid_all,
        "unique_compounds": {"records_after_filters": int(recs_df["ik_std"].nunique())},
        "tier_counts_post_groups": {b: {k: int(v) for k, v in g[g["window"] == "post"]["tier"].value_counts().sort_index().items()}
                                    for b, g in groups.groupby("bench")},
        "summary": summary, "leakage_checks": checks, "role_definitions": ROLE_DEFINITIONS,
        "organism_rule": {"default": DEFAULT_ORGANISM, **ORGANISM_KEYWORD},
        "environment": {"python": platform.python_version(), "pandas": pd.__version__, "numpy": np.__version__,
                        "rdkit": _rdkit_version()},
        "runtime_seconds": round(time.time() - t_start, 1),
        "outputs": {"records": "records.csv.gz", "groups": "groups.csv.gz"},
    }
    with open(out_dir / "manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=1, default=int)
    return manifest


def _rdkit_version() -> str:
    try:
        from rdkit import rdBase
        return rdBase.rdkitVersion
    except Exception:  # pragma: no cover
        return "unknown"


def leakage_checks(groups: pd.DataFrame) -> Dict:
    """Hard guarantees that must hold for every (benchmark, target)."""
    res = {"temporal_test_compounds_in_train": 0, "scaffold_groups_in_multiple_folds": 0, "scaffold_test_compounds_in_train": 0,
           "replicate_groups_split_across_windows_roles": 0}
    for (bench, sym), g in groups.groupby(["bench", "sym"]):
        train = set(g[g["temporal_role"] == "train"]["ik_std"])
        test = set(g[g["temporal_role"].isin(["test_primary", "test_strict", "test_possible_overlap"])]["ik_std"])
        res["temporal_test_compounds_in_train"] += len(train & test)
        pre = g[g["window"] == "pre"]
        folds = pre.groupby(pre["scaffold"].where(pre["scaffold"] != "", "acyclic:" + pre["ik_std"]))["scaffold_split"].nunique()
        res["scaffold_groups_in_multiple_folds"] += int((folds > 1).sum())
        s_train = set(pre[pre["scaffold_split"] == "train"]["ik_std"]); s_test = set(pre[pre["scaffold_split"] == "test"]["ik_std"])
        res["scaffold_test_compounds_in_train"] += len(s_train & s_test)
        res["replicate_groups_split_across_windows_roles"] += int(g.duplicated(["ik_std", "window"]).sum())
    res["passed"] = all(v == 0 for k, v in res.items())
    return res


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--source", required=True, type=Path)
    ap.add_argument("--out", type=Path, help="default: <source dir>/derived")
    ap.add_argument("--expected-sha256")
    ap.add_argument("--cutoff", default=PrepConfig.cutoff)
    ap.add_argument("--workers", type=int, default=PrepConfig.workers)
    a = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    cfg = PrepConfig(cutoff=a.cutoff, workers=a.workers)
    m = prepare(a.source, a.out or a.source.parent / "derived", cfg, expected_sha256=a.expected_sha256)
    print(json.dumps({"summary": m["summary"], "leakage_checks": m["leakage_checks"]}, indent=1))


if __name__ == "__main__":
    main()
