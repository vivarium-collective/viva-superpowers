# Discovery engine — materialization-aware readiness & grading (streamlining plan)

**Date:** 2026-10-27 · **Status:** proposed

## Why

Three recent cycles (genesis → island → eukaryogenesis) kept hitting the same *class* of
friction: **a study looks complete in YAML but is silently empty or ungraded in reality.** The
engine trusts declarations; it does not verify that the declared thing *materialized*. Concrete
instances from these cycles:

- **Declared viz, no rendered figure.** All 5 eukaryogenesis studies declared a `visualizations[]`
  entry but rendered no `studies/<slug>/viz/*.html`, so every workbench Visualizations tab showed
  *"No figures yet."* No error anywhere. (Fixed one-off in viva-superpowers#383 for viz; the shape
  is general.)
- **Tracked run grades SKIP.** On island, colony-behavior, and eukaryogenesis a tracked run emitted
  the right observables but the gate graded **SKIP**, because the run's env-worker imported a
  stale/diverged workspace venv that lacked the study's `register_derived_scalars` evaluators.
  `advance`/grade silently assumes the evaluators are on the run's import path.
- **Calibrated but "unassessed".** Eukaryogenesis's studies are scientifically calibrated (direct
  runs, findings recorded in `study.yaml`), yet the cycle reports them unassessed because there is
  no *tracked* verdict — the evidence exists but doesn't feed closure.

The common root cause: **`run_readiness` / `advance` check that a thing is *declared*, not that it
*exists*.** `complete` means "has the fields," not "produced the artifacts."

## Goal

Make readiness and advance **materialization-aware**: a study is `complete` only when its declared
artifacts actually exist, and the engine *detects and reports* when a tracked run cannot grade
(evaluators unresolvable) instead of silently SKIPping. Turn each silent gap into a checked signal
surfaced in the cycle and the workbench readiness panel.

## Scope — prioritized

### P0.1 — Materialization-aware `run_readiness` (generalize the viz guard)

`run_readiness` already verifies, per field: composite resolves (#382), observables emittable,
measure paths present, and (new, #383) viz rendered. Generalize this into one consistent
**"declared ⇒ materialized"** pass so every quality-bar field is checked the same way:

| declared | materialized check (gap if missing) | field |
|---|---|---|
| `visualizations[]` | a `studies/<slug>/viz/*.html` figure exists | `visualizations_rendered` (shipped #383) |
| `baseline.composite` | the composite module imports | `composite_resolves` (shipped #382) |
| `behavior_tests[].measure{derived}` | the derived-scalar computer is registered + resolvable | NEW `measures_resolvable` |
| `runs[]` / assessed | a run store exists with the gate observables | partly in `already_run`; make explicit |
| `contracts[]` | the contract is declared AND checkable | NEW `contracts_present` (lower priority) |

`complete` requires all *materialized* (not merely declared). Each missing materialization adds a
specific gap string naming the fix. **Files:** `viva_superpowers/discover.py` (`run_readiness`).
**Tests:** one per new check (declared-without-artifact flags; artifact present clears it), mirroring
`test_run_readiness_flags_declared_but_unrendered_viz`.

### P0.2 — Grading-env awareness (end the silent SKIP)

Before/alongside a tracked run, verify the grading environment can resolve the study's
derived-scalar evaluators; if not, **report it loudly** instead of letting the gate SKIP.

- Add `measures_resolvable` to `run_readiness`: for each derived measure, confirm
  `load_workspace_derived_scalars(ws_root).get(path)` resolves. If a measure's computer is not
  registered in the env that will grade the run, emit a gap:
  *"gate `<name>` measure `<path>` has no registered evaluator in this environment — it will SKIP;
  the run env-worker must import the workspace package that defines `register_derived_scalars`
  (editable-install / venv-sync gap)."*
- In `advance` / `_default_runner`, surface a SKIP caused by an unresolved evaluator as a distinct
  **`grade_unresolved`** outcome (not a generic SKIP), so the cycle can tell "the science is
  undecided" from "the environment couldn't grade it."
- Document the fix in the gap text: run the grading env against the workspace *source* (worktree on
  `PYTHONPATH`) or sync the editable install, rather than a stale canonical checkout.

**Files:** `viva_superpowers/discover.py` (`run_readiness`, `advance_cycle`, `_default_runner`),
`viva_superpowers/study_evaluator.py` (expose a cheap "is this measure resolvable?" helper).

### P1 — recorded findings as partial evidence

Let the cycle recognize a study's **recorded `findings[]` / calibration** as partial, non-tracked
evidence, so a calibrated-but-unrun study is visibly "calibrated, pending tracked run" rather than
flatly "unassessed." Keep it distinct from a tracked verdict (don't let it close a criterion on its
own). **Files:** `knowledge_store.py` (verdict derivation reads findings as a weak signal),
`discovery_engine.py` (frontier labels a calibrated study differently from a never-touched one).

### P1 — a "publishable" axis distinct from scientific closure

Scientific closure (acceptance criteria met) and presentation completeness (viz rendered, report
materialized) are orthogonal — an investigation can be *closed* and presentationally empty.
Surface a **`publishable`** summary in `diagnose` (all member studies `complete` + figures rendered),
separate from `closed`, so "done" can't hide "empty." **Files:** `discovery_engine.py` (`diagnose`).

### P1 — render-on-run (close the materialization loop)

Running/building a study should **auto-render its declared viz** so the figure can never silently
fail to materialize. This is mostly a workbench change (the auto-results path), but the engine's
`advance` should treat "ran but figures not rendered" as a remaining step and trigger/record the
render. **Files:** workbench `composite_runs` auto-results + `discover.advance_cycle`.

## Rollout & verification

1. P0.1 + P0.2 land together (one PR) — they share the `run_readiness` surface and are the highest
   leverage (each would have caught a real failure from these cycles *before* it was seen).
2. Verify on the three workspaces that exposed the friction: eukaryogenesis (viz + measures now
   materialized/resolvable), island + colony (the SKIP now reported as `grade_unresolved` with the
   venv-sync fix named).
3. Full `pytest -q` + ruff; new tests per check.
4. P1 items follow as separate PRs.

## Non-goals

- Fixing the editable-install mechanics itself (venv sync, worktree installs) — this plan makes the
  engine *detect and name* the gap, not re-plumb the run infrastructure.
- Auto-seeding frontier study proposals (tracked separately as finding #4 / #E).
