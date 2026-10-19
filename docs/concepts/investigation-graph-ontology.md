# Investigation-graph ontology — arms, the Study/Arm boundary, and the consolidation invariants

A **conservative** formalization of the Branch–Consolidate model from
[RFC-0003](../rfcs/RFC-0003-investigation-graphs-breathe.md), tied to the status axes
already in the codebase. It stays **Study-centric**: there is no new grouping layer and no new
visible edge type. The only addition is the **arm** — a folded study — as the unit of evidence
inside a consolidated study. Prefer this small vocabulary over more node/edge types.

This doc extends, and does not replace, the canonical data-model vocabulary in
[`vivarium-workbench-model.md`](vivarium-workbench-model.md) (Workspace · Study · Baseline ·
Variant · Intervention · Run · Visualization).

## The categories (shared vocabulary)

| Category | Definition | On-disk today |
|---|---|---|
| **Investigation** | Overarching inquiry; evolving questions + synthesis. | `investigations/<name>/spec.yaml` |
| **Study** | Primary unit *and* primary visible node: question, methods, evidence, interpretation. | `studies/<slug>/study.yaml` |
| **Arm** | A **folded study** inside a consolidated study: an experimental condition that once was its own node and now carries its identity + result as an arm. | *proposed* `arms:` block (below) |
| **Run** | Immutable execution record. | `runs.db` rows, `run_ids` |
| **Finding / Claim / Assessment** | Observed result / scoped proposition / evidence-based verdict with rationale. | `findings[]`, verdict axes |

## The Study-vs-Arm boundary (the principal design decision)

A new probe becomes a **separate Study** when it asks an *independently meaningful scientific
question*; otherwise it belongs as an **arm** in an existing study. State it explicitly because
it is the one judgment call consolidation turns on, and — since consolidation is non-reversible —
the one most worth getting right.

| Probe | Node | Rationale |
|---|---|---|
| A genuinely new question | **Study** | Independently meaningful; deserves its own visible node. |
| A baseline's ablation / calibration / parameter sweep | **Arm** | Just another *condition* on the same question. |
| A sharpened, higher-fidelity re-run of the same question | **Arm** (often `canonical`) | Same concept at a higher resolution; sets the honest ceiling. |
| A keystone refutation or a specificity control | **Study (standalone / off-spine)** | Cross-cutting: validates *every* concept, must never be buried in one. |

**Default to Study when in doubt** — folding is destructive and non-reversible (see below).

## Consolidation is destructive and non-reversible

`consolidate(studies) → one multi-arm study`:

1. each fold-in becomes an `arm` (with its tests + `run_ids` + `finding_ids`);
2. its artifacts/viz are `git mv`'d into the consolidated study;
3. the fold-in `study.yaml` nodes are **deleted** and de-rostered — **non-reversibly**;
4. all references repoint to the consolidated study, which claims its **canonical arm's** `plan_id`.

The node count genuinely drops. There is **no `split`/`reopen`** that re-promotes an arm to a
live node. To re-explore a settled concept, **branch new probe-studies** off it. The deletion is
lossless in *content* (artifacts moved, results in arms + git history) but final in *structure*.

## The two axes already in the code (reuse, don't reinvent)

The honesty invariants ride on status axes the codebase already derives — this ontology adds no
parallel status vocabulary.

- **Execution axis — observable, derived from runs** (`viva_superpowers/study_status.py`):
  `derive_simulation_status` → `not_run` / `running` / `ran`; `derive_evaluation_status` →
  `not_evaluated` / `evaluated`. These are *derive-on-read* — they reflect what actually ran, so
  an arm's execution state can't drift from a hand-set field.
- **Verdict axis — the scientific assessment**: per-study `gate_status` and the investigation
  roll-up in `viva_superpowers/investigation_status.py` (`roll_up_acceptance` →
  `passing` / `passing-with-caveats` / `failing` / `in-progress`), which maps run outcomes
  (`pass`/`fail`/`partial`) to criterion results.

RFC-0003's state categories map onto these as:

