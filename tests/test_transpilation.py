from __future__ import annotations

from pathlib import Path

from qiskit import QuantumCircuit

from src.metrics import circuit_instruction_metrics, explicit_swap_cx_equivalent, routing_overhead_cx
from src.processor_model import load_processor
from src.simulator import execute_counts
from src.transpilation import compile_for_processor, measurement_decoder, validate_compiled_circuit
import pytest

from src.transpilation import TranspilationError


ROOT = Path(__file__).resolve().parents[1]


def _assignment(bitstring: str, decoder: dict[int, int], width: int) -> tuple[int, ...]:
    bits = [int(character) for character in bitstring[::-1]]
    assignment = [0] * width
    for clbit, logical in decoder.items():
        assignment[logical] = bits[clbit]
    return tuple(assignment)


def test_compilation_respects_coupling_and_basis() -> None:
    processor = load_processor(ROOT / "processors" / "processor_A.json")
    circuit = QuantumCircuit(4, 4)
    circuit.h(0)
    circuit.cx(0, 3)
    circuit.measure(range(4), range(4))
    compiled = compile_for_processor(circuit, processor, 1, 7, "sabre", "sabre")
    validate_compiled_circuit(compiled, processor)
    metrics = circuit_instruction_metrics(compiled)
    assert metrics["two_qubit_count"] == metrics["cx_count"] + metrics["explicit_swap_count"]
    assert metrics["operation_count"] != metrics["two_qubit_count"]


def test_long_range_measurement_decoding() -> None:
    processor = load_processor(ROOT / "processors" / "processor_A.json")
    circuit = QuantumCircuit(4, 4)
    circuit.x(0)
    circuit.cx(0, 3)
    circuit.measure(range(4), range(4))
    compiled = compile_for_processor(circuit, processor, 1, 11, "sabre", "sabre")
    decoder = measurement_decoder(compiled, 4)
    counts = execute_counts(compiled, 128, 3, None)
    assert counts
    assert all(_assignment(bitstring, decoder, 4) == (1, 0, 0, 1) for bitstring in counts)


def test_swap_count_is_separate_from_decomposed_routing() -> None:
    circuit = QuantumCircuit(2)
    circuit.swap(0, 1)
    circuit.cx(0, 1)
    circuit.h(0)
    metrics = circuit_instruction_metrics(circuit)
    assert metrics["explicit_swap_count"] == 1
    assert metrics["cx_count"] == 1
    assert metrics["two_qubit_count"] == 2
    assert metrics["operation_count"] == 3
    assert metrics["single_qubit_count"] == 1
    assert explicit_swap_cx_equivalent(metrics["explicit_swap_count"]) == 3
    assert routing_overhead_cx(metrics["cx_count"], metrics["explicit_swap_count"], logical_rzz_count=1) == -1


def test_nine_qubit_schema_fixture_accepts_a_small_circuit() -> None:
    processor = load_processor(ROOT / "processors" / "fixtures" / "nine_qubit_schema_not_official.json")
    circuit = QuantumCircuit(2, 2)
    circuit.h(0)
    circuit.cx(0, 1)
    circuit.measure(range(2), range(2))
    compiled = compile_for_processor(circuit, processor, 1, 3, "sabre", "sabre")
    validate_compiled_circuit(compiled, processor)
    assert compiled.num_qubits == 9
    assert processor.provenance["official"] is False


def test_processor_rejects_a_circuit_that_does_not_fit() -> None:
    processor = load_processor(ROOT / "processors" / "processor_A.json")
    circuit = QuantumCircuit(6, 6)
    circuit.measure(range(6), range(6))
    with pytest.raises(TranspilationError, match="needs 6"):
        compile_for_processor(circuit, processor, 1, 1, "sabre", "sabre")
