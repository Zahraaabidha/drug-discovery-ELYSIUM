"""
Basic config & helpers for ELYSIUM.
Later we can extend this with env-based configuration.
"""

from typing import Dict


# ---- Target sequences (still small hardcoded map) ----

_TARGET_SEQUENCES: Dict[str, str] = {
    "EGFR": "MRPSGTAGAALLALLAALCPASRALEEKKVCQGTSNKLTQLGTF...",   # demo / truncated
    "DRD2": "MDSKGPLNVSFKREEVARRMVIAVTRTAVLAVGALIGNSLVVSV...",   # demo / truncated
    "FAKE_TARGET": "MSTNPKPQRITSAFLLQLLGLSLGCLPAESRA...",        # fallback
}


def resolve_target_sequence(target_id: str) -> str:
    """
    Resolve a target_id to an amino acid sequence string.

    For now this is a simple dict lookup with a fallback.
    Later we will plug in a real database / KG.
    """
    return _TARGET_SEQUENCES.get(target_id, _TARGET_SEQUENCES["FAKE_TARGET"])


# ---- Scoring backend selection ----

# For now we hardcode the scorer type here.
# Options:
#   "stub"         -> Use simple deterministic scores (always works)
#   "deeppurpose"  -> Try DeepPurpose; fall back to stub if it fails
SCORER_BACKEND: str = "deeppurpose"  # you can change this to "stub" if needed
