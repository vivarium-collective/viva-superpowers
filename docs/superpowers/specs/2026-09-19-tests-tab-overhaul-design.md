# Tests tab overhaul — measure → grade → render, framework-wide

**Date:** 2026-09-19
**Status:** design (approved to write; awaiting spec review)
**Repos touched:** `viva-superpowers` (seam), `vivarium-workbench` (endpoint + frontend), `viva-mGen` (proof-case evaluators)

## Problem

Every study's **Tests** tab renders as "pending / uninformative / inconclusive"
and the **Run tests** button does nothing useful. Seen across all 8 viva-mGen
studies (screenshot: `fig7-kinetic-parameters`, "0/7 gates passed", every test
`pending`).

Three distinct defects, all real, all framework-level:

1. **Declared tests are never measured.** `measure.kind: derived_scalar` is a
   *native* kind in `viva_superpowers/study_evaluator.py`
   (`RUN_DATA_KINDS`, L153–165), so `evaluate_test` (L562–650) **bypasses the
   workspace evaluator registry** (the `if kind not in RUN_DATA_KINDS` gate at
   L588) and tries to read the test's `field` as a **raw emitted observable** in
   the run store via `_resolve_series` (L609/L621–624). viva-mGen's tests declare
   `field: growth_is_monotonic_in_kcat`, `doubling_time_h`, `final_mass_ratio`,
   etc. — **derived quantities that are never emitted**. So `_resolve_series`
   raises `ObservableNotFound` → the test falls into the `_agent(...)` bucket
   (L623–624) → no `result`, no `measured_value`. There is **no seam** for a
   workspace to supply that computation. This is the root cause.

2. **"Run tests" is wired to the wrong mechanism.** The button POSTs
   `/api/study-tests-run`, which shells out to **pytest** against
   `studies/<slug>/tests/` (`vivarium_workbench/lib/study_tests.py`
   `run_study_tests`, L51–135). For a behavior-test study with no `tests/` dir it
   routes to `_run_spine_tests` → `compute_outcomes`, which writes only the
   **parallel `computed_outcomes` block**, *not* the authoritative
   `runs[].outcomes` the report card reads. It also **never re-simulates**. The
   map found **no on-demand endpoint** that grades a study's behavior tests into
   the authoritative outcomes without a full re-run.

3. **The tab reads empty surfaces.** `static/study-detail.js`
   (`loadTestsTab`, L3730+; `_renderTestsGateSummary`, L3706) reads
   `spec.outcome_rollup` / `spec.runs[].outcomes` / `spec.gate` /
   `spec.test_diff` — all correctly populated by the post-run flush's
   `auto_evaluate.evaluate_on_run_completion` (flush stage 7,
   `lib/study_runs.py` L291–295) — but for viva-mGen those surfaces are empty
   because defect (1) means grading produced nothing.

## Goal

Framework-wide: the Tests tab **describes** each test and **grades** it against
its band with a real measured value, verdict, and margin — and **Run tests**
drives that (grade the existing run; re-simulate only if there is no usable
run). Prove it on all 8 viva-mGen studies.

## Non-goals (YAGNI)

- **No verdict-schema unification.** Three verdict shapes coexist
  (`report_card_verdict/v1`+`v2`, `behavior_test_card/v1`, `conclusion`); the
  memories show the grand unification was deliberately deferred. This overhaul
  consumes the **existing** surfaces (`runs[].outcomes`+`axis`,
  `behavior_test_card/v1`, `test_diff`, `gate`) and introduces **no new
  schema**.
- **No stale-run provenance engine.** Re-sim triggers only when there is *no*
  usable completed run (approved decision). Timestamp/spec-drift detection is a
  later, additive follow-up.
- **No pytest-path removal.** `studies/<slug>/tests/` pytest keeps working where
  present; it is simply no longer what the button does for behavior-test
  studies.

## Approach (approved)

