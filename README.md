# Q-TEAM | PS-O1 Weighted Max-Cut | Qiskit Fall Fest 2026 Phase 1

Qiskit Fall Fest 2026 at SRM University-AP. Phase 1 online qualification. Team Q-TEAM. Track: Quantum Optimization. Organizer code: `O1`. Dashboard identifier: `PS-O1`.

This repository builds a weighted Max-Cut QAOA circuit, compiles it for two processor coupling graphs, and compares circuit cost, routing overhead, and shot-based cut quality. Phase 1 stops at Processor A and Processor B. Processor C, Processor D, and the Bell-correlation study are not part of this submission.

## Problem

Given an undirected weighted graph, assign each vertex 0 or 1 so that the total weight of edges with different endpoints is maximized. The executable instance is `data/raw/maxcut_provisional.json`: five vertices and seven weighted edges. The supplied Phase 1 documents name Max-Cut and do not include an official graph, so this instance is provisional. `official` is false in the file. Replacing that file is the intended way to drop in the Challenge Kit instance.

The exact optimum on this instance, from exhaustive enumeration, is **9.5**, with assignment `(1, 1, 0, 1, 0)` in vertex order. The solver checks that assignment with the cut function before accepting it.

## Technical objective

How does quantum processor connectivity affect the transpiled circuit cost, routing overhead, and observed solution quality of one QAOA Max-Cut circuit under shared parameters, shots, and transpiler settings?

## Workflow

```
provisional weighted graph
        |
        v
classical exhaustive optimum
        |
        v
logical depth-1 QAOA circuit
        |
        v
ideal statevector parameter search
        |
        +------------------+
        v                  v
   Processor A        Processor B
   framework 5-qubit  framework 9-qubit list
        |                  |
        v                  v
   Sabre compile      Sabre compile
        |                  |
        +--------+---------+
                 v
        ideal shots and provisional-noise shots
                 |
                 v
        tables, figures, manifest, report
```

## QAOA formulation

The cost Hamiltonian is the sum over edges of `w_uv * (I - Z_u Z_v) / 2`. Its computational-basis value is the weighted cut. The mixer is the sum of `X` on every vertex. Each layer applies `RZZ(-gamma * w_uv)` and then `RX(2 * beta)`. The run uses depth `p = 1` because the documents do not specify a depth. Parameters are optimized once on the logical statevector and then offered to both processors. A processor is not executed when it has fewer physical qubits than the logical circuit, and its measurements are not copied from the other processor.

The search is a 21 by 21 grid of `gamma` in `[0, pi]` and `beta` in `[0, pi/2]`, followed by COBYLA with at most 40 iterations. COBYLA stopped because it reached that evaluation cap (`success` is false in the manifest). The reported parameters are the best finite objective seen across the grid and COBYLA, 481 evaluations in total:

- `gamma = 0.36578315088218344`
- `beta = 0.37018328088858676`
- ideal statevector expected cut = `7.8151`

## Processors

The current executable coupling lists come from the 21-page framework. Processor A has undirected edges `(0,1), (1,2), (1,3), (3,4)`. Processor B has the 12-edge 9-qubit list. Basis gates, both CX directions, and the noise model remain provisional. The active graph is the custom six-vertex file. The 14-page overview diagram captions Processor B as 7 qubits. `official_benchmark_complete` remains false. A separate five-vertex run, `framework-coupling-supplementary-5vertex-p1`, is written only under `results/supplementary/five_vertex_framework/`. The earlier linear and Lagos run is in `results/historical/line_lagos_5vertex/`.

| | Processor A | Processor B |
| --- | --- | --- |
| Qubits | 5 | 9 |
| Edges | `(0,1), (1,2), (1,3), (3,4)` | framework 12-edge list, including `(0,8)` |
| Provenance | 21-page framework undirected list | 21-page framework undirected list |
| Basis | local assumption `rz`, `sx`, `x`, `cx`, both CX directions | same local assumption |
| Official | false | false |

Noise, when enabled, is the Challenge Guide section 10 illustration on both processors: depolarizing probability 0.001 on `x` and `sx`, 0.01 on `cx`, readout `[[0.99, 0.01], [0.02, 0.98]]`, and no error on `rz`. Ideal runs do not use that model. Lagos calibration data are not used. These simulations are not IBM QPU executions.

Details are in `docs/processor_specifications.md` and `docs/methodology.md`.

## Transpilation

Both processors use optimization level 1, Sabre layout, Sabre routing, and transpiler seed `20261010`. One logical `RZZ` becomes two `CX` gates on an all-to-all device with this basis. Routing overhead is the transpiled CX count minus twice the logical RZZ count. Explicit SWAP instructions are counted separately and are not added to that excess, so decomposed SWAP CX gates are not charged again. CX excess is the transpiled CX count minus twice the logical RZZ count. It is not a literal SWAP count. A zero explicit SWAP count does not mean the routing overhead is zero. Compiler optimization can also change the CX count. Measurement bits are mapped back to logical vertices with the final layout.

`E[C] / C_ref` and `C_best / C_ref` are different ratios.

## Measured results

These figures are the run `framework-coupling-custom-6vertex-p1`. The graph is the participant-selected custom six-vertex instance, not an organizer graph. The exact optimum is 21. Shots: 4096. Simulator seed: `20261010`. Noise remains the illustrative provisional model. Authoritative rows are in `results/tables/AB_comparison.csv`.

