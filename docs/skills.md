# Skills catalog

19 user-facing skills (plus `/init` machine setup and one internal dashboard callback). Each entry links to the skill's `SKILL.md` for the full contract (front-matter, args, side effects).

## Wrap & compose

| Skill | What it does |
|---|---|
| [`/expert <tool>`](../skills/expert/SKILL.md) | Wrap a simulator as a Process — full sibling `viva-<tool>/` repo with Process class, tests, README, HTML report, and a local commit. **Bridges the REAL tool by default** (keeps trying even when the build is hard); never silently downgrades. The canonical wrap. |
| [`/expert <name> <tools…>`](../skills/expert/SKILL.md) | Compose two or more wrapped simulators into a sibling `viva-<name>-composite/` repo with HTML report and a local commit. |
| [`/expert --lightweight <tool>`](../skills/expert/SKILL.md#lightweight-mode) | Lightweight in-workspace wrap: writes `viva_<slug>/processes/<tool>.py` + a test. Still a **real bridge** (lazy-imports + drives the genuine tool); only the repo scaffolding is dropped. No sibling repo, no report. (Alias: `--in-workspace`. Replaces v0.8 `/pbg-wrapper`.) |
| [`/expert --lightweight <name> <tools…>`](../skills/expert/SKILL.md#lightweight-mode) | Lightweight in-workspace composite: writes `viva_<slug>/composites/<name>.py` + a test. (Replaces v0.8 `/pbg-composer`.) |
| [`/expert --reproduce <tool>`](../skills/expert/SKILL.md#reproduction-mode) | Opt-in: clean-room reimplement the tool's published algorithm as a labeled `<Tool>ReproductionProcess` (for when the real tool genuinely can't run here). Not the default. |
| [`/expert --mock <tool>`](../skills/expert/SKILL.md#mock-mode) | Opt-in: emit a non-functional `<Tool>MockProcess` placeholder (real ports, inert `update()`) for scaffolding/wiring only. Never a fallback for a hard build. Alias `--stub`. |

## Workspace lifecycle & dashboard

| Skill | What it does |
|---|---|
| [`/workspace <name>`](../skills/workspace/SKILL.md) | Scaffold a fresh workspace — three modes: upstream-branch (clone an upstream model repo and create a workspace branch), standalone (clone `viva-template`), or in-place (promote an existing checkout). |
| [`/workbench [start\|stop\|status\|open\|restart]`](../skills/workbench/SKILL.md) | Start/stop/open the interactive vivarium-workbench (the side-rail-tabbed UI) and use its **session-per-tab** model — one workspace per browser tab. The single server every Studies skill depends on; it also serves the study reports. (Renamed from the former `/pbg-dashboard`.) |

## Catalog & registry

| Skill | What it does |
|---|---|
| [`/catalog [list]`](../skills/catalog/SKILL.md) | Browse the workspace catalog — composites, studies, registry. Default subcommand when no args. (Replaces v0.8 `/pbg-list`.) |
| [`/catalog install <pkg>`](../skills/catalog/SKILL.md#install) | Add a curated `viva-*` package, install it, refresh the workspace catalog. (Replaces v0.8 `/pbg-install`.) |
| [`/catalog uninstall <pkg>`](../skills/catalog/SKILL.md#uninstall) | Remove an installed `viva-*` package. (Replaces v0.8 `/pbg-uninstall`.) |

Maintainer-only: to audit an external `viva-*` repo for discovery- and
packaging-convention compliance, run `python scripts/audit-pbg-repo.py <repo>`
from a viva-superpowers checkout. (Replaces the v0.8 `/pbg-package` skill.)

## Run, explore, study

| Skill | What it does |
|---|---|
| [`/run <composite-id> [--steps N]`](../skills/run/SKILL.md) | Run a composite directly (no Study attached). |
| [`/remote-run [connect\|submit\|status\|fetch]`](../skills/remote-run/SKILL.md) | Run a **workspace composite remotely on viva-api (GovCloud/smsvpctest)** — the remote sibling of `/run`. Connecting (SSO + SSM tunnel), the run-path choice (generic compose/`run_pbg` vs the legacy comparison view), submit params, the composite-declares-its-emitter model, how a data-prep pipeline that is itself a composite dissolves cache-provisioning, and the hard-won API gotchas. Framework-generic — domain specifics stay in the domain repo. |
| [`/study <subcmd> …`](../skills/study/SKILL.md) | Full CRUD for **Studies** — baseline composites, variants, interventions, runs, behavior tests, follow-up proposals. Organized by lifecycle phase (Design → Build → Simulate → Evaluate → Decide). |
| [`/tests <author\|enrich\|run\|audit\|cite-bands> <study> …`](../skills/tests/SKILL.md) | Author/enrich/run a study's **graded Tests** — the report cards that compile a run into a pass/fail verdict AND a signed `margin` (distance-to-pass) + a cross-iteration diff, the feedback signal for agent-driven model building. Uses `viva_superpowers.check()`/`TestBuilder`; bands over magic numbers. `audit` judges whether Tests are sufficient (discriminating, covering the question, independent, with a discriminating control) BEFORE they are pre-registered/locked — the AUDIT gate of the agentic model-building loop, using `viva_superpowers.test_audit.build_audit_report`/`audit_gate` plus AI reasoning. `cite-bands` guides sourcing acceptance-band provenance from expert PDFs and writes structured `cites`/`calibration_anchor` into `study.yaml` via a deterministic comment-preserving helper. |
| [`/model-build <study> [--autonomous]`](../skills/model-build/SKILL.md) | Drive the agentic model-building loop: an open-ended question → author Tests → AUDIT → LOCK → build/run/evaluate → iterate the MODEL (never the locked Tests) until the severity gate passes or gives up honestly. Orchestration + invariant enforcement over `loop_state` (`.pbg/loop/<study>.json`); supervised by default, `--autonomous` for hands-off. |
| [`/benchmark <suite> [--variant-label] [--score-only]`](../skills/benchmark/SKILL.md) | Measure the framework's ability to produce models: run a suite of open-ended questions through the autonomous loop, score each with the reference-free process-quality rubric (question comprehension / test sufficiency / model plausibility / loop outcome / efficiency), and write a `benchmark_report/v1` you can diff across framework variants. |
| [`/investigation <subcmd> …`](../skills/investigation/SKILL.md) | Manage **Investigations** — named collections of Studies grouped under a shared research question, with a cross-study dependency DAG. |
| [`/harden-investigation [slug\|biology-forward <study-slug>]`](../skills/harden-investigation/SKILL.md) | Make an existing **Investigation** rigorous — verify canonical source first, triage to the single load-bearing claim↔evidence gap, classify the hardening mode, root-cause failing report-card gates, and resolve open decisions. The `biology-forward` aspect fills quantitative finding slots (`evidence.observed`, `expected.range`, `divergence_factor`) from `computed_outcomes`, then guides the agent to author the mechanism prose (`statement`/`summary`/`explanation`/`status`) over that scaffold. |
| [`/consolidate <consolidated-slug> --studies a,b,c`](../skills/consolidate/SKILL.md) | **Merge** proliferated probe-studies of one settled concept into a single multi-arm study — each fold-in becomes an **arm** (preserving its verdict, matched-null, `run_ids`, findings), artifacts are `git mv`'d in, and the original `study.yaml` nodes are deleted **non-reversibly**. The convergent half of the Branch–Consolidate rhythm ([RFC-0003](../docs/rfcs/RFC-0003-investigation-graphs-breathe.md)). Enforces the content-honesty invariants (nulls survive as arms; headline bounded by the canonical arm; fidelity ≠ support) and the three path-validation layers (audit lint + full suite + source-path-resolves). |
| [`/viz <study> <viz-name> '<description>'`](../skills/viz/SKILL.md) | Generate a `Visualization` subclass from a natural-language description and attach it to a Study. |
| [`/report [model\|--all]`](../skills/report/SKILL.md) | Regenerate `reports/index.html` after manual state changes. |
| [`/navigate <status\|ac-gaps\|source\|finding-by-observable\|dag> …`](../skills/navigate/SKILL.md) | **Read-only** query of the workspace linkage index (SP4a) — the AC→study gating matrix + unlinked-AC gaps, source↔study, finding-by-observable, study-DAG. Pure deterministic derive (`linkage_index` / `/api/linkage-index`), no writes, no AI. `status` is a quick workspace/server/git status check that works even without the dashboard server. |
| [`/fill [request.json]`](../skills/fill/SKILL.md) | The **AI filler** for the discovery engine's generation contract: read one typed `GenerationRequest` (propose_study / acquire_model / author_tests / interpret_finding / resolve_decision / explain / visualize), produce the `GenerationResult` the engine applies. The generative half of the AI-drivable cycle (the engine emits + applies; this fills), wired as `$VIVA_FILLER_CMD` for `discover requests --fill`. Honors the honesty rules (no fabricated numbers, provided-mechanisms-only, interpretation ≠ evidence). |
| [`/apply-cli-verb [request.json]`](../skills/apply-cli-verb/SKILL.md) | The **applier** for the discovery engine's two CLI-verb kinds (`visualize` / `propose_study`) — the kinds the pure engine deliberately does not auto-apply because applying one must RENDER a figure or SEED a study. Reads one typed `GenerationRequest`, applies it through the canonical skill (`/viz` / `/study`), and prints the outcome JSON the drive records. The apply-side counterpart to `/fill`, wired as `$VIVA_CLI_APPLIER_CMD` for `discover investigate`. Honors the same honesty rules. |
| [`/drive-engine <investigation-slug> <steering prompt…>`](../skills/drive-engine/SKILL.md) | **Drive** the discovery engine on one investigation with a free-text *steering goal*. Runs the bounded autonomous loop (`discover investigate --goal`) with the goal threaded into every generative act — it shapes how each request is filled (via `/fill`) and which requests fill first under the budget, while the frontier, gates, budget, and honesty rules stay the engine's. The autonomous counterpart to `/fill` (which fills one request; this runs the loop). Projects the frontier first, halts cleanly on closure/budget, reports what the goal actually biased. |

For the read/write surface each skill touches (which API endpoints, which on-disk files), see the [Skill ↔ concept map](concepts/vivarium-workbench-model.md#skill--concept-map).

> Also shipped: `/init`, a one-shot machine-setup installer that symlinks the skills into `~/.claude/skills/`. Not part of the workflow surface above. And `/suggest <id>`, an internal callback the dashboard's "Suggest" button asks the user to paste — kept registered so the callback works, but not part of the user-facing catalog.
