---
name: viva-consolidate
description: Use when an investigation's exploratory Studies have proliferated and a group of them probes one coherent concept whose verdict has stabilized — time to MERGE them into one multi-arm consolidated study, folding each into an arm and deleting the originals non-reversibly, while preserving every matched-null, verdict, and artifact. Also triggers on "consolidate", "fold these studies", "merge the probes", "re-granulate the graph", or a study list that has grown unwieldy.
user-invocable: true
allowed-tools: Bash(*) Read Write Edit Glob Grep
argument-hint: "<consolidated-slug> --studies a,b,c | <investigation-slug>"
---

# /viva-consolidate

Merge related probe-studies into **one multi-arm consolidated study** — each fold-in becomes an
**arm**, its artifacts move in, and the original `study.yaml` nodes are **deleted
non-reversibly**. This is the convergent half of the breathing rhythm in
[RFC-0003](../../docs/rfcs/RFC-0003-investigation-graphs-breathe.md): you branched many small
probe-studies while you didn't know which angle mattered; now the concept is understood, so you
state it *with its full evidence* as one node and the graph genuinely deflates.

## What this is (and is not)

**Consolidate = merge studies into one; fold-ins become arms; delete the originals.** It is
**destructive and non-reversible at the node level** — the folded `study.yaml` files are gone and
do not come back as live nodes. It is **content-lossless**: artifacts/figures are `git mv`'d into
the consolidated study, and each fold-in's verdict, matched-null, `run_ids`, and `finding_ids`
survive in its **arm** and in git history. There is **no reopen/split** — to re-explore a settled
concept you *branch new probes*, you do not resurrect folded nodes.

**An arm here IS a folded study** (not merely a condition authored inside a study from the start):

```yaml
arms:
  - source_study: og-35-chemical-energy-coupling
    concept_role: "energy-carrier-vs-gradient-only"   # quote it — see the YAML gotcha below
    fidelity: mechanistic_prediction                  # = evidence_tier
    verdict: qualified
    gate_status: passed
    matched_null: matched-null-equal-feeds
    composite: proto_energetics
    run_ids: [ ... ]
    finding_ids: [ ... ]
    canonical: true                                    # the headline-setting arm
```

**Two failures this skill exists to prevent:**
1. **Content loss masquerading as a fold.** Flattening probes into one study while dropping a
   matched-null, a refuted secondary verdict, or a run provenance. The fold deletes *nodes*, never
   *evidence* — every fold-in's result must land in its arm.
2. **Silent staleness after moving artifacts.** `git mv`'ing committed artifacts leaves stale
   hardcoded paths in **three distinct places**, and no single check catches all three (see the
   contract). A green lint with a red runtime read is worse than no check.

## Workflow

**1. Readiness — is this concept ready to consolidate?**
Consolidate only when all three hold:
- the concept's probe-studies have **stopped moving the verdict** (diminishing returns — new
  probes corroborate rather than change the assessment);
- a **sharpened arm/study exists** to bound the headline (the highest-fidelity relevant test that
  sets the honest ceiling);
- the **matched-nulls are in** (the controls that make a positive result meaningful).

Consolidating before this folds away exploration you still need; long after, it leaves the graph
needlessly inflated. If readiness is not met, STOP and say what is missing — a non-reversible fold
of a still-moving concept destroys exploration you cannot get back.

**2. Study-vs-Arm triage — the principal design boundary.**
For each candidate, decide by one test: **does it ask an independently meaningful scientific
question?**

| Candidate | Fate |
|---|---|
| Asks an independently meaningful question | **Stays its own Study** — do not fold it |
| A sweep / ablation / calibration / sharpened re-run — just another *condition* on the concept's question | **Fold into an arm** of the consolidated study |
| A **cross-cutting control** (keystone refutation, specificity control) | **Stays standalone / off-spine** — never folded into any one gate |

When in doubt, keep it its own Study — the fold is non-reversible. Record the call.

**3. Gather each fold-in as an arm — evidence travels with the claim.**
For every study being folded, build its `arms[]` entry (shape above) and pull its
behaviour-tests + run outcomes + findings, pinned to `run_ids`, into the consolidated study.
Mark the highest-fidelity arm `canonical: true`. The consolidated study **claims its canonical
arm's `plan_id`**.

**4. Move artifacts, then delete the originals — non-reversibly.**
- `git mv` each fold-in's artifacts and viz into the consolidated study, preserving provenance.
- **Delete the folded `study.yaml` files** and de-roster them from the investigation.
- This is **non-reversible**: there is no split/reopen. Be sure of step 1.

**5. Repoint every reference across three path layers — the consolidation OWNS this.**
`git mv`'ing artifacts leaves stale hardcoded paths in **three distinct places, each needing its
own check because no single one catches all three:**

| Layer | Stale path lives in | Caught by |
|---|---|---|
| 1 | **`study.yaml` references** (gate members, pipeline prerequisites, acceptance criteria, parents, handoff plan ids) | the **audit lint** (dangling-ref) |
| 2 | **test files** with hardcoded artifact paths (e.g. a phase-5 "committed artifacts carry the headline" test reading `<slug>/artifacts/*.json`) | only the **full test suite** — the lint can't see paths read at test time |
| 3 | **runtime source** — evaluator / viz modules that read a study's committed artifacts at render/eval time | **NEITHER the lint NOR CI** — it's a runtime read, not test-covered → needs a dedicated **source-path-resolves** check |

