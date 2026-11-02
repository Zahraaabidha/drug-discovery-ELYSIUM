"""RDKit chemistry helpers: standardisation, validation, descriptors, fingerprints.

Descriptors computed here are basic physicochemical properties and a Lipinski
rule-of-five check. They are NOT ADMET predictions.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Sequence

import numpy as np
from rdkit import Chem, DataStructs, RDLogger
from rdkit.Chem import Crippen, Descriptors, Lipinski, rdMolDescriptors
from rdkit.Chem.MolStandardize import rdMolStandardize

RDLogger.DisableLog("rdApp.*")
log = logging.getLogger(__name__)

FP_RADIUS = 2
FP_BITS = 2048


class InvalidMolecule(ValueError):
    """Raised when a SMILES cannot be parsed / standardised."""


@dataclass
class StandardisedMolecule:
    canonical_smiles: str
    inchikey: str
    formula: str
    original_smiles: str


@dataclass
class PhysChem:
    mol_weight: float
    logp: float
    tpsa: float
    hbd: int
    hba: int
    rotatable_bonds: int
    heavy_atoms: int
    ring_count: int
    lipinski_violations: int
    lipinski_pass: bool

    def as_dict(self) -> Dict:
        return asdict(self)


_largest_fragment = rdMolStandardize.LargestFragmentChooser()
_uncharger = rdMolStandardize.Uncharger()


def parse(smiles: str) -> Optional[Chem.Mol]:
    if not smiles or not isinstance(smiles, str):
        return None
    return Chem.MolFromSmiles(smiles.strip())


def is_valid(smiles: str) -> bool:
    return parse(smiles) is not None


def standardise(smiles: str, keep_stereo: bool = True) -> StandardisedMolecule:
    """Cleanup -> largest fragment -> neutralise -> canonical SMILES + InChIKey.

    The original SMILES is preserved in the returned object (callers store it as provenance).
    """
    mol = parse(smiles)
    if mol is None:
        raise InvalidMolecule(f"Cannot parse SMILES: {smiles!r}")
    try:
        mol = rdMolStandardize.Cleanup(mol)
        mol = _largest_fragment.choose(mol)
        mol = _uncharger.uncharge(mol)
        Chem.SanitizeMol(mol)
        if not keep_stereo:
            Chem.RemoveStereochemistry(mol)
        canonical = Chem.MolToSmiles(mol)
        inchikey = Chem.MolToInchiKey(mol)
        formula = rdMolDescriptors.CalcMolFormula(mol)
    except Exception as exc:  # RDKit raises many exception types
        raise InvalidMolecule(f"Standardisation failed for {smiles!r}: {exc}") from exc
    if not inchikey:
        raise InvalidMolecule(f"Could not compute InChIKey for {smiles!r}")
    return StandardisedMolecule(canonical, inchikey, formula, smiles)


def physchem(smiles: str) -> PhysChem:
    mol = parse(smiles)
    if mol is None:
        raise InvalidMolecule(f"Cannot parse SMILES: {smiles!r}")
    mw = Descriptors.MolWt(mol)
    logp = Crippen.MolLogP(mol)
    hbd = Lipinski.NumHDonors(mol)
    hba = Lipinski.NumHAcceptors(mol)
    violations = int(mw > 500) + int(logp > 5) + int(hbd > 5) + int(hba > 10)
    return PhysChem(
        mol_weight=round(float(mw), 3),
        logp=round(float(logp), 3),
        tpsa=round(float(rdMolDescriptors.CalcTPSA(mol)), 3),
        hbd=int(hbd),
        hba=int(hba),
        rotatable_bonds=int(Lipinski.NumRotatableBonds(mol)),
        heavy_atoms=int(mol.GetNumHeavyAtoms()),
        ring_count=int(rdMolDescriptors.CalcNumRings(mol)),
        lipinski_violations=violations,
        lipinski_pass=violations == 0,
    )


def morgan_fp(smiles: str):
    mol = parse(smiles)
    if mol is None:
        return None
    gen = rdMolDescriptors.GetMorganFingerprintAsBitVect(mol, FP_RADIUS, nBits=FP_BITS)
    return gen


def fp_to_numpy(fp) -> np.ndarray:
    arr = np.zeros((FP_BITS,), dtype=np.uint8)
    DataStructs.ConvertToNumpyArray(fp, arr)
    return arr


def fp_to_packed(fp) -> np.ndarray:
    """Pack the 2048-bit fingerprint into 256 uint8 for FAISS binary indexes."""
    return np.packbits(fp_to_numpy(fp))


def tanimoto(smiles_a: str, smiles_b: str) -> Optional[float]:
    fa, fb = morgan_fp(smiles_a), morgan_fp(smiles_b)
    if fa is None or fb is None:
        return None
    return float(DataStructs.TanimotoSimilarity(fa, fb))


def bulk_tanimoto(query_smiles: str, fps: Sequence) -> List[float]:
    q = morgan_fp(query_smiles)
    if q is None:
        raise InvalidMolecule(f"Cannot parse SMILES: {query_smiles!r}")
    return list(DataStructs.BulkTanimotoSimilarity(q, list(fps)))


def murcko_scaffold(smiles: str) -> Optional[str]:
    from rdkit.Chem.Scaffolds import MurckoScaffold
    mol = parse(smiles)
    if mol is None:
        return None
    try:
        return Chem.MolToSmiles(MurckoScaffold.GetScaffoldForMol(mol))
    except Exception:
        return None


def randomised_smiles(smiles: str, rng) -> Optional[str]:
    """A different, equally valid SMILES string for the same molecule (for retrieval sanity checks)."""
    mol = parse(smiles)
    if mol is None:
        return None
    atoms = list(range(mol.GetNumAtoms()))
    rng.shuffle(atoms)
    mol2 = Chem.RenumberAtoms(mol, atoms)
    return Chem.MolToSmiles(mol2, canonical=False)
