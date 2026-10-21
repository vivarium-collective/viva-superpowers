# How an investigation runs

The one-stop answer to "what actually executes when I run an investigation, and
how does a single study get run underneath it." The data model — what a Study and
an Investigation *are* — lives in
[`vivarium-workbench-model.md`](vivarium-workbench-model.md); the composite/template
substrate they sit on is in
[`composites-templates-and-the-study-investigation-stack.md`](composites-templates-and-the-study-investigation-stack.md).
This doc is just the run paths.

> **Read this before assuming the "investigation-as-composite" path is the default.**
> It is not. `run_jobs` is the canonical orchestrator; the composite path is real,
> tested, and sidelined.

---

## The three investigation orchestrators

Running an investigation means running its member studies (in dependency order where
`pipeline_gate.prerequisites` declares one). Three code paths can do that, and only
the first is the default:

| # | Entry point | What it drives | Status |
|---|---|---|---|
| 1 | `POST /api/investigation-run-unblocked` | the **`run_jobs`** manager (`lib/run_jobs.py`) — enumerates each member study's unblocked runs and submits them via `study_runs`; async (HTTP 202 + poll `…-status`) | **canonical** — the default the UI and skills use |
| 2 | `POST /api/investigation-run` | an inline `textwrap` script fired as one **synchronous `subprocess`**, in list order, no dependency scheduling | legacy / secondary; still present |
| 3 | `vivarium-workbench prepare-investigation` (full-run branch) | the **executable `StudyStep` composite** (`lib/investigation_execution.py`), run in-process | **non-default, local-only** |

`run_jobs` is canonical by an explicit decision: `vivarium-workbench`'s
`docs/run-orchestration-consolidation.md` **Decision 1** keeps the composite path
reachable from `prepare-investigation` but makes `run_jobs` *the* orchestrator.

Note the CLI naming trap: `vwb run investigation` / `run_investigation` routes to the
**inline-subprocess path (#2)**, *not* to the composite builder that lives next door in
`investigation_execution.py`. There is no CLI that runs the composite path except
`prepare-investigation`'s full-run branch.

---

## The composite path — what it is, and when it's used

`build_investigation_composite(ws_root, inv_slug)` (a plain build function, **not** a
registered `@composite_generator`) compiles `investigation.yaml` into a runnable
process-bigraph `Composite`:

- one `local:StudyStep` node per member study, ordered by `pipeline_gate.prerequisites`
  wiring — and a member with **no** real prerequisite gets a *synthetic serial edge* to
  the preceding declared member, so a no-prereq investigation still runs in declared
  order;
- `InvestigationAnalysisStep` nodes wired to the member result stores;
- run via `run_investigation_composite(...)` →
  `Composite({"state": …, "run_steps_on_init": True})`, where process-bigraph's
  `determine_steps` reads the wires and orders execution.

`StudyStep` and `InvestigationAnalysisStep` are defined in
`lib/investigation_steps.py` — they are **workbench `Step`s, not part of
process-bigraph**. The graph uses plain `"node"` ports and `local:<Class>` addresses;
it does **not** use template sites.

**It is sidelined on purpose.** The composite path is:

- **not wired** to any HTTP endpoint or the UI — reachable only through
  `prepare-investigation` (full-run branch) and the tests;
- **serial-only** and **fail-loud**;
- it **refuses on the `deployment` run target** — `investigation_steps.py` raises
  rather than dispatching a study that resolves to `deployment`.

So the composite path is for a local, in-process full run; production and UI-driven
runs go through `run_jobs` (#1).

### A separate thing: the pull-or-compute trigger document

Don't confuse the executable `StudyStep` composite with the **trigger document**
(`lib/investigation_composite.py` + `lib/investigation_trigger.py`). The trigger
document is content-addressed `{member: region}` with `_study` metadata and member
**sites** (the template/holes formalism); `investigation_trigger.py` wraps
`process_bigraph.templates.trigger` to open one target study — **pull** cached upstream
prerequisites, **compute** the open target, **prune** non-ancestors — returning a
`{pulled, computed, pruned}` report. It is the substrate under the *pull-or-compute
rerun* spine, not a full-investigation orchestrator. (The workbench never builds a
`Composite` from this document; it reads the `_study` metadata and delegates the run.)

---

## How a single study executes

Whatever orchestrates the investigation, running one member study is the same shape:

1. **Baseline model composite.** A study is never compiled into a composite itself — it
   *points at* one. Its `baseline[]` entry names a composite id; the run resolves that id
   and **builds that composite in-process** (`viva_superpowers/composite_spec.py`
   `build_composite`), merging the study's `params`. (On the canonical path this is
   `POST /api/study-run-baseline`; on the composite path a `StudyStep` dispatches the
   `run_study` capability to the persistent **env-worker pool**, which runs the study to
   completion — baseline + variants + post-sim — and returns its run refs + verdict.)
2. **Variants.** Each variant is the baseline plus `parameter_overrides` — a parameter
   fill-in, no structural edits — run the same way.
3. **Post-sim cascade.** `ResultsStep → {AnalysisStep, ReportCardStep, VisualizationStep}`
   (`viva_superpowers/post_sim.py`) is *documented* as a Composite, but on the live path
   it is invoked **imperatively**: `env_worker._run_generic_analyses` instantiates each
   `AnalysisStep` and calls `.update()` directly — no `Composite`, no `determine_steps`.

The trajectory + outcomes land in the per-study `runs.db`; per-test pass/fail is derived
on read from the latest run's `outcomes[test].result`.

---

## In one line

Investigations are canonically orchestrated by **`run_jobs`** (`/api/investigation-run-unblocked`);
the **`StudyStep` composite** is a real but sidelined local-run path
(`prepare-investigation`); a **study** always runs by building its baseline model
composite in-process (+ variants) and then running the post-sim steps — on the live
path, imperatively via the env-worker's `run_study` capability.
