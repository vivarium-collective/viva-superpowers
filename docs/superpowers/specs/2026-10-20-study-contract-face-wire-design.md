# Study Contract-Face ↔ Run-Observables Reconciliation (P3) — Design

**Status:** approved (Option A after a pivot), 2026-10-20
**Repo:** viva-superpowers only
**Depends on:** `viva_emitters.RunReader` (present); `run_registry.latest_run`.

## Intent

A study may declare a typed `contract.face` (ports with `_type`/`_units`/`_min`/`_max`;
schema via viva-template #80, shape-gated HARD via #334). Nothing checks that declared
interface against what the study's simulation **actually produces**. P3 adds that check as
a best-effort, report-time lint.

## Why not the composite's face (recorded pivot)

The first cut tried to diff `contract.face` against the composite's resolved
`ProcessContract` (the dormant `contract_spine`/`unified_contract_audit` stack). That
premise does not hold for real workspaces: a fully-wired composite exposes **no** open
face — for viva-genesis `og-00`, `core.render(comp.schema)` is literally
`"global_time:float"`, and `interface()`/`resolve_contract`/`collect_face`/`state`/
`default_state` are all empty of the declared ports (temperature, formate, H2, …). Those
variables are **run-emitted observables**, not static composite stores. So the reconciliation
target is the **run's observables**, not the composite's face.

Validated on `og-00`: the run emits 10 observables (temperature, H2, pH, porosity, fluxes…);
the study declares `pressure`, `flow_velocity`, `DIC` (inputs) and `heat_flux` (output) that
the run **never emits** — a real "declared-but-not-produced" finding, cleanly separated from
the ports that are present.

## Approach (Option A)

Resolve a study's **latest run** (`run_registry.latest_run(<study_dir>/runs.db)` →
`emitter_path` → `viva_emitters.RunReader.open`), read `reader.observables()`, and diff the
study's declared `contract.face` ports against that set. Observables are **untyped** (a run
emits values, not a typed schema), so the check is **presence-only**: a declared port that
the run does not emit is flagged; type/units are not checked (never fabricate). Surfaced as a
`report_linter` check.

**Best-effort & additive:** no `contract.face`, no run yet, or an unreadable run → **zero
findings** (abstain), never an exception, never a fabricated mismatch.

## Goals

1. `study_run_observables(study_spec, ws_root) -> set[str] | None` — latest run's emitted
   observable names; `None` when there is no run / it can't be read.
2. `reconcile_study_observables(study_spec, ws_root) -> list[dict]` — `[]` when the study
   declares no `contract.face` or has no readable run; otherwise one finding per declared
   port (inputs or outputs) absent from the run's observables
   (`{severity, check: "contract-observable", message}`).
3. A `report_linter` check (`_check_contract_observables`) emitting a **warning**-level
   `LintFinding` per gap for a study that declares a `contract.face`, registered in the
   check registry; abstains otherwise. Warning (not error): a declared input may be a fixed
   config quantity legitimately not emitted — surface it, don't red-wall it.

## Non-goals

- The composite-face / typed `unified_contract_findings` path (Option B) — left dormant for a
  future workspace whose composite exposes a typed face.
- No type/units reconciliation (run observables are untyped).
- No change to `study_audit`/`--gate` (stays simulator-free).
- No T1–T3 readout-unit wires; no workbench changes.

## Constraints

- **No AI attribution** in commits/PRs.
- Worktree off `origin/main` (`viva-superpowers--contract-face-wire`, branch
  `feat/study-contract-face-wire`). Validate with the viva-genesis venv +
  `PYTHONPATH=<worktree>`.
- Best-effort everywhere: contract/run resolution never crashes a report lint.
- Tests in `tests/`.

## Review focus

- Study with no `contract.face` → zero findings.
- Study with no run (or unreadable run) → zero findings, no crash.
- Declared port present in observables → no finding; absent → one warning finding.
- Both inputs and outputs are checked against the one observable set.
- `RunReader.open` / `latest_run` failure → abstain, never raises into the linter.
