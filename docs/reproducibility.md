# Reproducibility

## Environment

The benchmark was developed for Python 3.11.9. Install the pinned packages in `requirements.txt`. The manifest records the Python version and the installed versions of Qiskit, Qiskit Aer, NumPy, SciPy, NetworkX, Matplotlib, Pillow, and pylatexenc after a run.

## Commands

From the repository root:

```
python -m pip install -r requirements.txt
python -m pytest
python scripts/validate_processors.py
python scripts/run_benchmark.py
python scripts/generate_report.py
```

`run_benchmark.py` reads `config/experiment.json`, writes `results/`, and writes `report.md`. A second run with the same config and package versions is intended to reproduce the same transpiler layout and the same shot histograms, because the transpiler seed and the Aer seed are fixed and the parameter search does not draw random numbers.

## What is recorded

The files under `results/` and the numerical sections of `report.md` record the run identified by `experiment_id` `framework-coupling-custom-6vertex-p1`. That run uses the framework coupling lists, the illustrative noise model, and the participant-selected custom 6-vertex graph `data/raw/maxcut_custom_6vertex.json`. Processor A was not executed because it has 5 physical qubits and the circuit needs 6. `official_benchmark_complete` is false. The supplementary five-vertex run `framework-coupling-supplementary-5vertex-p1` is stored only under `results/supplementary/five_vertex_framework/` and is not part of the six-vertex tables. The archived copy of the earlier five-vertex framework-map run remains under `results/historical/framework_coupling_5vertex/`. The earlier linear and Lagos benchmark is stored under `results/historical/line_lagos_5vertex/`.

The manifest at `results/manifests/experiment_manifest.json` stores the instance SHA-256, both processor SHA-256 values, QAOA depth, the shared parameter vector, the optimizer budget, the transpiler settings, the simulator seed, the shot count, the noise provenance, circuit metrics, and the run status. Count histograms and OpenQASM circuits are stored beside it. Derived tables and figures are regenerated from those outputs by the same command.

## Controls that stay fixed across A and B

The problem file, QAOA depth, parameter vector, shot count, optimization level, layout method, routing method, transpiler seed, simulator seed, and basis gates are shared. The coupling maps differ because that is the comparison. Ideal and provisional-noise executions are separate rows.

## AI assistance

Cursor Grok was used to implement, test, and document this repository. The Phase 1 instructions require participants to understand, verify, and take responsibility for submitted work, and to disclose AI assistance when the organizer policy requires it. The tests and the seeded benchmark run are the verification recorded in this repository. AI assistance does not make the provisional processor maps or the provisional graph official.

## Official kit

Do not mark a file official unless it is the file issued for the challenge. An official processor file must also name `provenance.challenge_kit_file`. Keep optional studies out of `config/experiment.json`. `config/experiment_p2_provisional.json` is an optional depth-2 study and was not executed. Smoke and unit tests write to a temporary directory and use a smaller budget; they are not the Phase 1 result tables. The current manifest stores repository-relative paths for the config, instance, processor files, output directory, and artifact folders. Hashes and seeds are unchanged by that path formatting.
