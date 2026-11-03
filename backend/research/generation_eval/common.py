"""Shared helpers for the research-only generation evaluation (no writes to production code, DB or frozen benchmarks)."""
from __future__ import annotations

import json
import os
import shutil
import sqlite3
import sys
import tempfile
from pathlib import Path
from typing import List

import pandas as pd
from rdkit import RDLogger
from rdkit.Chem import QED, RDConfig, rdMolDescriptors
from rdkit.Chem.FilterCatalog import FilterCatalog, FilterCatalogParams

os.environ.setdefault("DATABASE_URL", "sqlite:///" + (Path(tempfile.mkdtemp(prefix="geneval_")) / "unused.db").as_posix())
os.environ.setdefault("ELYSIUM_DISABLE_ARANGO", "1")

from app.benchmarks import dti_benchmark as B  # noqa: E402
from app.services import chem  # noqa: E402

RDLogger.DisableLog("rdApp.*")
sys.path.append(os.path.join(RDConfig.RDContribDir, "SA_Score"))
import sascorer  # noqa: E402  (RDKit Contrib; Ertl & Schuffenhauer SA score; a heuristic)

FROZEN = Path(r"C:\ResearchDatasets\BindingDB\derived\benchmark_runs\dti-20261102-183553")
DB_PATH = Path(__file__).resolve().parents[2] / "elysium.db"
OUT_ROOT = Path(r"C:\ResearchDatasets\BindingDB\derived\generation_experiments")
TARGETS = ["EGFR", "DRD2"]
BENCHES = {"EGFR": ["IC50", "KiKd"], "DRD2": ["KiKd", "IC50"]}      # first = primary benchmark for that target; benchmarks are never pooled
CONDITIONS = ["A", "B"]
SEEDS = [20261104, 20261105, 20261106, 20261107, 20261108]
N_REQUESTED = 1000
POTENT, WEAK = 7.0, 6.0                                              # exploratory labels: pValue >= 7 "potent", < 6 "weak"
MAX_SEED_COMPOUNDS = 400                                              # same cap as app.services.discovery


def load_cfg_groups():
    res = json.loads((FROZEN / "results.json").read_text(encoding="utf-8"))
    cfg = B.BenchConfig(**{k: (tuple(v) if isinstance(v, list) else v) for k, v in res["config"].items()})
    return cfg, pd.read_csv(Path(cfg.derived_dir) / "groups.csv.gz", low_memory=False)


def registry_snapshot():
    """Read-only copy of the registry: seed SMILES exactly as discovery selects them, and every known InChIKey."""
    tmp = Path(tempfile.mkdtemp(prefix="geneval_db_")) / "copy.db"
    shutil.copyfile(DB_PATH, tmp)
    c = sqlite3.connect(f"file:{tmp.as_posix()}?mode=ro", uri=True)
    seeds = [r[0] for r in c.execute("select canonical_smiles from compounds where origin in ('reference','external') order by id limit ?", (MAX_SEED_COMPOUNDS,))]
    keys = {r[0] for r in c.execute("select inchikey from compounds")}
    origins = dict(c.execute("select origin,count(*) from compounds group by origin").fetchall())
    c.close()
    return seeds, keys, origins


def target_frames(cfg, groups, tgt):
    """Per benchmark: pre-cutoff training frame and temporal test_primary frame. Ki/Kd and IC50 stay separate."""
    out = {}
    for bench in BENCHES[tgt]:
        train, _, _, evals, _ = B.build_sets(groups, bench, tgt, cfg)
        out[bench] = {"train": train, "test_primary": evals.get("test_primary", train.iloc[0:0])}
    return out


# ── per-molecule quality (computed descriptors and heuristic scores; NOT experimental) ──
_catalogs = {}
for _nm, _e in (("pains", FilterCatalogParams.FilterCatalogs.PAINS), ("brenk", FilterCatalogParams.FilterCatalogs.BRENK), ("nih", FilterCatalogParams.FilterCatalogs.NIH)):
    _p = FilterCatalogParams()
    _p.AddCatalog(_e)
    _catalogs[_nm] = FilterCatalog(_p)


def mol_quality(smiles: List[str]) -> pd.DataFrame:
    rows = []
    for s in smiles:
        mol = chem.parse(s)
        pc = chem.physchem(s)
        rows.append({
            "smiles": s, "mw": pc.mol_weight, "logp": pc.logp, "tpsa": pc.tpsa, "hbd": pc.hbd, "hba": pc.hba, "rotb": pc.rotatable_bonds,
            "heavy": pc.heavy_atoms, "rings": pc.ring_count, "lipinski_pass": int(pc.lipinski_pass),
            "veber_pass": int(pc.rotatable_bonds <= 10 and pc.tpsa <= 140), "fsp3": rdMolDescriptors.CalcFractionCSP3(mol),
            "qed": QED.qed(mol), "sa_score": sascorer.calculateScore(mol),
            "pains": int(_catalogs["pains"].HasMatch(mol)), "brenk": int(_catalogs["brenk"].HasMatch(mol)), "nih": int(_catalogs["nih"].HasMatch(mol)),
            "n_brenk": len(_catalogs["brenk"].GetMatches(mol))})
    return pd.DataFrame(rows)
