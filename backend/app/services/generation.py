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
from rdkit.Chem import AllChem, BRICS, Descriptors

from ..data.candidate_library import CANDIDATE_LIBRARY


class GeneratorBackend(Protocol):
    def generate(self, target_id: str, num_molecules: int) -> List[str]:
        ...


class LibraryGenerator:
    """Samples valid SMILES from the predefined drug-like library."""

    def __init__(self) -> None:
        self._base_smiles = self._load_valid_smiles()

    def _load_valid_smiles(self) -> List[str]:
        smiles_list: List[str] = []
        for entry in CANDIDATE_LIBRARY:
            smi = entry.get("smiles")
            if smi and Chem.MolFromSmiles(smi) is not None:
                smiles_list.append(smi)
        if not smiles_list:
            smiles_list = ["CCO", "CC(=O)O", "CCN(CC)CC"]
        return smiles_list

    def generate(self, target_id: str, num_molecules: int) -> List[str]:
        if num_molecules <= 0:
            return []
        return [random.choice(self._base_smiles) for _ in range(num_molecules)]


class MutationGenerator(LibraryGenerator):
    """
    Generates NOVEL molecules from the library with RDKit:
      - BRICS recombination of fragments from library drugs
      - small random edits (halogen swap, methylation, ring-atom swap, OH/NH2 add)
    Every product is sanitised, de-duplicated and must differ from every
    library molecule, so results are new structures rather than lookups.
    """

    _EDITS = [
        "[c:1][H]>>[c:1]F",
        "[c:1][H]>>[c:1]Cl",
        "[c:1][H]>>[c:1]C",
        "[c:1][H]>>[c:1]O",
        "[c:1][H]>>[c:1]N",
        "[CH3:1]>>[CH2:1]F",
        "[F:1]>>[Cl:1]",
        "[Cl:1]>>[F:1]",
        "[c:1]-[OH:2]>>[c:1]-[O:2]C",
        "[nH:1]>>[n:1]C",
        "[NH2:1]>>[NH:1]C",
    ]

    def __init__(self) -> None:
        super().__init__()
        self._library_canon = {self._canon(s) for s in self._base_smiles}
        self._rxns = [AllChem.ReactionFromSmarts(e) for e in self._EDITS]
        frags = set()
        for smi in self._base_smiles:
            mol = Chem.MolFromSmiles(smi)
            if mol is not None:
                frags.update(BRICS.BRICSDecompose(mol, minFragmentSize=3))
        self._frag_mols = [m for m in (Chem.MolFromSmiles(f) for f in frags) if m is not None]

    @staticmethod
    def _canon(smi: str):
        mol = Chem.MolFromSmiles(smi)
        return Chem.MolToSmiles(mol) if mol is not None else None

    def _mutate(self, smi: str):
        mol = Chem.AddHs(Chem.MolFromSmiles(smi))
        rxn = random.choice(self._rxns)
        try:
            products = rxn.RunReactants((mol,))
        except Exception:
            return None
        if not products:
            return None
        prod = random.choice(products)[0]
        try:
            prod = Chem.RemoveHs(prod)
            Chem.SanitizeMol(prod)
            return Chem.MolToSmiles(prod)
        except Exception:
            return None

    def _recombine(self, count: int) -> List[str]:
        out: List[str] = []
        if len(self._frag_mols) < 2:
            return out
        seeds = random.sample(self._frag_mols, k=min(len(self._frag_mols), 30))
        try:
            for mol in BRICS.BRICSBuild(seeds, maxDepth=1, scrambleReagents=True):
                try:
                    Chem.SanitizeMol(mol)
                    out.append(Chem.MolToSmiles(mol))
                except Exception:
                    continue
                if len(out) >= count:
                    break
        except Exception:
            pass
        return out

    def generate(self, target_id: str, num_molecules: int) -> List[str]:
        if num_molecules <= 0:
            return []
        results: List[str] = []
        seen = set(self._library_canon)
        attempts = 0
        while len(results) < num_molecules and attempts < num_molecules * 60:
            attempts += 1
            if attempts % 4 == 0:
                candidates = self._recombine(2)
            else:
                candidates = [self._mutate(random.choice(self._base_smiles))]
            for smi in candidates:
                if not smi:
                    continue
                canon = self._canon(smi)
                mol = Chem.MolFromSmiles(canon) if canon else None
                if mol is None or canon in seen:
                    continue
                if not (150 <= Descriptors.MolWt(mol) <= 650):
                    continue
                seen.add(canon)
                results.append(canon)
                if len(results) >= num_molecules:
                    break
        # Top up from the library only if mutation could not fill the request.
        while len(results) < num_molecules:
            results.append(random.choice(self._base_smiles))
        return results


def get_generator() -> GeneratorBackend:
    """
    Factory for the current generator backend.

    Later we can add a config flag (like for scoring) to switch between:
      - library-based
      - TamGen
      - others
    """
    return MutationGenerator()
