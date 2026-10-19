# RFC-0003 · Investigation Graphs Breathe

**Branch–Consolidate as the core development rhythm of an investigation graph**

| | |
|---|---|
| **Status** | Draft |
| **Date** | October 2026 |
| **Relates to** | RFC-0001 (Agentic platform) · RFC-0002 (Typed investigation substrate) |
| **Worked example** | origins-of-life-vent (~49 → ~13 studies) |

---

## Summary

An investigation graph is not built at a fixed granularity. It develops by a repeated
**divergent → convergent** rhythm: you **branch** many small, falsifiable probe-studies to
explore a concept while you don't yet know which angle matters, then **consolidate** those
probes into one multi-arm study once the concept is understood. This RFC names that rhythm,
identifies the two invariants that make consolidation *content-lossless* — the **arm** as the
unit of evidence, and the **audit lint** as the content-preservation contract — and specifies
how to codify the rhythm as first-class graph operations, a typed schema, and tooling.

Consolidation is **destructive and non-reversible** at the level of graph *nodes*: the
fold-in studies' `study.yaml` nodes are deleted and are not recoverable as live nodes. It is
**lossless at the level of scientific content**: every fold-in's artifacts, figures, and
findings are moved into the consolidated study, and its verdict, matched-null, run-ids, and
finding-ids survive inside its **arm** (and in git history). The thesis in one line:
**study granularity is a function of epistemic maturity, and the graph should breathe.**

## Vocabulary

This RFC uses the shared investigation vocabulary:

- **Investigation** — the overarching inquiry and its evolving questions and synthesis.
- **Study** — the primary unit and primary visible node: a question, methods, evidence, and
  interpretation.
- **Arm** — within a consolidated study, a **folded study**: an experimental condition that
  was once its own node and now carries its identity and result as an arm (see §5).
- **Run** — an immutable execution record.
- **Finding** / **Claim** / **Assessment** — an observed result / a scoped proposition / an
  evidence-based verdict with rationale.

The ontology stays **Study-centric**: studies merge into bigger studies. There is no separate
grouping layer and no reversible view — consolidation *re-granulates the nodes themselves*.

## Motivation

In the origins-of-life campaign the study graph grew to ~49 nodes. Most were not independent
questions — they were probes of a smaller set of concepts: a baseline, its `-alt` ablation, a
`-cal` calibration, a parameter sweep, a *sharpened* re-do at higher fidelity, a planned
extension. The campaign in fact carried **two parallel arcs over the same concepts** — a
low-fidelity scaffold arc (`og-00…08` + variants) and a sharpened spine (`og-27…37`, the gate
members) — plus two planned programs. So the graph had proliferated, and the natural next move
was to *re-granulate*: fold each concept's probes into one multi-arm study.

This is not a tidiness chore. It is a recurring, structural phase of model-graph development,
and it has been happening — correctly, under pressure — without being named. Naming it lets us
(a) decide *when* to do it, (b) do it *safely* (without losing evidence), and (c) build tooling
that makes it cheap. A model that cannot be re-granulated ossifies at whatever granularity it
happened to reach first.

## The model

### 1. The breathing rhythm

Inquiry under uncertainty alternates between two motions:

- **Branch (divergent).** When a concept is not yet understood, the honest move is to spawn
  many *small, falsifiable probes*. Each is cheap and safe to add, and you add them *precisely
  because you don't yet know which angle is load-bearing*. The graph inflates on purpose.
- **Consolidate (convergent).** Once the concept is understood, the probes **merge into one
  multi-arm study**: each probe becomes an *arm* (a piece of evidence), matched-nulls and
  honest-negatives are preserved as arms, the old nodes are deleted, and the headline claim is
  bounded by the sharpest arm. You state the concept *with its full evidence*. The graph
  deflates — the node count genuinely drops.

The same rhythm appears throughout inquiry and engineering: spike branches → merge to main; many
experiments → a review paper; mutate/explore → select/consolidate. It is the breath of a search
process that must stay honest about what it has and hasn't established.

### 2. Granularity as epistemic maturity

A study node *should* hold "one concept with its evidence." But *what counts as one concept* only
becomes clear through exploration. Early, the right granularity is fine (many probes, because the
concept boundaries are unknown); late, the right granularity is coarse (one multi-arm node,
because the concept is known). **Granularity is therefore not a property of the domain — it is a
readout of how much you currently understand.** The graph's tendency to proliferate is correct
(every new question is a cheap, honest node); its need for periodic consolidation is also correct
(understanding coarsens the right unit).

### 3. Two layers: exploration and spine

An investigation has two layers:

- the **exploration layer** — many fine probe-nodes, the search;
- the **spine layer** — the consolidated studies, the result.

This is why the origins-of-life 49 → ~13 maps almost **1:1 onto the gate spine**:
*the gate spine IS the consolidated graph, and the proliferated studies are the exploration that
discovered it.* Consolidation is **projecting the exploration onto the spine it revealed**. You
do not know the spine in advance; you discover it by branching, then you present it by folding.

