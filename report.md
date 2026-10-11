# PS-O1 Weighted Max-Cut: Processor A/B QAOA Report

## 1. Abstract

This Phase 1 study implements weighted Max-Cut with the Quantum Approximate Optimization Algorithm and compiles the same parameterized circuit for two processor models. Shared parameters are chosen by an ideal statevector optimization, then both processors are executed with those parameters. Circuit cost, routing overhead, and shot-based cut statistics are compared. Every number below comes from the preserved provisional run that used the 5-qubit linear Processor A model and the 7-qubit Lagos-fragment Processor B model. Those configurations do not represent the final organizer-confirmed architectures. The Processor A diagram is an unlabeled five-node tree, so its exact numbered coupling map remains unverified. Processor B must use nine qubits according to the organizer's correction, and the full coupling map has not been supplied. The noise model and the Max-Cut graph are illustrative and provisional. This report is not an official benchmark.

## 2. Problem statement

Track: Quantum Optimization. Organizer code: O1. Dashboard identifier: PS-O1. Team: Q-TEAM. The selected problem is weighted Max-Cut. Phase 1 compares Processor A and Processor B. Processor C, Processor D, and the Bell-correlation study belong to the offline phase and are outside this run.

## 3. Research objective

How does quantum processor connectivity affect the transpiled circuit cost, routing overhead, and observed solution quality of a QAOA-based weighted Max-Cut solution under controlled experimental conditions?

## 4. Weighted Max-Cut formulation

For an undirected weighted graph and a bit assignment x, the cut is the sum of w_uv over edges whose endpoints receive different bits. The cost Hamiltonian used here is the sum over edges of w_uv (I - Z_u Z_v) / 2. Its computational-basis eigenvalue equals that cut. The mixer is the sum of X on every vertex. QAOA layer k applies the cost evolution with parameter gamma_k and then the mixer evolution with parameter beta_k, implemented as RZZ(-gamma_k w_uv) and RX(2 beta_k). Global phases that are identical for every basis state are omitted because they do not change measurement probabilities.

## 5. Classical reference method

Method: exhaustive_enumeration. Optimality guaranteed: True. Reference cut: 9.5000. Assignment, with vertex 0 in the first position: [1, 1, 0, 1, 0]. The solver re-evaluated that assignment with the same cut function as a consistency check. A separate exhaustive enumeration in the test suite checks the provisional graph without calling that function. Instance `provisional-weighted-maxcut-5` has 5 vertices and 7 edges. Official instance: False. The reference cut belongs to this loaded instance. It is not an official O1 optimum.

## 6. QAOA circuit formulation

Depth p = 1. Parameter vector, ordered gamma then beta: [0.36578315088218344, 0.37018328088858676]. The ideal statevector expectation at those parameters is 7.8151. Optimizer: grid_then_cobyla. Objective evaluations: 481. COBYLA reported success=False with message: Return from COBYLA because the objective function has been evaluated MAXFUN times. For depth 1, a deterministic grid over gamma in [0, pi] and beta in [0, pi/2] supplies the COBYLA start. The configured initial vector is recorded for reproducibility and is not a second, processor-specific start.

## 7. Processor A specification and provenance

Processor A is recorded as official=False, status `provisional`. It has 5 qubits and coupling edges [[0, 1], [1, 2], [2, 3], [3, 4]]. Basis gates: ['rz', 'sx', 'x', 'cx']. The executed edge list is the illustrative 5-qubit path from the Challenge Guide. The uploaded diagram is an unlabeled five-node tree, and it does not supply a verified numbering or edge direction. SHA-256 of the definition file: 4f4a114872d2627e4443eb687f3f27eaa4f7ff87f560dd2834045e37e5d79770.

## 8. Processor B specification and provenance

Processor B is recorded as official=False, status `provisional`. It has 7 qubits and coupling edges [[0, 1], [1, 2], [1, 3], [3, 5], [4, 5], [5, 6]]. Basis gates: ['rz', 'sx', 'x', 'cx']. Those edges are the published 7-qubit ibm_lagos CX fragment used for this preserved run. The organizer correction requires nine qubits. That coupling map has not been supplied, and the two additional qubits were not invented. Lagos calibration noise is not used. SHA-256 of the definition file: c686fc273a5a2549dc33051e6b00fd777c934cbfef7bd3e61f7539e3479ee618.

## 9. Experimental methodology