**A + C**: a workspace-pluggable **derived-scalar computer registry** consulted
by the native path (A), plus a generic **safe-formula** path for simple
arithmetic scalars (C). Studies keep `kind: derived_scalar` unchanged; the
computed scalar flows through the existing `pass_if` → `_apply_op` →
`_grade_axis_from_outcome` → `/v2` axis chain untouched.

---

## Design

### 1. Derived-scalar seam (viva-superpowers) — pieces A + C

**New workspace hook** (additive; mirrors `load_workspace_evaluators`,
L250–281):

```python
# viva_<pkg>/evaluators.py  (optional, per workspace)
def register_derived_scalars(reg: dict[str, Callable]) -> None:
    reg["growth_is_monotonic_in_kcat"] = _growth_is_monotonic  # field -> fn
```

- **Computer signature:** `fn(reader: RunReader, test: dict, ws_root) -> float`
  — returns a plain scalar (a boolean check returns `1.0`/`0.0`). It may read
  the *whole* run (all sweep variants), which raw observable resolution cannot.
- **Loader:** `load_workspace_derived_scalars(ws_root) -> dict[str, Callable]`,
  a sibling of `load_workspace_evaluators` — same package-candidate logic
  (`_workspace_evaluator_packages`, L207–247), same per-`ws_root` cache, same
  "never raise; skip a broken hook" contract. Cache invalidated by the existing
  `clear_workspace_evaluator_cache`.

**Native-path change** — `evaluate_test`, exactly at step 7 (L620–626). Replace
the bare `_resolve_series` with a resolution ladder:

```
path = measure.path or measure.field or measure.formula   (L609, unchanged)

if measure.formula is present:
    scalar = _eval_safe_formula(formula, reader, window_spec)   # piece C
    series = _scalar_series(scalar)
else:
    try:
        series = _resolve_series(path, reader)                  # raw observable (today)
    except ObservableNotFound:
        fn = load_workspace_derived_scalars(ws_root).get(path)  # piece A
        if fn is None:
            return _agent(f"derived scalar {path!r} not emitted and no "
                          f"workspace computer registered")
        scalar = fn(reader, test, ws_root)                      # may raise -> _agent
        series = _scalar_series(scalar)
```

`_scalar_series(x)` builds the trivial 1-row frame `_resolve_series` returns, so
steps 8–10 (window, empty-guard, `_apply_op`, axis attach) run **unchanged**.
For mGen (`pass_if.op: range, low: 1.0, high: 1.0` over a `1.0`/`0.0` boolean)
this grades correctly with zero new grading code.

**Piece C — reuse the existing AST expression evaluator (already shipped).**
Verified against code: `_resolve_series` (L738) already routes an arithmetic
`path` to `_eval_expression` (L835), which is **AST-based and safe** — it
substitutes tokens to `_v0…`, `ast.parse(mode="eval")`, then `_eval_ast_node`
(L887) with a **closed whitelist** (`Constant`, `Name`, `BinOp +−*/`,
`UnaryOp +−`); no `eval`. And the native path *already* passes
`measure.formula` into `_resolve_series` (L609). So a `formula:` over **emitted
observables** (e.g. `cell_mass / cell_mass_initial`) grades **today** with zero
new code — it evaluates per-tick, and the existing window + `_apply_op` reduce
it. Piece C therefore collapses to **confirm-and-test** that a study can declare
`formula:` and get a graded result, plus optionally widening the operator
whitelist to `Pow`/`Mod` if a study needs it. The genuinely-new code is piece A
only. A formula that references a *derived* (non-emitted) scalar is out of
scope for C — that is what piece A's registry is for.

**Precedence:** `formula` (if present) wins; else raw observable; else the
registry. A `field` that *is* emitted keeps today's behavior exactly (no
regression). Nothing consults the registry unless resolution otherwise fails.

**Tests (pytest, `viva-superpowers/tests/`):**
- registry loader finds `register_derived_scalars`, caches, tolerates a broken
  module;
- native fallback: unresolved `field` + a registered computer → graded outcome
  with `measured_value`, `result`, `axis`; unresolved + none → `_agent`;
