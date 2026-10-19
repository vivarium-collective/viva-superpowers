# Process Contract Unification — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Unify the two contract systems — the typed process-bigraph `ProcessContract` (face + port `_units`/bounds + conditions) and the study audit (`readouts`, `behavior_tests`, bands) — so a study's acceptance tests are **type/unit/shape-checked against the process contracts of the composite it runs**, with one shared Finding vocabulary. This is the foundation the investigation framework's contract spine (RFC-0004 §4) sits on; it ships as its own PR stack on `main`, and the investigation PRs (#78/#329/#1394) rebase onto it afterward.

**Architecture:** Version-tolerant wiring. The study audit already consumes the same core primitives the bigraph-schema audit uses — `readout_validation.validate_readouts`, and `composite_audit.py` which already calls `core.resolve_schemas` (type agreement) + `core._compute_unit_scale` (dimensional units). We point those at the composite's resolved port types/units and the process `ProcessContract.face`, flagging **only a declared disagreement** (never fabricating a unit it can't see). Workbench is already pinned to `bigraph-schema>=1.8.1`, so the wiring works today and strengthens as contracts gain faces/units.

**Tech Stack:** `process_bigraph` / `bigraph_schema` 1.8.1 (typed `ProcessContract`, `contract_audit`, `units`/pint); `vivarium_workbench/lib` (audit seam); `viva_superpowers` (bands); pytest.

**Spec:** RFC-0004 §4 (the contract spine) + this plan's grounding (below).

## Grounding (verified 2026-10-19)

- **bigraph-schema 1.8.1 is released** (PyPI + tag `v1.8.1`, a clean superset of `main` = main+9 commits). The API jump 1.4.x→1.8.1 is **additive** — no removed core defs, `edge.py` unchanged, `resolve_schemas`/`_compute_unit_scale` stable across refs. (The "1.4.17 break" memory is unsubstantiated — no such release.)
- **Typed machinery location:** `face`/`amend`/`_with_declared_face` are on bigraph-schema `main`; the `conditions` expr-parser + `contract_audit.py` + `contract_expr.py` live **only on the 1.8.x release tags, not `main`** — so `branch=main` consumers miss the audit.
- **Pin graph (fragmented):** process-bigraph `>=1.6.0`→1.6.0; viva-superpowers `>=0.0.60`→1.4.5; **vivarium-workbench `>=1.8.1`→1.8.1 ✅**; viva-template none; v2ecoli/sms-ecoli pin `git branch=main` but lockfiles frozen to pre-`face` SHAs (1.4.3 / 1.6.0).
- **Audit gate:** `process_bigraph/audit_contracts.py` (origin/main) has `--require-declared N` (default 0); wired into CI with **no floor** (advisory). Local process-bigraph checkout is 52 behind + lacks the file.
- **Coverage ~0:** ~36 v2ecoli processes declare `ProcessContract` but **prose-only** (no face/units/conditions); 25 expose `interface()` → face auto-fills free on 1.8.x. sms-ecoli ~6; viva-superpowers 0.
- **4 confirmed wire points:** `lib/readout_validation.py` (`available_observables`:122, `validate_readouts`:338); `lib/composite_audit.py` (`resolve_schemas`:134, `_compute_unit_scale`:155); `viva_superpowers/test_contract.py` (`band`:30); `lib/notebook_export.py` (`_contract_md`:365).

## Global constraints

- **Additive + version-tolerant.** The wiring must work on the current runtime and strengthen as contracts gain faces/units. A port with no declared units → no unit check (silent, not a mismatch). **Never fabricate a unit disagreement.**
- **Contracts compose, never collapse** (RFC-0004 §4): an interface/unit check passing ≠ a scientific verdict. No audit may mechanically upgrade a verdict.
- **The landing (PR-C) is a re-pin, not a code change.** bigraph-schema 1.8.1 is additive; the risk is resolver/composite-build on the big suites, not API breakage. Validate per repo against freshly-pulled trees.
- **Coverage is a ratchet.** Start the `--require-declared` floor at 0; raise it only as typed contracts are authored. Never force authoring to land the wiring.

## Review focus

- A readout on a port whose type carries **no `_units`** → `validate_readouts` must stay `ok`, not invent a unit mismatch. (PR-A)
- A band in a **convertible** unit (fg vs kg) → reconcile and compare; an **incompatible** unit (fg vs mol) → flagged. (PR-B)
- A composite with a **prose-only** contract (no face) → the audit degrades gracefully (reports low completeness), never errors. (PR-D)
- v2ecoli/sms **composite still assembles** across the 1.4→1.8 jump. (PR-C)
- The gate floor set **above current coverage** would red-wall CI → floor starts at 0. (PR-E)

## PR roadmap

| PR | Repo(s) | What | Buildable |
|---|---|---|---|
| **A** | vivarium-workbench | `available_observables` returns `{type, units, bounds}`; `validate_readouts` adds a type/unit/shape check via `_compute_unit_scale` | **now** |
| **B** | viva-superpowers | `test_contract` bands carry + reconcile a unit; wire `contract_face_diff` (study `contract.face` ↔ composite) into the lint | **now** |
| **C** | bigraph-schema → process-bigraph → viva-superpowers → viva-template (+ v2ecoli/sms) | **land 1.8.1**: resolve main-vs-release, re-pin bottom-up, relock, per-repo composite-build validate | infra |
| **D** | vivarium-workbench + viva-superpowers | unify the audit: study audits call bigraph-schema `contract_audit.audit_contract()`/`completeness()`; fold `op_invariants` + contract checks + readout validation into one surface; `/viva-tests`, `/viva-report` | after A/B/C |
| **E** | process repos | author faces (auto for 25) + `_units`/bounds/`conditions`; ratchet `--require-declared` | incremental |

