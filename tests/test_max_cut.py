from __future__ import annotations

import math
from pathlib import Path

import pytest

from src.max_cut import MaxCutError, build_instance, cut_value, load_instance, solve_classical
from src.metrics import summarize_cut_samples


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


def _separate_exhaustive_optimum(
    edges: list[tuple[int, int, float]],
    vertex_count: int,
) -> tuple[float, tuple[int, ...]]:
    best_value = -math.inf
    best_assignment = tuple(0 for _ in range(vertex_count))
    for mask in range(1 << vertex_count):
        assignment = tuple((mask >> vertex) & 1 for vertex in range(vertex_count))
        total = 0.0
        for u, v, weight in edges:
            if assignment[u] != assignment[v]:
                total += weight
        if total > best_value:
            best_value = total
            best_assignment = assignment
    return best_value, best_assignment


def test_complement_matches_the_optimum_and_success_counts_that_cut() -> None:
    instance = build_instance([0, 1, 2], [(0, 1, 1.0), (1, 2, 2.0), (0, 2, 3.0)], instance_id="complement")
    reference = solve_classical(instance)
    complement = tuple(1 - bit for bit in reference.assignment)
    separate = 0.0
    for edge in instance.edges:
        if complement[edge.u] != complement[edge.v]:
            separate += edge.weight
    assert math.isclose(separate, reference.objective_value)
    summary = summarize_cut_samples(
        [(reference.objective_value, 3), (0.0, 1)],
        reference.objective_value,
        True,
    )
    assert math.isclose(float(summary["optimal_success_probability"]), 0.75)


def test_supplementary_five_vertex_config_is_separate() -> None:
    import json

    active = json.loads((ROOT / "config" / "experiment.json").read_text(encoding="utf-8"))
    supplementary = json.loads(
        (ROOT / "config" / "experiment_5vertex_supplementary.json").read_text(encoding="utf-8")
    )
    assert active["experiment_id"] == "framework-coupling-custom-6vertex-p1"
    assert supplementary["experiment_id"] == "framework-coupling-supplementary-5vertex-p1"
    assert active["output_dir"] == "results"
    assert supplementary["output_dir"] == "results/supplementary/five_vertex_framework"
    assert active["instance_path"] != supplementary["instance_path"]
    provisional = load_instance(ROOT / "data" / "raw" / "maxcut_provisional.json")
    assert supplementary["instance_path"].endswith("maxcut_provisional.json")
    assert provisional.num_vertices == 5
    assert provisional.official is False


def test_custom_six_vertex_graph_is_the_active_instance() -> None:
    import json

    example = load_instance(ROOT / "data" / "raw" / "maxcut_example_6vertex.json")
    custom = load_instance(ROOT / "data" / "raw" / "maxcut_custom_6vertex.json")
    config = json.loads((ROOT / "config" / "experiment.json").read_text(encoding="utf-8"))
    assert config["instance_path"].endswith("maxcut_custom_6vertex.json")
    assert config["experiment_id"] == "framework-coupling-custom-6vertex-p1"
    assert custom.official is False
    assert custom.num_vertices == 6
    assert custom.connected is True
    assert custom.instance_id != example.instance_id
    assert all(float(edge.weight).is_integer() and 1 <= edge.weight <= 5 for edge in custom.edges)
    edges = [(edge.u, edge.v, edge.weight) for edge in custom.edges]
    best = -math.inf
    winners: list[tuple[int, ...]] = []
    for mask in range(1 << custom.num_vertices):
        bits = tuple((mask >> vertex) & 1 for vertex in range(custom.num_vertices))
        total = sum(weight for u, v, weight in edges if bits[u] != bits[v])
        if total > best:
            best = total
            winners = [bits]
        elif math.isclose(total, best):
            winners.append(bits)
    reference = solve_classical(custom)
    assert math.isclose(best, 21.0)
    assert math.isclose(reference.objective_value, best)
    assert reference.optimal is True
    assert tuple(reference.assignment) in winners
    assert all(tuple(1 - bit for bit in assignment) in winners for assignment in winners)
    assert len(winners) == 4


def test_six_vertex_example_is_not_the_benchmark_instance() -> None:
    example = load_instance(ROOT / "data" / "raw" / "maxcut_example_6vertex.json")
    provisional = load_instance(ROOT / "data" / "raw" / "maxcut_provisional.json")
    assert example.official is False
    assert example.num_vertices == 6
    assert example.instance_id != provisional.instance_id
    edges = [(edge.u, edge.v, edge.weight) for edge in example.edges]
    best = -math.inf
    for mask in range(1 << example.num_vertices):
        bits = [(mask >> vertex) & 1 for vertex in range(example.num_vertices)]
        total = sum(weight for u, v, weight in edges if bits[u] != bits[v])
        if total > best:
            best = total
    reference = solve_classical(example)
    assert math.isclose(reference.objective_value, best)
    assert reference.optimal is True


def test_provisional_instance_file() -> None:
    instance = load_instance(ROOT / "data" / "raw" / "maxcut_provisional.json")
    assert instance.official is False
    assert instance.dashboard_identifier == "PS-O1"
    reference = solve_classical(instance)
    separate_value, separate_assignment = _separate_exhaustive_optimum(
        [(edge.u, edge.v, edge.weight) for edge in instance.edges],
        instance.num_vertices,
    )
    assert reference.optimal is True
    assert math.isclose(separate_value, 9.5)
    assert math.isclose(reference.objective_value, separate_value)
    assert separate_assignment == reference.assignment
    complement = tuple(1 - bit for bit in separate_assignment)
    complement_total = 0.0
    for edge in instance.edges:
        if complement[edge.u] != complement[edge.v]:
            complement_total += edge.weight
    assert math.isclose(complement_total, 9.5)
    assert math.isclose(reference.cut_value, cut_value(instance, reference.assignment))


def test_zero_weight_edge_and_rejected_boolean_weight() -> None:
    instance = build_instance([0, 1, 2], [(0, 1, 0.0), (1, 2, 2.0)], instance_id="zero-weight")
    reference = solve_classical(instance)
    assert math.isclose(reference.objective_value, 2.0)
    with pytest.raises(MaxCutError, match="finite"):
        build_instance([0, 1], [(0, 1, True)])


def test_in_memory_official_flag_is_distinct_from_the_provisional_file() -> None:
    provisional = load_instance(ROOT / "data" / "raw" / "maxcut_provisional.json")
    labeled = build_instance([0, 1], [(0, 1, 1.0)], instance_id="labeled", official=True)
    assert provisional.official is False
    assert labeled.official is True
    assert labeled.instance_id != provisional.instance_id
