# The skills and the discovery cycle

One cross-walk that reconciles the vocabularies the `viva:` skills run on, so every
skill can tag the **stage** and **service** it serves and point here instead of
re-explaining the framing. The discovery cycle's own definitions live in the
discovery-engine glossary (`discovery-engine/docs/glossary.md`); this doc maps the
skills onto it.

## The six-stage discovery cycle (public vocabulary)

**Question → Hypothesize → Model → Experiment → Evaluate → Synthesize** — the
scientist-readable cycle (a backbone, not an enforced itinerary). Four **services**
operate *across* the stages: **Orchestrator** (coordinates the cycle, dependencies,
execution), **Reasoner** (typed AI generation + apply), **Strategist** (ranks
opportunities/experiments by value), **Knowledge Base** (preserves the persisted
graph). Scientific records progress **Observation → Finding → Discovery Candidate →
Discovery**.

## The three operational framings, cross-walked

The skills run on a **study lifecycle** (`Design → Build → Simulate → Evaluate →
Decide`), and the model-building loop runs a **state machine**. Both realize the six
cycle stages:

| Discovery stage | Study lifecycle | model-build state | Skills (primary) |
|---|---|---|---|
| **Question** | Design (the question) | — (intake) | `explore` (read the frontier), `investigate` (frame the campaign) |
| **Hypothesize** | Design (acceptance criteria) | AUTHOR · AUDIT · LOCK tests | `study`, `tests`, `reason` (propose) |
| **Model** | Build | SELECT · SPIKE · BUILD | `model`, `catalog`, `model-build` |
| **Experiment** | Simulate | RUN | `run` (local), `remote-run`, `study run-*` |
| **Evaluate** | Evaluate | EVALUATE (grade) | `tests` (grade/audit), `harden` (rigor), `viz` |
| **Synthesize** | Decide | DECIDE · NAVIGATE | `study` (findings/verdicts), `consolidate`, `investigate`, `report` |

The **Orchestrator** is `model-build` + `discover` (the whole loop) and `workbench`
(the backend); the **Reasoner** is `reason` (generate + `--apply`); the
**Strategist** surfaces through `explore` (decisions-needed ranking) and `benchmark`;
the **Knowledge Base** is `study` / `investigate` / `catalog` / `consolidate`.
Setup/utility skills (`workspace`, `orient`) sit outside the cycle.

## How to read a skill's tag

Each SKILL.md opens with a one-line tag, e.g.:

> **Stage:** Model · **Service:** — · **Lifecycle:** Build

- **Stage** — the discovery-cycle stage(s) the skill serves (or `—` for a service /
  utility skill).
- **Service** — the engine service it *is*, when it is one (`Reasoner`,
  `Orchestrator`), else `—`.
- **Lifecycle** — the study-lifecycle phase(s) it operates in, for day-to-day use.

A skill may span stages (e.g. `study` touches Hypothesize through Synthesize); the
tag names its center of gravity and the full span in the body.

## Records, not just findings

The cycle's output is an explicit progression, and the skills should preserve it:
a **run's measured outcome** is an *Observation*; an interpretation of it is a
*Finding*; a novel, evidence-backed nomination is a *Discovery Candidate*; a
reviewed promotion is a *Discovery*. Today most skills stop at `findings` + verdicts
— `consolidate` / `investigate` / `report` are where the candidate→discovery
promotion should surface.
