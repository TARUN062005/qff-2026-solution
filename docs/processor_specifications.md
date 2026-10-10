# Processor specifications

The Phase 1 guideline states:

- Processor A has 5 qubits, a fixed baseline graph, and a synthetic noise model.
- Processor B has 7 qubits, a heavy-hex-inspired graph, and a contemporary compilation baseline.

The guideline, the participant instructions, and the challenge guide do not list coupling edges, edge directions, or numerical noise rates for these two processors. The qualitative slide was not converted into an edge list. Public searches did not produce an organizer-issued PS-O1 coupling map.

## Processor A, provisional

File: `processors/processor_A.json`.

The executable graph is the path `0-1-2-3-4`. That path is the illustrative five-qubit example in Challenge Guide section 6 (`toy_5q_line`), including the basis `rz`, `sx`, `x`, `cx`. The guide says to replace illustrative values with the organizer definition. This file keeps `provenance.official` false.

Undirected edges: `(0, 1), (1, 2), (2, 3), (3, 4)`. Both CX directions are enabled because the file declares bidirectional connectivity. Five vertices and four edges are not the same quantity.

## Processor B, provisional

File: `processors/processor_B.json`.

The executable graph uses the published CX pairs of the 7-qubit IBM Quantum Lagos device, taken from Qiskit IBM Runtime `props_lagos.json`: `0-1`, `1-2`, `1-3`, `3-5`, `4-5`, `5-6`. That fragment is the heavy-hex coupling of a contemporary 7-qubit IBM processor. It is a tree, not a 6-cycle, and it is not a tracing of the challenge slide. Lagos calibration numbers are not used. `provenance.official` is false.

## Noise

Both files carry the same illustrative noise block from Challenge Guide section 10:

- Depolarizing probability `0.001` on `x` and `sx`.
- Depolarizing probability `0.01` on `cx`.
- Readout matrix `[[0.99, 0.01], [0.02, 0.98]]`.
- No error on `rz`.

The guide labels this model as illustrative. Identical rates are a study choice so a noisy A/B difference is not confounded by unequal per-gate error rates. The ideal runs do not use this model. The two execution modes are stored in separate result rows.

## Validation

The loader rejects unknown qubits, self-loops, duplicate undirected edges, probabilities outside `[0, 1]`, readout rows that do not sum to 1, and noise attached to a gate outside the basis. Replacing either JSON file is sufficient to change the benchmark. The plotting code reads the configured edges.
