from __future__ import annotations

import math
from typing import Sequence

from qiskit import QuantumCircuit

from src.max_cut import MaxCutInstance, cut_value


MEASUREMENT_NAMES = {"measure", "barrier"}


def proportion_standard_error(proportion: float, shots: int) -> float:
    if isinstance(shots, bool) or not isinstance(shots, int) or shots <= 0:
        raise ValueError("Shot count must be a positive integer.")
    if proportion < 0 or proportion > 1:
        raise ValueError("A proportion must lie between 0 and 1.")
    return math.sqrt(proportion * (1.0 - proportion) / shots)


def _computational(instruction_name: str) -> bool:
    return instruction_name not in MEASUREMENT_NAMES


def circuit_instruction_metrics(circuit: QuantumCircuit) -> dict[str, int]:
    operation_count = 0
    two_qubit_count = 0
    cx_count = 0
    swap_count = 0
    measurement_count = 0
    for instruction in circuit.data:
        name = instruction.operation.name
        if name == "measure":
            measurement_count += 1
        if not _computational(name):
            continue
        operation_count += 1
        if instruction.operation.num_qubits == 2:
            two_qubit_count += 1
        if name == "cx":
            cx_count += 1
        if name == "swap":
            swap_count += 1
    return {
        "depth": int(
            circuit.depth(
                filter_function=lambda instruction: _computational(instruction.operation.name)
            )
        ),
        "operation_count": operation_count,
        "two_qubit_count": two_qubit_count,
        "cx_count": cx_count,
        "explicit_swap_count": swap_count,
        "measurement_count": measurement_count,
        "qubit_count": int(circuit.num_qubits),
    }


def _nonnegative_count(value: int, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{label} must be a non-negative integer.")
    return value


def cx_excess_over_rzz_baseline(cx_count: int, logical_rzz_count: int) -> int:
    return _nonnegative_count(cx_count, "cx_count") - 2 * _nonnegative_count(logical_rzz_count, "logical_rzz_count")


def explicit_swap_cx_equivalent(explicit_swap_count: int) -> int:
    return 3 * _nonnegative_count(explicit_swap_count, "explicit_swap_count")


def routing_overhead_cx(cx_count: int, explicit_swap_count: int, logical_rzz_count: int) -> int:
    _nonnegative_count(explicit_swap_count, "explicit_swap_count")
    return cx_excess_over_rzz_baseline(cx_count, logical_rzz_count)


def logical_rzz_count(circuit: QuantumCircuit) -> int:
    return sum(1 for instruction in circuit.data if instruction.operation.name == "rzz")


def summarize_cut_samples(
    samples: Sequence[tuple[float, int]],
    reference_value: float,
    reference_is_exact: bool,
) -> dict[str, object]:
    shots = sum(count for _, count in samples)
    if shots <= 0:
        raise ValueError("Cut samples must contain at least one shot.")
    mean = sum(value * count for value, count in samples) / shots
    second = sum((value ** 2) * count for value, count in samples) / shots
    variance = max(0.0, second - mean ** 2)
    standard_error = math.sqrt(variance / shots)
    best = max(value for value, _ in samples)
    histogram = {f"{value:.10g}": count for value, count in sorted(samples)}
    ratio: float | None
    ratio_error: float | None
    success: float | None
    success_error: float | None
    if reference_value > 0:
        ratio = mean / reference_value
        ratio_error = standard_error / reference_value
    else:
        ratio = None
        ratio_error = None
    if reference_is_exact:
        success_count = sum(
            count for value, count in samples if math.isclose(value, reference_value, rel_tol=0.0, abs_tol=1e-6)
            or value > reference_value + 1e-6
        )
        success = success_count / shots
        success_error = proportion_standard_error(success, shots)
    else:
        success = None
        success_error = None
    return {
        "shots": shots,
        "expected_cut": mean,
        "expected_cut_standard_error": standard_error,
        "best_observed_cut": best,
        "approximation_ratio": ratio,
        "expected_cut_approximation_ratio": ratio,
        "best_cut_approximation_ratio": None if reference_value <= 0 else best / reference_value,
        "approximation_ratio_standard_error": ratio_error,
        "approximation_reference": "exact_optimum" if reference_is_exact else "best_known",
        "optimal_success_probability": success,
        "optimal_success_standard_error": success_error,
        "histogram": histogram,
    }


def samples_from_counts(
    counts: dict[str, int],
    decoder: dict[int, int],
    instance: MaxCutInstance,
) -> list[tuple[float, int]]:
    grouped: dict[float, int] = {}
    width = instance.num_vertices
    for bitstring, count in counts.items():
        if isinstance(count, bool) or not isinstance(count, int) or count < 0:
            raise ValueError("Counts must be non-negative integers.")
        bits = [int(character) for character in str(bitstring)[::-1]]
        assignment = [0] * width
        for clbit, logical in decoder.items():
            if clbit >= len(bits):
                raise ValueError("A count bitstring is shorter than the measured register.")
            assignment[logical] = bits[clbit]
        value = cut_value(instance, assignment)
        grouped[value] = grouped.get(value, 0) + count
    return list(grouped.items())
