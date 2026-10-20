# Study-Audit Unify + Harden — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make "how do we know a study is legit" a single enforced contract — promote the load-bearing checks that today only *warn* or *surface* into **HARD, ratcheted gates**, and ground test/card acceptance in the typed process contracts — so a study cannot roll up to Accepted while its verdict is stale, its acceptance was tuned post-hoc, its evidence is unprovenanced, or its claim contradicts the computed result.

**Architecture:** The study already proves legitimacy in six layers (structural → reproducible execution → graded tests/cards → cited acceptance → rolled-up verdict → reviewer audit). The checks for most of the middle layers already exist and are *computed* — they are just not *enforced* (`study_verdict.preregistration_gate_alignment` warns, `study_audit` L2–L5 are SOFT, `needs_attention` surfaces divergence). This plan flips the load-bearing ones to HARD using the **existing allowlist ratchet** in `study_audit.py` (allowlist may only shrink), so CI stays green on day one and tightens as workspaces are cleaned. The contract-grounding layer (bands checked against process-contract units) is delivered by the contract-unification stack (PRs A–E) and consumed here.

**Tech Stack:** `viva_superpowers` (`study_audit`, `study_verdict`, `card_grade`, `finding_observations`, `run_registry`); `vivarium_workbench/lib` (`report_linter`, `needs_attention`, `readout_validation`); `bigraph_schema` 1.8.1 (`contract_audit`); pytest.

**Spec:** The study-legitimacy map + the 8 hardening gaps (research synthesis, 2026-10-19, in `project_process_contract_unification` memory) + RFC-0004 §4 (the contract spine). The contract-unification plan `2026-10-19-process-contract-unification.md` is the wiring dependency.

## Global Constraints

- **Every new gate is a ratchet.** A gate lands with an **allowlist seeded with the current violators** (enumerated at implementation time), and the allowlist may only shrink (reuse `study_audit.stale_allowlist_entries` / `--gate`). Never red-wall CI; never force a workspace to fix content to land a gate.
- **Never fabricate.** A check that cannot resolve its inputs (no computed verdict, no contract face, no run manifest) **abstains** — it is not a violation. Enforcement applies only to a *declared* disagreement or a *present-but-wrong* artifact. This mirrors the existing never-fabricate seams (`readout_validation` not_in_structure, `finding_observations` SKIP-on-missing).
- **Checks compose, never upgrade.** A gate may *block* a claim; no gate may mechanically *raise* a verdict (RFC-0004 §4). Passing an interface/unit check is not a scientific result.
- **Derive-on-read stays intact.** Enforcement reads the parallel computed slots (`gate_evaluator`, `computed_outcomes`, `computed_verdict`) and the authored ones; it never overwrites authored fields.
- **Tier discipline.** New gates default to tier SOFT (warn) for one release, then flip to HARD with the ratchet. The plan marks the intended final tier; the flip is a one-line change guarded by the allowlist.

## Review Focus

- A study with **no canonical run yet** (planned, not simulated) → every enforcement check must abstain, not fail. (H1, H3, H4, H5)
- A study whose `verdict.json` is **hand-authored / stale** but says `overall: within_tol` → H1 must catch the recompute mismatch, not pass on file existence.
- An `acceptance_criterion` whose `pass_if` **equals** its `preregistered.thresholds` entry → H2 passes; a band *widened* after the preregistration entry → H2 fails. (not just missing-prereg)
- A finding rolled up to Accepted that cites a **bib key with no run** behind it → H3 fails; a `caveat`/`refuted` finding with no evidence → H3 abstains (only *supporting* claims need provenance).
- A single-seed run that is a **regression_pin** (not a scientific claim) → H5 exempts it; only `acceptance_criterion` primary claims gate on replication.

---

## PR roadmap

| PR | Gap | Repo(s) | What | Final tier |
|---|---|---|---|---|
| **H1** | #5 verdict not re-graded | viva-superpowers | `study_audit` L4 re-grades `grade_card` against the on-disk `verdict.json`; recompute mismatch fails | HARD |
| **H2** | #2 tune-to-pass | viva-superpowers | promote `unregistered_acceptance` (acceptance_criterion `pass_if` ≠ preregistered threshold) to a gated check | HARD (ratchet) |
| **H3** | #6 provenance not required | viva-superpowers + workbench | a finding rolling up to *supported/Accepted* must carry `evidence.from_test` + `provenance.run_ids` | HARD (ratchet) |
| **H4** | #7 divergence non-blocking | workbench | `diverges_from_authored` (authored verdict contradicts computed) blocks `/viva-report` publication | block-on-publish |
| **H5** | #3 single-seed | viva-superpowers | thread `seed` into `run_registry` manifest; a single-seed `acceptance_criterion` primary claim gates on replication | SOFT→HARD ratchet |
| **H6** | #4 reproducibility soft | viva-superpowers | promote L2 `node-keyable` (content-addressable) to HARD for studies that *claim* reproducibility | HARD (ratchet) |
| **H7** | #1,#8 contract grounding | (depends on A–E) | land 1.8.1 + wire `contract_spine` T1–T3 so `test_contract.check` reconciles band units against the process-contract port units on `main` | — |

