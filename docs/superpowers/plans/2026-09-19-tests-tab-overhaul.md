# Tests Tab Overhaul Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make every study's Tests tab describe each test and grade it against its band with a real measured value, verdict, and margin — and make "Run tests" drive that (grade the existing run; re-simulate only when there is no usable run). Prove it on all 8 viva-mGen studies.

**Architecture:** A workspace-pluggable **derived-scalar computer registry** consulted by `study_evaluator`'s native path when a test's `field` is not an emitted observable (piece A); the existing AST `formula:` path is reused unchanged for arithmetic over emitted observables (piece C). A new `POST /api/study-grade` grades a study's existing run on demand into the authoritative `runs[].outcomes` (the endpoint that is missing today); the frontend "Run tests" button calls it and chains to the existing baseline-run flow only when there is no usable run. The Tests tab is re-rendered as one report card per test over the now-populated surfaces — no new verdict schema.

**Tech Stack:** Python 3 · polars · FastAPI + pydantic (vivarium-workbench) · pytest · vanilla JS (no bundler) · ruamel.yaml (comment-preserving writes).

**Spec:** `viva-superpowers/docs/superpowers/specs/2026-09-19-tests-tab-overhaul-design.md`

## Global Constraints

- **No new verdict schema.** Consume existing surfaces only: `runs[].outcomes` (+ `axis`), `behavior_test_card/v1`, `test_diff.json`, `gate`. (Spec "Non-goals".)
- **Native-path change must be purely additive.** `viva_superpowers.study_evaluator` is re-exported by v2ecoli; the only new branch is "unresolved field → consult derived-scalar registry". An emitted `field`/`formula` must behave byte-identically to today. (Spec §1, Risks.)
- **Outcome authority:** authoritative outcomes are written only by `auto_evaluate.evaluate_on_run_completion`, `overwrite_authored=False` (never clobber human-authored outcomes). `compute_outcomes` writes only the parallel `computed_outcomes`. (Spec §3.)
- **Re-sim trigger:** only when there is *no* usable completed run. No timestamp/spec-drift detection. (Spec "Non-goals".)
- **Snapshot degradation:** the grade button and any live-only affordance must be hidden in the published read-only bundle. (Spec §4.)
- **Content style:** normal sentence case in any authored prose; no ALL-CAPS emphasis (viva-superpowers CLAUDE.md).
- **No AI attribution** in commits/PRs (user rule).
- **Worktrees:** one dedicated git worktree per repo, branched off `origin/main`. viva-superpowers worktree already exists at `~/code/viva-superpowers--tests-overhaul` (branch `feat/tests-tab-overhaul`). Create workbench + viva-mGen worktrees before their slices.
- **Re-lock:** before workbench slices see the new seam, re-lock workbench onto the new viva-superpowers rev (bump `viva-superpowers` only, not the `pbg-superpowers` shim).

---

## Slice 1 — viva-superpowers: derived-scalar seam (foundation)

**Worktree:** `~/code/viva-superpowers--tests-overhaul` (exists). Run `pytest -q` from there. Editable install already points at this package tree; if not, `pip install -e .` in the serving venv.

Reference code (read before starting):
- `viva_superpowers/study_evaluator.py`: `load_workspace_evaluators` (L250-281), `_workspace_evaluator_packages` (L207-247), `_WS_EVALUATOR_CACHE`/`clear_workspace_evaluator_cache` (L177-182), `evaluate_test` native path (L586-650), `_resolve_series` (L738), `_eval_expression`/`_eval_ast_node` (L835-919), `ObservableNotFound` (L288), `_agent`/`_code_outcome` (L657-672).
- Outcome dict shapes: `_agent(reason) -> {"evaluated_by":"agent","reason":...}`; `_code_outcome(result, measured_value, operator, detail) -> {"result","measured_value","evaluated_by":"code","operator","detail"}`; graded code outcomes also carry `outcome["axis"]`.
- Series shape (what `_resolve_series` returns): a polars `DataFrame` with columns `[generation, time, abs_time, value]`.

### Task 1.1: Derived-scalar registry loader

**Files:**
- Modify: `viva_superpowers/study_evaluator.py` (add loader + cache near `load_workspace_evaluators`, ~L177-281)
- Test: `tests/test_derived_scalar_registry.py` (create)

**Interfaces:**
- Produces: `load_workspace_derived_scalars(ws_root) -> dict[str, Callable]` where each value has signature `fn(reader, test, ws_root) -> float`. Hook name in a workspace package: `register_derived_scalars(reg: dict) -> None`. Cache cleared by the existing `clear_workspace_evaluator_cache()`.

- [ ] **Step 1: Write the failing test.** Create `tests/test_derived_scalar_registry.py`:

