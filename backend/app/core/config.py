"""
Basic config & helpers for ELYSIUM.
Later we can extend this with env-based configuration.
"""

from typing import Dict


# ---- Target sequences (real UniProt sequences in app/data/target_sequences.json) ----

import json
from pathlib import Path

_SEQ_FILE = Path(__file__).resolve().parents[1] / "data" / "target_sequences.json"
_TARGETS: Dict[str, Dict[str, str]] = json.loads(_SEQ_FILE.read_text())
_FALLBACK_TARGET = "EGFR"


def known_targets() -> Dict[str, Dict[str, str]]:
    return _TARGETS


def resolve_target_sequence(target_id: str) -> str:
    """Resolve a target_id (e.g. EGFR) to its amino acid sequence."""
    entry = _TARGETS.get(target_id.upper())
    if entry is None:
        print(f"[config] Unknown target '{target_id}', using {_FALLBACK_TARGET} sequence")
        entry = _TARGETS[_FALLBACK_TARGET]
    return entry["sequence"]


# ---- Scoring backend selection ----

# For now we hardcode the scorer type here.
# Options:
#   "stub"         -> Use simple deterministic scores (always works)
#   "deeppurpose"  -> Try DeepPurpose; fall back to stub if it fails
SCORER_BACKEND: str = "deeppurpose"  # you can change this to "stub" if needed
