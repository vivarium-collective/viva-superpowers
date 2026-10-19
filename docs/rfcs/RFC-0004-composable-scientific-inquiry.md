# RFC-0004 · Composable Scientific Inquiry

**Unifying the investigation graph with process bigraphs and a layered contract system**

| | |
|---|---|
| **Status** | Draft |
| **Date** | October 2026 |
| **Relates to** | RFC-0001 (Agentic platform) · RFC-0002 (Typed investigation substrate) |
| **Supersedes** | RFC-0003 (Investigation Graphs Breathe) — the *destructive, Study-only* consolidation model |
| **Source notes** | "Investigation Graphs as Composable Scientific Inquiry" (formalization) · "Mapping Investigation Graphs to Process Bigraphs" |
| **Worked example** | origins-of-life-vent (~49 → ~13 studies, 6-gate spine A1/A2/B/C/D/E) |

---

## Summary

An investigation is a **compositional object in one language with three distinct semantic layers**. A **Study** is a process-bigraph Composite reference plus a scientific contract. A **Concept** is a typed, versioned *knowledge Store* — a persistent authored record with a dynamically derived evidence projection — not another executable Composite and not a passive label. An **Investigation** is a declarative orchestration over Study Composites and Concept Stores, whose inquiry operations run at transaction boundaries, not at biological simulated time.

The thesis in one line: **a Study composes experiments into evidence; an Investigation composes Studies into understanding; and both compose the same way — Composites, Stores, and typed contracts — while keeping mechanism-composition and argument-composition semantically separate.**

This RFC supersedes RFC-0003's claim that consolidation is destructive and non-reversible. Consolidation here is **non-destructive**: it groups Study references and authors a Concept synthesis; member Studies, runs, findings, and negative controls survive. It adds a Concept layer, four typed edge families, seven transaction-boundary operations, and — the new contribution of this RFC — a **layered contract system** that grounds a study's acceptance tests in the process contracts of the composite it runs.

## 1. The unified ontology

| Object | Process-bigraph realization | Not |
|---|---|---|
| **Study** | a reference to a baseline/variant **Composite** (`composite` id + `config`) + a **scientific contract** (question, predictions, acceptance tests) | not itself an inline composite |
| **Concept** | a typed, versioned **knowledge Store**: authored record + derived evidence projection | not an executable Composite; not an unversioned label |
| **Investigation** | a declarative orchestration over Study Composites + Concept Stores (with a *compiled* composite representation available) | not necessarily an always-executing meta-Composite |
| **Arm** | a variant configuration or sub-composition within a Study | not necessarily a separate full Composite |
| **Run / Finding** | an immutable execution record / a measured or inferred result | — |
| **Assessment** | a versioned judgment on a proposition, from cited Findings | not an operation side effect |

Studies and Investigations are *already* process-bigraph composites in the codebase (see §6). This RFC adds the missing third primitive — the Concept Store — and the contract layer that ties the scientific argument to the executable mechanism.

## 2. Three graphs, two timescales (the semantic separation)

The single most important discipline: **one compositional language, three graph semantics, two scheduling regimes.** These must never be silently interchanged.

- **Execution graph** — processes, stores, ports, temporal/state dynamics. Scheduled on *biological simulated time*.
- **Scientific graph** — Study↔Study edges (`builds_on`, `tests`, `motivates`, `alternative_to`) + evidence→claim relations. An inference, not a time step.
- **Organizational graph** — Concept membership, expand/collapse projections, historical revisions. A grouping, not a dynamical coupling.

A wire between two model processes is **not** a scientific `tests` relationship; Concept membership is **not** a dynamical coupling; a knowledge Store is **not** subject to the simulator's time-step schedule or concentration/flux mutability. Inquiry operations run at **event/transaction boundaries** (an assessor reads evidence and writes a versioned assessment; a consolidator revises membership and publishes a synthesis). The four typed edge families of RFC-0002 (`E_sci / E_evid / E_org / E_prov`) are exactly these graph layers plus provenance.

## 3. Concept = typed knowledge Store (hybrid)

A Concept is **a persistent authored record + a derived evidence projection** — the hybrid the mapping note recommends and the shape already prototyped on the draft branches.

- **Authored half (persisted, versioned):** `concept_id`, unifying `question`, `member_studies[]` (references, many-to-many), `principal_propositions`, authored `synthesis`, `assessment {verdict, basis}`, `open_questions`, `org_state ∈ {exploring, consolidated, reopened}`, revision history.
- **Derived half (ephemeral, recomputed):** member counts, each member's canonical verdict, divergence flags, evidence links — **computed from the Study and evidence records, never copied.**

