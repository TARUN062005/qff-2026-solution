from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path

import networkx as nx
from qiskit.transpiler import CouplingMap
from qiskit_aer.noise import NoiseModel, ReadoutError, depolarizing_error


class ProcessorModelError(ValueError):
    pass


@dataclass(frozen=True)
class NoiseSpecification:
    label: str
    one_qubit_depolarizing_probability: float
    one_qubit_gates: tuple[str, ...]
    two_qubit_depolarizing_probability: float
    two_qubit_gates: tuple[str, ...]
    readout_probabilities: tuple[tuple[float, float], tuple[float, float]]
    rz_noise: str

    def to_dict(self) -> dict[str, object]:
        return {
            "label": self.label,
            "one_qubit_depolarizing_probability": self.one_qubit_depolarizing_probability,
            "one_qubit_gates": list(self.one_qubit_gates),
            "two_qubit_depolarizing_probability": self.two_qubit_depolarizing_probability,
            "two_qubit_gates": list(self.two_qubit_gates),
            "readout_probabilities": [
                list(row) for row in self.readout_probabilities
            ],
            "rz_noise": self.rz_noise,
        }


@dataclass(frozen=True)
class ProcessorModel:
    name: str
    identifier: str
    role: str
    num_qubits: int
    qubits: tuple[int, ...]
    coupling_edges: tuple[tuple[int, int], ...]
    connectivity: str
    basis_gates: tuple[str, ...]
    gate_directionality: str
    noise: NoiseSpecification | None
    provenance: dict[str, object]
    display_positions: dict[int, tuple[float, float]] | None

    def directed_edges(self) -> tuple[tuple[int, int], ...]:
        if self.connectivity == "directed":
            return self.coupling_edges
        expanded: list[tuple[int, int]] = []
        for u, v in self.coupling_edges:
            expanded.append((u, v))
            expanded.append((v, u))
        return tuple(expanded)

    def coupling_map(self) -> CouplingMap:
        return CouplingMap(list(self.directed_edges()))

    def networkx_graph(self) -> nx.Graph:
        graph = nx.Graph()
        graph.add_nodes_from(self.qubits)
        graph.add_edges_from(self.coupling_edges)
        return graph

    def noise_model(self) -> NoiseModel | None:
        if self.noise is None:
            return None
        model = NoiseModel()
        if self.noise.one_qubit_depolarizing_probability > 0:
            model.add_all_qubit_quantum_error(
                depolarizing_error(self.noise.one_qubit_depolarizing_probability, 1),
                list(self.noise.one_qubit_gates),
            )
        if self.noise.two_qubit_depolarizing_probability > 0:
            model.add_all_qubit_quantum_error(
                depolarizing_error(self.noise.two_qubit_depolarizing_probability, 2),
                list(self.noise.two_qubit_gates),
            )
        model.add_all_qubit_readout_error(
            ReadoutError([list(row) for row in self.noise.readout_probabilities])
        )
        return model


def _mapping(payload: object, label: str) -> dict[str, object]:
    if not isinstance(payload, dict):
        raise ProcessorModelError(f"{label} must be a JSON object.")
    return payload


