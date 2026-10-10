from __future__ import annotations

import math

import pytest

from src.max_cut import build_instance
from src.metrics import proportion_standard_error, routing_overhead_cx, samples_from_counts, summarize_cut_samples


def test_proportion_standard_error() -> None:
    assert math.isclose(proportion_standard_error(0.5, 4), 0.25)
    assert proportion_standard_error(0.0, 10) == 0.0
    assert proportion_standard_error(1.0, 10) == 0.0
    with pytest.raises(ValueError):
        proportion_standard_error(0.2, 0)


def test_expected_cut_uncertainty_and_zero_optimum() -> None:
    summary = summarize_cut_samples([(0.0, 1), (2.0, 1)], 4.0, True)
    assert math.isclose(summary["expected_cut"], 1.0)
    assert math.isclose(summary["expected_cut_standard_error"], math.sqrt(1.0 / 2.0))
    assert math.isclose(summary["approximation_ratio"], 0.25)
    zero = summarize_cut_samples([(0.0, 8)], 0.0, True)
    assert zero["approximation_ratio"] is None
    assert math.isclose(zero["optimal_success_probability"], 1.0)


def test_unknown_optimum_does_not_report_success_probability() -> None:
    summary = summarize_cut_samples([(3.0, 4), (1.0, 4)], 3.0, False)
    assert summary["optimal_success_probability"] is None
    assert summary["approximation_reference"] == "best_known"
    assert math.isclose(summary["approximation_ratio"], 2.0 / 3.0)


def test_routing_definition_and_sample_decoder() -> None:
    assert routing_overhead_cx(cx_count=10, explicit_swap_count=0, logical_rzz_count=4) == 2
    assert routing_overhead_cx(cx_count=4, explicit_swap_count=1, logical_rzz_count=3) == 1
    instance = build_instance([0, 1], [(0, 1, 2.5)])
    samples = samples_from_counts({"01": 3, "10": 1}, {0: 0, 1: 1}, instance)
    summary = summarize_cut_samples(samples, 2.5, True)
    assert math.isclose(summary["expected_cut"], 2.5)
    assert summary["shots"] == 4
