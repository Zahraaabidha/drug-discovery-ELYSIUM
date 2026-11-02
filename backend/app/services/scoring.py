"""Drug-target interaction scoring backends.

There is intentionally NO stub/placeholder scorer: a failed prediction raises
ScoringError instead of returning fabricated numbers.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import List, Protocol

from ..core.config import SCORER_BACKEND

log = logging.getLogger(__name__)


class ScoringError(RuntimeError):
    """The DTI model could not produce predictions."""


@dataclass(frozen=True)
class DTIResult:
    smiles: str
    kd_nm: float          # predicted dissociation constant, nM (lower = stronger predicted binding)
    pkd: float            # 9 - log10(Kd nM)
    normalised: float     # pKd / 10 clipped to [0, 1]; display convenience only


class ScoringBackend(Protocol):
    name: str

    def model_info(self) -> dict: ...

    def predict(self, smiles_list: List[str], target_sequence: str, target_id: str) -> List[DTIResult]: ...


class DeepPurposeScorer:
    name = "DeepPurposeScorer"

    def __init__(self) -> None:
        from .dti_deeppurpose import DeepPurposeScreeningModel
        self._model = DeepPurposeScreeningModel()

    def model_info(self) -> dict:
        return self._model.model_info()

    def predict(self, smiles_list: List[str], target_sequence: str, target_id: str) -> List[DTIResult]:
        if not smiles_list:
            return []
        try:
            return self._model.predict(smiles_list, target_sequence, target_id)
        except Exception as exc:
            log.exception("DeepPurpose prediction failed")
            raise ScoringError(f"DeepPurpose prediction failed: {exc}") from exc


_scorer: ScoringBackend | None = None


def get_scorer() -> ScoringBackend:
    global _scorer
    if _scorer is None:
        if SCORER_BACKEND.lower() != "deeppurpose":
            raise ScoringError(f"Unsupported SCORER_BACKEND {SCORER_BACKEND!r}")
        _scorer = DeepPurposeScorer()
    return _scorer


def set_scorer(scorer: ScoringBackend | None) -> None:
    """Dependency injection hook (used by tests to supply an explicit test double)."""
    global _scorer
    _scorer = scorer
