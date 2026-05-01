#C:\Users\Aabidha\Desktop\PROJECTS\elysium\elysium\backend\app\models.py
import uuid
import datetime as dt

from sqlalchemy import (
    Column,
    String,
    Integer,
    Float,
    DateTime,
    ForeignKey,
    Text,
)
from sqlalchemy.orm import relationship

from .db import Base


class DiscoveryRun(Base):
    __tablename__ = "discovery_runs"

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    target_id = Column(String, index=True, nullable=False)
    num_molecules = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=dt.datetime.utcnow)

    molecules = relationship(
        "MoleculeRecord",
        back_populates="run",
        cascade="all, delete-orphan",
    )


class MoleculeRecord(Base):
    __tablename__ = "molecules"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    run_id = Column(String, ForeignKey("discovery_runs.id"), index=True, nullable=False)
    smiles = Column(String, index=True, nullable=False)
    score = Column(Float, nullable=False)
    source = Column(String, nullable=False)
    notes = Column(Text)

    # ADMET properties
    admet_mw = Column(Float, nullable=True)
    admet_logp = Column(Float, nullable=True)
    admet_hbd = Column(Integer, nullable=True)
    admet_hba = Column(Integer, nullable=True)
    admet_tpsa = Column(Float, nullable=True)
    admet_rotatable_bonds = Column(Integer, nullable=True)
    admet_lipinski_pass = Column(Integer, nullable=True)  # 1 = True, 0 = False
    admet_lipinski_violations = Column(Integer, nullable=True)

    # Similarity
    similar_drug_fp = Column(String, nullable=True)
    tanimoto_fp = Column(Float, nullable=True)
    similar_drug_semantic = Column(String, nullable=True)
    tanimoto_semantic = Column(Float, nullable=True)

    # Scorer transparency
    scorer_used = Column(String, nullable=True)

    run = relationship("DiscoveryRun", back_populates="molecules")

class KGNode(Base):
    __tablename__ = "kg_nodes"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    node_type = Column(String, index=True)  # 'drug', 'target', 'generated_molecule', etc.
    external_id = Column(String, index=True, nullable=True)  # e.g. 'EGFR', 'runid:0'
    name = Column(String, index=True, nullable=False)
    smiles = Column(String, nullable=True)
    info = Column(Text, nullable=True)

    outgoing_edges = relationship(
        "KGEdge",
        back_populates="source",
        foreign_keys="KGEdge.source_id",
    )
    incoming_edges = relationship(
        "KGEdge",
        back_populates="target",
        foreign_keys="KGEdge.target_id",
    )


class KGEdge(Base):
    __tablename__ = "kg_edges"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    source_id = Column(Integer, ForeignKey("kg_nodes.id"), nullable=False)
    target_id = Column(Integer, ForeignKey("kg_nodes.id"), nullable=False)
    relation = Column(String, index=True)  # 'SIMILAR_TO', 'BINDS', 'TREATS'
    weight = Column(Float, nullable=True)  # e.g. similarity or score
    extra = Column(Text, nullable=True)    # JSON/string with extra info

    source = relationship(
        "KGNode",
        foreign_keys=[source_id],
        back_populates="outgoing_edges",
    )
    target = relationship(
        "KGNode",
        foreign_keys=[target_id],
        back_populates="incoming_edges",
    )
