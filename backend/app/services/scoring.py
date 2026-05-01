#C:\Users\Aabidha\Desktop\PROJECTS\elysium\elysium\backend\app\services\scoring.py
"""
Scoring backends for ELYSIUM.

We define a common interface for "score(drugs, target)" and provide:
  - StubScorer        -> always works, deterministic fake scores.
  - DeepPurposeScorer -> real DTI scoring using DeepPurpose (if available).
"""

from typing import List, Protocol

from ..core.config import SCORER_BACKEND


class ScoringBackend(Protocol):
    def score(self, smiles_list: List[str], target_sequence: str, target_id: str) -> List[float]:
        ...


class StubScorer:
    """Deterministic scoring stub."""

    def score(self, smiles_list: List[str], target_sequence: str, target_id: str) -> List[float]:
        base = 1.0
        step = 0.05
        scores: List[float] = []
        for i, _ in enumerate(smiles_list):
            s = base - step * i
            if s < 0:
                s = 0.0
            scores.append(s)
        return scores


class DeepPurposeScorer:
    """
    Wraps DeepPurpose in a safe way.
    If anything fails during import or prediction, it falls back to StubScorer.
    """

    def __init__(self) -> None:
        self._stub = StubScorer()
        self._model = None
        self._available = self._try_init_model()

    def _try_init_model(self) -> bool:
        try:
            # Lazy import so the rest of ELYSIUM doesn't depend on DeepPurpose.
            from DeepPurpose import oneliner  # type: ignore[attr-defined]

            self._oneliner = oneliner
            return True
        except Exception as e:
            # You can add proper logging here instead of print.
            print("[DeepPurposeScorer] Failed to import DeepPurpose, using stub instead:", e)
            return False

    def score(self, smiles_list: List[str], target_sequence: str, target_id: str) -> List[float]:
        # If DeepPurpose is not available, use stub.
        if not self._available:
            return self._stub.score(smiles_list, target_sequence, target_id)

        if not smiles_list:
            return []

        try:
            # Minimal usage via oneliner.virtual_screening.
            drug_names = [f"elysium_drug_{i}" for i in range(len(smiles_list))]
            target_name = [target_id]

            result = self._oneliner.virtual_screening(
                [target_sequence],
                X_repurpose=smiles_list,
                target_name=target_name,
                drug_names=drug_names,
            )

            # Import here to avoid top-level dependency if DeepPurpose isn't installed.
            import pandas as pd  # type: ignore
            import numpy as np   # type: ignore

            if isinstance(result, pd.DataFrame):
                df = result
            else:
                df = pd.DataFrame(result)

            if df.empty:
                return self._stub.score(smiles_list, target_sequence, target_id)

            # Heuristic: find score column.
            score_col = None
            for col in df.columns:
                low = col.lower()
                if "y_pred" in low or "score" in low or "prediction" in low:
                    score_col = col
                    break

            if score_col is None:
                numeric_cols = df.select_dtypes(include=[np.number]).columns
                if len(numeric_cols) == 0:
                    return self._stub.score(smiles_list, target_sequence, target_id)
                score_col = numeric_cols[0]

            # Build mapping from drug name to score.
            scores_by_name = {}
            for _, row in df.iterrows():
                name = row.get("drug_name") or row.get("Drug")
                if name is None:
                    continue
                scores_by_name[str(name)] = float(row[score_col])

            scores: List[float] = []
            for name in drug_names:
                scores.append(scores_by_name.get(name, 0.0))

            return scores

        except Exception as e:
            # If anything goes wrong in DeepPurpose, fall back and don't crash the API.
            print("[DeepPurposeScorer] Error during scoring, falling back to stub:", e)
            return self._stub.score(smiles_list, target_sequence, target_id)


def get_scorer() -> ScoringBackend:
    """
    Factory that returns the configured scoring backend.
    If SCORER_BACKEND is "deeppurpose", we *try* DeepPurpose but
    still fall back to stub if unavailable.
    """
    if SCORER_BACKEND.lower() == "deeppurpose":
        return DeepPurposeScorer()
    return StubScorer()
