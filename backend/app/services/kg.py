#C:\Users\Aabidha\Desktop\PROJECTS\elysium\elysium\backend\app\services\kg.py
"""
Knowledge-graph helper functions for ELYSIUM.

We store a very simple graph in SQL:
  - KGNode: drugs, targets, generated molecules
  - KGEdge: SIMILAR_TO, BINDS
"""

from typing import List, Optional

from sqlalchemy.orm import Session

from ..models import KGNode, KGEdge, DiscoveryRun
from ..schemas import (
    Molecule,
    SimilarDrug,
    MoleculeGraphEntry,
    TargetGraphResponse,
    DrugGraphEntry,
    DrugGraphResponse,
)

def _get_or_create_target_node(db: Session, target_id: str) -> KGNode:
    node = (
        db.query(KGNode)
        .filter(KGNode.node_type == "target", KGNode.external_id == target_id)
        .first()
    )
    if node:
        return node

    node = KGNode(
        node_type="target",
        external_id=target_id,
        name=target_id,
        info=f"Target protein {target_id}",
    )
    db.add(node)
    db.flush()
    return node


def _get_or_create_drug_node(
    db: Session,
    name: str,
    smiles: Optional[str],
    indication: Optional[str],
) -> KGNode:
    node = (
        db.query(KGNode)
        .filter(KGNode.node_type == "drug", KGNode.name == name)
        .first()
    )
    if node:
        return node

    info_parts = []
    if indication:
        info_parts.append(f"Indication: {indication}")
    info = " ".join(info_parts) if info_parts else None

    node = KGNode(
        node_type="drug",
        external_id=None,
        name=name,
        smiles=smiles,
        info=info,
    )
    db.add(node)
    db.flush()
    return node


def _create_generated_molecule_node(
    db: Session,
    run: DiscoveryRun,
    index: int,
    mol: Molecule,
) -> KGNode:
    ext_id = f"{run.id}:{index}"
    info = f"Generated in run {run.id} for target {run.target_id}"
    node = KGNode(
        node_type="generated_molecule",
        external_id=ext_id,
        name=f"gen_{run.id[:8]}_{index}",
        smiles=mol.smiles,
        info=info,
    )
    db.add(node)
    db.flush()
    return node


def attach_run_to_kg(db: Session, run: DiscoveryRun, molecules: List[Molecule]) -> None:
    """
    For each generated molecule:
      - create a KG node
      - link to the target with BINDS
      - link to most similar known drug with SIMILAR_TO
    """
    # Make sure target node exists
    target_node = _get_or_create_target_node(db, run.target_id)

    for idx, mol in enumerate(molecules):
        gen_node = _create_generated_molecule_node(db, run, idx, mol)

        # BINDS edge: generated molecule -> target
        bind_edge = KGEdge(
            source_id=gen_node.id,
            target_id=target_node.id,
            relation="BINDS",
            weight=mol.score,  # use predicted affinity score
            extra=None,
        )
        db.add(bind_edge)

        # SIMILAR_TO edge: generated molecule -> known drug (if available)
        if mol.similar_drug is not None:
            drug = mol.similar_drug
            drug_node = _get_or_create_drug_node(
                db,
                name=drug.name,
                smiles=drug.smiles,
                indication=drug.indication,
            )

            extra_parts = []
            extra_parts.append(f"Tanimoto={drug.similarity:.4f}")
            if (
                mol.similar_drug_semantic is not None
                and mol.similar_drug_semantic.semantic_similarity is not None
            ):
                extra_parts.append(
                    f"chemBERTa_cosine={mol.similar_drug_semantic.semantic_similarity:.4f}"
                )
            extra = "; ".join(extra_parts) if extra_parts else None

            sim_edge = KGEdge(
                source_id=gen_node.id,
                target_id=drug_node.id,
                relation="SIMILAR_TO",
                weight=drug.similarity,
                extra=extra,
            )
            db.add(sim_edge)

