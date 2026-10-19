# Investigation Graph Formalization (RFC-0003 → formalized) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Evolve the shipped (destructive, Study-only) RFC-0003 "breathe" model into the formalized non-destructive **Concept-layer** graph — adding a Concept grouping layer, four typed edge families, a canonical Verdict, and seven typed non-destructive operations (branch/link/execute/assess/consolidate/split/reopen) — entirely additively, on an isolated dev branch, reusing existing content.

**Architecture:** Derive-first overlay. Concepts and the typed edge/verdict projections are *computed* from existing fields (plan_gates/plan_acts, parent_studies, findings.provenance) the way `linkage_index` is — ephemeral, never written into YAML unless authored. Schema changes are additive (`additionalProperties: true`, new optional fields; investigation v2→v3, study spec additive). The destructive `consolidate` is rewritten to non-destructive (fold into a Concept, keep member Studies) and paired with `split`/`reopen`. Nothing on any repo's release line changes until the whole thing lands additively.

**Tech Stack:** JSON Schema (draft 2020-12) in `viva-template`; pure Python (`viva_superpowers/`) for derivation + ops; `vivarium-workbench` for render; `ruamel.yaml` round-trip for any authored writes; pytest.

**Spec:** `docs/rfcs/RFC-0004-composable-scientific-inquiry.md` — the unifying RFC (formalization + process-bigraph mapping + the layered contract spine). It supersedes `RFC-0003-investigation-graphs-breathe.md` (destructive consolidation). Source design notes: the two Desktop PDFs (`Vivarium_Investigation_Graph_Framework_Formalized.pdf`, `Vivarium_Process_Bigraph_Investigation_Mapping.pdf`).

## Global Constraints

- **Additive only. No breaking renames.** No workbench release is ever gated on an investigation upgrade (the genesis `plan_acts` lesson). `studies[]`, `plan_gates`, existing study fields stay canonical and unchanged.
- **Backward-compat:** every existing v1/v2 `investigation.yaml` and every existing `study.yaml` must validate unchanged after each schema change.
- **Derive-first / ephemeral:** the Concept overlay and typed edges are projected from existing content; they are only *authored* where derivation is impossible (synthesis prose, hand-corrections). Derived objects carry `derived: true`.
- **Three rules (every authored write):** never clobber the human (parallel computed slots, never overwrite authored); never guess (bucket as `derived`/`needs_author`, never fabricate a verdict); never destroy provenance (ruamel comment-preserving; every write is a git commit).
- **Non-destructive invariant (the supersession):** no operation deletes historical runs, findings, negative controls, or assessments. `consolidate` groups (keeps member Studies); it does not delete `study.yaml` nodes.
- **Isolation:** develop on `rfc-0003-investigation-graphs` (viva-superpowers) + `feat/concept-verdict-schema` (viva-template) + later workbench/genesis branches, in dedicated worktrees off current `origin/main`. PRs stack/draft against the dev branches, NOT main, until "working perfectly."
- **No AI attribution** in commits/PRs. Dashboard stays AI-free (all AI in viva-superpowers skills).

## Review Focus

- **Legacy investigation with no plan_gates/plan_acts** → `derive_concepts` must return `[]` (or a single implicit concept), never crash. (Owned by Stage 0 Task 3.)
- **Study whose verdict vocabs disagree** (authored `passed` but card `mismatch`) → `canonical_verdict` must be deterministic + surface the divergence, never silently pick one. (Stage 0 Task 4.)
- **Concept with a member study that doesn't exist / is in another concept** (many-to-many) → derivation + validation must tolerate many-to-many membership and flag dangling members, not dedupe silently. (Stage 0 Task 3 + Stage 3 invariants.)
- **An already-consolidated genesis study (arms[]) read under the new model** → must render as a Concept with member Studies without requiring the un-consolidation to have run yet (graceful dual-read during migration). (Stage 1.)
- **`split`/`reopen` on a Concept that was authored, not derived** → must preserve authored synthesis + prior assessments (supersedes_revision), never drop them. (Stage 2/3.)

---

## Stage roadmap (RFC-0004-aligned)