- emitted `field` still resolves without touching the registry (regression);
- `_eval_safe_formula`: arithmetic correct; `__import__`/attribute/call nodes
  rejected; div-by-zero → `_agent`.

### 2. Proof case (viva-mGen) — `viva_mgen/evaluators.py`

New module registering one derived-scalar computer per distinct `field` across
the 8 studies (fig1–fig7 + parca-parameter-fitting). Each reads the study's run
store through `reader` and returns a scalar:

- `growth_is_monotonic_in_kcat` — 1.0 iff growth is non-decreasing across the
  ordered kcat-proxy sweep variants.
- `growth_saturates_at_wt`, `growth_at_max_kcat_near_wt` — high-kcat growth ≈ 1.
- `growth_is_sigmoidal` — low-plateau → rise → high-plateau shape check.
- `growth_dynamic_range` — max−min growth across the sweep.
- `doubling_time_h`, `final_mass_ratio`, `protein_fraction`, … — the fig1–fig6
  scalars (enumerated during implementation from each `study.yaml`).

Acceptance: after `viva-compute-outcomes` (or Run tests) each fig study shows
non-null `measured_value` and a real PASS/FAIL + margin — no `_agent` buckets
for declared primary tests. (Exact per-study reductions are an implementation
detail; the seam contract above is the fixed part.)

### 3. On-demand grade endpoint (vivarium-workbench)

**New:** `POST /api/study-grade` — the missing "grade the existing run, no
re-sim" op.

- **Body:** `{ "study": "<slug>" }`.
- **Lib:** `lib/study_grade.py :: grade_study(ws_root, slug)`.
  1. Resolve the latest **completed** run + its store (reuse
     `auto_evaluate._evaluator_test_runner` store resolution).
  2. If a usable run exists → `auto_evaluate.evaluate_on_run_completion(...,
     overwrite_authored=False)` (writes authoritative `runs[].outcomes`, never
     clobbers human-authored), then `behavior_test_card.write_behavior_test_card`
     and refresh `test_diff.json`. Return **200**
     `{ graded: true, outcome_rollup, gate, run_id }`.
  3. If **no** usable run → return **200** `{ graded: false, reason: "no_run" }`
     (not an error — it's the signal for the frontend to run the baseline).
- **Route:** `api/app.py`, `@app.post("/api/study-grade")`, CSRF-guarded,
  delegates to the lib, `JSONResponse`. Add a pydantic body model in
  `lib/models.py` (sibling of `StudyTestsRunRequest`).
- **Tests:** fixture study with a completed run → `graded: true` + populated
  rollup; fixture study with no run → `graded: false, reason: "no_run"`; verify
  human-authored outcomes survive.

**Why not re-run inside the endpoint:** re-simulation is long and the existing
`/api/study-run-baseline` path *already* auto-evaluates in its flush tail (stage
7). Duplicating that in a blocking endpoint is wrong. The frontend chains to the
existing baseline flow instead (§4).

### 4. Rewire "Run tests" (frontend)

`runStudyTests()` (`study-detail.js` L4001–4024) becomes a two-state machine
against the new endpoint (replaces the `/api/study-tests-run` pytest call):

1. `POST /api/study-grade {study}`.
2. `graded: true` → reload the study spec (`GET /api/study/{slug}`) and
   re-render the tab. Done.
3. `graded: false, reason: "no_run"` → chain to the **existing** baseline-run
   UX (`_dispatchCurrentSpecBaseline`, L1970–1976) and poll to completion; that
   path's flush auto-evaluates, so on completion just reload the tab. (One
   idempotent `study-grade` after reload is harmless and keeps cards/diff
   fresh.)

Button label reflects state: `Run tests` → `Grading…` / `Simulating…` →
`Run tests`. Snapshot/read-only data source: hide the button (no live backend),
matching the existing Launch-button degradation pattern.

### 5. Redesign the Tests tab (frontend)

