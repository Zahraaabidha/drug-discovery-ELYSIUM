"""ChEMBL REST client: experimental bioactivity for a UniProt target."""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterator, List, Optional

from .http import get_json

BASE = "https://www.ebi.ac.uk/chembl/api/data"
ACTIVITY_TYPES = ("IC50", "Ki", "Kd")


@dataclass
class ChemblActivity:
    activity_id: str
    molecule_chembl_id: str
    smiles: str
    standard_type: str
    relation: Optional[str]
    value_nm: float
    pvalue: Optional[float]
    assay_ref: Optional[str]
    target_chembl_id: str


def resolve_target(uniprot_id: str) -> Optional[str]:
    """ChEMBL id of the single-protein target for a UniProt accession."""
    data = get_json("ChEMBL", f"{BASE}/target.json", {
        "target_components__accession": uniprot_id, "target_type": "SINGLE PROTEIN", "limit": 5,
    })
    targets = (data or {}).get("targets", [])
    return targets[0]["target_chembl_id"] if targets else None


def parse_activity(raw: dict, target_chembl_id: str) -> Optional[ChemblActivity]:
    """Parse one ChEMBL activity record; returns None if it lacks structure or a nM value."""
    smiles = raw.get("canonical_smiles")
    try:
        value = float(raw.get("standard_value"))
    except (TypeError, ValueError):
        return None
    if not smiles or raw.get("standard_units") != "nM" or value <= 0 or not math.isfinite(value):
        return None
    p = raw.get("pchembl_value")
    return ChemblActivity(
        activity_id=str(raw["activity_id"]), molecule_chembl_id=raw["molecule_chembl_id"], smiles=smiles,
        standard_type=raw["standard_type"], relation=raw.get("standard_relation"), value_nm=value,
        pvalue=float(p) if p not in (None, "") else -math.log10(value * 1e-9),
        assay_ref=raw.get("document_chembl_id") or raw.get("assay_chembl_id"),
        target_chembl_id=target_chembl_id,
    )


def iter_activities(target_chembl_id: str, max_records: int = 200, page_size: int = 100) -> Iterator[ChemblActivity]:
    """Exact-relation (=) IC50 / Ki / Kd measurements in nM, newest API order."""
    offset = 0
    yielded = 0
    while yielded < max_records:
        data = get_json("ChEMBL", f"{BASE}/activity.json", {
            "target_chembl_id": target_chembl_id,
            "standard_type__in": ",".join(ACTIVITY_TYPES),
            "standard_units": "nM",
            "standard_relation": "=",
            "limit": min(page_size, max_records - yielded),
            "offset": offset,
        })
        rows = (data or {}).get("activities", [])
        if not rows:
            return
        for raw in rows:
            act = parse_activity(raw, target_chembl_id)
            if act:
                yielded += 1
                yield act
                if yielded >= max_records:
                    return
        if not data.get("page_meta", {}).get("next"):
            return
        offset += len(rows)


def fetch_activities(uniprot_id: str, max_records: int = 200) -> tuple[Optional[str], List[ChemblActivity]]:
    tid = resolve_target(uniprot_id)
    if tid is None:
        return None, []
    return tid, list(iter_activities(tid, max_records))
