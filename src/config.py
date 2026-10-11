from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path


class ConfigError(ValueError):
    pass


@dataclass(frozen=True)
class OptimizerSettings:
    method: str
    grid_gamma_points: int
    grid_beta_points: int
    gamma_upper: float
    beta_upper: float
    cobyla_maxiter: int
    cobyla_rhobeg: float
    cobyla_tol: float


@dataclass(frozen=True)
class ExperimentConfig:
    team: str
    event: str
    phase: str
    track: str
    problem_code: str
    dashboard_identifier: str
    problem_title: str
    instance_path: Path
    processor_paths: dict[str, Path]
    qaoa_depth: int
    comparison_type: str
    optimizer: OptimizerSettings
    initial_parameters: tuple[float, ...]
    shots: int
    optimization_level: int
    seed_transpiler: int
    seed_simulator: int
    layout_method: str
    routing_method: str
    execution_modes: tuple[str, ...]
    output_dir: Path
    experiment_id: str

    def to_dict(self) -> dict[str, object]:
        return {
            "team": self.team,
            "event": self.event,
            "phase": self.phase,
            "track": self.track,
            "problem_code": self.problem_code,
            "dashboard_identifier": self.dashboard_identifier,
            "problem_title": self.problem_title,
            "instance_path": self.instance_path.as_posix(),
            "processors": {key: value.as_posix() for key, value in self.processor_paths.items()},
            "qaoa_depth": self.qaoa_depth,
            "comparison_type": self.comparison_type,
            "optimizer": {
                "method": self.optimizer.method,
                "grid_gamma_points": self.optimizer.grid_gamma_points,
                "grid_beta_points": self.optimizer.grid_beta_points,
                "gamma_upper": self.optimizer.gamma_upper,
                "beta_upper": self.optimizer.beta_upper,
                "cobyla_maxiter": self.optimizer.cobyla_maxiter,
                "cobyla_rhobeg": self.optimizer.cobyla_rhobeg,
                "cobyla_tol": self.optimizer.cobyla_tol,
            },
            "initial_parameters": list(self.initial_parameters),
            "shots": self.shots,
            "optimization_level": self.optimization_level,
            "seed_transpiler": self.seed_transpiler,
            "seed_simulator": self.seed_simulator,
            "layout_method": self.layout_method,
            "routing_method": self.routing_method,
            "execution_modes": list(self.execution_modes),
            "output_dir": self.output_dir.as_posix(),
            "experiment_id": self.experiment_id,
        }


def _text(payload: dict[str, object], field: str) -> str:
    value = payload.get(field)
    if not isinstance(value, str) or not value:
        raise ConfigError(f"{field} must be a non-empty string.")
    return value


def _int(payload: dict[str, object], field: str, minimum: int, maximum: int | None = None) -> int:
    value = payload.get(field)
    if isinstance(value, bool) or not isinstance(value, int):
        raise ConfigError(f"{field} must be an integer.")
    if value < minimum or (maximum is not None and value > maximum):
        raise ConfigError(f"{field} is outside the supported range.")
    return value


def _resolve(root: Path, value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path.resolve()
    return (root / path).resolve()


def _finite(value: object, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ConfigError(f"{field} must be a finite number.")
    number = float(value)
    if not math.isfinite(number):
        raise ConfigError(f"{field} must be a finite number.")
    return number


def load_experiment_config(path: Path, root: Path) -> ExperimentConfig:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ConfigError(f"Could not parse experiment config {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise ConfigError("Experiment config must be a JSON object.")
    depth = _int(payload, "qaoa_depth", 1)
    raw_parameters = payload.get("initial_parameters")
    if not isinstance(raw_parameters, list) or len(raw_parameters) != 2 * depth:
        raise ConfigError("initial_parameters must contain two values per QAOA layer.")
    parameters = tuple(_finite(value, "initial_parameters") for value in raw_parameters)
    optimizer_payload = payload.get("optimizer")
    if not isinstance(optimizer_payload, dict):
        raise ConfigError("optimizer must be a JSON object.")
    method = optimizer_payload.get("method")
    if method not in {"grid_then_cobyla", "cobyla_only"}:
        raise ConfigError("optimizer.method must be grid_then_cobyla or cobyla_only.")
    optimizer = OptimizerSettings(
        method=str(method),
        grid_gamma_points=_int(optimizer_payload, "grid_gamma_points", 2),
        grid_beta_points=_int(optimizer_payload, "grid_beta_points", 2),
        gamma_upper=_finite(optimizer_payload.get("gamma_upper"), "gamma_upper"),
        beta_upper=_finite(optimizer_payload.get("beta_upper"), "beta_upper"),
        cobyla_maxiter=_int(optimizer_payload, "cobyla_maxiter", 1),
        cobyla_rhobeg=_finite(optimizer_payload.get("cobyla_rhobeg"), "cobyla_rhobeg"),
        cobyla_tol=_finite(optimizer_payload.get("cobyla_tol"), "cobyla_tol"),
    )
    if optimizer.gamma_upper <= 0 or optimizer.beta_upper <= 0 or optimizer.cobyla_rhobeg <= 0:
        raise ConfigError("Optimizer ranges and rhobeg must be positive.")
    modes = payload.get("execution_modes")
    if not isinstance(modes, list) or not modes:
        raise ConfigError("execution_modes must be a non-empty list.")
    if any(mode not in {"ideal", "provisional_noise"} for mode in modes):
        raise ConfigError("execution_modes can contain only ideal and provisional_noise.")
    if len(set(modes)) != len(modes):
        raise ConfigError("execution_modes contains a duplicate.")
    processors = payload.get("processors")
    if not isinstance(processors, dict) or set(processors) != {"A", "B"}:
        raise ConfigError("processors must map exactly A and B to definition files.")
    processor_paths: dict[str, Path] = {}
    for key, value in processors.items():
        if not isinstance(value, str) or not value:
            raise ConfigError(f"processors.{key} must be a path.")
        processor_paths[key] = _resolve(root, value)
    comparison = _text(payload, "comparison_type")
    if comparison != "shared_parameter_architecture_comparison":
        raise ConfigError(
            "This runner implements shared_parameter_architecture_comparison. A processor-specific optimization study needs a separate config and output directory."
        )
    output_value = _text(payload, "output_dir")
    output_path = _resolve(root, output_value)
    experiment_id = payload.get("experiment_id", "")
    if not isinstance(experiment_id, str):
        raise ConfigError("experiment_id must be a string when present.")
    return ExperimentConfig(
        team=_text(payload, "team"),
        event=_text(payload, "event"),
        phase=_text(payload, "phase"),
        track=_text(payload, "track"),
        problem_code=_text(payload, "problem_code"),
        dashboard_identifier=_text(payload, "dashboard_identifier"),
        problem_title=_text(payload, "problem_title"),
        instance_path=_resolve(root, _text(payload, "instance_path")),
        processor_paths=processor_paths,
        qaoa_depth=depth,
        comparison_type=comparison,
        optimizer=optimizer,
        initial_parameters=parameters,
        shots=_int(payload, "shots", 1),
        optimization_level=_int(payload, "optimization_level", 0, 3),
        seed_transpiler=_int(payload, "seed_transpiler", 0),
        seed_simulator=_int(payload, "seed_simulator", 0),
        layout_method=_text(payload, "layout_method"),
        routing_method=_text(payload, "routing_method"),
        execution_modes=tuple(str(mode) for mode in modes),
        output_dir=output_path,
        experiment_id=experiment_id,
    )
