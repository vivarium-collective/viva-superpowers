# Composites, Templates, and the Study/Investigation Stack

How the vivarium-workbench data model layers research metadata — a question, its
evidence, and the argument several results build together — over a single runnable
substrate: the **process-bigraph composite**. And how a *composite template* — a
document with open **sites** (holes) — is the shape studies and investigations are
actually built from.

> Companion to [`vivarium-workbench-model.md`](vivarium-workbench-model.md), which
> is the source of truth for the on-disk YAML shapes and the dashboard API surface.
> This document is the conceptual bridge from those shapes *down* to the
> process-bigraph substrate. The template/site formalism lives in
> [`process_bigraph/templates.py`] and bigraph-schema's Milner implementation
> (`bigraph_schema/assembly.py`, `bigraph_schema/schema.py` `Site`); see
> bigraph-schema `.claude/plans/milner-formalism.md`.

---

## 1. The big idea

Three layers of metadata sit over one runnable object. Read the stack top-down and
it's an argument; read it bottom-up and it's a simulation.

```
Workspace  (workspace.yaml + viva_<pkg>/ + .pbg/ runtime state)
│
├─ Investigation   investigations/<slug>/investigation.yaml   (schema v2, 9-section spine)
│    = a named collection of studies under one research question
│    = also a git BRANCH and a WORKTREE (1:1:1)
│    └─ studies: [<slug>, …]   +   DAG computed from each study's prerequisites
│
├─ Study   studies/<slug>/study.yaml   (schema v3/v4, 8-section + v4 narrative spine)
│    = one research question wrapped around one-or-more composites
│    └─ baseline: [{name, composite: <pkg.composites.x>, params}]   ← points DOWN
│
└─ Composite   viva_<pkg>/composites/<id>.composite.json (or a generator .py)
     = the actual process-bigraph document — the only runnable thing
```

**The one sentence to remember:** a **Composite** is the runnable object; a **Study**
is the reason you run it; an **Investigation** is the argument several studies build
together. Everything above the composite is metadata that *references* composites by a
dotted id and records what came out — with one important twist covered in §4: an
investigation is itself *compiled into* a composite.

Why the split earns its keep: the composite is reusable across many questions; the
study attaches *one* question, one emit-contract, and one pass/fail bar to it; the
investigation lets a dozen such questions accumulate into a defensible claim. You can
re-run the science without rewriting the argument, and audit the argument without
re-reading the code.

---

## 2. The composite

A composite is a **process-bigraph document**: one `state` map of **typed nodes** of two
kinds — **processes** (`_type: process`; an `address` + `config` + an `update` that
computes each step) and **stores** (typed state). Processes never talk to each other
directly; they read and write **shared stores**, and that wiring *is* the coupling. A
real node from `spatio_flux/composites/fig07-1-community-dfba.composite.json`:

```jsonc
"ecoli core dFBA": {
  "_type": "process", "address": "local:DynamicFBA",       // resolved in the registry
  "config": { "model_file": "textbook", /* … */ },
  "inputs":  { "biomass": ["fields", "ecoli core"] },       // ← wiring path into a shared store
  "outputs": { "biomass": ["fields", "ecoli core"] },
  "interval": 1.0 }
```

