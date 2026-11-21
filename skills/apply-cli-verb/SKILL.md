---
name: apply-cli-verb
description: Use when acting as the APPLIER for the discovery engine's CLI-verb kinds (visualize / propose_study) — the kinds the pure engine deliberately does not auto-apply because applying them RENDERS a figure or SEEDS a study. Turns one typed GenerationRequest into the applied artifact (via /viva:viz or /viva:study) and prints the outcome JSON the engine records. Wired as $VIVA_CLI_APPLIER_CMD for `discover investigate`. The end-to-end counterpart to /viva:fill.
user-invocable: true
allowed-tools: Bash(*) Read Write Edit
argument-hint: "[request.json] — reads a GenerationRequest (stdin or path), applies it, prints an outcome JSON"
---

# /apply-cli-verb — the applier for the discovery cycle's CLI-verb kinds

> **This skill runs non-interactively.** It is invoked as
> `claude -p "/viva:apply-cli-verb"` with one `GenerationRequest` on stdin, and
> the discovery engine parses your **entire stdout** with `json.loads`. Your
> final assistant message *is* that stdout.

## Output contract — read this first (absolute)

Your final assistant message must be **exactly one outcome JSON object** — raw
text starting with `{`, nothing before or after (no prose, no code fence, no log):

```json
{"status": "applied", "applied_to": ["studies/<slug>/visualizations[<name>]", "..."]}
```

- `status`: `"applied"` when you rendered/seeded and wrote it; `"queued_for_review"`
  if you deliberately decline (e.g. a branch-point that needs a human); `"error"`
  with a short `"reason"` if you could not.
- `applied_to`: the concrete field/file paths you wrote, so the drive's decision
  log is honest about what landed. Empty list for a decline.

Do everything else — read files, run the viz/study flow, render, write — with
tool calls **before** that final message; the engine never sees those. A final
message with prose around the JSON, an empty message, or a non-JSON message is a
contract violation (the drive records it as an error).

## Why this skill exists

`apply_result` in `discovery_engine.phases.generation_apply` wires a native or
registry handler for 7 of the 9 generation kinds. The two **CLI-verb kinds** —
`visualize` and `propose_study` — have **no** handler on purpose: applying a
`visualize` must RENDER a real figure, and `propose_study` must SEED a new study;
the pure, LLM-free engine does neither. So the engine queues them and names the
skill — unless a drive exports `$VIVA_CLI_APPLIER_CMD`, in which case
`discover investigate` dispatches each CLI-verb request to **you**, and you apply
it through the same canonical skill a human would use (`/viva:viz`, `/viva:study`).
You are the one place the render/seed happens; the engine stays pure.

## The contract (what you read and print)

**Input** — one `GenerationRequest` JSON, from stdin or the path in the argument:

```json
{
  "id": "...", "kind": "visualize" | "propose_study",
  "target": "<study-slug or claim:<slug> or a prose target>",
  "produces": "viz/v1" | "study/v1",
  "context": {"goal": "<the drive's free-text steering goal>", "...": "..."},
  "provenance": {"...": "..."}
}
```

Resolve the workspace the same way every skill does:
`eval "$(python -m viva_superpowers.paths --env --workspace "$WS")"` (the drive
runs in the workspace, so `WS` is the cwd / the investigation's workspace root).

**Output** — exactly one outcome JSON on stdout (see the Output contract above).

## Per-kind: what to do

### `visualize`
Author **one** real Visualization for the target study and render it, exactly as
`/viva:viz` does — then report what you wrote.

1. Resolve the target study (`target` is its slug, or `claim:<slug>`; strip the
   `claim:` prefix). Read its `study.yaml`, runs, and the `context.goal`.
2. Run the `/viva:viz <name>` flow for that study: author a **Visualization v2
   class** in the workspace package (or an `embed_visualizations` HTML for a
   committed run), register it in `study.yaml.visualizations[]` with a `rendered:`
   path or a `local:<Class>` address, and **render the figure** (commit the
   `viz/<name>.html|svg` the address points at). The goal shapes WHAT the figure
   shows, within the honesty rules below — never invent data.
3. `applied_to` = the paths you wrote, e.g.
   `["studies/<slug>/visualizations[<name>]", "studies/<slug>/viz/<name>.html"]`.
   If the study has no run data and even a PLANNED mockup is inappropriate,
   decline with `status: "queued_for_review"` and an empty `applied_to`.

**Do not write a spec pointing at a figure that does not exist** — that is the
exact half-measure this skill replaces. Either render the file the address names,
or use a `local:<Class>` address that the workbench renders on demand.

### `propose_study`
Seed **one** new child study, exactly as `/viva:study` (create + the engine's
`growth.seeding.build_seeded_study` / `growth.seed_from_followup.write_child_study`).

1. Resolve the parent (`target` / `provenance`) and the `context.goal`.
2. Author a complete, run-ready child `study.yaml` under
   `$INVESTIGATIONS_DIR/<inv>/studies/<new-slug>/` with the `investigation:`
   back-ref, inheriting the parent's baseline composite + observables +
   behaviour tests, and the proposal's `model_change` as the variation under test.
   Add it to the investigation's member list. Atomic tmp-file + rename.
3. `applied_to` = `["studies/<new-slug>/study.yaml"]` (plus the investigation
   stamp). A branch-point you are not confident is sound → decline with
   `status: "queued_for_review"`.

## Honesty rules (non-negotiable — same as /viva:fill)

- **No fabricated numbers.** A rendered figure shows data the run actually
  produced; a seeded study's bands/assumptions come only from the parent's
  tests or expert-provided sources. A figure for a study with no run is a
  clearly-labelled PLANNED mockup, never a fake result.
- **Provided mechanisms only.** Do not introduce a paper/parameter/mechanism the
  expert did not provide; if one is needed, record it under the investigation's
  `proposed_inputs:` (`status: pending`) — never fold it in as sanctioned.
- **Decline honestly.** If you cannot apply it cleanly, return
  `queued_for_review` (not a half-written artifact). The drive leaves it for a
  human; nothing is corrupted.

## Wiring it as `$VIVA_CLI_APPLIER_CMD`

`discover investigate` passes `apply_cli_verb=subprocess_cli_applier()` to the
drive loop; `subprocess_cli_applier` reads `$VIVA_CLI_APPLIER_CMD`, feeds each
CLI-verb request's JSON on stdin and reads your outcome JSON on stdout. Enable
end-to-end apply by exporting it alongside the filler:

```bash
export VIVA_FILLER_CMD='claude -p "/viva:fill"'              # generates all kinds
export VIVA_CLI_APPLIER_CMD='claude -p "/viva:apply-cli-verb"'  # ALSO applies viz / propose_study
discover --workspace "$WS" investigate <slug> --goal "<goal>" --generation-calls 8
```

With `$VIVA_CLI_APPLIER_CMD` **unset** (the default), the drive queues
`visualize` / `propose_study` for a human to apply with `/viva:viz` / `/viva:study`
— today's behaviour, unchanged. This is heavier (one LLM apply per CLI-verb
request, charged against the generation budget), so enable it when you want a
drive to land rendered viz + seeded studies itself.

## Red flags — STOP

- **Prose around the JSON / a code fence / an empty final message** → the engine's
  `json.loads` fails and the drive records an error. Print only the object.
- **A viz spec with a broken image address** → you did not render. Render the file
  or use a `local:` address.
- **Inventing a number, paper, or mechanism to make the figure/study "complete"** →
  decline instead, or record it under `proposed_inputs:`.
- **Auto-seeding a study you are not confident is sound** → it is a branch-point;
  `queued_for_review` is the honest outcome.