H1–H3 are decomposed below (ready now, pure study-audit, independent of the 1.8.1 landing). H4–H6 are outlined (each a tier flip + its check). H7 is the contract-unification stack (A–E) — see its own plan; this plan only consumes it.

---

## H1 — re-grade the verdict instead of trusting the file (viva-superpowers)

**Files:** `viva_superpowers/study_audit.py` (replace the L4 `report-card-verdict` existence check with a recompute); `viva_superpowers/card_grade.py` (reuse `grade_card`/`verdict_json`); `tests/test_study_audit_regrade.py`.

**Interfaces:**
- Consumes: `card_grade.grade_card(card, reference) -> verdict dict`, `card_grade.verdict_json(...)`, the on-disk `*.verdict.json` (`overall` + per-axis), the study's canonical run dir.
- Produces: `study_audit._check_verdict_regrade(study_dir) -> list[CheckResult]` (level `"L4"`, tier `HARD`), wired into the existing `CHECKS`/`--gate` allowlist flow.

- [ ] **Step 1: Write the failing test** — `test_stale_verdict_json_fails_regrade`: a study dir with a `verdict.json` whose `overall` is `within_tol` but whose stored reference + measured values re-grade to `mismatch` → `_check_verdict_regrade` returns one `CheckResult(level="L4", status="fail")`. `test_matching_verdict_passes`: re-grade equals stored → `status="pass"`. `test_no_run_abstains`: study with no canonical run / no verdict.json → returns `[]` (abstain), not a fail.
- [ ] **Step 2: Run it, verify it fails** — `pytest tests/test_study_audit_regrade.py -v` → FAIL (function missing).
- [ ] **Step 3: Implement `_check_verdict_regrade(study_dir)`** — load each `*.verdict.json`; for every axis that carries its inputs (`reference`/`ref_vector`/`measured`), recompute via `card_grade.grade_card` and compare the rolled-up `overall`; on a resolvable mismatch emit a HARD `CheckResult`; when an axis lacks stored inputs to recompute, skip that axis (abstain) rather than fail. Register in `CHECKS`.
- [ ] **Step 4: Run tests, verify pass.**
- [ ] **Step 5: Seed the allowlist + commit** — run `--gate` across the workspaces, capture current violators into the L4 allowlist, commit the check + allowlist together.

## H2 — gate post-hoc acceptance (viva-superpowers)

**Files:** `viva_superpowers/study_audit.py` (new check consuming `study_verdict`); `viva_superpowers/study_verdict.py` (expose `unregistered_acceptance` as a pure list if not already); `tests/test_study_audit_prereg.py`.

**Interfaces:**
- Consumes: `study_verdict.preregistration_gate_alignment(spec) -> {unregistered_acceptance: [...], ...}`, `study_verdict.classify_gates`.
- Produces: `study_audit._check_preregistration(study_dir) -> list[CheckResult]` (level `"L1"` tier HARD, ratcheted).

- [ ] **Step 1: Write the failing test** — `test_unregistered_acceptance_fails`: a study with an `acceptance_criterion` test whose `pass_if` has **no** matching `preregistered.thresholds` entry → one HARD `CheckResult`. `test_widened_band_fails`: a preregistered entry exists but the `pass_if` band is *wider* than it → fail. `test_matching_prereg_passes`: `pass_if` equals the preregistered threshold → pass. `test_regression_pin_exempt`: a `regression_pin` with no prereg → abstain (pins are not claims).
- [ ] **Step 2: Run it, verify it fails.**
- [ ] **Step 3: Implement `_check_preregistration`** — call `preregistration_gate_alignment`; map each `unregistered_acceptance` entry to a HARD `CheckResult`; pins and non-acceptance gates abstain. Register in `CHECKS`.
- [ ] **Step 4: Run tests, verify pass.**
- [ ] **Step 5: Seed the allowlist (every current post-hoc acceptance) + commit.**

## H3 — require provenance for supporting claims (viva-superpowers + workbench)

**Files:** `viva_superpowers/study_audit.py` (new check); reuse `finding_observations` + `study_verdict.derive_confidence`; `tests/test_study_audit_provenance.py`. (Companion workbench lint: `report_linter.finding_without_evidence` flips from warning→error under the same allowlist — a one-line severity change + test.)

