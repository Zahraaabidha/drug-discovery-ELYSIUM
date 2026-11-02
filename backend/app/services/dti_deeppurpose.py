"""DeepPurpose DTI prediction (pretrained BindingDB ensemble).

DeepPurpose's oneliner returns None, writes results to disk and needs numpy arrays
with one row per drug-target pair, so predictions are read back from the pickle it
writes into a private temp directory. Output is the ensemble-mean predicted Kd in nM.
"""
from __future__ import annotations

import logging
import math
import os
import pickle
import shutil
import tempfile
from pathlib import Path
from typing import List

import numpy as np

from .scoring import DTIResult

log = logging.getLogger(__name__)

BACKEND_DIR = Path(__file__).resolve().parents[2]
PRETRAINED_DIR = Path(os.getenv("DEEPPURPOSE_MODEL_DIR", BACKEND_DIR / "save_folder" / "pretrained_models" / "DeepPurpose_BindingDB"))
MODEL_NAME = "DeepPurpose BindingDB pretrained ensemble (mean of members)"


def kd_to_result(smiles: str, kd_nm: float) -> DTIResult:
    kd_nm = max(float(kd_nm), 1e-6)
    pkd = 9.0 - math.log10(kd_nm)
    return DTIResult(smiles=smiles, kd_nm=kd_nm, pkd=pkd, normalised=float(min(max(pkd / 10.0, 0.0), 1.0)))


class DeepPurposeScreeningModel:
    def model_info(self) -> dict:
        try:
            import DeepPurpose  # noqa: F401
            from importlib.metadata import version
            dp_version = version("DeepPurpose")
        except Exception:
            dp_version = None
        members = sorted(p.name for p in PRETRAINED_DIR.glob("model_*")) if PRETRAINED_DIR.exists() else []
        return {
            "model_name": MODEL_NAME,
            "model_version": dp_version,
            "members": members,
            "aggregation": "mean",
            "output": "predicted Kd (nM)",
            "training_data": "BindingDB (pretrained weights distributed with DeepPurpose)",
        }

    def predict(self, smiles_list: List[str], target_sequence: str, target_id: str) -> List[DTIResult]:
        if not smiles_list:
            return []
        if not PRETRAINED_DIR.exists():
            raise FileNotFoundError(
                f"DeepPurpose pretrained models not found at {PRETRAINED_DIR}. "
                "Set DEEPPURPOSE_MODEL_DIR or download them (see README)."
            )
        from DeepPurpose import oneliner

        n = len(smiles_list)
        tmp = tempfile.mkdtemp(prefix="elysium_dp_")
        try:
            oneliner.virtual_screening(
                np.array([target_sequence] * n, dtype=object),
                X_repurpose=np.array(smiles_list, dtype=object),
                target_name=[target_id] * n,
                drug_names=[f"drug_{i}" for i in range(n)],
                save_dir=tmp,
                pretrained_dir=str(PRETRAINED_DIR),
                agg="mean",
                convert_y=True,
            )
            with open(os.path.join(tmp, "results_aggregation", "logits_VS_mean.pkl"), "rb") as f:
                kd = np.asarray(pickle.load(f), dtype=float).reshape(-1)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

        if len(kd) != n or not np.all(np.isfinite(kd)):
            raise RuntimeError(f"DeepPurpose returned {len(kd)} predictions for {n} molecules (or non-finite values)")
        return [kd_to_result(s, v) for s, v in zip(smiles_list, kd)]