On disk this is the additive `concepts[]` block (investigation.yaml v3). At the execution layer it is a typed knowledge Store the Investigation composite can read alongside the per-study result stores — the type system already permits stores that hold typed record trees, not just numeric state (§6). Derived concepts carry `derived: true`; authoring synthesis promotes a concept to a durable record whose interpretation history must never be clobbered by re-derivation.

**Verdict is computed into a parallel slot and reconciled, never overwritten.** `canonical_verdict` projects the several study/card vocabularies onto one canonical set (`unassessed | supported | qualified | inconclusive | refuted`) and **surfaces divergence** between the coded and authored verdicts rather than silently reconciling them.

## 4. The contract spine (the new contribution)

A study's acceptance tests and a process's interface contract are the **same kind of promise at different altitudes**. Today they meet at exactly one thin seam — the never-fabricate observable gate (`validate_readouts → ok | unresolved | not_in_structure | aspirational`), which checks only *does this emitted path exist in the built structure*. This RFC generalizes that seam from an **existence check** into a **typed contract check**, giving one layered contract system:

```
Interface contract   (process describe)       ports · types · UNITS/dims · shapes
        ↓ grounds
Behavioral contract  (process/composite)       invariants: conservation, bounds, steady-state, monotonicity
        ↓ grounds
Acceptance contract  (study behavior_tests)    measure + pass_if + band, CITED to literature
        ↓ rolls up
Investigation criteria (acceptance_criteria)   {study, behavior} → verdict
```

One typed contract language, one validator, one provenance trail across all four levels. What this changes:

1. **Bands become type- and unit-checked, not bare numbers.** A behavior test's measured observable is *typed by the process `describe()` contract*; a band whose dimensions disagree with the port it reads (a `[fg]` band on a `[mol]` observable), or a measure that mis-aggregates a vector observable, is a **contract error caught at author time** — not a silent runtime fabrication.
2. **The never-fabricate guarantee upgrades from string-match to type-check.** `not_in_structure` (phantom path) remains; it is joined by *wrong-type / wrong-unit / wrong-shape* against the port's declared contract.
3. **Process invariants become reusable contract clauses** a Study composes into its acceptance set, instead of re-authoring conservation/bounds as prose `pass_if`.
4. **Audit collapses to contract-checking at every altitude.** The fail-loud lint guards, report-card grading (`card_criteria`), and readout validation unify into one contract-validation pass with one vocabulary and one report. "Is this study real?" becomes "do its contracts hold at every level, grounded in the process contracts beneath them?"

**The discipline that keeps it honest:** the altitudes share a language but never collapse. An interface contract passing ≠ a behavioral invariant holding ≠ a scientific acceptance being met. A model can be dimensionally perfect and conservation-clean and still be *refuted* on the science. Critically — **graph and contract operations may propose but must never mechanically upgrade a scientific verdict.** A test is *typed by* the process contract (structural + dimensional correctness) but *judged by* its cited band (scientific acceptance): two checks, one language, two verdicts, never merged.

### 4.1 Grounding: one seam, four wires

This is a **connection task, not a new mechanism** — the typed vocabulary already exists on both sides and simply isn't joined. Verified against the code:

- **The seam exists and is existence-only.** `readout_validation.validate_readouts` checks each study readout against the built composite's emittable leaves → `ok | unresolved | not_in_structure | aspirational`; `available_observables` returns **leaf names only** — no type, units, or shape.
- **The typed contract is real.** `bigraph_schema.contract.ProcessContract`: a `face` mapping port → bigraph type (machine-checked), with **units/bounds carried inside the port type** (`_units`, `_min`, `_max`), validated against a pint registry (`bigraph_schema/units.py`); plus `math`, `symbols`, and monotone `conditions` (`invariant/pre/post/validity`). It ships a CI audit gate (`process_bigraph/audit_contracts.py`) and an audit (`contract_audit.py`: `bad_units`, `bad_range`, `unknown_port`). **Caveat:** this lives on bigraph-schema's **1.8.x release branches**, not the pinned venv (1.4.5, face-only) — so unit-grounded bands depend on landing that release.
- **A working type + unit checker already exists** — `composite_audit.py` resolves port schemas (`core.resolve_schemas` → type agreement) and dimensional units (`core._compute_unit_scale` → units agreement) for ports wired to the same store. It just checks process-port ↔ process-port, never study-test ↔ port.
- **A study can already carry a `contract:` block** in the *same* `face`/`_units`/`conditions` shape, authored and rendered in the Design phase (`notebook_export._contract_md`, `static/study-detail.js`) — but nothing cross-checks it against the composite's `contract_of(...)`.