```python
import sys
import textwrap
from pathlib import Path

import viva_superpowers.study_evaluator as se


def _make_ws(tmp_path: Path, pkg: str, body: str) -> Path:
    (tmp_path / "workspace.yaml").write_text(f"name: {pkg}\n", encoding="utf-8")
    p = tmp_path / f"viva_{pkg}"
    p.mkdir()
    (p / "__init__.py").write_text("", encoding="utf-8")
    (p / "evaluators.py").write_text(textwrap.dedent(body), encoding="utf-8")
    return tmp_path


def test_loads_register_derived_scalars(tmp_path):
    se.clear_workspace_evaluator_cache()
    ws = _make_ws(tmp_path, "demo", """
        def register_derived_scalars(reg):
            reg["my_scalar"] = lambda reader, test, ws_root: 1.0
    """)
    try:
        reg = se.load_workspace_derived_scalars(ws)
        assert "my_scalar" in reg
        assert reg["my_scalar"](None, {}, ws) == 1.0
    finally:
        sys.path[:] = [p for p in sys.path if p != str(ws.resolve())]
        se.clear_workspace_evaluator_cache()


def test_missing_hook_returns_empty(tmp_path):
    se.clear_workspace_evaluator_cache()
    ws = _make_ws(tmp_path, "empty", "x = 1\n")  # no register_derived_scalars
    reg = se.load_workspace_derived_scalars(ws)
    assert reg == {}


def test_broken_hook_is_skipped(tmp_path):
    se.clear_workspace_evaluator_cache()
    ws = _make_ws(tmp_path, "broken", """
        def register_derived_scalars(reg):
            raise RuntimeError("boom")
    """)
    assert se.load_workspace_derived_scalars(ws) == {}


def test_none_ws_root_returns_empty():
    assert se.load_workspace_derived_scalars(None) == {}
```

- [ ] **Step 2: Run test to verify it fails.**

Run: `pytest tests/test_derived_scalar_registry.py -q`
Expected: FAIL — `AttributeError: module ... has no attribute 'load_workspace_derived_scalars'`.

- [ ] **Step 3: Implement the loader.** In `study_evaluator.py`, add a sibling cache + loader modeled exactly on `load_workspace_evaluators` (reuse `_workspace_evaluator_packages`). Place after `load_workspace_evaluators` (~L282). Make `clear_workspace_evaluator_cache` clear both caches.

```python
_WS_DERIVED_SCALAR_CACHE: dict[str, dict[str, Callable]] = {}


def load_workspace_derived_scalars(ws_root: Any) -> dict[str, Callable]:
    """Import the workspace's ``<pkg>.evaluators`` hook and collect derived-scalar
    computers registered via ``register_derived_scalars(reg)``.

    Returns a ``{field_name: fn}`` dict where ``fn(reader, test, ws_root) -> float``.
    Empty if ws_root is None or no hook is present. A hook that raises is skipped
    (a broken workspace hook must never crash evaluation). Cached per ws_root.
    """
    import sys
    from pathlib import Path
    if ws_root is None:
        return {}
    key = str(Path(ws_root).resolve())
    if key in _WS_DERIVED_SCALAR_CACHE:
        return _WS_DERIVED_SCALAR_CACHE[key]
    registry: dict[str, Callable] = {}
    if key not in sys.path:
        sys.path.insert(0, key)
    for pkg in _workspace_evaluator_packages(ws_root):
        try:
            mod = __import__(f"{pkg}.evaluators", fromlist=["register_derived_scalars"])
            hook = getattr(mod, "register_derived_scalars", None)
            if callable(hook):
                hook(registry)
        except Exception:  # noqa: BLE001 — never let a workspace hook break evaluation
            continue
    _WS_DERIVED_SCALAR_CACHE[key] = registry
    return registry
```

And extend the existing cache-clear (L180-182):

```python
def clear_workspace_evaluator_cache() -> None:
    """Drop the per-workspace evaluator + derived-scalar caches."""
    _WS_EVALUATOR_CACHE.clear()
    _WS_DERIVED_SCALAR_CACHE.clear()
```

- [ ] **Step 4: Run test to verify it passes.**

Run: `pytest tests/test_derived_scalar_registry.py -q`
Expected: PASS (4 passed).

- [ ] **Step 5: Commit.**

```bash
git add viva_superpowers/study_evaluator.py tests/test_derived_scalar_registry.py
git commit -m "feat(evaluator): workspace derived-scalar computer registry loader"
```

### Task 1.2: Native-path fallback to the derived-scalar registry

**Files:**
- Modify: `viva_superpowers/study_evaluator.py` — `evaluate_test` step 7 (L620-626); add `_scalar_series` helper.
- Test: `tests/test_derived_scalar_eval.py` (create)

**Interfaces:**
- Consumes: `load_workspace_derived_scalars` (Task 1.1); `_resolve_series`, `_apply_window`, `_apply_op`, `_grade_axis_from_outcome`, `_agent`, `ObservableNotFound`.
- Produces: `_scalar_series(value: float) -> pl.DataFrame` (columns `[generation, time, abs_time, value]`, one row). Behavior: when a native test's `field` is not an emitted observable but a workspace derived-scalar computer is registered under that field name, the computer's scalar is graded through the normal pipeline and returns a `code` outcome with `measured_value`, `result`, and `axis`.

