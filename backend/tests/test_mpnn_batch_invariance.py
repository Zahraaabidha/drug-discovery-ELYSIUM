"""Batch/order invariance of the DeepPurpose ensemble members (see docs/EVALUATION.md 4.7 and docs/MPNN_BATCH_DEPENDENCE.md).

Upstream DeepPurpose MPNN.forward offsets the atom->bond index graph by the cumulative ATOM count instead of the BOND count,
so every molecule but the first in a DataLoader batch reads the wrong bond messages. The stock MPNN_CNN test is therefore a
documented by running the STOCK forward explicitly (strict xfail); production scoring applies app.services.mpnn_fix (bond offset,
version-guarded, self-checked) and must be invariant and carry the corrected model version.
"""
import numpy as np
import pytest
import torch

from app.services import mpnn_fix
from app.services.mpnn_fix import STOCK_FORWARD, corrected_forward as fixed_forward
from research.mpnn_batch.mpnn_repro import SMILES, load, score

MEMBERS_OK = ["CNN_CNN", "Morgan_CNN", "Morgan_AAC", "Daylight_AAC"]
TOL = 1e-4


def _seq():
    from app.services.targets import resolve_target
    return resolve_target("EGFR").sequence


def _invariance_gaps(models, model, tmp):
    seq, rng = _seq(), np.random.default_rng(1)
    single = np.array([score(models, model, [s], seq, tmp)[0] for s in SMILES])
    perm = rng.permutation(len(SMILES))
    shuffled = np.empty(len(SMILES))
    shuffled[perm] = score(models, model, [SMILES[i] for i in perm], seq, tmp)
    full = score(models, model, SMILES, seq, tmp)
    rev = score(models, model, SMILES[::-1], seq, tmp)[::-1]
    again = score(models, model, SMILES, seq, tmp)
    return {"batch_vs_single": np.abs(full - single).max(), "shuffled_vs_single": np.abs(shuffled - single).max(),
            "reversed_vs_batch": np.abs(rev - full).max(), "repeat": np.abs(again - full).max()}


def test_synthetic_mpnn_offset_defect_and_fix():
    """Fast, no pretrained weights: random-weight MPNN. Stock forward is batch dependent; bond-offset forward is not."""
    from DeepPurpose.encoders import MPNN
    from DeepPurpose.utils import mpnn_feature_collate_func, smiles2mpnnfeature
    torch.manual_seed(0)
    net = MPNN(32, 3).eval()
    feats = [smiles2mpnnfeature(s) for s in SMILES[:8]]
    batch = lambda idx: mpnn_feature_collate_func([feats[i] for i in idx])
    stock_single = torch.cat([STOCK_FORWARD(net, batch([i])) for i in range(8)])
    stock_batch = STOCK_FORWARD(net, batch(range(8)))
    fix_single = torch.cat([fixed_forward(net, batch([i])) for i in range(8)])
    fix_batch = fixed_forward(net, batch(range(8)))
    assert torch.allclose(stock_batch[0], stock_single[0], atol=1e-6)            # first molecule is always right
    assert (stock_batch - stock_single).abs().max() > 1e-3                        # defect present in stock code
    assert torch.allclose(fix_single, stock_single, atol=1e-6)                    # fix preserves single-molecule values
    assert torch.allclose(fix_batch, fix_single, atol=1e-5)                       # fix is batch invariant
    perm = torch.randperm(8)
    assert torch.allclose(fixed_forward(net, batch(perm.tolist())), fix_batch[perm], atol=1e-5)


@pytest.mark.slow
@pytest.mark.parametrize("member", MEMBERS_OK)
def test_other_members_are_invariant(member, tmp_path):
    models, model = load(member)
    gaps = _invariance_gaps(models, model, str(tmp_path))
    assert all(v < TOL for v in gaps.values()), gaps


@pytest.mark.slow
def test_mpnn_is_deterministic_for_identical_input(tmp_path, monkeypatch):
    from DeepPurpose import encoders
    monkeypatch.setattr(encoders.MPNN, "forward", STOCK_FORWARD)
    models, model = load("MPNN_CNN")
    assert _invariance_gaps(models, model, str(tmp_path))["repeat"] == 0.0


@pytest.mark.slow
@pytest.mark.xfail(strict=True, reason="upstream DeepPurpose MPNN.forward offsets agraph by atom count, not bond count")
def test_stock_mpnn_cnn_is_batch_invariant(tmp_path, monkeypatch):
    from DeepPurpose import encoders
    monkeypatch.setattr(encoders.MPNN, "forward", STOCK_FORWARD)
    models, model = load("MPNN_CNN")
    gaps = _invariance_gaps(models, model, str(tmp_path))
    assert gaps["batch_vs_single"] < TOL and gaps["shuffled_vs_single"] < TOL and gaps["reversed_vs_batch"] < TOL, gaps


@pytest.mark.slow
def test_mpnn_with_bond_offset_patch_is_batch_invariant(tmp_path, monkeypatch):
    from DeepPurpose import encoders
    monkeypatch.setattr(encoders.MPNN, "forward", fixed_forward)
    models, model = load("MPNN_CNN")
    gaps = _invariance_gaps(models, model, str(tmp_path))
    assert all(v < TOL for v in gaps.values()), gaps


@pytest.mark.slow
def test_production_ensemble_is_order_and_batch_invariant():
    from app.services.dti_deeppurpose import DeepPurposeScreeningModel
    m, seq = DeepPurposeScreeningModel(), _seq()
    a = np.array([r.pkd for r in m.predict(SMILES, seq, "EGFR")])
    b = np.array([r.pkd for r in m.predict(SMILES[::-1], seq, "EGFR")])[::-1]
    c = np.array([m.predict([s], seq, "EGFR")[0].pkd for s in SMILES])
    assert np.abs(a - b).max() < TOL and np.abs(a - c).max() < TOL


def test_selfcheck_passes_and_detects_stock_defect(monkeypatch):
    from DeepPurpose import encoders
    assert mpnn_fix.batch_invariance_selfcheck() < 1e-4
    monkeypatch.setattr(encoders.MPNN, "forward", STOCK_FORWARD)
    with pytest.raises(RuntimeError, match="self-check FAILED"):
        mpnn_fix.batch_invariance_selfcheck()


def test_guard_refuses_unvalidated_deeppurpose_version(monkeypatch):
    monkeypatch.setitem(mpnn_fix._state, "verified", False)
    monkeypatch.setattr(mpnn_fix, "version", lambda _: "9.9.9")
    with pytest.raises(RuntimeError, match="validated on DeepPurpose"):
        mpnn_fix.ensure_corrected()


def test_model_version_distinguishes_corrected_predictions():
    from app.services.dti_deeppurpose import DeepPurposeScreeningModel
    info = DeepPurposeScreeningModel().model_info()
    assert info["model_version"] == f"{info['base_package_version']}+elysium.mpnn-bond-offset-1" and info["corrections"]
