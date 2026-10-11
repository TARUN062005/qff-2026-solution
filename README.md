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
   path, 5 qubits     Lagos-class fragment, 7 qubits
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

The cost Hamiltonian is the sum over edges of `w_uv * (I - Z_u Z_v) / 2`. Its computational-basis value is the weighted cut. The mixer is the sum of `X` on every vertex. Each layer applies `RZZ(-gamma * w_uv)` and then `RX(2 * beta)`. The run uses depth `p = 1` because the documents do not specify a depth. Parameters are optimized once on the logical statevector and then reused on both processors. That is a shared-parameter architecture comparison, not two independent optimizations.

The search is a 21 by 21 grid of `gamma` in `[0, pi]` and `beta` in `[0, pi/2]`, followed by COBYLA with at most 40 iterations. COBYLA stopped because it reached that evaluation cap (`success` is false in the manifest). The reported parameters are the best finite objective seen across the grid and COBYLA, 481 evaluations in total:

- `gamma = 0.36578315088218344`
- `beta = 0.37018328088858676`
- ideal statevector expected cut = `7.8151`

## Processors

Both executable definitions used for the recorded results are provisional. Processor A was the 5-qubit linear path. Processor B was the 7-qubit Lagos fragment. Those configurations do not represent the final organizer-confirmed architectures.

The uploaded Processor A diagram is an unlabeled five-node tree, so its exact numbered coupling map remains unverified. The organizer later corrected Processor B to nine qubits. That count takes precedence, and the full nine-qubit coupling map has not been supplied. The noise model and the Max-Cut graph are illustrative and provisional. `official_benchmark_complete` remains false.

| | Processor A | Processor B |
| --- | --- | --- |
| Qubits | 5 | 7 |
| Edges | `0-1-2-3-4` (4 edges) | `0-1`, `1-2`, `1-3`, `3-5`, `4-5`, `5-6` (6 edges) |
| Provenance | Challenge Guide illustrative path | Published `ibm_lagos` CX pairs from Qiskit IBM Runtime `props_lagos.json` |
| Basis | `rz`, `sx`, `x`, `cx`, both CX directions | same basis, both CX directions |
| Official | false | false |

Noise, when enabled, is the Challenge Guide section 10 illustration on both processors: depolarizing probability 0.001 on `x` and `sx`, 0.01 on `cx`, readout `[[0.99, 0.01], [0.02, 0.98]]`, and no error on `rz`. Ideal runs do not use that model. Lagos calibration data are not used. These simulations are not IBM QPU executions.

Details are in `docs/processor_specifications.md` and `docs/methodology.md`.

## Transpilation

Both processors use optimization level 1, Sabre layout, Sabre routing, and transpiler seed `20261010`. One logical `RZZ` becomes two `CX` gates on an all-to-all device with this basis. Routing overhead is the transpiled CX count minus twice the logical RZZ count. Explicit SWAP instructions are counted separately and are not added to that excess, so decomposed SWAP CX gates are not charged again. After basis translation the explicit SWAP count in the preserved run is zero. The extra CX gates are the routing and decomposition residue under this optimization level, not a direct inserted-SWAP count. Compiler optimization can also change the CX count. Measurement bits are mapped back to logical vertices with the final layout.

The approximation ratio in the preserved table is `E[C] / C_ref`. The best observed cut on every preserved row is 9.5, so `C_best / C_ref` is 1 for this provisional reference. Those are different ratios.

## Measured A/B results

These figures are the preserved provisional run on the 5-qubit linear Processor A model and the 7-qubit Lagos-fragment Processor B model. They are not results for the organizer-confirmed architectures. Shots: 4096. Simulator seed: `20261010`. Authoritative rows are in `results/tables/AB_comparison.csv`. Rounded values:

| Metric | Processor A | Processor B |
| --- | ---: | ---: |
| Logical depth | 8 | 8 |
| Transpiled depth | 33 | 41 |
| Logical two-qubit gates (`RZZ`) | 7 | 7 |
| Transpiled two-qubit gates (`CX`) | 27 | 21 |
| Explicit SWAP count | 0 | 0 |
| CX-equivalent routing overhead | 13 | 7 |
| Physical qubits allocated | 5 | 7 |
| Physical qubits used | 5 | 5 |
| Ancillas outside the logical layout | 0 | 0 |
| Ideal expected cut (SE) | 7.8300 (0.0275) | 7.8300 (0.0275) |
| Ideal approximation ratio | 0.8242 | 0.8242 |
| Ideal optimum-shot probability (SE) | 0.2485 (0.0068) | 0.2485 (0.0068) |
| Provisional-noise expected cut (SE) | 7.3936 (0.0305) | 7.4502 (0.0302) |
| Provisional-noise approximation ratio | 0.7783 | 0.7842 |
| Best observed cut, every mode | 9.5 | 9.5 |

The ideal histograms for A and B matched in this seeded run. The transpiled OpenQASM does not match: A has 27 CX gates and B has 21. Both ideal shot means sit within four standard errors of the statevector value 7.8151. On these settings, compilation preserved the logical measurement distribution, and the architecture difference shows up in the compiled circuit.

Processor B used fewer CX gates and a smaller routing overhead. Its transpiled depth was 41 against 33 on Processor A, so the lower two-qubit count did not produce a shorter critical path. Processor B allocated two physical qubits that the final circuit did not use.

Under the shared illustrative noise model, Processor A's noisy expected cut is lower, in the direction predicted by its extra CX gates. The gap is about 0.057 against a combined standard error of about 0.043, so it stays inside two combined standard errors. This run does not resolve a noisy quality difference.

These two small provisional models do not establish a general ranking of connectivities.

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

- The stored benchmark is a provisional run on the 5-qubit linear Processor A model and the 7-qubit Lagos-fragment Processor B model. Those configurations do not represent the final organizer-confirmed architectures.
- The Processor A diagram is an unlabeled five-node tree. Its exact numbered coupling map remains unverified.
- Processor B must use nine qubits according to the organizer's correction. The full coupling map has not been supplied.
- The current noise model and Max-Cut graph are illustrative and provisional. `official_benchmark_complete` remains false.
- Official Processor A edges, the nine-qubit Processor B edges, noise rates, the O1 graph, QAOA depth, and the shot budget were not in the supplied documents.
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
6. Qiskit IBM Runtime `props_lagos.json` for the 7-qubit CX pairs used as the provisional Processor B graph.

## AI assistance

Cursor Grok assisted with the implementation, tests, figures, and documentation. The Phase 1 instructions require the team to understand, verify, and take responsibility for the submission, and to disclose AI assistance when the organizer policy requires it. `docs/ai_prompt.md` is a reconstructed summary of that assistance, and `docs/adrs.md` records the architectural decisions present in this repository. Verification recorded here is the pytest run and the seeded benchmark that wrote `results/`.

## Publishing to GitHub

The repository is prepared locally and has not been pushed. From this directory, after reviewing the files:

```
git init
git add .
git status
git commit -m "Add provisional PS-O1 QAOA Max-Cut A/B benchmark"
```

Create an empty public GitHub repository, then:

```
git remote add origin <repository-url>
git push -u origin HEAD
```

Confirm the repository is visible to the judges before submitting the URL. Do not commit tokens or credential files. This tree does not contain any.