- [ ] **Step 1: Write the failing test.** Create `tests/test_derived_scalar_eval.py`. Uses a fake reader that only knows one emitted observable, and a monkeypatched registry so the test needs no on-disk workspace:

```python
import polars as pl
import pytest

import viva_superpowers.study_evaluator as se


class FakeReader:
    """Knows only the observables in `series_map`; everything else 404s."""
    def __init__(self, series_map):
        self._m = series_map

    def series(self, token):
        if token in self._m:
            return self._m[token]
        raise KeyError(token)

    def select(self, sel):  # never used in these tests
        raise KeyError(sel)


def _flat(value):
    return pl.DataFrame({
        "generation": [1], "time": [0.0], "abs_time": [0.0], "value": [value],
    })


def test_derived_scalar_via_registry(monkeypatch):
    # field is NOT emitted; a workspace computer supplies it.
    monkeypatch.setattr(
        se, "load_workspace_derived_scalars",
        lambda ws_root: {"growth_is_monotonic": lambda r, t, w: 1.0},
    )
    reader = FakeReader({})  # no emitted observables
    test = {
        "name": "growth-monotonic",
        "measure": {"kind": "derived_scalar", "field": "growth_is_monotonic"},
        "pass_if": {"op": "range", "low": 1.0, "high": 1.0},
    }
    out = se.evaluate_test(test, reader, ws_root="/tmp/ws")
    assert out["evaluated_by"] == "code"
    assert out["result"] == "PASS"
    assert out["measured_value"] == 1.0
    assert "axis" in out


def test_unresolved_field_no_computer_is_agent(monkeypatch):
    monkeypatch.setattr(se, "load_workspace_derived_scalars", lambda ws_root: {})
    reader = FakeReader({})
    test = {
        "name": "x",
        "measure": {"kind": "derived_scalar", "field": "not_emitted"},
        "pass_if": {"op": "range", "low": 1.0, "high": 1.0},
    }
    out = se.evaluate_test(test, reader, ws_root="/tmp/ws")
    assert out["evaluated_by"] == "agent"


def test_emitted_field_ignores_registry(monkeypatch):
    # Regression: an emitted observable must NOT consult the registry.
    called = {"n": 0}
    def _reg(ws_root):
        called["n"] += 1
        return {}
    monkeypatch.setattr(se, "load_workspace_derived_scalars", _reg)
    reader = FakeReader({"cell_mass": _flat(2.0)})
    test = {
        "name": "mass",
        "measure": {"kind": "derived_scalar", "field": "cell_mass"},
        "pass_if": {"op": "range", "low": 1.0, "high": 3.0},
    }
    out = se.evaluate_test(test, reader, ws_root="/tmp/ws")
    assert out["evaluated_by"] == "code"
    assert out["result"] == "PASS"
    assert called["n"] == 0  # registry never consulted for an emitted field
```

- [ ] **Step 2: Run test to verify it fails.**

Run: `pytest tests/test_derived_scalar_eval.py -q`
Expected: FAIL — the first test returns an `agent` bucket (no fallback yet); `test_emitted_field_ignores_registry` may already pass.

- [ ] **Step 3: Implement `_scalar_series` + the fallback branch.** Add the helper next to `_resolve_series`:

```python
def _scalar_series(value: float) -> pl.DataFrame:
    """Wrap a single computed scalar as the flat series shape the pipeline expects.

    One row so the default ``full_lineage_from_gen_0`` window keeps it and
    ``_apply_op`` reduces it exactly as for an emitted observable.
    """
    return pl.DataFrame({
        "generation": [1], "time": [0.0], "abs_time": [0.0], "value": [float(value)],
    })
```

Replace `evaluate_test` step 7 (the `try: series = _resolve_series(path, reader)` block at L620-626) with a resolution ladder that falls back to the registry on `ObservableNotFound`:

```python
    # 7. Resolve the observable series — falling back to a workspace-registered
    #    derived-scalar computer when the field is not an emitted observable.
    try:
        series = _resolve_series(path, reader)
    except ObservableNotFound as exc:
        fn = load_workspace_derived_scalars(ws_root).get(path)
        if fn is None:
            return _agent(str(exc))
        try:
            series = _scalar_series(fn(reader, test, ws_root))
        except Exception as exc2:  # noqa: BLE001
            return _agent(f"derived-scalar computer {path!r} error: {exc2}")
    except Exception as exc:  # noqa: BLE001
        return _agent(f"series resolution error: {exc}")
```

Note: `path` is `measure.path or measure.field or measure.formula` (L609), so the registry key is the declared `field`. A `formula:` that resolves via `_eval_expression` never reaches the fallback (piece C, already working).

- [ ] **Step 4: Run test to verify it passes.**

Run: `pytest tests/test_derived_scalar_eval.py -q`
Expected: PASS (3 passed).

