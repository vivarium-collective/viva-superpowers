# RFC-0005 — The Narrative and Argument Layer

**Status:** Draft · additive · continues the composable-scientific-inquiry line
**Foundation:** the shipped knowledge-store synthesis layer
(`viva_superpowers/knowledge_store.py`, `viva_superpowers/investigation_ops.py`)
and RFC-0003's non-destructive, derive-first contract.
**Formal source:** *Scientific Inquiry Process Bigraphs* (working technical
proposal, 24 Oct 2026) — the formal companion to *From Investigation to
Composition to Scientific Narrative*. This RFC uses its definitions verbatim.

> **Scope.** We already build three of the four inquiry operations; this RFC adds
> the fourth — **Narrate** — and the first-class **argument graph** it projects
> from, as one more synchronized view over the same typed store, and closes the
> loop so a narrative gap generates a new study. The cleanup in §2 and §12 is as
> important as the new layer: it aligns our shipped vocabulary to the formal
> ontology, where it had drifted.

---

## 1. The formal object

An investigation is a **versioned knowledge state**, not a static graph:

```
I = (B, S, M, E, C, N, R, P)
```

| Symbol | Meaning | Where it lives today |
|---|---|---|
| **B** | typed process-bigraph substrate | pbg `Composite` / `CompositeSpec` |
| **S** | studies | `studies/<slug>/study.yaml` |
| **M** | executable model artifacts | composite refs + params in each study |
| **E** | evidence | runs, findings, analyses on disk |
| **C** | scientific claims | — **not yet a first-class object** (this RFC) |
| **N** | narratives | — **nothing** (this RFC) |
| **R** | typed relationships | E_sci edges, `parent_studies[].relation` |
| **P** | immutable provenance / version info | git + content-addressed store |

Knowledge advances by a transition over *scientific* state, on its own clock:

```
I[n+1] = T(a[n], I[n], delta[n])
```

where `a[n]` is a scientific **operation** (§5) and `delta[n]` is results,
observations, or **human-reviewed decisions**. This is the knowledge clock `n`,
distinct from biological simulation time `t` (§6).

## 2. Typed object ontology — and the terminology we must fix

The formal ontology (§3 of the source) defines six objects. Three map cleanly to
our code; **three expose a naming drift we have to correct.**

| Object | Minimal content | Semantics | Our status |
|---|---|---|---|
| **Study** | question, hypotheses, protocol, model refs, runs, analyses, conclusions, status | bounded scientific inquiry; can be hierarchical | ✅ canonical `study.yaml` = `S = (Q,H,M,X,D,A,F,C,V)` |
| **Model** | processes, stores, schemas, coupling maps, parameters, version | executable mechanism or composite | ✅ pbg composite, referenced by a study |
| **Evidence** | dataset/result, method, provenance, uncertainty, quality checks | observation bearing on a claim | ✅ runs + findings (not yet a typed node) |
| **Claim** | proposition, scope, qualifiers, warrants, support **and rebuttals** | **epistemic assertion, not a simulation state** | ❌ only a `study.yaml` *field* today → **this RFC** |
| **Narrative** | ordered explanatory units referencing claims, evidence, figures | communicative projection of knowledge | ❌ nothing → **this RFC** |
| **Concept** | canonical identifier, definition, ontology links | **reusable vocabulary and referent** | ⚠️ **our code misuses this name** (see below) |

**The correction.** Our shipped `knowledge_store` defines a *Concept* as "a
persistent, revisable synthesis-grouping over member Studies." The formal
ontology says that is **not** a Concept. Formally:

- a **Concept** is a *dictionary term* — a canonical identifier with a definition
  and ontology links (e.g. "bistability", "stringent response"). Reusable across
  studies and investigations. We barely have this yet, and it is low priority.
- **grouping studies under a shared question** is the **investigation composition
  operator** `⊞` (§3 below), expressed through `R` (organizational `contains`
  relations) — *not* a new object.
- the thing our "Concept grouping" was really standing in for — an assertion with
  a verdict — is a **Claim**.

