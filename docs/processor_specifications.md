# Processor specifications

The 21-page Universal Challenge Framework states:

- Processor A has 5 qubits and undirected edges `(0, 1), (1, 2), (1, 3), (3, 4)`.
- Processor B has 9 qubits and undirected edges `(0, 1), (1, 2), (1, 6), (2, 3), (2, 6), (2, 5), (3, 4), (4, 5), (5, 6), (6, 7), (6, 8), (8, 0)`.
- Organizer-provided benchmark definitions are the source of truth for the final noise model and simulator settings.

`Processor_AB_Benchmark_Configuration_FINAL.pdf` repeats those undirected edges, says it is for organizer approval, and states that the exact noise parameters are not verified. The 14-page overview diagram captions Processor B as 7 qubits. This repository uses the framework's explicit 9-qubit edge list.

`official_benchmark_complete` stays false because the noise model and the Max-Cut instance are not the issued benchmark definitions.

## Processor A

File: `processors/processor_A.json`.

Executable undirected edges: `(0, 1), (1, 2), (1, 3), (3, 4)`. This is not the historical path `0-1-2-3-4`. Both CX directions are enabled because the framework lists undirected edges and no directed calibration was issued. Basis gates `rz`, `sx`, `x`, `cx` are a local assumption matching the framework's example gate set. `provenance.official` is false.

## Processor B

File: `processors/processor_B.json`.

Executable undirected edges are the 12 framework connections. `(8, 0)` is stored as `(0, 8)`. This is not the historical 7-qubit Lagos fragment. `processors/fixtures/nine_qubit_schema_not_official.json` is a synthetic path used only by tests. It is not Processor B.

## Noise

Both executable files still carry the same illustrative noise block:

- Depolarizing probability `0.001` on `x` and `sx`.
- Depolarizing probability `0.01` on `cx`.
- Readout matrix `[[0.99, 0.01], [0.02, 0.98]]`.
- No error on `rz`.

Those numbers are a local assumption. The ideal runs do not use them. The active Max-Cut instance is `data/raw/maxcut_custom_6vertex.json`, a participant-selected custom graph with `official` false. `data/raw/maxcut_provisional.json` is the archived five-vertex graph. `data/raw/maxcut_example_6vertex.json` is an earlier participant example and is not the active benchmark.

## Historical run

`results/historical/line_lagos_5vertex/` keeps the earlier benchmark on the linear Processor A file and the 7-qubit Lagos Processor B file. Those files are copied under `processors/historical/`.

## Validation

The loader rejects unknown qubits, self-loops, duplicate undirected edges, probabilities outside `[0, 1]`, readout rows that do not sum to 1, and noise attached to a gate outside the basis. A file with `provenance.official` true is rejected unless `provenance.challenge_kit_file` names an issued file.
