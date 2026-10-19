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
through the **vivarium-workbench** dashboard. The `/viva-*` skills are thin clients
over the `viva_superpowers` helpers and the workbench API. **The workbench is the
backend — most skills do nothing without it.**

## The Rule

If there is even a 1% chance a `/viva-*` skill fits what you're about to do, invoke
it BEFORE acting — before reading YAML, exploring, scripting, or curling the API.
The skills encode this workspace's conventions (canonical `study.yaml`, provenance,
pre-registered gates); hand-rolling silently drifts the workspace. Not negotiable;
if a skill turns out wrong you needn't use it, but check first and announce
**"Using /viva-X to …"**.

## Preconditions (every dashboard skill assumes both)

1. A **workspace** (`workspace.yaml` + a `viva_<pkg>/` package). None? → `/viva-workspace`.
2. The **workbench running** (`.pbg/server/`). Not up? → `/viva-workbench start`.

## The arc — a research question → generated study content

A question does **not** go straight to hand-authored YAML. It runs through the
**agentic model-building loop**, which *generates* the study's content and iterates
it to a gate:

```
question → /viva-model-build <study>          (creates the study if needed)
  AUTHOR tests    /viva-study + /viva-tests
  SELECT model    /viva-catalog + /viva-expert (wrap the REAL tool)
  BUILD→RUN→GRADE  iterate the MODEL (never the locked tests) to the severity gate
  DECIDE  pass → findings · verdicts · report GENERATED from the run
                 else → iterate, or GIVE_UP honestly
then  /viva-investigation (group studies) · /viva-harden-investigation (rigor)
      · /viva-consolidate (merge settled probes → one multi-arm study)
      · /viva-report (publish) · /viva-benchmark (score the loop)
```

**Content is generated, not hand-written:** `findings`, verdicts, `key_metrics`
and report prose are DERIVED from run outcomes + graded tests. You author the
question, the tests, and the model; the loop produces the rest.

## Route by observable state

| State | Route to |
|---|---|
| No `workspace.yaml`, want to model | `/viva-workspace` **first** |
| Workspace but no `.pbg/server/` | `/viva-workbench start` |
| "wrap X" / "use simulator X" | `/viva-expert` |
| any research question ("is X true?", "compare A/B") | `/viva-model-build` (drives the loop; creates the study) |
| run one composite / "what does it emit?" | `/viva-run` (local) · `/viva-remote-run` (viva-api) |
| lost / just arrived | `/viva-navigate status`, then `/viva-catalog` |

Full skill catalog: `docs/skills.md`. Vocabulary + on-disk shapes:
`docs/concepts/vivarium-workbench-model.md`. Rigor conventions (gate_class,
pre-registration, held-out, conservation): `docs/conventions/rigor-checklist.md`.

## Red flags — STOP

| Thought | Reality |
|---|---|
| "research question → I'll create a study and fill it in" | `/viva-model-build` — the loop authors tests, sources the model, and generates the content, gated. |
| "I'll hand-write the findings / verdict / result" | They're DERIVED from the run — generate them (`findings --auto`, `set-verdicts`), don't paraphrase. |
| "I'll read/edit the study YAML directly" / "I'll curl the API" | Use the skill — direct edits skip canonicalization, provenance, and the right endpoint. |
| "The server's probably up" | Verify `.pbg/server/` first, or `/viva-workbench start`. |
