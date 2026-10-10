# Methodology

## Problem

The selected problem statement is O1, shown on the dashboard as PS-O1: weighted Max-Cut. Phase 1 asks for one problem, implemented once, and evaluated on Processor A and Processor B under shared controls. This repository does not implement a second problem statement.

The cut of an assignment `x` is the sum of the weights of edges whose endpoints differ. The classical reference for the five-vertex provisional instance is exhaustive enumeration, so the reported reference is an exact optimum. The returned assignment is checked by evaluating the cut function a second time.

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

On this basis, one logical RZZ decomposes to two CX gates when the qubits are already adjacent. An explicit SWAP that has not been decomposed is charged as three CX gates. The CX-equivalent routing overhead is

`transpiled CX count + 3 * explicit SWAP count - 2 * logical RZZ count`.

A zero SWAP count means SWAP instructions were decomposed or avoided. Optimization can cancel gates, so the overhead can be smaller than a hand count of inserted SWAPs and can be negative. The same optimization level, layout method, routing method, and transpiler seed are used for both processors. One seed is one layout sample, not an average over Sabre.

## Execution

Ideal runs use Qiskit Aer with no noise model. Provisional noisy runs use the illustrative depolarizing and readout model stored in the processor files, with the same rates on A and B. `rz` is noiseless. These rates are the Challenge Guide's placeholder, not a claim about IBM hardware. No result in this repository comes from a quantum processing unit.

The expected-cut standard error is the square root of the plug-in one-shot variance divided by the number of shots. The binomial standard error is used only for the optimal-shot proportion. If the exact optimum is zero, the approximation ratio is left undefined.

## What would make the benchmark official

Replace `data/raw/maxcut_provisional.json`, `processors/processor_A.json`, and `processors/processor_B.json` with the organizer files, set their official flags only when those files are the issued definitions, and keep the runner's shared settings. Until that replacement, `official_benchmark_complete` stays false.
