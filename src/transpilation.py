from __future__ import annotations

from qiskit import QuantumCircuit, transpile

from src.metrics import (
    circuit_instruction_metrics,
    cx_excess_over_rzz_baseline,
    explicit_swap_cx_equivalent,
    logical_rzz_count,
    routing_overhead_cx,
)
from src.processor_model import ProcessorModel


class TranspilationError(RuntimeError):
    pass


def compile_for_processor(
    circuit: QuantumCircuit,
    processor: ProcessorModel,
    optimization_level: int,
    seed_transpiler: int,
    layout_method: str,
    routing_method: str,
) -> QuantumCircuit:
    if circuit.num_qubits > processor.num_qubits:
        raise TranspilationError(
            f"{processor.name} has {processor.num_qubits} qubits and the circuit needs {circuit.num_qubits}."
        )
    compiled = transpile(
        circuit,
        coupling_map=processor.coupling_map(),
        basis_gates=list(processor.basis_gates),
        optimization_level=optimization_level,
        seed_transpiler=seed_transpiler,
        layout_method=layout_method,
        routing_method=routing_method,
    )
    validate_compiled_circuit(compiled, processor)
    return compiled


def validate_compiled_circuit(circuit: QuantumCircuit, processor: ProcessorModel) -> None:
    allowed_edges = set(processor.directed_edges())
    allowed_gates = set(processor.basis_gates)
    for instruction in circuit.data:
        name = instruction.operation.name
        if name in {"measure", "barrier"}:
            continue
        if name not in allowed_gates:
            raise TranspilationError(
                f"Compiled circuit contains {name}, which is outside the {processor.name} basis."
            )
        if instruction.operation.num_qubits == 2:
            qubit_0 = circuit.find_bit(instruction.qubits[0]).index
            qubit_1 = circuit.find_bit(instruction.qubits[1]).index
            if (qubit_0, qubit_1) not in allowed_edges:
                raise TranspilationError(
                    f"{name} on physical qubits {qubit_0} and {qubit_1} is outside the {processor.name} coupling map."
                )


def measurement_decoder(circuit: QuantumCircuit, num_logical: int) -> dict[int, int]:
    if circuit.layout is None:
        measured = _measurement_pairs(circuit)
        if set(measured) != set(range(num_logical)):
            raise TranspilationError("The uncompiled circuit does not measure every logical qubit once.")
        return {clbit: clbit for clbit in range(num_logical)}
    final_layout = list(circuit.layout.final_index_layout(filter_ancillas=True))
    if len(final_layout) < num_logical:
        raise TranspilationError("The transpiler layout does not cover every logical qubit.")
    physical_to_logical = {final_layout[logical]: logical for logical in range(num_logical)}
    decoder: dict[int, int] = {}
    for clbit, physical in _measurement_pairs(circuit).items():
        if physical not in physical_to_logical:
            continue
        decoder[clbit] = physical_to_logical[physical]
    if set(decoder.values()) != set(range(num_logical)):
        raise TranspilationError("Transpiled measurements do not cover every logical qubit exactly once.")
    return decoder


def _measurement_pairs(circuit: QuantumCircuit) -> dict[int, int]:
    pairs: dict[int, int] = {}
    for instruction in circuit.data:
        if instruction.operation.name != "measure":
            continue
        clbit = circuit.find_bit(instruction.clbits[0]).index
        qubit = circuit.find_bit(instruction.qubits[0]).index
        if clbit in pairs:
            raise TranspilationError(f"Classical bit {clbit} is measured more than once.")
        pairs[clbit] = qubit
    return pairs


def used_physical_qubits(circuit: QuantumCircuit) -> set[int]:
    used: set[int] = set()
    for instruction in circuit.data:
        if instruction.operation.name == "barrier":
            continue
        for qubit in instruction.qubits:
            used.add(circuit.find_bit(qubit).index)
    return used


def resource_report(
    logical_circuit: QuantumCircuit,
    compiled_circuit: QuantumCircuit,
    compilation_seconds: float,
) -> dict[str, object]:
    logical = circuit_instruction_metrics(logical_circuit)
    compiled = circuit_instruction_metrics(compiled_circuit)
    rzz_count = logical_rzz_count(logical_circuit)
    decoder = measurement_decoder(compiled_circuit, logical_circuit.num_qubits)
    if compiled_circuit.layout is None:
        layout = list(range(logical_circuit.num_qubits))
    else:
        layout = list(compiled_circuit.layout.final_index_layout(filter_ancillas=True))
    occupied = used_physical_qubits(compiled_circuit)
    logical_physical = set(layout[: logical_circuit.num_qubits])
    return {
        "logical_depth": logical["depth"],
        "transpiled_depth": compiled["depth"],
        "logical_operation_count": logical["operation_count"],
        "transpiled_operation_count": compiled["operation_count"],
        "logical_single_qubit_count": logical["single_qubit_count"],
        "transpiled_single_qubit_count": compiled["single_qubit_count"],
        "logical_two_qubit_count": logical["two_qubit_count"],
        "transpiled_two_qubit_count": compiled["two_qubit_count"],
        "cx_count": compiled["cx_count"],
        "explicit_swap_count": compiled["explicit_swap_count"],
        "explicit_swap_cx_equivalent": explicit_swap_cx_equivalent(compiled["explicit_swap_count"]),
        "logical_rzz_count": rzz_count,
        "cx_excess_over_rzz_baseline": cx_excess_over_rzz_baseline(compiled["cx_count"], rzz_count),
        "routing_overhead_cx": routing_overhead_cx(
            compiled["cx_count"],
            compiled["explicit_swap_count"],
            rzz_count,
        ),
        "logical_qubits": logical_circuit.num_qubits,
        "physical_qubits_allocated": compiled_circuit.num_qubits,
        "physical_qubits_used": len(occupied),
        "ancillas_used": len(occupied - logical_physical),
        "compilation_seconds": compilation_seconds,
        "final_index_layout": layout[: logical_circuit.num_qubits],
        "measurement_decoder": [[clbit, logical] for clbit, logical in sorted(decoder.items())],
    }
