#C:\Users\Aabidha\Desktop\PROJECTS\elysium\elysium\backend\app\services\generation.py
"""
Molecule generation backends for ELYSIUM.

We define a common interface:
    generate(target_id, num_molecules) -> List[SMILES]

For now we provide:
  - LibraryGenerator: samples from a small drug-like library.

Later you can add:
  - TamGenGenerator: wraps TamGen or other Transformer.
  - HybridGenerator: library + mutation, etc.
"""

from typing import List, Protocol
import random

from rdkit import Chem

from ..data.candidate_library import CANDIDATE_LIBRARY


class GeneratorBackend(Protocol):
    def generate(self, target_id: str, num_molecules: int) -> List[str]:
        ...


class LibraryGenerator:
    """
    Simple generator that samples valid SMILES from a predefined library.

    This is NOT target-conditional yet; target_id is accepted so that
    we can easily switch to a target-conditioned generator later.
    """

    def __init__(self) -> None:
        self._base_smiles = self._load_valid_smiles()

    def _load_valid_smiles(self) -> List[str]:
        smiles_list: List[str] = []
        for entry in CANDIDATE_LIBRARY:
            smi = entry.get("smiles")
            if not smi:
                continue
            mol = Chem.MolFromSmiles(smi)
            if mol is not None:
                smiles_list.append(smi)
        if not smiles_list:
            # Fallback to a couple of very simple molecules
            smiles_list = ["CCO", "CC(=O)O", "CCN(CC)CC"]
        return smiles_list

    def generate(self, target_id: str, num_molecules: int) -> List[str]:
        if num_molecules <= 0:
            return []
        # Sample with replacement to allow any requested size.
        return [random.choice(self._base_smiles) for _ in range(num_molecules)]


def get_generator() -> GeneratorBackend:
    """
    Factory for the current generator backend.

    Later we can add a config flag (like for scoring) to switch between:
      - library-based
      - TamGen
      - others
    """
    return LibraryGenerator()
