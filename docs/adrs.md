# Architecture decision records

These records describe decisions visible in the current repository. Where a choice was made during the provisional build and is still present in the code, that is stated. Alternatives are included only when the code or the surrounding documents show that they were considered.

## ADR-1. Shared parameters for the A/B comparison

The runner optimizes one logical QAOA circuit on an ideal statevector and applies that parameter vector to both processors. `config/experiment.json` accepts only `shared_parameter_architecture_comparison`. A processor-specific re-optimization was not implemented. The consequence is that measured quality differences, if any, come from compilation and noise rather than from a second optimizer.

## ADR-2. Provisional processor files stay executable and unofficial

`processors/processor_A.json` now uses the framework undirected edges `(0,1), (1,2), (1,3), (3,4)`. `processors/processor_B.json` now uses the framework 9-qubit undirected list. Both keep `provenance.official` false because the noise model, directed calibration, and Max-Cut instance were not issued with those edge lists. The earlier linear and Lagos files are copied under `processors/historical/`, and that benchmark is copied under `results/historical/line_lagos_5vertex/`.

The 14-page overview diagram captions Processor B as 7 qubits. The explicit framework edge list is the one loaded for the new run. The synthetic 9-qubit path fixture is not Processor B.

## ADR-3. Official status requires a named Challenge Kit file

The loader reads qubit count, edges, basis gates, and noise from JSON. It does not fill missing edges. If `provenance.official` is true, `provenance.challenge_kit_file` must name the issued file. `official_benchmark_complete` is true only when the instance and both processors are official. No current input meets that condition.

## ADR-4. Nine-qubit support is a schema fixture

`processors/fixtures/nine_qubit_schema_not_official.json` is a synthetic path of nine qubits. It exists so tests can load and compile a 9-qubit configuration. It is not Processor B.

## ADR-5. Expected-cut ratio and best-cut ratio are separate

`approximation_ratio` and `expected_cut_approximation_ratio` are `E[C] / C_ref`. `best_cut_approximation_ratio` is `C_best / C_ref`. The active comparison is `framework-coupling-custom-6vertex-p1` on `data/raw/maxcut_custom_6vertex.json`. That file is a participant-selected custom graph, not an organizer instance. The five-vertex comparison remains under `results/historical/framework_coupling_5vertex/`.

## ADR-6. Routing overhead is CX excess, not an inserted-SWAP count

The reported overhead is transpiled CX count minus twice the logical RZZ count. Explicit SWAP instructions are counted separately, and three CX per remaining SWAP is not added to the excess. The earlier combined formula would double-count a SWAP whose CX gates were already in the CX count. Compiler optimization can still change the CX count. The preserved run has zero explicit SWAP instructions, so its stored overhead numbers match this CX excess.

## ADR-7. Depth 1 remains the recorded baseline

The preserved experiment uses depth 1, a 21 by 21 grid, then COBYLA. The grid optimizer raises an error for any other depth. `config/experiment_p2_provisional.json` selects `cobyla_only` at depth 2 and a separate output directory. That file was not executed. No repository source requires depth 2 or SamplerV2.

## ADR-8. Simulation only

Ideal runs use Aer without a noise model. Noisy runs use the illustrative depolarizing and readout block stored in the processor JSON. The experiment manifest records `hardware_execution` false. Nothing in the runner submits a circuit to a quantum processor.

## ADR-9. Classical optimum check is not a second objective

The solver re-evaluates its chosen assignment with the same `cut_value` function. That is a consistency check. The provisional optimum 9.5 is also checked by a separate bit-mask enumeration in `tests/test_max_cut.py` that sums edge weights directly. That value is the optimum of the provisional graph only.
