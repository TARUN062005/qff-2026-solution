from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

import networkx as nx


EXHAUSTIVE_VERTEX_LIMIT = 20


class MaxCutError(ValueError):
    pass


@dataclass(frozen=True)
class WeightedEdge:
    u: int
    v: int
    weight: float


@dataclass(frozen=True)
class ClassicalReference:
    objective_value: float
    assignment: tuple[int, ...]
    cut_value: float
    method: str
    optimal: bool


@dataclass(frozen=True)
class MaxCutInstance:
    instance_id: str
    official: bool
    provenance: str
    vertices: tuple[int, ...]
    edges: tuple[WeightedEdge, ...]
    constraints: tuple[str, ...]
    connected: bool
    problem_code: str
    dashboard_identifier: str
    track: str
    title: str

    @property
    def num_vertices(self) -> int:
        return len(self.vertices)

    @property
    def num_edges(self) -> int:
        return len(self.edges)

    def to_dict(self) -> dict[str, object]:
        return {
            "instance_id": self.instance_id,
            "official": self.official,
            "problem_statement": {
                "track": self.track,
                "organizer_code": self.problem_code,
                "dashboard_identifier": self.dashboard_identifier,
                "title": self.title,
            },
            "provenance": self.provenance,
            "vertices": list(self.vertices),
            "edges": [
                {"u": edge.u, "v": edge.v, "weight": edge.weight} for edge in self.edges
            ],
            "constraints": list(self.constraints),
            "connected": self.connected,
        }


def _require_mapping(payload: object, label: str) -> dict[str, object]:
    if not isinstance(payload, dict):
        raise MaxCutError(f"{label} must be a JSON object.")
    return payload


def _vertex_list(values: object) -> tuple[int, ...]:
    if not isinstance(values, list) or not values:
        raise MaxCutError("vertices must be a non-empty list.")
    vertices: list[int] = []
    for value in values:
        if isinstance(value, bool) or not isinstance(value, int):
            raise MaxCutError("Vertex identifiers must be integers.")
        vertices.append(value)
    if len(set(vertices)) != len(vertices):
        raise MaxCutError("Vertex identifiers must be unique.")
    expected = list(range(len(vertices)))
    if vertices != expected:
        raise MaxCutError(
            "Vertex identifiers must be exactly 0, 1, ..., n-1 in that order."
        )
    return tuple(vertices)


