from __future__ import annotations

import math
from pathlib import Path


def _number(value: object, digits: int = 4) -> str:
    if value is None:
        return "undefined"
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return str(value)
    number = float(value)
    if not math.isfinite(number):
        return "undefined"
    return f"{number:.{digits}f}"


def _execution(processor: dict[str, object], mode: str) -> dict[str, object]:
    executions = processor["executions"]
    if not isinstance(executions, dict) or mode not in executions:
        raise KeyError(mode)
    execution = executions[mode]
    if not isinstance(execution, dict):
        raise TypeError("Execution records must be objects.")
    return execution


def _best_cut_ratio(execution: dict[str, object], classical: dict[str, object]) -> float | None:
    stored = execution.get("best_cut_approximation_ratio")
    if isinstance(stored, (int, float)) and not isinstance(stored, bool):
        return float(stored)
    best = execution.get("best_observed_cut")
    reference = classical.get("objective_value")
    if (
        isinstance(best, (int, float))
        and not isinstance(best, bool)
        and isinstance(reference, (int, float))
        and not isinstance(reference, bool)
        and float(reference) > 0
    ):
        return float(best) / float(reference)
    return None


def _resources(processor: dict[str, object]) -> dict[str, object]:
    resources = processor["resources"]
    if not isinstance(resources, dict):
        raise TypeError("Resource records must be objects.")
    return resources


def _difference_sentence(label: str, left: float, right: float, left_name: str, right_name: str) -> str:
    if math.isclose(left, right, rel_tol=0.0, abs_tol=1e-9):
        return f"{label} is the same on {left_name} and {right_name} ({_number(left, 0)})."
    larger = left_name if left > right else right_name
    smaller = right_name if left > right else left_name
    high = max(left, right)
    low = min(left, right)
    return (
        f"{label} is { _number(high, 0)} on {larger} and {_number(low, 0)} on {smaller}."
    )