### 4. Fidelity as the vertical axis — a separate dimension from support

The scaffold arc and the sharpened arc are **the same concept at two resolutions**. Fidelity
(`evidence_tier`: `conceptual_demonstration` → `mechanistic_prediction`) is the vertical axis of a
concept. Fidelity is **not** the same as evidential support: **higher fidelity does not
automatically imply stronger evidence** — a `calibrated`/mechanistic arm describes the model's
character, not the strength of the claim it underwrites. The governing rule: **a claim is only as
strong as its best test.** The highest-fidelity arm sets the honest ceiling (the headline
verdict); lower-fidelity arms are corroborating evidence *beneath* it, never allowed to inflate
the claim past what the sharpest test supports.

### 5. The arm is the content-lossless-refactor unit

Consolidation is **destructive at the node level but a squash that keeps every commit's
authorship at the content level.** Each fold-in becomes an *arm* carrying its own identity and
result:

```yaml
arms:
  - source_study: og-35-chemical-energy-coupling
    concept_role: "energy-carrier-vs-gradient-only"
    fidelity: mechanistic_prediction      # = evidence_tier
    verdict: qualified
    gate_status: passed
    matched_null: matched-null-equal-feeds
    composite: proto_energetics
    run_ids: [ ... ]
    finding_ids: [ ... ]
    canonical: true                        # the headline-setting arm
```

The arm **is a folded study** — not merely a condition authored inside a study from the start.
Because each arm preserves its source study's verdict, its matched-null, its fidelity, and its
run provenance, the fold **loses no content** even though it deletes the node. The old
`study.yaml` is gone (non-reversibly), but what it established travels into the consolidated
study and git history. The arm is what lets the graph breathe in without forgetting what the
breathing-out discovered.

## Operations

Two inverse operations on the graph, to be made first-class:

- **`branch(concept) → node`** — add a probe-study off a concept (baseline / ablation /
  calibration / sweep / sharpened re-do / planned extension). Cheap, honest, divergent.
- **`consolidate(nodes) → multi-arm node`** — merge same-concept nodes into one study. The
  mechanics, as executed in the worked example:
  1. gather each fold-in as an `arm`, plus its behaviour-tests + run outcomes + findings (pinned
     to run-ids) so the evidence travels with the claim;
  2. `git mv` artifacts/viz into the consolidated study, preserving provenance;
  3. **delete the folded `study.yaml` files** and de-roster them — **non-reversibly**;
  4. **repoint every reference** to a folded slug — gate members, pipeline-gate prerequisites,
     acceptance criteria, parents, handoff-table plan ids — to the consolidated study; the
     consolidated study claims its **canonical arm's** `plan_id`;
  5. the consolidation that folds a study **owns** repointing every reference to it, across all
     three path layers below.

Consolidation is **non-reversible**: there is no `split`/`reopen` that re-promotes an arm back
into a live node. If a settled concept must be re-explored, you **branch new probe-studies** off
it — the old folded nodes do not return.

## Invariants — the consolidation contract

A consolidation is **valid iff**:

1. **Content-lossless (audit lint green before and after).** Zero dangling references, every
   arm's evidence (tests + runs + findings) present, every gate member resolvable. The lint *is*
   the content-preservation contract — not a separate check but the definition of a valid fold.
   The lint must **hard-fail on an unparseable `investigation.yaml`**: a silently-skipped check
   is worse than none.
2. **Honest headline.** The consolidated verdict is bounded by the **highest-fidelity (canonical)
   arm**; lower-fidelity arms may corroborate but never inflate it, and **no headline silently
   overwrites a constituent arm's verdict**.
3. **Nulls survive.** Every matched-null and every honest-negative is preserved *as an arm, with
   its own `gate_status`* — never smoothed into the headline. A refuted secondary result stays
   `refuted`/`failed` inside the study.
4. **Fidelity ≠ support.** The evidence indicator (`demonstration`/`mechanistic`/`calibrated`) is
   recorded as model character; it does not by itself raise the verdict. Execution success
   (progress `completed`) is not scientific support (a verdict).
5. **Cross-cutting nodes stay standalone** (see taxonomy) — they are not folded into any one gate.
6. **All references repoint across three path layers** (see "Three path-validation layers").

## State categories

Three independent dimensions travel with every study and arm:

- **Progress** — `proposed`, `planned`, `running`, `completed`, `failed`.
- **Verdict** — `unassessed`, `supported`, `qualified`, `inconclusive`, `refuted`.
- **Evidence indicators** — `demonstration`, `mechanistic`, `calibrated` (a *separate* dimension;
  calibration/validation/uncertainty are different axes again).

Execution success is not scientific support; higher fidelity does not automatically imply
stronger evidence.

## Node taxonomy

Not every node consolidates into a gate. Two roles:

- **Concept nodes** — fold into the gate they establish (A1 network, B spatial, C
  compartmentation, …). Most nodes.
