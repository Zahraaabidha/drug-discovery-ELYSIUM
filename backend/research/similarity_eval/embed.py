"""Research-only: extend a copy of the frozen-ChemBERTa CLS cache with every molecule needed by the similarity experiment."""
import json, logging, sys
from pathlib import Path
import pandas as pd
from app.benchmarks import dti_benchmark as B
from research.dti_features.run_experiment import chemberta_embeddings, FROZEN

PLAN = [("KiKd", t) for t in ("DRD2", "CDK2", "VEGFR2", "ESR1")] + [("IC50", "BACE1")]

def all_smiles(cfg, groups):
    out = set()
    for bench, tgt in PLAN:
        train, scaf_train, scaf_test, evals, _ = B.build_sets(groups, bench, tgt, cfg)
        for df in (train, evals["test_primary"], scaf_train, scaf_test):
            out |= set(df["smiles_std"])
    return sorted(out)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    root = Path(sys.argv[1])
    res = json.loads((FROZEN / "results.json").read_text(encoding="utf-8"))
    cfg = B.BenchConfig(**{k: (tuple(v) if isinstance(v, list) else v) for k, v in res["config"].items()})
    groups = pd.read_csv(Path(cfg.derived_dir) / "groups.csv.gz", low_memory=False)
    s = all_smiles(cfg, groups)
    print("molecules", len(s))
    chemberta_embeddings(s, root / "chemberta_cls_cache.npz")
    print("done")
