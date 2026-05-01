from typing import Tuple, Optional
from rdkit import Chem, DataStructs
from rdkit.Chem import AllChem
from .fda_library import FDA_LIKE_DRUGS
from .schemas import SimilarDrug
from .services.embeddings import find_most_semantic_drug


def _smiles_to_fp(smiles: str):
    """Return Morgan fingerprint for a SMILES string, or None if invalid."""
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return None
    return AllChem.GetMorganFingerprintAsBitVect(mol, radius=2, nBits=2048)


# Precompute fingerprints for library drugs
_LIB_FPS = []
for drug in FDA_LIKE_DRUGS:
    fp = _smiles_to_fp(drug["smiles"])
    if fp is not None:
        _LIB_FPS.append((drug, fp))


def find_most_similar_drug(smiles: str) -> Optional[SimilarDrug]:
    """
    For a candidate molecule, return the most similar known drug
    from the tiny FDA-like library using Tanimoto similarity.
    """
    fp = _smiles_to_fp(smiles)
    if fp is None or not _LIB_FPS:
        return None

    best = None
    best_sim = -1.0

    for drug, lib_fp in _LIB_FPS:
        sim = DataStructs.TanimotoSimilarity(fp, lib_fp)
        if sim > best_sim:
            best_sim = sim
            best = drug

    if best is None:
        return None

    return SimilarDrug(
        name=best["name"],
        smiles=best["smiles"],
        indication=best.get("indication"),
        similarity=best_sim,
    )

def find_combined_similar_drugs(smiles: str) -> Tuple[Optional[SimilarDrug], Optional[SimilarDrug]]:
    """
    Returns:
      (fp_neighbor, semantic_neighbor)
    fp_neighbor  -> highest Tanimoto similarity (Morgan fingerprints)
    semantic_neighbor -> highest chemBERTa cosine similarity
    """
    fp_neighbor = find_most_similar_drug(smiles)
    semantic_neighbor = find_most_semantic_drug(smiles)
    return fp_neighbor, semantic_neighbor
