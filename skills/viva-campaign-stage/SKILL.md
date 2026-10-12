---
name: viva-campaign-stage
description: Use when building a study as a stage in a multi-stage research campaign (e.g. viva-genesis) where every stage must clear the same high, consistent quality bar — the campaign "definition of done". Encodes the 9-point standard a stage must satisfy (real-tool model, units-typed ports + config, filled Process contract, reusable domain-named composite, pre-registered auto-graded behavior_tests, canonical sims/run.py, authored narrative from real results, real-data visualization, green + clean) so the bar is applied automatically, not re-derived each stage. Follow it alongside viva-expert (build) and viva-study (lifecycle).
user-invocable: true
allowed-tools: Bash(*) Read Write Edit Glob Grep
argument-hint: "<stage-slug> — the campaign stage/study to build or audit against the bar"
---

# viva-campaign-stage

The single authoritative **quality bar** for a study built as one stage of a
multi-stage campaign. A campaign is a sequence of studies/stages, each built to
the *same* standard so the campaign reads as one coherent body of work rather
than a pile of uneven one-offs. This skill is the **definition of done** for a
stage — a checklist you follow while building, and the gate you run before
calling a stage finished.

It does not replace the build and lifecycle skills — it raises their floor:

- [`/viva-expert`](../viva-expert/SKILL.md) builds the Processes + composite
  (real-tool bridge, units-typed ports, filled `contract`, `@composite_generator`).
- [`/viva-study`](../viva-study/SKILL.md) drives the study lifecycle
  (Design → Build → Simulate → Evaluate → Decide), the `behavior_tests[]`
  grammar, findings, verdicts, and the rigor scorecard.
- [`/viva-tests`](../viva-tests/SKILL.md) authors/grades the report-card tests.
- [`/viva-viz`](../viva-viz/SKILL.md) builds the visualization.

This skill tells you the standard *all nine* must jointly reach for the stage to
count as done. Where a point overlaps `viva-expert`'s or `viva-study`'s rules,
this is the campaign-level restatement — the same letter, with the stage bar
made explicit.

## The bar — a stage is DONE only when ALL nine hold

Treat any unmet point as **NOT done**. No partial credit; a stage that clears
eight of nine is an eight-of-nine stage, reported honestly as such, not shipped
as finished.

### 1. Real-tool model

