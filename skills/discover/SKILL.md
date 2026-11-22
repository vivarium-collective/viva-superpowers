---
name: discover
description: Use when you want to drive the discovery engine on one investigation with a free-text steering goal — e.g. "develop this toward <X>", "make this a visual exposition of <Y>", "push <inv> further". Runs the engine's bounded loop (discover investigate --goal) with the goal threaded into every generative act, so what it proposes and fills is shaped toward the goal while the frontier, gates, budget, and honesty rules stay the engine's.
user-invocable: true
allowed-tools: Bash(*) Read Write Edit
argument-hint: "<investigation-slug> <steering prompt...>  — e.g. ecoli-baseline make this a visual exposition of the baseline biology"
---

# /discover — steer the discovery cycle with a free-text goal

> **Stage:** all six — Question → Synthesize (drives the whole loop) · **Service:** Orchestrator · **Lifecycle:** Design → Decide. Cross-walk: [`docs/concepts/skills-and-the-discovery-cycle.md`](../../docs/concepts/skills-and-the-discovery-cycle.md).

Drives the **discovery engine** on one investigation and lets a free-text
*steering goal* influence what the engine develops. It is the autonomous
counterpart to `/reason`: `/reason` fills **one** request you hand it;
`/discover` runs the engine's bounded **loop** (`discover investigate`) —
project the cycle → emit the frontier's typed `GenerationRequest`s → fill the
auto-gated ones through `/reason` → apply → repeat, under a budget — with your
goal threaded through every step.

**What the engine keeps (it is not a free-text generator):** the frontier,
opportunities, gates, budget, and honesty rules stay the engine's. The goal does
**not** invent work. It does two honest things (both in
`discovery_engine/discover/investigate.py`):

1. **Shapes how each act is filled** — every request carries the goal in
   `context["goal"]`, so `/reason` pitches the generated study / interpretation
   / decision / **visualization** toward it (richer, more explanatory, on-theme),
   within the no-fabricated-numbers / provided-mechanisms-only rules.
2. **Shapes which acts run first** — the auto-gated requests are stably ordered by
   relevance to the goal, so the most on-goal work fills first under the budget.
   This only reorders what the cycle already emitted; nothing is added or dropped.

So the goal biases *emphasis and order*, never *truth*. A run on a demonstration
investigation stays a demonstration; scaffolds stay simulation-deferred unless you
actually run them.

## Preconditions

1. **A workspace** — a dir with `workspace.yaml` (resolve with
   `python -m viva_superpowers.paths --env --workspace <ws>`). The engine reads the
   investigation straight from `investigations/<slug>/` — **no workbench server is
   required** for a drive.
2. **`discovery-engine` installed** with `--goal` support (the console script
   `discover`; `discover investigate --help` must list `--goal`). If it is missing,
   the installed engine predates the steering hook — tell the user to update
   `viva-discovery-engine`, and do not silently run without the goal.
3. **A model behind the filler** — the generative half runs an LLM via
   `$VIVA_FILLER_CMD`. This skill sets it to `/reason` (below). With no filler,
   the drive is a safe projection — it emits and logs but applies nothing.

## Steps

1. **Parse the argument.** The first whitespace token is the `<investigation-slug>`
   (validate `^[a-z0-9][a-z0-9_-]*$`); the remainder is the free-text steering goal.
   If the goal is empty, ask the user what to steer toward rather than running an
   unsteered drive.

2. **Resolve the workspace + confirm the investigation exists.**
   ```bash
   eval "$(python -m viva_superpowers.paths --env --workspace "$WS")"
   test -f "$INVESTIGATIONS_DIR/<slug>/investigation.yaml" \
     || { echo "No investigation <slug> under $INVESTIGATIONS_DIR"; exit 1; }
   ```