- [ ] **Step 5: Run the full evaluator suite (no regressions).**

Run: `pytest tests/ -q -k "evaluator or evaluate or derived or study_eval"`
Expected: PASS (existing evaluator tests unchanged).

- [ ] **Step 6: Commit.**

```bash
git add viva_superpowers/study_evaluator.py tests/test_derived_scalar_eval.py
git commit -m "feat(evaluator): native derived_scalar falls back to workspace computer registry"
```

### Task 1.3: Confirm + test the existing `formula:` path (piece C)

**Files:**
- Test: `tests/test_formula_measure.py` (create). No production change unless Step 4 fails.

**Interfaces:**
- Consumes: `evaluate_test`, `_resolve_series`/`_eval_expression` (existing).
- Produces: proof that `measure.formula` over emitted observables grades without any new code.

- [ ] **Step 1: Write the test.** Create `tests/test_formula_measure.py`:

```python
import polars as pl

import viva_superpowers.study_evaluator as se


class FakeReader:
    def __init__(self, series_map):
        self._m = series_map

    def series(self, token):
        if token in self._m:
            return self._m[token]
        raise KeyError(token)

    def select(self, sel):
        raise KeyError(sel)


def _series(values):
    n = len(values)
    return pl.DataFrame({
        "generation": [1] * n,
        "time": [float(i) for i in range(n)],
        "abs_time": [float(i) for i in range(n)],
        "value": [float(v) for v in values],
    })


def test_formula_ratio_of_observables_grades():
    reader = FakeReader({
        "cell_mass": _series([2.0, 4.0]),
        "cell_mass_initial": _series([1.0, 2.0]),
    })
    test = {
        "name": "mass-doubles",
        "measure": {"kind": "derived_scalar",
                    "formula": "cell_mass / cell_mass_initial"},
        "pass_if": {"op": "range", "low": 1.9, "high": 2.1},
    }
    out = se.evaluate_test(test, reader, ws_root=None)
    assert out["evaluated_by"] == "code"
    assert out["result"] == "PASS"
```

- [ ] **Step 2: Run it.**

Run: `pytest tests/test_formula_measure.py -q`
Expected: PASS (proves piece C already works). If it FAILS, read the error:
  - `unknown variable`/tokenization issue → the observable names in the formula must match `_extract_observable_tokens`; adjust the test's observable names.
  - unsupported operator (only `**`/`%` are missing) → widen `_eval_ast_node` (L899-911) to add `ast.Pow`→`left ** right` and `ast.Mod`→`left % right`, then re-run. Only do this if a real study needs it.

- [ ] **Step 3: Commit.**

```bash
git add tests/test_formula_measure.py
git commit -m "test(evaluator): confirm formula: measure grades over emitted observables"
```

### Task 1.4: Push branch, open PR

- [ ] **Step 1: Verify provenance.** `git log --oneline origin/main..HEAD` shows only your 3 commits; `git branch --show-current` is `feat/tests-tab-overhaul`.
- [ ] **Step 2:** `git push -u origin feat/tests-tab-overhaul`
- [ ] **Step 3:** `gh pr create --title "Derived-scalar computer registry for study tests" --body "<summary + link to spec>"` (no AI attribution).

---

## Slice 2 — viva-mGen: prove the seam on 8 studies

**Worktree:** create it before starting.

```bash
git -C ~/code/viva-mGen fetch origin main
git -C ~/code/viva-mGen worktree add ~/code/viva-mGen--tests-overhaul -b feat/tests-tab-overhaul origin/main
cd ~/code/viva-mGen--tests-overhaul
```

**PYTHONPATH gotcha:** viva-superpowers must be importable at the Slice-1 rev. Either `pip install -e ~/code/viva-superpowers--tests-overhaul` into the workspace venv, or verify `python -c "import viva_superpowers; print(viva_superpowers.__file__)"` points at the Slice-1 tree. Run the workspace against the worktree, not the canonical checkout.

Reference: `viva_mgen/` has no `evaluators.py` today (that is the defect). Each study's `study.yaml` `behavior_tests[].measure.field` names the derived scalars to compute. Run stores are under `workspace/studies/<slug>/results/*.zarr`. The `reader` passed to a computer is a `RunReader` with `reader.series(token) -> pl.DataFrame[generation,time,abs_time,value]` and `reader.select(dict)`; study run configs (variant params, e.g. the kcat sweep values) come from the study spec — read them via the `test`/`ws_root` args as needed.

### Task 2.1: Enumerate the derived-scalar fields

**Files:** none (investigation task).

- [ ] **Step 1:** For each of the 8 studies, list the distinct `measure.field` values that are NOT emitted observables:

```bash
cd ~/code/viva-mGen--tests-overhaul
for d in workspace/studies/*/; do
  echo "== $d =="
  grep -E "^\s+(field|formula):" "$d/study.yaml" 2>/dev/null | sort -u
done
```

