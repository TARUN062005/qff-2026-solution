from __future__ import annotations

import math
from pathlib import Path

import pytest

from src.max_cut import MaxCutError, build_instance, cut_value, load_instance, solve_classical


ROOT = Path(__file__).resolve().parents[1]


def test_triangle_optimum_and_assignment_agreement() -> None:
    instance = build_instance([0, 1, 2], [(0, 1, 1.0), (1, 2, 1.0), (0, 2, 1.0)], instance_id="triangle")
    reference = solve_classical(instance)
    assert reference.optimal is True
    assert reference.method == "exhaustive_enumeration"
    assert math.isclose(reference.objective_value, 2.0)
    assert math.isclose(reference.cut_value, cut_value(instance, reference.assignment))


def test_unequal_weights() -> None:
    instance = build_instance([0, 1, 2], [(0, 1, 5.0), (1, 2, 1.0), (0, 2, 1.0)], instance_id="weighted")
    reference = solve_classical(instance)
    assert math.isclose(reference.objective_value, 6.0)
    assert math.isclose(cut_value(instance, reference.assignment), 6.0)


def test_disconnected_graph() -> None:
    instance = build_instance(
        [0, 1, 2, 3],
        [(0, 1, 2.0), (2, 3, 3.0)],
        instance_id="disconnected",
    )
    assert instance.connected is False
    reference = solve_classical(instance)
    assert reference.optimal is True
    assert math.isclose(reference.objective_value, 5.0)


def test_invalid_vertex_reference() -> None:
    with pytest.raises(MaxCutError, match="not in the vertex set"):
        build_instance([0, 1, 2], [(0, 5, 1.0)])


def test_invalid_weight() -> None:
    with pytest.raises(MaxCutError, match="Negative"):
        build_instance([0, 1], [(0, 1, -1.0)])


def test_empty_graph_behavior() -> None:
    with pytest.raises(MaxCutError, match="non-empty"):
        build_instance([], [])
    instance = build_instance([0, 1], [], instance_id="edgeless")
    reference = solve_classical(instance)
    assert math.isclose(reference.objective_value, 0.0)
    assert reference.optimal is True
    assert math.isclose(cut_value(instance, (0, 1)), 0.0)


def test_supplied_assignment_evaluation() -> None:
    instance = build_instance([0, 1, 2], [(0, 1, 1.5), (1, 2, 2.5)])
    assert math.isclose(cut_value(instance, (0, 1, 0)), 4.0)
    assert math.isclose(cut_value(instance, (0, 0, 0)), 0.0)


def test_exhaustive_matches_objective_function() -> None:
    instance = build_instance(
        [0, 1, 2, 3],
        [(0, 1, 1.0), (1, 2, 0.5), (2, 3, 1.25), (0, 3, 0.75), (0, 2, 2.0)],
    )
    reference = solve_classical(instance)
    assert math.isclose(reference.objective_value, cut_value(instance, reference.assignment))


def test_duplicate_edge_and_self_loop() -> None:
    with pytest.raises(MaxCutError, match="Duplicate"):
        build_instance([0, 1], [(0, 1, 1.0), (1, 0, 2.0)])
    with pytest.raises(MaxCutError, match="Self-loop"):
        build_instance([0, 1], [(0, 0, 1.0)])


def test_local_search_does_not_claim_optimality() -> None:
    edges = [(vertex, vertex + 1, 1.0) for vertex in range(20)]
    instance = build_instance(list(range(21)), edges, instance_id="path21")
    reference = solve_classical(instance)
    assert reference.optimal is False
    assert reference.method == "deterministic_local_search"
    assert math.isclose(reference.cut_value, cut_value(instance, reference.assignment))


def test_provisional_instance_file() -> None:
    instance = load_instance(ROOT / "data" / "raw" / "maxcut_provisional.json")
    assert instance.official is False
    assert instance.dashboard_identifier == "PS-O1"
    reference = solve_classical(instance)
    assert reference.optimal is True
    assert math.isclose(reference.cut_value, cut_value(instance, reference.assignment))
