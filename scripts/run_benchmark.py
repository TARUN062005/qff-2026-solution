from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.experiment import run_controlled_experiment


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=ROOT / "config" / "experiment.json")
    parser.add_argument("--output-dir", type=Path, default=None)
    args = parser.parse_args()
    manifest = run_controlled_experiment(args.config, args.output_dir)
    print("success", manifest["success"])
    print("official_benchmark_complete", manifest["official_benchmark_complete"])
    artifacts = manifest.get("artifacts", {})
    for name, location in artifacts.items():
        print(name, location)
    return 0 if manifest["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
