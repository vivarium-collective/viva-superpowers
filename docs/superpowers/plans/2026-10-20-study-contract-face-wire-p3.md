# Study↔Composite Contract-Face Reconciliation (P3) — Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (Native) to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Light up the dormant study↔composite contract-face reconciliation as a best-effort, report-time check: resolve the real composite's `ProcessContract` and diff the study's declared `contract.face` against it.

**Architecture:** viva-superpowers only, additive, best-effort. A new resolver builds the study's baseline composite (`build_core` + `CompositeSpec.to_composite`) and reads its contract (`resolve_contract`); a thin reconciler feeds it to the existing `unified_contract_findings`; a `report_linter` check surfaces disagreements. Nothing is wired into the simulator-free `study_audit --gate`.

**Tech Stack:** Python 3.12; viva-superpowers on `origin/main` (`4462492`); process-bigraph 1.9.1 / bigraph-schema 1.8.1 (viva-genesis venv); pytest.

**Spec:** `docs/superpowers/specs/2026-10-20-study-contract-face-wire-design.md`

## Global Constraints

- **No AI attribution** in commits or PR.
- **viva-superpowers only**; reuse `contract_face_diff` / `lint_study_contract` / `unified_contract_findings` — don't reimplement them.
- **Best-effort everywhere:** a missing/unbuildable composite or absent `contract.face` → zero findings, never a crash.
- **Worktree:** `~/code/viva-superpowers--contract-face-wire` (branch `feat/study-contract-face-wire`, off `origin/main`). Validate with `~/code/viva-genesis/.venv/bin/python` + `PYTHONPATH=<worktree>`; confirm `import viva_superpowers` resolves into the worktree.
- Tests in `tests/`.

## Review Focus

- No `contract.face` declared → abstain (0 findings). → Task 2/3.
- Composite unbuildable (bad id/params/missing dep) → abstain, no crash. → Task 1/2.
- Declared face matches → 0 findings. → Task 2.
- Declared face disagrees (missing port / type / units) → one error finding each. → Task 2/3.
- bigraph-schema typed audit absent → face diff still runs (version-tolerant via `unified_contract_findings`). → Task 2.

---

### Task 1: Composite→contract resolver

**Files:**
- Create: `viva_superpowers/composite_contract_resolver.py`
- Test: `tests/test_composite_contract_resolver.py`

**Interfaces:**
- Produces: `contract_of_composite(composite) -> ProcessContract | None` (best-effort `resolve_contract`); `study_composite_contract(study_spec, ws_root, core=None) -> tuple[ProcessContract | None, object | None]` — resolve the workspace package's `build_core()`, `discover_specs(ws_root)`, find the study's baseline composite id, `spec.to_composite(overrides=params, core=core, emit=False)`, then `contract_of_composite`. Returns `(None, core_or_None)` on any failure.
- Consumes: `bigraph_schema.resolve_contract`; `process_bigraph.composite_spec.discover_specs`; the workspace-package resolution pattern in `study_evaluator._workspace_package`.

- [ ] **Step 1: Write failing tests.**
```python
def test_contract_of_composite_reads_face():
    # build a tiny composite (one registered process, ca_sense→pth_out) via core.access+Composite;
    # contract_of_composite(composite).face has the composite's inputs/outputs.
def test_contract_of_composite_none_on_junk():
    assert contract_of_composite(object()) is None   # best-effort, never raises
def test_study_composite_contract_none_on_bad_ws(tmp_path):
    # a study spec whose composite can't be resolved → (None, <core-or-None>), no raise
    c, core = study_composite_contract({"conditions": {"baseline": {"composite": "nope"}}}, tmp_path)
    assert c is None
```
- [ ] **Step 2: Run tests, verify fail.** `pytest tests/test_composite_contract_resolver.py -v`
- [ ] **Step 3: Implement.** `contract_of_composite` = `resolve_contract(composite)` in try/except → None. `study_composite_contract`: best-effort build_core (import the ws package per `_workspace_package`), `discover_specs(ws_root)`, read baseline composite id from `spec["conditions"]["baseline"]["composite"]` (+ params), `to_composite(emit=False)`, resolve. Every failure path → `(None, core?)`.
- [ ] **Step 4: Run tests, verify pass.**
- [ ] **Step 5: Commit.** `feat(contract): best-effort composite→ProcessContract resolver`

