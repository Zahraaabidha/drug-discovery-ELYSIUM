#C:\Users\Aabidha\Desktop\PROJECTS\elysium\elysium\backend\app\schemas.py
from pydantic import BaseModel, Field
from typing import List, Optional
import datetime as dt


class DiscoveryRequest(BaseModel):
    target_id: str
    num_molecules: int = Field(..., ge=1, le=100)
    lipinski_only: bool = False

class ADMETProperties(BaseModel):
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
    admet: Optional[ADMETProperties] = None



class DiscoveryResponse(BaseModel):
    run_id: str
    target_id: str
    num_molecules: int
    molecules: List[Molecule]

class DiscoveryRunSummary(BaseModel):
    run_id: str
    target_id: str
    num_molecules: int
    created_at: dt.datetime


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
