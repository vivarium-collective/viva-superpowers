---
name: harden
description: Use when an existing viva Investigation or Study needs to be made more rigorous, trustworthy, or defensible — an overclaiming verdict, a failing/partial report-card gate, a deferred/scaffolded study, an unresolved decisions_needed, a single-seed/uncalibrated claim, or a reviewer asking "is this real?". Also triggers on "harden", "de-risk", "stress-test", or "make rigorous".
user-invocable: true
allowed-tools: Bash(*) Read Write Edit Glob
argument-hint: "[investigation-slug]"
---

# /harden

> **Stage:** Evaluate (+ Synthesize) · **Service:** — (surfaces the Strategist's frontier via the crank) · **Lifecycle:** Evaluate → Decide. Cross-walk: [`docs/concepts/skills-and-the-discovery-cycle.md`](../../docs/concepts/skills-and-the-discovery-cycle.md).

Take an investigation that *looks* done and make its conclusions survive scrutiny. Hardening is
not "sprinkle more seeds everywhere" — it is: **verify the source is canonical, find the one gap
that most weakens the headline claim, and close that gap the right way for its kind.**

**Two failures this skill exists to prevent** (both observed in baseline agents):
1. Diagnosing from a summary / memory / a tree you never confirmed is current. Investigation
   content drifts across branches and worktrees — a study called a "deferred scaffold" on one
   branch may have *run and passed* on `origin/main`. Trusting the wrong tree gives a wrong premise.
2. Producing an undifferentiated rigor checklist (n≥4 seeds, add stats, add provenance…) without
   first locating the *load-bearing* weakness or root-causing a real divergence. Generic rigor
   poured onto an un-diagnosed failing gate hides the signal instead of explaining it.

## Workflow

**0. Verify canonical source — before reading anything for content.**
`git fetch origin main` and confirm the tree you are about to diagnose IS current `origin/main`
(or the branch you intend). Re-derive each study's state from its actual canonical axes in
`study.yaml` — `simulation_status`, `gate_status`, `evaluation_status`, and the investigation's
`executive.verdict_status` / `decisions_needed` — **not** from a memory, a prior survey, or prose.
Then verify the claim is *real, not just declared*: (a) the artifacts/numbers a `ran`/`passed`
study cites must actually exist on disk and its pipeline must run in the **canonical** env — a
`ran` status with uncommitted artifacts or an un-runnable pipeline is a **reproducibility gap**,
not a result; (b) when the claim is a *passed gate*, re-run it under a **seed/parameter sweep** — a
pass that holds only at one seed or one calibration is **knife-edge**, not a certificate.

**1. Survey & triage — turn the crank to locate the load-bearing gap.**
Don't rank gaps by hand first — the **discovery crank** computes the ranked frontier for you.
It is the deterministic engine behind this skill's whole premise ("find the one gap that most
weakens the headline claim"):

```bash
python -m discovery_engine.discover --workspace <WS> crank <investigation-slug>
```

It prints `closure` (CLOSED / OPEN), the single `next` action, and the top frontier — each item
`{priority, op, kind, target}`. **The top item is the load-bearing gap; its `op` names how to
close it.** Map the `op` to its executor and work that one item:

| `op` | kind (priority) | execute it with |
|---|---|---|
| `branch` | `unaddressed_criterion` (90) / `narrative_gap` with no edge (70) | `/study propose-followup` + `seed-from-followup` (a study that addresses it) |
| `connect`/`relate` | `narrative_gap` where the edge exists but is **bare** (70) | `discover connect <inv> --relation builds-on` / `relate <downstream> <upstream>` — author the relation; **do not** seed a study. (`connect` reaches only `pipeline_gate.prerequisites` edges today; a `parent_studies`-only edge needs an explicit `relate` — see the crank doc's "known limitation".) Re-crank and read the residual |
| `synthesize` | `open_challenge` (80) | adjudicate into a finding (`/study findings`), then `discover resolve … open_challenge …` |
| `reconcile` | `divergence` (50) | [`/investigate`](../investigate/SKILL.md) reconcile + `/study set-verdicts` |
| `test` | `open_question` (40) | `/study` evaluate / run-baseline |
| `steer` | `open_decision` (60) | the expert decides — the crank's hand-back point |

The `op` label is advisory — read the `target`; when a whole frontier is one kind, suspect a
systematic cause (e.g. all prerequisite edges bare → one `connect` clears many gaps). The full
contract, verbs, convergence rule, and the stale-install precondition are in
[`docs/conventions/discovery-crank.md`](../../docs/conventions/discovery-crank.md).

If the engine isn't importable in the workspace venv (a common stale-install case), see that
doc's precondition check. If the crank can't run at all, fall back to
[`/report`](../report/SKILL.md) `--audit` (its Pass A audit surfaces verdict↔chart
drift, stale framings, follow-ups) or audit the gate axes by hand — but rank by *leverage on the
headline claim* and pick the ONE that matters most. Do not enumerate; prioritize.

**2. Classify the hardening mode — each needs different work:**

| Gap | Do this |
|-----|---------|
| Unbacked claim / deferred scaffold (`evidence_for` items are *targets*) | RUN it, measure, replace targets with real numbers |
| Passed-but-thin (single seed, one generation, uncalibrated, directional-only gate) | Re-run at scale; add seeds, statistics, tolerance bands, fitted metrics (the generic-rigor part) |
| Un-graded or un-cited **hard** gating axis (bare `passed: bool`, magic threshold, no evidence) | Grade it via [`/tests`](../tests/SKILL.md) `enrich` — a **cited** acceptance band + a signed `margin` + a `knob` — so the gate carries evidence and an agent-actionable gradient, not just pass/fail. An un-graded hard axis is itself a hardening gap. |
| Failing / partial report-card gate with a real divergence | **ROOT-CAUSE it first — REQUIRED: superpowers:systematic-debugging.** No fix, no added rigor, until you can state the cause. A verdict of *real & understood* (no bug) is a COMPLETE hardening: document the mechanism, resolve the decide, recommend an optional fix — do **not** force a code patch |
| Overclaimed verdict (`verdict: pass, confidence: high` on thin evidence) | Reconcile `verdict_status`/confidence to the evidence via `/study set-verdicts` / `set-conclusion` |
| Open `decisions_needed` / empty followups | Resolve, or fill with concrete follow-up proposals (`/study propose-followup`, `seed-from-followup`) |

> **Bounded-metric CIs.** A normal-approximation CI on a bounded metric (a
> fraction in [0,1], a count, a non-negative rate) can spill outside the
> metric's support — e.g. a lower bound below 0 on a [0,1] fraction. Use a
> Wilson score interval, or at minimum clamp the normal-approx CI to the
> metric's support; never report a CI bound outside the metric's range.

**2b. Reviewer lens — hunt the review's durable failure modes.**
After classifying the load-bearing gap, sweep the investigation once for the
failure modes external peer review keeps finding in *finished* investigations:
post-hoc gate presented as acceptance, tuned surrogate labeled substitutability,
under-powered stochastic causal claim (n<20/arm, single seed, no rank test or
drift-null), authored criterion dressed as emergence, missing conservation
ledger, unseeded stochastic / dropped config keys, decorative physical unit
labels, best-seed headline. The full criteria — each mode's signature and the
rigor-scorecard dimension or report-linter check behind it — live once in
[`docs/conventions/rigor-checklist.md`](../../docs/conventions/rigor-checklist.md);
point authors at the enforcing check rather than re-litigating the principle.

Any hit is a hardening gap in its own right — fold it into the step-2 table
(most land in "passed-but-thin" or "overclaimed verdict") and fix it per kind.
Remediation is usually a reclassification, not a rewrite: a post-hoc gate
becomes an honest `gate_class: regression_pin`; a best-seed headline becomes a
band; a tuned surrogate claim narrows to "fits condition A" until a held-out
condition exists.

**3. Look for cross-investigation leverage.** The same signature (e.g. an O₂ exchange deficit)
often weakens two investigations at once. Root-cause once; update *every* study/investigation that
cites it, including the `decisions_needed` your finding resolves.

**4. Execute in isolation, integrate carefully.** Work in a dedicated worktree off *current*
`origin/main` (REQUIRED: superpowers:using-git-worktrees); never commit in the shared checkout.
Commit deliverables early and often. Keep **run-only scaffolding out of what you land** — SUMMARY
files, env-shadow helpers, local `.gitignore`/`.deps` entries are for the run, not the canonical
branch. If the worktree needs a dependency newer than a shared venv, shadow it locally
(git-ignored) — never mutate a venv other running work depends on.

**Integrating a headless / parallel agent's branch:** its base is almost always stale (origin
moved on while it ran). A whole-branch merge — or reading `git diff origin/main..branch` — shows
**phantom reversions**: files `main` added *after* the agent branched appear deleted. Do NOT merge
wholesale. **Cherry-pick per commit** onto current `origin/main`, then verify
`git diff --stat origin/main HEAD` contains ONLY your deliverables — any unrelated deletion (CI
config, lockfile, audit allowlists) is a base-gap artifact to drop.

**5. Close the loop — record, then re-crank.** Record findings (`/study findings`,
`set-verdicts`), resolve/fill `decisions_needed`, seed follow-ups. Then **discharge the frontier
item you worked** so the crank's closure reflects it: `discover resolve <inv> <kind> <target>
--rationale "<the adjudication / bridge>" --by <study>#<finding>` (a met acceptance criterion
discharges itself from its behavior outcome; challenges, gaps, and decisions need an explicit
`resolve`). **Re-run `discover crank`** — a correct resolution drops the item and surfaces the
next; repeat from step 1. The crank advances monotonically to **CLOSED** (no unmet criterion, no
open gap, no unadjudicated challenge). What remains at CLOSED is the `steer` class
(`open_decision`) — genuine expert calls to hand back, not work to grind on. Also re-run
`/report --audit` until the drift it flagged is gone. A hardening is done when the crank
reads CLOSED (or only `steer` items remain) and the report card and the verdict tell the same
story as the data.

