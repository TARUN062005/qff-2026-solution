from __future__ import annotations

import csv
import hashlib
import json
import math
import sys
import time
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path
from typing import Sequence

import qiskit.qasm2 as qasm2

from src.config import ExperimentConfig, load_experiment_config
from src.max_cut import MaxCutInstance, load_instance, solve_classical
from src.metrics import samples_from_counts, summarize_cut_samples
from src.optimization import optimize_shared_parameters
from src.processor_model import ProcessorModel, load_processor
from src.qaoa import bind_qaoa_parameters, build_qaoa_circuit
from src.reporting import write_report
from src.simulator import execute_counts
from src.transpilation import TranspilationError, compile_for_processor, resource_report
from src.visualization import (
    save_circuit_figure,
    save_circuit_panel,
    save_cut_histogram,
    save_grouped_bars,
    save_performance_chart,
    save_problem_graph,
    save_processor_graph,
    save_tradeoff_chart,
)


BLOCKING_SPECIFICATIONS = [
    "The supplied Phase 1 documents do not list Processor A's coupling edges, edge direction, or native-gate constraints.",
    "The supplied Phase 1 documents do not list Processor B's coupling edges. The configured map is the published ibm_lagos fragment, not an organizer definition.",
    "The supplied Phase 1 documents do not include the official weighted Max-Cut graph, weights, or constraints for O1.",
    "QAOA depth, parameter initialization, optimizer budget, and shot count are not specified by the supplied documents. The configured values are provisional defaults.",
    "The noise rates are the Challenge Guide's illustrative example, and the guide says to replace them with the official assumptions.",
]


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _plain(value: object) -> object:
    if isinstance(value, dict):
        return {str(key): _plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(item) for item in value]
    if isinstance(value, Path):
        return value.as_posix()
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return int(value)
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if hasattr(value, "item"):
        return _plain(value.item())
    return value


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_plain(payload), indent=2), encoding="utf-8")