> **The full formalism lives in process-bigraph:**
> [`docs/concepts/composites-and-templates.md`](https://github.com/vivarium-collective/process-bigraph/blob/main/docs/concepts/composites-and-templates.md)
> — the composite anatomy (addresses, nesting), static vs generator composites, **draft
> processes**, and the **template/site** mechanism. This document summarizes only what
> the study/investigation layer needs and builds *on top* of that substrate.

**Stubbing a not-yet-built mechanism (holes-in-place).** When the model's topology
needs a mechanism whose dynamics aren't written yet, leave a **hole**: an open site
whose `_sort` names a `ProcessContract` — `{"_type": "site", "_sort": "<Contract>"}`
(see §3). The contract declares the ports + a description of what the mechanism is
*meant* to do, so the model stays complete and reviewable; `Composite` reports the
unfilled hole until a real Process fills it. A stub is a *hole*, not a node.

> **Deprecated — don't reach for `DraftProcess`.** The older pattern (a
> `DraftProcess` / `@draft_process` — a present-but-inert placeholder *node* that
> carries a contract but no `update` dynamics) is deprecated in process-bigraph and
> emits `DraftProcessDeprecationWarning`. Use a hole instead. Migrate an existing
> draft with `draft_to_contract(SomeDraft)` → `core.register_contract("SomeDraft",
> contract)` → replace the `local:SomeDraft` node with `{"_type": "site", "_sort":
> "SomeDraft"}`. Full treatment:
> [`designing-with-holes.md`](https://github.com/vivarium-collective/process-bigraph/blob/main/docs/concepts/designing-with-holes.md).

---

## 3. Templates: composites with holes (sites)

A **template** is a composite document that is not *ground* — it has open **sites**
(`{"_type": "site", "_sort": <face>}`), Milner place-graph **holes** where a whole
composite, process, or value plugs in. `Composite` won't run a document with any open
required site; filling every required site makes it **ground** and runnable. The full
mechanism — `open_sites` / `fill_sites` / `template_document` / `investigation_document`
and the literal on-disk shape — is in process-bigraph
[`docs/concepts/composites-and-templates.md`](https://github.com/vivarium-collective/process-bigraph/blob/main/docs/concepts/composites-and-templates.md).

The two template shapes the study/investigation layer is built from:

| Template kind | Shape | Build helper |
|---|---|---|
| **Study template** | analysis/emitter/card network fixed; **the model is a site** | `template_document` — fill the model hole with a composite → ground → runnable |
| **Investigation template** | **one site per member study** | `investigation_document` — fill a member's site to admit it, **prune** members left open |

Investigation gating is expressed as *filling*, not scheduling: an unfilled member site
is dropped from the built document, so a blocked prerequisite simply never appears in the
run. This is the substrate under investigation-as-composite (§4).

Keep three "blanks" apart: a **site** is an empty structural *hole* (the template
mechanism); a **draft process** is a present-but-inert *node* (§2); and **`config` /
`params` / `${name}`** fills a node's *parameters*. So a template is specialized two ways
— **fill its sites** (structure) and **set its parameters** (values). A study picks a
composite for the model site and sets its params; an investigation fills one site per
member study.

---

## 4. How studies and investigations use it

### A study specializes the template

A study doesn't rebuild the composite — it wraps one question, one specialization, and
one pass/fail bar around it. Five fields do the joining (full field docs in
[`vivarium-workbench-model.md`](vivarium-workbench-model.md)):

| Field | Role in the join |
|---|---|
| `baseline[]` / `conditions.baseline` | **Which** composite(s) to run — a list, so one study can compare several. |
| `variants[]` | A baseline + `parameter_overrides` — the parameter fill-in surface, no structural edits. |
| `simulation_set[]` | The run recipe: `base_model`, `perturbation`, `condition`, `seeds`, `duration`. |
| `readouts[].store_path` | The **emit contract** — ties a named observable to the exact store path in the composite's output tree. |
| `behavior_tests[]` | `measure` + `pass_if` over those readouts — the verdict. |

At run time `POST /api/study-run-baseline` resolves the `baseline` id, **builds that
composite in-process**, merges the study's `params`, runs it, and records the trajectory
in `runs.db`. The study itself is never compiled into a composite — it stays metadata
that *points at* one and reads back what came out. (Per-test pass/fail pills are
**derived on read** from the latest run's `outcomes[test].result`, never from a
hand-set `status:`.)

### An investigation can run as a composite — but `run_jobs` is canonical today

An investigation groups member studies into one argument. Two *separate* process-bigraph
mechanisms sit under that grouping, and they are easy to conflate — keep them apart. For
the single-source-of-truth on how an investigation actually runs, see
[`how-an-investigation-runs.md`](how-an-investigation-runs.md); this section is the
conceptual summary.

**1. The executable `StudyStep` composite** (`lib/investigation_execution.py`).
`build_investigation_composite(ws_root, inv_slug)` — a plain build function, not a
registered `@composite_generator` — compiles `investigation.yaml` into a runnable
process-bigraph `Composite`: one `local:StudyStep` node per member study, ordered by
`pipeline_gate.prerequisites` wiring (a member with no real prerequisite gets a
*synthetic serial edge* to the preceding declared member, so a no-prereq investigation
still runs in declared order), plus `InvestigationAnalysisStep` nodes wired to the member
result stores. `run_investigation_composite(...)` runs it as
`Composite({"state": …, "run_steps_on_init": True})`; process-bigraph's `determine_steps`
reads the wires and orders execution. A `StudyStep` doesn't rebuild anything itself — it
dispatches the `run_study` capability to the persistent env-worker pool, which runs that
member's baseline + variants + post-sim end-to-end and writes `investigation/<slug>/result`.
`StudyStep` / `InvestigationAnalysisStep` are defined in `lib/investigation_steps.py`
(they are workbench `Step`s — **not** part of process-bigraph). Note this graph does
**not** use template sites: its ports are plain `"node"` and its addresses are
`local:<Class>`.

> **This path is real and tested, but currently sidelined.** It is *not* wired to any
> HTTP endpoint or the UI; it is reachable only through
> `vivarium-workbench prepare-investigation` (the full-run branch) and the tests. It is
> **serial-only**, **fail-loud**, and **refuses on the `deployment` run target**
> (`investigation_steps.py` raises rather than dispatching a deployment-pinned study).
> The canonical orchestrator is `run_jobs` — see the table below.

**2. The pull-or-compute trigger document** (`lib/investigation_composite.py` +
`lib/investigation_trigger.py`). A *different* mechanism, and the one that actually uses
the §3 template/site formalism. `investigation_composite.py` builds a content-addressed
`{member: region}` document in which each region carries `_study` metadata and the member
sites are the template holes; `investigation_trigger.py` wraps
`process_bigraph.templates.trigger` to open one target study — **pull** cached upstream
prerequisites already computed, **compute** the open target, and **prune** non-ancestors
— returning a `{pulled, computed, pruned}` report. This is the substrate under the
pull-or-compute rerun spine, not a full investigation run. (The workbench never
constructs a `Composite` from this document; it reads the `_study` metadata and delegates
the actual run.)

**What orchestrates an investigation run today.** There are **three** investigation
orchestrators, and the composite path above is *not* the default:

| Orchestrator | How it runs | Status |
|---|---|---|
| `POST /api/investigation-run-unblocked` | the `run_jobs` manager (async 202 + poll, via `study_runs`) | **canonical** |
| `POST /api/investigation-run` | inline `textwrap` script fired as a synchronous `subprocess` | legacy / secondary |
| `vivarium-workbench prepare-investigation` (full-run branch) | the `StudyStep` composite above, in-process | non-default, local-only |

`run_jobs` is the canonical orchestrator: `docs/run-orchestration-consolidation.md`
Decision 1 (in `vivarium-workbench`) makes it so, keeping the composite path reachable
from `prepare-investigation` but not the default. (The `vwb run investigation` /
`run_investigation` CLI routes to the inline-subprocess path, **not** the composite —
despite the composite builder living next door in `investigation_execution.py`.)

**The dependency DAG.** `studies: []` controls grouping/visibility and run order; the
DAG is computed at render time from each member's `pipeline_gate.prerequisites`, with
edge semantics `builds-on · tests · motivates · alternative-to` (default `builds-on`;
legacy `leads-to · model-input · refutes · precedes` still parse as aliases). In the
executable `StudyStep` composite, those same prerequisite edges *are* the store wiring
that sequences execution (and a member with no prerequisite gets a synthetic serial edge).
**Investigation ≡ branch ≡ worktree**, so parallel agents each drive one without
colliding on runtime DBs or dashboard ports.

### What compiles, what stays a reference

| Layer | How it becomes runnable | Compiled to a composite? |
|---|---|---|
| Composite | It *is* the process-bigraph document (or a generator that emits one) | — (it is the target) |
| Study | Resolves its `baseline` id → builds that composite in-process, applies `params` | **No** — reference + param merge |
| Investigation | Canonically run by the `run_jobs` orchestrator (`/api/investigation-run-unblocked`); *can* also be compiled to a `StudyStep` composite via `build_investigation_composite`, but that path is non-default — local-run only, not UI-wired | **Optional** — composite path exists but is sidelined |

---

## 5. Worked example — `spatio-flux`, end to end

`spatio-flux` builds the Process-Bigraph paper's figures: one investigation, one study
per figure. Following Figure 7:

**① Investigation** — `investigations/paper-figures/investigation.yaml`:

```yaml
schema_version: 2
name: paper-figures
title: Process Bigraph paper — figures
studies: [fig-01, fig-02, fig-03, fig-07, fig-08]
```

Five member studies, no explicit prerequisites → a flat DAG.

**② Study** — `studies/fig-07/study.yaml` frames one figure over **three** composites:

```yaml
schema_version: 3
name: fig-07
investigation: paper-figures
status: complete
confidence: Accepted
baseline:
  - {name: 7-1-community-dfba,     composite: spatio_flux.composites.fig07-1-community-dfba}
  - {name: 7-2-comets,            composite: spatio_flux.composites.fig07-2-comets}
  - {name: 7-3-brownian-particles, composite: spatio_flux.composites.fig07-3-brownian-particles}
behavior_tests: [bigraph-loom image generated correctly]
runs:
  - {name: '…fig07-1-community-dfba__1786323957__36c785', status: completed}
```

`baseline[]` holds all three panels; `simulation_set` are the recipes, `runs[]` the
executions, `visualizations[]` the outputs, `behavior_tests` the gate.

**③ Composite** — `spatio_flux.composites.fig07-1-community-dfba` resolves to the
process-bigraph document the engine runs: a community of `local:DynamicFBA` processes
(one per species) plus `local:MonodKinetics`, all wired through one shared `fields`
store. Coupling happens *only* through those input/output paths. `fig-07`'s
`readouts[].store_path` point at paths like `fields/glucose`; its `behavior_tests`
measure over them; its `runs` land in `runs.db`; and `paper-figures` groups `fig-07`
with its four sibling figure-studies.

The whole chain, in one line: **shared-store composite → study that questions, runs,
and tests it → investigation that collects the figures into a single paper-shaped
claim.**

---

## 6. Where the code lives

Four repos, stacked by dependency: **bigraph-schema** (types) ⊂ **process-bigraph**
(engine + composite/template primitives) ⊂ **vivarium-workbench** (server +
investigation-as-composite) ⊂ **viva-superpowers** (`/viva-*` skills + authoring). Each
lower layer is imported by the ones above it.

### bigraph-schema + process-bigraph — the substrate

The type system (`bigraph_schema`: the `Site` type, the `assembly.py` bigraph algebra)
and the engine + composite/template primitives (`process_bigraph`: `composite.py`,
`templates.py`, `draft_process.py`, `composite_spec.py`) are catalogued in the
process-bigraph companion doc,
[`docs/concepts/composites-and-templates.md`](https://github.com/vivarium-collective/process-bigraph/blob/main/docs/concepts/composites-and-templates.md#3-where-the-code-lives).
The tables below cover the two layers that own the *study/investigation* concepts.

### vivarium-workbench — the dashboard server + investigation-as-composite

| File | What it is |
|---|---|
| `vivarium_workbench/api/app.py` | The HTTP API — `/api/study-*`, `/api/iset/*`, `/api/investigation-run-unblocked`, `/api/investigation-run`, `/api/investigation-composite-rebuild`. |
| `lib/run_jobs.py` | The **canonical** investigation orchestrator (`/api/investigation-run-unblocked`). |
| `lib/investigation_steps.py` | `StudyStep` + `InvestigationAnalysisStep` (studies as nodes; plain `"node"` ports, `local:<Class>` addresses). |
| `lib/investigation_execution.py` | `build_investigation_composite` / `run_investigation_composite` — the sidelined executable composite path. |
| `lib/investigation_composite.py` · `investigation_trigger.py` | The pull-or-compute trigger document (`_study` sites; `{pulled, computed, pruned}`). |
| `lib/composite_mutations.py` | `rebuild_investigation_composite` + composite edits. |
| `lib/study_runs.py` · `cli_runs.py` | Run baseline / variant / investigation. |
| `env_worker.py` | The spawned worker — `run_study` / `run_investigation_analysis` capabilities. |
| `templates/study-detail.html` · `loom/` | The 5-act study-spine UI; the composite-explorer (loom) view. |

### viva-superpowers — the `/viva-*` skills + study/investigation authoring

| File | What it is |
|---|---|
| `docs/concepts/vivarium-workbench-model.md` | The data-model source of truth (on-disk YAML + API). |
| `skills/` | The `/viva-*` skills — study, investigation, expert, viz, run. |
| `viva_superpowers/scaffold.py` | Emits the study/investigation YAML spines (TODO placeholders). |
| `viva_superpowers/study_canonicalize.py` · `investigation_canonicalize.py` | Canonicalize specs on read. |
| `viva_superpowers/study_status.py` | `study_clarity_summary` — the derive-on-read status source. |
| `viva_superpowers/report.py` · `report_linter.py` · `test_audit.py` · `rigor.py` | Report render + lint + assurance/rigor scorecards. |

---

## 7. Study lifecycle & on-disk layout

A study moves through five phases, each writing to a different part of the spine:

| Phase | Produces | Writes to |
|---|---|---|
| **Design** | The spec: question, gate, run set, tests | `purpose`, `pipeline_gate`, `simulation_set`, `behavior_tests` |
| **Build** | Executable code: Process classes + composites | `model_change`, `implementation_requirements`, the composite files |
| **Simulate** | The runs: trajectories | `runs.db` |
| **Evaluate** | The verdict: test results + figures | `outcomes`, `visualizations`, `findings` |
| **Decide** | Conclusion + follow-ups | `conclusion_verdicts`, `discovery_implications` |

Coarsely sequential, iterative in practice: Evaluate routinely sends you back to Build.
An investigation card surfaces its *slowest-phase* member.

```
# A workspace root
workspace.yaml
viva_<pkg>/composites/<id>.composite.json    # the runnable substrate (ground or a template)
investigations/<slug>/investigation.yaml      # the collection (= branch = worktree)
studies/<slug>/study.yaml                     # the question + spine
studies/<slug>/runs.db                        # canonical run + outcome record
studies/<slug>/parquet-runs/<run>/            # emitted trajectories
.pbg/server/                                  # dashboard runtime state
```

To see it rendered: `/viva-workbench start`, then open an investigation — the same three
layers appear as the **Investigation graph** (nodes = studies, Asks → Finds →
Confidence), the **study-detail spine** (Design / Evidence / Assurance / Decision acts),
and the **Composite Explorer** (the wired process graph).
