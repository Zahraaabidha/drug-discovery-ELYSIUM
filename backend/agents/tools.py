# backend/agents/tools.py

from discovery import run_discovery
from scoring import score_molecules_batch

def generate_molecules(target_id: str, num_molecules: int = 10):
    """
    Calls the existing discovery pipeline.
    """
    return run_discovery(
        target_id=target_id,
        num_molecules=num_molecules
    )

def score_molecules(molecules: list):
    """
    Calls the existing scoring pipeline.
    """
    return score_molecules_batch(molecules)
