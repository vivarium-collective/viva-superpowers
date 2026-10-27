# RFC-0007 — The Validator Layer

**Status:** Draft · additive · continues RFC-0003 (investigation graphs) and
RFC-0005 (narrative & argument layer).
**Foundation:** the shipped derive-first discovery cycle
(`viva_superpowers/discover.py:run_cycle`), the discovery crank
(`viva_superpowers/discovery_engine.py`), and the checks already scattered across
`narrative.py`, `rigor.py`, `band_provenance.py`, `study_contract.py`,
`report_linter.py`, `card_grade.py`.
**Source spec:** *Validator Types and Scopes* (investigation-graph validator
specification). This RFC adopts its two independent axes — **type** (what kind of
correctness is tested) and **scope** (which graph artifact is evaluated) — and its
`V(T, C, E) → (J, F, A)` contract, and shows they are a generalization of
machinery the framework already runs.

> **Scope.** We already run ~eight validators; they are hard-wired, each a
> different shape, only one of them (`narrative.audit`) wired into the crank, and
> none tagged by type/scope. This RFC adds (1) **one validation-record shape** and
> (2) **a validator registry**, then wires records through the **existing** audit
> spine and frontier. The vocabulary cleanup in §6 is as important as the new
> structure: our result/judgment/status terms have drifted into four overlapping
> families and this RFC canonicalizes them.

---

## 1. The formal object

A **validator** is an executable or AI-assisted evaluation of one graph artifact:

```
V(T, C, E) → (J, F, A)
```

`T` target artifact · `C` criteria · `E` available evidence → `J` judgment ·
`F` findings · `A` recommended actions. Two **independent** axes classify it:

- **type** — what kind of correctness/justification is tested (8):
  `structural · semantic · computational · empirical · logical · scientific · narrative · visual`
- **scope** — which graph artifact is evaluated (7):
  `component · claim · figure · study · relationship · investigation · narrative`

The axes are orthogonal: an *empirical* check at *claim* scope and an *empirical*
check at *study* scope are different cells of one matrix. The matrix, and **which
cells have validators**, is the coverage view the framework has never had.

## 2. This is a generalization of the audit spine, not a new system

`run_cycle` is already a pure derive-first projection — the audit spine — wired to
exactly one validator:

```
derive_knowledge → derive_argument → narrate → audit → synthesize_gates → open_calls
                                               └── the ONLY validator today (narrative)
```

`frontier()` already turns that bundle into typed, prioritized, op-carrying,
resolvable items via one helper, `add(kind, target, rationale)`, with
`_resolution_keys()` as the discharge. Map the spec onto what exists:

| Spec concept | Already in the spine |
|---|---|
| a **validator** `V(T,C,E)→(J,F,A)` | a derive-first projector (`audit`, `rigor`, `band_provenance`, `study_contract`, …) |
| a **validation record** | an `audit` gap · an `open_calls` entry · a `rigor` scorecard row · an `invariants()` violation — the same thing in four shapes |
| `execution_status ⊥ scientific_judgment` | `canonical_verdict` already projects `progress` separately and "never feeds the verdict"; frontier item 1 already separates behavior `PASS` from roll-up verdict |
| **recommendations / actions** `A` | the frontier `op` (`_OP`) + `resolutions` + `propose-followup` |
| **evaluation ⊥ intervention** | validators are read-only; `relate` / `set-verdict` / `resolve` are the separate op that executes |
| **re-validation triggers** | `run_cycle` is pure → re-derives every crank; `divergence` already compares authored vs derived |

So the work is to **lift the one hard-wired validator into a registry** and let its
records flow through the frontier that already exists.

## 3. The validation record (`#1`)

One shape, a superset of what `audit`/`open_calls`/`rigor` already emit:

```yaml
validator:
  type: scientific            # one of the 8
  scope: study                # one of the 7
  target: study_12            # the artifact id
  criteria: [controls_adequacy, evidence_sufficiency, alternative_explanations]
  result:
    execution_status: passed          # passed | failed | inconclusive | error
    scientific_judgment: unresolved   # supported | qualified | refuted | unresolved | null
  findings: ["Model reproduces observed behavior", "Competing mechanism not excluded"]
  recommendations: ["Add control simulation", "Compare competing hypotheses"]
  evidence: [figure_12a, simulation_run_34]
  provenance: {validator_id: scientific.study.controls, validator_version: "1.0", evaluated_at: "…"}
```

The record is **data, not a verdict write.** It is projected each cycle (derive
first), merged over any authored override, and never mutates the artifact it
evaluates — only `set-verdict`/`resolve`/`relate` do that (evaluation ⊥
intervention).

### The two-axis rule, made enforceable

`result` carries **two** statuses, and the split is the spec's core principle — "a
successful computational check does not establish biological truth." We make it a
hard invariant via the type axis:

- **execution_status** — did the check run and pass? (`passed · failed ·
  inconclusive · error`). Every validator sets this.
- **scientific_judgment** — does the artifact's scientific claim hold?
  (the canonical verdict vocabulary; `null` = "this validator does not speak to
  scientific truth").

A validator **type** that can only establish execution correctness —
`structural`, `computational`, `visual` — **must** leave `scientific_judgment`
null. Only `empirical`, `scientific`, `logical`, `semantic`, `narrative` types may
assert a judgment. `discovery_engine.invariants()` enforces this as
**`epistemic_separation`** (today documented in its docstring but unimplemented):
a record whose type cannot establish judgment yet sets one is a violation. This is
the executable form of "a model reran and conserved mass" ≠ "the claim is
supported."

## 4. The validator registry (`#2`)

A validator is a function tagged with its `(type, scope)` and an id:

```python
@validator(type="logical", scope="claim", id="logical.claim.provenance")
def provenance(ctx) -> list[ValidationRecord]: ...
```

`run_validators(ctx)` dispatches the registry over a `ValidationContext`
(the already-derived `inv_spec`, `studies_by_slug`, `argument`, `narrative`) and
returns records. The existing checks become **thin adapters**, no rewrites:

| Adapter wraps | type | scope |
|---|---|---|
| `narrative.audit` | narrative | narrative |
| `knowledge_store` provenance invariant | logical | claim |
| `rigor.py` scorecard | scientific | study / investigation |
| `band_provenance` / cite-bands | empirical | claim |
| `study_contract` / `test_contract` | structural | study / component |
| `study_observable_lint` | semantic | claim |
| argument `challenge` edges | logical | relationship |
| conservation ledger | computational | study |

`coverage_matrix(registry)` renders the type×scope grid and its empty cells — the
answer to "what's missing" becomes a standing report, not a one-off audit.

## 5. Wiring into the discovery cycle (`#3`, `#4`, `#5`)

Three small, additive touch-points — no new control flow:

- **`#3` — one line in `run_cycle`.** Add `"validations": run_validators(ctx)` to
  the returned bundle. `audit` stays as one registered validator, so `open_calls`
  and existing frontier kinds are unchanged (back-compat).
- **`#4` — one loop in `frontier()`.** For each **frontier-surfacing** validation
  record whose `execution_status` is `failed`/`error` and whose `(type,target)` is
  not in `_resolution_keys`, call the existing `add(...)`. A validator declares
  `surfaces="frontier"` (a real defect) or `surfaces="standing"` (scorecard-style
  feedback, the default); only the former reaches the actionable crank, so adding
  standing validators — rigor, band provenance — can never flood the frontier (they
  stay in the coverage/census view). `inconclusive` records are standing by nature.
  Records already surfaced by another path (narrative gaps via `open_calls`) are
  skipped so they are not double-counted. The record's `recommendations` seed the `op`.
- **`#5` — implement `epistemic_separation`** in `invariants()` over
  `cycle_result["validations"]` (§3).

The crank loop is unchanged: `crank → work the op → record/resolve → re-crank`.
Validators simply feed it more, already-typed, already-resolvable items.

### `#6` — re-validation as re-projection (implemented, Phase 4)

Because `run_cycle` is pure and records carry no wall-clock, staleness is "accepted
record ≠ freshly re-derived record." `discover snapshot-validations <inv>` writes a
content signature per record (`validation.record_signature`: type/scope/target + both
result statuses + findings, provenance excluded) into the investigation's
`validation_snapshot`. Each later cycle calls `validation.stale_records(fresh,
snapshot)`; a record whose signature drifted is `changed`, one whose target is gone is
`removed`, and a brand-new record is *not* stale. `frontier()` raises each as a
`stale_validation` item (priority 55, op `revalidate`), resolvable like any item. No
polling — the crank re-derives every turn; snapshotting is the explicit "I accept this
validation state" act, and drift from it is the re-evaluation trigger.

## 6. Vocabulary unification

Our result/judgment/status terms have drifted into four overlapping families. This
RFC canonicalizes them; adapters translate legacy fields, no stored data churns.

**Two axes, two vocabularies — never mixed:**

| Axis | Canonical values | Absorbs these legacy terms |
|---|---|---|
| **execution_status** (did the check run?) | `passed · failed · inconclusive · error` | gate `PASS`/`FAIL`, card grade, `gate_status`, `simulation_status`, `evaluation_status`'s run half, rigor `ok`/`warn`/`gap` |
| **scientific_judgment** (does the claim hold?) | `supported · qualified · refuted · unresolved · null` | `verdict` (`VERDICT_VOCAB`: `supported/qualified/inconclusive/refuted/unassessed`), `verdict_status`, the spec's `supported/refuted/unresolved/contested` |

Reconciliation decisions (adopted, so skills and renderers stop drifting):

- **`judgment` is the verdict.** `scientific_judgment` *is* the existing canonical
  `verdict`; we keep the verdict vocabulary as the judgment vocabulary. The spec's
  `contested` maps to an open **challenge** (tracked on the challenge axis, not a
  judgment value); the spec's `unresolved` maps to `inconclusive`/`unassessed`,
  normalized to **`unresolved`** going forward.
- **`progress` / `execution_status` is never a judgment.** `simulation_status`,
  `gate_status`, and the run half of `evaluation_status` are all **execution**
  facets; they fold into `execution_status`. A green run is `passed`, full stop.
- **"finding" is one word.** A `finding` is an observation a validator emits
  (`findings[]`); it is not a verdict and not a frontier item. `audit` "gaps",
  `rigor` rows, and `invariants()` violations are all **findings** under the
  record.
- **"recommendation" ≠ "resolution".** A `recommendation` (`A`) is what a validator
  suggests; a `resolution` is the authored record that an op *executed* a
  recommendation and discharged the item. Evaluation proposes; intervention
  resolves.

A glossary table (`docs/concepts/vivarium-workbench-model.md`) is updated in the
same change so the model doc and the code agree.

## 7. Staging

- **Phase 1 (this RFC's first landing):** the record shape + registry
  (`viva_superpowers/validation.py`), **one** real adapter wired end-to-end
  (`logical.claim.provenance`), a second registered to prove the matrix has
  multiple cells (`narrative.narrative`), the `run_cycle` line, the `frontier`
  loop, and the `epistemic_separation` invariant — the smallest step that proves
  the whole path, with the coverage matrix rendering.
- **Phase 2:** adapt the remaining existing checks (`rigor`, `band_provenance`,
  `study_contract`, …) into the registry — each a thin wrapper.
- **Phase 3:** the empty cells the matrix exposes — the `visual` type
  (plotted-state-vs-output) and `figure` scope are the genuinely-absent ones.
- **Phase 4 (landed):** re-validation/staleness (`#6`) — `snapshot-validations` +
  the `stale_validation` frontier kind.

## 8. Non-goals

- Not a new store: records are a derived projection over the RFC-0003/0005 typed
  store, cached like `knowledge_cycle`, never a source of truth.
- Not a verdict writer: validators never mutate the artifact; `set-verdict` /
  `resolve` / `relate` remain the only writers.
- Not a hard gate by default: like the rigor scorecard, records are standing
  feedback; promoting a cell to a merge gate is a per-cell decision, not this RFC.
