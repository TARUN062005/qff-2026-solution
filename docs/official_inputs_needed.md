# Official inputs still required

Searched on 11 October 2026: this repository, the 5-page Phase 1 participant instructions, the 21-page Universal Challenge Framework (`Problem_Statment_Details.pdf`), the 14-page geometry overview, `Updated_Challenge_Guide_Phase_1.pdf`, and `Processor_AB_Benchmark_Configuration_FINAL.pdf`. The starter-guide Drive folder named in the participant instructions is not in this workspace.

The undirected coupling lists are already specified and are loaded by `processors/processor_A.json` and `processors/processor_B.json`. They are not open questions. `official_benchmark_complete` stays false until the items below are issued and used.

| # | Unresolved question | Why it is still open |
| --- | --- | --- |
| 1 | Where is the designated PS-O1 six-vertex weighted graph, including its edge weights? | The framework describes a 6-vertex task and says example edge lists with integer weights 1–5 should be provided. No organizer edge list is in the searched files. `data/raw/maxcut_custom_6vertex.json` is a participant-selected custom graph used for the current run. It is not that issued instance. |
| 2 | What exact noise model and parameters must be used for Processor A and Processor B? | The updated challenge guide labels its depolarizing and readout example as illustrative and says to replace it with official assumptions. The processor approval note says the noise parameters are not verified. |
| 3 | Which directed two-qubit operations are permitted on each coupling edge? | The framework lists undirected edges. No issued directed calibration was found. Both CX directions in the JSON files are a local assumption. |
| 4 | What is the official basis-gate set and transpilation configuration? | The framework gives an example set such as X, SX, Rz, and CX. It does not freeze a basis, optimization level, layout method, or routing method. |
| 5 | Which approximation-ratio definition is scored, and what shot budget and evaluation protocol are required? | The framework asks for quantum cut weight divided by the brute-force optimum, plus the best cut and the optimal-bitstring probability. It permits QAOA depth 1 or 2, and either several random initial parameters or Qiskit's QAOA module. It does not set a shot count or say whether the scored weight is an expectation or the best sample. |