A/B land on `main` now; C is the external re-pin; D unifies once C lands; E ratchets.

---

## PR-A — study readouts type/unit-checked against the composite (vivarium-workbench)

**Files:** `vivarium_workbench/lib/readout_validation.py` (extend `available_observables` + `validate_readouts`); `tests/test_readout_validation_types.py`. Reuse `composite_audit._safe_units`/`core.access`/`core._compute_unit_scale`.

- [ ] **A1 — `available_observables` returns per-leaf type metadata.** Add, per leaf, `{type, units, min, max}` resolved via `core.access` (mirroring `composite_audit._safe_units`), alongside the existing `leaves`/`catalogs` (additive — existing callers unaffected). Test: on a composite with a unit-typed leaf, the leaf reports its units; a bare leaf reports `units: None`.
- [ ] **A2 — `validate_readouts` gains a type/unit/shape check.** For a resolved readout whose declared `units` (already carried on `ResolvedReadout.units`) and the leaf's declared units are both present, compare via `core._compute_unit_scale`; on dimensional disagreement emit `status: "unit_mismatch"` (new) with detail; shape disagreement → `"shape_mismatch"`. Both units absent → unchanged (`ok`). Test: `[fg]` readout on a `[mol]` leaf → `unit_mismatch`; `[fg]` on a unitless leaf → `ok`; convertible units → `ok`.
- [ ] **A3 — endpoint passthrough.** The `/api/study-observable-check` payload carries the new statuses (pass-through model; no client change required). Test the builder returns the new status.
- [ ] Commit per task; PR targets `main`.

## PR-B — bands carry + reconcile units; face-diff in the lint (viva-superpowers)

**Files:** `viva_superpowers/test_contract.py` (bands); wire `viva_superpowers/contract_spine.contract_face_diff` into the study lint (`report_linter.py` or `study_audit.py`); tests.

- [ ] **B1 — `Expected.band` carries a unit; `check` reconciles it.** Add optional `units` to `band(low, high, units=None)`; in `check(...)`, when both the band and the observed carry units, reconcile dimensionally (via `bigraph_schema.units` pint registry) before the margin; incompatible units → a typed error finding, not a silent pass (today `units=` is display-only). Test: convertible reconciles; incompatible errors; no-units unchanged.
- [ ] **B2 — wire `contract_face_diff` into the study lint.** When a study authors a `contract:` block, diff its `face` against the composite's resolved contract face; surface disagreements as lint findings (reuse the pure fn — already tested). Test on a study with a mismatched face.
- [ ] Commit per task; PR targets `main`.

## PR-C — land bigraph-schema 1.8.1 (outline, infra)

- Resolve the **main-vs-release-line** question first: merge the 9-commit 1.8.x line into bigraph-schema `main` (+ bump its stale `1.6.0` version string) **or** re-point every `git branch=main` source at tag `v1.8.1`/PyPI. Pick one; otherwise `branch=main` consumers keep missing `contract_audit`.
- Re-pin **bottom-up**: process-bigraph `>=1.6.0`→`>=1.8.1`; viva-superpowers `>=0.0.60`→`>=1.8.1`; viva-template add `>=1.8.1`; v2ecoli/sms re-point the `[tool.uv.sources]` + `uv lock --upgrade` off the frozen pre-`face` SHAs. Workbench already there.
- **Validate per repo**: `uv sync` + composite build + full test for v2ecoli/sms (the only real risk is "does the big composite still assemble" across the 4-family jump; API is additive). Pull the stale local process-bigraph/bigraph-schema checkouts first.

## PR-D — unify the audit layer (outline)

- Point `composite_audit.py`/`readout_validation.py` at each process's resolved `ProcessContract.face` (+ `_units`/`_min`/`_max`) via 1.8.x `resolve_contract`, and call bigraph-schema `contract_audit.audit_contract()`/`completeness()` so **study audits and the process-bigraph gate report the same `Finding`s**.
- Feed `conditions()` (invariant/pre/post/validity) into `test_contract` bands and surface them through `_contract_md` in the study `contract:` block.
- Fold `viva_superpowers.op_invariants` + the PR-A/B checks into one audit surface consumed by `/viva-tests` and `/viva-report` (so studies and investigations lint through the same gate).

## PR-E — contract authoring + ratchet the floor (outline, incremental)

- Author faces (auto-fill for the 25 v2ecoli `interface()` processes), then hand-author `_units`/bounds + `conditions` on the load-bearing processes.
- Turn `process-bigraph/.github/workflows/pytest.yml` `audit_contracts` from advisory to enforcing by adding `--require-declared N`, starting low and ratcheting as coverage grows.

## Self-review

- Spec coverage vs RFC-0004 §4: the four wires → PR-A (readouts) + PR-B (bands/face-diff) + PR-D (shared Findings); the typed-contract dependency → PR-C; authoring → PR-E. The never-fabricate + never-upgrade-verdict rules are global constraints.
- Proportion: PR-A/B are decomposed (buildable now, pytest-verifiable); C/D/E are outlined (C gated on the re-pin, D on C, E incremental).
