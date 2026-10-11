# AI assistance record

This file is a reconstructed summary of AI-assisted work on the Q-TEAM PS-O1 repository. The original prompt transcripts were not copied into the repository, so the wording below is reconstructed from the files that exist and from the work recorded in this workspace. It is not a verbatim prompt log.

## Activities

Cursor Grok assisted with reading the Phase 1 guideline, participant instructions, and challenge guide, then with implementing the provisional QAOA Max-Cut runner, tests, figures, and the first report. A later technical audit inspected the saved circuits, tables, manifest, and processor files without treating passing tests as proof of an official benchmark. A documentation pass then labeled the stored results as a provisional linear Processor A run and a 7-qubit Lagos-fragment Processor B run.

A further implementation pass, also AI-assisted, added the checks and documents described in `docs/adrs.md`: separate ratio names, a routing excess that does not add explicit SWAP counts on top of CX counts, a nine-qubit schema fixture, an optional unexecuted depth-2 config, and this file. A later pass recomputed the provisional benchmark with `python scripts/run_benchmark.py` and executed `main.ipynb` in a clean kernel. Those outputs are in the tree. This paragraph records that later work. It is not a recovered prompt.

## Purpose

The assistance was used to build a reproducible provisional Phase 1 comparison and to keep official claims from running ahead of the Challenge Kit. The team remains responsible for checking the code, the tests, and any submission.

## Verification

Verification that can be repeated from this repository is `python -m pytest`, `python scripts/validate_processors.py`, and `python scripts/run_benchmark.py`. `main.ipynb` contains outputs from a clean-kernel execution that called the same experiment configuration. This reconstruction does not claim that a quantum processor was used or that the official benchmark is complete.