- [ ] **Step 2:** For each field, decide: is it a plain emitted observable (leave alone), an arithmetic ratio of observables (convert to `formula:` — piece C, no code), or a genuinely derived scalar (needs a computer — piece A)? Record the list; it drives Task 2.2. Do **not** rename fields that already resolve.

### Task 2.2: Author `viva_mgen/evaluators.py`

**Files:**
- Create: `viva_mgen/evaluators.py`
- Test: `tests/test_evaluators.py` (create; use a small synthetic reader, not the full zarr)

**Interfaces:**
- Produces: `register_derived_scalars(reg)` registering `fn(reader, test, ws_root) -> float` for each derived field from Task 2.1. Booleans return `1.0`/`0.0`.

- [ ] **Step 1: Write a failing unit test** for one representative computer with a synthetic reader. Example for `growth_is_monotonic_in_kcat` (adapt to the real sweep-reading approach discovered in 2.1):

```python
import polars as pl
from viva_mgen.evaluators import growth_is_monotonic_in_kcat  # or via the registry


class SweepReader:
    """Minimal stand-in exposing the growth series the computer reduces."""
    def __init__(self, growth_by_variant):
        self.growth_by_variant = growth_by_variant
    # ... shape this to match how the real computer reads the store (from 2.1)


def test_monotonic_true_for_increasing():
    r = SweepReader([0.1, 0.3, 0.6, 0.9])
    assert growth_is_monotonic_in_kcat(r, {}, None) == 1.0


def test_monotonic_false_for_dip():
    r = SweepReader([0.1, 0.6, 0.3, 0.9])
    assert growth_is_monotonic_in_kcat(r, {}, None) == 0.0
```

- [ ] **Step 2:** Run it — Expected: FAIL (`ImportError`, module/function absent).

- [ ] **Step 3: Implement `viva_mgen/evaluators.py`.** Write one computer per derived field. Register them:

```python
def register_derived_scalars(reg):
    reg["growth_is_monotonic_in_kcat"] = growth_is_monotonic_in_kcat
    reg["growth_saturates_at_wt"] = growth_saturates_at_wt
    reg["growth_is_sigmoidal"] = growth_is_sigmoidal
    reg["growth_dynamic_range"] = growth_dynamic_range
    reg["growth_at_max_kcat_near_wt"] = growth_at_max_kcat_near_wt
    # ... fig1-fig6 fields from Task 2.1
```

Each computer reads the run store via `reader` (and sweep config via `test`/`ws_root` as 2.1 determined) and returns a scalar. Keep reductions simple and documented; sentence-case any docstrings.

- [ ] **Step 4:** Run the unit test — Expected: PASS.

- [ ] **Step 5: End-to-end grade one study** against its real run:

Run: `cd ~/code/viva-mGen--tests-overhaul && viva-compute-outcomes fig7-kinetic-parameters` (or the equivalent `python -m viva_superpowers.study_evaluator` CLI / the workbench `/api/study-grade` once Slice 3 lands).
Expected: `fig7`'s primary tests report non-null `measured_value` and real PASS/FAIL — no `agent`/`ungraded` buckets for declared primary tests.

- [ ] **Step 6: Commit.**

```bash
git add viva_mgen/evaluators.py tests/test_evaluators.py
git commit -m "feat(evaluators): derived-scalar computers for fig1-fig7 + parca studies"
```

### Task 2.3: Grade all 8 studies, verify, PR

- [ ] **Step 1:** Grade each study; confirm every declared primary test grades (no `null` measured values for declared primaries). Fix any computer that still buckets to `agent`.
- [ ] **Step 2:** Verify provenance (`git log --oneline origin/main..HEAD` = only your commits), push, open PR (no AI attribution).

---

## Slice 3 — vivarium-workbench: `POST /api/study-grade`

**Worktree:** create it, then re-lock onto the Slice-1 viva-superpowers rev.

```bash
git -C ~/code/vivarium-workbench fetch origin main
git -C ~/code/vivarium-workbench worktree add ~/code/vivarium-workbench--tests-overhaul -b feat/tests-tab-overhaul origin/main
cd ~/code/vivarium-workbench--tests-overhaul
# re-lock onto the new seam (bump viva-superpowers ONLY, not the pbg-superpowers shim):
uv lock --upgrade-package viva-superpowers
pip install -e .   # into the serving venv
```

Reference code:
- `lib/auto_evaluate.py`: `evaluate_on_run_completion(study_dir, run_id, *, ws_root, test_runner=None, overwrite_authored=False)` (L254-352); `_evaluator_test_runner` store resolution (L152-174).
- `lib/behavior_test_card.py`: `write_behavior_test_card(study_dir)` (L298-339).
- `lib/study_runs.py`: `_run_post_run_flush` (L135-305) — stage 7 auto_evaluate at L291-295; how it resolves the latest run + store.
- `lib/study_tests.py`: `run_study_tests` (L51-135), `_run_spine_tests` (L138-225) — the pytest path (leave intact).
- Route + model patterns: `api/app.py` `study_tests_run` route (L6404-6425); `lib/models.py` `StudyTestsRunRequest` (~L2984); `lib/test_run_views.py` `study_tests_run` (L29-57).
- `lib/workspace_paths.py` for `studies/<slug>` resolution; `_csrf_ok()` guard convention.

