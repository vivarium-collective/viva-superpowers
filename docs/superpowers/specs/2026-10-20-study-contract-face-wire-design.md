# Study↔Composite Contract-Face Reconciliation (P3) — Design

**Status:** approved (Option A), 2026-10-20
**Repo:** viva-superpowers only
**Depends on:** bigraph-schema ≥1.8 (available; the typed audit degrades gracefully if absent)

## Intent

A study may declare a typed `contract.face` (ports with `_type`/`_units`/`_min`/`_max`;
schema merged via viva-template #80, shape-gated HARD via viva-superpowers #334). Today
nothing checks that declared face against the **real composite the study runs** — the
reconciliation machinery exists but is dormant and uncalled:

- `contract_spine.contract_face_diff(study_face, composite_face)` — pure type/unit/port diff.
- `study_contract_lint.lint_study_contract(study_spec, composite_face)` — reads
  `study.contract.face`, calls the diff.
- `unified_contract_audit.unified_contract_findings(process_contract, study_face, core)` —
  fuses the bigraph-schema contract audit *and* the face diff into one Findings surface
  (version-tolerant: skips the typed audit pre-1.8).

The uniform gap: all three need the composite's **resolved `ProcessContract`/face**, and
nothing resolves a real composite to produce it. P3 builds that resolver and lights up the
stack as a **best-effort, report-time** check.

## Approach (Option A)

A new resolver imports the workspace package's `build_core()`, builds the study's baseline
composite from its id/params (`process_bigraph.composite_spec.discover_specs` →
`CompositeSpec.to_composite(emit=False)`), and reads its contract via
`bigraph_schema.resolve_contract`. A thin reconciler feeds that into
`unified_contract_findings`. The result surfaces as a `report_linter` check.

**Best-effort and additive:** a study with no declared `contract.face`, or whose composite
can't be built (missing deps, bad params), yields **no findings** — the check abstains, never
fabricates, never crashes. It is NOT wired into the static `study_audit --gate` (which stays
simulator-free); capturing the face at run time for a hard CI gate is a possible later upgrade
(Option B), out of scope here.

## Goals

1. `composite_contract_resolver`: best-effort `study_composite_contract(study_spec, ws_root,
   core=None) -> (ProcessContract | None, core)` — build the baseline composite, resolve its
   contract; `(None, core)` on any failure. Plus a small, directly-testable
   `contract_of_composite(composite) -> ProcessContract | None`.
2. `reconcile_study_contract(study_spec, ws_root) -> list[dict]` — resolve, then
   `unified_contract_findings(process_contract, study_face, core)`; `[]` when the study
   declares no face or the composite is unresolvable.
3. A `report_linter` check (`_check_contract_face_reconciliation`) that emits an
   **error-level** `LintFinding` per face disagreement for a study that declares a
   `contract.face`, registered in the check registry; abstains otherwise.

## Non-goals

- No change to `study_audit`/`--gate` (stays simulator-free).
- No run-time face-capture artifact (Option B).
- Not implementing the T1–T3 readout-unit wires named in `contract_spine` (`available_observables`,
  `validate_readouts`, `test_contract` unit bands) — a separate, deeper extension.
- No workbench changes.

## Constraints

- **No AI attribution** in commits/PRs.
- Worktree off `origin/main` (`viva-superpowers--contract-face-wire`, branch
  `feat/study-contract-face-wire`). Validate with the viva-genesis venv (bigraph-schema 1.8.1)
  + `PYTHONPATH=<worktree>`.
- Reuse the dormant layers (`contract_face_diff`, `lint_study_contract`,
  `unified_contract_findings`) — do not reimplement the diff/fusion.
- Best-effort everywhere: never let contract resolution crash a report lint.

## Review focus

- Study with no `contract.face` → zero findings (abstain).
- Composite unbuildable (bad id/params/missing dep) → zero findings, no crash.
- Declared face matches composite → zero findings.
- Declared face disagrees (missing port / type / units) → one error finding each.
- bigraph-schema typed audit present vs absent → face diff still runs (version-tolerant).
