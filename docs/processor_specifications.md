# Processor specifications

The Phase 1 guideline states:

- Processor A has 5 qubits, a fixed baseline graph, and a synthetic noise model.
- Processor B has 7 qubits, a heavy-hex-inspired graph, and a contemporary compilation baseline.

The guideline, the participant instructions, and the challenge guide do not list coupling edges, edge directions, or numerical noise rates for these two processors. Public searches did not produce an organizer-issued PS-O1 coupling map.

The numbers in `results/` and `report.md` are a preserved provisional run. They were produced with the 5-qubit linear Processor A model and the 7-qubit Lagos-fragment Processor B model in the JSON files below. Those configurations do not represent the final organizer-confirmed architectures. `official_benchmark_complete` remains false.

## Processor A, provisional

File: `processors/processor_A.json`.

The executable graph used for the recorded run is the path `0-1-2-3-4`. That path is the illustrative five-qubit example in Challenge Guide section 6 (`toy_5q_line`), including the basis `rz`, `sx`, `x`, `cx`. The guide says to replace illustrative values with the organizer definition. This file keeps `provenance.official` false.

The uploaded processor diagram draws Processor A as an unlabeled five-node tree: one node joined to a left node, a right node, and a node beneath it, with that lower node joined to a fifth node. No qubit index is printed on that drawing, so its exact numbered coupling map remains unverified. The linear path above is the model that was executed. It is not a confirmed tracing of the diagram.

Undirected edges: `(0, 1), (1, 2), (2, 3), (3, 4)`. Both CX directions are enabled because the file declares bidirectional connectivity. Five vertices and four edges are not the same quantity.

## Processor B, provisional

File: `processors/processor_B.json`.

The executable graph used for the recorded run uses the published CX pairs of the 7-qubit IBM Quantum Lagos device, taken from Qiskit IBM Runtime `props_lagos.json`: `0-1`, `1-2`, `1-3`, `3-5`, `4-5`, `5-6`. Lagos calibration numbers are not used. `provenance.official` is false.

The same slide captions Processor B as 7 qubits. The organizer later corrected Processor B to nine qubits, and that correction takes precedence for the qubit count. The full nine-qubit coupling map has not been supplied. Qubits beyond this 7-qubit fragment, and any edges among them, are not invented here. The Lagos fragment remains only as the preserved provisional model behind the current tables.

## Noise

Both files carry the same illustrative noise block from Challenge Guide section 10:

- Depolarizing probability `0.001` on `x` and `sx`.
- Depolarizing probability `0.01` on `cx`.
- Readout matrix `[[0.99, 0.01], [0.02, 0.98]]`.
- No error on `rz`.

The guide labels this model as illustrative. It is not an organizer-confirmed noise model. Identical rates are a study choice so a noisy A/B difference is not confounded by unequal per-gate error rates. The ideal runs do not use this model. The two execution modes are stored in separate result rows. The Max-Cut instance in `data/raw/maxcut_provisional.json` is likewise illustrative and provisional.

## Validation

The loader rejects unknown qubits, self-loops, duplicate undirected edges, probabilities outside `[0, 1]`, readout rows that do not sum to 1, and noise attached to a gate outside the basis. A file with `provenance.official` true is rejected unless `provenance.challenge_kit_file` names an issued Challenge Kit file. Replacing either JSON file is sufficient to change the benchmark. The plotting code reads the configured edges.

`processors/fixtures/nine_qubit_schema_not_official.json` is a synthetic 9-qubit path. It demonstrates that the loader and transpiler accept a nine-qubit file. Its edges and noise numbers are not Processor B and are not official.
