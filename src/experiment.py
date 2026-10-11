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


def blocking_specifications(instance: MaxCutInstance | None = None) -> list[str]:
    if instance is None:
        graph = "The executed Max-Cut graph is the file named by the experiment config. It is not an organizer-provided instance unless that file is marked official. Its optimum is not an official O1 optimum unless the issued instance is loaded."
    else:
        graph = (
            f"The executed Max-Cut graph is `{instance.instance_id}` ({instance.num_vertices} vertices). "
            "It is not an organizer-provided instance. Its optimum is not an official O1 optimum."
        )
    return [
        "Processor A coupling edges are the undirected framework list (0,1), (1,2), (1,3), (3,4). Basis gates and both CX directions are a local assumption. Official directed calibration was not supplied.",
        "Processor B coupling edges are the undirected 9-qubit framework list. The 14-page overview diagram is captioned 7 qubits. Basis gates and both CX directions are a local assumption.",
        "The noise rates are the illustrative Challenge Guide model. The framework says organizer benchmark definitions are authoritative for the final noise model, and those parameters were not in the coupling-map documents.",
        graph,
        "QAOA depth 1 with a deterministic grid and COBYLA is the selected reproducible policy. The framework permits p=1 or p=2. It does not require SamplerV2.",
    ]


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _display_path(path: Path) -> str:
    resolved = path.resolve()
    root = repo_root().resolve()
    try:
        return resolved.relative_to(root).as_posix()
    except ValueError:
        return resolved.as_posix()


def _relative_settings(config: ExperimentConfig) -> dict[str, object]:
    settings = config.to_dict()
    settings["instance_path"] = _display_path(config.instance_path)
    settings["output_dir"] = _display_path(config.output_dir)
    settings["processors"] = {
        key: _display_path(path) for key, path in config.processor_paths.items()
    }
    return settings


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _plain(value: object) -> object:
    if isinstance(value, dict):
        return {str(key): _plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(item) for item in value]
    if isinstance(value, Path):
        return _display_path(value)
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
        "blocking_specifications": blocking_specifications(),
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
    progress["blocking_specifications"] = blocking_specifications(instance)
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
    placement_errors: list[str] = []
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
        if compiled_circuits[key] is None:
            result = processor_results[key]
            if isinstance(result, dict):
                placement_errors.append(str(result.get("placement_error", "")))
    if len(placement_errors) == 2:
        raise TranspilationError(placement_errors[0])
    progress["stage"] = "export"
    manifest: dict[str, object] = {
        "success": True,
        "official_benchmark_complete": official,
        "blocking_specifications": [] if official else blocking_specifications(instance),
        "team": config.team,
        "event": config.event,
        "phase": config.phase,
        "track": config.track,
        "problem_code": config.problem_code,
        "dashboard_identifier": config.dashboard_identifier,
        "problem_title": config.problem_title,
        "comparison_type": config.comparison_type,
        "experiment_id": config.experiment_id,
        "stage": "complete",
        "started_utc": started.isoformat(),
        "finished_utc": datetime.now(timezone.utc).isoformat(),
        "config_path": _display_path(config_path),
        "config_sha256": _sha256(config_path),
        "settings": _relative_settings(config),
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
            "parameter_selection": optimization["parameter_selection"],
            "cobyla_terminal_expected_cut": optimization["cobyla_terminal_expected_cut"],
            "cobyla_last_five_span": optimization["cobyla_last_five_span"],
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
        "report": _display_path(report_path),
        "tables": _display_path(destination / "tables"),
        "figures": _display_path(destination / "figures"),
        "circuits": _display_path(destination / "circuits"),
    }
    progress.update(manifest)
    return manifest


def _clear_unexecuted_processor_outputs(destination: Path, key: str) -> None:
    for path in (
        destination / "circuits" / f"processor_{key}_transpiled.qasm",
        destination / "figures" / f"processor_{key}_transpiled.png",
    ):
        if path.exists():
            path.unlink()
    tables = destination / "tables"
    if tables.exists():
        for path in tables.glob(f"processor_{key}_*"):
            path.unlink()


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
    if logical_circuit.num_qubits > processor.num_qubits:
        _clear_unexecuted_processor_outputs(destination, key)
        message = (
            f"{processor.name} has {processor.num_qubits} qubits and the logical circuit needs "
            f"{logical_circuit.num_qubits}. No shots or transpiled metrics were produced for this processor."
        )
        _write_json(
            destination / "circuits" / f"processor_{key}_layout.json",
            {"placement_feasible": False, "placement_error": message},
        )
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
            "placement_feasible": False,
            "placement_error": message,
            "resources": None,
            "executions": {},
        }, None
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
        "placement_feasible": True,
        "placement_error": "",
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
        if processor.get("placement_feasible") is False:
            continue
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
                    "expected_cut_approximation_ratio": execution.get(
                        "expected_cut_approximation_ratio",
                        execution["approximation_ratio"],
                    ),
                    "best_cut_approximation_ratio": execution.get("best_cut_approximation_ratio"),
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
                    "logical_single_qubit_count": resources.get("logical_single_qubit_count"),
                    "transpiled_single_qubit_count": resources.get("transpiled_single_qubit_count"),
                    "logical_two_qubit_count": resources["logical_two_qubit_count"],
                    "transpiled_two_qubit_count": resources["transpiled_two_qubit_count"],
                    "cx_count": resources["cx_count"],
                    "explicit_swap_count": resources["explicit_swap_count"],
                    "explicit_swap_cx_equivalent": resources.get("explicit_swap_cx_equivalent"),
                    "cx_excess_over_rzz_baseline": resources.get("cx_excess_over_rzz_baseline"),
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
    _write_placement_table(manifest, tables)