The Process `update()` drives a **genuine installed simulator** (FiPy,
eQuilibrator, libRoadRunner, Reaktoro, COBRApy, …) — never a paraphrase of its
math in NumPy. Bridge the real tool; keep trying when the build is hard (see
`viva-expert`'s escalation ladder).

A clean-room reproduction is allowed **only** when either:
- the real tool genuinely cannot run in-environment (GPU-only/CUDA on a CPU
  host, proprietary, unreleased, unbuildable), **or**
- the study's own proposed method *is* explicitly a coarse-grained / reduced
  model (that is the science, not a shortcut).

When a reproduction is used, **label it honestly**: name the class
`<Tool>ReproductionProcess` (or a clearly coarse-grained name), calibrate it to
the cited source, and never pass it off as the real tool. Surface the blocker;
do not silently downgrade.

### 2. Units-typed ports AND config

Every input port, every output port, and **every `config_schema` entry** for a
dimensioned quantity uses `{"_type": <t>, "_units": <unit>}` — e.g. `kelvin`,
`molar`, `volt`, `mole/second`, `meter`, `pascal`, `1/second`, `dimensionless`.
Never a bare `float` for a quantity that has a unit. `_units` is metadata (the
value stays a plain float), so it costs nothing and makes the physical meaning
checkable and loom-visible. A boolean flag is inherently dimensionless and needs
no unit. Config params carry units too: `{"type": "float", "units": "<unit>",
"default": …}`.

### 3. Filled Process `contract`

Every Process/Step declares a class-level `contract` dict with **at minimum
`summary`**, plus: `description`, per-port `inputs` and `outputs` (prose naming
each port's unit), `assumptions`, `math`, `symbols`, and `references` (bib keys
→ `references/papers.bib`). The loom renders `contract.summary`/`description` and
the contract audit grades the rest; no contract ⇒ "no contract" in the loom and
nothing to grade.

### 4. Reusable, domain-named composite

The composite generator is a parameterized `@composite_generator` **named for
its domain / mechanism** — `serpentinizing_vent_reactor`,
`hydrothermal_carbon_fixation`, `thermophoretic_concentration` — **not for the
study number** (`og_03_baseline`). One generator drives *every* condition of the
stage: the favorable arm and every control, all from its `parameters`. Put it in
a topic-named module (`composites/vent_reactor.py`), not `campaign0.py`. Several
studies may reuse the same generator with different params — that is the point.

### 5. Pre-registered, auto-graded behavior_tests

Each `behavior_tests[]` entry declares, **before the run**:

- `measure: {kind: derived, path: <evaluator>}` (or `kind: cross_run` for an
  across-arm contrast);
- a `pass_if` band — an `op` plus a `value`/`range`;
- `units`, `classification`, and `gate_class`
  (`acceptance_criterion` for a prior stated before the run; `regression_pin`
  for a threshold set after seeing it — never let a pin pose as acceptance);
- **provenance**, exactly one of:
  - `cites: [bibkey]` for a literature-anchored band, or
  - `band_basis ∈ {first_principles, conservation_law, machine_precision,
    numerical}` for a physics/math band.

The derived metrics are **real functions** in the workspace evaluators module,
registered via `register_derived_scalars`, reading the run's emitted series —
never hand-typed numbers. A band with neither `cites` nor `band_basis` is not
pre-registered; a derived `path` with no registered evaluator cannot grade.

### 6. Canonical runner (`sims/run.py`)

A single `sims/run.py` that:
- runs the **favorable arm as the canonical run** and persists an **isolated
  sqlite store** for it;
- calls `evaluate_on_run_completion` to auto-grade the `kind: derived` tests;
- runs the **control arms** to grade the `kind: cross_run` tests, writing their
  verdicts into the run's `outcomes`;
- writes `.pbg/runs/<run_id>/viz.json` so the native viz gallery shows the
  figures.

> **`is_empty(Float, 0.0)` gotcha.** `bigraph_schema.is_empty(Float, 0.0)` is
> `True`, so `Core.fill()` treats an explicit `0.0` config/param value as
> "not set" and **silently replaces it with the schema default**. A "zero"
> control driven by a `0.0` generator param therefore runs at the default, not
> at zero. Drive zero controls via **state inputs** or a **tiny epsilon**
> (`1e-12`), never a `0.0` generator param.

### 7. Authored narrative from real results

Every narrative field is sourced from the **graded run** and cited to
`Resources/papers.bib` — not invented, not aspirational:

- `claim`;
- `findings[]` — each `{id, kind, status, statement, evidence: {from_test,
  observed, units}, expected: {cites}, explanation, next_action}`;
- `report` — `{verdict, confidence, main_insight, conclusion, caveat,
  key_metrics}`;
- `conclusion_verdicts`, `limitations`, `discovery_implications`;
- `readouts[]` — each `{name, store_path, units, description, status}`.

**Honest planned-vs-done.** Anything deferred is labeled a caveat/limitation —
never implied done. Write prose in normal sentence case (see the repo's
authored-content style); the ALL-CAPS in these instructions is for you, the
agent, not a style to copy.

### 8. Real-data visualization

A `Visualization` (Step) class rendering **only from simulated output** — every
pixel from the sim, nothing fabricated or illustrative. Declared in the study's
`visualizations[]`, registered so it renders in the workbench gallery and the
report. It produces **both** a static figure **and** a legible, actually-moving
animation wherever a time or parameter dimension exists (a still frame where a
trajectory exists is an unmet point). Add via [`/viva-viz`](../viva-viz/SKILL.md).

### 9. Green + clean

- The study's gate is refreshed via
  `viva_superpowers.study_verdict.write_gate_evaluator`;
- `scripts/lint-workspace.py` prints **OK with no WARN**;
- the test suite passes.

> **Two recurring YAML/enum traps:**
> - A **plain scalar containing `": "`** parses as a map — quote it (`"k: v"`)
>   or rephrase.
> - **Enum fields take their specific values** — `evaluation_status` is
>   `evaluated`, not `"passed"`; `status` close-out is `complete`, not
>   `evaluated` (there is no badge-evaluated style). Using the wrong token
>   leaves a surface stale or a field inert.

## Build order (follow top to bottom)

1. **Design the stage** — `/viva-study new <domain-composite>`; author
   `question`/`claim` framing, the pre-registered `behavior_tests[]` (point 5),
   `units_and_time`, and the `preregistered:` block **before any run**.
2. **Build the model** — `/viva-expert` for the real-tool Processes (points 1–3)
   and the domain-named `@composite_generator` (point 4). Register derived
   evaluators (`register_derived_scalars`).
3. **Wire the runner** — write `sims/run.py` (point 6); mind the `0.0` gotcha
   for controls.
4. **Run + auto-grade** — `verify` + `check-observables` pass, then run the
   canonical arm and the controls; let `evaluate_on_run_completion` grade.
5. **Visualize** — `/viva-viz` for the static + animated figure (point 8).
6. **Author the narrative** — findings/report/readouts from the graded run,
   cited; honest planned-vs-done (point 7).
7. **Green + clean** — refresh the gate, run the lint and the tests, advance
   `status: complete` / `phase: Decide` only on real evidence (point 9).

## Done-check (run before claiming the stage is finished)

Confirm each with a command's output, not from memory:

- [ ] **1** Process `update()` calls the real installed tool (or a labeled
      reproduction with a stated reason).
- [ ] **2** Every dimensioned port and config entry has `_units`; no bare
      `float` for a quantity with a unit.
- [ ] **3** Every Process has a `contract` with `summary` + the fuller fields.
- [ ] **4** The composite generator is domain-named and parameterized; one
      generator drives the favorable arm and all controls.
- [ ] **5** Every `behavior_test` has `measure`, `pass_if`, `units`,
      `classification`, `gate_class`, and provenance (`cites` **or**
      `band_basis`); derived metrics are registered real functions.
- [ ] **6** `sims/run.py` runs the canonical arm (isolated sqlite),
      auto-grades derived tests, runs controls for cross_run verdicts, and
      writes `.pbg/runs/<run_id>/viz.json`. No `0.0` generator-param controls.
- [ ] **7** `claim`, `findings[]`, `report`, `conclusion_verdicts`,
      `limitations`, `discovery_implications`, `readouts[]` — all from the
      graded run, cited; deferred items labeled as caveats.
- [ ] **8** A `Visualization` renders from sim-only data, declared + registered,
      with a static figure **and** a moving animation where a time/param
      dimension exists.
- [ ] **9** Gate refreshed, `scripts/lint-workspace.py` prints OK (no WARN),
      tests pass; no `": "`-in-scalar YAML and no wrong enum tokens.

A stage that passes all nine is consistent with every other stage in the
campaign by construction — which is the whole point of the bar.
