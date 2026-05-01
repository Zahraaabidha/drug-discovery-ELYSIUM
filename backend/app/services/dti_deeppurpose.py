
#C:\Users\Aabidha\Desktop\PROJECTS\elysium\elysium\backend\app\services\dti_deeppurpose.py
"""
DeepPurpose-based DTI (drug–target interaction) scoring for ELYSIUM.

This uses the DeepPurpose.oneliner.virtual_screening helper with
pretrained models to score a list of SMILES against a single target.
"""

from typing import List
import numpy as np
import pandas as pd

from DeepPurpose import oneliner


class DeepPurposeScreeningModel:
    """
    Lightweight wrapper around DeepPurpose's virtual_screening oneliner.

    Usage:
        model = DeepPurposeScreeningModel()
        scores = model.score(smiles_list, target_seq, target_id="EGFR")
    """

    def score(self, smiles_list: List[str], target_sequence: str, target_id: str) -> List[float]:
        if not smiles_list:
            return []

        # Names to keep mapping stable
        drug_names = [f"elysium_drug_{i}" for i in range(len(smiles_list))]
        target_name = [target_id]

        # DeepPurpose expects list of targets, list of drugs
        # This call uses pretrained models under the hood.
        result = oneliner.virtual_screening(
            [target_sequence],                  # target (list of sequences)
            X_repurpose=smiles_list,           # list of SMILES
            target_name=target_name,
            drug_names=drug_names,
        )

        # Ensure we have a DataFrame
        if isinstance(result, pd.DataFrame):
            df = result
        else:
            df = pd.DataFrame(result)

        if df.empty:
            # Fallback: no predictions
            return [0.0 for _ in smiles_list]

        # Try to detect the score column (name can vary).
        score_col = None

        # Most likely options
        for col in df.columns:
            low = col.lower()
            if "y_pred" in low or "score" in low or "prediction" in low:
                score_col = col
                break

        # If we didn't find by name, grab the first numeric column.
        if score_col is None:
            numeric_cols = df.select_dtypes(include=[np.number]).columns
            if len(numeric_cols) == 0:
                # No numeric columns -> fallback zeros
                return [0.0 for _ in smiles_list]
            score_col = numeric_cols[0]

        # Align scores with our input order using drug_names
        scores_by_name = {
            str(row["drug_name"]) if "drug_name" in df.columns else str(row.get("Drug", name)): row[score_col]
            for name, row in df.iterrows()
        }

        scores: List[float] = []
        for name in drug_names:
            scores.append(float(scores_by_name.get(name, 0.0)))

        return scores
