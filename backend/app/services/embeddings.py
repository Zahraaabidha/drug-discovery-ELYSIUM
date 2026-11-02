#C:\Users\Aabidha\Desktop\PROJECTS\elysium\elysium\backend\app\services\embeddings.py
"""
chemBERTa-based molecular embeddings for ELYSIUM.

We use a pretrained model (e.g. seyonec/ChemBERTa-zinc-base-v1)
to embed SMILES into a vector space and compute semantic similarity
to a small library of known drugs.
"""

from typing import List, Optional, Tuple

import numpy as np
import torch
from transformers import AutoTokenizer, AutoModel

from ..fda_library import FDA_LIKE_DRUGS
from ..schemas import SimilarDrug


CHEMBERTA_MODEL_NAME = "seyonec/ChemBERTa-zinc-base-v1"


class ChemBERTaEmbedder:
    def __init__(self) -> None:
        self._available = False
        self._tokenizer = None
        self._model = None
        self._device = torch.device("cpu")
        self._drug_embeds: List[Tuple[dict, np.ndarray]] = []

        self._init_model()

    def _init_model(self) -> None:
        try:
            self._tokenizer = AutoTokenizer.from_pretrained(CHEMBERTA_MODEL_NAME)
            self._model = AutoModel.from_pretrained(CHEMBERTA_MODEL_NAME)
            self._model.to(self._device)
            self._model.eval()
            self._available = True

            self._precompute_library_embeddings()
        except Exception as e:
            print("[ChemBERTaEmbedder] Failed to load model, disabling embeddings:", e)
            self._available = False

    def _smiles_to_embedding(self, smiles: str) -> Optional[np.ndarray]:
        if not self._available:
            return None
        try:
            inputs = self._tokenizer(
                smiles,
                return_tensors="pt",
                padding=True,
                truncation=True,
                max_length=128,
            )
            inputs = {k: v.to(self._device) for k, v in inputs.items()}
            with torch.no_grad():
                outputs = self._model(**inputs)
            # Use CLS token representation
            hidden = outputs.last_hidden_state[:, 0, :]
            vec = hidden.cpu().numpy()[0]
            # Normalize to unit vector
            norm = np.linalg.norm(vec)
            if norm == 0:
                return None
            return vec / norm
        except Exception as e:
            print("[ChemBERTaEmbedder] Error embedding SMILES:", e)
            return None

    def _precompute_library_embeddings(self) -> None:
        self._drug_embeds = []
        for drug in FDA_LIKE_DRUGS:
            smi = drug.get("smiles")
            if not smi:
                continue
            emb = self._smiles_to_embedding(smi)
            if emb is not None:
                self._drug_embeds.append((drug, emb))
        if not self._drug_embeds:
            print("[ChemBERTaEmbedder] No valid embeddings for FDA-like drugs")

    def most_similar_drug(self, smiles: str) -> Optional[SimilarDrug]:
        if not self._available or not self._drug_embeds:
            return None

        query = self._smiles_to_embedding(smiles)
        if query is None:
            return None

        best_drug = None
        best_sim = -1.0

        for drug, emb in self._drug_embeds:
            # cosine similarity (dot of unit vectors)
            sim = float(np.dot(query, emb))
            if sim > best_sim:
                best_sim = sim
                best_drug = drug

        if best_drug is None:
            return None

        return SimilarDrug(
            name=best_drug["name"],
            smiles=best_drug["smiles"],
            indication=best_drug.get("indication"),
            similarity=0.0,  # we leave fingerprint similarity for other function
            semantic_similarity=best_sim,
        )


# Single global instance reused across requests
embedder = ChemBERTaEmbedder()


def find_most_semantic_drug(smiles: str) -> Optional[SimilarDrug]:
    """
    Public helper used by the discovery pipeline to get the
    chemBERTa-nearest known drug.
    """
    return embedder.most_similar_drug(smiles)


class EmbeddingUnavailable(RuntimeError):
    """ChemBERTa could not be loaded or failed to embed a molecule."""


def embedding_model_name() -> str:
    return CHEMBERTA_MODEL_NAME


def embed_smiles(smiles: str) -> np.ndarray:
    """Unit-length ChemBERTa CLS embedding. Raises EmbeddingUnavailable on failure (no fallback)."""
    if not embedder._available:
        raise EmbeddingUnavailable("ChemBERTa model is not loaded")
    vec = embedder._smiles_to_embedding(smiles)
    if vec is None:
        raise EmbeddingUnavailable(f"Could not embed SMILES {smiles!r}")
    return vec.astype("float32")
