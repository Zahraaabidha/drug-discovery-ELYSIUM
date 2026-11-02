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
    JSON,
    Boolean,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from .db import Base


class DiscoveryRun(Base):
    __tablename__ = "discovery_runs"

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    target_id = Column(String, index=True, nullable=False)
    num_molecules = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=dt.datetime.utcnow)

    # Reproducibility / provenance (migration 0002)
    status = Column(String, nullable=True)            # completed | failed
    error = Column(Text, nullable=True)
    seed = Column(Integer, nullable=True)
    params = Column(JSON, nullable=True)              # request + generation parameters
    models = Column(JSON, nullable=True)              # model names / versions used
    data_sources = Column(JSON, nullable=True)        # data / library versions used
    metrics = Column(JSON, nullable=True)             # validity / uniqueness / novelty ...

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

    # Link to the persistent registry (migration 0002)
    compound_id = Column(Integer, ForeignKey("compounds.id"), index=True, nullable=True)

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


# ═══════════════════════════════════════════════════════════════════════════
#  Persistent compound registry (authoritative store for identity & metadata)
# ═══════════════════════════════════════════════════════════════════════════

ORIGIN_REFERENCE = "reference"      # known drug / curated reference compound
ORIGIN_EXTERNAL = "external"        # imported from PubChem / ChEMBL / BindingDB
ORIGIN_GENERATED = "generated"      # produced by an ELYSIUM generator


class Compound(Base):
    """One row per unique standardised structure (deduplicated by InChIKey)."""
    __tablename__ = "compounds"

    id = Column(Integer, primary_key=True, autoincrement=True)
    inchikey = Column(String(27), unique=True, index=True, nullable=False)
    canonical_smiles = Column(String, index=True, nullable=False)   # standardised
    original_smiles = Column(String, nullable=False)                # first SMILES seen
    name = Column(String, index=True, nullable=True)
    formula = Column(String, nullable=True)
    origin = Column(String, index=True, nullable=False)             # reference|external|generated
    created_at = Column(DateTime, default=dt.datetime.utcnow)

    # Basic RDKit physicochemical descriptors (NOT ADMET predictions)
    mol_weight = Column(Float, index=True)
    logp = Column(Float, index=True)
    tpsa = Column(Float, index=True)
    hbd = Column(Integer)
    hba = Column(Integer)
    rotatable_bonds = Column(Integer)
    heavy_atoms = Column(Integer)
    ring_count = Column(Integer)
    lipinski_violations = Column(Integer, index=True)
    lipinski_pass = Column(Boolean)

    # Generation provenance (only for origin == generated)
    generation_method = Column(String, nullable=True)
    generation_run_id = Column(String, ForeignKey("discovery_runs.id"), nullable=True, index=True)

    sources = relationship("CompoundSource", back_populates="compound", cascade="all, delete-orphan")
    bioactivities = relationship("Bioactivity", back_populates="compound", cascade="all, delete-orphan")
    predictions = relationship("Prediction", back_populates="compound", cascade="all, delete-orphan")
    annotations = relationship("Annotation", back_populates="compound", cascade="all, delete-orphan")


class CompoundSource(Base):
    """Where a compound (or an alias of it) came from."""
    __tablename__ = "compound_sources"
    __table_args__ = (UniqueConstraint("compound_id", "source_db", "external_id", name="uq_compound_source"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    compound_id = Column(Integer, ForeignKey("compounds.id"), index=True, nullable=False)
    source_db = Column(String, index=True, nullable=False)   # pubchem|chembl|bindingdb|elysium_reference|elysium_generator
    external_id = Column(String, nullable=False, default="")  # CID, CHEMBL id, monomer id ...
    original_smiles = Column(String, nullable=False)
    url = Column(String, nullable=True)
    retrieved_at = Column(DateTime, default=dt.datetime.utcnow)
    note = Column(Text, nullable=True)

    compound = relationship("Compound", back_populates="sources")


class Bioactivity(Base):
    """EXPERIMENTALLY MEASURED activity retrieved from an external database."""
    __tablename__ = "bioactivities"
    __table_args__ = (
        UniqueConstraint("compound_id", "target_symbol", "source_db", "external_id", name="uq_bioactivity"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    compound_id = Column(Integer, ForeignKey("compounds.id"), index=True, nullable=False)
    target_symbol = Column(String, index=True, nullable=False)
    uniprot_id = Column(String, index=True, nullable=True)
    source_db = Column(String, index=True, nullable=False)     # chembl | bindingdb
    external_id = Column(String, nullable=False)               # ChEMBL activity id / BindingDB row key
    standard_type = Column(String, nullable=False)             # IC50 | Ki | Kd | EC50
    relation = Column(String, nullable=True)                   # = < >
    value_nm = Column(Float, nullable=False)                   # standardised to nM
    pvalue = Column(Float, nullable=True)                      # -log10(M)
    assay_ref = Column(String, nullable=True)                  # assay / PMID / DOI
    evidence_type = Column(String, nullable=False, default="experimental")
    retrieved_at = Column(DateTime, default=dt.datetime.utcnow)

    compound = relationship("Compound", back_populates="bioactivities")


class Prediction(Base):
    """COMPUTATIONAL prediction. Never experimental evidence."""
    __tablename__ = "predictions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    compound_id = Column(Integer, ForeignKey("compounds.id"), index=True, nullable=False)
    run_id = Column(String, ForeignKey("discovery_runs.id"), index=True, nullable=True)
    target_symbol = Column(String, index=True, nullable=False)
    uniprot_id = Column(String, nullable=True)
    model_name = Column(String, nullable=False)
    model_version = Column(String, nullable=True)
    value = Column(Float, nullable=False)                      # predicted Kd
    units = Column(String, nullable=False, default="nM")
    pkd = Column(Float, nullable=True)                         # 9 - log10(nM)
    normalised_score = Column(Float, nullable=True)            # pKd/10 clipped to [0,1] (display only)
    evidence_type = Column(String, nullable=False, default="computational_prediction")
    params = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=dt.datetime.utcnow)

    compound = relationship("Compound", back_populates="predictions")


class Annotation(Base):
    __tablename__ = "annotations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    compound_id = Column(Integer, ForeignKey("compounds.id"), index=True, nullable=False)
    author = Column(String, nullable=True)
    text = Column(Text, nullable=False)
    created_at = Column(DateTime, default=dt.datetime.utcnow)

    compound = relationship("Compound", back_populates="annotations")


class Collection(Base):
    __tablename__ = "collections"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, unique=True, nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=dt.datetime.utcnow)

    items = relationship("CollectionItem", back_populates="collection", cascade="all, delete-orphan")


class CollectionItem(Base):
    __tablename__ = "collection_items"
    __table_args__ = (UniqueConstraint("collection_id", "compound_id", name="uq_collection_item"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    collection_id = Column(Integer, ForeignKey("collections.id"), index=True, nullable=False)
    compound_id = Column(Integer, ForeignKey("compounds.id"), index=True, nullable=False)
    added_at = Column(DateTime, default=dt.datetime.utcnow)

    collection = relationship("Collection", back_populates="items")


class EvaluationReport(Base):
    __tablename__ = "evaluation_reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    kind = Column(String, index=True, nullable=False)   # generation | similarity | dti
    created_at = Column(DateTime, default=dt.datetime.utcnow)
    parameters = Column(JSON, nullable=True)
    dataset = Column(JSON, nullable=True)
    metrics = Column(JSON, nullable=True)
    limitations = Column(Text, nullable=True)