**Landing & publishing.** These repos use strict protection (`enforce_admins`, required review,
up-to-date-required). A PR you authored can't be self-approved, and with `enforce_admins` ON,
`gh pr merge --admin` is *refused* — don't thrash it. Landing needs a reviewer, or (only on the
owner's explicit say-so) a **minimal** `enforce_admins` toggle OFF → merge → **restore ON**,
verified, touching nothing else in the protection config. Strict mode serializes a batch: each
merge puts the siblings BEHIND, so `update-branch` + re-run CI between merges. After merge, the
read-only dashboard auto-publishes from `main` on `workspace/**` changes — confirm the Publish
workflow goes **green** (a triggered run ≠ a successful one).

### Aspect: biology-forward → moved to `/tests`

Biology-forward finding authoring — filling the quantitative finding slots
(`evidence.observed`, `expected.range`, `divergence_factor`) from
`computed_outcomes`, then authoring the mechanism prose
(`statement`/`summary`/`explanation`/`status`) over that scaffold — **now lives in
[`/tests biology-forward`](../tests/SKILL.md)**. It is finding/grading work, not
hardening. Step 5 ("Close the loop") above reaches for it when findings carry
numbers but no mechanism prose: invoke `/tests biology-forward <study-slug>` there.

---

## Red flags — STOP