---

### Task 2: `reconcile_study_contract`

**Files:**
- Modify: `viva_superpowers/study_contract_lint.py` (add the resolver-backed entry alongside the pure `lint_study_contract`)
- Test: `tests/test_study_contract_lint.py` (add cases)

**Interfaces:**
- Produces: `reconcile_study_contract(study_spec, ws_root) -> list[dict]` — resolve via `study_composite_contract`, then `unified_contract_findings(process_contract, study_face, core)`; `[]` when the study declares no `contract.face` or the composite is unresolvable.
- Consumes: `composite_contract_resolver.study_composite_contract`; `unified_contract_audit.unified_contract_findings`.

- [ ] **Step 1: Write failing tests** (monkeypatch the resolver to inject a known `ProcessContract`, so these are deterministic and need no workspace):
```python
def test_reconcile_flags_declared_mismatch(monkeypatch):
    # study declares outputs.pth_out: float; injected composite contract lacks it → 1 error finding.
def test_reconcile_silent_when_faces_agree(monkeypatch):
    # injected composite face == declared face → [].
def test_reconcile_abstains_without_declared_face(monkeypatch):
    # study has no contract.face → [] (resolver not even required).
def test_reconcile_abstains_when_composite_unresolvable(monkeypatch):
    # resolver returns (None, None) → [].
```
- [ ] **Step 2: Run tests, verify fail.**
- [ ] **Step 3: Implement** `reconcile_study_contract`: early-return `[]` if `study_spec["contract"]["face"]` absent; `(contract, core) = study_composite_contract(...)`; if `contract is None` return `[]`; else `unified_contract_findings(contract, study_face, core)`.
- [ ] **Step 4: Run tests, verify pass.**
- [ ] **Step 5: Commit.** `feat(contract): reconcile study contract.face against composite (report-time)`

---

### Task 3: Surface in `report_linter`

**Files:**
- Modify: `viva_superpowers/report_linter.py`
- Test: `tests/test_report_linter.py` (or the report-linter test module) — add cases

**Interfaces:**
- Consumes: `study_contract_lint.reconcile_study_contract`; `_LintContext.ws_root`; the study spec on the context.
- Produces: a check `_check_contract_face_reconciliation(ctx)` registered in the file's check registry, emitting one error-level `LintFinding` per reconcile finding (reuse the file's finding constructor + `check`/`override_key` conventions).

- [ ] **Step 1: Recon the registry.** Read how `report_linter` registers checks (`_CHECK_FUNCTIONS` / `CHECKS`), the `LintFinding` constructor, and how a check reads the study spec + `ctx.ws_root`. Mirror an existing error-level check.
- [ ] **Step 2: Write failing tests.** A study (fixture/dict) declaring a `contract.face` that disagrees with a monkeypatched `reconcile_study_contract` → the lint surfaces an error finding with the expected `check` slug; a study with no face / agreeing face → none. (Monkeypatch `reconcile_study_contract` to avoid building a real composite in the linter test.)
- [ ] **Step 3: Run tests, verify fail.**
- [ ] **Step 4: Implement** `_check_contract_face_reconciliation(ctx)`: call `reconcile_study_contract(ctx.spec, ctx.ws_root)`; map each finding to a `LintFinding(severity error, check "contract-face", ...)`; register in the check registry. Best-effort (wrap so a resolver error never breaks the lint run).
- [ ] **Step 5: Run tests + the existing report_linter suite, verify pass.** `pytest tests/ -k "report_linter or contract" -q`
- [ ] **Step 6: Commit.** `feat(report-linter): surface study↔composite contract-face disagreements`

---

## Final whole-branch review

Run `pytest -q` (full viva-superpowers suite); confirm no regression. Dispatch a fresh whole-branch review (most capable model) with this plan + spec + Review Focus. Fix Critical/Important in one TDD pass; ledger minors. Then `superpowers:finishing-a-development-branch` (push + PR, no auto-merge).
