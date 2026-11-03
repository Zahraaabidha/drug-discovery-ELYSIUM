"""Re-run the frozen DTI benchmark with the CURRENT code into a separate root (no DB writes, frozen run untouched)."""
import json
import logging
import sys
from pathlib import Path

from app.benchmarks import dti_benchmark as B

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    frozen = Path(sys.argv[1])
    res = json.loads((frozen / "results.json").read_text(encoding="utf-8"))
    cfg = B.BenchConfig(**{k: (tuple(v) if isinstance(v, list) else v) for k, v in res["config"].items()})
    p = B.run(cfg, out_root=Path(sys.argv[2]), store_db=False)
    print(p["run_id"], p["runtime_seconds"])
