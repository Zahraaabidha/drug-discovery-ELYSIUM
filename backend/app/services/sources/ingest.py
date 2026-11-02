"""Ingest external data into the persistent registry with full provenance."""
from __future__ import annotations

import datetime as dt
import logging
from typing import Dict, Iterable, Optional

from sqlalchemy.orm import Session

from ... import models as m
from .. import chem, registry
from ..targets import resolve_target
from . import bindingdb, chembl, pubchem
from .http import ExternalServiceError

log = logging.getLogger(__name__)


def _add_bioactivity(db: Session, comp: m.Compound, *, target, source_db: str, external_id: str,
                     standard_type: str, relation: Optional[str], value_nm: float,
                     pvalue: Optional[float], assay_ref: Optional[str]) -> bool:
    exists = db.query(m.Bioactivity).filter_by(
        compound_id=comp.id, target_symbol=target.symbol, source_db=source_db, external_id=external_id
    ).first()
    if exists:
        return False
    db.add(m.Bioactivity(
        compound_id=comp.id, target_symbol=target.symbol, uniprot_id=target.uniprot_id,
        source_db=source_db, external_id=external_id, standard_type=standard_type, relation=relation,
        value_nm=value_nm, pvalue=pvalue, assay_ref=assay_ref, evidence_type="experimental",
        retrieved_at=dt.datetime.utcnow(),
    ))
    db.flush()          # sessions run with autoflush off: make duplicates within one batch visible
    return True


def ingest_target_bioactivity(db: Session, target_id: str, sources: Iterable[str] = ("chembl", "bindingdb"),
                              max_records: int = 200) -> Dict:
    """Pull experimental activities for a supported target from ChEMBL and/or BindingDB.

    Each source is independent: a failure in one is reported in `errors` and does not hide
    results from the other. Nothing is fabricated when a service is unavailable.
    """
    target = resolve_target(target_id)
    report: Dict = {"target": target.symbol, "uniprot_id": target.uniprot_id, "sources": {}, "errors": {}}

    for source in sources:
        stats = {"records": 0, "new_compounds": 0, "new_bioactivities": 0, "invalid_structures": 0}
        try:
            if source == "chembl":
                chembl_target, acts = chembl.fetch_activities(target.uniprot_id, max_records)
                stats["chembl_target"] = chembl_target
                items = [(a.molecule_chembl_id, a.smiles, a.activity_id, a.standard_type, a.relation, a.value_nm,
                          a.pvalue, a.assay_ref, f"https://www.ebi.ac.uk/chembl/compound_report_card/{a.molecule_chembl_id}/")
                         for a in acts]
                src_name = "chembl"
            elif source == "bindingdb":
                acts = bindingdb.fetch_activities(target.uniprot_id, max_records=max_records)
                items = [(a.monomer_id, a.smiles, f"{a.monomer_id}:{a.standard_type}:{a.value_nm}:{a.assay_ref or ''}", a.standard_type,
                          a.relation, a.value_nm, a.pvalue, a.assay_ref,
                          f"https://www.bindingdb.org/rest/getLigandsByUniprot?uniprot={target.uniprot_id}")
                         for a in acts]
                src_name = "bindingdb"
            else:
                raise ValueError(f"Unknown source {source!r}")
        except ExternalServiceError as exc:
            log.warning("Ingest %s/%s failed: %s", source, target.symbol, exc)
            report["errors"][source] = str(exc)
            continue

        for mol_id, smiles, act_id, a_type, rel, val, pval, ref, url in items:
            stats["records"] += 1
            try:
                comp, created = registry.register_compound(
                    db, smiles, origin=m.ORIGIN_EXTERNAL, source_db=src_name, external_id=str(mol_id), url=url,
                    note=f"Retrieved for target {target.symbol}",
                )
            except chem.InvalidMolecule:
                stats["invalid_structures"] += 1
                continue
            stats["new_compounds"] += int(created)
            stats["new_bioactivities"] += int(_add_bioactivity(
                db, comp, target=target, source_db=src_name, external_id=str(act_id), standard_type=a_type,
                relation=rel, value_nm=val, pvalue=pval, assay_ref=ref))
        db.commit()
        report["sources"][source] = stats
    return report


def ingest_pubchem_by_name(db: Session, name: str) -> Dict:
    """Look a compound up in PubChem by name and register it (origin=external unless already known)."""
    hits = pubchem.fetch_by_name(name)
    if not hits:
        return {"name": name, "found": False}
    h = hits[0]
    comp, created = registry.register_compound(
        db, h.smiles, origin=m.ORIGIN_EXTERNAL, source_db="pubchem", external_id=h.cid,
        name=h.title or name, url=h.url, note="PubChem name lookup",
    )
    db.commit()
    return {"name": name, "found": True, "compound_id": comp.id, "created": created, "cid": h.cid,
            "inchikey": comp.inchikey, "pubchem_inchikey": h.inchikey}