One logical QAOA circuit is built for the selected instance. Parameters are optimized once on that logical circuit with an ideal statevector. The bound circuit is then compiled separately for Processor A and Processor B with the same transpiler seed, optimization level, layout method, and routing method. Each compiled circuit is checked against that processor's basis and directed coupling map. Shots are decoded back to logical vertices with the transpiler's final layout and the actual measure instructions. The same shot count and simulator seed value are used for every execution.

## 10. Controlled experimental settings

Comparison type: shared_parameter_architecture_comparison. Shots: 4096. Transpiler optimization level: 1. Layout method: sabre. Routing method: sabre. Transpiler seed: 20261010. Simulator seed: 20261010. Execution modes: ideal, provisional_noise. Basis gates identical: True. Illustrative noise rates identical: True.

## 11. Transpilation and routing methodology

Qiskit preset transpilation maps the logical circuit onto each coupling map and the shared basis rz, sx, x, cx, with the same optimization level, layout method, routing method, and transpiler seed on both processors. An RZZ gate decomposes to two CX gates on an all-to-all device with this basis. The stored routing overhead is the transpiled CX count minus two times the logical RZZ count. Explicit SWAP instructions are counted separately. Their three-CX equivalent is stored beside that excess and is not added to it, so a SWAP that has already been decomposed into CX gates is not charged a second time. A zero explicit SWAP count means no SWAP instruction remains. It does not mean that routing added no two-qubit operations. Compiler optimization can cancel or rewrite CX gates, so the excess is not a direct count of inserted SWAP gates.

## 12. Simulation and noise assumptions

Ideal runs use the Qiskit Aer automatic simulator with no noise model. Provisional noisy runs attach the illustrative depolarizing and readout model stored in each processor file: probability 0.001 on x and sx, probability 0.01 on cx, and readout matrix [[0.99, 0.01], [0.02, 0.98]]. rz is noiseless. These rates come from the Challenge Guide's illustrative example and are applied to both processors so connectivity, rather than unequal error rates, is the controlled difference. This is a circuit-level simulator. It is not execution on an IBM quantum processor.

## 13. Problem-performance results

Mode `ideal`: Processor A expected cut 7.8300 (SE 0.0275), best observed 9.5000, expected-cut approximation ratio E[C]/C_ref 0.8242, best-cut ratio C_best/C_ref 1.0000. Processor B expected cut 7.8300 (SE 0.0275), best observed 9.5000, expected-cut approximation ratio E[C]/C_ref 0.8242, best-cut ratio C_best/C_ref 1.0000.
Agreement of the Processor A ideal shots with the statevector expectation, within four standard errors: True. The same check for Processor B: True.
Mode `provisional_noise`: Processor A expected cut 7.3936 (SE 0.0305), best observed 9.5000, expected-cut approximation ratio E[C]/C_ref 0.7783, best-cut ratio C_best/C_ref 1.0000. Processor B expected cut 7.4502 (SE 0.0302), best observed 9.5000, expected-cut approximation ratio E[C]/C_ref 0.7842, best-cut ratio C_best/C_ref 1.0000.

## 14. Circuit-resource results

Logical computational depth 8, logical two-qubit gates 7, logical operations 17. These logical figures are properties of the shared circuit.
Transpiled computational depth is 41 on Processor B and 33 on Processor A.
Transpiled two-qubit instruction count is 27 on Processor A and 21 on Processor B.
Processor A allocates 5 physical qubits, uses 5, and uses 0 ancillas outside the final logical layout. Processor B allocates 7, uses 5, and uses 0 such ancillas. Logical problem qubits: 5.

## 15. SWAP bottleneck analysis

Processor A explicit SWAP count: 0. Processor B explicit SWAP count: 0. Processor A CX excess over the two-CX-per-RZZ baseline: 13. Processor B CX excess over that baseline: 7. These stored excesses are not a direct inserted-SWAP count. With an explicit SWAP count of zero they equal the transpiled CX count minus twice the logical RZZ count. Final layouts, logical qubit to physical qubit: A [3, 0, 2, 1, 4], B [5, 1, 4, 3, 6].

## 16. Processor A versus Processor B comparison

CX-equivalent routing overhead is 13 on Processor A and 7 on Processor B. In mode `ideal`, the expected cuts agree within two combined standard errors. In mode `provisional_noise`, the expected cuts agree within two combined standard errors.

## 17. Statistical uncertainty and reproducibility

