"""Persistent compound registry: deduplicated by standardised InChIKey.

The relational database is authoritative for compound identity, metadata,
experimental bioactivity and prediction history.
"""
from __future__ import annotations

import datetime as dt
import logging
from typing import Dict, Iterable, List, Optional, Tuple

from sqlalchemy.orm import Session

from .. import models as m
from . import chem

log = logging.getLogger(__name__)

REFERENCE_SOURCE = "elysium_reference"
GENERATOR_SOURCE = "elysium_generator"


def get_by_inchikey(db: Session, inchikey: str) -> Optional[m.Compound]:
    return db.query(m.Compound).filter(m.Compound.inchikey == inchikey).first()


def register_compound(
    db: Session,
    smiles: str,
    *,
    origin: str,
    source_db: str,
    external_id: str = "",
    name: Optional[str] = None,
    url: Optional[str] = None,
    note: Optional[str] = None,
    generation_method: Optional[str] = None,
    generation_run_id: Optional[str] = None,
) -> Tuple[m.Compound, bool]:
    """Insert a compound or return the existing record for the same standardised structure.

    Returns (compound, created). The original SMILES and the source are always recorded as
    a CompoundSource row so provenance is preserved even for duplicates. An existing
    compound keeps its original origin ("reference"/"external" never gets relabelled as
    "generated").
    """
    if origin not in (m.ORIGIN_REFERENCE, m.ORIGIN_EXTERNAL, m.ORIGIN_GENERATED):
        raise ValueError(f"Unknown origin {origin!r}")
    std = chem.standardise(smiles)
    existing = get_by_inchikey(db, std.inchikey)
    created = existing is None

    if created:
        pc = chem.physchem(std.canonical_smiles)
        comp = m.Compound(
            inchikey=std.inchikey,
            canonical_smiles=std.canonical_smiles,
            original_smiles=smiles,
            name=name,
            formula=std.formula,
            origin=origin,
            generation_method=generation_method if origin == m.ORIGIN_GENERATED else None,
            generation_run_id=generation_run_id if origin == m.ORIGIN_GENERATED else None,
            **pc.as_dict(),
        )
        db.add(comp)
        db.flush()
    else:
        comp = existing
        if name and not comp.name:
            comp.name = name

    already = (
        db.query(m.CompoundSource)
        .filter_by(compound_id=comp.id, source_db=source_db, external_id=external_id or "")
        .first()
    )
    if already is None:
        db.add(m.CompoundSource(
            compound_id=comp.id, source_db=source_db, external_id=external_id or "",
            original_smiles=smiles, url=url, note=note, retrieved_at=dt.datetime.utcnow(),
        ))
        db.flush()
    return comp, created


def import_reference_collections(db: Session) -> Dict[str, int]:
    """Import the bundled known-drug collections as origin='reference'."""
    from ..fda_library import FDA_LIKE_DRUGS
    from ..data.candidate_library import CANDIDATE_LIBRARY

    stats = {"created": 0, "existing": 0, "invalid": 0}
    for entry in list(FDA_LIKE_DRUGS) + list(CANDIDATE_LIBRARY):
        try:
            _, created = register_compound(
                db, entry["smiles"], origin=m.ORIGIN_REFERENCE, source_db=REFERENCE_SOURCE,
                external_id=entry["name"].lower(), name=entry["name"],
                note=entry.get("indication"),
            )
            stats["created" if created else "existing"] += 1
        except chem.InvalidMolecule:
            stats["invalid"] += 1
            log.warning("Skipping invalid reference SMILES for %s", entry.get("name"))
    db.commit()
    log.info("Reference import: %s", stats)
    return stats


def record_prediction(
    db: Session, compound: m.Compound, *, target_symbol: str, uniprot_id: Optional[str],
    model_name: str, model_version: Optional[str], value_nm: float, run_id: Optional[str],
    params: Optional[dict] = None,
) -> m.Prediction:
    import math
    pkd = 9.0 - math.log10(max(value_nm, 1e-6))
    pred = m.Prediction(
        compound_id=compound.id, run_id=run_id, target_symbol=target_symbol, uniprot_id=uniprot_id,
        model_name=model_name, model_version=model_version, value=float(value_nm), units="nM",
        pkd=float(pkd), normalised_score=float(min(max(pkd / 10.0, 0.0), 1.0)),
        evidence_type="computational_prediction", params=params,
    )
    db.add(pred)
    db.flush()
    return pred


def all_compounds(db: Session) -> List[m.Compound]:
    return db.query(m.Compound).order_by(m.Compound.id).all()


def compound_ids_for_smiles(db: Session, smiles_list: Iterable[str]) -> Dict[str, int]:
    out: Dict[str, int] = {}
    for s in smiles_list:
        try:
            std = chem.standardise(s)
        except chem.InvalidMolecule:
            continue
        c = get_by_inchikey(db, std.inchikey)
        if c:
            out[s] = c.id
    return out
