# PS-O1 Weighted Max-Cut: Processor A/B QAOA Report

## 1. Abstract

This Phase 1 study implements weighted Max-Cut with the Quantum Approximate Optimization Algorithm and compiles the same parameterized circuit for two processor models. Shared parameters are chosen by an ideal statevector optimization. Processor A was not executed because it has insufficient qubits. Processor A has 5 qubits and the logical circuit needs 6. No shots or transpiled metrics were produced for this processor. No measurements were inferred for it. This report is not a complete Processor A versus Processor B measurement comparison. The coupling edges are the undirected lists in the 21-page framework: Processor A has 5 qubits and Processor B has 9 qubits. Basis gates, both CX directions, the noise model, and the Max-Cut graph remain provisional. The 14-page overview diagram captions Processor B as 7 qubits; this run uses the framework's 9-qubit edge list. This report is not an official benchmark. Earlier linear and Lagos results are kept under results/historical/line_lagos_5vertex/.

## 2. Problem statement

Track: Quantum Optimization. Organizer code: O1. Dashboard identifier: PS-O1. Team: Q-TEAM. The selected problem is weighted Max-Cut. Phase 1 compares Processor A and Processor B. Processor C, Processor D, and the Bell-correlation study belong to the offline phase and are outside this run.

## 3. Research objective

How does quantum processor connectivity affect the transpiled circuit cost, routing overhead, and observed solution quality of a QAOA-based weighted Max-Cut solution under controlled experimental conditions?

## 4. Weighted Max-Cut formulation

For an undirected weighted graph and a bit assignment x, the cut is the sum of w_uv over edges whose endpoints receive different bits. The cost Hamiltonian used here is the sum over edges of w_uv (I - Z_u Z_v) / 2. Its computational-basis eigenvalue equals that cut. The mixer is the sum of X on every vertex. QAOA layer k applies the cost evolution with parameter gamma_k and then the mixer evolution with parameter beta_k, implemented as RZZ(-gamma_k w_uv) and RX(2 beta_k). Global phases that are identical for every basis state are omitted because they do not change measurement probabilities.

## 5. Classical reference method

Method: exhaustive_enumeration. Optimality guaranteed: True. Reference cut: 21.0000. Assignment, with vertex 0 in the first position: [1, 1, 0, 0, 1, 0]. The solver re-evaluated that assignment with the same cut function as a consistency check. A separate exhaustive enumeration in the test suite checks this graph without calling that function. Instance `participant-custom-weighted-maxcut-6` has 6 vertices and 10 edges. Official instance: False. Provenance: Participant-selected custom graph. It has 6 vertices and integer edge weights from 1 to 5. The 21-page framework allows one custom graph and describes a 6-vertex task, but it does not include a designated edge list. This file is not an organizer-provided instance and must not be reported as the official O1 graph. The reference cut belongs to this loaded instance. It is not an official O1 optimum.

## 6. QAOA circuit formulation

Depth p = 1. Parameter vector, ordered gamma then beta: [0.17999663227285423, 0.33781294897063635]. The ideal statevector expectation at those parameters is 17.8055. Optimizer: grid_then_cobyla. Objective evaluations: 481. COBYLA reported success=False with message: Return from COBYLA because the objective function has been evaluated MAXFUN times. That success flag is the solver status. The saved vector is the recorded evaluation with the largest expected cut, selected by `maximum expected cut across every recorded grid and COBYLA evaluation`. The last COBYLA evaluation has expected cut 17.8055, and the range of the last five COBYLA objectives is 1.313e-09. For depth 1, a deterministic grid over gamma in [0, pi] and beta in [0, pi/2] supplies the COBYLA start. The configured initial vector is recorded and is not a second, processor-specific start. The framework also permits several random initial parameters or Qiskit's QAOA module. This run uses the deterministic grid.

## 7. Processor A specification and provenance

Processor A is recorded as official=False, status `framework_coupling_map`. It has 5 qubits and coupling edges [[0, 1], [1, 2], [1, 3], [3, 4]]. Basis gates: ['rz', 'sx', 'x', 'cx']. The undirected edges are the framework list (0,1), (1,2), (1,3), (3,4), not the earlier linear path. Basis gates and both CX directions are a local assumption. SHA-256 of the definition file: bfc9bb81ab637787cb8c4f1434b5b1f53666de8754b5b0c7a18f23aecf2e0b0e.

