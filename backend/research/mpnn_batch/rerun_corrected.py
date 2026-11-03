"""Re-run the DTI benchmark with the CORRECTED MPNN (production, version-suffixed) into a separate root. No DB writes."""
import json
import logging
import sys
from pathlib import Path

from app.benchmarks import dti_benchmark as B

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    res = json.loads((Path(sys.argv[1]) / "results.json").read_text(encoding="utf-8"))
    cfg = B.BenchConfig(**{k: (tuple(v) if isinstance(v, list) else v) for k, v in res["config"].items()})
    B.CORRECTED_MPNN = True
    p = B.run(cfg, out_root=Path(sys.argv[2]), store_db=False)
    print(p["run_id"], p["runtime_seconds"], p["production_equivalence_check"])
