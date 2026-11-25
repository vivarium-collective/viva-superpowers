# RFC-0008 · Decoupling the Investigation and Simulation Frameworks

**A study pins its own simulator; study/investigation repos reference shared simulator registries instead of vendoring them**

| | |
|---|---|
| **Status** | Draft |
| **Date** | November 2026 |
| **Relates to** | RFC-0001 (Agentic platform) · RFC-0002 (Typed investigation substrate) · RFC-0003 (Investigation graphs breathe) |
| **Builds on** | Per-run environment capture (`discovery_engine.study.run_registry.capture_environment` / `env_id`, PRs #196/#198) · the run-discoverable audit (#197) · compose-api registry + `vivarium-workbench compose-entry` |
| **Spans** | discovery-engine (study schema + audit) · vivarium-workbench (registry resolution, `build_core`, run path) · viva-superpowers (workspace scaffolding) · repo structure |

---

## Summary

Today a **workspace repo** (viva-genesis, sms-ecoli, viva-multicell-blueprint, …) locks three
things into one repository with one `uv.lock` and one `build_core` registry: its
**studies/investigations**, its **own simulators** (the `viva_<pkg>/` composites), and **one
pinned version** of every framework and simulator — shared by every study in the repo. So every
study resolves the *same* registry at the *same* commit. You cannot have study A on
`process-bigraph 1.11.0 + viva-smoldyn` and study B on `1.11.2 + viva-cpm` in the same repo.

This RFC proposes decoupling along the seam that already exists conceptually but not
structurally: the **investigation/study framework** (what a study asks, finds, and concludes)
and the **simulation framework** (the simulators/composites that produce the evidence). A study
should **pin its own simulator** — a `composite-id` at a specific package/commit, resolved
through a **shared, importable registry** — rather than inherit one workspace-wide pin.
Simulators become published, versioned, reusable packages; study/investigation repos become
light and reference them. The thesis in one line: **a study owns its question and its evidence;
it borrows its simulator, by name and version, and need not be welded to it.**

The *recorded* half of this already shipped: every run now stamps the commit + resolved package
set + `env_id` it ran under. This RFC adds the *declared* half (what a study is supposed to run
against) and the structure that lets the two be different per study.

## Motivation

Four drivers, all requested together:

1. **Reproducibility.** A study must pin and re-run against the exact simulator + commit it was
   built on, independent of what the rest of the workspace later moves to.
2. **Per-study version freedom.** Different studies in one investigation should be able to use
   different simulators, or the same simulator at different commits, without being forced onto
   one shared lockfile.
3. **Sharing / reuse.** A simulator (a process-bigraph registry) is not owned by one workspace;
   it should be published once and imported by many separate study repos.
4. **Lighter study repos.** A study/investigation repo should not have to carry and build heavy
   simulator code and dependencies just to hold its findings.

## What is already decoupled, and what is not

The **frameworks** are already independent packages:

- **Simulation**: `process-bigraph` + `bigraph-schema`, plus the ~60 `viva-<simulator>` wrapper
  packages (viva-smoldyn, viva-cpm, viva-copasi, …), each of which registers composites.
- **Investigation/study**: `discovery-engine` (the study/investigation framework) +
  `viva-superpowers` (agent skills) + `vivarium-workbench` (UI/server).

The coupling is one level down, at the **workspace repo**, which vendors studies + its own
simulators + a single pinned dependency set. The constraint to break is precisely: *every study
in a workspace resolves one registry at one commit.*

## Three models

| Model | What a study pins | Operational cost | Reproducibility |
|---|---|---|---|
| **A · Per-study simulator manifest** | `study.yaml` declares `simulator: {package, ref}`; one repo, but studies may diverge | per-study env resolution only when pins actually differ | strong (declared + recorded) |
| **B · Two repo types** (target) | study/investigation repos *import* simulator/registry repos by `@commit`; simulators are shared published packages | a resolution layer + per-study environments | strongest (clean separation) |
| **C · Provenance only** (shipped) | nothing declared; the run *records* what it ran against | none | descriptive, not prescriptive |

Model C is the substrate we already built (#196/#198). Model B is the end-state that satisfies
all four drivers. Model A is the migration stepping stone — and the 80/20.

## Proposed architecture (Model B)

**Simulator / registry repos** (simulation side)
- Each simulator is a *published, versioned* package that registers process-bigraph composites
  (most `viva-*` repos already are this) and declares the composites it provides.
- A **shared registry** maps `composite-id → package@version/commit`. The seed exists:
  compose-api's `manifest.yaml` + `vivarium-workbench compose-entry` (which pins a workspace's
  module roots to a commit). This becomes the resolution layer.

**Study / investigation repos** (investigation side)
- Hold only studies/investigations (`study.yaml`, findings, `runs.db`, viz) + framework deps
  (discovery-engine / workbench). No vendored simulator code.
- Each **study** carries its own pin: in addition to `baseline[].composite: <id>`, a
  `simulator: {package, ref, registry}` **per study**, not per workspace.
- Light and portable — a study repo is YAML + findings + a pointer, not a simulator toolbox.

**Resolution at run time**
- The engine resolves a study's declared pin → materializes that environment → builds the
  registry → runs → records `env_id`. The declared pin and the recorded `env_id` should agree,
  and a run-discoverable-style audit (#197) can enforce it. `discovery_engine` stays
  domain-free (it already resolves via the registry and never names a simulator), so this fits
  its design without coupling.

## The crux: per-study environments

This is the real cost of the freedom. If study A pins `process-bigraph 1.11.0 + viva-smoldyn`
and study B pins `1.11.2 + viva-cpm`, **they cannot share one venv** — you need an environment
*per pin-set*. The tradeoff **is** the decision; everything else is plumbing.

Mitigations that already exist:
- The workbench runs each simulation as a **detached subprocess** — a run can activate the
  study's own environment rather than the server's.
- `env_id` already identifies the exact environment, so an environment can be built on demand
  and cached by `env_id` (uv resolves from the lockfile; containers are the heavier fallback).

The tax: "run every study in this investigation in one shot" now spans several environments
instead of one. An investigation-level runner must orchestrate across per-study envs.

## How it builds on existing pieces

- **`capture_environment` / `env_id`** (#196/#198) — the per-run fingerprint becomes the thing a
  re-run resolves *to*, and the thing a declared pin is checked *against*.
- **compose-api registry + `compose-entry`** — already pins module roots to a commit cross-repo;
  the natural home for `composite-id → package@commit` resolution.
- **`study.yaml baseline[].composite`** — today resolves in the one workspace registry; the
  change is letting that reference name an *external* registry entry + version.
- **`run-discoverable` audit** (#197) — the pattern for a fail-loud "declared pin vs recorded
  env" consistency check.

## Phased rollout

- **Phase 0 — shipped.** Per-run environment provenance (commit + packages + `env_id`).
- **Phase 1 — cheap, high value (recommended first).** Add a *declared* per-study
  `simulator: {package, ref}` to `study.yaml`; add an audit that the declared pin matches the
  recorded `env_id`/packages. Studies become self-describing and reproducible **without**
  splitting repos yet (pins still share one venv while they remain compatible). De-risks the big
  question — do per-study pins actually diverge in practice? — before paying for per-study envs.
- **Phase 2.** Formalize simulators as registry-published importable packages and the
  `composite-id → package@commit` contract (most `viva-*` are already packages; this is a
  registry-contract job, not a rewrite).
- **Phase 3 — full Model B.** Study-only repos that import simulators by pin; the run path
  materializes a per-study environment from the pin (built/cached by `env_id`). Delivers all
  four drivers.

### Phase 1 concrete spec

```yaml
# study.yaml (addition; all fields optional, back-compatible)
simulator:
  package: viva-smoldyn        # the dist that registers the composite
  ref: "1.4.2"                 # a version or a git commit
  registry: compose-api        # where composite-id resolves (default: the workspace)
baseline:
  - composite: <composite-id>  # unchanged; resolved via the registry above
```

- `discovery_engine.study.audit`: a new L2 check `simulator-pin-matches-env` — when a study
  declares `simulator` and has a recorded run, the run's `env` must contain that package at that
  `ref` (reuse the `env_id`/`sim_packages` recorded by `capture_environment`). Fail loud on a
  mismatch, abstain when undeclared (back-compat).
- No run-path change in Phase 1: the declaration is captured and checked, not yet used to build
  a separate environment.

## Non-goals

- Not changing how process-bigraph composites are authored or registered in-process
  (`build_core` stays the per-env registry builder).
- Not mandating containers; per-study environments may be uv-resolved venvs keyed by `env_id`,
  with containers as an option, not a requirement.
- Not forcing existing workspaces to split immediately; Phase 1 is additive and in-place.

## Open questions

1. **Pin granularity** — per-study (this RFC) vs per-run vs per-investigation? Per-study is the
   natural unit of reproducible intent; per-run is already recorded.
2. **Registry authority** — is compose-api's `manifest.yaml` the single resolution source, or do
   studies also allow a direct `git+https://…@commit` ref when a composite isn't registered?
3. **Investigation-level runs across mixed envs** — what does `/investigate run` do when member
   studies pin incompatible simulators? (Orchestrate per-study envs; surface the env set.)
4. **Shared-registry drift** — a registry entry that moves while a study pins an older commit:
   the declared pin wins, but the audit should flag when the registry no longer offers it.
