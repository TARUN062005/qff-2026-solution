from __future__ import annotations

from typing import Sequence

from qiskit import QuantumCircuit
from qiskit.circuit import ParameterVector
from qiskit.quantum_info import SparsePauliOp, Statevector

from src.max_cut import MaxCutError, MaxCutInstance, cut_value


class QaoaError(ValueError):
    pass


def parameter_count(depth: int) -> int:
    if isinstance(depth, bool) or not isinstance(depth, int) or depth < 1:
        raise QaoaError("QAOA depth must be a positive integer.")
    return 2 * depth


def build_qaoa_circuit(instance: MaxCutInstance, depth: int, measure: bool = True) -> QuantumCircuit:
    parameter_count(depth)
    gammas = ParameterVector("gamma", depth)
    betas = ParameterVector("beta", depth)
    circuit = QuantumCircuit(instance.num_vertices, instance.num_vertices if measure else 0)
    circuit.h(range(instance.num_vertices))
    for layer in range(depth):
        for edge in instance.edges:
            circuit.rzz(-(gammas[layer] * edge.weight), edge.u, edge.v)
        for qubit in range(instance.num_vertices):
            circuit.rx(2.0 * betas[layer], qubit)
    if measure:
        circuit.measure(range(instance.num_vertices), range(instance.num_vertices))
    return circuit


def bind_qaoa_parameters(
    circuit: QuantumCircuit,
    values: Sequence[float],
    depth: int,
) -> QuantumCircuit:
    expected = parameter_count(depth)
    if len(values) != expected:
        raise QaoaError(f"Expected {expected} QAOA parameters and received {len(values)}.")
    parsed: list[float] = []
    for value in values:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise QaoaError("QAOA parameters must be finite numbers.")
        number = float(value)
        if number != number or number in (float("inf"), float("-inf")):
            raise QaoaError("QAOA parameters must be finite numbers.")
        parsed.append(number)
    mapping = {}
    for parameter in circuit.parameters:
        name = parameter.name
        if name.startswith("gamma["):
            index = int(name[len("gamma[") : -1])
            mapping[parameter] = parsed[index]
        elif name.startswith("beta["):
            index = int(name[len("beta[") : -1])
            mapping[parameter] = parsed[depth + index]
        else:
            raise QaoaError(f"Unexpected circuit parameter {name}.")
    if len(mapping) != expected:
        raise QaoaError("The circuit parameter set does not match the requested QAOA depth.")
    return circuit.assign_parameters(mapping, inplace=False)


def cost_hamiltonian(instance: MaxCutInstance) -> SparsePauliOp:
    terms: list[tuple[str, float]] = []
    constant = 0.0
    width = instance.num_vertices
    for edge in instance.edges:
        label = ["I"] * width
        label[width - 1 - edge.u] = "Z"
        label[width - 1 - edge.v] = "Z"
        terms.append(("".join(label), -edge.weight / 2.0))
        constant += edge.weight / 2.0
    terms.append(("I" * width, constant))
    return SparsePauliOp.from_list(terms)


def hamiltonian_cut(instance: MaxCutInstance, assignment: Sequence[int]) -> float:
    if len(assignment) != instance.num_vertices:
        raise MaxCutError("Assignment length does not match the Hamiltonian width.")
    label = "".join(str(bit) for bit in reversed(assignment))
    expectation = Statevector.from_label(label).expectation_value(cost_hamiltonian(instance))
    return float(expectation.real)


def expected_cut_from_statevector(circuit: QuantumCircuit, instance: MaxCutInstance) -> float:
    if circuit.num_qubits != instance.num_vertices:
        raise QaoaError("Statevector circuit width does not match the Max-Cut instance.")
    if list(circuit.parameters):
        raise QaoaError("Cannot evaluate a circuit that still has unbound parameters.")
    probabilities = Statevector.from_instruction(circuit).probabilities_dict()
    total = 0.0
    for bitstring, probability in probabilities.items():
        text = str(bitstring).zfill(instance.num_vertices)
        assignment = tuple(int(bit) for bit in text[::-1])
        total += float(probability) * cut_value(instance, assignment)
    return total
