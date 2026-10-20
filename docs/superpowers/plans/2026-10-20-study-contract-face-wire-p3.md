# Study Contract-Face ↔ Run-Observables Reconciliation (P3) — Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans (Native). Steps use checkbox (`- [ ]`).

**Goal:** Best-effort, report-time check that every port a study declares in `contract.face` is actually emitted by the study's latest run.

**Architecture:** viva-superpowers only, additive, best-effort. Resolve the latest run's emitted observables (`run_registry.latest_run` → `emitter_path` → `viva_emitters.RunReader.observables()`), presence-diff the declared face against them, surface gaps in `report_linter`. Not wired into the simulator-free `study_audit --gate`.

**Tech Stack:** Python 3.12; viva-superpowers on `origin/main` (`4462492`); viva_emitters RunReader; viva-genesis venv; pytest.

**Spec:** `docs/superpowers/specs/2026-10-20-study-contract-face-wire-design.md`

## Global Constraints

- **No AI attribution** in commits/PR.
- **viva-superpowers only.** Best-effort everywhere: no `contract.face`, no run, or an unreadable run → zero findings, never a crash, never a fabricated mismatch.
- **Presence-only:** run observables are untyped; check that a declared port is emitted, do not check type/units.
- **Worktree:** `~/code/viva-superpowers--contract-face-wire` (branch `feat/study-contract-face-wire`, off `origin/main`). Validate with `~/code/viva-genesis/.venv/bin/python` + `PYTHONPATH=<worktree>`; confirm `import viva_superpowers` resolves into the worktree.
- Tests in `tests/`.

## Review Focus

- No `contract.face` → abstain. → Task 2/3.
- No run / unreadable run → abstain, no crash. → Task 1/2.
- Declared port present in observables → no finding; absent → one warning finding. → Task 2.
- Both inputs and outputs checked against the one observable set. → Task 2.
- `latest_run`/`RunReader.open` failure never raises into the linter. → Task 1/3.

---

### Task 1: Latest-run observables resolver

**Files:**
- Create: `viva_superpowers/run_observables.py`
- Test: `tests/test_run_observables.py`

**Interfaces:**
- Produces: `study_run_observables(study_spec, ws_root) -> set[str] | None` — resolve the study dir (`WorkspacePaths(ws_root).study_dir(slug)`; slug from `study_spec["slug"]`/`["name"]`), `run_registry.latest_run(study_dir/"runs.db")`, take `emitter_path` (resolve relative to study_dir), `RunReader.open(emitter_path)`, return `set(reader.observables())`. `None` on any failure (no runs.db, no run row, no emitter_path, open/read error).
- Consumes: `viva_superpowers.run_registry.latest_run`; `viva_superpowers.workspace_paths.WorkspacePaths`; `viva_emitters.RunReader`.

- [ ] **Step 1: Write failing tests** (use the real og-00 run under viva-genesis — a committed canonical run — for the happy path; a tmp_path for the empty path):
```python
def test_observables_from_real_run():
    # ws_root = ~/code/viva-genesis; study slug og-00-vent-reactor-baseline
    obs = study_run_observables({"slug": "og-00-vent-reactor-baseline"}, "/Users/eranagmon/code/viva-genesis")
    assert obs and "temperature" in obs and "pressure" not in obs   # pressure declared but not emitted
def test_observables_none_when_no_run(tmp_path):
    assert study_run_observables({"slug": "nope"}, tmp_path) is None
```
- [ ] **Step 2: Run tests, verify fail.** `pytest tests/test_run_observables.py -v`
- [ ] **Step 3: Implement** `study_run_observables` per the Interfaces note; wrap the whole body so any failure → `None`.
- [ ] **Step 4: Run tests, verify pass.**
- [ ] **Step 5: Commit.** `feat(contract): latest-run observables resolver`

*Note:* if the committed og-00 run isn't present/readable in CI, downgrade the happy-path test to skip-when-absent and keep the None-path test as the gate; record a ruling.