### Task 3.1: `grade_study` lib function

**Files:**
- Create: `lib/study_grade.py`
- Test: `tests/test_study_grade.py` (create)

**Interfaces:**
- Consumes: `auto_evaluate.evaluate_on_run_completion`, `behavior_test_card.write_behavior_test_card`, `WorkspacePaths`.
- Produces: `grade_study(ws_root: Path, slug: str) -> tuple[dict, int]` returning `({"graded": True, "outcome_rollup": {...}, "gate": {...}, "run_id": "..."}, 200)` when a usable completed run exists, `({"graded": False, "reason": "no_run"}, 200)` when none, `({"error": "study not found: <slug>"}, 404)` when the study is absent. Mirrors the `(body, status)` shape of `test_run_views.study_tests_run`.

- [ ] **Step 1: Write failing tests** using a fixture workspace. Copy an existing study-with-run fixture pattern from `tests/_fixtures/` and `tests/conftest.py` (`dashboard_client`). Two cases:

```python
# tests/test_study_grade.py
from pathlib import Path
from vivarium_workbench.lib import study_grade


def test_grade_study_with_completed_run(ws_with_completed_run):
    body, status = study_grade.grade_study(ws_with_completed_run, "demo-study")
    assert status == 200
    assert body["graded"] is True
    assert "outcome_rollup" in body


def test_grade_study_no_run(ws_without_run):
    body, status = study_grade.grade_study(ws_without_run, "demo-study")
    assert status == 200
    assert body == {"graded": False, "reason": "no_run"}


def test_grade_missing_study(ws_without_run):
    body, status = study_grade.grade_study(ws_without_run, "nope")
    assert status == 404
```

(Fixtures `ws_with_completed_run`/`ws_without_run` follow the existing `_fixtures` conventions; reuse a study fixture that already has a `runs[]` + store, and one that has tests but no run.)

- [ ] **Step 2:** Run — Expected: FAIL (`ModuleNotFoundError: study_grade`).

- [ ] **Step 3: Implement `lib/study_grade.py`:**

```python
"""On-demand grading of a study's declared behavior tests against its latest
completed run — the fast 'Run tests' path (no re-simulation).

Writes the authoritative runs[].outcomes via auto_evaluate (overwrite_authored
=False) and refreshes the behavior-test card. Returns (body, status).
"""
from __future__ import annotations

from pathlib import Path

from . import auto_evaluate, behavior_test_card
from .workspace_paths import WorkspacePaths


def _latest_completed_run_id(spec: dict) -> str | None:
    for r in reversed(spec.get("runs") or []):
        if (r or {}).get("status") == "completed":
            return r.get("run_id") or r.get("name")
    return None


def grade_study(ws_root: Path, slug: str) -> tuple[dict, int]:
    ws_root = Path(ws_root)
    study_dir = WorkspacePaths.load(ws_root).studies / slug
    spec_path = study_dir / "study.yaml"
    if not spec_path.exists():
        return {"error": f"study not found: {slug}"}, 404

    import yaml
    spec = yaml.safe_load(spec_path.read_text(encoding="utf-8")) or {}
    run_id = _latest_completed_run_id(spec)
    if not run_id:
        return {"graded": False, "reason": "no_run"}, 200

    result = auto_evaluate.evaluate_on_run_completion(
        study_dir, run_id, ws_root=ws_root, overwrite_authored=False,
    )
    # If the store could not be resolved, treat as no usable run.
    if isinstance(result, dict) and result.get("status") in {"store_unresolved", "no_tests", "evaluator_unavailable"}:
        return {"graded": False, "reason": result.get("status")}, 200

    behavior_test_card.write_behavior_test_card(study_dir)

    # Re-read the enriched spec surfaces the tab consumes.
    spec2 = yaml.safe_load(spec_path.read_text(encoding="utf-8")) or {}
    rollup = _rollup(spec2)
    return {"graded": True, "outcome_rollup": rollup, "run_id": run_id}, 200


def _rollup(spec: dict) -> dict:
    passed = failed = skipped = 0
    for r in spec.get("runs") or []:
        for o in (r.get("outcomes") or {}).values():
            res = (o or {}).get("result")
            if res == "PASS":
                passed += 1
            elif res == "FAIL":
                failed += 1
            elif res == "SKIP":
                skipped += 1
    total = passed + failed + skipped
    return {"PASS": passed, "FAIL": failed, "SKIP": skipped, "total": total}
```

