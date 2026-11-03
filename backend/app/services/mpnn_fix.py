"""Guarded correction of DeepPurpose's MPNN batch-dependence defect.

DeepPurpose 0.1.5 `encoders.MPNN.forward` offsets the atom->bond index table `agraph` by the cumulative ATOM count (`N_a`)
although `agraph` holds BOND indices, so every molecule except the first in a batch reads other molecules' bond messages and
MPNN_CNN predictions depend on batch composition and order. The only change made here is `+ N_b` instead of `+ N_a`; single
molecule outputs are unchanged. See docs/MPNN_BATCH_DEPENDENCE.md.

The patch is applied only on the exact DeepPurpose version it was validated against and only if the stock source still contains
the defect; otherwise it refuses to run (RuntimeError) rather than silently scoring with an unvalidated model. A synthetic
batch-invariance self-check (random-weight MPNN, fixed seed) must pass before predictions are produced.
"""
from __future__ import annotations

import inspect
import logging
import threading
from importlib.metadata import version

import torch

log = logging.getLogger(__name__)

VALIDATED_DEEPPURPOSE = "0.1.5"
CORRECTION_ID = "mpnn-bond-offset-1"
CORRECTED_VERSION_SUFFIX = f"+elysium.{CORRECTION_ID}"
_DEFECT_MARK = "agraph[i,:atom_num,:] + N_a"

_lock = threading.Lock()
_state = {"applied": False, "verified": False}


def _stock_forward():
    from DeepPurpose.encoders import MPNN
    return MPNN.forward


STOCK_FORWARD = _stock_forward()          # captured at import, before any patch (used by regression tests)


def corrected_forward(self, feature):
    """DeepPurpose MPNN.forward with the atom->bond index table offset by the cumulative bond count."""
    import torch.nn.functional as F
    from DeepPurpose.encoders import create_var, device, index_select_ND
    fatoms, fbonds, agraph, bgraph, N_atoms_bond = feature
    scope, N_a, N_b = [], 0, 0
    fa, fb, ag, bg = [], [], [], []
    for i in range(N_atoms_bond.shape[0]):
        an, bn = int(N_atoms_bond[i][0].item()), int(N_atoms_bond[i][1].item())
        fa.append(fatoms[i, :an, :])
        fb.append(fbonds[i, :bn, :])
        ag.append(agraph[i, :an, :] + N_b)               # stock code adds N_a here (the defect)
        bg.append(bgraph[i, :bn, :] + N_b)
        scope.append((N_a, an))
        N_a += an
        N_b += bn
    fatoms, fbonds = torch.cat(fa, 0), torch.cat(fb, 0)
    agraph, bgraph = torch.cat(ag, 0).long(), torch.cat(bg, 0).long()
    fatoms, fbonds = create_var(fatoms).to(device), create_var(fbonds).to(device)
    agraph, bgraph = create_var(agraph).to(device), create_var(bgraph).to(device)
    binput = self.W_i(fbonds)
    message = F.relu(binput)
    for _ in range(self.mpnn_depth - 1):
        message = F.relu(binput + self.W_h(index_select_ND(message, 0, bgraph).sum(dim=1)))
    nei = index_select_ND(message, 0, agraph).sum(dim=1)
    hid = F.relu(self.W_o(torch.cat([fatoms, nei], dim=1)))
    return torch.stack([torch.mean(hid.narrow(0, s, l), 0) for s, l in scope], 0)


corrected_forward._elysium_correction = CORRECTION_ID

_CHECK_SMILES = ["CCO", "CC(=O)Nc1ccc(O)cc1", "COc1cc2ncnc(Nc3ccc(F)c(Cl)c3)c2cc1OCCCN1CCOCC1", "c1ccc2c(c1)[nH]c1ccccc12", "CCN(CC)CCNC(=O)c1ccc(N)cc1"]


def batch_invariance_selfcheck(tol: float = 1e-4) -> float:
    """Random-weight MPNN, fixed seed: batch vs single and shuffled-order outputs must agree. Returns the max deviation."""
    from DeepPurpose.encoders import MPNN
    from DeepPurpose.utils import mpnn_feature_collate_func, smiles2mpnnfeature
    gen_state = torch.get_rng_state()
    try:
        torch.manual_seed(12345)
        net = MPNN(32, 3).eval()
    finally:
        torch.set_rng_state(gen_state)                     # do not disturb global RNG state
    feats = [smiles2mpnnfeature(s) for s in _CHECK_SMILES]
    n = len(feats)
    with torch.no_grad():
        single = torch.cat([net(mpnn_feature_collate_func([feats[i]])) for i in range(n)])
        batch = net(mpnn_feature_collate_func(feats))
        perm = [3, 0, 4, 2, 1]
        shuffled = net(mpnn_feature_collate_func([feats[i] for i in perm]))
    dev = max(float((batch - single).abs().max()), float((shuffled - single[perm]).abs().max()))
    if not dev < tol:
        raise RuntimeError(f"MPNN batch-invariance self-check FAILED (max deviation {dev:.3g} >= {tol}); refusing to score")
    return dev


def ensure_corrected() -> None:
    """Apply the correction (idempotent) and verify it. Raises RuntimeError if it cannot be applied safely."""
    with _lock:
        if _state["verified"]:
            return
        from DeepPurpose import encoders
        dp = version("DeepPurpose")
        if dp != VALIDATED_DEEPPURPOSE:
            raise RuntimeError(f"MPNN correction was validated on DeepPurpose {VALIDATED_DEEPPURPOSE}, found {dp}; refusing to score")
        if not _state["applied"]:
            src = "".join(inspect.getsource(STOCK_FORWARD).split())
            if _DEFECT_MARK.replace(" ", "") not in src:
                raise RuntimeError("DeepPurpose MPNN.forward no longer matches the validated defective source; refusing to patch")
            encoders.MPNN.forward = corrected_forward
            _state["applied"] = True
        dev = batch_invariance_selfcheck()
        _state["verified"] = True
        log.info("MPNN bond-offset correction %s active (self-check deviation %.2e)", CORRECTION_ID, dev)


def is_active() -> bool:
    return _state["verified"]
