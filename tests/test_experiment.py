from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.experiment import run_controlled_experiment
from src.max_cut import build_instance, cut_value
from src.metrics import samples_from_counts, summarize_cut_samples
from src.simulator import execute_counts
from src.transpilation import TranspilationError


ROOT = Path(__file__).resolve().parents[1]


def _write(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


def _config(directory: Path, instance: Path, processor_a: Path, processor_b: Path, modes: list[str]) -> Path:
    payload = {
        "team": "Q-TEAM",
        "event": "Qiskit Fall Fest 2026",
        "phase": "Phase 1",
        "track": "Quantum Optimization",
        "problem_code": "O1",
        "dashboard_identifier": "PS-O1",
        "problem_title": "Max-Cut on Weighted Graphs",
        "instance_path": str(instance),
        "processors": {"A": str(processor_a), "B": str(processor_b)},
        "qaoa_depth": 1,
        "comparison_type": "shared_parameter_architecture_comparison",
        "optimizer": {
            "method": "grid_then_cobyla",
            "grid_gamma_points": 2,
            "grid_beta_points": 2,
            "gamma_upper": 1.0,
            "beta_upper": 0.5,
            "cobyla_maxiter": 4,
            "cobyla_rhobeg": 0.2,
            "cobyla_tol": 1e-4,
        },
        "initial_parameters": [0.4, 0.2],
        "shots": 128,
        "optimization_level": 1,
        "seed_transpiler": 5,
        "seed_simulator": 9,
        "layout_method": "sabre",
        "routing_method": "sabre",
        "execution_modes": modes,
        "output_dir": str(directory / "configured-output"),
    }
    path = directory / "experiment.json"
    _write(path, payload)
    return path


def test_controlled_run_uses_one_instance_and_real_counts(tmp_path: Path) -> None:
    instance = build_instance([0, 1, 2], [(0, 1, 1.0), (1, 2, 1.5), (0, 2, 0.5)], instance_id="experiment-triangle")
    instance_path = tmp_path / "instance.json"
    _write(instance_path, instance.to_dict())
    output = tmp_path / "run"
    manifest = run_controlled_experiment(
        _config(
            tmp_path,
            instance_path,
            ROOT / "processors" / "processor_A.json",
            ROOT / "processors" / "processor_B.json",
            ["ideal"],
        ),
        output,
    )
    assert manifest["success"] is True
    assert manifest["official_benchmark_complete"] is False
    processors = manifest["processors"]
    assert processors["A"]["instance_sha256"] == processors["B"]["instance_sha256"]
    assert processors["A"]["instance_sha256"] == manifest["instance"]["sha256"]
    parameters = manifest["qaoa"]["parameters"]
    assert isinstance(parameters, list) and len(parameters) == 2
    comparison = (output / "tables" / "AB_comparison.csv").read_text(encoding="utf-8")
    assert "expected_cut" in comparison
    counts = json.loads((output / "tables" / "processor_A_ideal_counts.json").read_text(encoding="utf-8"))
    decoder = {
        int(clbit): int(logical)
        for clbit, logical in processors["A"]["resources"]["measurement_decoder"]
    }
    summary = summarize_cut_samples(
        samples_from_counts(counts, decoder, instance),
        float(manifest["classical_reference"]["objective_value"]),
        True,
    )
    recorded = float(processors["A"]["executions"]["ideal"]["expected_cut"])
    assert summary["expected_cut"] == pytest.approx(recorded)
    assert (output / "figures" / "processor_A_graph.png").exists()
    assert (output / "figures" / "routing_overhead.png").exists()
    assert (output / "report.md").exists()
    assert "provisional" in (output / "report.md").read_text(encoding="utf-8").lower()
    repeated = execute_counts(
        _compiled_from_qasm(output / "circuits" / "processor_A_transpiled.qasm"),
        128,
        9,
        None,
    )
    assert repeated == counts
    assignment = tuple(manifest["classical_reference"]["assignment"])
    assert cut_value(instance, assignment) == pytest.approx(manifest["classical_reference"]["cut_value"])


def test_failed_run_is_not_marked_successful(tmp_path: Path) -> None:
    tiny = {
        "name": "Tiny",
        "identifier": "T",
        "role": "test",
        "num_qubits": 2,
        "qubits": [0, 1],
        "coupling_map": [[0, 1]],
        "connectivity": "undirected",
        "basis_gates": ["rz", "sx", "x", "cx"],
        "gate_directionality": "bidirectional",
        "provenance": {"status": "test", "official": False, "source": "Unit test processor."},
    }
    processor_a = tmp_path / "a.json"
    processor_b = tmp_path / "b.json"
    _write(processor_a, tiny)
    _write(processor_b, tiny)
    instance = build_instance([0, 1, 2], [(0, 1, 1.0), (1, 2, 1.0)], instance_id="too-wide")
    instance_path = tmp_path / "wide.json"
    _write(instance_path, instance.to_dict())
    output = tmp_path / "failed"
    with pytest.raises(TranspilationError):
        run_controlled_experiment(
            _config(tmp_path, instance_path, processor_a, processor_b, ["ideal"]),
            output,
        )
    manifest = json.loads((output / "manifests" / "experiment_manifest.json").read_text(encoding="utf-8"))
    assert manifest["success"] is False
    assert manifest["error_type"] == "TranspilationError"


def _compiled_from_qasm(path: Path):
    from qiskit import QuantumCircuit

    return QuantumCircuit.from_qasm_file(str(path))