So the knowledge layer's real output is **Claims + relations**, not
"concepts + verdicts". This RFC adopts the formal names; §12 gives the
back-compatible migration off the shipped `concepts{}` key.

## 3. Three compositions — how investigation, model, and evidence coexist

The user's goal ("investigations, compositions, and narrative coexist
copacetically") is, formally, that there are **three different composition
operators**, and they must never be collapsed into one (§5 of the source):

```
Model:         M₁ ⊗[Γ] M₂  →  Mc      couple executable components under an
                                       interface contract Γ (schema, units,
                                       mappings, time coordination, update
                                       rules). PARTIAL — incompatible models
                                       need an adapter or changed assumptions.

Investigation: S₁ ⊞ S₂  →  I           organize studies under a shared question,
                                       retaining branching, dependencies, and
                                       alternatives WITHOUT implying their models
                                       execute together.

Evidence:      Synthesize(C, {E₁..Eₖ}, W)  →  (C, J)
                                       justify a claim C from evidence and
                                       warrants W; may strengthen, qualify,
                                       weaken, or leave the claim unresolved.
                                       Not aggregation; not assumed Bayesian.
```

This is the precise answer to "coexist": `⊗` is executable model composition
(the composition graph), `⊞` is investigation composition (the study graph), and
`Synthesize` + `Narrate` build the argument/narrative graph. An integrated model
(`⊗`) reproducing a phenomenon is **not** evidence it is the unique cause — that
is a `Synthesize`/`Audit` judgment on a different graph.

## 4. Relation types — three classes, and the one rule that matters

Relations are typed (§6 of the source). Our edge families map onto three classes:

| Class | Examples | Our edges |
|---|---|---|
| **Computational** | reads, writes, shares-state, executes | pbg store wires (inside `M`) |
| **Epistemic** | tests, supports, challenges, motivates, alternative-to | E_sci (`tests/motivates/alternative_to`) + the **new claim→claim edges** |
| **Organizational** | contains, builds-on, version-of, derived-from | membership (`⊞`), lineage (`builds_on`), provenance (git) |

Note the reclassification: **`builds_on` is organizational (lineage), not
epistemic** — our model had it in E_sci. `supports`/`challenges` are epistemic
and are the argument-graph edges this RFC adds.

**The rule:** epistemic relations are stored as graph-valued scientific state and
read/updated by scientific operations. **They are not process-bigraph numerical
connections.** A numerical state wire and a scientific justification edge have
different meanings and must not be interchanged. This is why the argument graph
is a derived overlay, never pbg wiring.

## 5. The operational algebra

Seven operations (§7 of the source). An operation may be run by software, an AI
agent, or a human procedure, and **proposal is distinct from acceptance** —
lifecycle (execution + review) is tracked separately from the truth status of
claims. Mapping to our code:

| Op | Signature | Postcondition | Our code |
|---|---|---|---|
| **Branch** | `Branch(S, q, {h}) → {S₁..Sₖ}` | new studies retain question + hypothesis provenance | ✅ `investigation_ops.branch` |
| **Refine** | `Refine(S, δ) → S'` | prior executed versions stay immutable | 🟡 study edit + run (no explicit immutable-version op) |
| **Compose** | `Compose({M}, Γ) → Mc` | schema/interface validation recorded | ✅ `investigation_execution` + `study_contract` |
| **Test** | `Test(C, X, M, Dobs) → E` | evidence includes protocol, outcome, uncertainty | 🟡 run + evaluate (evidence not yet a typed node) |
| **Synthesize** | `Synthesize(C, E, W) → J` | explicit justification + qualifiers | 🟡 `knowledge_store.canonical_verdict` (verdict only; no warrants `W`/justification `J`) |
| **Narrate** | `Narrate(GE, Q, audience) → N` | ordered units preserve links to source evidence | ❌ **this RFC** |
| **Audit** | `Audit(N, GE) → gaps` | unsupported links + unresolved alternatives exposed | ❌ **this RFC** |

`GE` is the epistemic graph (claims + evidence + epistemic relations) — the
argument graph of §7 below.

## 6. Two clocks

