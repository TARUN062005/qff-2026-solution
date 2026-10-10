from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from src.processor_model import ProcessorModelError, load_processor, processor_from_mapping


ROOT = Path(__file__).resolve().parents[1]


def _payload(name: str) -> dict:
    return json.loads((ROOT / "processors" / name).read_text(encoding="utf-8"))


def test_shipped_processors_load_and_match_their_graphs() -> None:
    processor_a = load_processor(ROOT / "processors" / "processor_A.json")
    processor_b = load_processor(ROOT / "processors" / "processor_B.json")
    graph_a = processor_a.networkx_graph()
    graph_b = processor_b.networkx_graph()
    assert processor_a.num_qubits == 5
    assert graph_a.number_of_edges() == 4
    assert graph_a.number_of_nodes() != graph_a.number_of_edges()
    assert processor_b.num_qubits == 7
    assert graph_b.number_of_edges() == 6
    assert processor_a.provenance["official"] is False
    assert processor_b.provenance["official"] is False
    assert processor_a.noise_model() is not None
    assert processor_b.noise_model() is not None


def test_invalid_qubit_identifier() -> None:
    payload = _payload("processor_A.json")
    payload["coupling_map"] = [[0, 9]]
    with pytest.raises(ProcessorModelError, match="not a qubit"):
        processor_from_mapping(payload)


def test_duplicate_edge_and_self_loop() -> None:
    payload = _payload("processor_A.json")
    payload["coupling_map"] = [[0, 1], [1, 0]]
    with pytest.raises(ProcessorModelError, match="Duplicate"):
        processor_from_mapping(payload)
    payload = _payload("processor_A.json")
    payload["coupling_map"] = [[0, 0]]
    with pytest.raises(ProcessorModelError, match="self-loop"):
        processor_from_mapping(payload)


def test_invalid_noise_configuration() -> None:
    payload = _payload("processor_A.json")
    payload["noise"]["one_qubit_depolarizing_probability"] = 1.5
    with pytest.raises(ProcessorModelError, match="between 0 and 1"):
        processor_from_mapping(payload)
    payload = _payload("processor_A.json")
    payload["noise"]["readout_probabilities"] = [[0.2, 0.2], [0.5, 0.5]]
    with pytest.raises(ProcessorModelError, match="sum to 1"):
        processor_from_mapping(payload)


def test_unsupported_noise_gate() -> None:
    payload = _payload("processor_A.json")
    payload["noise"]["two_qubit_gates"] = ["ecr"]
    with pytest.raises(ProcessorModelError, match="outside the processor basis"):
        processor_from_mapping(payload)


def test_missing_required_field() -> None:
    payload = _payload("processor_B.json")
    del payload["coupling_map"]
    with pytest.raises(ProcessorModelError, match="coupling_map"):
        processor_from_mapping(payload)


def test_directed_edges_are_not_silently_added() -> None:
    payload = copy.deepcopy(_payload("processor_A.json"))
    payload["connectivity"] = "directed"
    payload["gate_directionality"] = "as_listed"
    processor = processor_from_mapping(payload)
    assert processor.directed_edges() == ((0, 1), (1, 2), (2, 3), (3, 4))
