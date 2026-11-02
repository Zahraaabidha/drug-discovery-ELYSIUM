"""FAISS-backed similarity search over the compound registry.

Two views of molecular similarity:
  * fingerprint - Morgan (r=2, 2048 bit) bit vectors in a FAISS binary index (Hamming); the
                  candidate pool is re-ranked with the exact Tanimoto coefficient, which is
                  recoverable from popcounts and Hamming distance.
  * embedding   - ChemBERTa CLS embeddings (unit length) in a FAISS inner-product index
                  (exact cosine similarity).

The index is derived data: it is rebuilt from the relational registry (authoritative) and
embeddings are cached on disk by InChIKey.
"""
from __future__ import annotations

import logging
import os
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

import faiss
import numpy as np
from sqlalchemy.orm import Session

from .. import models as m
from . import chem

log = logging.getLogger(__name__)

INDEX_DIR = Path(os.getenv("ELYSIUM_INDEX_DIR", Path(__file__).resolve().parents[2] / "index_data"))
RERANK_FACTOR = 10  # fingerprint candidates examined per requested neighbour


@dataclass
class Neighbour:
    compound_id: int
    similarity: float
    method: str          # "tanimoto" | "chemberta_cosine"


class SimilarityIndex:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._ids: List[int] = []
        self._inchikeys: List[str] = []
        self._smiles: List[str] = []
        self._fp_bits: Optional[faiss.IndexBinaryFlat] = None
        self._popcount: Optional[np.ndarray] = None
        self._emb_index: Optional[faiss.IndexFlatIP] = None
        self._emb_ids: List[int] = []
        self._cache: Dict[str, np.ndarray] = {}
        self._cache_loaded = False

    # ── embedding cache ────────────────────────────────────────────────
    def _cache_path(self) -> Path:
        return INDEX_DIR / "chemberta_embeddings.npz"

    def _load_cache(self) -> None:
        if self._cache_loaded:
            return
        p = self._cache_path()
        if p.exists():
            try:
                data = np.load(p, allow_pickle=False)
                self._cache = {k: data[k] for k in data.files}
            except Exception:
                log.exception("Could not read embedding cache; it will be rebuilt")
                self._cache = {}
        self._cache_loaded = True

    def _save_cache(self) -> None:
        INDEX_DIR.mkdir(parents=True, exist_ok=True)
        np.savez(self._cache_path(), **self._cache)

    # ── build ──────────────────────────────────────────────────────────
    def rebuild(self, db: Session, with_embeddings: bool = False) -> Dict:
        with self._lock:
            rows = db.query(m.Compound.id, m.Compound.inchikey, m.Compound.canonical_smiles).order_by(m.Compound.id).all()
            self._ids, self._inchikeys, self._smiles = [], [], []
            packed = []
            for cid, ik, smi in rows:
                fp = chem.morgan_fp(smi)
                if fp is None:
                    continue
                self._ids.append(cid)
                self._inchikeys.append(ik)
                self._smiles.append(smi)
                packed.append(chem.fp_to_packed(fp))
            self._fp_bits = faiss.IndexBinaryFlat(chem.FP_BITS)
            if packed:
                arr = np.vstack(packed).astype("uint8")
                self._fp_bits.add(arr)
                self._popcount = np.unpackbits(arr, axis=1).sum(axis=1).astype("int32")
            else:
                self._popcount = np.zeros((0,), dtype="int32")
            self._emb_index = None
            self._emb_ids = []
            info = {"compounds": len(self._ids), "embeddings": 0}
            if with_embeddings:
                info["embeddings"] = self._build_embeddings()
            return info

    def _build_embeddings(self) -> int:
        from .embeddings import embed_smiles
        self._load_cache()
        vecs, ids, dirty = [], [], False
        for cid, ik, smi in zip(self._ids, self._inchikeys, self._smiles):
            vec = self._cache.get(ik)
            if vec is None:
                vec = embed_smiles(smi)
                self._cache[ik] = vec
                dirty = True
            vecs.append(vec)
            ids.append(cid)
        if dirty:
            self._save_cache()
        index = faiss.IndexFlatIP(vecs[0].shape[0]) if vecs else faiss.IndexFlatIP(768)
        if vecs:
            index.add(np.vstack(vecs).astype("float32"))
        self._emb_index, self._emb_ids = index, ids
        return len(ids)

    def ensure_current(self, db: Session, with_embeddings: bool = False) -> None:
        with self._lock:
            n = db.query(m.Compound).count()
            stale = self._fp_bits is None or n != len(self._ids)
            if stale:
                self.rebuild(db, with_embeddings=with_embeddings)
            elif with_embeddings and self._emb_index is None:
                self._build_embeddings()

    # ── search ─────────────────────────────────────────────────────────
    def search_fingerprint(self, smiles: str, k: int = 10, exclude_id: Optional[int] = None) -> List[Neighbour]:
        with self._lock:
            if self._fp_bits is None or self._fp_bits.ntotal == 0:
                return []
            fp = chem.morgan_fp(smiles)
            if fp is None:
                raise chem.InvalidMolecule(f"Cannot parse SMILES: {smiles!r}")
            q = chem.fp_to_packed(fp)[None, :].astype("uint8")
            pool = min(self._fp_bits.ntotal, max(k * RERANK_FACTOR, k + 1))
            _, idx = self._fp_bits.search(q, pool)
            qbits = int(np.unpackbits(q, axis=1).sum())
            qfp = np.unpackbits(q, axis=1)[0].astype(bool)
            out: List[Neighbour] = []
            for i in idx[0]:
                if i < 0:
                    continue
                cid = self._ids[i]
                if exclude_id is not None and cid == exclude_id:
                    continue
                other = np.unpackbits(self._fp_bits.reconstruct(int(i))[None, :], axis=1)[0].astype(bool)
                inter = int(np.logical_and(qfp, other).sum())
                union = qbits + int(self._popcount[i]) - inter
                out.append(Neighbour(cid, (inter / union) if union else 0.0, "tanimoto"))
            out.sort(key=lambda n: n.similarity, reverse=True)
            return out[:k]

    def search_embedding(self, smiles: str, k: int = 10, exclude_id: Optional[int] = None) -> List[Neighbour]:
        from .embeddings import embed_smiles
        with self._lock:
            if self._emb_index is None or self._emb_index.ntotal == 0:
                return []
            q = embed_smiles(smiles)[None, :]
            kk = min(self._emb_index.ntotal, k + (1 if exclude_id is not None else 0))
            sims, idx = self._emb_index.search(q, kk)
            out = []
            for s, i in zip(sims[0], idx[0]):
                if i < 0:
                    continue
                cid = self._emb_ids[i]
                if exclude_id is not None and cid == exclude_id:
                    continue
                out.append(Neighbour(cid, float(s), "chemberta_cosine"))
            return out[:k]

    def exact_tanimoto(self, smiles: str, k: int = 10, exclude_id: Optional[int] = None) -> List[Neighbour]:
        """Brute-force exact Tanimoto top-k (ground truth for evaluating the FAISS path)."""
        from rdkit import DataStructs
        with self._lock:
            qfp = chem.morgan_fp(smiles)
            if qfp is None:
                raise chem.InvalidMolecule(f"Cannot parse SMILES: {smiles!r}")
            fps = [chem.morgan_fp(s) for s in self._smiles]
            sims = DataStructs.BulkTanimotoSimilarity(qfp, fps)
            order = np.argsort(sims)[::-1]
            out = []
            for i in order:
                cid = self._ids[i]
                if exclude_id is not None and cid == exclude_id:
                    continue
                out.append(Neighbour(cid, float(sims[i]), "tanimoto"))
                if len(out) >= k:
                    break
            return out

    @property
    def size(self) -> int:
        return len(self._ids)

    @property
    def has_embeddings(self) -> bool:
        return self._emb_index is not None


index = SimilarityIndex()