| Stage | Repo(s) | Deliverable | Status |
|---|---|---|---|
| **0 — Concept overlay schema + derivation** | viva-template + viva_superpowers | additive `concepts[]` + canonical `computed_verdict`; `derive_concepts()`/`canonical_verdict()`, proven on genesis | **DONE** |
| **1 — Projection + §11 render** | viva_superpowers + vivarium-workbench | `/api/concept-overlay` + `DataSource.loadConceptOverlay` + publish bake; §11 Concept view (Concepts\|Studies collapse toggle, expand-to-boundaries) | backend+data **DONE**; render WIP |
| **2 — Concept as hybrid Store** | viva-template + viva_superpowers | persist the **authored half** (synthesis/assessment/open_questions/revision history) that makes a Concept a knowledge Store; derived half stays derived; never-clobber | **NEW (next)** |
| **3 — Declarative inquiry operations** | viva_superpowers | `consolidate` (non-destructive) / `split` / `reopen` / `assess` / `narrate` as declarative transaction-boundary ops (preview → invariant-check → atomic commit); **supersede the destructive `/viva-consolidate`** | re-slotted |
| **4 — Invariants + three graphs explicit** | viva_superpowers (+ workbench render) | the 7 hard invariants as op pre/postconditions (genesis's 3 guards generalized); name `E_sci/E_evid/E_org/E_prov` as execution/scientific/organizational + provenance; retire RFC-0003 breathe semantics | re-slotted |
| **5 — Contract spine (the four wires)** | bigraph-schema → vivarium-workbench + viva_superpowers | generalize `validate_readouts` from existence-check to **type/unit/shape**; bands carry+reconcile units; study `contract.face` ↔ composite `contract_of` diff | **NEW (gated on bigraph-schema 1.8.x)** |
| **6 — Genesis migration** | viva-genesis | un-consolidate the destructive folds into Concept + member-Study form via the non-destructive `split` op, **selectively by verdict-independence** | re-slotted (was Stage 4) |

Stages 2, 3, and 5 are detailed below (the RFC-0004-specific work, all pytest-verifiable). Stages 4 and 6 are outlined; each depends on the prior stage's realized interfaces. The "declarative vs executable Investigation" choice (RFC-0004 §7-Q1) resolves to **declarative** — the compiled `investigation_execution` composite exists but is not the production runner, so ops are declarative transactions, with the composite kept as an available substrate.

---

## Stage 0 — Concept overlay schema + derivation

**File structure (Stage 0):**
- `viva-template`: `template/.pbg/schemas/investigation.schema.json` (add `concepts`), `template/.pbg/schemas/study.schema.json` (add `computed_verdict`); tests under `viva-template/tests/`.
- `viva_superpowers`: new `viva_superpowers/concept_overlay.py` (`derive_concepts`), new `viva_superpowers/verdict_vocab.py` (`canonical_verdict`); tests under `viva-superpowers/tests/`.

### Task 1: Additive `concepts` field in investigation.schema.json

**Files:**
- Modify: `template/.pbg/schemas/investigation.schema.json` (add `concepts` property; bump `schema_version` enum to accept 3)
- Test: `tests/test_investigation_schema_concepts.py`

**Interfaces:**
- Produces: the on-disk `concepts[]` shape consumed by Stage 0 Task 3 (`derive_concepts` emits it) and Stage 1 render. A concept object:
  `{id (req, slug), title?, question?, from_gate?, from_act?, member_studies[] (slugs), principal_propositions?[], synthesis?, assessment?{verdict, basis}, open_questions?[], org_state? (exploring|consolidated|reopened), derived? (bool)}`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_investigation_schema_concepts.py
def test_investigation_with_concepts_validates(load_schema, validator):
    inv = {"name": "x", "title": "X", "schema_version": 3,
           "concepts": [{"id": "energy-coupling", "from_gate": "C",
                         "member_studies": ["og-energetics", "og-carrier"],
                         "org_state": "consolidated", "derived": True}]}
    validator(load_schema("investigation")).validate(inv)  # no raise

def test_legacy_investigation_without_concepts_still_validates(load_schema, validator):
    validator(load_schema("investigation")).validate({"name": "x", "title": "X", "schema_version": 2})

def test_concept_missing_id_fails(load_schema, validator):
    import pytest, jsonschema
    with pytest.raises(jsonschema.ValidationError):
        validator(load_schema("investigation")).validate(
            {"name": "x", "title": "X", "concepts": [{"from_gate": "C", "member_studies": []}]})
```

- [ ] **Step 2: Run to verify it fails** — `pytest tests/test_investigation_schema_concepts.py -v` → FAIL (`concepts` unconstrained ⇒ `missing_id` test fails to raise). Follow the existing `tests/test_investigation_schema_s5.py` fixture/helper pattern for `load_schema`/`validator`.
- [ ] **Step 3: Add the `concepts` property** to `investigation.schema.json` (array; items `required: ["id"]`, `additionalProperties: true`, `id` pattern `^[a-z0-9][a-z0-9_-]*$`, `member_studies` items slug-patterned, `org_state` enum, `derived` boolean), and add `3` to the `schema_version` enum. Keep top-level `additionalProperties: true`. Update the title/description to `(v1/v2/v3)`.
- [ ] **Step 4: Run to verify it passes** — `pytest tests/test_investigation_schema_concepts.py -v` → PASS; also run `pytest tests/test_investigation_schema_s5.py -q` to confirm no regression.
- [ ] **Step 5: Commit** — `feat(schema): add additive concepts[] overlay to investigation.schema (v3)`

### Task 2: Canonical `computed_verdict` slot in study.schema.json

**Files:**
- Modify: `template/.pbg/schemas/study.schema.json` (add `computed_verdict` enum, parallel to authored verdict fields)
- Test: `tests/test_study_schema_computed_verdict.py`

**Interfaces:**
- Produces: `computed_verdict` ∈ `unassessed | supported | qualified | inconclusive | refuted` — the canonical vocab Stage 0 Task 4 writes and Stage 1 renders. Parallel computed slot; never replaces authored verdict fields.

- [ ] **Step 1: Write the failing test** — a study with `computed_verdict: "qualified"` validates; one with `computed_verdict: "passed"` (wrong vocab) fails; a study without it still validates.
- [ ] **Step 2: Run to verify it fails** — `pytest tests/test_study_schema_computed_verdict.py -v`.
- [ ] **Step 3: Add `computed_verdict`** (string enum of the five canonical values) to `study.schema.json` properties, with a description noting it is a computed parallel slot projected by `canonical_verdict`, never authored. Keep additive.
- [ ] **Step 4: Run to verify it passes** — plus `pytest tests/test_study_schema_canonical.py -q` for no regression.
- [ ] **Step 5: Commit** — `feat(schema): add canonical computed_verdict slot to study.schema`

### Task 3: `derive_concepts()` — the overlay derivation

**Files:**
- Create: `viva_superpowers/concept_overlay.py`
- Test: `tests/test_concept_overlay.py`

**Interfaces:**
- Consumes: an investigation spec dict + `studies_by_slug: dict[str, dict]` (same shape `linkage_index.build_index` consumes).
- Produces: `derive_concepts(inv_spec, studies_by_slug) -> list[dict]` — each dict is a Concept in the Task-1 on-disk shape with `derived: True`, `member_studies` from gate/act membership (plan_gates member_studies, else plan_acts `gates`→members, else each study's own gate tag), `org_state` inferred (`consolidated` if the gate's members include an `arms[]`-bearing study, else `exploring`). Pure; ephemeral; never writes YAML. Legacy investigation with no gates/acts → `[]`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_concept_overlay.py
def test_derives_one_concept_per_gate():
    inv = {"name": "og", "title": "OG",
           "plan_gates": [{"id": "C", "member_studies": ["og-energetics"]}]}
    studies = {"og-energetics": {"name": "og-energetics", "pipeline_gate": {"gate_status": "passed"}}}
    concepts = derive_concepts(inv, studies)
    assert [c["from_gate"] for c in concepts] == ["C"]
    assert concepts[0]["member_studies"] == ["og-energetics"]
    assert concepts[0]["derived"] is True

def test_no_gates_yields_no_concepts():
    assert derive_concepts({"name": "x", "title": "X"}, {}) == []

def test_consolidated_org_state_when_member_has_arms():
    inv = {"name": "og", "title": "OG", "plan_gates": [{"id": "D", "member_studies": ["og-heredity"]}]}
    studies = {"og-heredity": {"name": "og-heredity", "arms": [{"source_study": "og-inheritance"}]}}
    assert derive_concepts(inv, studies)[0]["org_state"] == "consolidated"
```

- [ ] **Step 2: Run to verify it fails** — `pytest tests/test_concept_overlay.py -v` → FAIL (module missing).
- [ ] **Step 3: Implement `derive_concepts(inv_spec: dict, studies_by_slug: dict) -> list[dict]`** in `viva_superpowers/concept_overlay.py`. Read `plan_gates` (fallback `plan_acts` overlay `gates:`); per gate emit a concept `{id: slug(gate_id), from_gate, member_studies, org_state, derived: True}`; `org_state="consolidated"` iff any member study has a non-empty `arms`. No external deps.
- [ ] **Step 4: Run to verify it passes** — `pytest tests/test_concept_overlay.py -v` → PASS.
- [ ] **Step 5: Commit** — `feat(concept-overlay): derive ephemeral Concepts from plan_gates/plan_acts`

### Task 4: `canonical_verdict()` — vocab projection

**Files:**
- Create: `viva_superpowers/verdict_vocab.py`
- Test: `tests/test_verdict_vocab.py`

**Interfaces:**
- Consumes: a study spec dict (reads `pipeline_gate.gate_evaluator`/`gate_status`, report-card verdicts, `conclusion_verdicts`).
- Produces: `canonical_verdict(study_spec) -> Literal["unassessed","supported","qualified","inconclusive","refuted"]` + `canonical_verdict_detail(study_spec) -> dict` with `{verdict, source_vocab, diverges: bool}`. Deterministic priority: a coded `gate_evaluator.result` first, then card worst-of, then authored; `diverges=True` when sources disagree. Never guesses — absent evidence → `unassessed`.

- [ ] **Step 1: Write the failing test** — map `gate_evaluator.result=="passed"` → `supported`; `"failed"` → `refuted`; `"needs_calibration"` → `qualified`; card `mismatch` with authored `passed` → `inconclusive`/`diverges:True`; empty → `unassessed`.
- [ ] **Step 2: Run to verify it fails** — `pytest tests/test_verdict_vocab.py -v`.
- [ ] **Step 3: Implement** the projection table + `diverges` detection in `verdict_vocab.py`. Pure, `eval`-free.
- [ ] **Step 4: Run to verify it passes.**
- [ ] **Step 5: Commit** — `feat(verdict): canonical_verdict projection over the four existing vocabs`

### Task 5: Prove Stage 0 on the live genesis workspace

- [ ] **Step 1:** Write `tests/test_concept_overlay_genesis.py` that loads the real `~/code/viva-genesis` `origins-of-life-vent` investigation.yaml + studies (skip-if-absent, like the golden tests) and asserts `derive_concepts` returns one concept per gate A1/A2/B/C/D/E with non-empty members and `canonical_verdict` runs on every member without raising.
- [ ] **Step 2: Run** → PASS (or `importorskip`/skip when the workspace is absent, mirroring existing golden-study tests).
- [ ] **Step 3: Commit** — `test(concept-overlay): prove derivation against the live genesis gate spine`

---

## Stage 2 — Concept as hybrid Store (persist the authored half)

**Goal (RFC-0004 §3):** make a Concept a *persistent knowledge Store*, not derived-only. Today `concepts[]` is derived-first + ephemeral; the authored half (synthesis, assessment, open_questions, revision history) has no durable home. Persist it, never clobbering derivation.

**Files:** viva-template `investigation.schema.json` (authored concept fields already on the draft branch — add `revisions[]`); viva_superpowers `concept_store.py` (new) + extend `concept_overlay`; `tests/test_concept_store.py`.

- [ ] **T1 — schema:** add `concepts[].revisions[]` (versioned `{at, by, synthesis, assessment, note}`). Test: additive + v2/v3 back-compat.
- [ ] **T2 — `load_concepts(inv_spec) -> list[dict]`:** merge authored `concepts[]` over derived (authored wins on synthesis/assessment; derived fills member_studies + verdict projection; `derived:false` once authored). Never overwrite authored. Test the merge precedence.
- [ ] **T3 — `write_concept(inv_dir, concept_id, *, synthesis=, assessment=, open_questions=, note=)`:** ruamel comment-preserving; appends a `revisions[]` entry; idempotent; fill-absent; sibling concepts untouched. Test round-trip + revision append + no-clobber.
- [ ] **T4 — wire into `/api/concept-overlay`:** return merged (authored+derived); render shows authored synthesis when present.
- [ ] **T5 — prove on genesis:** author a synthesis for gate C; verify persisted + rendered + re-derivation leaves it intact.

## Stage 3 — Declarative inquiry operations

**Goal (RFC-0004 §5):** `consolidate`/`split`/`reopen`/`assess`/`narrate` as declarative transaction-boundary ops, each **preview → invariant-check → atomic commit**, non-destructive. Supersedes the shipped destructive `/viva-consolidate`.

**Files:** viva_superpowers `inquiry_ops.py` (engine: `plan_<op>(...) -> OpPlan` pure preview; `apply_op(plan)` atomic ruamel+git commit); rewrite `skills/viva-consolidate/SKILL.md` non-destructive; add `viva-split`/`viva-reopen`/`viva-assess`; `tests/test_inquiry_ops.py`.

- [ ] **T1 — `consolidate(study_refs, concept_id)` NON-DESTRUCTIVE:** create/extend a Concept grouping the refs + author a synthesis stub; **member `study.yaml` files are NOT deleted.** Invariant: no study/finding/null lost. Test: members survive on disk; concept created; idempotent.
- [ ] **T2 — `split(concept_id, partition)`:** partition `member_studies` into sub-concepts (or promote an arm-cluster to a member Study by verdict-independence); prior grouping retained in `revisions[]`. Test: all members preserved; prior grouping recoverable.
- [ ] **T3 — `reopen(concept_id, reason)`:** `org_state=reopened` + a revision with reason + new open_question; **prior assessment retained** (`supersedes_revision`). Test: prior assessment retrievable.
- [ ] **T4 — `assess(proposition_ref, finding_refs, verdict, basis)`:** write a versioned Assessment citing findings; **never overwrite a prior verdict** (append). Test: prior verdict retrievable; cites findings.
- [ ] **T5 — `narrate(inv)`:** project Concept syntheses into an ordered report section; claims link to member studies. Test: narrative lines carry study refs.
- [ ] Each op calls the Stage-4 invariant gate before commit; a failed op leaves the prior graph usable.

## Stage 4 — Invariants + three graphs explicit (outline)

- `op_invariants.check(plan) -> [violation]` generalizing genesis's 3 fail-loud guards (yaml-parse / stale-source-path / dangling-edge-target) + the 7 RFC-0004 hard invariants (Identity, Non-destructive, Epistemic-integrity, Typed-relations, Recoverable-history, Projection-correctness, Atomicity); called by every Stage-3 op before commit (fail-loud).
- Name the three graphs: `builds_on/tests/motivates/alternative_to` + `parent_studies.relation` → `E_sci`; evidence/provenance fields → `E_evid`/`E_prov`; `concepts[].member_studies` → `E_org`. Surface via the linkage index; §11 views render by family.
- Retire RFC-0003 breathe semantics (destructive consolidate replaced by Stage 3's non-destructive op).

## Stage 5 — Contract spine: the four wires (gated on bigraph-schema 1.8.x)

**Goal (RFC-0004 §4/§4.1):** generalize the study↔composite seam from existence-check to a typed contract check, reusing existing primitives (`composite_audit`, `core._compute_unit_scale`, `bigraph_schema.units`). The vocabulary already exists on both sides; this connects it.

- [ ] **T0 — land bigraph-schema 1.8.x** (typed `ProcessContract` + `contract_audit`) onto the pinned version (release branch → main → bump pin; today's venv is 1.4.5, face-only). Gate for T1–T4.
- [ ] **T1 — `available_observables` returns per-leaf `{type, units, min, max}`** (via `core.access`, mirroring `composite_audit._safe_units`). Test: a known observable reports its units.
- [ ] **T2 — `validate_readouts` type/unit/shape check:** compare a readout's declared `units` (already on `ResolvedReadout.units`) + shape against the leaf type via `core._compute_unit_scale`; add statuses `unit_mismatch`/`shape_mismatch` alongside `not_in_structure`. Test: a `[fg]` band on a `[mol]` observable → `unit_mismatch`.
- [ ] **T3 — `test_contract` bands carry + reconcile units** before the margin (today `units=` is display-only). Test: convertible unit reconciles; incompatible errors.
- [ ] **T4 — `contract_face_diff(study.contract.face, composite contract_of(...).face)`** — surface port/type/unit disagreements between a study's authored contract and the composite it runs. Test: a mismatched face is flagged.
- [ ] **Discipline:** these are structural/dimensional checks; they NEVER upgrade a scientific verdict (RFC-0004 §4).

## Stage 6 — Genesis migration (outline)

- Run the selective un-consolidation of genesis's `arms[]` studies into Concept + member-Study form via the Stage-3 `split` op, licensed per-arm by verdict-independence (the strengthening-plan test). Derived Concepts for A1/A2/B/C/D/E remain; authored syntheses added. lint + full pytest green per PR; worktree off current origin/main.

## Self-review notes

- Spec coverage vs RFC-0004: §2 ontology + §3 Concept-Store → Stages 0/2; §2 three graphs → Stage 4; §4 contract spine → Stage 5; §5 operations → Stage 3; §6 real-vs-build + §8 migration → Stages 5-T0/6. The destructive→non-destructive supersession is a Global Constraint, enforced from Stage 3.
- Proportion: Stages 2/3/5 are decomposed (the RFC-0004-specific, pytest-verifiable work); Stages 4/6 are outlined (they depend on 2/3/5's realized interfaces).
- Dependency note: Stage 5 is **gated on bigraph-schema 1.8.x**; Stages 2/3/4/6 have no external version dependency and can proceed on the draft branches now.