**Interfaces:**
- Consumes: the study spec's `findings[]` (`statement`, `evidence.from_test`, `provenance.run_ids`, `claim_scope`), `study_verdict.derive_confidence(spec)`, `roll_up_verdict`.
- Produces: `study_audit._check_supporting_provenance(study_dir) -> list[CheckResult]` (level `"L2"`, tier HARD, ratcheted).

- [ ] **Step 1: Write the failing test** — `test_accepted_finding_without_runid_fails`: a finding whose claim supports an Accepted/`supported` verdict but has empty `provenance.run_ids` → HARD fail. `test_caveat_without_evidence_abstains`: a `caveat`/`refuted`/exploratory finding with no evidence → abstain (only supporting claims need provenance). `test_fully_provenanced_passes`.
- [ ] **Step 2: Run it, verify it fails.**
- [ ] **Step 3: Implement `_check_supporting_provenance`** — for each finding whose confidence is supporting (`derive_confidence`/verdict maps to Accepted/supported), require non-empty `evidence.from_test` **and** `provenance.run_ids`; non-supporting findings abstain. Register in `CHECKS`.
- [ ] **Step 4: Run tests, verify pass.**
- [ ] **Step 5: Flip `report_linter.finding_without_evidence` to error under its override allowlist; seed allowlist; commit.**

---

## H4 — divergence blocks publication (workbench, outline)

- `/viva-report` Pass A already reads `needs_attention`; add a **blocking** finding class when `study_verdict.diverges_from_authored(spec)` is true (authored verdict contradicts the computed one) — authored-contradicts-computed blocks render unless `--force` (reuse the existing Pass-A blocking + `--force` path). Never auto-reconcile; the author resolves by fixing the claim or the gate.
- Test: a study whose authored `gate_status` says PASS but `roll_up_verdict` says FAIL → `GET /api/report-lint` returns a blocking finding; render refuses without `--force`.

## H5 — replication gate for primary claims (viva-superpowers, outline)

- Thread `seed` into `run_registry.build_run_manifest` (today `seed: None`); record the seed set behind a canonical run. Add `study_audit._check_replication`: an `acceptance_criterion` primary claim whose canonical run has a single seed → SOFT first, then HARD via the ratchet. `regression_pin`s and exploratory studies exempt.
- Test: single-seed acceptance claim → flagged; multi-seed → pass; pin → abstain.

## H6 — reproducibility ratchet (viva-superpowers, outline)

- Promote L2 `node-keyable` (content-addressable: composite + config + sorted input ids + commit all resolve) from SOFT to HARD **only for studies that assert reproducibility** (a `reproducibility:` claim or an investigation acceptance that depends on rerun). Keep it SOFT elsewhere. Ratcheted.
- Test: a reproducibility-claiming study missing a resolvable producer → fail; a study making no such claim → still SOFT.

## H7 — contract grounding on main (depends on A–E, outline)

- This is the contract-unification stack: land bigraph-schema 1.8.1 (PR-C, done in draft), merge the unified audit (PR-D #332), and implement `contract_spine` T1–T3 so `test_contract.check` reconciles a band's declared units against the composite's **process-contract port units** before computing the margin (gap #1). PR-E (#851) supplies the typed contracts the bands check against. No new work here beyond merging A–E and turning on T3; this plan consumes the result.

---

## Self-review

- **Spec coverage vs the 8 gaps:** #1/#8 → H7 (the A–E stack); #2 → H2; #3 → H5; #4 → H6; #5 → H1; #6 → H3; #7 → H4. All eight have an owning PR.
- **Step scan:** H1–H3 steps each decide one thing (the check's resolution rule, its tier, its abstain condition); the allowlist-seeding step is folded into each gate's final commit (it is that gate's enablement, not a separate deliverable). H4–H6 are outlined because each is a tier flip whose check already exists (`diverges_from_authored`, seed threading, L2) — decompose at execution.
- **Type consistency:** every new check returns `list[CheckResult]` with `level`/`status`/`tier` matching `study_audit`'s existing dataclass and registers in the same `CHECKS` tuple + `--gate` allowlist flow; no new gate mechanism is introduced.
- **Review Focus:** the five uncovered inputs (planned-no-run abstain, stale verdict.json, widened-band, bib-key-no-run, single-seed pin) each map to a named test in H1/H2/H3/H5.
- **Proportion:** three PRs decomposed, four outlined — matching the unification plan's shape; the shared ratchet + never-fabricate rules live once in Global Constraints, not repeated per task.
