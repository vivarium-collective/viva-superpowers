---
title: "The Discovery Engine"
subtitle: "Technical Specification --- viva-superpowers scientific-investigation framework"
date: "2026-10-27"
documentclass: article
geometry: "margin=1in"
fontsize: 11pt
toc: true
toc-depth: 2
numbersections: true
colorlinks: true
linkcolor: RoyalBlue
urlcolor: RoyalBlue
---

\newpage

# Overview and scope

The **discovery engine** is a derive-first projection and reasoning layer over a
scientific investigation. An *investigation* is an `investigation.yaml` together with a set
of member *study* files (`study.yaml`), each carrying a claim, a hypothesis, acceptance
behaviors (gate tests), runs, and a verdict. The engine does not perform science directly;
it **reads that authored and recorded state, projects a structured view of it, identifies
what remains unresolved, ranks the unresolved work by value, and proposes --- and, under
explicit gates, executes --- the next move.**

One invocation of `run_cycle` is one *turn* of the crank. Turning the crank repeatedly
drives an investigation from open questions toward a machine-checkable closure condition.

This document specifies the data model, the projections a cycle produces, the reasoning
layer built over them, the validator layer, the execution bridge, the persistence and
renewal rules, and the command surface. It reflects the implementation in
`viva_superpowers/` (`discover.py`, `discovery_engine.py`, `knowledge_store.py`,
`argument_store.py`, `synthesis.py`, `narrative.py`, `validation.py`,
`study_evaluator.py`). It builds on RFC-0005 (derive-first inquiry), RFC-0006 (typed
substrate) and RFC-0007 (the validator layer).

# Design principles

**Derive-first, authored-wins, empty-never-clobbers.** Every view the engine presents is
*computed* from the member studies, then merged over any hand-authored block of the same
name (`inv_spec["knowledge"]`, `inv_spec["argument"]`). In that merge an authored value
overrides the derived one, but an empty authored value (`None`, `""`, `[]`, `{}`) never
clobbers a derived one. Consequently the cycle is fully reproducible from the studies, yet
a scientist retains final authority over any projection by authoring it explicitly.

**Two orthogonal axes.** The engine keeps *progress* (did a run execute? the study's
`execution_status`) strictly separate from *verdict* (does the claim hold?
`supported` / `qualified` / `refuted` / `inconclusive`). A failed execution is not a
refuted hypothesis, and a completed run may be refuted. An adversarial null control whose
designed success is a `refuted` verdict, and whose acceptance behavior passed, is a *met*
criterion, not an open item. Progress never feeds the verdict.

**Suppress false signal as hard as you surface real work.** A frontier is useful only if
every item on it is genuinely unresolved. The engine therefore works as deliberately to
*not* flag non-problems as to surface real ones: a gate recorded in a sibling run is not
"unverified"; a `qualified` verdict refining a `supported` roll-up is not a "divergence"; a
decision already resolved must not still read as "open".

**Explicit gating of consequence.** Reading and projecting are free and side-effect-free.
Anything that writes --- recording a resolution, persisting state, running a simulation,
overwriting a verdict --- is classified by consequence and gated accordingly. The engine
never takes a consequential action implicitly.

# Data model

## Investigation

`investigation.yaml` holds the authored spine:

- `studies` / `members` --- the member study slugs.
- `question`, `audience` --- what the investigation asks and for whom (drive the narrative).
- `acceptance_criteria: [{study, behavior}]` --- the gates that define closure: each names
  a study and the acceptance behavior that must pass.
- `executive: {what_is_this, verdict, verdict_status, verdict_detail, decisions_needed,
  decisions_resolved}` --- the state-first opening and the report's executive summary.
  `decisions_needed: [{question, context}]` are the open expert decisions.
- `resolutions: [{kind, target, rationale, by?}]` --- the uniform discharge record: a
  resolution marks one frontier item of any kind as settled, documenting *why*.
- `knowledge` / `argument` --- optional authored overrides merged over the derived
  projections.
- `cycle_state` --- the slim, regenerable summary the engine writes on persist (below).
- `validation_snapshot` --- the accepted validator state, for staleness detection.

## Study

`study.yaml` (the eight-section canonical form) carries, among other fields:

- `claim`, `hypothesis`, `question`, `concept` --- what the study argues.
- `verdict` --- the authored canonical verdict, when present (else derived).
- `execution_status` --- the progress axis (`proposed` / `planned` / `running` /
  `completed` / `failed`).
