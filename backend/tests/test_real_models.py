"""Tests that load the REAL ML models (DeepPurpose pretrained ensemble, ChemBERTa)."""
import numpy as np
import pytest

from app.services.dti_deeppurpose import DeepPurposeScreeningModel
from app.services.targets import resolve_target

pytestmark = pytest.mark.slow


def test_deeppurpose_real_predictions_and_model_info():
    model = DeepPurposeScreeningModel()
    t = resolve_target("EGFR")
    smiles = ["COc1cc2ncnc(Nc3ccc(F)c(Cl)c3)c2cc1OCCCN1CCOCC1", "CCO", "CC(=O)Nc1ccc(O)cc1"]   # gefitinib, ethanol, paracetamol
    res = model.predict(smiles, t.sequence, "EGFR")
    assert len(res) == 3 and all(np.isfinite(r.kd_nm) and r.kd_nm > 0 for r in res)
    assert all(abs(r.pkd - (9 - np.log10(r.kd_nm))) < 1e-9 for r in res)
    assert res[0].kd_nm < res[1].kd_nm                      # a known EGFR inhibitor is predicted tighter than ethanol
    info = model.model_info()
    assert info["output"].startswith("predicted Kd") and len(info["members"]) >= 3 and info["model_version"]


def test_deeppurpose_failure_is_raised_not_replaced(tmp_path, monkeypatch):
    from app.services import dti_deeppurpose
    monkeypatch.setattr(dti_deeppurpose, "PRETRAINED_DIR", tmp_path / "missing")
    with pytest.raises(FileNotFoundError):
        DeepPurposeScreeningModel().predict(["CCO"], resolve_target("EGFR").sequence, "EGFR")


def test_chemberta_embeddings_and_embedding_search(db):
    from app.services.embeddings import embed_smiles
    from app.services.similarity_index import index
    v = embed_smiles("CC(=O)Nc1ccc(O)cc1")
    assert v.shape[0] >= 256 and abs(float(np.linalg.norm(v)) - 1.0) < 1e-4
    index.rebuild(db, with_embeddings=True)
    top = index.search_embedding("CC(=O)Nc1ccc(O)cc1", 3)
    assert top and top[0].similarity > 0.99 and top[0].method == "chemberta_cosine"