The expected-cut standard error is the square root of the plug-in shot variance divided by the number of shots. It describes multinomial sampling for this seeded run. It does not describe variation over transpiler seeds or over the unfinished optimizer search. The optimal-success standard error uses the binomial proportion formula only for that success indicator. The column approximation_ratio, and the phrase expected-cut approximation ratio, both mean E[C]/C_ref. The best-cut ratio is C_best/C_ref and is a different quantity. The approximation-ratio standard error scales the expected-cut standard error by the classical reference when that reference is positive. A zero reference leaves both ratios undefined. Package versions, seeds, file hashes, and the parameter vector are stored in the experiment manifest.

## 18. Scientific interpretation

Processor A carries the larger CX-equivalent routing overhead on this instance and this Sabre seed. Transpiled depth ranks the processors in the opposite order from the two-qubit count: depth 33 on Processor A and 41 on Processor B. The processor with fewer two-qubit instructions does not have the shorter critical path on this seed. Both ideal shot estimates sit within four standard errors of the shared statevector expectation 7.8151. Under that check, compilation preserved the logical measurement distribution, and the architectural difference appears in circuit cost. The provisional noise model uses the same per-gate rates on both processors. Processor A, which has more two-qubit instructions, also has the lower noisy expected cut. The gap stays inside two combined standard errors, so this run does not resolve a noisy quality difference.

## 19. Limitations and threats to validity

The numbers in this report are a preserved provisional run on the 5-qubit linear Processor A model and the 7-qubit Lagos-fragment Processor B model. Those configurations do not represent the final organizer-confirmed architectures. The Processor A diagram is an unlabeled five-node tree, so its exact numbered coupling map remains unverified. Processor B must use nine qubits according to the organizer's correction, and the full coupling map has not been supplied. The current noise model and Max-Cut graph are illustrative and provisional. official_benchmark_complete remains false until those official inputs are verified and used. Identical illustrative noise rates isolate connectivity only under that assumption. One Sabre seed is not a distribution over layouts. Ideal agreement tests the compiled samples and the decoder. Noisy differences mix routing overhead with the synthetic error model. Two small graphs cannot support a general ranking of architectures.

## 20. Conclusion

Processor B has the smaller transpiled two-qubit count in this run. The measured circuit costs and cut statistics describe this provisional 5-vertex instance, depth-1 QAOA parameters, and the two configured coupling maps. They do not establish a universal advantage for either connectivity. Replacing the JSON processor files and the instance file with the organizer's Challenge Kit, without changing the runner, is the step that turns this provisional study into the official benchmark.

## 21. References

1. Qiskit Fall Fest 2026 guideline, Steven Rayan, quanTA, University of Saskatchewan, supplied as QFF_IBM_Hackathon_Guideline.pdf.
2. Qiskit Fall Fest 2026 Phase 1 participant instructions, SRM University-AP.
3. Qiskit Fall Fest 2026 Phase 1 challenge guide, geometry-aware processor and architecture starter.
4. Farhi, Goldstone, and Gutmann, A Quantum Approximate Optimization Algorithm, arXiv:1411.4028.
5. IBM Quantum, The IBM Quantum heavy hex lattice, https://www.ibm.com/quantum/blog/heavy-hex-lattice.
6. Qiskit IBM Runtime, ibm_lagos coupling recorded in props_lagos.json, https://github.com/Qiskit/qiskit-ibm-runtime/blob/main/qiskit_ibm_runtime/fake_provider/backends/lagos/props_lagos.json.
7. Qiskit and Qiskit Aer documentation for transpilation, layouts, and noise models matching the versions in the manifest.

## Blocking specifications

- Processor A has 5 qubits. The uploaded diagram is an unlabeled five-node tree, so its numbered coupling map, edge directions, and basis remain unverified. The preserved run used the provisional linear path.
- Processor B must have 9 qubits under the organizer correction. The complete coupling map has not been supplied. The preserved run used the provisional 7-qubit Lagos fragment.
- Official noise parameters were not in the supplied documents. The preserved noise model is the Challenge Guide illustration.
- The official O1 weighted Max-Cut instance was not in the supplied documents. The preserved graph is provisional.
- QAOA depth, shot count, and optimizer settings are provisional defaults. No available source in this repository requires p=2 or SamplerV2.

Official benchmark complete: False.
Software run success: True.

The blocker bullets above are the text stored in this run's manifest. Current repository status, including the unlabeled Processor A tree and the missing nine-qubit Processor B map, is also stated in the abstract and in the limitations section.