```
Biological dynamics:  x(t + dt) = F[M](x(t), dt)
Knowledge dynamics:   K[n+1]   = T(K[n], a[n], r[n])
```

Simulation time `t` and investigation iteration `n` are separate. One operation
may execute thousands of biological steps and many model variants before
yielding a single evidence object:
`M[n] = SelectModel(K[n]); r[n] = Evaluate(Run(M[n])); K[n+1] = Update(K[n], r[n])`.
The knowledge layer invokes model composites but does **not** inherit their
biological update semantics — which is exactly why our knowledge overlay is
derive-first and non-destructive, never a pbg Step mutating simulation state.

## 7. The delta — the argument graph and Narrate (what this RFC builds)

### 7.1 Claim (first-class node)

```
Claim                                        (formal: proposition + scope +
  id            stable                        qualifiers + warrants + support
  proposition   precisely worded assertion;   and rebuttals)
                derived from study `claim` / question, authored override wins,
                never fabricated
  scope         where it holds ("within the tested model class" vs
                "if externally validated")
  verdict       canonical 5: supported | qualified | inconclusive |
                refuted | unassessed
  qualifiers    confidence, uncertainty (authored, optional)
  warrants (W)  why the evidence licenses the proposition
  evidence_refs study / run / finding / figure ids
  rebuttals     refs to contradicting evidence / alternative claims
  derived       true for the seed projection
```

A Claim carries the canonical Verdict that `knowledge_store` already computes —
the verdict becomes a Claim field, not a parallel `verdicts{}` map.

### 7.2 Claim→Claim edges (the epistemic/argument graph, `GE`)

`support · challenge · prerequisite · synthesis` — epistemic relations (§4),
graph-valued, never pbg wires. Derive-first seeding so `GE` is non-empty before
anything is authored:

- `alternative_to` between study claims → a **challenge** candidate (keeps both
  sides; never deletes);
- `builds_on` lineage → a **prerequisite** candidate;
- a `refuted` claim that an authored claim `support`s → surfaced by Audit, not
  dropped.

**Module:** `viva_superpowers/argument_store.py` — `derive_argument` /
`merge_argument`, same authored-wins / empty-never-clobbers rule as
`knowledge_store`. **Schema:** additive `argument` block in `investigation.schema`
(version bump, old readers ignore it).

### 7.3 Narrate + Audit

**Module:** `viva_superpowers/narrative.py`, matching the algebra signatures:

- `narrate(GE, question, audience) → N` — ordered explanatory units that
  **preserve links to source evidence**. Ordering is a deterministic topological
  pass over `prerequisite` then `support` (ties broken by id), so the same
  evidence regenerates the same reading (invariant, §8). A narrative is a
  *projection of `GE`*, never a requirement that `GE` be linear.
- `audit(N, GE) → gaps` — the loop-closer. An adjacent transition with no
  `support`/`prerequisite` path in `GE`, or a jump from weaker to stronger
  verdict with no supporting edge, is an **unsupported transition**; each gap
  names the missing evidence and is emitted as a candidate follow-up study via
  the existing `/viva-study propose-followup` → `seed-from-followup` path.

The worked example's unsupported move — *"regulatory feedback is necessary in the
composite"* → *"regulatory feedback causes the observed bimodality in living
cells"* — is exactly what `audit` flags and turns into study F (single-cell
imaging).

## 8. Required validity invariants (§9 of the source — enforced)

1. **Type preservation** — execution *and* scientific graph transformations
   preserve declared object types.
2. **Interface validity** — model coupling checks units, conservation
   assumptions, temporal consistency (the `⊗`/`Compose` gate; unchanged).
3. **Provenance** — every claim traces to evidence, analyses, model versions, runs.
4. **Epistemic separation** — simulation success is not claim acceptance;
   persuasive narrative is not proof. (Three axes: execution ⊥ review ⊥ truth.)
5. **Non-destructive revision** — completed runs and prior interpretations remain
   reconstructable.
6. **Counterevidence retention** — consolidation and narration do not silently
   remove alternatives or negative results.

## 9. Architecture — one store, three synchronized projections (§11)