def render_report(manifest: dict[str, object]) -> str:
    processors = manifest["processors"]
    if not isinstance(processors, dict):
        raise TypeError("Manifest processors must be an object.")
    processor_a = processors["A"]
    processor_b = processors["B"]
    if not isinstance(processor_a, dict) or not isinstance(processor_b, dict):
        raise TypeError("Processor results must be objects.")
    resources_a = _resources(processor_a)
    resources_b = _resources(processor_b)
    classical = manifest["classical_reference"]
    qaoa = manifest["qaoa"]
    instance = manifest["instance"]
    if not isinstance(classical, dict) or not isinstance(qaoa, dict) or not isinstance(instance, dict):
        raise TypeError("Manifest sections are incomplete.")
    modes = manifest["execution_modes"]
    if not isinstance(modes, list):
        raise TypeError("execution_modes must be a list.")
    lines = [
        "# PS-O1 Weighted Max-Cut: Processor A/B QAOA Report",
        "",
        "## 1. Abstract",
        "",
        "This Phase 1 study implements weighted Max-Cut with the Quantum Approximate Optimization Algorithm and compiles the same parameterized circuit for two processor models. Shared parameters are chosen by an ideal statevector optimization, then both processors are executed with those parameters. Circuit cost, routing overhead, and shot-based cut statistics are compared. Every number below comes from the preserved provisional run that used the 5-qubit linear Processor A model and the 7-qubit Lagos-fragment Processor B model. Those configurations do not represent the final organizer-confirmed architectures. The Processor A diagram is an unlabeled five-node tree, so its exact numbered coupling map remains unverified. Processor B must use nine qubits according to the organizer's correction, and the full coupling map has not been supplied. The noise model and the Max-Cut graph are illustrative and provisional. This report is not an official benchmark.",
        "",
        "## 2. Problem statement",
        "",
        f"Track: {manifest['track']}. Organizer code: {manifest['problem_code']}. Dashboard identifier: {manifest['dashboard_identifier']}. Team: {manifest['team']}. The selected problem is weighted Max-Cut. Phase 1 compares Processor A and Processor B. Processor C, Processor D, and the Bell-correlation study belong to the offline phase and are outside this run.",
        "",
        "## 3. Research objective",
        "",
        "How does quantum processor connectivity affect the transpiled circuit cost, routing overhead, and observed solution quality of a QAOA-based weighted Max-Cut solution under controlled experimental conditions?",
        "",
        "## 4. Weighted Max-Cut formulation",
        "",
        "For an undirected weighted graph and a bit assignment x, the cut is the sum of w_uv over edges whose endpoints receive different bits. The cost Hamiltonian used here is the sum over edges of w_uv (I - Z_u Z_v) / 2. Its computational-basis eigenvalue equals that cut. The mixer is the sum of X on every vertex. QAOA layer k applies the cost evolution with parameter gamma_k and then the mixer evolution with parameter beta_k, implemented as RZZ(-gamma_k w_uv) and RX(2 beta_k). Global phases that are identical for every basis state are omitted because they do not change measurement probabilities.",
        "",
        "## 5. Classical reference method",
        "",
        f"Method: {classical['method']}. Optimality guaranteed: {classical['optimal']}. Reference cut: {_number(classical['objective_value'])}. Assignment, with vertex 0 in the first position: {classical['assignment']}. The solver re-evaluated that assignment with the same cut function as a consistency check. A separate exhaustive enumeration in the test suite checks the provisional graph without calling that function. Instance `{instance['instance_id']}` has {instance['num_vertices']} vertices and {instance['num_edges']} edges. Official instance: {instance['official']}. The reference cut belongs to this loaded instance. It is not an official O1 optimum.",
        "",
        "## 6. QAOA circuit formulation",
        "",
        f"Depth p = {qaoa['depth']}. Parameter vector, ordered gamma then beta: {qaoa['parameters']}. The ideal statevector expectation at those parameters is {_number(qaoa['ideal_expected_cut'])}. Optimizer: {qaoa['method']}. Objective evaluations: {qaoa['evaluation_count']}. COBYLA reported success={qaoa['cobyla_success']} with message: {str(qaoa['cobyla_message']).rstrip('.')}. For depth 1, a deterministic grid over gamma in [0, pi] and beta in [0, pi/2] supplies the COBYLA start. The configured initial vector is recorded for reproducibility and is not a second, processor-specific start.",
        "",
        "## 7. Processor A specification and provenance",
        "",
        f"Processor A is recorded as official={processor_a['official']}, status `{processor_a['provenance_status']}`. It has {processor_a['num_qubits']} qubits and coupling edges {processor_a['coupling_edges']}. Basis gates: {processor_a['basis_gates']}. The executed edge list is the illustrative 5-qubit path from the Challenge Guide. The uploaded diagram is an unlabeled five-node tree, and it does not supply a verified numbering or edge direction. SHA-256 of the definition file: {processor_a['sha256']}.",
        "",
        "## 8. Processor B specification and provenance",
        "",
        f"Processor B is recorded as official={processor_b['official']}, status `{processor_b['provenance_status']}`. It has {processor_b['num_qubits']} qubits and coupling edges {processor_b['coupling_edges']}. Basis gates: {processor_b['basis_gates']}. Those edges are the published 7-qubit ibm_lagos CX fragment used for this preserved run. The organizer correction requires nine qubits. That coupling map has not been supplied, and the two additional qubits were not invented. Lagos calibration noise is not used. SHA-256 of the definition file: {processor_b['sha256']}.",
        "",
        "## 9. Experimental methodology",
        "",
        "One logical QAOA circuit is built for the selected instance. Parameters are optimized once on that logical circuit with an ideal statevector. The bound circuit is then compiled separately for Processor A and Processor B with the same transpiler seed, optimization level, layout method, and routing method. Each compiled circuit is checked against that processor's basis and directed coupling map. Shots are decoded back to logical vertices with the transpiler's final layout and the actual measure instructions. The same shot count and simulator seed value are used for every execution.",
        "",
        "## 10. Controlled experimental settings",
        "",
        f"Comparison type: {manifest['comparison_type']}. Shots: {manifest['shots']}. Transpiler optimization level: {manifest['optimization_level']}. Layout method: {manifest['layout_method']}. Routing method: {manifest['routing_method']}. Transpiler seed: {manifest['seed_transpiler']}. Simulator seed: {manifest['seed_simulator']}. Execution modes: {', '.join(str(mode) for mode in modes)}. Basis gates identical: {manifest['basis_gates_identical']}. Illustrative noise rates identical: {manifest['noise_rates_identical']}.",
        "",
        "## 11. Transpilation and routing methodology",
        "",
        "Qiskit preset transpilation maps the logical circuit onto each coupling map and the shared basis rz, sx, x, cx, with the same optimization level, layout method, routing method, and transpiler seed on both processors. An RZZ gate decomposes to two CX gates on an all-to-all device with this basis. The stored routing overhead is the transpiled CX count minus two times the logical RZZ count. Explicit SWAP instructions are counted separately. Their three-CX equivalent is stored beside that excess and is not added to it, so a SWAP that has already been decomposed into CX gates is not charged a second time. A zero explicit SWAP count means no SWAP instruction remains. It does not mean that routing added no two-qubit operations. Compiler optimization can cancel or rewrite CX gates, so the excess is not a direct count of inserted SWAP gates.",
        "",
        "## 12. Simulation and noise assumptions",
        "",
        "Ideal runs use the Qiskit Aer automatic simulator with no noise model. Provisional noisy runs attach the illustrative depolarizing and readout model stored in each processor file: probability 0.001 on x and sx, probability 0.01 on cx, and readout matrix [[0.99, 0.01], [0.02, 0.98]]. rz is noiseless. These rates come from the Challenge Guide's illustrative example and are applied to both processors so connectivity, rather than unequal error rates, is the controlled difference. This is a circuit-level simulator. It is not execution on an IBM quantum processor.",
        "",
        "## 13. Problem-performance results",
        "",
    ]
    for mode in modes:
        left = _execution(processor_a, str(mode))
        right = _execution(processor_b, str(mode))
        lines.append(
            f"Mode `{mode}`: Processor A expected cut {_number(left['expected_cut'])} (SE {_number(left['expected_cut_standard_error'])}), best observed {_number(left['best_observed_cut'])}, expected-cut approximation ratio E[C]/C_ref {_number(left['approximation_ratio'])}, best-cut ratio C_best/C_ref {_number(_best_cut_ratio(left, classical))}. Processor B expected cut {_number(right['expected_cut'])} (SE {_number(right['expected_cut_standard_error'])}), best observed {_number(right['best_observed_cut'])}, expected-cut approximation ratio E[C]/C_ref {_number(right['approximation_ratio'])}, best-cut ratio C_best/C_ref {_number(_best_cut_ratio(right, classical))}."
        )
        if mode == "ideal":
            lines.append(
                f"Agreement of the Processor A ideal shots with the statevector expectation, within four standard errors: {left['consistent_with_statevector']}. The same check for Processor B: {right['consistent_with_statevector']}."
            )
    lines.extend(
        [
            "",
            "## 14. Circuit-resource results",
            "",
            f"Logical computational depth {_number(resources_a['logical_depth'], 0)}, logical two-qubit gates {_number(resources_a['logical_two_qubit_count'], 0)}, logical operations {_number(resources_a['logical_operation_count'], 0)}. These logical figures are properties of the shared circuit.",
            _difference_sentence(
                "Transpiled computational depth",
                float(resources_a["transpiled_depth"]),
                float(resources_b["transpiled_depth"]),
                "Processor A",
                "Processor B",
            ),
            _difference_sentence(
                "Transpiled two-qubit instruction count",
                float(resources_a["transpiled_two_qubit_count"]),
                float(resources_b["transpiled_two_qubit_count"]),
                "Processor A",
                "Processor B",
            ),
            f"Processor A allocates {resources_a['physical_qubits_allocated']} physical qubits, uses {resources_a['physical_qubits_used']}, and uses {resources_a['ancillas_used']} ancillas outside the final logical layout. Processor B allocates {resources_b['physical_qubits_allocated']}, uses {resources_b['physical_qubits_used']}, and uses {resources_b['ancillas_used']} such ancillas. Logical problem qubits: {resources_a['logical_qubits']}.",
            "",
            "## 15. SWAP bottleneck analysis",
            "",
            f"Processor A explicit SWAP count: {resources_a['explicit_swap_count']}. Processor B explicit SWAP count: {resources_b['explicit_swap_count']}. Processor A CX excess over the two-CX-per-RZZ baseline: {resources_a['routing_overhead_cx']}. Processor B CX excess over that baseline: {resources_b['routing_overhead_cx']}. These stored excesses are not a direct inserted-SWAP count. With an explicit SWAP count of zero they equal the transpiled CX count minus twice the logical RZZ count. Final layouts, logical qubit to physical qubit: A {resources_a['final_index_layout']}, B {resources_b['final_index_layout']}.",
            "",
            "## 16. Processor A versus Processor B comparison",
            "",
            _comparison_paragraph(resources_a, resources_b, processor_a, processor_b, modes),
            "",
            "## 17. Statistical uncertainty and reproducibility",
            "",
            "The expected-cut standard error is the square root of the plug-in shot variance divided by the number of shots. It describes multinomial sampling for this seeded run. It does not describe variation over transpiler seeds or over the unfinished optimizer search. The optimal-success standard error uses the binomial proportion formula only for that success indicator. The column approximation_ratio, and the phrase expected-cut approximation ratio, both mean E[C]/C_ref. The best-cut ratio is C_best/C_ref and is a different quantity. The approximation-ratio standard error scales the expected-cut standard error by the classical reference when that reference is positive. A zero reference leaves both ratios undefined. Package versions, seeds, file hashes, and the parameter vector are stored in the experiment manifest.",
            "",
            "## 18. Scientific interpretation",
            "",
            _interpretation(resources_a, resources_b, processor_a, processor_b, modes, float(qaoa["ideal_expected_cut"])),
            "",
            "## 19. Limitations and threats to validity",
            "",
            "The numbers in this report are a preserved provisional run on the 5-qubit linear Processor A model and the 7-qubit Lagos-fragment Processor B model. Those configurations do not represent the final organizer-confirmed architectures. The Processor A diagram is an unlabeled five-node tree, so its exact numbered coupling map remains unverified. Processor B must use nine qubits according to the organizer's correction, and the full coupling map has not been supplied. The current noise model and Max-Cut graph are illustrative and provisional. official_benchmark_complete remains false until those official inputs are verified and used. Identical illustrative noise rates isolate connectivity only under that assumption. One Sabre seed is not a distribution over layouts. Ideal agreement tests the compiled samples and the decoder. Noisy differences mix routing overhead with the synthetic error model. Two small graphs cannot support a general ranking of architectures.",
            "",
            "## 20. Conclusion",
            "",
            _conclusion(resources_a, resources_b, processor_a, processor_b),
            "",
            "## 21. References",
            "",
            "1. Qiskit Fall Fest 2026 guideline, Steven Rayan, quanTA, University of Saskatchewan, supplied as QFF_IBM_Hackathon_Guideline.pdf.",
            "2. Qiskit Fall Fest 2026 Phase 1 participant instructions, SRM University-AP.",
            "3. Qiskit Fall Fest 2026 Phase 1 challenge guide, geometry-aware processor and architecture starter.",
            "4. Farhi, Goldstone, and Gutmann, A Quantum Approximate Optimization Algorithm, arXiv:1411.4028.",
            "5. IBM Quantum, The IBM Quantum heavy hex lattice, https://www.ibm.com/quantum/blog/heavy-hex-lattice.",
            "6. Qiskit IBM Runtime, ibm_lagos coupling recorded in props_lagos.json, https://github.com/Qiskit/qiskit-ibm-runtime/blob/main/qiskit_ibm_runtime/fake_provider/backends/lagos/props_lagos.json.",
            "7. Qiskit and Qiskit Aer documentation for transpilation, layouts, and noise models matching the versions in the manifest.",
            "",
            "## Blocking specifications",
            "",
        ]
    )
    blocking = manifest["blocking_specifications"]
    if isinstance(blocking, list):
        for item in blocking:
            lines.append(f"- {item}")
    lines.extend(
        [
            "",
            f"Official benchmark complete: {manifest['official_benchmark_complete']}.",
            f"Software run success: {manifest['success']}.",
            "",
            "The blocker bullets above are the text stored in this run's manifest. Current repository status, including the unlabeled Processor A tree and the missing nine-qubit Processor B map, is also stated in the abstract and in the limitations section.",
            "",
        ]
    )
    return "\n".join(lines)