So the contract spine is **four small wires onto existing primitives**:
1. `available_observables` also returns each leaf's resolved **type + `_units` + bounds** (reachable via `core.access`, exactly as `composite_audit` does);
2. `validate_readouts` compares a readout's declared units/shape against that leaf type, reusing `core._compute_unit_scale`;
3. `test_contract` bands carry a unit and reconcile it dimensionally before computing a margin (today `units=` is a display-only label);
4. a cross-check diffs a study's authored `contract.face` against the composite's `contract_of(...)` face — a structural diff in a shared schema.

None of this is new vocabulary; it is connecting the study acceptance path to the type/unit primitives the ecosystem already ships.

This is how the mapping note's "Study = Composite + scientific contract" gets teeth — the scientific contract is not a parallel prose document, it is a typed layer that grounds out in the composite's process `describe()` contracts.

## 5. Operations: declarative, transaction-boundary, invariant-bound

The seven inquiry operations run as declarative transactions over the registries (preview → invariant-check → atomic commit; a failed operation leaves the prior graph usable). They are *not* required to be live meta-Processes (see §6, §7-Q).

| Operation | Behavior | Scientific invariant |
|---|---|---|
| **branch** | instantiate a Study (composite ref + question + rationale) | does not rewrite existing evidence |
| **execute** | run a Study, append immutable artifacts | runs are reproducible and immutable |
| **assess** | derive a versioned judgment from cited Findings | no silent overwrite of a prior verdict |
| **consolidate** | group Study references, author a Concept synthesis | **no loss of source Studies, nulls, or contradictions** (non-destructive — supersedes RFC-0003) |
| **split / reopen** | revise groupings / resume inquiry | historical organizational state survives |
| **narrate** | project Concept syntheses into a report | narrative claims stay evidence-linked |

Every write obeys the three rules: **never clobber the human** (parallel computed slots), **never guess** (bucket as derived/needs-author, never fabricate), **never destroy provenance** (comment-preserving round-trip; every write is a git commit). The RFC-0002 **hard invariants** (stable identity, non-destructive evolution, epistemic integrity, typed relations, recoverable history, projection correctness, atomicity) gate every operation.

## 6. What is real vs to-build (grounded in the current runtime)

Validated against `origin/main` of `process-bigraph` and `vivarium-workbench`:

| Capability | Status | Evidence |
|---|---|---|
| Investigation → a runnable pbg Composite (study → `StudyStep`, prereq → store wiring) | **REAL, merged** | PR #715; `lib/investigation_execution.py` (`build_investigation_composite`, `run_investigation_composite`), `lib/investigation_steps.py` (`StudyStep`, `InvestigationAnalysisStep`) |
| …is that composite the production run path? | **NO** | `run_jobs`/viva-api is canonical; the composite path "refuses since #957"; `StudyStep` raises on deployment targets ("do not dispatch yet") |
| Two distinct "investigation composite" artifacts | **beware** | runnable `investigation_execution.py` vs the *trigger document* `investigation_composite.py` (never run; powers cache/pull-or-compute badges). Do not conflate. |
| Study references a composite (not itself one) | **REAL** | `study_spec.study_interface` → `{composite, config, inputs, outputs, emitter}` |
| Composite carries non-executable typed metadata | **REAL mechanism** | `process_bigraph.composite_spec.CompositeSpec` (`tags`, `parameters`, `requires`, `visualizations`, `analyses`, …); a specific `scientific_contract_ref` is **not yet present** |
| Stores hold typed references / knowledge records | **REAL** | `study_<slug>_result` stores typed `node` hold full run-reply/verdict/ref dicts; emitters are side-channel stores distinct from sim state |
| Graph-creating / mutating processes | **primitive REAL, unused at investigation layer** | `_add`/`_remove`/`_divide` sentinels + structural rebuild (cell division); nothing spawns StudySteps at investigation runtime |
| Execution vs definition vs concept persistence | **REAL, distinct lifecycles** | run data (db/parquet/artifacts, regenerable) · git-YAML definitions · derived-ephemeral concepts |
| `concepts[]` field / Concept overlay | **DRAFT only** | viva-template `feat/concept-verdict-schema`; viva-superpowers `feat/rfc-0003-concept-layer`; workbench `feat/concept-overlay` |
| Typed `ProcessContract` (face + units + conditions + CI audit) | **REAL, but on bigraph-schema 1.8.x release branches — NOT the pinned venv (1.4.5, face-only)** | `bigraph_schema/contract.py`, `contract_audit.py`, `units.py`; `process_bigraph/audit_contracts.py` |
| Study acceptance test ↔ process contract check | **existence-only** (no type/units/shape) | `lib/readout_validation.py::validate_readouts`, `available_observables` |
| Dimensional type+unit checker | **REAL, but process-port ↔ port only** (not test ↔ port) | `lib/composite_audit.py` (`core.resolve_schemas`, `core._compute_unit_scale`) |
| Study can author a `contract:` block (same `face` shape) | **REAL, authored + rendered, never cross-checked** | `lib/notebook_export.py::_contract_md`, `static/study-detail.js` |
| Acceptance bands carry/reconcile units | **NO** — `units=` is a display label only | `viva_superpowers/test_contract.py` (`Expected.band`, `check`) |