- `behavior_tests: [{name, measure, pass_if, ...}]` --- the acceptance behaviors; each has
  a `measure` (e.g. `{kind: derived, path: <observable>}`) and a `pass_if` threshold.
- `runs: [{name, status, outcomes, computed_outcomes, store_path?, canonical?, ...}]` ---
  the recorded runs; `outcomes[test].result` is the authored/recorded grade,
  `computed_outcomes` the freshly re-computed parallel block.
- `parent_studies` / `pipeline_gate.prerequisites` --- the epistemic edges to other
  studies, typed by `relation` (`builds-on`, `refutes`, `qualifies`, ...).

# The cycle bundle

`run_cycle(inv_spec, studies_by_slug) -> dict` is pure (no disk I/O). It computes four
projections, three synthesis products, the validator records and the study suggestions:

```
knowledge   = merge_knowledge(authored, derive_knowledge(inv, studies))
argument    = merge_argument(authored, derive_argument(inv, studies))
narrative   = narrate(argument, question, audience)
audit       = audit(narrative, argument)
gates       = synthesize_gates(inv, argument["claims"])
open_calls  = open_calls(inv, argument["claims"], audit)
validations = run_validators(ctx = {inv, studies, knowledge, argument, narrative, audit})
suggestions = suggest_studies(bundle, inv, studies)
```

The returned bundle has keys `knowledge`, `argument`, `narrative`, `audit`, `gates`,
`open_calls`, `validations`, `suggestions`.

## Knowledge

`derive_knowledge` produces, per study slug:

- **verdict** --- `canonical_verdict(study)`: the authored `verdict` when it is one of
  `{supported, qualified, inconclusive, refuted}`, otherwise the *derived* verdict from the
  coded test roll-up (`roll_up_verdict`), mapped `passed -> supported`,
  `failed -> refuted`, `needs_calibration -> qualified`, `blocked`/`not_started ->
  unassessed`. The record also carries `verdict_source`, `evidence_refs`, a separately
  projected `progress`, and `diverges` (below).
- **concept** --- the single concept the study establishes.
- **behaviors** --- a map `{behavior_name -> PASS | FAIL | SKIP | PENDING}` bucketed from
  the study's run outcomes by test name. The outcomes are *unioned across the study's
  runs* (`_merged_run_outcomes`): a study's acceptance behaviors are often split across the
  several composite runs that produced them, so reading a single canonical run would report
  a gate recorded in a sibling run as PENDING. Canonical runs are applied last so they win
  a genuine key conflict; the verdict roll-up's single-canonical-run authority is unchanged.

## Argument graph

`derive_argument` produces the discourse graph:

- **claims** --- one per study, `{proposition, verdict, evidence_refs, ...}`.
- **edges** --- typed relations between claims (`builds-on`, `refutes`, `qualifies`,
  challenge edges). Edges come from each study's `parent_studies` /
  `pipeline_gate.prerequisites`, each carrying a `relation`.

A **divergence** is recorded on a claim when the authored verdict and the derived roll-up
disagree on the *answer*, not on any inequality. `supported` and `qualified` are the same
answer ("the claim holds"), so `authored=qualified` vs `derived=supported` is not a
divergence; `authored=qualified` vs `derived=refuted` is, and so is
`inconclusive`-vs-`supported` (the author withholding what the gates grant).

## Narrative and audit

`narrate(argument, question, audience)` orders the argument graph into a linear reading
aimed at the investigation's question. `audit(narrative, argument)` returns the transitions
the narrative asserts that the argument graph does not support --- the narrative gaps. A
narrative gap requires a genuine epistemic relation (a `builds-on` the reading claims but
the graph lacks), not merely a missing mention.

## Open calls

`open_calls(inv, claims, audit)` unifies two sources of "what is open": the authored
`executive.decisions_needed` (each becomes a `decision` call) and the derived narrative
gaps (each becomes a `narrative_gap` call). These map onto frontier kinds.

# The validator layer (RFC-0007)

Validators run *inside* `run_cycle` over the derived bundle. The framework provides a
registry keyed by `(type, scope)`:

- **type** --- `logical`, `structural`, `empirical`, `scientific`, `narrative`, ...
- **scope** --- `claim`, `study`, `investigation`, `narrative`, ...

Each validator returns records of the form:

```
{type, scope, target,
 result: {execution_status, scientific_judgment},
 findings: [...], recommendations: [...],
 surfaces: "frontier" | "standing",
 provenance: {validator_id}}
```

**Epistemic separation** is an invariant: `execution_status` (did the check run:
`passed` / `failed` / `error` / `inconclusive`) is kept distinct from
`scientific_judgment` (what it concluded). A validator may run successfully and still
report a negative judgment, and vice versa.

**Surfaces.** A `frontier` record that `failed`/`error`ed becomes an actionable
`validation_finding` on the frontier. A `standing` record (rigor scores, band provenance,
calibration warnings) is feedback shown elsewhere and never floods the frontier. A record
with no surface defaults to `frontier`; an `inconclusive` record is standing feedback.

**Staleness.** Accepted records are snapshotted into `validation_snapshot`. On a later
cycle, a record whose fresh re-derivation no longer matches the snapshot is flagged as a
`stale_validation` (an accepted judgment the world moved past --- an upstream model or run
changed), to be re-validated and re-snapshotted.

**Hygiene guards.** `structural.investigation.hygiene` flags a retired bloat cache
(`knowledge_cycle`), a deprecated field (`plan_acts`), and a `decisions_needed` entry whose
target is already resolved (narrative drift the persist-time renewal clears).

# The reasoning layer

`discovery_engine` reads the bundle and derives the actionable layer.

## Frontier

`frontier(bundle, inv) -> [ {kind, target, rationale, op, priority} ]` is the prioritized
set of *unresolved* items. Items whose `(kind, target)` appears in the investigation's
`resolutions` are discharged and omitted --- a single uniform mechanism for every kind.

| kind                   | priority | blocks closure | op          | meaning                                           |
|------------------------|:--------:|:--------------:|-------------|---------------------------------------------------|
| `unaddressed_criterion`|    90    |      yes       | branch      | an acceptance criterion not yet met               |
| `open_challenge`       |    80    |      yes       | synthesize  | an alternative/refutation not yet adjudicated     |
| `narrative_gap`        |    70    |      yes       | branch      | an unsupported transition in the reading          |
| `open_decision`        |    60    |      no        | steer       | an authored decision awaiting an expert choice    |
| `stale_validation`     |    55    |      no        | revalidate  | a snapshotted judgment the world moved past       |
| `divergence`           |    50    |      no        | reconcile   | authored verdict conflicts with the coded roll-up |
| `validation_finding`   |    45    |      no        | revise      | a registered validator reported a failing check   |
| `pending_gate`         |    42    |      no        | test        | a gate met by verdict only; behavior never run    |
| `open_question`        |    40    |      no        | test        | an unassessed / inconclusive claim                |

Items are sorted by descending priority, then kind, then target.

## Closure

`closure(bundle, inv)` reports the investigation *closed* iff there is no
`unaddressed_criterion`, no `narrative_gap`, and no `open_challenge` --- the
machine-checkable form of the RFC-0005 closure condition. It also returns the count of all
open items. The lower-priority kinds are work but do not block closure: an `open_decision`,
a `divergence`, or a `pending_gate` can remain while the argument is settled.

An acceptance criterion `{study, behavior}` is *met* when its named behavior PASSED, or ---
as a fallback --- when the study verdict is `supported`/`qualified`. A criterion met *only*
by the verdict fallback (verdict holds but the named behavior never ran) is satisfied on
paper but unverified on evidence; it surfaces as a non-closure-blocking `pending_gate`
(verification debt), while still counting as met for closure.

## Next action, invariants, crank

`next_action` returns the single highest-leverage frontier item (or `None` when closed).
`invariants(bundle)` flags validity violations each turn --- for example an assessed claim
(`supported`/`qualified`/`refuted`) with no `evidence_refs` (provenance), or a validation
record that breaches epistemic separation. `crank(bundle, inv)` + `summarize(report)`
bundle a turn into a report and human-readable text.

## Diagnosis

`diagnose(bundle, inv)` explains *why* the cycle is stuck, as bottleneck flags (following
the "perfect discovery engine" Table-2 taxonomy): `task_saturated`, `input_limited`
(expert decisions pending), `planner_limited`, `validation_limited` (low validator
pass-rate), `capability_limited`. It also reports the validator pass-rate.

## Value-aware opportunities

`opportunities(bundle, inv)` ranks the frontier by *value*, not merely priority --- the
shift from knowing what is unresolved to knowing what is most worth resolving. Each item is
scored:

```
score = 0.30 * info  +  0.40 * impact  +  0.20 * enable  -  0.30 * cost
```

where `info` is the information yield of the op, `impact` is the number of downstream
claim-graph dependents of the target, `enable` is how much the move unblocks, and `cost` is
the op's expense. The weights live in `_OPP_WEIGHTS`; per-op `info`/`cost` priors in
`_OPP_INFO`/`_OPP_COST`.

# The execution bridge

`execute_plan(bundle, inv)` resolves every next move to a concrete, gated action:

```
{source, action_type, score, executor, command, consequence, auto_safe, state}
```

Each frontier op maps to an executor, a command template, and a **consequence class**:

| op          | executor                      | command (template)                                   | consequence       | auto |
|-------------|-------------------------------|------------------------------------------------------|-------------------|:----:|
| revalidate  | snapshot-validations          | `discover snapshot-validations <inv>`                | safe              | yes  |
| test        | run-study                     | `vivarium-workbench run study <slug> --workspace <ws>`| simulation        | no   |
| branch      | seed-from-followup + run-study| `viva-study seed-from-followup ...; vivarium-workbench run study ...` | simulation+study | no |
| reconcile   | set-verdict                   | `discover set-verdict <slug> <derived> --rationale ...`| review           | no   |
| steer       | expert                        | (none --- an expert decision)                         | human-only        | no   |
| synthesize  | author finding + resolve      | `viva-study findings ...; discover resolve ...`      | human-only        | no   |

Only a `safe` (side-effect-free) action is `auto_safe`.

# Autonomous execution and AI-driven decisions

`execute_action(ws, slug, *, autonomous=False, runner=None, decider=None, target=None)`
carries out the top (or a targeted) action, gated by consequence:

