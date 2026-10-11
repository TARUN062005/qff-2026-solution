# PS-O1 submission checklist

This checklist uses the 5-page Phase 1 participant instructions and the 21-page framework, read from local PDF copies that are not stored in the repository. The starter-guide Drive folder named in the instructions is not in the workspace. `PASS` means the provisional repository meets the item. It does not mean the official benchmark is complete.

`PASS` means the provisional repository meets the item. It does not mean the official benchmark is complete.

| Requirement | Evidence or file path | Status | Exact remaining action |
| --- | --- | --- | --- |
| One Phase 1 problem, PS-O1 weighted Max-Cut, evaluated once on Processor A and Processor B | `config/experiment.json`, `README.md`, `docs/methodology.md` | PASS | None for the provisional study. |
| Processor C, Processor D, and the Bell study stay out of Phase 1 | `README.md`, `report.md` | NOT APPLICABLE | Do not add them for Phase 1. |
| Weighted-cut objective is the sum of weights on disagreeing endpoints | `src/max_cut.py`, `src/qaoa.py`, `tests/test_max_cut.py`, `tests/test_qaoa.py` | PASS | None. |
| Custom graph optimum is not presented as the official O1 optimum | `data/raw/maxcut_custom_6vertex.json` (`official` false), `report.md` section 5 | PASS | Replace the file only with the issued instance. |
| Same logical circuit and shared parameters on both processors | `config/experiment.json`. The six-vertex circuit was executed only on Processor B. Processor A was not executed because it has 5 qubits. | PARTIAL | Do not describe this run as a complete A/B measurement comparison. The five-vertex supplementary run is separate. |
| Transpilation respects the configured coupling map and basis | `src/transpilation.py`, `results/circuits/processor_A_transpiled.qasm`, `results/circuits/processor_B_transpiled.qasm` | PASS | Recompile after official maps replace the JSON files. |
| Explicit SWAP count is separate from CX excess, with no double count | `src/metrics.py`, `results/tables/circuit_resources.csv` | PASS | None for this definition. |
| A/B comparison reports cost and solution quality without a universal ranking | `report.md` sections 16 and 20, `results/figures/` | PASS | None. |
| `E[C]/C_ref` and `C_best/C_ref` stay distinct | `results/tables/AB_comparison.csv`, `README.md`, `report.md` | PASS | None. |
| Noise and shot uncertainty are labeled as illustrative and single-seed | `processors/processor_A.json`, `processors/processor_B.json`, `report.md` section 17 | PASS | Replace noise only with the issued model. |
| Reproducible commands from the repository root, with pinned packages and recorded seeds | `README.md`, `docs/reproducibility.md`, `requirements.txt`, `results/manifests/experiment_manifest.json` | PASS | Re-run after official inputs change. |
| Notebook uses the same configuration as `scripts/run_benchmark.py` and has stored outputs | `main.ipynb`, `config/experiment.json` | PASS | Re-execute after the next benchmark change. |
| Report, tables, circuits, and figures agree on the provisional run | `report.md`, `results/tables/AB_comparison.csv`, `results/manifests/experiment_manifest.json`, `results/figures/` | PASS | Refresh together if inputs change. |
| AI-use disclosure | `README.md`, `docs/ai_prompt.md` | PASS | The 5-page instructions require disclosure when the official AI policy requires it. The policy text itself is not in that PDF. The repository disclosure is present. |
| Single-qubit gate counts | `results/tables/circuit_resources.csv` | PASS | Reported beside CX, depth, and SWAP. |
| Repository remote and tracked deliverables | `origin` `https://github.com/TARUN062005/qff-2026-solution.git`; tracked `results/`, `report.md`, `main.ipynb` | PASS | Commit and push later documentation updates only when requested. |
| Framework Processor A coupling list | `processors/processor_A.json` uses `(0,1), (1,2), (1,3), (3,4)`. `provenance.official` is false because basis and direction are local assumptions. | PARTIAL | Replace basis and direction only if an issued file differs. |
| Framework Processor B coupling list | `processors/processor_B.json` uses the 12-edge 9-qubit list. It is not the Lagos fragment and not the schema fixture. | PARTIAL | Keep the 7-qubit overview caption recorded as a discrepancy. |
| Official noise model | Not in the repository. Both JSON files use the illustrative Challenge Guide rates | BLOCKED | Obtain the issued noise assumptions. |
| Official PS-O1 graph and weights | Not in the repository. The active file is a participant-selected custom graph | BLOCKED | Obtain the issued instance. Do not treat the custom optimum as official. |
| `official_benchmark_complete` | `results/manifests/experiment_manifest.json` is false | BLOCKED | Set it true only after the issued instance and both processor files are verified and used. |
| QAOA depth 2 | `config/experiment_p2_provisional.json` is optional and was not executed | NOT APPLICABLE | Do not treat depth 2 as mandatory. No file in this repository requires it. |
| SamplerV2 | No implementation and no requirement in the repository | NOT APPLICABLE | Do not add it unless an issued instruction requires it. |
| Nine-qubit schema fixture as Processor B | `processors/fixtures/nine_qubit_schema_not_official.json` | NOT APPLICABLE | Keep it as a loader fixture. The experiment config does not reference it. |
