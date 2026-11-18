# AgentOS-Style Deterministic Solver Harness (PLE)

A real, tested harness for Physical-Engineering's Last Exam. Unlike the third-party notebook
that inspired this design, **no benchmark scores are simulated** and `harness.py` never returns an
unconditional success.

## What is implemented

- `solvers.py` — four deterministic closed-form solvers (AISC 360-16 LRFD steel beam, NEC 2023
  feeder ampacity + voltage drop, Darcy-Weisbach/Swamee-Jain + 25-year LCC, prismoidal earthwork)
  with explicit bounds and named governing equations.
- `test_solvers.py` — 7 known-answer tests (real hand calculations).
- `harness.py` — reads task files and instruction, selects a solver, writes `solution.json`, then
  independently **re-verifies** the written report by recomputing from the echoed parameters. A
  fabricated `gate=1` with impossible ratios is rejected by `hard_gate()` (tested).
- `test_harness.py` — 3 tests with an in-memory fake session: steel deliverable passes the gate,
  a fabricated success report is rejected, an unmapped task fails closed with `gate=0`.
- `serve.py` / `taskbridge.py` — the standard PLE serve protocol entrypoint.
- `submission.yaml` — `model_api: google-cloud/claude-opus-5-5`, no egress.

## Verification performed locally

- `python3 test_solvers.py` → 7 passed.
- `python3 test_harness.py` → 3 passed.
- `kit check <entry>` with the PLE kit → `[PASS] submission.yaml`; the only FAIL is the missing
  `MODEL_PROXY_URL`/`MODEL_PROXY_KEY`, which Google injects at evaluation time.

## Blocker (honest)

`uv run python eval/run.py` could **not** be completed in this environment:

- The dev tasks are served from a **gated** Hugging Face dataset
  (`google/physical-engineerings-last-exam`) and this machine has no `HF_TOKEN` with access.
- `kit artifacts` therefore correctly reports `no artifacts/ folder` and refuses.

Consequently this repo does **not** contain committed `artifacts/`, and no dev score, gate pass
rate, ablation, or figure derived from dev runs is claimed. Any Writeup填报 with invented numbers
would be verdict laundering — the exact failure this harness is designed to avoid.

To finish the submission: obtain an `HF_TOKEN` with dataset access, set
`MODEL_PROXY_URL`/`MODEL_PROXY_KEY` (or use a local `openai-compatible/<model>` for dev only), run
`uv run python eval/run.py <entry> --env-file local.env`, then `uv run python -m kit check <entry>`
and `uv run python -m kit artifacts <entry>` and commit the resulting `artifacts/`.