def _write_csv(path: Path, rows: Sequence[dict[str, object]], fieldnames: Sequence[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(fieldnames))
        writer.writeheader()
        for row in rows:
            writer.writerow({key: "" if row.get(key) is None else row.get(key) for key in fieldnames})


def _environment() -> dict[str, object]:
    packages = {}
    for package_name in ("qiskit", "qiskit-aer", "numpy", "scipy", "networkx", "matplotlib", "pillow", "pylatexenc"):
        packages[package_name] = version(package_name)
    return {"python": sys.version, "packages": packages}


def _decoder(resources: dict[str, object]) -> dict[int, int]:
    pairs = resources["measurement_decoder"]
    if not isinstance(pairs, list):
        raise TranspilationError("The measurement decoder was not recorded.")
    return {int(clbit): int(logical) for clbit, logical in pairs}


def _consistent(expected: float, standard_error: float, reference: float) -> bool:
    if standard_error == 0:
        return math.isclose(expected, reference, rel_tol=0.0, abs_tol=1e-6)
    return abs(expected - reference) <= 4.0 * standard_error


def _execute_mode(
    circuit,
    processor: ProcessorModel,
    mode: str,
    shots: int,
    seed_simulator: int,
    instance: MaxCutInstance,
    decoder: dict[int, int],
    reference_value: float,
    reference_is_exact: bool,
    statevector_expectation: float,
) -> tuple[dict[str, object], dict[str, int]]:
    started = time.perf_counter()
    noise = None if mode == "ideal" else processor.noise_model()
    if mode == "provisional_noise" and noise is None:
        raise TranspilationError(f"{processor.name} has no noise model for provisional_noise execution.")
    counts = execute_counts(circuit, shots, seed_simulator, noise)
    summary = summarize_cut_samples(
        samples_from_counts(counts, decoder, instance),
        reference_value,
        reference_is_exact,
    )
    summary["execution_seconds"] = time.perf_counter() - started
    summary["seed_simulator"] = seed_simulator
    summary["simulator"] = "qiskit_aer.AerSimulator"
    summary["noise_model"] = "none" if mode == "ideal" else processor.noise.label if processor.noise else "missing"
    if mode == "ideal":
        summary["consistent_with_statevector"] = _consistent(
            float(summary["expected_cut"]),
            float(summary["expected_cut_standard_error"]),
            statevector_expectation,
        )
    return summary, counts


def run_controlled_experiment(
    config_path: Path,
    output_dir: Path | None = None,
    report_path: Path | None = None,
) -> dict[str, object]:
    root = repo_root()
    config = load_experiment_config(config_path, root)
    destination = output_dir.resolve() if output_dir is not None else config.output_dir
    if report_path is None:
        report_path = root / "report.md" if destination == (root / "results").resolve() else destination / "report.md"
    for folder in ("tables", "figures", "circuits", "manifests", "processed"):
        (destination / folder).mkdir(parents=True, exist_ok=True)
    manifest_path = destination / "manifests" / "experiment_manifest.json"
    progress: dict[str, object] = {
        "success": False,
        "stage": "start",
        "official_benchmark_complete": False,
        "blocking_specifications": list(BLOCKING_SPECIFICATIONS),
        "team": config.team,
        "problem_code": config.problem_code,
        "dashboard_identifier": config.dashboard_identifier,
    }
    try:
        manifest = _run_stages(config, config_path, destination, report_path, progress)
    except Exception as exc:
        progress["success"] = False
        progress["error_type"] = type(exc).__name__
        progress["error_message"] = str(exc)
        progress["finished_utc"] = datetime.now(timezone.utc).isoformat()
        _write_json(manifest_path, progress)
        raise
    _write_json(manifest_path, manifest)
    return manifest


def _run_stages(
    config: ExperimentConfig,
    config_path: Path,
    destination: Path,
    report_path: Path,
    progress: dict[str, object],
) -> dict[str, object]:
    root = repo_root()
    progress["stage"] = "load_instance"
    instance = load_instance(config.instance_path)
    if instance.problem_code != config.problem_code:
        raise TranspilationError("The instance problem code does not match the experiment config.")
    progress["stage"] = "classical_reference"
    reference = solve_classical(instance)
    if destination == (root / "results").resolve():
        processed_path = root / "data" / "processed" / "instance_with_reference.json"
    else:
        processed_path = destination / "processed" / "instance_with_reference.json"
    _write_json(
        processed_path,
        {
            "instance": instance.to_dict(),
            "classical_reference": {
                "objective_value": reference.objective_value,
                "assignment": list(reference.assignment),
                "cut_value": reference.cut_value,
                "method": reference.method,
                "optimal": reference.optimal,
            },
        },
    )
    progress["stage"] = "logical_circuit"
    logical = build_qaoa_circuit(instance, config.qaoa_depth, measure=True)
    progress["stage"] = "optimize_parameters"
    started = datetime.now(timezone.utc)
    optimization = optimize_shared_parameters(
        instance,
        config.qaoa_depth,
        config.optimizer.method,
        config.initial_parameters,
        config.optimizer.grid_gamma_points,
        config.optimizer.grid_beta_points,
        config.optimizer.gamma_upper,
        config.optimizer.beta_upper,
        config.optimizer.cobyla_maxiter,
        config.optimizer.cobyla_rhobeg,
        config.optimizer.cobyla_tol,
    )
    parameters = [float(value) for value in optimization["parameters"]]
    bound = bind_qaoa_parameters(logical, parameters, config.qaoa_depth)
    (destination / "circuits").mkdir(parents=True, exist_ok=True)
    (destination / "circuits" / "logical_qaoa_bound.qasm").write_text(qasm2.dumps(bound), encoding="utf-8")
    _write_json(destination / "tables" / "optimizer_history.json", optimization["history"])
    processors = {
        key: load_processor(path) for key, path in config.processor_paths.items()
    }
    if "provisional_noise" in config.execution_modes:
        missing = [key for key, processor in processors.items() if processor.noise is None]
        if missing:
            raise TranspilationError(
                "provisional_noise was requested but these processors have no noise model: " + ", ".join(missing)
            )
    noise_signatures = {
        key: None if processor.noise is None else processor.noise.to_dict() for key, processor in processors.items()
    }
    basis_gates_identical = processors["A"].basis_gates == processors["B"].basis_gates
    noise_rates_identical = noise_signatures["A"] == noise_signatures["B"]
    official = bool(
        instance.official
        and processors["A"].provenance.get("official") is True
        and processors["B"].provenance.get("official") is True
    )
    processor_results: dict[str, object] = {}
    compiled_circuits = {}
    for key in ("A", "B"):
        progress["stage"] = f"compile_{key}"
        processor_results[key], compiled_circuits[key] = _benchmark_processor(
            key,
            processors[key],
            config.processor_paths[key],
            bound,
            config,
            instance,
            reference.objective_value,
            reference.optimal,
            float(optimization["ideal_expected_cut"]),
            destination,
            _sha256(config.instance_path),
        )
    progress["stage"] = "export"
    manifest: dict[str, object] = {
        "success": True,
        "official_benchmark_complete": official,
        "blocking_specifications": [] if official else list(BLOCKING_SPECIFICATIONS),
        "team": config.team,
        "event": config.event,
        "phase": config.phase,
        "track": config.track,
        "problem_code": config.problem_code,
        "dashboard_identifier": config.dashboard_identifier,
        "problem_title": config.problem_title,
        "comparison_type": config.comparison_type,
        "stage": "complete",
        "started_utc": started.isoformat(),
        "finished_utc": datetime.now(timezone.utc).isoformat(),
        "config_path": config_path.resolve().as_posix(),
        "config_sha256": _sha256(config_path),
        "settings": config.to_dict(),
        "execution_modes": list(config.execution_modes),
        "shots": config.shots,
        "optimization_level": config.optimization_level,
        "layout_method": config.layout_method,
        "routing_method": config.routing_method,
        "seed_transpiler": config.seed_transpiler,
        "seed_simulator": config.seed_simulator,
        "basis_gates_identical": basis_gates_identical,
        "noise_rates_identical": noise_rates_identical,
        "instance": {
            "instance_id": instance.instance_id,
            "official": instance.official,
            "sha256": _sha256(config.instance_path),
            "num_vertices": instance.num_vertices,
            "num_edges": instance.num_edges,
            "connected": instance.connected,
            "provenance": instance.provenance,
        },
        "classical_reference": {
            "objective_value": reference.objective_value,
            "assignment": list(reference.assignment),
            "cut_value": reference.cut_value,
            "method": reference.method,
            "optimal": reference.optimal,
        },
        "qaoa": {
            "depth": config.qaoa_depth,
            "method": optimization["method"],
            "parameters": parameters,
            "ideal_expected_cut": optimization["ideal_expected_cut"],
            "evaluation_count": optimization["evaluation_count"],
            "cobyla_success": optimization["cobyla_success"],
            "cobyla_message": optimization["cobyla_message"],
            "cobyla_nfev": optimization["cobyla_nfev"],
            "configured_initial_parameters": list(config.initial_parameters),
            "parameter_source": "shared ideal statevector optimization, applied unchanged to both processors",
        },
        "processors": processor_results,
        "environment": _environment(),
        "hardware_execution": False,
    }
    _export_tables(manifest, destination / "tables")
    _export_figures(manifest, instance, processors, bound, compiled_circuits, destination / "figures")
    write_report(manifest, report_path)
    manifest["artifacts"] = {
        "report": report_path.resolve().as_posix(),
        "tables": (destination / "tables").resolve().as_posix(),
        "figures": (destination / "figures").resolve().as_posix(),
        "circuits": (destination / "circuits").resolve().as_posix(),
    }
    progress.update(manifest)
    return manifest


def _benchmark_processor(
    key: str,
    processor: ProcessorModel,
    source: Path,
    logical_circuit,
    config: ExperimentConfig,
    instance: MaxCutInstance,
    reference_value: float,
    reference_is_exact: bool,
    statevector_expectation: float,
    destination: Path,
    instance_sha256: str,
) -> tuple[dict[str, object], object]:
    started = time.perf_counter()
    compiled = compile_for_processor(
        logical_circuit,
        processor,
        config.optimization_level,
        config.seed_transpiler,
        config.layout_method,
        config.routing_method,
    )
    resources = resource_report(logical_circuit, compiled, time.perf_counter() - started)
    (destination / "circuits" / f"processor_{key}_transpiled.qasm").write_text(
        qasm2.dumps(compiled),
        encoding="utf-8",
    )
    _write_json(destination / "circuits" / f"processor_{key}_layout.json", {
        "final_index_layout": resources["final_index_layout"],
        "measurement_decoder": resources["measurement_decoder"],
    })
    decoder = _decoder(resources)
    executions: dict[str, object] = {}
    for mode in config.execution_modes:
        summary, counts = _execute_mode(
            compiled,
            processor,
            mode,
            config.shots,
            config.seed_simulator,
            instance,
            decoder,
            reference_value,
            reference_is_exact,
            statevector_expectation,
        )
        executions[mode] = summary
        _write_json(destination / "tables" / f"processor_{key}_{mode}_counts.json", counts)
        _write_json(destination / "tables" / f"processor_{key}_{mode}_histogram.json", summary["histogram"])
    return {
        "name": processor.name,
        "identifier": processor.identifier,
        "official": processor.provenance.get("official"),
        "provenance_status": processor.provenance.get("status"),
        "provenance_source": processor.provenance.get("source"),
        "num_qubits": processor.num_qubits,
        "coupling_edges": [list(edge) for edge in processor.coupling_edges],
        "basis_gates": list(processor.basis_gates),
        "noise": None if processor.noise is None else processor.noise.to_dict(),
        "sha256": _sha256(source),
        "instance_sha256": instance_sha256,
        "resources": resources,
        "executions": executions,
    }, compiled


def _comparison_rows(manifest: dict[str, object]) -> list[dict[str, object]]:
    processors = manifest["processors"]
    if not isinstance(processors, dict):
        raise TypeError("processors must be an object.")
    modes = manifest["execution_modes"]
    if not isinstance(modes, list):
        raise TypeError("execution_modes must be a list.")
    rows: list[dict[str, object]] = []
    for key in ("A", "B"):
        processor = processors[key]
        if not isinstance(processor, dict):
            raise TypeError("processor result must be an object.")
        resources = processor["resources"]
        executions = processor["executions"]
        if not isinstance(resources, dict) or not isinstance(executions, dict):
            raise TypeError("processor metrics must be objects.")
        for mode in modes:
            execution = executions[str(mode)]
            if not isinstance(execution, dict):
                raise TypeError("execution result must be an object.")
            rows.append(
                {
                    "processor": key,
                    "execution_mode": mode,
                    "instance_sha256": processor["instance_sha256"],
                    "expected_cut": execution["expected_cut"],
                    "expected_cut_standard_error": execution["expected_cut_standard_error"],
                    "best_observed_cut": execution["best_observed_cut"],
                    "approximation_ratio": execution["approximation_ratio"],
                    "approximation_ratio_standard_error": execution["approximation_ratio_standard_error"],
                    "approximation_reference": execution["approximation_reference"],
                    "optimal_success_probability": execution["optimal_success_probability"],
                    "optimal_success_standard_error": execution["optimal_success_standard_error"],
                    "shots": execution["shots"],
                    "execution_seconds": execution["execution_seconds"],
                    "logical_depth": resources["logical_depth"],
                    "transpiled_depth": resources["transpiled_depth"],
                    "logical_operation_count": resources["logical_operation_count"],
                    "transpiled_operation_count": resources["transpiled_operation_count"],
                    "logical_two_qubit_count": resources["logical_two_qubit_count"],
                    "transpiled_two_qubit_count": resources["transpiled_two_qubit_count"],
                    "cx_count": resources["cx_count"],
                    "explicit_swap_count": resources["explicit_swap_count"],
                    "routing_overhead_cx": resources["routing_overhead_cx"],
                    "logical_qubits": resources["logical_qubits"],
                    "physical_qubits_allocated": resources["physical_qubits_allocated"],
                    "physical_qubits_used": resources["physical_qubits_used"],
                    "ancillas_used": resources["ancillas_used"],
                    "compilation_seconds": resources["compilation_seconds"],
                }
            )
    return rows


def _export_tables(manifest: dict[str, object], tables: Path) -> None:
    rows = _comparison_rows(manifest)
    fieldnames = list(rows[0]) if rows else []
    _write_csv(tables / "AB_comparison.csv", rows, fieldnames)
    for key in ("A", "B"):
        processor_rows = [row for row in rows if row["processor"] == key]
        _write_csv(tables / f"processor_{key}_metrics.csv", processor_rows, fieldnames)
    resource_rows = []
    processors = manifest["processors"]
    if isinstance(processors, dict):
        for key in ("A", "B"):
            processor = processors[key]
            if isinstance(processor, dict) and isinstance(processor.get("resources"), dict):
                resource_rows.append(
                    {
                        "processor": key,
                        **{
                            field: value
                            for field, value in processor["resources"].items()
                            if field not in {"measurement_decoder", "final_index_layout"}
                        },
                    }
                )
    if resource_rows:
        resource_fields = [field for field in resource_rows[0] if field not in {"measurement_decoder", "final_index_layout"}]
        _write_csv(tables / "circuit_resources.csv", resource_rows, resource_fields)


def _export_figures(
    manifest: dict[str, object],
    instance: MaxCutInstance,
    processors: dict[str, ProcessorModel],
    bound_circuit,
    compiled_circuits: dict[str, object],
    figures: Path,
) -> None:
    save_problem_graph(instance, figures / "problem_graph.png")
    save_processor_graph(processors["A"], figures / "processor_A_graph.png")
    save_processor_graph(processors["B"], figures / "processor_B_graph.png")
    logical_path = figures / "logical_qaoa.png"
    transpiled_paths = {}
    save_circuit_figure(bound_circuit, logical_path, "Logical QAOA circuit")
    processors_manifest = manifest["processors"]
    if not isinstance(processors_manifest, dict):
        raise TypeError("processors must be an object.")
    for key in ("A", "B"):
        image_path = figures / f"processor_{key}_transpiled.png"
        save_circuit_figure(compiled_circuits[key], image_path, f"Processor {key} transpiled circuit")
        transpiled_paths[key] = image_path
    save_circuit_panel(
        [logical_path, transpiled_paths["A"], transpiled_paths["B"]],
        figures / "logical_vs_transpiled.png",
    )
    rows = _comparison_rows(manifest)
    resource_a = processors_manifest["A"]["resources"]
    resource_b = processors_manifest["B"]["resources"]
    save_grouped_bars(
        ["Processor A", "Processor B"],
        {
            "Logical depth": [float(resource_a["logical_depth"]), float(resource_b["logical_depth"])],
            "Transpiled depth": [float(resource_a["transpiled_depth"]), float(resource_b["transpiled_depth"])],
        },
        "Computational depth",
        "Logical and transpiled circuit depth",
        figures / "depth_comparison.png",
    )
    save_grouped_bars(
        ["Processor A", "Processor B"],
        {
            "Logical two-qubit gates": [
                float(resource_a["logical_two_qubit_count"]),
                float(resource_b["logical_two_qubit_count"]),
            ],
            "Transpiled two-qubit gates": [
                float(resource_a["transpiled_two_qubit_count"]),
                float(resource_b["transpiled_two_qubit_count"]),
            ],
        },
        "Two-qubit instructions",
        "Two-qubit gate count before and after transpilation",
        figures / "two_qubit_comparison.png",
    )
    save_grouped_bars(
        ["Processor A", "Processor B"],
        {
            "Explicit SWAP count": [
                float(resource_a["explicit_swap_count"]),
                float(resource_b["explicit_swap_count"]),
            ],
            "CX-equivalent routing overhead": [
                float(resource_a["routing_overhead_cx"]),
                float(resource_b["routing_overhead_cx"]),
            ],
        },
        "Gate count",
        "SWAP count and CX-equivalent routing overhead",
        figures / "routing_overhead.png",
    )
    save_grouped_bars(
        ["Processor A", "Processor B"],
        {
            "Allocated physical qubits": [
                float(resource_a["physical_qubits_allocated"]),
                float(resource_b["physical_qubits_allocated"]),
            ],
            "Used physical qubits": [
                float(resource_a["physical_qubits_used"]),
                float(resource_b["physical_qubits_used"]),
            ],
        },
        "Qubits",
        "Physical qubit allocation and use",
        figures / "qubit_utilization.png",
    )
    classical = manifest["classical_reference"]
    qaoa = manifest["qaoa"]
    if not isinstance(classical, dict) or not isinstance(qaoa, dict):
        raise TypeError("Manifest is missing reference sections.")
    save_performance_chart(
        rows,
        float(classical["objective_value"]),
        float(qaoa["ideal_expected_cut"]),
        figures / "problem_performance.png",
    )
    save_tradeoff_chart(rows, figures / "architecture_tradeoff.png")
    histograms = {}
    for row in rows:
        processor = processors_manifest[str(row["processor"])]
        execution = processor["executions"][str(row["execution_mode"])]
        histograms[f"{row['processor']} {row['execution_mode']}"] = {
            str(key): int(value) for key, value in execution["histogram"].items()
        }
    save_cut_histogram(histograms, figures / "cut_value_distribution.png")
