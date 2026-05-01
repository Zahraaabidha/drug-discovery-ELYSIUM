from rdkit import Chem
from rdkit.Chem import Draw
import io

def smiles_to_png(smiles: str) -> bytes:
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        raise ValueError("Invalid SMILES")

    img = Draw.MolToImage(mol, size=(300, 300))

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)

    return buf.getvalue()
