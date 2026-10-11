from __future__ import annotations

import math
from pathlib import Path

import numpy as np
from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector

from src.config import load_experiment_config
from src.max_cut import build_instance, cut_value
from src.optimization import optimize_shared_parameters
from src.qaoa import (
    QaoaError,
    bind_qaoa_parameters,
    build_qaoa_circuit,
    expected_cut_from_statevector,
    hamiltonian_cut,
    parameter_count,
)
import pytest


def test_circuit_width_parameters_and_layers() -> None:
    instance = build_instance([0, 1, 2], [(0, 1, 1.0), (1, 2, 2.0)])
    circuit = build_qaoa_circuit(instance, 2, measure=True)
    assert circuit.num_qubits == 3
    assert parameter_count(2) == 4
    assert len(circuit.parameters) == 4
    assert sum(instruction.operation.name == "rzz" for instruction in circuit.data) == 4
    assert sum(instruction.operation.name == "rx" for instruction in circuit.data) == 6
    assert sum(instruction.operation.name == "h" for instruction in circuit.data) == 3
    assert circuit.num_clbits == 3


def test_cost_hamiltonian_matches_cut_for_every_assignment() -> None:
    instance = build_instance([0, 1, 2], [(0, 1, 1.5), (1, 2, 2.0), (0, 2, 0.5)])
    for mask in range(8):
        assignment = tuple((mask >> vertex) & 1 for vertex in range(3))
        assert math.isclose(hamiltonian_cut(instance, assignment), cut_value(instance, assignment))


def test_cost_layer_relative_phase() -> None:
    gamma = math.pi / 2
    circuit = QuantumCircuit(2)
    circuit.rzz(-gamma, 0, 1)
    zero = Statevector.from_label("00").evolve(circuit)
    one = Statevector.from_label("01").evolve(circuit)
    ratio = one.data[1] / zero.data[0]
    assert np.isclose(ratio, np.exp(-1j * gamma))


def test_parameter_binding_uses_names_not_alphabetical_order() -> None:
    instance = build_instance([0, 1], [(0, 1, 2.0)])
    circuit = build_qaoa_circuit(instance, 1, measure=False)
    bound = bind_qaoa_parameters(circuit, [0.3, 0.8], 1)
    assert list(bound.parameters) == []
    rzz_angles = [
        float(instruction.operation.params[0])
        for instruction in bound.data
        if instruction.operation.name == "rzz"
    ]
    rx_angles = [
        float(instruction.operation.params[0])
        for instruction in bound.data
        if instruction.operation.name == "rx"
    ]
    assert rzz_angles == [pytest.approx(-0.6)]
    assert rx_angles == [pytest.approx(1.6), pytest.approx(1.6)]


def test_measurement_mapping_and_plus_state_expectation() -> None:
    instance = build_instance([0, 1], [(0, 1, 2.0)])
    measured = build_qaoa_circuit(instance, 1, measure=True)
    pairs = [
        (
            measured.find_bit(instruction.clbits[0]).index,
            measured.find_bit(instruction.qubits[0]).index,
        )
        for instruction in measured.data
        if instruction.operation.name == "measure"
    ]
    assert pairs == [(0, 0), (1, 1)]
    bound = bind_qaoa_parameters(build_qaoa_circuit(instance, 1, measure=False), [0.0, 0.0], 1)
    first = expected_cut_from_statevector(bound, instance)
    second = expected_cut_from_statevector(bound, instance)
    assert math.isclose(first, 1.0)
    assert math.isclose(first, second)


def test_optional_depth_two_cobyla_does_not_replace_the_baseline() -> None:
    root = Path(__file__).resolve().parents[1]
    baseline = load_experiment_config(root / "config" / "experiment.json", root)
    optional = load_experiment_config(root / "config" / "experiment_p2_provisional.json", root)
    assert baseline.qaoa_depth == 1
    assert baseline.optimizer.method == "grid_then_cobyla"
    assert optional.qaoa_depth == 2
    assert optional.optimizer.method == "cobyla_only"
    assert optional.output_dir != baseline.output_dir
    instance = build_instance([0, 1], [(0, 1, 1.0)], instance_id="depth-two")
    result = optimize_shared_parameters(
        instance,
        2,
        "cobyla_only",
        [0.2, 0.1, 0.2, 0.1],
        2,
        2,
        math.pi,
        math.pi / 2,
        6,
        0.2,
        1e-4,
    )
    assert result["method"] == "cobyla_only"
    assert len(result["parameters"]) == 4
    assert math.isfinite(float(result["ideal_expected_cut"]))
    with pytest.raises(QaoaError, match="depth 1"):
        optimize_shared_parameters(
            instance,
            2,
            "grid_then_cobyla",
            [0.2, 0.1, 0.2, 0.1],
            2,
            2,
            math.pi,
            math.pi / 2,
            6,
            0.2,
            1e-4,
        )


def test_invalid_depth_and_parameter_count() -> None:
    instance = build_instance([0, 1], [(0, 1, 1.0)])
    circuit = build_qaoa_circuit(instance, 1, measure=False)
    with pytest.raises(QaoaError):
        parameter_count(0)
    with pytest.raises(QaoaError):
        bind_qaoa_parameters(circuit, [0.2], 1)
