"""
Basic config & helpers for ELYSIUM.
Later we can extend this with env-based configuration.
"""

from typing import Dict


# ---- Target sequences (real UniProt sequences in app/data/target_sequences.json) ----

def known_targets() -> Dict[str, Dict[str, str]]:
    """Supported targets as {symbol: {uniprot_id, sequence}} (see services/targets.py)."""
    from ..services.targets import all_targets
    return {k: {"uniprot_id": t.uniprot_id, "sequence": t.sequence} for k, t in all_targets().items()}


def resolve_target_sequence(target_id: str) -> str:
    """Resolve a target to its sequence. Raises UnsupportedTarget (no silent substitution)."""
    from ..services.targets import resolve_target
    return resolve_target(target_id).sequence


# ---- Scoring backend ----
# Only "deeppurpose" is supported. There is deliberately no placeholder scorer:
# if DeepPurpose cannot produce a prediction the request fails with an error.
SCORER_BACKEND: str = "deeppurpose"
