"""Compare a re-run against the frozen run: file hashes, predictions, and every numeric value in results.json."""
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

IGNORE = {"run_id", "created_utc", "runtime_seconds", "code_sha256", "artifacts", "production_equivalence_check"}


def walk(a, b, path, diffs, stats):
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b)):
            if not path and k in IGNORE:
                continue
            if k not in a or k not in b:
                diffs.append((path + "/" + k, "missing in one run")); continue
            walk(a[k], b[k], path + "/" + k, diffs, stats)
    elif isinstance(a, list) and isinstance(b, list) and len(a) == len(b):
        for i, (x, y) in enumerate(zip(a, b)):
            walk(x, y, f"{path}[{i}]", diffs, stats)
    elif isinstance(a, (int, float)) and isinstance(b, (int, float)) and not isinstance(a, bool):
        stats["numeric"] += 1
        d = abs(a - b)
        stats["max_abs"] = max(stats["max_abs"], d)
        if d > 0:
            stats["nonzero"] += 1
            diffs.append((path, f"{a} vs {b}"))
    else:
        stats["other"] += 1
        if a != b:
            diffs.append((path, f"{a!r} vs {b!r}"))


def main(frozen: Path, rerun: Path):
    fa, fb = json.loads((frozen / "results.json").read_text("utf-8")), json.loads((rerun / "results.json").read_text("utf-8"))
    diffs, stats = [], {"numeric": 0, "other": 0, "max_abs": 0.0, "nonzero": 0}
    walk(fa, fb, "", diffs, stats)
    pa, pb = pd.read_csv(frozen / "predictions.csv.gz"), pd.read_csv(rerun / "predictions.csv.gz")
    same_shape = pa.shape == pb.shape and (pa[["bench", "target", "test_set", "inchikey", "model"]].values == pb[["bench", "target", "test_set", "inchikey", "model"]].values).all()
    pred_diff = float(np.abs(pa.pred_pvalue.to_numpy() - pb.pred_pvalue.to_numpy()).max()) if same_shape else None
    out = {"frozen_run": frozen.name, "rerun": rerun.name,
           "dataset_files_sha256_equal": fa["dataset_files_sha256"] == fb["dataset_files_sha256"],
           "software_versions_equal": fa["software_versions"] == fb["software_versions"],
           "config_equal": fa["config"] == fb["config"],
           "predictions_rows": [len(pa), len(pb)], "predictions_keys_and_order_identical": bool(same_shape),
           "predictions_max_abs_diff_pvalue": pred_diff,
           "predictions_file_sha256": [hashlib.sha256((frozen / "predictions.csv.gz").read_bytes()).hexdigest(), hashlib.sha256((rerun / "predictions.csv.gz").read_bytes()).hexdigest()],
           "results_json_values_compared": stats["numeric"], "results_json_nonnumeric_compared": stats["other"],
           "results_json_max_abs_numeric_diff": stats["max_abs"], "results_json_differing_values": len(diffs),
           "first_differences": diffs[:15],
           "code_sha256": [fa["code_sha256"], fb["code_sha256"]],
           "production_equivalence_check": [fa["production_equivalence_check"], fb["production_equivalence_check"]]}
    Path(__file__).with_name("rerun_comparison.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]))