def _write_placement_table(manifest: dict[str, object], tables: Path) -> None:
    processors = manifest["processors"]
    if not isinstance(processors, dict):
        return
    logical_qubits = manifest.get("instance", {})
    logical_count = logical_qubits.get("num_vertices") if isinstance(logical_qubits, dict) else ""
    rows = []
    for key in ("A", "B"):
        processor = processors.get(key)
        if not isinstance(processor, dict):
            continue
        feasible = processor.get("placement_feasible") is True
        rows.append(
            {
                "processor": key,
                "placement_feasible": feasible,
                "measured": feasible,
                "physical_qubits": processor.get("num_qubits", ""),
                "logical_qubits": logical_count,
                "reason": "" if feasible else processor.get("placement_error", "not executed"),
            }
        )
    _write_csv(
        tables / "placement_status.csv",
        rows,
        ["processor", "placement_feasible", "measured", "physical_qubits", "logical_qubits", "reason"],
    )


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
    panel_paths = [logical_path]
    for key in ("A", "B"):
        image_path = figures / f"processor_{key}_transpiled.png"
        compiled = compiled_circuits.get(key)
        if compiled is None:
            if image_path.exists():
                image_path.unlink()
            continue
        save_circuit_figure(compiled, image_path, f"Processor {key} transpiled circuit")
        transpiled_paths[key] = image_path
        panel_paths.append(image_path)
    save_circuit_panel(panel_paths, figures / "logical_vs_transpiled.png")
    rows = _comparison_rows(manifest)
    placed = [
        key
        for key in ("A", "B")
        if isinstance(processors_manifest[key], dict)
        and isinstance(processors_manifest[key].get("resources"), dict)
    ]
    footnote = None
    unplaced = [key for key in ("A", "B") if key not in placed]
    if unplaced:
        footnote = "Measured processors only. " + " ".join(
            str(processors_manifest[key].get("placement_error", f"Processor {key} was not executed."))
            for key in unplaced
        )
    resource_by_key = {key: processors_manifest[key]["resources"] for key in placed}
    labels = [f"Processor {key}" for key in placed]

    def _series(fields: dict[str, str]) -> dict[str, list[float]]:
        return {
            label: [float(resource_by_key[key][field]) for key in placed]
            for label, field in fields.items()
        }

    save_grouped_bars(
        labels,
        _series({"Logical depth": "logical_depth", "Transpiled depth": "transpiled_depth"}),
        "Computational depth",
        "Logical and transpiled circuit depth",
        figures / "depth_comparison.png",
        footnote=footnote,
    )
    save_grouped_bars(
        labels,
        _series({
            "Logical two-qubit gates": "logical_two_qubit_count",
            "Transpiled two-qubit gates": "transpiled_two_qubit_count",
        }),
        "Two-qubit instructions",
        "Two-qubit gate count before and after transpilation",
        figures / "two_qubit_comparison.png",
        footnote=footnote,
    )
    save_grouped_bars(
        labels,
        _series({
            "Explicit SWAP count": "explicit_swap_count",
            "CX-equivalent routing overhead": "routing_overhead_cx",
        }),
        "Gate count",
        "SWAP count and CX-equivalent routing overhead",
        figures / "routing_overhead.png",
        footnote=footnote,
    )
    save_grouped_bars(
        labels,
        _series({
            "Allocated physical qubits": "physical_qubits_allocated",
            "Used physical qubits": "physical_qubits_used",
        }),
        "Qubits",
        "Physical qubit allocation and use",
        figures / "qubit_utilization.png",
        footnote=footnote,
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
        footnote=footnote,
    )
    save_tradeoff_chart(rows, figures / "architecture_tradeoff.png", footnote=footnote)
    histograms = {}
    for row in rows:
        processor = processors_manifest[str(row["processor"])]
        execution = processor["executions"][str(row["execution_mode"])]
        histograms[f"{row['processor']} {row['execution_mode']}"] = {
            str(key): int(value) for key, value in execution["histogram"].items()
        }
    save_cut_histogram(histograms, figures / "cut_value_distribution.png")
