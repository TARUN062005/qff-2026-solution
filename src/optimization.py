from __future__ import annotations

import math
from typing import Sequence

import numpy as np
from scipy.optimize import minimize

from src.max_cut import MaxCutInstance
from src.qaoa import QaoaError, bind_qaoa_parameters, build_qaoa_circuit, expected_cut_from_statevector


def _finite_parameter_vector(values: Sequence[float], depth: int) -> list[float]:
    if len(values) != 2 * depth:
        raise QaoaError(f"Expected {2 * depth} initial parameters.")
    parsed: list[float] = []
    for value in values:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise QaoaError("Initial parameters must be finite numbers.")
        number = float(value)
        if not math.isfinite(number):
            raise QaoaError("Initial parameters must be finite numbers.")
        parsed.append(number)
    return parsed


def optimize_shared_parameters(
    instance: MaxCutInstance,
    depth: int,
    method: str,
    initial_parameters: Sequence[float],
    grid_gamma_points: int,
    grid_beta_points: int,
    gamma_upper: float,
    beta_upper: float,
    cobyla_maxiter: int,
    cobyla_rhobeg: float,
    cobyla_tol: float,
) -> dict[str, object]:
    template = build_qaoa_circuit(instance, depth, measure=False)
    history: list[dict[str, float | str | int]] = []

    def expected_cut(values: Sequence[float]) -> float:
        bound = bind_qaoa_parameters(template, values, depth)
        return expected_cut_from_statevector(bound, instance)

    def record(stage: str, values: Sequence[float], objective: float) -> None:
        if not math.isfinite(objective):
            raise QaoaError("QAOA evaluation returned a non-finite objective.")
        row: dict[str, float | str | int] = {
            "stage": stage,
            "evaluation": len(history) + 1,
            "expected_cut": objective,
            "negative_expected_cut": -objective,
        }
        for index, value in enumerate(values):
            row[f"parameter_{index}"] = float(value)
        history.append(row)

    if method == "grid_then_cobyla":
        if depth != 1:
            raise QaoaError("The deterministic grid search is implemented for QAOA depth 1.")
        if grid_gamma_points < 2 or grid_beta_points < 2:
            raise QaoaError("Grid searches need at least two points on each axis.")
        gamma_values = np.linspace(0.0, gamma_upper, grid_gamma_points)
        beta_values = np.linspace(0.0, beta_upper, grid_beta_points)
        best_values = [float(gamma_values[0]), float(beta_values[0])]
        best_objective = -math.inf
        for gamma in gamma_values:
            for beta in beta_values:
                candidate = [float(gamma), float(beta)]
                objective = expected_cut(candidate)
                record("grid", candidate, objective)
                if objective > best_objective:
                    best_objective = objective
                    best_values = candidate
        start = best_values
    elif method == "cobyla_only":
        start = _finite_parameter_vector(initial_parameters, depth)
        best_objective = expected_cut(start)
        record("initial", start, best_objective)
    else:
        raise QaoaError(f"Unsupported optimizer method {method}.")

    def negative_cut(values: np.ndarray) -> float:
        objective = expected_cut([float(value) for value in values])
        record("cobyla", [float(value) for value in values], objective)
        return -objective

    result = minimize(
        negative_cut,
        np.array(start, dtype=float),
        method="COBYLA",
        options={"maxiter": cobyla_maxiter, "rhobeg": cobyla_rhobeg, "tol": cobyla_tol},
    )
    finite_rows = [row for row in history if math.isfinite(float(row["expected_cut"]))]
    if not finite_rows:
        raise QaoaError("The optimizer did not produce a finite objective.")
    best_row = max(finite_rows, key=lambda row: float(row["expected_cut"]))
    parameter_keys = [key for key in best_row if key.startswith("parameter_")]
    parameters = [float(best_row[key]) for key in sorted(parameter_keys, key=lambda key: int(key.split("_")[1]))]
    return {
        "method": method,
        "parameters": parameters,
        "ideal_expected_cut": float(best_row["expected_cut"]),
        "cobyla_success": bool(result.success),
        "cobyla_message": str(result.message),
        "cobyla_nfev": int(result.nfev),
        "evaluation_count": len(history),
        "history": history,
        "gamma_upper": gamma_upper,
        "beta_upper": beta_upper,
        "grid_gamma_points": grid_gamma_points,
        "grid_beta_points": grid_beta_points,
        "cobyla_maxiter": cobyla_maxiter,
    }
