#C:\Users\Aabidha\Desktop\PROJECTS\elysium\elysium\backend\app\schemas.py
from pydantic import BaseModel, Field
from typing import List, Optional
import datetime as dt


class DiscoveryRequest(BaseModel):
    target_id: str
    num_molecules: int = Field(..., ge=1, le=100)
    lipinski_only: bool = False
    seed: Optional[int] = Field(None, description="RNG seed; omit to draw one (it is recorded for reproduction)")

    # Physicochemical filters, applied to generated candidates BEFORE scoring
    min_mw: Optional[float] = Field(None, ge=0)
    max_mw: Optional[float] = Field(None, ge=0)
    min_logp: Optional[float] = None
    max_logp: Optional[float] = None
    max_tpsa: Optional[float] = Field(None, ge=0)
    max_hbd: Optional[int] = Field(None, ge=0)
    max_hba: Optional[int] = Field(None, ge=0)
    max_rotatable_bonds: Optional[int] = Field(None, ge=0)

class ADMETProperties(BaseModel):
    """Basic RDKit physicochemical descriptors + Lipinski rule of five.
    (Name kept for API compatibility. These are NOT ADMET predictions.)"""
    molecular_weight: float
    logp: float
    hbd: int   # hydrogen bond donors
    hba: int   # hydrogen bond acceptors
    rotatable_bonds: int
    tpsa: float
    lipinski_violations: int
    lipinski_pass: bool

class SimilarDrug(BaseModel):
    name: str
    smiles: str
    indication: Optional[str] = None
    similarity: float
    semantic_similarity: Optional[float] = None  # chemBERTa cosine (0–1)

class Molecule(BaseModel):
    smiles: str
    score: float
    source: str = "elysium_dummy_generator"
    notes: Optional[str] = None
    similar_drug: Optional[SimilarDrug] = None
    similar_drug_semantic: Optional[SimilarDrug] = None
    admet: Optional[ADMETProperties] = None   # physicochemical descriptors (alias: physchem)

    # Registry link and evidence labelling
    compound_id: Optional[int] = None
    origin: Optional[str] = None                      # generated | reference | external
    evidence_type: str = "computational_prediction"   # never experimental
    predicted_kd_nm: Optional[float] = None
    pkd: Optional[float] = None
    model: Optional[str] = None
    units: str = "nM"
    nearest_known: List["NearestKnown"] = []


class NearestKnown(BaseModel):
    compound_id: int
    name: Optional[str] = None
    origin: str
    tanimoto: float


Molecule.model_rebuild()


class DiscoveryResponse(BaseModel):
    run_id: str
    target_id: str
    num_molecules: int
    molecules: List[Molecule]
    status: Optional[str] = None
    seed: Optional[int] = None
    params: Optional[dict] = None
    models: Optional[dict] = None
    data_sources: Optional[dict] = None
    metrics: Optional[dict] = None
    evidence_note: str = (
        "Scores are computational DTI predictions (predicted Kd in nM), not experimentally confirmed interactions."
    )

class DiscoveryRunSummary(BaseModel):
    run_id: str
    target_id: str
    num_molecules: int
    created_at: dt.datetime
    status: Optional[str] = None     # completed | failed | legacy_unverified
    seed: Optional[int] = None


class DiscoveryRunListResponse(BaseModel):
    runs: List[DiscoveryRunSummary]    

class MoleculeGraphEntry(BaseModel):
    run_id: str
    molecule_index: int
    smiles: str
    score: float
    similar_drug: Optional[SimilarDrug] = None


class TargetGraphResponse(BaseModel):
    target_id: str
    molecules: List[MoleculeGraphEntry]

class DrugGraphEntry(BaseModel):
    target_id: str
    run_id: str
    molecule_index: int
    smiles: str
    score: float


class DrugGraphResponse(BaseModel):
    drug_name: str
    molecules: List[DrugGraphEntry]