| RFC-0003 category | Code axis |
|---|---|
| **Progress** `proposed/planned/running/completed/failed` | execution axis (`simulation_status`, run `status`) |
| **Verdict** `unassessed/supported/qualified/inconclusive/refuted` | `gate_status` + `roll_up_acceptance` criterion results |
| **Evidence indicator** `demonstration/mechanistic/calibrated` | `fidelity`/`evidence_tier` on an arm — a *separate* dimension (see below) |

**Execution success is not scientific support**, and the two axes are kept orthogonal precisely
so that a `ran`/`completed` arm can still be `refuted`. `study_status.py` already flags the
reverse drift (a "planning" status on a study that has actually run) — the same derive-on-read
discipline is what keeps an arm's recorded verdict honest against its runs.

## The invariants (what a valid consolidation must preserve)

Content-level honesty survives the destructive fold:

1. **Content-lossless.** Every artifact, figure, finding, run provenance, and verdict survives
   (in its arm + git history). Node deletion is expected; evidence loss is a breach.
2. **Honest headline, bounded by the canonical arm.** The consolidated verdict is bounded by the
   highest-fidelity (`canonical`) arm; lower-fidelity arms corroborate but never inflate it, and
   **no headline silently overwrites a constituent arm's verdict**.
3. **Nulls and negatives survive as arms.** Every matched-null and honest-negative keeps its own
   `gate_status` (`failed`/`refuted`) — never smoothed into the headline.
4. **Fidelity ≠ support.** The evidence indicator is model character, not claim strength; higher
   fidelity does not automatically raise the verdict.
5. **Cross-cutting controls stay standalone.** Keystone refutation off-spine; specificity control
   standalone.
6. **Provenance + valid references.** References survive regrouping and resolve across the **three
   path-validation layers** (study.yaml → audit lint; test files → full suite; runtime source →
   source-path-resolves grep). See RFC-0003 and the `/viva-consolidate` skill.

## Proposed schema stub — `arms:` (NOT implemented; flagged for human decision)

Promoting `arms` to a first-class schema field is RFC-0003's highest-leverage codification step,
but it is a schema change and **out of scope for this docs-only pass**. This section **proposes**
the minimal, non-invasive shape and **flags it for a human decision** rather than editing any
schema or the scaffold. Nothing in this PR writes or validates `arms:`.

Proposed: an **optional** top-level `arms:` list on a consolidated `study.yaml`, additive and
back-compatible (a study with no `arms:` is unchanged):

```yaml
# OPTIONAL, consolidated studies only. Proposed — not yet in study.schema.json.
arms:
  - source_study: og-35-chemical-energy-coupling   # the folded study's old slug
    concept_role: "energy-carrier-vs-gradient-only" # quoted: free text may contain ': '
    fidelity: mechanistic_prediction                # = evidence_tier (evidence indicator)
    verdict: qualified                              # the fold-in's assessment, preserved
    gate_status: passed                             # preserved; nulls/negatives keep theirs
    matched_null: matched-null-equal-feeds
    composite: proto_energetics
    run_ids: [ ... ]                                # provenance travels with the arm
    finding_ids: [ ... ]
    canonical: true                                 # at most one; bounds the headline + plan_id
```

Why a stub here and not an edit: the task is **conservative** — one new optional field touches
`study.schema.json`, the scaffold study stub, the report renderer (to draw arms), and the audit
lint (to resolve arm evidence). That is a coordinated change deserving its own reviewed PR, not a
drive-by. **Decisions needed from a human:**

- **Adopt `arms:` as proposed, or a different shape?** (e.g. a map keyed by `source_study`
  instead of a list; `evidence_tier` vs `fidelity` as the field name.)
- **Where does the audit lint resolve arm evidence** — does `run_ids`/`finding_ids` on an arm
  count toward the "every arm's evidence present" check, and does a dangling `source_study`
  become a lint error?
- **Renderer**: should the report draw folded arms as a sub-table under the consolidated study,
  and surface each arm's preserved `gate_status`?
- **`canonical` cardinality**: enforce at most one `canonical: true` per study in the lint?

Until those are decided, consolidations record arms in prose/freeform and rely on git history +
the three path-validation layers; the typed `arms:` contract is deferred to a follow-up.
