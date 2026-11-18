# PLE harness: deterministic solvers, honest gate

This is our entry for Physical-Engineering's Last Exam. It is a small harness: four closed-form
engineering solvers, a pre-submission check that recomputes the answer independently, and a
WebSocket server that speaks the PLE protocol. No agent framework, no retrieval stack, no claims
about scores we did not measure.

## Why we built it this way

We looked at a public notebook that claimed a large jump on this benchmark. Its "evaluation"
generated scores with `np.random`, and its `harness.py` returned `gate_G = 1` no matter what task
it was given. That is not a harness; it is a placeholder wearing a result. We decided the useful
contribution here was the opposite: real calculations, a real gate, and a recorded refusal when
the task is outside what the solvers can do.

The gate is the part we care about. After a solver writes `solution.json`, `hard_gate()` reads it
back, recomputes each ratio from the parameters the report itself carries, and compares. A report
claiming `gate = 1` with a moment ratio of 1e12 is rejected. We have a test for exactly that.

## Layout

```
submission.yaml     model_api: google-cloud/claude-opus-5-5
serve.py            taskbridge.run(harness.solve)
harness.py          task routing, model proposal, solver call, hard gate, deliverables
solvers.py          AISC 360 / NEC 2023 / Darcy-Weisbach / prismoidal earthwork
taskbridge.py       PLE serve protocol (from the competition kit)
test_solvers.py     7 known-answer tests
test_harness.py     3 tests including fabricated-success rejection
gen_figures.py      builds the three Writeup figures from measured results.json
WRITEUP.md          the Kaggle Writeup (≤2000 words)
```

The model call is real but narrow. `model_propose_params()` asks the declared model for numeric
parameters from the task text, keeps only allowlisted numeric fields, and never lets the model
decide a verdict. The solver does the arithmetic; the gate decides pass or fail.

## Running the tests

```
python3 test_solvers.py
python3 test_harness.py
```

Both pass locally. The solver tests check hand-calculated ratios, NEC 125% current and derating,
Darcy-Weisbach head loss, and prismoidal earthwork. The harness tests check a steel deliverable,
rejection of a fabricated success report, and fail-closed on an unmapped task.

## Dev set and artifacts

`artifacts/` is produced by the official runner, not edited by hand:

```
uv run python eval/run.py <this-entry> --env-file local.env
uv run python -m kit check <this-entry>
uv run python -m kit artifacts <this-entry>
```

The dev tasks live in a gated Hugging Face dataset. Local dev runs use a model you can serve
yourself (we used llama3.2:3b through Ollama); `submission.yaml` still pins a sponsored
`google-cloud/<id>` model as the rules require. We document the local model in the Writeup rather
than pretending we ran a frontier model.

## What this harness does not do

It does not read the seven PNG drawing sheets, does not build IFC4 geometry, and does not do clash
detection. Most PLE tasks need all three. On the real dev set this scores near zero, and we say so.
When the instruction matches none of the four solvers, the harness writes a `gate=0` error report
instead of a fabricated success; the hard gate rejects any report whose numbers do not survive
independent recomputation.

## Repository rules we checked

- Public repo, own repository, everything in one commit.
- `submission.yaml`, `serve.py`, `LICENSE` (Apache-2.0), and unpacked `artifacts/` at the root.
- No secrets, no Git LFS, no symlinks, no harness code inside `artifacts/`.
- `model_api` set to one of the eight sponsored `google-cloud/<id>` models; `model_base_url`
  removed in the committed version.
- The harness calls the declared model, as the rules require.