## 8. Processor B specification and provenance

Processor B is recorded as official=False, status `framework_coupling_map`. It has 9 qubits and coupling edges [[0, 1], [1, 2], [1, 6], [2, 3], [2, 6], [2, 5], [3, 4], [4, 5], [5, 6], [6, 7], [6, 8], [0, 8]]. Basis gates: ['rz', 'sx', 'x', 'cx']. Those edges are the framework 9-qubit list, not the 7-qubit Lagos fragment and not the synthetic schema fixture. The 14-page overview diagram is captioned 7 qubits. Basis gates and both CX directions are a local assumption. SHA-256 of the definition file: b44c7415700fe0fa8ab16553fc7861ba74d3165c3e71f583529246217e291fd5.

## 9. Experimental methodology

One logical QAOA circuit is built for the selected instance. Parameters are optimized once on that logical circuit with an ideal statevector. Each processor is then asked to compile that circuit with the same transpiler seed, optimization level, layout method, and routing method. A processor is not executed when its physical qubit count is smaller than the logical circuit. Processor A was not executed because it has insufficient qubits. Processor A has 5 qubits and the logical circuit needs 6. No shots or transpiled metrics were produced for this processor. No measurements were inferred for it.

## 10. Controlled experimental settings

Comparison type: shared_parameter_architecture_comparison. Shots: 4096. Transpiler optimization level: 1. Layout method: sabre. Routing method: sabre. Transpiler seed: 20261010. Simulator seed: 20261010. Execution modes: ideal, provisional_noise. Basis gates identical: True. Illustrative noise rates identical: True.

## 11. Transpilation and routing methodology

Qiskit preset transpilation maps the logical circuit onto each coupling map and the shared basis rz, sx, x, cx, with the same optimization level, layout method, routing method, and transpiler seed on both processors. An RZZ gate decomposes to two CX gates on an all-to-all device with this basis. The stored routing overhead is the transpiled CX count minus two times the logical RZZ count. Explicit SWAP instructions are counted separately. Their three-CX equivalent is stored beside that excess and is not added to it, so a SWAP that has already been decomposed into CX gates is not charged a second time. A zero explicit SWAP count means no SWAP instruction remains. It does not mean that routing added no two-qubit operations. Compiler optimization can cancel or rewrite CX gates, so the excess is not a direct count of inserted SWAP gates.

## 12. Simulation and noise assumptions

Ideal runs use the Qiskit Aer automatic simulator with no noise model. Provisional noisy runs attach the illustrative depolarizing and readout model stored in each processor file: probability 0.001 on x and sx, probability 0.01 on cx, and readout matrix [[0.99, 0.01], [0.02, 0.98]]. rz is noiseless. These rates come from the Challenge Guide's illustrative example and are applied to both processors so connectivity, rather than unequal error rates, is the controlled difference. This is a circuit-level simulator. It is not execution on an IBM quantum processor.

## 13. Problem-performance results

Processor A was not executed. Processor A has 5 qubits and the logical circuit needs 6. No shots or transpiled metrics were produced for this processor.
Mode `ideal`: Processor B expected cut 17.7227 (SE 0.0491), best observed 21.0000, expected-cut approximation ratio E[C]/C_ref 0.8439, best-cut ratio C_best/C_ref 1.0000, optimal-bitstring probability 0.2632.
Agreement of the ideal shots with the statevector expectation, within four standard errors: Processor B True.
Mode `provisional_noise`: Processor B expected cut 16.9597 (SE 0.0566), best observed 21.0000, expected-cut approximation ratio E[C]/C_ref 0.8076, best-cut ratio C_best/C_ref 1.0000, optimal-bitstring probability 0.2139.

## 14. Circuit-resource results

