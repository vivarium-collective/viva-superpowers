# viva-investigate — detailed reference

Companion reference for **SKILL.md** in this skill directory. SKILL.md holds the
subcommand specs, the common prelude, the atomic-write patterns, and the honesty
invariants an agent needs to run `/investigate`; this file holds the conceptual
preamble that was moved out of it to keep the command surface lean. All of it
restates — and points at — canonical docs:

- The **Investigation graph** (discourse graph) and the `relation:` enum live in
  [`docs/concepts/vivarium-workbench-model.md`](../../docs/concepts/vivarium-workbench-model.md#the-investigation-graph-discourse-graph).
- The **arm / Study-vs-Arm boundary** and the consolidation invariants live in
  [`docs/concepts/investigation-graph-ontology.md`](../../docs/concepts/investigation-graph-ontology.md).
- The **per-dimension rigor spec** (per-study + investigation-level) lives in
  [`docs/conventions/rigor-checklist.md`](../../docs/conventions/rigor-checklist.md).

SKILL.md keeps a 2-4 line summary of each section below with a pointer here.

## Layout (flat writer, nested-aware resolver)

The dashboard's study-create endpoint — the **authoritative writer** — creates
each study **flat** at `$STUDIES_DIR/<slug>/study.yaml` (the conventional
`studies/<slug>/`, or `workspace/studies/<slug>/` when the workspace `layout:`
relocates it). As of vivarium-workbench 0.4.1 it does **not** write the nested
`investigations/<inv>/studies/<slug>/` tree. The investigation's
publication/report lives at `investigations/<inv>/reports/` (per-investigation —
there is **no global repo-wide report**).

- **Resolve a study dir** (nested- and flat-aware): tooling checks the nested
  path `$INVESTIGATIONS_DIR/<inv>/studies/<slug>/` first, then the flat
  `$STUDIES_DIR/<slug>/`. New studies land flat; the nested path resolves only
  after a repo is migrated.
- **The nested layout is a convention/migration target, not the default writer
  output.** A repo adopts it by running `viva-migrate-nested`, which relocates
  flat studies under their investigation and writes the `investigation: <inv>`
  back-ref. Until then, studies stay flat and carry membership only via the
  investigation's `studies[]` list.

Where older text below says "create under the nested path" or implies the
writer produces `investigations/<inv>/studies/<slug>/`, read it as the
post-migration convention — the live endpoint writes `$STUDIES_DIR/<slug>/`.

---

## The Investigation graph (discourse graph)

The dashboard reframes the investigation page as an **Investigation graph**: a discourse/knowledge graph whose nodes are its member studies and whose edges are their `parent_studies` dependencies. The framing is **mechanism-centered** — the investigation's primary artifact is an *evolving mechanistic understanding* of the biology; each study is a **knowledge-producing operation** that generates evidence which updates confidence in mechanism elements. Read each node as **Question (Asks) → Evidence (Finds) → Confidence**:

- **Asks** — the study's `question:`.
- **Finds** — the study's `claim:` (one-line headline of what we now believe), falling back to the top `findings[].summary`.
- **Confidence** — the study's `confidence:` badge (`Accepted | Investigating | Planned | Refuted`), derived from the 6-axis status when unset.
- **Display name** — the study's `title:` (slug, prefix-stripped + humanized, when unset).

These are **study-level** fields — author them per member study via `/study` (see [viva-study → Investigation-graph fields](../study/SKILL.md)). At Design, set each study's `title:` and wire `parent_studies` with a `relation:` (`builds-on` default / `tests` / `motivates` → solid edge; `alternative-to` → dashed edge). At Evaluate/Decide, set `claim:` and (when the derived value is wrong) `confidence:`.

**Confidence rollup.** The investigation aggregates over its members: the graph badges each node with its study-level confidence, and the investigation's `executive.verdict_status` is the higher-level rollup a reviewer lands on first. Keep the two consistent — a `Refuted` study should be reflected in the investigation verdict.

**State-first opening — `executive` is the single source.** The investigation opening is state-first and is rendered from `executive: {what_is_this, verdict, verdict_status, verdict_detail, decisions_needed:[{question, context}]}`. The **same `executive` block** drives the report's Executive summary — do not maintain a second copy. Update `verdict` / `verdict_status` (`in-progress | passed | complete | blocked | failed | planning`) as member studies pass or fail. The framing + argument come from `question:`, `hypothesis:`, and `scientific_argument: {main_claim, evidence_for[], evidence_against[], key_figures[], caveats[]}`.

---

## Multi-realization claims

An investigation may hold **more than one realization of the same claim** at
different fidelity levels — e.g. a phenomenological realization (a scalar
rate/knob) alongside a mechanistic realization (the same behavior emergent
from a finer-grained process). Both are first-class members; the finer one
does not replace the coarser one, it **refines** it.

- Declare the relationship with `parent_studies[].relation: refines` (see the
  `relation` enum in [viva-study → Investigation-graph fields](../study/SKILL.md)),
  pointing from the finer (refining) study back to the coarser one it refines.
- On the finer study, name the coarser realization's passing behaviors it must
  reproduce, and whether it currently does:

  ```yaml
  refinement:
    must_preserve:
      - {coarse_study: <coarse-slug>, behavior: <coarse-behavior-name>, note: "…"}
    satisfaction: PASSED   # PASSED | FAILED | PENDING
  ```

- **Re-check `satisfaction` whenever either realization changes** — a `refines`
  edge is a standing obligation, not a one-time note at authoring time.

---

## Design principles — build the investigation as a MAP OF BOTTLENECKS

An exploratory campaign is strongest when it exposes *dependencies, failure
regimes, and discriminating experiments*, and weakest when it produces one
successful narrative. A passing gate means the model satisfies a prespecified
criterion under its assumptions — it does NOT establish that the real transition
occurred. Carry these investigation-level expectations (from the viva-genesis
Scientific Enrichment Plan §14):

1. **Phase maps, not representative trajectories.** Every major claim identifies
   its PASS *and* its FAILURE regions. At the study level this is the Decision
   view (see [viva-study → Three-view standard](../study/SKILL.md)); at the
   investigation level, the `scientific_argument` should read the failure
   regions as findings, not footnotes.
2. **Provenance class on every parameter** — measured vs calibrated vs
   extrapolated, carried explicitly (the per-study `cites` / `provenance: theory`
   / `proposed_inputs` discipline rolls up here).
3. **Conservation accounting** — matter, charge, and free-energy ledgers across
   the composed processes, with losses bounded and reported.
4. **Feature ablations find NECESSARY (not merely correlated) mechanisms.**
   Include member studies that remove one mechanism at a time (`kind: ablation`
   or an `ablation:` block naming what's removed) and show the claim break —
   that's how you distinguish a load-bearing mechanism from a bystander.
5. **Negative controls that fail the same gates.** At least one adversarial
   member (`kind: adversarial`) — a system that should NOT qualify (a
   vent-specificity / non-vent control) and passes the gate by rejecting it.
6. **Shared modules across scenarios.** Multiple scenarios (deep/shallow vents,
   terrestrial geothermal, photochemical) reuse the same composite modules and
   are compared through the same gates (see the composites-are-reusable-modules
   rule in [viva-model](../model/SKILL.md)).
7. **Negative results are scientific output.** A broken transition is a finding,
   not a failure to hide — it identifies an experimentally targetable
   bottleneck. Frame a member study that *refutes* its hypothesis as a result
   (`confidence: Refuted`, a `claim:` that states what broke), and let the
   investigation `verdict` carry it honestly (the status triad takes the
   weakest honest reading — see below).

---

## Investigation-owned inputs (schemas + migration)

**Investigation-owned inputs.** An investigation owns its datasets/references under `investigations/<inv>/inputs/` (e.g. `inputs/datasets/<file>`), recorded in `investigation.yaml`:

```yaml
inputs:
  datasets:
    - inputs/datasets/beulig.csv
  references: []
  expert_docs: []
```

Repo-wide source packages and shared/unused inputs stay global (repo-level `datasets/`, `references/papers.bib`). To migrate existing repo-level datasets, run the `viva-migrate-inputs` console script (`--workspace <ws> [--apply]`): it assigns a dataset to an investigation only when exactly ONE investigation's studies reference it (by filename in `study.yaml`); multi-investigation and unused datasets are reported and left global. Default prints the plan; `--apply` performs the `git mv` and updates `investigation.yaml`.

**NEVER silently add an input the expert did not provide.** `inputs.references`, `inputs.datasets`, and `expert_docs` are the *provided* inputs — things the expert supplied or explicitly approved. If, while working, you find yourself wanting to cite a paper, invoke a mechanism, or lean on a parameter the expert did **not** give you, do **not** add it to `inputs.` and do **not** weave it into the prose as fact. Instead record it under `proposed_inputs:` with `status: pending`, plus the `provenance` (which commit / why it came up) and the `rationale` (what you used it for). The expert then Accepts or Declines each item in the report; on Accept the dashboard promotes a `kind: reference` item into `inputs.references` (a `kind: mechanism` is marked accepted for a human to integrate), on Decline it is marked declined and left out. This keeps the agent from quietly importing outside claims as if they were expert-sanctioned.

```yaml
proposed_inputs:
  _note: "Why this block exists — agent-suggested inputs the expert did NOT provide."
  items:
  - id: <slug>                 # stable id; reference ids double as the bib-key on accept
    kind: reference            # reference | mechanism
    citation: "..."            # kind=reference: the citation text
    summary: "..."             # kind=mechanism: what the mechanism is
    proposed_by: agent
    proposed_at: '2026-06-08'
    related_study: <study-slug>
    rationale: "what it was used for"
    provenance: "which commit / why it came up; NOT provided by the expert"
    status: pending            # pending | accepted | declined  (expert sets via the report)
```

---

## Acceptance criteria — full guidance

An `acceptance_criteria: []` left empty until results exist is the single most
common way an investigation ends up grading itself post-hoc — a reviewer reads
criteria written after the runs as regression pins dressed up as acceptance.
Populate `acceptance_criteria[]` at scaffold time, **before any member study
runs**, with two kinds of entry:

- **Pre-stated directional priors** — what direction/magnitude is expected if
  the hypothesis is right (e.g. "raising adhesion asymmetry should monotonically
  increase the sorting index"), each linked to the member study behavior_test
  that will gate it (`{study: <slug>, behavior: <name>}`). Mirror each prior into
  that study's `preregistered:` block and mark the gating test
  `gate_class: acceptance_criterion` (see
  [viva-study → Born-rigorous defaults](../study/SKILL.md)).
- **Order-of-magnitude EXTERNAL ANCHORS** — literature values that bound what a
  plausible result looks like (e.g. "sorting completes within ~10²–10³ MCS at
  Graner–Glazer scale"). Flag each explicitly as an **anchor** — a sanity bound
  the result is *compared against* — never as a calibration target the model is
  *tuned to hit*. Source anchors via `/tests cite-bands`; an anchor the
  expert did not provide and you cannot cite is a `proposed_inputs` pending
  item, not a fact.

A criterion first conceived after the runs exist may still be recorded — but
honestly, as a `regression_pin` on the member study, never back-dated into this
list as acceptance.
