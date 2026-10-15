---
name: viva-orient
description: Use when starting any viva-superpowers session or workspace task — orients you to the /viva-* skills, the one automated arc from a research question to generated, gated study content, and the two preconditions every skill assumes. Auto-injected at session start; not a command to run.
---

<SUBAGENT-STOP>
If you were dispatched as a subagent to execute a specific task, ignore this skill and do that task.
</SUBAGENT-STOP>

# Orienting in a viva-superpowers workspace

viva-superpowers turns a **research question into a validated, gated simulation
study** — wrapping real simulators as typed Processes, composing them, and
iterating a model against pre-registered tests until it passes a severity gate,
all through the **vivarium-workbench** dashboard. The `/viva-*` skills are thin
clients over the `viva_superpowers` helpers and the workbench HTTP API. **The
workbench is the backend — most skills do nothing useful without it.**

## The Rule

**If there is even a 1% chance a `/viva-*` skill fits what you are about to do,
invoke it BEFORE acting** — before reading YAML, exploring the workspace, writing
a script, or calling the API by hand. The skills encode this workspace's
conventions (canonical `study.yaml`, the AI-free/dashboard split, provenance,
pre-registered gates). Hand-rolling around them silently drifts the workspace.
This is not negotiable; you cannot rationalize your way out of it. If a skill
turns out wrong for the situation you don't have to use it — but you must check
first, and announce **"Using /viva-X to …"**.

## Preconditions — every dashboard skill assumes both

1. A **workspace**: a directory with `workspace.yaml` + a `viva_<pkg>/` package.
   None in cwd/ancestors? → `/viva-workspace` **first** (never wrap tools or write
   models into a bare directory).
2. The **workbench running**: skills resolve its URL from `.pbg/server/`. Not up?
   → `/viva-workbench start`.

If either is missing, a skill should fail with a clear error naming the missing
precondition — not guess.

## The arc — a research question → generated study content

A research question does **not** go straight to hand-authored YAML. It runs
through the **agentic model-building loop**, which *generates* the study's content
and iterates it to a gate. This is the default path; know it before reaching for
anything else:

```
 research question
   │
   └─ /viva-model-build <study>          the driver (creates the study if needed)
        AUTHOR   tests          /viva-study (Design) + /viva-tests (graded report cards)
        SELECT   the model       /viva-catalog (survey) + /viva-expert (wrap/compose the REAL tool)
        BUILD→RUN→GRADE          iterate the MODEL (never the locked tests) to the severity gate
        DECIDE   pass→DONE        findings · verdicts · metrics · report GENERATED from the run
                 else→iterate, or GIVE_UP honestly
   │
   ├─ /viva-investigation       group studies into a campaign under one question
   ├─ /viva-harden-investigation make a done-looking result survive scrutiny
   ├─ /viva-report              reviewer-readiness audit → render the dashboard/report
   └─ /viva-benchmark           score the loop's generation across many questions (reliability meter)
```

**Content is generated, not hand-written.** `findings`, three-track verdicts,
`key_metrics` and report prose are **derived from run outcomes + graded tests** —
you author the *question*, the *tests*, and the *model*; the loop produces the
rest. Don't hand-write a `claim`/`result`/`findings` the run can generate.

## Where are you? Route by observable state (top to bottom)

| State you can observe | Route to |
|---|---|
| No `workspace.yaml`, and the user wants to model something | `/viva-workspace <name>` **first** |
| Workspace exists but `.pbg/server/` missing/stale | `/viva-workbench start` |
| "wrap X" / "use simulator X" / "add a solver" | `/viva-expert` (bridges the REAL tool; `--lightweight` for in-workspace) |
| "is X true?" / "compare A vs B" / any research question | **`/viva-model-build`** (drives the loop; creates + fills the study) |
| Hand-editing one study's lifecycle fields directly | `/viva-study` (Design→Build→Simulate→Evaluate→Decide) |
| "run this composite" / "what does it emit?" | `/viva-run` (local) · `/viva-remote-run` (GovCloud viva-api) |
| "what's here?" / lost / just arrived | `/viva-navigate status`, then `/viva-catalog` |

**First session, from nothing:** `/viva-workspace my-model` → `/viva-workbench
start` → wrap a tool (`/viva-expert`) → put a question through
`/viva-model-build`. "Model X" always means **workspace first**.

## Skill map

| Group | Skills |
|---|---|
| **Generate (the loop)** | `/viva-model-build` (question → validated model, the driver), `/viva-tests` (author/enrich/run graded tests → margin + diff; also `audit`, `cite-bands`), `/viva-study` (lifecycle + behavior-test grammar), `/viva-benchmark` (score generation across questions) |
| **Source the model** | `/viva-expert` (wrap the REAL simulator, or compose several), `/viva-catalog` (browse/install workspace modules) |
| **Organize & assure** | `/viva-investigation` (group studies into a campaign), `/viva-harden-investigation` (rigor; also `biology-forward`), `/viva-report` (reviewer audit → render) |
| **Run & visualize** | `/viva-run` (local smoke-test), `/viva-remote-run` (viva-api), `/viva-viz` (figures) |
| **Navigate & setup** | `/viva-navigate` (read-only graph queries + `status` + "decisions needed"), `/viva-workspace`, `/viva-workbench`, `/viva-init` (machine setup) |

Vocabulary and on-disk shapes: `docs/concepts/vivarium-workbench-model.md`. Rigor
conventions (gate_class, pre-registration, held-out grading, conservation): one
home at `docs/conventions/rigor-checklist.md`. For any skill, use the **Skill** tool.

## Red flags — STOP, you're rationalizing

| Thought | Reality |
|---|---|
| "A research question → I'll just create a study and fill it in" | `/viva-model-build` — the loop authors tests, sources the model, and generates the content, gated. |
| "I'll hand-write the findings / verdict / result" | Those are DERIVED from the run — generate them (`findings --auto`, `set-verdicts`), don't paraphrase. |
| "I'll read the study YAML and edit it directly" | `/viva-study` — direct edits skip canonicalization + provenance. |
| "I'll write a quick script to run the composite" | `/viva-run` / `/viva-study run-*` already does this correctly. |
| "The API call is simple, I'll curl it" | The skill knows the right endpoint and the AI-free/dashboard split. |
| "The server's probably up, I'll start" | Verify `.pbg/server/` first, or `/viva-workbench start`. |
