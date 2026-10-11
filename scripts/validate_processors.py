from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.processor_model import load_processor


def main() -> int:
    paths = [
        ROOT / "processors" / "processor_A.json",
        ROOT / "processors" / "processor_B.json",
        ROOT / "processors" / "fixtures" / "nine_qubit_schema_not_official.json",
    ]
    for path in paths:
        processor = load_processor(path)
        graph = processor.networkx_graph()
        print(
            processor.identifier,
            "qubits",
            processor.num_qubits,
            "edges",
            graph.number_of_edges(),
            "official",
            processor.provenance.get("official"),
            "status",
            processor.provenance.get("status"),
        )
        if graph.number_of_nodes() == graph.number_of_edges() and graph.number_of_nodes() != 1:
            print(processor.identifier, "edge count equals vertex count; that is allowed only when the graph really has that many edges.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