**Reading:** the primitives for this RFC already exist — a real investigation composite representation, typed stores that hold records, a structural-mutation primitive, distinct persistence lifecycles. What is missing is *wiring*, not *mechanism*. Because the investigation composite is **not** the production runner, "Investigation = always-executing meta-Composite" is premature; a **declarative orchestration** over Study Composites + a typed Concept knowledge Store is the right altitude now, with the composite form kept as a compatible execution substrate.

## 7. Open questions / decisions

- **Q1 — declarative vs executable Investigation.** The code points to declarative-first (the composite isn't the production runner). Decision: **declarative orchestration now; keep the compiled composite as an available substrate; revisit when pbg is the execution path.**
- **Q2 — `scientific_contract_ref` on the composite.** Add as an additive `CompositeSpec` field pointing a composite at its study's scientific contract? (Enables the §4 grounding.) Proposed: yes, additive.
- **Q3 — contract language.** Reuse `bigraph_schema.ProcessContract` (`face` + port-type `_units`/bounds + `conditions`) for the interface/behavioral layers; the study already authors the same shape. The dimensional-check primitives exist (`composite_audit`, `units.py`, `core._compute_unit_scale`). The real dependency is **landing bigraph-schema 1.8.x off the release branches onto the pinned version** (today's venv is 1.4.5, face-only) before unit-grounded bands can be enforced.
- **Q4 — where the Concept Store lives at runtime.** Authored half in git YAML (`concepts[]`); derived half ephemeral; optional typed knowledge Store in the `investigation_execution` composite. Start with YAML + derived; lift into the composite store when needed.
- **Q5 — verdict composition.** How arm/member verdicts at different fidelities compose into a Concept headline (current rule: the most-caveated honest member bounds it; fidelity ≠ support).

## 8. Backward compatibility & migration

Entirely additive, on a stable render contract — no breaking renames, no release gated on an investigation upgrade (the genesis `plan_acts` lesson). `studies[]`, `plan_gates`, existing study fields, and `investigation_execution` stay canonical. The Concept layer and typed edges are **derived-first** (projected from existing content) and authored only where derivation can't reach. Schema bumps are additive (investigation v2→v3). Genesis migration un-consolidates the destructive folds back into Concept + member-Study form, **selectively by verdict-independence**, via the non-destructive `split` operation — preserving every run, finding, and matched-null. All work proceeds on draft branches until proven end-to-end.

## Relation to prior RFCs

- **RFC-0001 (Agentic platform)** — agents branch, assess, and consolidate; this RFC gives them typed operations + a contract to execute against under human review.
- **RFC-0002 (Typed investigation substrate)** — the four edge families, the Concept record, and the contract layers are typed extensions of that substrate.
- **RFC-0003 (Investigation Graphs Breathe)** — **superseded.** Its breathing rhythm (branch ↔ consolidate) is retained; its *destructive, non-reversible, Study-only* consolidation is replaced by the non-destructive Concept layer. Its `arms` field remains the content-lossless refactor unit within a single-question Study.

## See also

- `docs/concepts/investigation-graph-ontology.md` — the arm/Study boundary and the two-axis status model.
- `docs/superpowers/plans/2026-10-19-investigation-graph-formalization.md` — the staged implementation plan (Stage 0 schema+derivation done; Stage 1 endpoint+render in progress).