- "The survey/memory says study X is a scaffold" → confirm on current `origin/main` first (step 0).
- "Let me add seeds and statistics to this failing gate" → root-cause it first (step 2).
- "Here are 11 things to improve" with no ranking → you skipped triage; turn the crank — it ranks them (step 1).
- A whole frontier of `narrative_gap`s with `op: branch` → check whether the edges merely lack a `relation` facet; `connect`/`relate` closes them, seeding 14 studies fabricates links (step 1).
- Worked a frontier item but never ran `discover resolve` / re-cranked → closure can't see your progress; the loop isn't closed (step 5).
- A gate whose threshold matches the run it grades, presented as acceptance → it's a `regression_pin` until a pre-stated prior exists (step 2b).
- A headline number from the best seed of a stochastic ensemble → lead with the band; gate on the ensemble statistic (step 2b).
- An observable computed only over the sub-population the mechanism gates/selects (e.g. measuring recruitment over just the cells the mechanism activated) → circular by construction; require the observable's domain/denominator be fixed independently of the mechanism under test.
- Hardening the investigation you were handed without checking a sibling has the same defect (step 3).
- Committing in the shared `~/code/<repo>` checkout instead of a worktree (step 4).
- Merging an agent's whole branch, or trusting `diff origin/main..branch` — cherry-pick per commit and check the landed diff is deliverables-only (step 4).
- Landing an agent's `SUMMARY.md` / env-shadow helpers into the canonical branch (step 4).
- Forcing a code patch when the root cause is real, understood biology → document + resolve the decide instead (step 2).
- Re-trying `gh pr merge --admin` against `enforce_admins` — it won't bypass; get a review or an owner-authorized minimal toggle (step 5).
- Any branch-protection change beyond a minimal, restored-immediately `enforce_admins` toggle, or without explicit owner authorization (step 5).

## Real-world impact

Across 7 v2ecoli investigations hardened this way: a stale-branch survey mislabeled *passed*
studies as "scaffolds" (Step 0 caught it); the real #143 gap was **real FBA behavior + an
averaging-window fragility, not a bug** → closed by documenting + resolving the decide, no forced
patch; a study marked `ran` proved **unreproducible** (uncommitted artifacts + an un-runnable
pipeline) and an SBC "PASS" proved **knife-edge** under a seed sweep — both caught only by
re-deriving, not trusting the status. Landing exposed the base-gap trap (a branch diff falsely
showing `ci.yml` deleted) — per-commit cherry-pick + a deliverables-only check kept main's newer
work intact.
