---
name: viva-fill
description: Use when acting as the AI *filler* for the discovery engine's generation contract — turning one typed GenerationRequest (propose_study / acquire_model / author_tests / interpret_finding / resolve_decision / explain / visualize) into the GenerationResult the engine applies. The generative half of the AI-drivable cycle, wired as $VIVA_FILLER_CMD for `discover requests --fill`. Honors the honesty rules — no fabricated numbers, provided-mechanisms-only.
user-invocable: true
allowed-tools: Bash(*) Read Write Edit
argument-hint: "[request.json] — reads a GenerationRequest (stdin or path), prints a GenerationResult JSON"
---

# /viva-fill — the AI filler for the discovery cycle

The discovery engine is a pure, LLM-free projection. It **emits** typed
`GenerationRequest`s for the generative work the frontier wants
(`discovery_engine.generation` / `generation_emit`) and **applies** the
`GenerationResult`s you return (`discovery_engine.generation_apply`). It never
generates the artifact itself. **You are the filler** — the one place an LLM
runs — injected across the seam as `$VIVA_FILLER_CMD` (the generalization of the
decider seam). Read `docs/specs/2026-10-30-ai-drivable-discovery-cycle.md` in the
discovery-engine repo for the full design.

A deterministic baseline filler already exists (`viva_superpowers.filler` /
the `viva-fill` console script) for the factual core of `interpret_finding`. This
skill is the **judgment** layer: you fill the kinds that need reasoning
(propose a study, resolve a decision, write a narrative) and enrich the ones the
deterministic filler can only template.

## The contract (what you read and print)

**Input** — one `GenerationRequest` JSON, from stdin or the path in the argument:
```
{ id, kind, target, produces, rationale, context, value, provenance, gate }
```
**Output** — exactly one `GenerationResult` JSON on stdout, nothing else:
```
{ "request_id": "<the request's id>",
  "artifact": { ... },                 # content satisfying the request's `produces`
  "filler": { "kind": "ai", "id": "viva-fill", "model": "<model>" },
  "rationale": "<why this artifact>",
  "confidence": <0..1 or null> }
```
If you cannot fill the request honestly (missing context, or it would require a
number you do not have), print nothing (empty output) — the runner then leaves it
`queued_for_review`. **Never** invent a result to avoid an empty output.

Validate before printing: the shape must satisfy
`discovery_engine/schemas/generation-result.schema.json`. The engine applies the
artifact through the canonical write op for the kind, so the artifact fields must
match what that op expects (below).

## Per-kind: what `artifact` must contain

| kind | artifact | apply op (engine) | notes |
|---|---|---|---|
| `interpret_finding` | `{study, finding, statement?, explanation?, status?}` | writes the finding's prose slots | The numbers are already in `evidence.observed` (filled from the run). Write the **interpretation only** — what the measured value *means* for the claim, its evidence class, and scope. Do not restate or alter the number. Prefer to seed from the deterministic `viva_superpowers.filler.fill(request)` and enrich its `explanation`. |
| `resolve_decision` | `{rationale}` (+ optional `choice`) | `record_resolution` | Choose the option that most advances the investigation; ground the rationale in `context` + the investigation's provided inputs. |
| `explain` | `{study, finding, explanation}` (narrative for a promoted claim) | finding prose | Plain-language statement of what the promoted claim means and its caveats. |
| `propose_study` | a `study.yaml/v4` spec (purpose/question, baseline composite, behavior_tests) | `build_seeded_study` | Ground it in the frontier `context` (the unaddressed criterion / divergence). Use only REAL registered composites. |
| `author_tests` | `{study, behavior_tests: [...]}` | writes `behavior_tests[]` | Each test: `name`, `measure{kind,path}`, `pass_if` band with provenance. |
| `visualize` | a `viz_spec/v1` (a declared chart over the run's recorded observables) | viz declare/build | No fabricated data — chart only recorded observables. |
| `acquire_model` | a `model_spec/v1` (route reuse/wrap/build + composite) | model-version binder | Prefer reuse of a catalogued composite; build only when nothing provides the mechanism. |

## Honesty rules (non-negotiable — the cycle's integrity depends on them)

1. **No fabricated numbers.** Every quantitative claim must trace to a run's
   recorded/graded value. If you need a number you don't have, leave it out (or
   return empty). Prose-only assertions are not evidence.
2. **Provided-mechanisms-only.** Never introduce a mechanism, parameter, or
   literature value the expert did not provide to force a result. If one would
   help, record it as a `proposed_inputs` item on the investigation (pending), not
   as fact — see `/viva-study`’s mechanism-discipline section.
3. **Interpretation ≠ evidence.** For `interpret_finding`/`explain`, you supply
   the *meaning*; the *measurement* stays the engine's (the finding's `observed`
   and the run's `computed_outcomes`). Never overwrite the numeric evidence.
4. **Sentence case**, no ALL-CAPS emphasis, in all authored prose (per CLAUDE.md).

## Wiring it as `$VIVA_FILLER_CMD`

The engine's runner (`discovery_engine.generation_apply.run_requests` /
`discover requests <inv> --fill`) dispatches each auto-gated request to the
command in `$VIVA_FILLER_CMD`, feeding the request JSON on stdin and reading the
result JSON on stdout. Wire this skill as that command, e.g.:

```bash
export VIVA_FILLER_CMD='claude -p "/viva-fill"'
# gate the kinds you want auto-filled (panel presets or discovery.gates):
#   free_run      — fill everything
#   propose_review — fill the cheap kinds, review the branch-points
discover requests <investigation> --fill
```

Only requests whose `gate` is `auto` are dispatched to you; `review`-gated ones
queue for a human. A result you return that the engine's apply op rejects
(malformed artifact) is recorded as an error and **never applied silently**, so a
mistake is safe — it surfaces, it does not corrupt the study.

## Red flags — STOP

- About to put a number in an artifact that isn't from a run → don't; leave it out.
- About to cite a paper/mechanism the expert didn't provide → `proposed_inputs`, not the artifact.
- About to overwrite a finding's `observed` or a run's computed outcome → never; you write interpretation, not measurement.
- Unsure what the target resolves to → print empty output and let it queue, rather than guess.
