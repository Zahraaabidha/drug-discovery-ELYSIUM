"""BindingDB REST client: measured affinities for a UniProt target."""
from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import List, Optional

from .http import get_json

URL = "https://www.bindingdb.org/rest/getLigandsByUniprots"
_NUM = re.compile(r"^\s*([<>]?=?)\s*([0-9]*\.?[0-9]+(?:[eE][-+]?\d+)?)\s*$")


@dataclass
class BindingDBActivity:
    monomer_id: str
    smiles: str
    standard_type: str
    relation: str
    value_nm: float
    pvalue: float
    assay_ref: Optional[str]


def parse_affinity(text) -> Optional[tuple[str, float]]:
    """'12.5' -> ('=', 12.5); '>10000' -> ('>', 10000.0). None if not numeric."""
    m = _NUM.match(str(text)) if text is not None else None
    if not m:
        return None
    raw_rel = m.group(1)
    rel = "=" if raw_rel in ("", "=") else raw_rel[0]   # '>=' -> '>' (inequality, not a point estimate)
    return rel, float(m.group(2))


def parse_response(payload) -> List[BindingDBActivity]:
    """Parse the getLigandsByUniprots JSON payload (values are reported in nM)."""
    rows = ((payload or {}).get("getLindsByUniprotsResponse") or {}).get("affinities") or []
    out: List[BindingDBActivity] = []
    for r in rows:
        parsed = parse_affinity(r.get("affinity"))
        smiles = r.get("smile")
        a_type = r.get("affinity_type")
        if not parsed or not smiles or a_type not in ("Ki", "Kd", "IC50", "EC50"):
            continue
        rel, val = parsed
        if val <= 0 or not math.isfinite(val):
            continue
        out.append(BindingDBActivity(
            monomer_id=str(r.get("monomerid")), smiles=smiles, standard_type=a_type, relation=rel,
            value_nm=val, pvalue=-math.log10(val * 1e-9),
            assay_ref=r.get("doi") or (f"PMID:{r['pmid']}" if r.get("pmid") else None),
        ))
    return out


def fetch_activities(uniprot_id: str, cutoff_nm: float = 10000, max_records: int = 200) -> List[BindingDBActivity]:
    """Ligands with affinity below `cutoff_nm` for the UniProt target (BindingDB reports nM)."""
    payload = get_json("BindingDB", URL, {
        "uniprot": uniprot_id, "cutoff": cutoff_nm, "response": "application/json",
    }, timeout=90)
    acts = parse_response(payload)
    # Keep exact measurements only; inequality values are not point estimates.
    acts = [a for a in acts if a.relation == "="]
    return acts[:max_records]