One underlying typed artifact/provenance store (`I`), three views:

1. **Investigation view** — studies + branching (`⊞`, E_sci). Have it.
2. **Composition view** — pbg composites, stores, typed interfaces (`⊗`). Have it.
3. **Argument / narrative view** — claims, evidence, counterarguments, explanatory
   order (`Synthesize` + `Narrate` over `GE`). **This RFC.**

Selecting a claim reveals its supporting studies, runs, figures, model versions;
selecting a composite reveals its component validations and the claims that depend
on it; the report generator constructs narratives from evidence-backed claims and
**returns explicit audit gaps rather than silently inventing missing links.**

## 10. Consolidation: the ontology as a normal form + the N+1 derivation spec

### 10.1 The study lifecycle is preserved — the ontology is an orthogonal projection

**The current study structure does not change.** The authoring surface a user
drives — **Overview · Model · Simulation · Audit · Decide** (the
Design→Build→Simulate→Evaluate→Decide phases and the study-detail tabs) — stays
exactly as it is. The six formal objects are **not a replacement grouping**; they
are a *derived read-model* computed from those phases. The two groupings are
orthogonal: phases are the **workflow axis** (how you drive one study); the
ontology objects are the **knowledge axis** (how typed knowledge links across
studies). They align rather than compete:

| Study phase (authoring, unchanged) | Projects into (derived) |
|---|---|
| **Overview** — `name`, `title`, `question`, `hypothesis`, `key_assumptions`, `study_type` | **Study** node `Q, H` + its place in `R` |
| **Model** — `conditions`, `enforced_params`, `experiment`, composite ref | **Model** `M` |
| **Simulation** — `runs[]` (`store_path`, `outcomes`) | **Evidence** `E` |
| **Audit / Tests** — `behavior_tests[]`, `preregistered.thresholds`, `runs[].outcomes` | **Evidence** `E` + the verdict feeding **Claim** |
| **Decide** — `verdict`, `claim`, `findings[]`, `confidence`, `primary_limitation`, `proposed_controls` | **Claim** `C` (+ follow-ups via `Branch`) |

So "preserve the study structure" and "adopt the ontology" are the same move: the
study spine is the source of truth, the ontology is what we *derive from it*.

### 10.2 Normal form — the consolidation that dissolves complexity

Today's v4 `study.yaml` carries ~35 top-level keys with real redundancy: **six
parallel progress axes** (`status`, `execution_status`, `simulation_status`,
`evaluation_status`, `gate_status`, `design_status`), overlapping verdict carriers,
and **two parallel relation keys** (`parent_relations` vs `parent_studies`). The
ontology is a normal form onto which these collapse many-to-one, losslessly:

| Formal object | Existing keys it absorbs (real genesis v4) |
|---|---|
| **Study** `S=(Q,H,M,X,D,A,F,C,V)` | `question`·`hypothesis`·`key_assumptions`·`conditions`·`experiment`·`title`·`study_type`·`phase` |
| **Model** `M` | composite ref · `enforced_params` · `conditions` · (legacy `baseline`/`variants`/`interventions`/`model_change`) |
| **Evidence** `E` | `runs[]` (`outcomes`,`store_path`) · `behavior_tests[]` · `primary_output` · `visualizations[]` · report/gate cards |
| **Claim** `C` | `claim` · `verdict` · `confidence` · `evidence_tier` · `primary_limitation` · `findings[]` · `preregistered.thresholds` (+ legacy `conclusion`/`conclusion_verdicts`/`conclusion_logic`) |
| **Narrative** `N` | `title` · `biological_summary` · literature anchors · report prose |
| **Relations** `R` | `parent_relations[]` (epistemic) · `parent_studies[]` (organizational gate) · `upstream_state_consumed[]` (computational) |
| **Provenance** `P` | `created` · `runs[].timestamp` · git · content-addressed store |

**Complexity removed, concretely:** six progress axes → one Progress projection
(kept off the verdict by the epistemic-separation invariant, §8.4); the scattered
verdict carriers → one canonical verdict on the Claim; the two relation keys →
their correct relation classes (§4).