def get_target_graph(db: Session, target_id: str) -> TargetGraphResponse:
    """
    Build a simple graph view for a target:

    - Find the target node.
    - Find all BINDS edges (generated molecule -> target).
    - For each generated molecule, find its SIMILAR_TO edge to a known drug.
    """
    target_node = (
        db.query(KGNode)
        .filter(KGNode.node_type == "target", KGNode.external_id == target_id)
        .first()
    )

    if target_node is None:
        # No graph info yet for this target
        return TargetGraphResponse(target_id=target_id, molecules=[])

    bind_edges = (
        db.query(KGEdge)
        .filter(KGEdge.relation == "BINDS", KGEdge.target_id == target_node.id)
        .all()
    )

    entries: List[MoleculeGraphEntry] = []

    for bind in bind_edges:
        gen_node = db.query(KGNode).filter(KGNode.id == bind.source_id).first()
        if gen_node is None:
            continue

        # Parse run_id and index from external_id like "runid:index"
        run_id = ""
        molecule_index = 0
        if gen_node.external_id and ":" in gen_node.external_id:
            run_part, idx_part = gen_node.external_id.split(":", 1)
            run_id = run_part
            try:
                molecule_index = int(idx_part)
            except ValueError:
                molecule_index = 0

        # Find the SIMILAR_TO edge (if any)
        sim_edge = (
            db.query(KGEdge)
            .filter(
                KGEdge.relation == "SIMILAR_TO",
                KGEdge.source_id == gen_node.id,
            )
            .order_by(KGEdge.weight.desc())
            .first()
        )

        similar: Optional[SimilarDrug] = None
        if sim_edge is not None:
            drug_node = db.query(KGNode).filter(KGNode.id == sim_edge.target_id).first()
            if drug_node is not None:
                tanimoto = sim_edge.weight or 0.0
                cosine = None

                if sim_edge.extra:
                    for part in sim_edge.extra.split(";"):
                        part = part.strip()
                        if part.startswith("chemBERTa_cosine="):
                            try:
                                cosine = float(part.split("=", 1)[1])
                            except ValueError:
                                pass

                similar = SimilarDrug(
                    name=drug_node.name,
                    smiles=drug_node.smiles or "",
                    indication=drug_node.info,  # may contain "Indication: ..."
                    similarity=tanimoto,
                    semantic_similarity=cosine,
                )

        entries.append(
            MoleculeGraphEntry(
                run_id=run_id,
                molecule_index=molecule_index,
                smiles=gen_node.smiles or "",
                score=bind.weight or 0.0,
                similar_drug=similar,
            )
        )

    # Sort by score descending
    entries.sort(key=lambda e: e.score, reverse=True)

    return TargetGraphResponse(
        target_id=target_id,
        molecules=entries,
    )

def get_drug_graph(db: Session, drug_name: str) -> DrugGraphResponse:
    """
    For a given drug name, return all generated molecules that are SIMILAR_TO it,
    across all targets and runs.
    """
    # Find the drug node
    drug_node = (
        db.query(KGNode)
        .filter(KGNode.node_type == "drug", KGNode.name == drug_name)
        .first()
    )
    if drug_node is None:
        return DrugGraphResponse(drug_name=drug_name, molecules=[])

    # Find SIMILAR_TO edges where target is this drug
    sim_edges = (
        db.query(KGEdge)
        .filter(KGEdge.relation == "SIMILAR_TO", KGEdge.target_id == drug_node.id)
        .all()
    )

    entries: List[DrugGraphEntry] = []

    for sim_edge in sim_edges:
        gen_node = db.query(KGNode).filter(KGNode.id == sim_edge.source_id).first()
        if gen_node is None:
            continue

        # Parse run_id and index from external_id like "runid:index"
        run_id = ""
        molecule_index = 0
        if gen_node.external_id and ":" in gen_node.external_id:
            run_part, idx_part = gen_node.external_id.split(":", 1)
            run_id = run_part
            try:
                molecule_index = int(idx_part)
            except ValueError:
                molecule_index = 0

        # Find the target this generated molecule binds to
        bind_edge = (
            db.query(KGEdge)
            .filter(
                KGEdge.relation == "BINDS",
                KGEdge.source_id == gen_node.id,
            )
            .first()
        )

        target_id = ""
        score = sim_edge.weight or 0.0
        if bind_edge is not None:
            target_node = db.query(KGNode).filter(KGNode.id == bind_edge.target_id).first()
            if target_node is not None and target_node.external_id:
                target_id = target_node.external_id
            if bind_edge.weight is not None:
                score = bind_edge.weight

        entries.append(
            DrugGraphEntry(
                target_id=target_id,
                run_id=run_id,
                molecule_index=molecule_index,
                smiles=gen_node.smiles or "",
                score=score,
            )
        )

    # Sort by score descending
    entries.sort(key=lambda e: e.score, reverse=True)

    return DrugGraphResponse(drug_name=drug_name, molecules=entries)