3. **Project first (read-only), so you and the user see what the goal will bias**
   before anything is written:
   ```bash
   discover --workspace "$WS" status <slug>
   discover --workspace "$WS" requests <slug> --json   # the typed frontier, by kind
   ```
   Summarize the request mix (e.g. "29 visualize, 9 interpret_finding, 6
   propose_study…") and say which the goal will float to the top.

4. **(Optional) persist the goal on the investigation.** If the user wants this
   steering to stick for later runs, record it durably — the engine reads
   `discovery.goal` when no explicit `--goal` is passed:
   ```yaml
   # investigations/<slug>/investigation.yaml
   discovery:
     goal: "<the steering goal>"
   ```
   Write it with the atomic tmp-file + rename pattern (see `/investigate`),
   not an in-place edit. Skip this for a one-off drive.

5. **Wire the filler and run the bounded drive**, with a budget so it halts cleanly:
   ```bash
   export VIVA_FILLER_CMD='claude -p "/viva:reason"'   # namespaced plugin skill; bare /reason does not resolve
   discover --workspace "$WS" investigate <slug> \
     --goal "<the steering goal>" \
     --generation-calls 8        # cap LLM fills; tune to the budget the user wants
   # add --simulation-runs 0 to keep scaffolds simulation-deferred (no runs triggered)
   # add --free-run to auto-gate every kind; omit to respect the investigation's gates
   ```
   `investigate` fills implicitly through `$VIVA_FILLER_CMD` — there is no `--fill`
   flag on it. It prints a JSON summary:
   `{iterations, stop_reason, applied, decisions, inv_path, goal}`. A `stop_reason`
   of `closed` / `budget_exhausted` / `no_informative_experiment` /
   `insufficient_evidence` is a **legitimate halt, not a failure**.

   **End-to-end apply of visualize / propose_study (opt-in).** Two generation
   kinds — `visualize` and `propose_study` — are *CLI-verb kinds*: the pure engine
   deliberately does not auto-apply them, because applying one must RENDER a figure
   or SEED a study. By default the drive **queues** them for a human to apply with
   `/viva:viz` / `/viva:study`. To let the drive land them itself, also export the
   applier — [`/viva:reason --apply`](../reason/SKILL.md), the apply-side
   counterpart to `/reason`:
   ```bash
   export VIVA_CLI_APPLIER_CMD='claude -p "/viva:reason --apply"'
   ```
   `discover investigate` passes it to the loop (via `subprocess_cli_applier()`),
   so each `visualize` / `propose_study` request is dispatched to the applier, which
   renders the figure / seeds the study through the same canonical skill and reports
   what landed. This is **heavier** (one LLM apply per CLI-verb request, charged
   against `--generation-calls`), so enable it only when you want rendered viz +
   seeded studies to land in the drive, not just the cheap derivations. Unset, the
   behaviour above is unchanged.

6. **Report honestly.** State the goal, the budget, the stop reason, how many acts
   applied, and *what the goal actually biased* (which requests filled, which were
   deferred). Point at the decision log (`decision_log[]` in the investigation) and
   any new/updated studies, findings, or viz specs. If the engine abstained, say so
   plainly — do not manufacture activity to look productive.

## Human-in-the-loop vs autonomous

- Default (no `--autonomous`, no `--free-run`): the investigation's own gates
  decide what auto-fills vs. queues for review — branch-points (new studies, model
  choices) queue; cheap derivations fill. Safest for a first drive.
- `--autonomous` / `--free-run`: fill more aggressively. Use only when the user asks
  to let it run, and keep a budget on it.

## Red flags — STOP

- **The goal cannot rescue a thin result.** If the engine abstains or applies
  little, report that — never widen the goal into an instruction to fabricate.
- **No `--goal` in `discover investigate --help`** → the installed engine is too
  old; update it, don't run unsteered and pretend it was steered.
- **"I'll just edit the studies directly to match the goal"** → no. Drive through
  the engine so every change is gated, budgeted, and logged. Hand-authoring the
  outcome defeats the point.
- **A demonstration investigation is not a hypothesis test.** Steering it toward
  "exposition / showcase" shapes exposition; it does not license invented findings.
