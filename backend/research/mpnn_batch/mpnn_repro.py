"""Research-only: reproduce and localise the MPNN_CNN batch/order dependence. Does not touch production scoring.

Run from backend/:  venv/Scripts/python.exe -m research.mpnn_batch.mpnn_repro
"""
from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

import numpy as np
import torch

from app.benchmarks.dti_benchmark import MEMBERS
from app.services.dti_deeppurpose import PRETRAINED_DIR
from app.services.targets import resolve_target

SMILES = [
    "COc1cc2ncnc(Nc3ccc(F)c(Cl)c3)c2cc1OCCCN1CCOCC1", "CCO", "CC(=O)Nc1ccc(O)cc1", "CC(C)Cc1ccc(cc1)C(C)C(=O)O",
    "CN1CCC[C@H]1c1cccnc1", "O=C(O)c1ccccc1OC(C)=O", "Cn1cnc2c1c(=O)n(C)c(=O)n2C", "c1ccc2c(c1)[nH]c1ccccc12",
    "CC(=O)Oc1ccccc1C(=O)O", "NC(=O)c1ccccc1", "OC[C@H]1OC(O)[C@H](O)[C@@H](O)[C@@H]1O", "Clc1ccc(cc1)C(c1ccccc1)N1CCNCC1",
    "CCN(CC)CCNC(=O)c1ccc(N)cc1", "COc1ccc2[nH]cc(CCNC(C)=O)c2c1", "FC(F)(F)c1ccc(cc1)Oc1ccccc1", "CCCCCCCC(=O)O",
]


def load(name):
    from DeepPurpose import DTI as models
    return models, models.model_pretrained(str(PRETRAINED_DIR / f"model_{name}"))


def score(models, model, smiles, seq, tmp):
    n = len(smiles)
    r = models.virtual_screening(list(smiles), [seq] * n, model, [f"d{i}" for i in range(n)], ["T"] * n,
                                 convert_y=False, result_folder=tmp + os.sep, verbose=False)
    return np.asarray(r, float).reshape(-1)


def experiments(models, model, seq, tmp, rng):
    n = len(SMILES)
    single = np.array([score(models, model, [s], seq, tmp)[0] for s in SMILES])
    full = score(models, model, SMILES, seq, tmp)
    rev = score(models, model, SMILES[::-1], seq, tmp)[::-1]
    rep = [score(models, model, SMILES, seq, tmp) for _ in range(3)]
    perms = []
    for _ in range(5):
        p = rng.permutation(n)
        out = np.empty(n)
        out[p] = score(models, model, [SMILES[i] for i in p], seq, tmp)
        perms.append(out)
    sub = {k: score(models, model, SMILES[:k], seq, tmp) for k in (2, 4, 8)}
    pos_effect = {}                                    # same molecule (ethanol) placed at each position of a batch
    for pos in (0, 1, 5, 10):
        b = [s for s in SMILES if s != "CCO"]
        b.insert(pos, "CCO")
        pos_effect[pos] = float(score(models, model, b, seq, tmp)[pos])
    mad = lambda a, b: float(np.max(np.abs(np.asarray(a) - np.asarray(b))))
    return {
        "model_training_flag": bool(model.model.training),
        "batch_size_config": int(model.config.get("batch_size", -1)),
        "single_values": single.tolist(),
        "full_vs_single_max_abs": mad(full, single),
        "reversed_vs_full_max_abs": mad(rev, full),
        "repeat_same_batch_max_abs": max(mad(r, rep[0]) for r in rep),
        "random_orders_vs_single_max_abs": [mad(p, single) for p in perms],
        "random_orders_vs_each_other_max_abs": max(mad(a, b) for a in perms for b in perms),
        "prefix_batches_vs_single_max_abs": {str(k): mad(v, single[:k]) for k, v in sub.items()},
        "first_element_of_full_batch_equals_single": bool(abs(full[0] - single[0]) < 1e-6),
        "per_position_deviation_full_batch": (full - single).round(4).tolist(),
        "ethanol_by_position": pos_effect,
        "ethanol_single": float(single[1]),
    }


def fixed_forward(self, feature):
    """Identical to DeepPurpose.encoders.MPNN.forward except agraph is offset by N_b (bond count), not N_a."""
    import torch.nn.functional as F
    from DeepPurpose.encoders import create_var, index_select_ND, device
    fatoms, fbonds, agraph, bgraph, N_atoms_bond = feature
    scope, N_a, N_b = [], 0, 0
    fa, fb, ag, bg = [], [], [], []
    for i in range(N_atoms_bond.shape[0]):
        an, bn = int(N_atoms_bond[i][0].item()), int(N_atoms_bond[i][1].item())
        fa.append(fatoms[i, :an, :]); fb.append(fbonds[i, :bn, :])
        ag.append(agraph[i, :an, :] + N_b)             # <-- only change: bond offset
        bg.append(bgraph[i, :bn, :] + N_b)
        scope.append((N_a, an)); N_a += an; N_b += bn
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


def main():
    seq = resolve_target("EGFR").sequence
    tmp = tempfile.mkdtemp(prefix="mpnn_repro_")
    rng = np.random.default_rng(0)
    res = {"torch": torch.__version__, "n_molecules": len(SMILES), "members": {}}
    try:
        for nm in MEMBERS:
            models, model = load(nm)
            res["members"][nm] = experiments(models, model, seq, tmp, rng)
            print(nm, "full-vs-single", res["members"][nm]["full_vs_single_max_abs"], flush=True)
        from DeepPurpose import encoders
        orig = encoders.MPNN.forward
        encoders.MPNN.forward = fixed_forward
        models, model = load("MPNN_CNN")
        res["mpnn_with_offset_fix"] = experiments(models, model, seq, tmp, np.random.default_rng(0))
        res["mpnn_with_offset_fix"]["fixed_single_equals_original_single_max_abs"] = float(np.max(np.abs(
            np.array(res["mpnn_with_offset_fix"]["single_values"]) - np.array(res["members"]["MPNN_CNN"]["single_values"]))))
        encoders.MPNN.forward = orig
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    out = Path(__file__).with_name("repro_results.json")
    out.write_text(json.dumps(res, indent=1), encoding="utf-8")
    print("wrote", out)


if __name__ == "__main__":
    main()