def _probability(value: object, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ProcessorModelError(f"{label} must be a probability.")
    probability = float(value)
    if not math.isfinite(probability) or probability < 0 or probability > 1:
        raise ProcessorModelError(f"{label} must be between 0 and 1.")
    return probability


def _gate_list(value: object, label: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not value or not all(isinstance(item, str) and item for item in value):
        raise ProcessorModelError(f"{label} must be a non-empty list of gate names.")
    if len(set(value)) != len(value):
        raise ProcessorModelError(f"{label} contains duplicate gate names.")
    return tuple(value)


def _noise(payload: object, basis_gates: tuple[str, ...]) -> NoiseSpecification | None:
    if payload is None:
        return None
    raw = _mapping(payload, "noise")
    label = raw.get("label")
    if not isinstance(label, str) or not label:
        raise ProcessorModelError("noise.label must be a non-empty string.")
    one_qubit_gates = _gate_list(raw.get("one_qubit_gates"), "noise.one_qubit_gates")
    two_qubit_gates = _gate_list(raw.get("two_qubit_gates"), "noise.two_qubit_gates")
    basis = set(basis_gates)
    unknown = [gate for gate in (*one_qubit_gates, *two_qubit_gates) if gate not in basis]
    if unknown:
        raise ProcessorModelError(
            "Noise is attached to gates outside the processor basis: " + ", ".join(unknown)
        )
    readout = raw.get("readout_probabilities")
    if not isinstance(readout, list) or len(readout) != 2:
        raise ProcessorModelError("readout_probabilities must be a 2 by 2 matrix.")
    rows: list[tuple[float, float]] = []
    for row in readout:
        if not isinstance(row, list) or len(row) != 2:
            raise ProcessorModelError("Each readout row must contain two probabilities.")
        parsed = (
            _probability(row[0], "readout probability"),
            _probability(row[1], "readout probability"),
        )
        if not math.isclose(parsed[0] + parsed[1], 1.0, rel_tol=0.0, abs_tol=1e-9):
            raise ProcessorModelError("Each readout row must sum to 1.")
        rows.append(parsed)
    rz_noise = raw.get("rz_noise", "none")
    if rz_noise != "none":
        raise ProcessorModelError("Only rz_noise = none is supported by this noise schema.")
    return NoiseSpecification(
        label=label,
        one_qubit_depolarizing_probability=_probability(
            raw.get("one_qubit_depolarizing_probability"),
            "one_qubit_depolarizing_probability",
        ),
        one_qubit_gates=one_qubit_gates,
        two_qubit_depolarizing_probability=_probability(
            raw.get("two_qubit_depolarizing_probability"),
            "two_qubit_depolarizing_probability",
        ),
        two_qubit_gates=two_qubit_gates,
        readout_probabilities=(rows[0], rows[1]),
        rz_noise="none",
    )


def _positions(payload: object, qubits: tuple[int, ...]) -> dict[int, tuple[float, float]] | None:
    if payload is None:
        return None
    raw = _mapping(payload, "display_positions")
    expected = {str(qubit) for qubit in qubits}
    if set(raw) != expected:
        raise ProcessorModelError("display_positions must contain exactly the processor qubits.")
    positions: dict[int, tuple[float, float]] = {}
    for key, value in raw.items():
        if not isinstance(value, list) or len(value) != 2:
            raise ProcessorModelError("Each display position must be a pair of finite numbers.")
        coordinates: list[float] = []
        for coordinate in value:
            if isinstance(coordinate, bool) or not isinstance(coordinate, (int, float)):
                raise ProcessorModelError("Display coordinates must be finite numbers.")
            number = float(coordinate)
            if not math.isfinite(number):
                raise ProcessorModelError("Display coordinates must be finite numbers.")
            coordinates.append(number)
        positions[int(key)] = (coordinates[0], coordinates[1])
    return positions


def _coupling(
    payload: object,
    qubits: set[int],
    connectivity: str,
) -> tuple[tuple[int, int], ...]:
    if not isinstance(payload, list) or not payload:
        raise ProcessorModelError("coupling_map must be a non-empty list of edges.")
    seen: set[tuple[int, int]] = set()
    edges: list[tuple[int, int]] = []
    for entry in payload:
        if not isinstance(entry, list) or len(entry) != 2:
            raise ProcessorModelError("Each coupling edge must be a pair of qubit identifiers.")
        endpoints: list[int] = []
        for endpoint in entry:
            if isinstance(endpoint, bool) or not isinstance(endpoint, int):
                raise ProcessorModelError("Coupling endpoints must be integers.")
            if endpoint not in qubits:
                raise ProcessorModelError(
                    f"Coupling endpoint {endpoint} is not a qubit of this processor."
                )
            endpoints.append(endpoint)
        u, v = endpoints
        if u == v:
            raise ProcessorModelError("Coupling self-loops are not allowed.")
        key = (u, v) if connectivity == "directed" or u < v else (v, u)
        stored = (u, v) if connectivity == "directed" else key
        if key in seen:
            raise ProcessorModelError(f"Duplicate coupling edge {stored[0]}-{stored[1]}.")
        seen.add(key)
        edges.append(stored)
    return tuple(edges)


def processor_from_mapping(payload: dict[str, object]) -> ProcessorModel:
    name = payload.get("name")
    identifier = payload.get("identifier")
    if not isinstance(name, str) or not name:
        raise ProcessorModelError("name must be a non-empty string.")
    if not isinstance(identifier, str) or not identifier:
        raise ProcessorModelError("identifier must be a non-empty string.")
    num_qubits = payload.get("num_qubits")
    if isinstance(num_qubits, bool) or not isinstance(num_qubits, int) or num_qubits < 1:
        raise ProcessorModelError("num_qubits must be a positive integer.")
    raw_qubits = payload.get("qubits")
    if not isinstance(raw_qubits, list):
        raise ProcessorModelError("qubits must be a list.")
    qubits: list[int] = []
    for qubit in raw_qubits:
        if isinstance(qubit, bool) or not isinstance(qubit, int):
            raise ProcessorModelError("Qubit identifiers must be integers.")
        qubits.append(qubit)
    if qubits != list(range(num_qubits)):
        raise ProcessorModelError("qubits must be exactly 0, 1, ..., num_qubits-1.")
    connectivity = payload.get("connectivity")
    directionality = payload.get("gate_directionality")
    if connectivity == "undirected" and directionality != "bidirectional":
        raise ProcessorModelError(
            "Undirected processors must set gate_directionality to bidirectional."
        )
    if connectivity == "directed" and directionality != "as_listed":
        raise ProcessorModelError("Directed processors must set gate_directionality to as_listed.")
    if connectivity not in ("undirected", "directed"):
        raise ProcessorModelError("connectivity must be undirected or directed.")
    basis_gates = _gate_list(payload.get("basis_gates"), "basis_gates")
    if not any(gate in {"cx", "cz", "ecr", "rzz"} for gate in basis_gates):
        raise ProcessorModelError("basis_gates must include a two-qubit gate.")
    provenance = payload.get("provenance")
    provenance_map = _mapping(provenance, "provenance")
    if not isinstance(provenance_map.get("status"), str) or not provenance_map.get("status"):
        raise ProcessorModelError("provenance.status must be a non-empty string.")
    if not isinstance(provenance_map.get("official"), bool):
        raise ProcessorModelError("provenance.official must be a boolean.")
    if not isinstance(provenance_map.get("source"), str) or not provenance_map.get("source"):
        raise ProcessorModelError("provenance.source must be a non-empty string.")
    if provenance_map.get("official") is True:
        kit_file = provenance_map.get("challenge_kit_file")
        if not isinstance(kit_file, str) or not kit_file.strip():
            raise ProcessorModelError(
                "official processors require provenance.challenge_kit_file naming the issued Challenge Kit file."
            )
    role = payload.get("role", "unspecified")
    if not isinstance(role, str):
        raise ProcessorModelError("role must be a string.")
    return ProcessorModel(
        name=name,
        identifier=identifier,
        role=role,
        num_qubits=num_qubits,
        qubits=tuple(qubits),
        coupling_edges=_coupling(payload.get("coupling_map"), set(qubits), connectivity),
        connectivity=connectivity,
        basis_gates=basis_gates,
        gate_directionality=str(directionality),
        noise=_noise(payload.get("noise"), basis_gates),
        provenance=provenance_map,
        display_positions=_positions(payload.get("display_positions"), tuple(qubits)),
    )


def load_processor(path: Path) -> ProcessorModel:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ProcessorModelError(f"Could not parse processor file {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise ProcessorModelError(f"Processor file {path} must be a JSON object.")
    return processor_from_mapping(payload)
