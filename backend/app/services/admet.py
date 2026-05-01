#C:\Users\Aabidha\Desktop\PROJECTS\elysium\elysium\backend\app\services\admet.py
from typing import Optional

from rdkit import Chem
from rdkit.Chem import Descriptors, Crippen, Lipinski, rdMolDescriptors

from ..schemas import ADMETProperties


def calculate_admet(smiles: str) -> Optional[ADMETProperties]:
    """
    Compute basic ADMET / drug-likeness properties for a SMILES string
    using simple RDKit descriptors and Lipinski rule-of-five.
    """
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return None

    mw = Descriptors.MolWt(mol)
    logp = Crippen.MolLogP(mol)
    hbd = Lipinski.NumHDonors(mol)
    hba = Lipinski.NumHAcceptors(mol)
    rot_bonds = Lipinski.NumRotatableBonds(mol)
    tpsa = rdMolDescriptors.CalcTPSA(mol)

    # Lipinski rule-of-five thresholds
    violations = 0
    if mw > 500:
        violations += 1
    if logp > 5:
        violations += 1
    if hbd > 5:
        violations += 1
    if hba > 10:
        violations += 1

    return ADMETProperties(
        molecular_weight=round(mw, 3),
        logp=round(logp, 3),
        hbd=int(hbd),
        hba=int(hba),
        rotatable_bonds=int(rot_bonds),
        tpsa=round(tpsa, 3),
        lipinski_violations=violations,
        lipinski_pass=(violations == 0),
    )
