"""PubChem PUG REST client (structures + identifiers)."""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import List, Optional
from urllib.parse import quote

from .http import get_json

BASE = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"
PROPS = "SMILES,ConnectivitySMILES,InChIKey,MolecularFormula,Title"


@dataclass
class PubChemCompound:
    cid: str
    smiles: str
    inchikey: Optional[str]
    formula: Optional[str]
    title: Optional[str]
    url: str


def parse_properties(payload) -> List[PubChemCompound]:
    """Parse a PUG REST PropertyTable response."""
    if not payload:
        return []
    out = []
    for p in payload.get("PropertyTable", {}).get("Properties", []):
        smiles = p.get("SMILES") or p.get("ConnectivitySMILES") or p.get("IsomericSMILES") or p.get("CanonicalSMILES")
        if not smiles:
            continue
        cid = str(p["CID"])
        out.append(PubChemCompound(
            cid=cid, smiles=smiles, inchikey=p.get("InChIKey"), formula=p.get("MolecularFormula"),
            title=p.get("Title"), url=f"https://pubchem.ncbi.nlm.nih.gov/compound/{cid}",
        ))
    return out


def _params():
    key = os.getenv("NCBI_API_KEY")
    return {"api_key": key} if key else None


def fetch_by_name(name: str) -> List[PubChemCompound]:
    payload = get_json("PubChem", f"{BASE}/compound/name/{quote(name, safe='')}/property/{PROPS}/JSON", _params())
    return parse_properties(payload)


def fetch_by_cid(cid: int | str) -> List[PubChemCompound]:
    payload = get_json("PubChem", f"{BASE}/compound/cid/{cid}/property/{PROPS}/JSON", _params())
    return parse_properties(payload)
