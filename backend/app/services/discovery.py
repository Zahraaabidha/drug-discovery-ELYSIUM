#C:\Users\Aabidha\Desktop\PROJECTS\elysium\elysium\backend\app\services\discovery.py*

import uuid
from typing import List, cast

from sqlalchemy.orm import Session

from ..schemas import Molecule, DiscoveryRequest, DiscoveryResponse
from ..core.config import resolve_target_sequence
from ..models import DiscoveryRun, MoleculeRecord
from ..similarity import find_combined_similar_drugs
from .scoring import get_scorer
from .generation import get_generator
from .kg import attach_run_to_kg
from .admet import calculate_admet
from app.arangodb_client import get_arango_db


scorer = get_scorer()
generator = get_generator()

def _generate_candidate_smiles(num: int) -> List[str]:
    """
    Temporary candidate generator.

    Right now we just cycle through a few simple SMILES strings.
    Later this will be replaced by:
      - TamGen or other Transformer generator
      - Library-based sampling + scaffold hopping
    """
    base_smiles = [
        "CCO",          # ethanol
        "CC(=O)O",      # acetic acid
        "CCN(CC)CC",    # triethylamine
        "CCOC(=O)C",    # ethyl acetate
        "CC(C)O",       # isopropanol
    ]
    return (base_smiles * ((num // len(base_smiles)) + 1))[:num]


def _simple_score(smiles_list: List[str], target_sequence: str, target_id: str) -> List[float]:
    """
    Simple deterministic scoring stub.

    This mimics a DTI model by assigning decreasing scores.
    It keeps ELYSIUM's pipeline structure intact until we plug in
    DeepPurpose (or another real model) again.
    """
    scores: List[float] = []
    base = 1.0
    step = 0.05  # how much the score drops per molecule

    for i, _ in enumerate(smiles_list):
        s = base - step * i
        if s < 0:
            s = 0.0
        scores.append(s)

    return scores


def run_discovery(req, db):
    if isinstance(req, dict):
        target_id = req["target_id"]
        num_molecules = req.get("num_molecules", 5)
        lipinski_only = req.get("lipinski_only", False)
    else:
        target_id = req.target_id
        num_molecules = req.num_molecules
        lipinski_only = req.lipinski_only
    """
    ELYSIUM discovery pipeline:

    1. Generate candidate molecules.
    2. Resolve target sequence.
    3. Score molecules with configured backend (stub or DeepPurpose).
    4. Compute similarity to known drugs.
    5. Save to DB.
    6. Return ranked molecules.
    """

    # 1) Generate candidate molecules (library-based for now)
    smiles_list = generator.generate(target_id, num_molecules)


    # 2) Resolve target sequence
    target_seq = resolve_target_sequence(target_id)

    # 3) Score with configured backend
    scores = scorer.score(smiles_list, target_seq, target_id)

    # 4) Build Molecule objects with similarity info
    molecules: List[Molecule] = []
    for smi, score in zip(smiles_list, scores):
        fp_neighbor, semantic_neighbor = find_combined_similar_drugs(smi)
        admet_props = calculate_admet(smi)

        note_parts = ["Scored with ELYSIUM backend."]

        if fp_neighbor is not None:
            note_parts.append(
                f"Most similar known drug (fingerprint): "
                f"{fp_neighbor.name} (Tanimoto={fp_neighbor.similarity:.2f})."
            )

        if (
            semantic_neighbor is not None
            and semantic_neighbor.semantic_similarity is not None
            and (fp_neighbor is None or semantic_neighbor.name != fp_neighbor.name)
        ):
            note_parts.append(
                f"Most similar known drug (chemBERTa): "
                f"{semantic_neighbor.name} "
                f"(cosine={semantic_neighbor.semantic_similarity:.2f})."
            )

        if admet_props is not None:
            lip = "pass" if admet_props.lipinski_pass else "fail"
            note_parts.append(
                f"Lipinski {lip}, violations={admet_props.lipinski_violations}."
            )

        molecules.append(
            Molecule(
                smiles=smi,
                score=score,
                source=type(scorer).__name__,
                notes=" ".join(note_parts),
                similar_drug=fp_neighbor,
                similar_drug_semantic=semantic_neighbor,
                admet=admet_props,
            )
        )

            # Optional Lipinski filter
    if lipinski_only:
        filtered = [
            m for m in molecules
            if m.admet is not None and m.admet.lipinski_pass
        ]
        if filtered:
            molecules = filtered
        # if filtered is empty, we keep original list, so the user still gets something


    # Sort by score desc
    molecules.sort(key=lambda m: m.score, reverse=True)

    # 5) Save to DB (same as before)
    run_record = DiscoveryRun(
        target_id=target_id,
        num_molecules=len(molecules),
    )
    db.add(run_record)
    db.flush()  # assign ID

    for m in molecules:
        admet = m.admet
        fp = m.similar_drug
        sem = m.similar_drug_semantic

        db.add(
            MoleculeRecord(
                run_id=run_record.id,
                smiles=m.smiles,
                score=m.score,
                source=m.source,
                notes=m.notes,
                scorer_used=type(scorer).__name__,

                # ADMET
                admet_mw=admet.molecular_weight if admet else None,
                admet_logp=admet.logp if admet else None,
                admet_hbd=admet.hbd if admet else None,
                admet_hba=admet.hba if admet else None,
                admet_tpsa=admet.tpsa if admet else None,
                admet_rotatable_bonds=admet.rotatable_bonds if admet else None,
                admet_lipinski_pass=1 if (admet and admet.lipinski_pass) else 0,
                admet_lipinski_violations=admet.lipinski_violations if admet else None,

                # Similarity
                similar_drug_fp=fp.name if fp else None,
                tanimoto_fp=fp.similarity if fp else None,
                similar_drug_semantic=sem.name if sem else None,
                tanimoto_semantic=sem.semantic_similarity if sem else None,
            )
        )

    # Attach this run to the knowledge graph (nodes + edges)
    attach_run_to_kg(db, run_record, molecules)

    db.commit()
    db.refresh(run_record)

    try:
        arango = get_arango_db()
        molecules_col = arango.collection("molecules")
        binds_edge = arango.collection("binds")
        similar_edge = arango.collection("similar_to")

        for idx, m in enumerate(molecules):
            mol_key = f"{run_record.id}_{idx}"
            try:
                molecules_col.insert({
                    "_key": mol_key,
                    "run_id": run_record.id,
                    "index": idx,
                    "target_id": target_id,
                    "smiles": m.smiles,
                    "score": m.score,
                })
            except Exception:
                pass

            try:
                binds_edge.insert({
                    "_from": f"molecules/{mol_key}",
                    "_to": f"targets/{target_id}",
                    "score": m.score,
                    "source": "ELYSIUM/DeepPurpose"
                })
            except Exception:
                pass

            try:
                if m.similar_drug is not None:
                    similar_edge.insert({
                        "_from": f"molecules/{mol_key}",
                        "_to": f"drugs/{m.similar_drug.name.lower()}",
                        "tanimoto": m.similar_drug.similarity,
                        "semantic": m.similar_drug.semantic_similarity,
                    })
            except Exception:
                pass

    except Exception as e:
        print(f"[Arango] write failed (non-critical): {e}")


    # 6) Return response
    return DiscoveryResponse(
        run_id=cast(str, run_record.id),
        target_id=cast(str, run_record.target_id),
        num_molecules=cast(int, run_record.num_molecules),
        molecules=molecules,
    )