**Preservation is checkable, not hoped.** Three mechanisms: (1) **derive-first** —
objects are computed, the keys above stay the source; (2) **authored overlay**
(authored-wins / empty-never-clobbers) — author a formal object only where the
derivation is thin, never clobbering derived content; (3) **back-compat shim** —
legacy/duplicate keys keep parsing. Losslessness is **enforced** by invariants
§8.5 (non-destructive revision) and §8.6 (counterevidence retention), and verified
by the `Audit` op.

### 10.3 Slice N+1 derivation spec — the exact keys `derive_*` reads

`argument_store.derive_argument(inv_spec, studies_by_slug) → {claims{}, edges[]}`.
For each study (or each `arms[]` entry when present — see below), build one
**Claim**. Each field names its source keys in fallback order; a missing source
yields a stub, **never fabricated text** (invariant §8-derived-never-fabricate).

```
Claim.id          "claim:{slug}"  (arms: "claim:{slug}:{arm.id}")
Claim.proposition study.claim → study.title → study.question
                  → stub "⟨no claim authored for {slug}⟩"   (derived=stub)
Claim.verdict     canonical_verdict(study): authored study.verdict if ∈ the 5,
                  else roll_up(runs[].outcomes); arms use arm.verdict / arm.gate_status
Claim.scope       study.primary_limitation
Claim.qualifiers  {confidence: study.confidence, evidence_tier: study.evidence_tier}
Claim.hypothesis  study.hypothesis
Claim.warrants(W) study.preregistered.thresholds
                  + behavior_tests[classification=="primary"]{name,pass_if,band_basis,cites}
Claim.evidence_refs  findings[].id ∪ runs[].name ∪ behavior_tests[].name
                     ∪ visualizations[] ∪ study.primary_output
Claim.rebuttals   findings[status ∈ {refutes,challenges,disconfirms}].statement
                  ∪ proposed_controls ∪ (incoming parent_relations{refutes,alternative-to})
Claim.derived     true
```

**Claim→Claim edges (`GE`) read `parent_relations`, NOT `parent_studies`** — this
is the key disambiguation the two parallel keys force:

```
for each study S, for each parent_relations entry {study: P, relation: r}:
    builds-on     → edge claim:P → claim:S  type=prerequisite   (organizational lineage)
    tests         → type = support if S.verdict=="supported" else challenge
    refutes       → type = challenge
    alternative-to→ type = challenge          (both sides retained, never deleted)
    motivates     → NOT a claim edge → emit on the study graph (E_sci), skip in GE
```

`parent_studies[] {study, condition: tests-passed|ran}` is the **organizational
gate/provenance** form → goes to `R` as a `contains`/prerequisite-gate edge, not
to `GE`. `upstream_state_consumed[] {from, provides}` is **computational**
dataflow provenance → `R`, never an epistemic edge.

**Multi-arm studies (`arms[]`).** When a study carries `arms[]`
(`{id, concept_role, fidelity, verdict, gate_status, matched_null, composite}`),
derive one Claim **per arm** (verdict from `arm.verdict`/`arm.gate_status`),
grouped by `arm.concept_role` — this is the `⊞` consolidation at arm scale. The
study-level Claim becomes the **synthesis** claim over its arms (a `synthesis`
edge to each); `arm.matched_null` is a rebuttal/control ref. This is how the
genesis consolidated multi-arm studies project without un-consolidating on disk.

**Progress projection** collapses the six status axes by precedence into one
normalized marker for display, and **never feeds `Claim.verdict`** (§8.4).

`merge_argument(authored, derived)` applies the authored-wins / empty-never-clobbers
rule verbatim from `knowledge_store.merge_knowledge`. Slice N+1's read-only
genesis proof asserts: claims derive for all members, `parent_relations` edges
classify into `GE`, `parent_studies` stays in `R`, arms yield per-arm claims, and
`git status` is unchanged.

## 11. Migration — phased, mapped to the formal implementation sequence (§12)