Logical computational depth 10, logical single-qubit gates 12, logical two-qubit gates 10, logical operations 22. These logical figures are properties of the shared circuit.
A direct A/B circuit comparison is not available because one processor could not hold the logical circuit.
Processor B transpiled depth 48, transpiled single-qubit gates 58, CX count 26, explicit SWAP count 0, CX excess 6, physical qubits allocated 9, used 6. CX excess is transpiled CX count minus twice the logical RZZ count. It is not a literal SWAP count. A zero explicit SWAP count does not mean the routing overhead is zero.

## 17. Statistical uncertainty and reproducibility

The expected-cut standard error is the square root of the plug-in shot variance divided by the number of shots. It describes multinomial sampling for this seeded run. It does not describe variation over transpiler seeds. The COBYLA success flag is separate from the selected parameters. The optimal-success standard error uses the binomial proportion formula only for that success indicator. The column approximation_ratio, and the phrase expected-cut approximation ratio, both mean E[C]/C_ref. The best-cut ratio is C_best/C_ref and is a different quantity. The approximation-ratio standard error scales the expected-cut standard error by the classical reference when that reference is positive. A zero reference leaves both ratios undefined. Package versions, seeds, file hashes, and the parameter vector are stored in the experiment manifest.

## 18. Scientific interpretation

No noisy expected-cut gap between Processor A and Processor B is reported. This is not a complete A/B measurement comparison. A processor was not executed when it had fewer physical qubits than the logical circuit, and its measurements were not inferred from the other processor.

## 19. Limitations and threats to validity

The coupling maps in this report are the undirected framework lists. The noise model is the illustrative provisional model. The executed graph `participant-custom-weighted-maxcut-6` has 6 vertices and is not an organizer-issued instance, so official_benchmark_complete remains false. One Sabre seed is not a distribution over layouts. These results do not support a universal hardware ranking. Processor A was not executed because it has insufficient qubits. Processor A has 5 qubits and the logical circuit needs 6. No shots or transpiled metrics were produced for this processor. No measurements were inferred for it. Measured rows belong only to the processor that was executed.

## 20. Conclusion

The measured circuit costs and cut statistics describe only the processors that can hold this 6-vertex instance. A processor with fewer physical qubits than the logical circuit has no invented shot metrics. The noise model and this graph stay provisional until the organizer issues the simulator configuration and the designated instance.

## 21. References

1. Qiskit Fall Fest 2026 guideline, Steven Rayan, quanTA, University of Saskatchewan, supplied as QFF_IBM_Hackathon_Guideline.pdf.
2. Qiskit Fall Fest 2026 Phase 1 participant instructions, SRM University-AP.
3. Qiskit Fall Fest 2026 Phase 1 challenge guide, geometry-aware processor and architecture starter.
4. Farhi, Goldstone, and Gutmann, A Quantum Approximate Optimization Algorithm, arXiv:1411.4028.
5. IBM Quantum, The IBM Quantum heavy hex lattice, https://www.ibm.com/quantum/blog/heavy-hex-lattice.
6. Qiskit IBM Runtime, ibm_lagos coupling recorded in props_lagos.json, https://github.com/Qiskit/qiskit-ibm-runtime/blob/main/qiskit_ibm_runtime/fake_provider/backends/lagos/props_lagos.json.
7. Qiskit and Qiskit Aer documentation for transpilation, layouts, and noise models matching the versions in the manifest.

## Blocking specifications

- Processor A coupling edges are the undirected framework list (0,1), (1,2), (1,3), (3,4). Basis gates and both CX directions are a local assumption. Official directed calibration was not supplied.
- Processor B coupling edges are the undirected 9-qubit framework list. The 14-page overview diagram is captioned 7 qubits. Basis gates and both CX directions are a local assumption.
- The noise rates are the illustrative Challenge Guide model. The framework says organizer benchmark definitions are authoritative for the final noise model, and those parameters were not in the coupling-map documents.
- The executed Max-Cut graph is participant-custom-weighted-maxcut-6 (6 vertices). It is not an organizer-provided instance. Its optimum is not an official O1 optimum.
- QAOA depth 1 with a deterministic grid and COBYLA is the selected reproducible policy. The framework permits p=1 or p=2. It does not require SamplerV2.

Official benchmark complete: False.
Software run success: True.

The blocker bullets above are the text stored in this run's manifest. The noise model named there is illustrative. It is not an official calibration, and a result from another graph is not a result of this experiment.