Processor A has 5 physical qubits. The logical circuit needs 6, so Processor A was not executed and no Processor A shot or transpiled metrics were written. Processor B has 9 physical qubits and was executed with the same shared parameters.

| Metric | Processor A | Processor B |
| --- | ---: | ---: |
| Placement | not executed (5 qubits, circuit needs 6) | executed |
| Logical depth | 10, shared circuit | 10 |
| Transpiled depth | — | 48 |
| Logical single-qubit gates | 12, shared circuit | 12 |
| Transpiled single-qubit gates | — | 58 |
| Logical two-qubit gates (`RZZ`) | 10, shared circuit | 10 |
| Transpiled CX count | — | 26 |
| Explicit SWAP count | — | 0 |
| CX excess over 2 CX per RZZ | — | 6 |
| Physical qubits allocated / used | 5 / not used | 9 / 6 |
| Ideal expected cut (SE) | — | 17.7227 (0.0491) |
| Ideal E[C]/C_ref | — | 0.8439 |
| Ideal optimal-bitstring probability (SE) | — | 0.2632 (0.0069) |
| Provisional-noise expected cut (SE) | — | 16.9597 (0.0566) |
| Provisional-noise E[C]/C_ref | — | 0.8076 |
| Best observed cut | — | 21 |

The ideal Processor B shot mean sits near the statevector value 17.8055. COBYLA stopped at `MAXFUN`; the saved parameters are the best recorded evaluation. There is no A-versus-B noisy gap in this run, because Processor A produced no shots. The five-vertex comparison that used these same processor maps is a separate experiment, `framework-coupling-supplementary-5vertex-p1`, under `results/supplementary/five_vertex_framework/`. Its optimum is 9.5, and both processors were executed there. Those numbers are not Processor A results for the six-vertex graph.

## Installation

Python 3.11.9. From the repository root:

```
python -m pip install -r requirements.txt
```

## Commands

```
python -m pytest
python scripts/validate_processors.py
python scripts/run_benchmark.py
python scripts/generate_report.py
```

Run the notebook from the repository root so `Path.cwd()` is the project directory. `main.ipynb` calls `run_controlled_experiment` and then prints the comparison table.

## Outputs

| Path | Contents |
| --- | --- |
| `results/tables/AB_comparison.csv` | Problem metrics and circuit metrics for each processor and execution mode |
| `results/tables/circuit_resources.csv` | One resource row per processor |
| `results/tables/processor_*_counts.json` | Shot histograms |
| `results/tables/optimizer_history.json` | Parameter-search trace |
| `results/figures/` | Coupling graphs, circuits, depth, two-qubit count, routing, qubit use, performance, tradeoff, cut distribution |
| `results/circuits/` | Bound logical OpenQASM, transpiled OpenQASM, layouts |
| `results/manifests/experiment_manifest.json` | Seeds, hashes, versions, parameters, status |
| `data/processed/instance_with_reference.json` | Instance plus the classical reference |
| `report.md` | Technical report populated from the manifest |

`official_benchmark_complete` in the manifest is false. The blocking list is in the manifest and at the end of `report.md`.

## Reproducibility

`docs/reproducibility.md` lists the seeds, the shared controls, and the package pins. Repeating `python scripts/run_benchmark.py` with the pinned environment is the reproduction command. Unit tests and the integration test use a temporary directory and a smaller budget. They are not the Phase 1 tables.

## Limitations

- The active graph is the participant-selected custom six-vertex file `data/raw/maxcut_custom_6vertex.json`. Its optimum 21 is not an official O1 optimum. `official_benchmark_complete` remains false.
- The coupling lists are the undirected framework maps. Basis gates, both CX directions, and the noise model are local assumptions.
- Processor A cannot place the 6-qubit logical circuit. The earlier five-vertex A/B comparison remains archived.
- The 14-page overview diagram captions Processor B as 7 qubits. The executable file uses the 9-qubit framework list.
- The configured noise rates are identical on purpose. A real device comparison could differ in gate errors as well as connectivity.
- One Sabre seed is one layout sample.
- COBYLA stopped at its evaluation cap. The kept parameters are the best evaluated point, not a claim that the local solver certified a global maximum.
- No circuit in this repository was executed on a quantum processor.

## References

1. Qiskit Fall Fest 2026 guideline, Steven Rayan, quanTA / University of Saskatchewan.
2. Qiskit Fall Fest 2026 Phase 1 participant instructions, SRM University-AP.
3. Phase 1 challenge guide, geometry-aware processor starter.
4. Farhi, Goldstone, and Gutmann, A Quantum Approximate Optimization Algorithm, arXiv:1411.4028.
5. IBM Quantum, The IBM Quantum heavy hex lattice.
6. Qiskit IBM Runtime `props_lagos.json`, cited only for the archived 7-qubit fragment under `processors/historical/`. It is not the current Processor B map.

## AI assistance

Cursor Grok assisted with the implementation, tests, figures, and documentation. The Phase 1 instructions require the team to understand, verify, and take responsibility for the submission, and to disclose AI assistance when the organizer policy requires it. `docs/ai_prompt.md` is a reconstructed summary of that assistance, and `docs/adrs.md` records the architectural decisions present in this repository. Verification recorded here is the pytest run and the seeded benchmark that wrote `results/`.

## Publishing to GitHub

The local `main` branch tracks `origin` at `https://github.com/TARUN062005/qff-2026-solution.git`. The last commit is `db56aa6`. Uncommitted work is still only in the working tree. Do not commit tokens or credential files. This tree does not contain any. Confirm the repository is visible to the judges before submitting the URL.