| Formal phase | Our slice | Work |
|---|---|---|
| **P1** typed schemas (Study, Model, Run, Evidence, Claim, NarrativeUnit, Relation) with immutable IDs + provenance | **N+1 (data)** | `argument_store.py` (`derive_argument`/`merge_argument`); additive `argument` block in `investigation.schema`; promote verdict into Claim; evidence refs typed. TDD mirrors `test_knowledge_store`; read-only genesis proof. |
| **P2** Branch/Refine/Compose/Test/Synthesize as auditable transformations | mostly **have** | reconcile `investigation_ops` + `knowledge_store` to the algebra signatures (add `Refine` immutability, `Synthesize` warrants/justification `W`/`J`). |
| **P3** narrative ordering + claim-to-evidence audit | **N+2** | `narrative.py` (`narrate`, `audit`); wire gaps to `propose-followup`. Highest value — closes the investigate↔narrate loop. |
| **P4** test on a real investigation (alternatives, failed runs, versions, human review) | **N+3a** | origins-of-life-vent end-to-end: claims, refutations, `diverges`, human-reviewed verdicts. |
| **P5** specify formal properties + test that transformations preserve them | **N+3b** | invariants (§8) as op pre/postconditions; property tests. |
| render | **N+3** | add **Argument | Narrative** to the §11 workbench graph toggle (peers of Concepts|Studies); audit badges on the reading; contradictions drawn, never hidden. |

Cross-repo order unchanged: `viva-template` schema → `viva-superpowers`
derivation/ops → `vivarium-workbench` render.

## 12. Terminology reconciliation (back-compatible)

The one change that touches shipped code. Apply additively, with aliases, so no
v2/v3 reader breaks:

| Formal term | Shipped name today | Action |
|---|---|---|
| **Claim** (assertion + verdict + warrants + rebuttals) | `knowledge_store` "Concept" grouping + parallel `verdicts{}` | fold verdict into a Claim node; `claims{}` is the new output. Keep deriving `claims` where we derived `concepts`. |
| **Investigation composition `⊞`** (study grouping under a question) | also called "Concept" | express as organizational `contains` relations in `R`; it is an operation/relation, not an object. |
| **Concept** (vocabulary/referent: id, definition, ontology links) | *mostly unused* | reserve the name for this; low priority, separate slice. |
| `knowledge` block (`concepts{}` + `verdicts{}`) in `investigation.schema` | shipped | add `argument` block (`claims{}` + `edges[]`); keep `knowledge` readable; a shim projects old `concepts/verdicts` → `claims` for one version. |

**Recommendation:** do the rename inside slice N+1 behind a back-compat shim
(`concepts/verdicts` still parse and project into `claims`), rather than a
flag-day rename. This honors "reuse the existing structure" while making the
on-disk vocabulary match the formal ontology.

## 13. Grounding and limits

The source is explicit that this is **a candidate formalism, not a proved
theory** (§13): conceptual inspiration from Bechtel & Richardson (mechanistic
decomposition/recomposition), Darden (discovery strategies), Nersessian
(model-based reasoning), Toulmin & Walton (argumentation), and Morgan (narrative
ordering). Reference implementation is `vivarium-collective/process-bigraph`
(`CompositeSpec` + runtime `Composite`) — i.e. our own substrate `B`. We adopt
the ontology and algebra as our target vocabulary; we do not claim the full
algebra is established, and each op lands with its invariants as tests (P5).

**Open questions.**

- **Claim granularity.** One Claim per study assertion is the seed. A study that
  establishes two distinct propositions needs authored Claim splitting — is that
  a new op, or `Branch` at the claim level?
- **Evidence as a typed node.** P1 lists `Evidence` as first-class; today it is
  runs+findings. How much of `Test(C,X,M,Dobs)→E` do we formalize now vs. keep
  derived from run artifacts?
- **Warrants `W` and justification `J`.** `Synthesize` returns an explicit
  justification; our `canonical_verdict` has `rationale` but no structured
  warrants. Minimal schema for `W`/`J`?
- **Narrative persistence.** Determinism (§8) permits always-regenerate; authored
  ordering overrides would need a persisted, revisioned slot (like the Concepts
  revision history).
