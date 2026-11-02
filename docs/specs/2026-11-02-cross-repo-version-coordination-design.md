# Cross-repo version coordination — design

Status: proposed · 2026-11-02 · scope: ecosystem (viva-superpowers, discovery-engine,
vivarium-workbench, and the shared server venv)

## Problem

The tightly-coupled core repos depend on each other as git `branch=main` sources and
resolve them *live* at install time. That makes a bump invisible and unbounded: an
unrelated merge in an upstream repo silently changes what a downstream repo builds and
tests, and the breakage only surfaces later, on some unrelated downstream push.

This is not hypothetical — it was proven on 2026-11-02. `viva-superpowers` `main` was
green, but only because no push had triggered its CI since `discovery-engine` advanced
**31 commits** (Phase 1/2 graded-outcomes, G1–G5, the grading-ontology RFC). The first
PR to run CI after that drift (a one-line facade shim) came back red with ~25 failures —
none in the changed code, all in the scaffold → report/import/e2e chain, from an engine
contract change the downstream had never been tested against.

Two masking layers hid it:

1. **The lockfile is maintained but not load-bearing.** `#391` added Renovate
   `lockFileMaintenance` to refresh `uv.lock` to the latest engine commit weekly — the
   *propagation* half of a "decoupled but in sync" seam. But CI installed with
   `uv pip install -e ".[…]"`, which **ignores `uv.lock`** and re-resolves every
   `branch=main` dep to its tip. So the maintained lock never governed what CI tested.
2. **No downstream trigger.** A repo's CI runs on *its own* push/PR, never when an
   upstream it tracks changes. So upstream breakage waits for an unrelated downstream PR.

The same shape, worse, governs the running servers: the shared dev venv editable-installs
`discovery_engine` from a checkout, so advancing that checkout changes behavior under ~9
live servers at once — the "coordinated bump window" that has to be hand-managed.

## Principle

Depend on a **pinned** upstream, and make every bump an **intentional, tested** change.
This repo already does exactly that for `pbg-template` (CI pins the exact commit via
`PBG_TEMPLATE_REF`; bumping it is a deliberate PR that updates the pin and regenerates the
manifest together). The fix is to apply that same, already-blessed pattern to the
`branch=main` Python deps.

## This PR (the consumption half)

`plugin-ci.yml` now installs with **`uv sync --frozen`** instead of a live
`uv pip install -e .`. Effects:

- CI installs the four first-party `branch=main` deps (`discovery-engine`,
  `viva-workspace`, `viva-basic-processes`, `investigation-contracts`) **from `uv.lock`**,
  not from each branch tip. `main` stays green against the engine it was locked and tested
  with; an unrelated upstream merge can no longer redden it.
- The only place a *new* engine is exercised is the **lock-bump PR** — Renovate's weekly
  `lockFileMaintenance` (or a manual `uv lock --upgrade-package discovery-engine`). That PR
  changes `uv.lock`, so frozen CI now tests the new engine and goes red **at the bump**,
  where the incompatibility belongs, with a small reviewable diff — instead of ambushing an
  unrelated PR weeks later.

Together with `#391` this closes the seam: `#391` propagates (opens the bump), this change
consumes (tests the bump). Validated locally: `uv sync --frozen` resolves the full env from
the lock and pins `discovery_engine` to the locked commit, not `main`.

## Follow-ups (staged — need owner sign-off, not built here)

1. **Detection trigger — built.** `upstream-drift-canary.yml` runs the suite daily against
   *live* upstream main (deliberately not frozen), so drift surfaces the same day with a
   dated, attributable signal instead of ambushing an unrelated PR. It only detects — the
   bump stays an intentional lock-bump PR — so it never duplicates Renovate even if the app
   is on. Remaining open question (owner: org admin / Eran): is the Renovate GitHub App
   actually enabled for the *auto*-bump PR? If not, the bump is a manual
   `uv lock --upgrade-package discovery-engine` whenever the canary (or a release) says it is
   time — the seam does not depend on the app being on.
2. **Generalize to the other consumers.** `vivarium-workbench` (and any repo that installs
   these `branch=main` deps live) has the same exposure — apply frozen installs + a
   maintained lock + Renovate there too. Owner: per-repo.
3. **Publish `discovery-engine` version tags.** Today the pin is a git commit. Once the
   engine tags releases, Renovate tracks the tag bump (it is already configured to), and
   consumers pin a semver range — turning "which commit" into "which release," the
   lockstep-compatibility-set idea. Owner: discovery-engine.
4. **Servers off the shared editable venv (the #2 item).** The running servers import
   `discovery_engine` from an editable checkout, so a dev advance ripples to all of them and
   bumps are a hand-coordinated window. Move servers to install from a pinned lock (the same
   authoritative `uv.lock`), and do day-to-day dev in per-worktree venvs (the pattern already
   used to run the latest without touching the shadow venv). A server bump then becomes one
   deliberate, isolated, tested upgrade rather than a global ripple. This is a production
   deployment cutover — owner: Eran, on a chosen window.

## On the "single contract package" (the #3 item)

A separate `viva-study-contract` package is **not** proposed. `discovery_engine` is already
the de-facto single contract: the study/outcome/grading model, report linter, rigor,
schemas, and `workspace_paths` all live there, and `viva_superpowers` is a facade of
re-export shims (one implementation, zero divergence, asserted by
`test_discovery_engine_facade.py`). What was missing was not another package but the
**compatibility enforcement** between the one contract and its consumers — which is exactly
what the frozen-CI seam above provides. The future refinement is versioned releases (item 3),
not a new extraction.

## Decisions requested

- Adopt frozen CI installs across the consumer repos (this PR for viva-superpowers; same for
  vivarium-workbench)?
- Confirm the Renovate app is enabled, or approve the scheduled-fallback workflow?
- Approve a window for the server-venv cutover (#2)?
- Commit discovery-engine to publishing version tags so consumers pin semver (#3)?