Reorganize the scattered pieces (`_renderComputedOutcomeRow`,
`_fillReportCardModules`, the gate badge, the "N/M gates passed" strip) into one
coherent **report card per test**, grouped **primary first**. New render
`_renderTestReportCard(test, outcome, diff)` consuming the now-populated
surfaces — **no new data contract**:

Per test, top-to-bottom:
- **Header:** name · classification badge (primary/secondary) · verdict chip
  (`within_tol`/`drift`/`mismatch` from `outcome.axis.verdict`) · PASS/FAIL.
- **What it checks:** `test.description`.
- **Band + measured:** `pass_if` rendered human-readably
  ("expected within [0.7, 1.0]") next to `outcome.measured_value`.
- **Margin bar:** `outcome.axis.meter` (0..1, pass boundary at 0.5) as a visual
  bar (reuse the existing margin-bar styling from vwb #829).
- **Evidence:** `pass_if.provenance.note` + any `cites` / `calibration_anchor`
  — the citation basis (currently not surfaced together with the result).
- **Since last run:** change badge (`fixed`/`broke`/`improved`/`regressed`/
  `new`) + `margin_delta` from `spec.test_diff.per[]`.
- **Footer:** link to the run that produced the value; a collapsed **Assertion**
  detail.

Tab header keeps: `N/M gates passed` + the severity-gate badge (`spec.gate`),
and ties to Decision by showing the study's `pipeline_gate.proceed_condition`
and whether the gate passes. Empty state only when a study genuinely declares no
tests.

Frontend has no unit harness (vanilla JS); correctness rides on the §3 endpoint
tests + the §1/§2 grading tests + a manual pass over all 8 mGen studies in the
running workbench.

---

## Data flow (after)

```
study.yaml behavior_tests[]  ──┐
                               ▼
run store (zarr)  ──►  evaluate_test  ──►  derived-scalar registry / formula (NEW)
                               │                     │
                               ▼                     ▼
                    _apply_op + /v2 axis  ◄──── scalar
                               │
                               ▼
         auto_evaluate.evaluate_on_run_completion  ──►  runs[].outcomes(+axis)
                               │                         behavior-tests.verdict.json
                               ▼                         test_diff.json / gate
                     GET /api/study/{slug} spec surfaces
                               │
                               ▼
              Tests tab report cards (redesigned)
                       ▲
         POST /api/study-grade  (Run tests: grade now; re-sim only if no run)
```

## Implementation slices (for the plan)

1. **viva-superpowers** — derived-scalar registry loader + native-path fallback
   (piece A); confirm/test the existing `formula:` path (piece C — reuse
   `_eval_expression`); pytest. *(Foundation; unblocks the rest.)*
2. **viva-mGen** — `viva_mgen/evaluators.py` computers for the 8 studies;
   verify grading populates non-null outcomes.
3. **vivarium-workbench** — `POST /api/study-grade` + `lib/study_grade.py` +
   model; pytest.
4. **vivarium-workbench** — rewire `runStudyTests()` (grade → chain-to-baseline)
   and the tab redesign (`_renderTestReportCard`).

Each repo gets its **own git worktree**; the workbench must re-lock onto the new
viva-superpowers rev via the sandbox recipe before slices 3–4 see the seam.
Slices 1→2 and 1→3 are ordered by the seam dependency; 3 and 4 are the same
repo.

## Risks / gotchas

- **v2ecoli re-exports `viva_superpowers.study_evaluator`** — the native-path
  change must stay purely additive (unresolved-field is the only new branch) so
  no downstream registry study regresses. Covered by the "emitted field still
  resolves" regression test.
- **Workbench↔viva-superpowers pin** — slices 3–4 need a `uv` re-lock onto the
  new seam; bump `viva-superpowers` only (not the `pbg-superpowers` shim), per
  the lock-illusion trap.
- **Safe-formula scope creep** — keep the node whitelist closed; no names
  beyond observable tokens, no calls, ever. It is a convenience for ratios, not
  a DSL.
- **Snapshot data source** — the grade button and any live-only affordance must
  degrade (hidden) in the published read-only bundle.