So after the fold: **grep both `tests/` AND the package source** (not just tests) for every folded
study's artifact paths and repoint them. Lint, full-suite, and source-path-resolves are **three
layers because each catches a different class of moved-artifact stale path** — run all three.

**6. Honest headline — bound by the canonical arm.**
- Preserve **every matched-null, negative, and contradictory result** as an arm with its own
  `gate_status`/verdict — never smoothed into the headline. A refuted secondary result stays
  `refuted`/`failed` inside its arm.
- The consolidated verdict is bounded by the **canonical (highest-fidelity) arm**. Lower-fidelity
  arms corroborate beneath it; they never inflate the claim. **No headline silently overwrites a
  constituent arm's verdict.**
- **Fidelity is a separate dimension from support.** A `calibrated`/mechanistic arm describes
  model character, not claim strength. Execution success (progress `completed`) is not scientific
  support (a verdict).

**7. Verify the contract — run all three layers, then review.**
Run the **audit lint** → GREEN. Run the **full test suite** (not just the lint). Run the
**source-path-resolves** grep. Then route the structural change + any new claim through review
(reviewable automation — you *propose*; evidence checks and a human *gate*).

## Consolidation contract (the invariants)

A consolidation is **valid iff** every item holds:

1. **Content-lossless.** No artifact, figure, finding, run provenance, or verdict is lost; each
   fold-in's result lands in its arm (+ git history). Node deletion is expected; evidence loss is
   a contract breach.
2. **Audit lint GREEN — and it is the contract, not a formality.** The lint *is* the
   content-preservation definition (zero dangling refs, every arm's evidence resolvable, every
   gate member resolvable). It must **hard-fail on an unparseable `investigation.yaml`** — a
   silently-skipped check is worse than none.
3. **Full test suite passes, not just the lint.** Tests read committed artifacts by path the lint
   cannot see (layer 2).
4. **Source-artifact-path-resolves.** Grep the **package source** (not only tests) for every
   folded study's artifact paths and assert each resolves post-move (layer 3 — covered by neither
   the lint nor CI otherwise).
5. **YAML is parseable — quote role/prose scalars.** An unquoted multi-line plain scalar
   containing `": "` breaks `yaml.safe_load`. Quote `concept_role`, synthesis prose, and any
   free-text scalar that can contain a colon-space. **Token-serialize** `investigation.yaml`
   edits — concurrent writers corrupt the roster; one writer at a time, and re-read before write.
6. **Honest headline.** Matched-nulls and honest-negatives preserved as arms with their own
   verdicts; the headline is bounded by the canonical arm and never overwrites a constituent
   arm's verdict; fidelity kept separate from support.
7. **Cross-cutting controls stay standalone.** The **keystone refutation stays off-spine** and the
   **specificity control stands alone** — never buried inside a consolidated gate.
8. **References repoint across all three layers** (study.yaml + tests + package source), and the
   consolidated study claims its canonical arm's `plan_id`.
9. **Reviewable automation.** Agents may propose branches, consolidations, and interpretations;
   claims and structural changes require evidence checks and review.

When landing a batch, the **merge-train rebases**: each consolidation PR puts its siblings behind,
so `update-branch` + re-run the lint/suite between merges (strict protection serializes them).

## Red flags — STOP

- "I'll fold this concept now" — but a probe still moves the verdict, or the matched-null isn't in
  → **not ready**; the fold is non-reversible, don't destroy exploration you still need (step 1).
- "The lint is green, ship it" → run the **full suite** (layer 2) and the **source-path grep**
  (layer 3) too; green lint + red runtime read is worse than no check.
- "The `investigation.yaml` didn't parse so the lint skipped it — fine" → a silently-skipped check
  is worse than none; the lint must **hard-fail** on an unparseable file.
- "I only grepped `tests/` for the moved paths" → grep the **package source** too; evaluator and
  viz modules read committed artifacts at runtime and are covered by neither lint nor CI.
- "This sweep/ablation deserves its own study node" → if it is just another *condition* on the
  concept's question, it folds into an **arm** (step 2).
- "I'll flatten the probes and drop the matched-null from the headline" → every matched-null and
  honest-negative survives as an arm with its own `gate_status`.
- "The consolidated verdict is `supported`, so I'll relabel the member arms" → no headline
  overwrites a constituent arm's verdict; the canonical arm bounds it.
- "The calibrated arm is higher fidelity, so the claim is stronger" → fidelity is a separate
  dimension from support; the sharpest *relevant* test bounds the headline.
- "I'll fold the specificity control / keystone refutation into its nearest gate" → those are
  cross-cutting; keep them standalone/off-spine.
- "I'll split this consolidated study back into its probes" → there is **no split/reopen**; to
  re-explore, **branch new probes** off the concept.
- Committing in the shared `~/code/<repo>` checkout instead of a dedicated worktree.
