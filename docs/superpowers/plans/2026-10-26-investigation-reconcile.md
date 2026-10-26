# Investigation-reconcile capability — Implementation Plan (Part B)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task (user chose native inline execution). Steps use checkbox (`- [ ]`) syntax.

**Goal:** A reusable `/viva-investigation reconcile <inv>` capability that deterministically detects investigation drift after a structural edit (studies removed / added / merged) and guides the narrative rewrite.

**Architecture:** A new AI-free helper `viva_superpowers/investigation_reconcile.py` — `detect_drift()` (pure, no writes) + `apply_mechanical()` (structured drops via the comment-preserving ruamel writer) — mirroring the `finding_observations.py` deterministic-helper + agent-authoring split. Prose rewrites stay agent-authored (guided by a new `reconcile` section in the `viva-investigation` skill). No dashboard/AI writes.

**Tech Stack:** Python 3.11+, ruamel.yaml (comment-preserving), pytest. Builds on `investigation_import.investigation_members`, `investigation_canonicalize._ruamel`/`migrate_investigation_file`.

**Spec:** `../../../../spatio-flux--novel-sims/docs/superpowers/specs/2026-10-26-novel-sims-and-investigation-reconcile-design.md` (Part B). Read it alongside this plan.

## Global Constraints
- Worktree only: `~/code/viva-superpowers--inv-reconcile`, branch `feat/investigation-reconcile`, off `origin/main` (7d8b794). `study_narrative.py` is DELETED on main — do not reference it.
- No AI attribution; no auto-merge; squash-merge; verify-before-complete.
- Comment-preserving writes via `investigation_canonicalize._ruamel()` ONLY — never `study_io.dump_yaml` (strips the scaffold's TODO-comment narrative sections).
- Deterministic/AI-free: the helper detects + applies MECHANICAL structured drops; it never rewrites prose. Prose reconciliation is the agent's, via the skill checklist.
- Idempotent: a second `apply_mechanical` with the same drift → `applied=0`, no write (mirrors `finding_observations`).

## Review Focus
- **Membership read must union `members:` AND `studies:`** — `investigation_members()` reads `members`/acceptance_criteria/at_a_glance but NOT `studies:`; a pre-canonicalized investigation (like the dogfood target) uses `studies:`. Missing this → every member reads as "removed." Covered in Task 1 tests.
- **Prose name-matching false positives** — a removed slug that is a substring of a surviving slug/word must not over-match (word-boundary match; report, never auto-delete prose). Covered in Task 1 tests.
- **Missing narrative sections are not errors** — an investigation with no `at_a_glance`/`acceptance_criteria`/`glossary` yields those-checks-empty, not a crash. Covered in Task 1 tests.
- **Both `at_a_glance` shapes** — dict-with-`studies` and list-of-`{study,role}`. Covered in Task 1 tests.
- **apply_mechanical must preserve comments + untouched sections** — ruamel round-trip; a study.yaml-style narrative with `#` comments survives. Covered in Task 2 tests.

---

### Task 1: `detect_drift` (pure detector)

**Files:**
- Create: `viva_superpowers/investigation_reconcile.py`
- Test: `tests/test_investigation_reconcile.py`

**Interfaces — Produces:**
- `@dataclass DriftItem: kind: str; where: str; detail: str; suggested_action: str`
- `def detect_drift(ws_root, inv_slug: str) -> list[DriftItem]` — pure, no writes. Resolves the investigation dir (reuse the repo's investigation-path resolver), loads the yaml (`yaml.safe_load`), computes `declared = union(spec.get("members",[]), spec.get("studies",[]), investigation_members(inv_yaml))`, `on_disk = {study dirs under the investigation / flat studies/}`. Emits DriftItems:
  - `kind="member_missing_on_disk"` for declared−on_disk (a removed study still listed);
  - `kind="orphan_on_disk"` for on_disk−declared (an added study not listed);
  - `kind="prose_ref_to_removed"` — for each removed slug, a word-boundary scan of `executive.verdict`/`what_is_this`, `scientific_argument.evidence_for`/`evidence_against`/`key_figures` (incl. `studies/<slug>/…` paths), `biological_story` → one item per hit (`where`=dotted path, action="confirm+rewrite");
  - `kind="structured_ref_to_removed"` — removed slug in `at_a_glance` (both shapes), `acceptance_criteria[].study`, or any surviving study's `pipeline_gate.prerequisites`;
  - `kind="stale_rollup"` — `executive.verdict`/`verdict_status` names a removed study.

- [ ] **Step 1: failing tests** in `tests/test_investigation_reconcile.py` with tmp-dir fixtures:
```python
def test_detects_removed_member_listed_in_studies_key(tmp_path): ...   # uses `studies:` not `members:`
def test_detects_orphan_study_on_disk(tmp_path): ...
def test_prose_ref_to_removed_study_in_evidence_for(tmp_path): ...      # evidence_for free-text mentions removed slug
def test_prose_match_is_word_boundary_no_substring_false_positive(tmp_path): ...  # 'spatial' not matched inside 'spatial_growth_front' survivor
def test_missing_at_a_glance_and_acceptance_is_not_an_error(tmp_path): ...
def test_both_at_a_glance_shapes(tmp_path): ...
def test_clean_investigation_returns_no_drift(tmp_path): ...
```
- [ ] **Step 2: run, verify fail** — `pytest tests/test_investigation_reconcile.py -q` → fail (module/func missing).
- [ ] **Step 3: implement** `detect_drift` + `DriftItem`. Membership union includes `studies:`. Prose scan uses `re.search(r"\b"+re.escape(slug)+r"\b", text)` (+ the `studies/<slug>/` path form). Absent sections → skipped.
- [ ] **Step 4: run, verify pass.**
- [ ] **Step 5: commit** — `git commit -m "feat(reconcile): detect_drift — investigation drift detector after structural edits"`.

### Task 2: `apply_mechanical` (structured drops, comment-preserving)

**Files:** Modify `viva_superpowers/investigation_reconcile.py`; extend `tests/test_investigation_reconcile.py`.

**Interfaces — Produces:** `def apply_mechanical(ws_root, inv_slug, *, confirm=True) -> dict` — re-detects, then via `investigation_canonicalize._ruamel()` round-trip removes **structured** references to removed studies only: drop them from `members`/`studies` lists, `at_a_glance` (both shapes), `acceptance_criteria[]`, and surviving studies' `pipeline_gate.prerequisites`. Returns `{applied: int, skipped_prose: int}`. NEVER edits prose fields (those are the agent's). Idempotent (second call → `applied=0`, no write).

- [ ] **Step 1: failing tests** — `test_apply_drops_removed_from_members_and_at_a_glance`, `test_apply_prunes_dangling_prerequisite`, `test_apply_preserves_comments_and_prose`, `test_apply_is_idempotent`, `test_apply_leaves_prose_refs_for_the_agent` (prose hit count returned, not deleted).
- [ ] **Step 2: run, verify fail.**
- [ ] **Step 3: implement** via `_ruamel()`; comment-preserving; leaves prose untouched.
- [ ] **Step 4: run, verify pass** (incl. idempotence + comment preservation).
- [ ] **Step 5: commit** — `git commit -m "feat(reconcile): apply_mechanical — comment-preserving structured drops"`.

### Task 3: CLI entrypoint

**Files:** Modify `viva_superpowers/investigation_reconcile.py` (add `main(argv)` + `if __name__=="__main__"`).

- [ ] **Step 1: failing test** `test_cli_reports_drift_and_applies` — invoke `main(["--ws", str(tmp), "<inv>"])` prints a grouped report (exit 0); `main([..., "--apply"])` performs mechanical drops; `--json` emits the report as JSON.
- [ ] **Step 2–4:** RED → implement argparse (`--ws`, positional `<inv>`, `--apply`, `--json`) → GREEN.
- [ ] **Step 5: commit** — `feat(reconcile): CLI (python -m viva_superpowers.investigation_reconcile)`.

### Task 4: skill `reconcile` section

**Files:** Modify `skills/viva-investigation/SKILL.md`.

- [ ] Add a `#### reconcile <slug> [--apply]` subcommand section: when to run (after any add/remove/merge of member studies), the flow (run `detect_drift` → show report → `apply_mechanical` for structured drops → **agent reconciles prose**: rewrite `scientific_argument.evidence_for` to surviving+new studies, refresh `executive.verdict`/`verdict_status`, reconcile `biological_story` mentions, add `at_a_glance` roles for new studies, record `reconciled_from: [a,b]` on a merge → re-run `detect_drift` to confirm zero residual). Mirror the YAML-direct dispatch style of the existing subcommands (shell to `python -m viva_superpowers.investigation_reconcile`). Note it's AI-free in the helper; the prose rewrite is the host agent's.
- [ ] **Commit** — `docs(skill): viva-investigation reconcile subcommand`.

### Task 5: PR
- [ ] `pytest -q` green; push `feat/investigation-reconcile`; `gh pr create` against `main` (no AI attribution). Body: the capability + the AI-free/agent split + that Part A will dogfood it. **Stop — no merge until the user says "merge".**
