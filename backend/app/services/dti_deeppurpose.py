"""
DeepPurpose-based DTI (drug-target interaction) scoring for ELYSIUM.

Wraps DeepPurpose.oneliner.virtual_screening with the pretrained BindingDB
ensemble. The oneliner returns None and writes its results to disk, and it
expects numpy arrays of equal length for drugs / targets (one row per pair),
so we build the pairs ourselves and read the aggregated predictions back
from the pickle it writes into a private temp directory.
"""

import os
import pickle
import shutil
import tempfile
from pathlib import Path
from typing import List

import numpy as np

BACKEND_DIR = Path(__file__).resolve().parents[2]
PRETRAINED_DIR = BACKEND_DIR / "save_folder" / "pretrained_models" / "DeepPurpose_BindingDB"


def kd_nm_to_score(kd_nm: float) -> float:
    """Convert a predicted Kd (nM) to a 0-1 score via pKd (pKd 10 -> 1.0)."""
    kd_nm = max(float(kd_nm), 1e-6)
    pkd = 9.0 - np.log10(kd_nm)
    return float(min(max(pkd / 10.0, 0.0), 1.0))


class DeepPurposeScreeningModel:
    def score(self, smiles_list: List[str], target_sequence: str, target_id: str) -> List[float]:
        if not smiles_list:
            return []

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

        if len(kd) != n:
            raise RuntimeError(f"DeepPurpose returned {len(kd)} predictions for {n} molecules")
        return [kd_nm_to_score(v) for v in kd]
