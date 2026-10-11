# Methodology

## Problem

The selected problem statement is O1, shown on the dashboard as PS-O1: weighted Max-Cut. Phase 1 asks for one problem, implemented once, and evaluated on Processor A and Processor B under shared controls. This repository does not implement a second problem statement.

The cut of an assignment `x` is the sum of the weights of edges whose endpoints differ. The classical reference for the active six-vertex custom instance is exhaustive enumeration, so the reported reference is an exact optimum of that graph. The returned assignment is checked by evaluating the cut function a second time. A separate test enumeration does not call that function.

## QAOA

The cost Hamiltonian is

`H_C = sum over edges (u, v) of w_uv * (I - Z_u Z_v) / 2`.

Its computational-basis eigenvalues are the cut values. The mixer is the sum of `X` on every vertex. Layer `k` applies `RZZ(-gamma_k * w_uv)` on each edge and then `RX(2 * beta_k)` on each vertex. The initial state is the uniform superposition. Omitting a global phase on each edge does not change the measurement distribution; the relative phase between cut and uncut basis states is covered by the unit tests.

Depth `p = 1` is a provisional default. The supplied Phase 1 documents do not prescribe `p`, the optimizer, or the shot count.

## Shared parameters

Parameters are optimized once, on the logical circuit, with an ideal statevector expectation of the weighted cut. A deterministic grid over `gamma` in `[0, pi]` and `beta` in `[0, pi/2]` chooses the start point. COBYLA then refines that point with a fixed iteration budget. Both processors receive that same parameter vector. This is a shared-parameter architecture comparison. It is not a processor-specific re-optimization, and the two studies are not mixed.

## Compilation

Each processor file supplies the coupling map and basis gates. Undirected edges are expanded to both CX directions only when `gate_directionality` is `bidirectional`. Directed files keep the listed directions. The compiled circuit is rejected if it contains a gate outside the basis or a two-qubit gate off the directed coupling map.

Logical measurement outcomes are recovered from the transpiler final layout together with the actual measure instructions. Tests check that a known computational-basis state survives routing on the five-qubit path.

## Routing metric

On this basis, one logical RZZ decomposes to two CX gates when the qubits are already adjacent. The reported routing overhead is

`transpiled CX count - 2 * logical RZZ count`.

Explicit SWAP instructions are counted separately. Three CX per remaining SWAP is recorded as its own quantity and is not added to the CX excess. Adding both would count a SWAP twice when its CX gates are already in the transpiled CX count. A zero SWAP count means no SWAP instruction remains. It does not mean routing added no CX gates. Optimization can cancel gates, so the excess can be smaller than a hand count of inserted SWAPs and can be negative. The same optimization level, layout method, routing method, and transpiler seed are used for both processors. One seed is one layout sample, not an average over Sabre.

`approximation_ratio` and `expected_cut_approximation_ratio` in the result tables are the expected-cut ratio `E[C] / C_ref`. `best_cut_approximation_ratio` is `C_best / C_ref`. They are different quantities. The active tables are `results/tables/AB_comparison.csv`. The five-vertex tables, where the best observed cut was 9.5, are archived under `results/historical/framework_coupling_5vertex/`.

Depth `p = 2` is available as an optional provisional config at `config/experiment_p2_provisional.json`. It uses `cobyla_only`, writes to `results/optional_p2_provisional`, and was not executed for the preserved baseline. The grid optimizer remains depth 1. No source in this repository requires SamplerV2.

## Execution

Ideal runs use Qiskit Aer with no noise model. Provisional noisy runs use the illustrative depolarizing and readout model stored in the processor files, with the same rates on A and B. `rz` is noiseless. These rates are the Challenge Guide's placeholder, not a claim about IBM hardware. No result in this repository comes from a quantum processing unit.

The expected-cut standard error is the square root of the plug-in one-shot variance divided by the number of shots. The binomial standard error is used only for the optimal-shot proportion. If the exact optimum is zero, the approximation ratio is left undefined.

## What would make the benchmark official

The current executable maps are the undirected framework lists: Processor A has edges `(0,1), (1,2), (1,3), (3,4)`, and Processor B has the 12 edges of the 9-qubit list. Basis gates, both CX directions, and the illustrative noise block remain provisional. The active graph is the participant-selected custom file `data/raw/maxcut_custom_6vertex.json`. It is not an organizer-issued edge list. This run keeps one shared deterministic grid plus COBYLA. The saved parameters are the best recorded evaluation. A COBYLA `success` value of false means the iteration cap was reached. The five-vertex framework-map run is archived under `results/historical/framework_coupling_5vertex/`. The earlier linear and Lagos run is archived under `results/historical/line_lagos_5vertex/`.

Replace `data/raw/maxcut_provisional.json`, `processors/processor_A.json`, and `processors/processor_B.json` with the organizer files, set their official flags only when those files are the issued definitions, and keep the runner's shared settings. Until that replacement, `official_benchmark_complete` stays false.
