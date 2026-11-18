# AgentOS-Style Deterministic Solver Harness on PLE

**Project:** https://github.com/FiscalMindset/ple-harness-agentos
**Commit:** _TO_BE_FILLED_FROM_REAL_RUN_ (git rev-parse HEAD of the commit carrying artifacts/)

## Headline finding

A deterministic, closed-form engineering solver behind an independent pre-submission gate is
**not sufficient** for Physical-Engineering's Last Exam: on the 29 public dev tasks our harness
scored 0.0219 (mean reward 0-1). The binding constraint is not arithmetic — it is reading
seven-sheet drawing sets, choosing governing code clauses, and producing clash-free IFC4 geometry
that the graders actually read. We report the failure honestly and show which tasks the gate
refused versus which the grader scored.

## 1. Insight & failure analysis (25 pts)

The external notebook that motivated this design reported 50.6% → 74.8% gains. Its "evaluation"
was a seeded `np.random` generator with baseline scores hardcoded as inputs, and its `harness.py`
returned `gate_G=1` unconditionally. We did not reproduce those numbers.

Our harness fails closed. `hard_gate()` recomputes every numeric ratio from the echoed parameters
and rejects a report whose claimed `gate=1` disagrees with the recomputation. Three local tests
prove: a steel deliverable passes, a fabricated `gate=1` with a 1e12 ratio is rejected, and an
unmapped task (a poem about bridges) writes `gate=0`. Against the real dev set, the measured
breakdown in Figure 3 is: 15 tasks where a solver ran and the grader rejected its deliverable,
one rubric task whose local judge failed after three attempts, one whose grader dependencies
would not install, and 12 heavy rubric tasks we could not run locally because the Docker images
exhausted the host disk. Those 12 count 0, exactly as the leaderboard treats unmeasured tasks.
One task (`landscape-sheet-revision`) did score 0.636 from the local judge — a real, measured
result, not a simulation.

Controlled comparison available: the four deterministic solvers are known-answer tested
(`test_solvers.py`, 7 tests). They are real AISC 360 / NEC 2023 / Darcy-Weisbach / prismoidal
calculations, not stubs. The ablation we can honestly report is structural — gate on vs off is
measurable locally — not a dev-score ablation, because we did not fabricate dev scores.

## 2. Engineering reasoning (25 pts)

On a structural task the harness: reads the instruction and `params.json`, selects the AISC 360
LRFD solver, computes `Mu/(phi*Fy*Zx)`, `Vu/(phi*0.6*Fy*Aw)` and live-load `L/360` deflection,
writes `solution.json`, then the gate independently recomputes all three ratios and checks the
claimed gate. Where it holds up: arithmetic and unit-consistent ratio computation. Where it
takes shortcuts: it assumes square-root geometry from parameters rather than reading the actual
CAD/IFC model; a licensed engineer would reconcile the drawing callouts first. That gap is the
main source of zero scores on drawing-heavy tasks.

## 3. Cross-model generalizability (15 pts)

Dev artifacts were generated locally with `llama3.2:3b` (Ollama) as documented in
`docs/local-models.md` of the competition kit; the submitted `submission.yaml` pins
`google-cloud/claude-opus-5-5` per Stage 2 rules. The harness's deterministic solvers are
model-independent, so the same code runs on any sponsored model. The local runner used the same
`llama3.2:3b` endpoint as the judge for rubric and checks-judge tasks (`JUDGE_MODEL` wasn't
overridden). We did not run multiple frontier models; the cross-model table is therefore
explicitly **not claimed**. This is an honest scope limitation, not a missing experiment we
pretend to have run.

## 4. Efficiency & scaling (20 pts)

The deterministic solvers are constant-time; the gate recomputes once per task. Figure 2 plots
measured score against measured runtime — the local model is self-hosted, so there is no USD cost
to plot and we do not invent one. There is no accuracy plateau to report because the harness does
not scale compute into competence — more solver calls do not fix an unmapped multimodal task. This
is a real negative result.

## 5. Clarity & visuals (15 pts)

The Media Gallery cover and all three figures come from `gen_figures.py`: Figure 1 is the actual
harness architecture, Figure 2 is score vs measured runtime, and Figure 3 is the failure breakdown
on the 29 dev tasks. No figure uses invented data.

## Limitations

No novelty, invention or AGI claim. The harness does not read PNG/CAD drawings, does not build
IFC4 models, and scores near zero on the real dev set. The fail-closed deliverable is a genuine
refusal, not a passing answer. The third-party notebook's simulated numbers were not copied.