- A `safe` action always runs (re-snapshot the accepted validations).
- A **consequential** action (`simulation` / `simulation+study`) runs only with
  `autonomous=True`, by invoking its real executor command as a subprocess (`runner`,
  injectable for tests; default a real subprocess in the workspace). The `<ws>` placeholder
  is filled with the workspace root; a command still carrying an unfillable placeholder
  (e.g. a branch op's `<parent>`/`<proposal>`) is gated rather than run.
- A **`steer`** decision is normally `human-only`, but when an AI `decider` is supplied and
  `autonomous=True` the AI drives it: `decider(target, detail)` returns the option that
  maximizes discovery plus a rationale, recorded as an `[ai-driven]` resolution so the
  decision is made and its gated study becomes ready. The engine itself never reasons ---
  the `decider` is the AI, injected by the caller (a skill, an agent, or the session).
- A `review` (verdict overwrite) or a `human-only` action with no decider is never
  auto-run; it is handed back.

`target=` lets a caller drive a *specific* frontier item rather than `plan[0]` --- needed
because a high-value verification run can rank ahead of an expert decision, so the top-only
bridge would never reach the decision.

Executed actions append to the investigation's `executed_actions` log and the frontier is
re-derived so the caller sees the change.

The CLI exposes this: `discover execute <inv> [--execute] [--autonomous] [--ai-decide]`,
where `--ai-decide` wires a decider that shells out to `$VIVA_DECIDER_CMD` (an agent that
reads `{target, detail}` JSON and returns `{choice, rationale}`).

# Persistence and renewal

The projection is read-only and recomputable on demand. Three operations write.

**Resolutions.** `record_resolution(inv, kind, target, rationale, by?)` appends a
`{kind, target, rationale, by?}` record (idempotent on `(kind, target)`), discharging a
frontier item. A rationale is required --- a resolution documents *why* an item is settled,
it does not silently suppress it.

**`cycle_state` (via `persist_cycle`).** `build_cycle_state` projects a slim, actionable
summary --- closure, frontier size, next action, top value-ranked opportunities, the
suggestions census, the diagnosis flags and validator pass-rate, the execution plan, the
validator census, and drift (divergences, stale validations). `persist_cycle` writes this
`cycle_state` into `investigation.yaml`, re-reading on disk first so concurrent authored
edits are never clobbered. The full `knowledge`/`argument`/`narrative` projections are not
dumped --- they are recomputable via `run_cycle`.

**Narrative renewal (persist-time).** Because the cycle is derive-first and authors no
prose, the authored `executive` block can drift from what the cycle has resolved.
`persist_cycle` reconciles it: a `decisions_needed` entry whose target is now in
`resolutions` is moved to `executive.decisions_resolved` and dropped from the open list, so
the narrative cannot keep listing a resolved decision as open. The same pass retires the
dead data-model fields (`knowledge_cycle`, `plan_acts`). Until the next persist, the
hygiene guard surfaces the drift on the frontier.

# The completion map

`build_completion_map(ws, slug)` assembles the "what remains to complete this cycle" view
in one object: closure, the **verification gates** (`pending_gate` items --- gates met by
verdict only), the **decisions that gate the next studies**, the suggested follow-ups, and
the ordered next-step commands. `discover complete <inv>` renders it.

# The crank lifecycle

A complete turn:

1. **Load** --- `load_cycle_inputs(ws, slug)` reads the investigation and its member
   studies from disk.
2. **Project** --- `run_cycle` builds the bundle.
3. **Locate** --- `frontier` + `closure`.
4. **Diagnose** --- `diagnose`.
5. **Rank by value** --- `opportunities`.
6. **Suggest** --- `suggest_studies` (each proposal tied to a parent study, `ready` or
   `awaiting_expert`).
7. **Plan** --- `execute_plan`.
8. **Decide / execute** --- `execute_action`, gated by consequence (safe / simulation /
   review / human-only; AI-driven steer via a decider).
9. **Record / renew / persist** --- resolutions, `cycle_state`, decision renewal, dead-field
   retirement.
10. **Re-crank** --- repeat until `closure.closed`.

# Command surface

| verb                                     | effect                                                                 |
|------------------------------------------|------------------------------------------------------------------------|
| `discover crank <inv>`                   | project a turn and print the frontier + next action                    |
| `discover diagnose <inv>`                | why the cycle is stuck (bottleneck flags)                              |
| `discover suggest <inv>`                 | proposed new studies, each tied to a parent                            |
| `discover opportunities <inv>`           | the frontier ranked by value                                           |
| `discover complete <inv>`                | the completion map in one view                                         |
| `discover execute <inv> [--execute] [--autonomous] [--ai-decide]` | the recommendation->action bridge; run the next move, gated by consequence |
| `discover set-verdict <slug> <v>`        | author a canonical verdict on a study                                  |
| `discover resolve <inv> <kind> <target>` | record a resolution discharging a frontier item                        |
| `discover snapshot-validations <inv>`    | accept the current validator state (staleness baseline)                |

# Invariants and correctness properties

1. **Reproducibility.** The bundle is a pure function of the investigation and its studies;
   re-running `run_cycle` with the same inputs yields the same bundle.
2. **Authored authority.** An authored verdict, knowledge block, or argument block always
   overrides the derived projection; an empty authored value never clobbers a derived one.
3. **Axis independence.** Progress never feeds the verdict; the verdict never reads
   execution status.
4. **Epistemic separation.** No validator record's `scientific_judgment` is inferred from
   its `execution_status` or vice versa.
5. **Uniform discharge.** A frontier item of any kind is removed iff a matching
   `{kind, target}` resolution exists, with a non-empty rationale.
6. **No implicit consequence.** No `review`, `human-only`, `simulation`, or
   `simulation+study` action runs without an explicit gate (`--autonomous`, a decider, or a
   human).
7. **No false signal.** A gate recorded in any of a study's runs is seen (behaviors union);
   a `qualified`-refines-`supported` difference is not a divergence; a resolved decision is
   not listed as open after persist.

# Appendix: the "stop flagging non-problems" refinements

Three refinements ensure the frontier reflects only genuine work:

- **Behavior-gate union across runs.** `_study_behaviors` buckets acceptance-behavior
  outcomes against the union of outcomes across a study's runs (canonical last), not a
  single canonical run --- so a gate computed in a sibling composite run is not reported
  PENDING.
- **Divergence as answer-conflict.** `canonical_verdict` flags `diverges` only when the
  authored and derived verdicts disagree on the answer (`supported` and `qualified` share
  the "holds" answer), not on any inequality.
- **Persist-time decision renewal.** Resolved `decisions_needed` are archived to
  `decisions_resolved` on persist, and the hygiene guard surfaces any resolved-but-listed
  decision in the interim.

Each targets a case where the engine previously flagged work that was already done or was
not in fact a conflict. A frontier is only worth acting on if every item on it is real.