def _weight(value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise MaxCutError("Edge weights must be finite numbers.")
    weight = float(value)
    if not math.isfinite(weight):
        raise MaxCutError("Edge weights must be finite numbers.")
    if weight < 0:
        raise MaxCutError(
            "Negative edge weights are rejected because the supplied PS-O1 documents do not permit them."
        )
    return weight


def _edges(values: object, vertex_count: int) -> tuple[WeightedEdge, ...]:
    if not isinstance(values, list):
        raise MaxCutError("edges must be a list.")
    seen: set[tuple[int, int]] = set()
    edges: list[WeightedEdge] = []
    for entry in values:
        entry_map = _require_mapping(entry, "edge")
        for field in ("u", "v", "weight"):
            if field not in entry_map:
                raise MaxCutError(f"Edge is missing {field}.")
        endpoints: list[int] = []
        for field in ("u", "v"):
            endpoint = entry_map[field]
            if isinstance(endpoint, bool) or not isinstance(endpoint, int):
                raise MaxCutError("Edge endpoints must be integers.")
            if endpoint < 0 or endpoint >= vertex_count:
                raise MaxCutError(
                    f"Edge endpoint {endpoint} is not in the vertex set."
                )
            endpoints.append(endpoint)
        u, v = endpoints
        if u == v:
            raise MaxCutError("Self-loops are not allowed.")
        key = (u, v) if u < v else (v, u)
        if key in seen:
            raise MaxCutError(f"Duplicate undirected edge {key[0]}-{key[1]}.")
        seen.add(key)
        edges.append(WeightedEdge(u, v, _weight(entry_map["weight"])))
    return tuple(edges)


def _connected(vertices: tuple[int, ...], edges: tuple[WeightedEdge, ...]) -> bool:
    graph = nx.Graph()
    graph.add_nodes_from(vertices)
    graph.add_edges_from((edge.u, edge.v) for edge in edges)
    return bool(nx.is_connected(graph))


def build_instance(
    vertices: Sequence[int],
    edges: Sequence[tuple[int, int, float]],
    instance_id: str = "in-memory",
    official: bool = False,
    provenance: str = "Constructed in memory.",
    constraints: Sequence[str] | None = None,
    problem_code: str = "O1",
    dashboard_identifier: str = "PS-O1",
    track: str = "Quantum Optimization",
    title: str = "Max-Cut on Weighted Graphs",
) -> MaxCutInstance:
    payload = {
        "instance_id": instance_id,
        "official": official,
        "provenance": provenance,
        "vertices": list(vertices),
        "edges": [{"u": u, "v": v, "weight": weight} for u, v, weight in edges],
        "constraints": list(constraints or ()),
        "problem_statement": {
            "track": track,
            "organizer_code": problem_code,
            "dashboard_identifier": dashboard_identifier,
            "title": title,
        },
    }
    return instance_from_mapping(payload)


def instance_from_mapping(payload: dict[str, object]) -> MaxCutInstance:
    instance_id = payload.get("instance_id")
    if not isinstance(instance_id, str) or not instance_id:
        raise MaxCutError("instance_id must be a non-empty string.")
    official = payload.get("official")
    if not isinstance(official, bool):
        raise MaxCutError("official must be a boolean.")
    provenance = payload.get("provenance", "")
    if not isinstance(provenance, str):
        raise MaxCutError("provenance must be a string.")
    vertices = _vertex_list(payload.get("vertices"))
    edges = _edges(payload.get("edges"), len(vertices))
    raw_constraints = payload.get("constraints", [])
    if not isinstance(raw_constraints, list) or not all(
        isinstance(item, str) for item in raw_constraints
    ):
        raise MaxCutError("constraints must be a list of strings.")
    statement = payload.get("problem_statement", {})
    if statement is None:
        statement = {}
    statement_map = _require_mapping(statement, "problem_statement") if statement else {}
    track = str(statement_map.get("track", "Quantum Optimization"))
    problem_code = str(statement_map.get("organizer_code", "O1"))
    dashboard_identifier = str(statement_map.get("dashboard_identifier", "PS-O1"))
    title = str(statement_map.get("title", "Max-Cut on Weighted Graphs"))
    return MaxCutInstance(
        instance_id=instance_id,
        official=official,
        provenance=provenance,
        vertices=vertices,
        edges=edges,
        constraints=tuple(raw_constraints),
        connected=_connected(vertices, edges),
        problem_code=problem_code,
        dashboard_identifier=dashboard_identifier,
        track=track,
        title=title,
    )


def load_instance(path: Path) -> MaxCutInstance:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise MaxCutError(f"Could not parse Max-Cut instance {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise MaxCutError(f"Max-Cut instance {path} must be a JSON object.")
    return instance_from_mapping(payload)


def cut_value(instance: MaxCutInstance, assignment: Sequence[int]) -> float:
    if len(assignment) != instance.num_vertices:
        raise MaxCutError(
            f"Assignment length {len(assignment)} does not match {instance.num_vertices} vertices."
        )
    for bit in assignment:
        if isinstance(bit, bool) or bit not in (0, 1):
            raise MaxCutError("Assignment entries must be 0 or 1.")
    total = 0.0
    for edge in instance.edges:
        if assignment[edge.u] != assignment[edge.v]:
            total += edge.weight
    return total


def _confirmed_reference(
    instance: MaxCutInstance,
    assignment: tuple[int, ...],
    objective_value: float,
    method: str,
    optimal: bool,
) -> ClassicalReference:
    recomputed = cut_value(instance, assignment)
    if not math.isclose(recomputed, objective_value, rel_tol=0.0, abs_tol=1e-9):
        raise MaxCutError(
            "Classical reference assignment does not reproduce the reported objective."
        )
    return ClassicalReference(
        objective_value=objective_value,
        assignment=assignment,
        cut_value=recomputed,
        method=method,
        optimal=optimal,
    )


def _exhaustive(instance: MaxCutInstance) -> ClassicalReference:
    best_value = -math.inf
    best_assignment: tuple[int, ...] | None = None
    for mask in range(1 << instance.num_vertices):
        assignment = tuple((mask >> vertex) & 1 for vertex in range(instance.num_vertices))
        value = cut_value(instance, assignment)
        if value > best_value:
            best_value = value
            best_assignment = assignment
    if best_assignment is None:
        raise MaxCutError("Exhaustive search did not evaluate an assignment.")
    return _confirmed_reference(
        instance,
        best_assignment,
        best_value,
        "exhaustive_enumeration",
        True,
    )


def _local_search(instance: MaxCutInstance) -> ClassicalReference:
    n = instance.num_vertices
    starts = [
        [0 for _ in range(n)],
        [vertex % 2 for vertex in range(n)],
        [1 if vertex == 0 else 0 for vertex in range(n)],
    ]
    best_assignment: tuple[int, ...] | None = None
    best_value = -math.inf
    for start in starts:
        current = list(start)
        current_value = cut_value(instance, current)
        improved = True
        while improved:
            improved = False
            for vertex in range(n):
                current[vertex] ^= 1
                candidate = cut_value(instance, current)
                if candidate > current_value + 1e-12:
                    current_value = candidate
                    improved = True
                else:
                    current[vertex] ^= 1
        if current_value > best_value:
            best_value = current_value
            best_assignment = tuple(current)
    if best_assignment is None:
        raise MaxCutError("Local search did not evaluate an assignment.")
    return _confirmed_reference(
        instance,
        best_assignment,
        best_value,
        "deterministic_local_search",
        False,
    )


def solve_classical(instance: MaxCutInstance) -> ClassicalReference:
    if instance.num_vertices <= EXHAUSTIVE_VERTEX_LIMIT:
        return _exhaustive(instance)
    return _local_search(instance)