(Verify `evaluate_on_run_completion`'s exact return value while implementing — the status-enum guard above matches the L294 enum in `auto_evaluate.py`; adjust field names to the real return.)

- [ ] **Step 4:** Run — Expected: PASS.

- [ ] **Step 5: Commit.**

```bash
git add vivarium_workbench/lib/study_grade.py tests/test_study_grade.py
git commit -m "feat(study-grade): on-demand behavior-test grading of a study's latest run"
```

### Task 3.2: `POST /api/study-grade` route + model

**Files:**
- Modify: `lib/models.py` (add `StudyGradeRequest`)
- Modify: `api/app.py` (add route)
- Test: `tests/test_study_grade_endpoint.py` (create)

**Interfaces:**
- Consumes: `study_grade.grade_study` (Task 3.1).
- Produces: `POST /api/study-grade` body `{ "study": "<slug>" }` → JSON `{graded, outcome_rollup?, gate?, run_id?, reason?}`; 404 on missing study. CSRF-guarded.

- [ ] **Step 1: Write the failing endpoint test** using the `dashboard_client` fixture (mirror `tests/test_study_tests_endpoint.py`):

```python
def test_study_grade_endpoint(dashboard_client):
    r = dashboard_client.post("/api/study-grade", json={"study": "demo-study"})
    assert r.status_code == 200
    assert "graded" in r.json()
```

- [ ] **Step 2:** Run — Expected: FAIL (404 route missing).

- [ ] **Step 3: Implement.** In `lib/models.py`, next to `StudyTestsRunRequest`:

```python
class StudyGradeRequest(BaseModel):
    """POST /api/study-grade request body — ``{"study"}``."""
    study: str
```

In `api/app.py`, next to `study_tests_run` (L6404):

```python
@app.post("/api/study-grade", tags=["Studies"],
          summary="Grade a study's behavior tests against its latest run (no re-sim)")
def study_grade(req: StudyGradeRequest, ws: Path = Depends(get_workspace)) -> JSONResponse:
    """Grade the declared behavior tests against the study's latest completed
    run and return the refreshed rollup. Body: ``{"study"}``. Returns
    ``{graded: false, reason: "no_run"}`` when there is no usable run."""
    from ..lib import study_grade as _study_grade
    body, status = _study_grade.grade_study(ws, req.study)
    return JSONResponse(status_code=status, content=body)
```

(Import `StudyGradeRequest` where the other request models are imported; match the file's existing import style.)

- [ ] **Step 4:** Run — Expected: PASS.

- [ ] **Step 5:** Run `pytest tests/test_study_grade_endpoint.py tests/test_study_grade.py -q` — Expected: PASS.

- [ ] **Step 6: Commit.**

```bash
git add vivarium_workbench/lib/models.py vivarium_workbench/api/app.py tests/test_study_grade_endpoint.py
git commit -m "feat(api): POST /api/study-grade route"
```

---

## Slice 4 — vivarium-workbench: rewire "Run tests" + redesign the tab

**Worktree:** same as Slice 3 (`~/code/vivarium-workbench--tests-overhaul`).

Reference: `static/study-detail.js` — `runStudyTests()` (L4001-4024), `_dispatchCurrentSpecBaseline` (L1970-1976), `_pollChainProgress` (L2547-2559), `loadTestsTab` (L3730+), `_renderTestsGateSummary` (L3706), `_renderComputedOutcomeRow` (L3890), `_fillReportCardModules`, `escapeHtmlForTests` (L3959). Data surfaces on the study spec: `spec.behavior_tests[]`, `spec.runs[].outcomes[name]` (+ `.axis`), `spec.outcome_rollup`, `spec.gate`, `spec.test_diff.per[]`. Frontend has no unit harness — verify by loading the workbench against viva-mGen.

### Task 4.1: Rewire the "Run tests" button

**Files:** Modify `static/study-detail.js` — `runStudyTests()`.

- [ ] **Step 1: Replace `runStudyTests()`** to call `/api/study-grade` and chain to the baseline flow only on `no_run`:

```javascript
function runStudyTests() {
  var btn = document.getElementById('run-tests-btn');
  if (!btn) return;
  btn.disabled = true;
  btn.textContent = 'Grading…';
  fetch('/api/study-grade', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({study: studyName()}),
  }).then(function(resp) {
    return resp.json().then(function(d) { return {status: resp.status, body: d}; });
  }).then(function(r) {
    if (r.status !== 200) { alert('Grade failed: ' + (r.body && r.body.error || r.status)); return; }
    if (r.body.graded) { _reloadStudyAndTests(); return; }
    // No usable run → run the baseline (its flush auto-evaluates), then reload.
    btn.textContent = 'Simulating…';
    _dispatchCurrentSpecBaseline();   // existing baseline-run + progress-poll flow
    // _reloadStudyAndTests() is triggered by the baseline flow's completion handler.
  }).catch(function(err) {
    alert('Grade error: ' + err);
  }).then(function() {
    btn.disabled = false;
    if (btn.textContent === 'Grading…') btn.textContent = 'Run tests';
  });
}
```

Add a small `_reloadStudyAndTests()` that re-fetches `GET /api/study/{slug}` and calls `loadTestsTab(spec)` (reuse the page's existing study-reload path if one exists; otherwise fetch + re-render). Ensure the baseline flow's completion handler (`_pollChainProgress` terminal state) calls `_reloadStudyAndTests()` when the run was initiated from the Tests tab (guard with a module flag so it only fires for that case).

- [ ] **Step 2: Manual verify** against viva-mGen: with a completed run present, clicking Run tests grades and repopulates without re-simulating; on a study with no run it kicks off the baseline then repopulates.

- [ ] **Step 3: Commit.**

```bash
git add vivarium_workbench/static/study-detail.js
git commit -m "feat(tests-tab): Run tests grades the latest run; re-sims only when none exists"
```

### Task 4.2: Redesign the per-test report card

**Files:** Modify `static/study-detail.js` — add `_renderTestReportCard`, restructure `loadTestsTab` to use it; keep `_renderTestsGateSummary` and the gate badge.

- [ ] **Step 1: Add `_renderTestReportCard(test, outcome, diff)`** rendering, per test, top-to-bottom: header (name · classification badge · verdict chip from `outcome.axis.verdict` · PASS/FAIL); "what it checks" (`test.description`); band + measured (`pass_if` human-readable + `outcome.measured_value`); margin bar (`outcome.axis.meter`, boundary 0.5 — reuse the existing margin-bar styling); evidence (`pass_if.provenance.note` + `cites`/`calibration_anchor`); since-last-run badge (`diff.change` + `margin_delta`); footer (run link + collapsed Assertion). Escape all text via `escapeHtmlForTests`. Group primary tests first.

- [ ] **Step 2: Restructure `loadTestsTab`** to build the per-test list from `spec.behavior_tests` joined to the latest run's `outcomes[name]` and `spec.test_diff.per[]`, calling `_renderTestReportCard` per row. Retire the scattered `_renderComputedOutcomeRow` injection in favor of the unified card (or have the card subsume it). Keep the "N/M gates passed" strip and severity-gate badge. Add the study's `pipeline_gate.proceed_condition` + gate status near the header to tie Tests to the Decision.

- [ ] **Step 3: Snapshot degradation** — hide `#run-tests-btn` when the data source is the published bundle (match the existing Launch-button pattern in `data-source.js`).

- [ ] **Step 4: Manual verify** against all 8 viva-mGen studies in the running workbench: each declared test shows description, band, measured value, verdict, margin bar, evidence, and change badge; "N/M gates passed" and the gate badge reflect the graded outcomes; no "pending/inconclusive" for graded primaries.

- [ ] **Step 5: Run the workbench Python suite** (no backend regressions):

Run: `pytest tests/ -q -k "study or tests or render or spec"`
Expected: PASS.

- [ ] **Step 6: Commit.**

```bash
git add vivarium_workbench/static/study-detail.js
git commit -m "feat(tests-tab): redesign per-test report card over graded outcomes"
```

### Task 4.3: Push, PR, re-lock note

- [ ] **Step 1:** Verify provenance (only your commits), push `feat/tests-tab-overhaul`, open PR. In the PR body, note the viva-superpowers dependency bump (Slice 1) required for the seam.
- [ ] **Step 2:** After viva-superpowers Slice 1 merges, rebase/refresh the workbench lock onto the merged rev before merging Slice 3-4.

---

## Self-review (against the spec)

**Spec coverage:**
- §1 piece A (registry + native fallback) → Tasks 1.1, 1.2. ✓
- §1 piece C (formula reuse) → Task 1.3. ✓
- §2 proof case (viva_mgen/evaluators.py) → Slice 2. ✓
- §3 `/api/study-grade` (grade existing run, `no_run` signal, `overwrite_authored=False`) → Tasks 3.1, 3.2. ✓
- §4 rewire Run tests (grade → chain-to-baseline; snapshot hide) → Task 4.1, 4.2 Step 3. ✓
- §5 tab redesign (per-test report card over existing surfaces) → Task 4.2. ✓
- Non-goals (no new schema, no stale-provenance, keep pytest) → honored: Slice 3 reuses `behavior_test_card/v1`; `run_study_tests` untouched; re-sim only on `no_run`. ✓
- Risks (additive native path + regression test; workbench↔SP re-lock; formula scope; snapshot) → Task 1.2 Step 5 regression test; Slice 3 re-lock step; Task 1.3 operator note; Task 4.2 Step 3. ✓

**Placeholder scan:** Slice-2 computer bodies and the frontend render are intentionally spec'd as "implement per the reference + discovered store shape" because the exact per-study reductions (2.1) and the DOM structure depend on read-time investigation; every framework seam (signatures, endpoint, fallback branch) carries real code. No TBD/TODO left in the seam/endpoint tasks.

**Type consistency:** `load_workspace_derived_scalars` / `register_derived_scalars` / `fn(reader, test, ws_root) -> float` / `_scalar_series(value) -> pl.DataFrame` / `grade_study(ws_root, slug) -> (dict, int)` / `StudyGradeRequest{study}` used consistently across tasks.
