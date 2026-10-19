---
name: viva-consolidate
description: Use when an investigation's exploratory Studies have proliferated and a group of them probes one coherent concept whose verdict has stabilized — time to GROUP them under a Concept (a knowledge Store) with an authored synthesis, NON-destructively (member Studies and their evidence all survive; reversible via split/reopen). Also triggers on "consolidate", "group these studies", "make a concept", or a study list that has grown unwieldy.
user-invocable: true
allowed-tools: Bash(*) Read Write Edit Glob Grep
argument-hint: "<concept-id> --studies a,b,c | <investigation-slug>"
---

# viva-consolidate — group Studies under a Concept (non-destructive)

> **Supersedes the RFC-0003 "breathe" model.** Consolidation is no longer destructive. It does **not** delete `study.yaml` nodes or fold them into arms. Per **RFC-0004 §3/§5**, a Concept is a typed *knowledge Store* (authored record + derived evidence projection); `consolidate` **groups Study references** under a Concept and authors a synthesis, while every member Study, run, finding, and matched-null stays exactly where it is. The grouping carries a revision history and is reversible with `split` / `reopen`.

## What this does

`consolidate(concept_id, study_refs)` writes/extends a Concept in `investigations/<inv>/investigation.yaml` (`concepts[]`): it sets the Concept's `member_studies` to the grouped references, marks `org_state: consolidated`, authors a `synthesis`, and appends a `revisions[]` entry. **No study file is deleted or moved.** It is backed by `viva_superpowers.inquiry_ops.consolidate` — a declarative transaction (preview → invariant-check → atomic commit); a non-destructive invariant check refuses the op if any referenced Study is missing (it would lose a source).

The sibling operations (same engine, same non-destructive contract):
- **`split(concept_id, partition)`** — partition a Concept's members into sub-Concepts; the prior grouping is recorded in the original's revision history (recoverable).
- **`reopen(concept_id, reason)`** — resume inquiry; mark `reopened`, keep the prior assessment, append an open question.
- **`assess(concept_id, verdict, basis)`** — write a versioned Concept assessment from cited findings; the prior verdict is never overwritten (it survives in `revisions[]`).

## When to consolidate (the readiness signal)

A concept is ready to be grouped when its probes have **stopped moving the verdict** (diminishing returns), a sharpest-fidelity arm/study exists to bound the honest headline, and the matched-nulls are in. Consolidating earlier folds away exploration you still need; much later leaves the graph needlessly inflated. If readiness is not met, STOP and say what is missing — but note the cost is now low: because consolidation is non-destructive and reversible, a premature grouping can be `split`/`reopen`ed without losing anything.

## The honest-headline rule

When you author the Concept synthesis/assessment, the headline verdict is **bounded by the most-caveated honest member** — a claim is only as strong as its sharpest test. Never smooth a matched-null, a refuted secondary result, or a negative control into the headline; they remain visible as member Studies with their own verdicts. Higher fidelity does **not** by itself raise the verdict (fidelity ≠ support), and **grouping must never mechanically upgrade a scientific verdict** (RFC-0004 §4).

## Procedure

1. **Identify the concept + its member Studies.** Confirm each member Study exists (the op will refuse otherwise). When in doubt whether a Study belongs, keep it separate — the grouping is cheap to revise later.
2. **Check readiness** (verdict stabilized, sharpest test present, nulls in). If not ready, stop and report the gap.
3. **Run the op** (via the `inquiry_ops` engine or the dashboard action): it writes the Concept record + a revision; member Studies are untouched.
4. **Author the synthesis + assessment** honestly (honest headline rule). Cite the member evidence in the `basis`.
5. **Verify**: member `study.yaml` files still present; the Concept's `member_studies`/`synthesis`/`revisions` are set; lint + tests green.

## Red flags — STOP

- "I'll delete the folded study files / fold them into arms" → **no.** Consolidation groups references; the Studies survive. (The `arms[]` field remains the content-lossless unit *within a single-question Study*, not a replacement for member Studies.)
- "This grouping is final / non-reversible" → **no.** Use `split`/`reopen` to revise it; the prior grouping is recoverable from the revision history.
- "The most sophisticated model sets the verdict" → no — the most-caveated honest member bounds it; grouping never upgrades a verdict.