---

### Task 2: `reconcile_study_observables`

**Files:**
- Create: `viva_superpowers/study_observable_lint.py`
- Test: `tests/test_study_observable_lint.py`

**Interfaces:**
- Produces: `observable_gaps(study_face: dict, observables) -> list[str]` (pure: a message per declared inputs/outputs port absent from `observables`); `reconcile_study_observables(study_spec, ws_root) -> list[dict]` — `[]` if no `contract.face`; else resolve observables (`study_run_observables`); `[]` if `None`; else `[{severity:"warning", check:"contract-observable", message} for m in observable_gaps(face, obs)]`.
- Consumes: `run_observables.study_run_observables`.

- [ ] **Step 1: Write failing tests** (monkeypatch `study_run_observables` for determinism — no real run needed):
```python
def test_gaps_flags_declared_but_unemitted():
    face = {"inputs": {"temperature": {}, "pressure": {}}, "outputs": {"formate": {}}}
    gaps = observable_gaps(face, {"temperature", "formate"})
    assert any("pressure" in g for g in gaps) and not any("temperature" in g for g in gaps)
def test_reconcile_silent_without_face(monkeypatch):
    assert reconcile_study_observables({"name": "x"}, "/ws") == []
def test_reconcile_silent_without_run(monkeypatch):
    monkeypatch.setattr(..., "study_run_observables", lambda *a, **k: None)
    assert reconcile_study_observables({"contract": {"face": {"outputs": {"m": {}}}}}, "/ws") == []
def test_reconcile_warns_on_gap(monkeypatch):
    monkeypatch.setattr(..., "study_run_observables", lambda *a, **k: {"temperature"})
    out = reconcile_study_observables({"contract": {"face": {"outputs": {"heat_flux": {}}}}}, "/ws")
    assert out and out[0]["check"] == "contract-observable" and out[0]["severity"] == "warning"
```
- [ ] **Step 2: Run tests, verify fail.**
- [ ] **Step 3: Implement** `observable_gaps` + `reconcile_study_observables`.
- [ ] **Step 4: Run tests, verify pass.**
- [ ] **Step 5: Commit.** `feat(contract): reconcile study contract.face against run observables`

---

### Task 3: Surface in `report_linter`

**Files:**
- Modify: `viva_superpowers/report_linter.py`
- Test: the report-linter test module — add cases

**Interfaces:**
- Consumes: `study_observable_lint.reconcile_study_observables`; `_LintContext.ws_root` + the study spec on the context.
- Produces: `_check_contract_observables(ctx)` registered in the file's check registry, emitting one **warning** `LintFinding` (check slug `contract-observable`) per gap; abstains otherwise; best-effort (a resolver error never breaks the lint run).

- [ ] **Step 1: Recon** the check registry (`_CHECK_FUNCTIONS`/`CHECKS`), the `LintFinding` constructor + `override_key`, and how a check reads the study spec + `ctx.ws_root`. Mirror an existing warning-level check.
- [ ] **Step 2: Write failing tests** (monkeypatch `reconcile_study_observables`): a study declaring a face with a gap → one warning finding with slug `contract-observable`; no face / no gap → none.
- [ ] **Step 3: Run tests, verify fail.**
- [ ] **Step 4: Implement** `_check_contract_observables(ctx)`; register it; wrap best-effort.
- [ ] **Step 5: Run tests + the existing report_linter suite, verify pass.** `pytest tests/ -k "report_linter or observable or contract" -q`
- [ ] **Step 6: Commit.** `feat(report-linter): surface declared-but-unemitted contract.face ports`

---

## Final whole-branch review

`pytest -q` (full suite; note any pre-existing failures by name). Dispatch a fresh whole-branch review (most capable model) with this plan + spec + Review Focus. Fix Critical/Important in one TDD pass; ledger minors. Then `superpowers:finishing-a-development-branch` (push + PR, no auto-merge).
