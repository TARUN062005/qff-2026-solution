from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.reporting import write_report


def main() -> int:
    manifest_path = ROOT / "results" / "manifests" / "experiment_manifest.json"
    if not manifest_path.exists():
        print("No experiment manifest found. Run scripts/run_benchmark.py first.")
        return 1
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("success") is not True:
        print("The manifest records an unsuccessful run. The report was not refreshed.")
        return 1
    destination = ROOT / "report.md"
    write_report(manifest, destination)
    print("report", destination)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