def _comparison_paragraph(
    resources_a: dict[str, object],
    resources_b: dict[str, object],
    processor_a: dict[str, object],
    processor_b: dict[str, object],
    modes: list[object],
) -> str:
    sentences = [
        _difference_sentence(
            "CX-equivalent routing overhead",
            float(resources_a["routing_overhead_cx"]),
            float(resources_b["routing_overhead_cx"]),
            "Processor A",
            "Processor B",
        )
    ]
    for mode in modes:
        left = _execution(processor_a, str(mode))
        right = _execution(processor_b, str(mode))
        gap = abs(float(left["expected_cut"]) - float(right["expected_cut"]))
        combined = math.sqrt(
            float(left["expected_cut_standard_error"]) ** 2
            + float(right["expected_cut_standard_error"]) ** 2
        )
        if combined == 0 or gap <= 2 * combined:
            sentences.append(
                f"In mode `{mode}`, the expected cuts agree within two combined standard errors."
            )
        else:
            better = "A" if float(left["expected_cut"]) > float(right["expected_cut"]) else "B"
            sentences.append(
                f"In mode `{mode}`, Processor {better} has the higher expected cut, and the gap exceeds two combined standard errors."
            )
    return " ".join(sentences)


def _interpretation(
    resources_a: dict[str, object],
    resources_b: dict[str, object],
    processor_a: dict[str, object],
    processor_b: dict[str, object],
    modes: list[object],
    ideal_expectation: float,
) -> str:
    overhead_gap = float(resources_a["routing_overhead_cx"]) - float(resources_b["routing_overhead_cx"])
    if overhead_gap > 0:
        routing_sentence = "Processor A carries the larger CX-equivalent routing overhead on this instance and this Sabre seed."
    elif overhead_gap < 0:
        routing_sentence = "Processor B carries the larger CX-equivalent routing overhead on this instance and this Sabre seed."
    else:
        routing_sentence = "The two processors have the same CX-equivalent routing overhead on this instance and this Sabre seed."
    depth_a = float(resources_a["transpiled_depth"])
    depth_b = float(resources_b["transpiled_depth"])
    two_a = float(resources_a["transpiled_two_qubit_count"])
    two_b = float(resources_b["transpiled_two_qubit_count"])
    if two_a == two_b and depth_a != depth_b:
        depth_sentence = (
            f"The transpiled two-qubit counts match, while depth is {depth_a:.0f} on Processor A and {depth_b:.0f} on Processor B."
        )
    elif (depth_a - depth_b) * (two_a - two_b) < 0:
        depth_sentence = (
            f"Transpiled depth ranks the processors in the opposite order from the two-qubit count: "
            f"depth {depth_a:.0f} on Processor A and {depth_b:.0f} on Processor B. "
            f"The processor with fewer two-qubit instructions does not have the shorter critical path on this seed."
        )
    elif depth_a == depth_b:
        depth_sentence = "Transpiled depth matches on the two processors."
    else:
        depth_sentence = (
            f"Transpiled depth is {depth_a:.0f} on Processor A and {depth_b:.0f} on Processor B, "
            f"in the same order as the two-qubit counts."
        )
    quality_bits = [depth_sentence]
    if "ideal" in modes:
        left = _execution(processor_a, "ideal")
        right = _execution(processor_b, "ideal")
        if left["consistent_with_statevector"] and right["consistent_with_statevector"]:
            quality_bits.append(
                f"Both ideal shot estimates sit within four standard errors of the shared statevector expectation {_number(ideal_expectation)}. Under that check, compilation preserved the logical measurement distribution, and the architectural difference appears in circuit cost."
            )
        else:
            quality_bits.append(
                "At least one ideal shot estimate sits outside four standard errors of the statevector expectation. That discrepancy has to be resolved before an ideal quality difference is attributed to connectivity."
            )
    if "provisional_noise" in modes:
        noisy_a = _execution(processor_a, "provisional_noise")
        noisy_b = _execution(processor_b, "provisional_noise")
        gap = abs(float(noisy_a["expected_cut"]) - float(noisy_b["expected_cut"]))
        combined = math.sqrt(
            float(noisy_a["expected_cut_standard_error"]) ** 2
            + float(noisy_b["expected_cut_standard_error"]) ** 2
        )
        direction = (
            "Processor A, which has more two-qubit instructions, also has the lower noisy expected cut."
            if float(noisy_a["expected_cut"]) < float(noisy_b["expected_cut"])
            else "The noisy expected cut is lower on Processor B."
        )
        if combined == 0 or gap <= 2 * combined:
            noise_sentence = (
                "The provisional noise model uses the same per-gate rates on both processors. "
                f"{direction} The gap stays inside two combined standard errors, so this run does not resolve a noisy quality difference."
            )
        else:
            noise_sentence = (
                "The provisional noise model uses the same per-gate rates on both processors. "
                f"{direction} The gap exceeds two combined standard errors."
            )
        quality_bits.append(noise_sentence)
    return " ".join([routing_sentence, *quality_bits])


def _conclusion(
    resources_a: dict[str, object],
    resources_b: dict[str, object],
    processor_a: dict[str, object],
    processor_b: dict[str, object],
) -> str:
    cheaper = "A" if float(resources_a["transpiled_two_qubit_count"]) < float(resources_b["transpiled_two_qubit_count"]) else "B"
    if float(resources_a["transpiled_two_qubit_count"]) == float(resources_b["transpiled_two_qubit_count"]):
        cost_sentence = "The transpiled two-qubit counts match."
    else:
        cost_sentence = f"Processor {cheaper} has the smaller transpiled two-qubit count in this run."
    return (
        f"{cost_sentence} The measured circuit costs and cut statistics describe this provisional 5-vertex instance, depth-1 QAOA parameters, and the two configured coupling maps. They do not establish a universal advantage for either connectivity. Replacing the JSON processor files and the instance file with the organizer's Challenge Kit, without changing the runner, is the step that turns this provisional study into the official benchmark."
    )


def write_report(manifest: dict[str, object], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_report(manifest), encoding="utf-8")