- **Cross-cutting controls** — validate *every* gate and must never be buried inside one:
  - a **keystone refutation** (e.g. endogenous autocatalysis, refuted off-spine) whose verdict
    must not gate downstream concepts;
  - a **specificity control** (e.g. does the vent *specifically* win vs alternatives) that
    falsifies the whole campaign, not one gate.

## Three path-validation layers

When consolidation `git mv`s committed artifacts into the consolidated study, stale hardcoded
paths appear in **three distinct places, each needing its own check because no single one catches
all three**:

1. **`study.yaml` references** → caught by the **audit lint** (dangling-ref).
2. **Test files** with hardcoded artifact paths (e.g. a phase-5 "committed artifacts carry the
   headline" test reading `<slug>/artifacts/*.json`) → caught only by running the **full test
   suite**, not the lint.
3. **Runtime source** — evaluator / viz modules that read a study's committed artifacts at
   render/eval time → caught by **neither the lint nor CI** (it is a runtime read, not
   test-covered), so it needs a dedicated **source-path-resolves** check: grep the package source
   (not just tests) for every folded study's artifact paths and assert they resolve post-move.

**Lint, full-suite, and source-path-resolves are three layers because each catches a different
class of moved-artifact stale path.** A fold is not done until all three are green.

## Lifecycle & readiness

A concept moves `exploring → understood → consolidated`. The signal that it is **ready to
consolidate**: its probes have stopped moving the verdict (diminishing returns), a sharpened arm
exists to bound the headline, and the matched-nulls are in. Consolidating *before* this is
premature (you fold away exploration you still need); consolidating *long after* leaves the graph
needlessly inflated. The readiness signal is detectable and should be surfaced, not eyeballed.

## Codification plan

In rough order of leverage:

1. **Promote `arms` to a first-class schema field** (`study.schema.json` in viva-template) — turn
   "multi-arm study" from a session convention into a typed contract (fits RFC-0002's substrate).
2. **Name `branch` / `consolidate` as graph operations** — a `/viva-consolidate` skill +
   workbench action implementing the mechanics above, with the lint as the acceptance gate.
3. **Formalize the lint as the consolidation contract** — state content-losslessness as the
   definition of a valid fold; the dangling-ref / verdict-evidence / gate-member / artifacts
   checks *are* it; the source-path-resolves check closes the runtime-read gap.
4. **Add a consolidation-readiness view** — the workbench flags same-gate clusters that have
   proliferated *and* whose verdict has stabilized across probes, so you know *when* to breathe in.
5. **This RFC** — the methods document the above derive from.

## Worked example — origins-of-life-vent, 49 → ~13

The campaign's 49 studies consolidate into ~13 concept studies mapping 1:1 onto the gate spine
(A1/A2/B/C/D/E) plus a geochemistry split and two cross-cutting controls. Each consolidated study
is multi-fidelity and multi-arm; every matched-null is an arm; the A2 autocatalysis keystone stays
off-spine and refuted; og-08's superseded "no-subset-sufficient" reading is preserved as an
earlier-fidelity arm, resolved by the per-driver rebuild. The first consolidations
(`og-energetics` 5→1, `og-heredity` 3→1, `og-autocatalysis-A2` 2→1) landed with the audit lint
green and large net line reductions — empirical confirmation that the fold is content-lossless
when the contract holds, even though the fold-in nodes are deleted non-reversibly.

## Relation to prior RFCs

- **RFC-0001 (Agentic platform)** — the agents that branch and consolidate; this RFC gives them a
  named operation and an acceptance contract to execute against under review (agents *propose*;
  evidence checks and a human *gate* the structural change and any claim).
- **RFC-0002 (Typed investigation substrate)** — the `arms` field and the consolidation contract
  are typed extensions of that substrate; promoting `arms` to the schema is the concrete tie-in.

## Open questions

1. **Re-exploration after a fold.** Consolidation is non-reversible, so re-opening a settled
   concept means **branching fresh probe-studies**, not resurrecting folded nodes. What triggers
   that, and how does a new probe cite the arm it is re-testing?
2. **Automated readiness detection** — formalizing "the verdict has stopped moving across probes"
   into a computable signal.
3. **Fidelity × verdict aggregation** — the precise rule for how arm verdicts at different
   fidelities compose into a headline (currently: highest-fidelity arm bounds it; is that always
   right when a low-fidelity arm is refuted?).
4. **Granularity drift** — over a long campaign, how often should the graph breathe, and can the
   readiness view schedule it rather than relying on a human noticing the list has grown.

## See also

- Operational procedure: [`/viva-consolidate`](../../skills/viva-consolidate/SKILL.md) — the Consolidate operation, executed against the contract.
- Ontology formalization: [`docs/concepts/investigation-graph-ontology.md`](../concepts/investigation-graph-ontology.md) — the `arm` category, the Study/Arm boundary, and the invariants tied to the execution × verdict status axes already in the codebase.
