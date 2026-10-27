"""The validator layer — RFC-0007.

One **validation-record** shape and a **(type, scope)-tagged registry**, a
generalization of the checks the framework already runs (``narrative.audit``,
``rigor``, ``band_provenance``, ``study_contract``, …). A validator is a pure,
derive-first projector ``V(T, C, E) -> [record]``; it never mutates the artifact
it evaluates (evaluation ⊥ intervention — ``set-verdict`` / ``resolve`` / ``relate``
are the only writers).

Two **independent** axes classify every validator:

* **type** — what kind of correctness/justification is tested (8).
* **scope** — which graph artifact is evaluated (7).

The record carries **two** result statuses, and the split is the layer's core
principle — "a successful computational check does not establish biological truth":

* ``execution_status`` — did the check run and pass? Every validator sets it.
* ``scientific_judgment`` — does the artifact's scientific claim hold? ``None`` =
  "this validator does not speak to scientific truth".

A validator *type* that can only establish execution correctness (``structural``,
``computational``, ``visual``) **must** leave ``scientific_judgment`` null; this is
enforced at record construction and re-checked each cycle by
:func:`epistemic_separation_violations` (wired into
``discovery_engine.invariants``).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

#: what kind of correctness/justification a validator tests.
VALIDATOR_TYPES = (
    "structural", "semantic", "computational", "empirical",
    "logical", "scientific", "narrative", "visual",
)
#: which graph artifact a validator evaluates.
VALIDATOR_SCOPES = (
    "component", "claim", "figure", "study",
    "relationship", "investigation", "narrative",
)
#: did the check run and pass? (orthogonal to the scientific judgment).
EXECUTION_STATUSES = ("passed", "failed", "inconclusive", "error")
#: does the artifact's scientific claim hold? (``None`` = validator asserts no truth).
#: This is the canonical verdict vocabulary; the spec's ``unresolved``/``contested``
#: map to ``unresolved`` / an open challenge (RFC-0007 §6).
JUDGMENT_VALUES = ("supported", "qualified", "refuted", "unresolved")

#: types that can only establish execution correctness — they must leave the
#: scientific judgment null (a rerun that conserves mass is not a supported claim).
_EXECUTION_ONLY_TYPES = frozenset({"structural", "computational", "visual"})


def establishes_judgment(vtype: str) -> bool:
    """True if a validator of this type may assert a ``scientific_judgment``."""
    return vtype not in _EXECUTION_ONLY_TYPES


def validation_record(*, type: str, scope: str, target: str,
                      execution_status: str, scientific_judgment: str | None = None,
                      criteria: list | None = None, findings: list | None = None,
                      recommendations: list | None = None, evidence: list | None = None,
                      validator_id: str | None = None, validator_version: str = "0.1",
                      evaluated_at: str | None = None) -> dict:
    """Build one validation record, validating both axes and the two-axis rule.

    ``evaluated_at`` is left ``None`` unless supplied: the record is produced inside
    the pure, deterministic cycle projection (same evidence → same record), so a
    wall-clock stamp belongs to the persist step, not here."""
    if type not in VALIDATOR_TYPES:
        raise ValueError(f"type must be one of {VALIDATOR_TYPES}, got {type!r}")
    if scope not in VALIDATOR_SCOPES:
        raise ValueError(f"scope must be one of {VALIDATOR_SCOPES}, got {scope!r}")
    if execution_status not in EXECUTION_STATUSES:
        raise ValueError(f"execution_status must be one of {EXECUTION_STATUSES}, got {execution_status!r}")
    if scientific_judgment is not None:
        if scientific_judgment not in JUDGMENT_VALUES:
            raise ValueError(f"scientific_judgment must be one of {JUDGMENT_VALUES} or None, "
                             f"got {scientific_judgment!r}")
        if not establishes_judgment(type):
            raise ValueError(f"a {type!r} validator establishes execution correctness only and "
                             f"must leave scientific_judgment null (got {scientific_judgment!r})")
    return {
        "type": type,
        "scope": scope,
        "target": target,
        "criteria": list(criteria or []),
        "result": {
            "execution_status": execution_status,
            "scientific_judgment": scientific_judgment,
        },
        "findings": list(findings or []),
        "recommendations": list(recommendations or []),
        "evidence": list(evidence or []),
        "provenance": {
            "validator_id": validator_id,
            "validator_version": validator_version,
            "evaluated_at": evaluated_at,
        },
    }


# ---------------------------------------------------------------------------
# Validator context + registry
# ---------------------------------------------------------------------------

@dataclass
class ValidationContext:
    """The already-derived inputs a validator reads (it computes nothing new)."""
    inv_spec: dict = field(default_factory=dict)
    studies: dict = field(default_factory=dict)
    argument: dict = field(default_factory=dict)
    narrative: dict = field(default_factory=dict)
    audit: list = field(default_factory=list)


#: the default process-wide registry (adapters below register into it).
_REGISTRY: list[dict] = []


def validator(*, type: str, scope: str, id: str, registry: list | None = None):
    """Register ``fn(ctx) -> [record]`` under its ``(type, scope)`` and id."""
    if type not in VALIDATOR_TYPES:
        raise ValueError(f"type must be one of {VALIDATOR_TYPES}, got {type!r}")
    if scope not in VALIDATOR_SCOPES:
        raise ValueError(f"scope must be one of {VALIDATOR_SCOPES}, got {scope!r}")
    reg = _REGISTRY if registry is None else registry

    def deco(fn: Callable):
        reg.append({"type": type, "scope": scope, "id": id, "fn": fn})
        return fn

    return deco


def registry() -> list[dict]:
    """The registered validators (a copy of the default registry)."""
    return list(_REGISTRY)


def run_validators(ctx: ValidationContext | None, registry: list | None = None) -> list[dict]:
    """Dispatch every registered validator over ``ctx`` and collect the records."""
    reg = _REGISTRY if registry is None else registry
    out: list[dict] = []
    for v in reg:
        out.extend(v["fn"](ctx) or [])
    return out


def coverage_matrix(registry: list | None = None) -> dict[str, dict[str, list[str]]]:
    """The type × scope grid of registered validator ids — empty cells included."""
    reg = _REGISTRY if registry is None else registry
    cells: dict[str, dict[str, list[str]]] = {
        t: {s: [] for s in VALIDATOR_SCOPES} for t in VALIDATOR_TYPES}
    for v in reg:
        cells[v["type"]][v["scope"]].append(v["id"])
    return cells


def epistemic_separation_violations(records: list[dict]) -> list[dict]:
    """Records whose type can only establish execution correctness yet assert a
    scientific judgment — the executable form of "a passing computational check
    does not establish biological truth"."""
    out: list[dict] = []
    for r in records or []:
        if not isinstance(r, dict):
            continue
        judgment = (r.get("result") or {}).get("scientific_judgment")
        vtype = r.get("type")
        if judgment is not None and not establishes_judgment(vtype):
            out.append({"invariant": "epistemic_separation", "target": r.get("target"),
                        "detail": (f"{vtype} validator establishes execution correctness only "
                                   f"but set scientific_judgment {judgment!r}")})
    return out


# ---------------------------------------------------------------------------
# Shipped adapters (RFC-0007 Phase 1) — thin wrappers over existing checks
# ---------------------------------------------------------------------------

@validator(type="logical", scope="claim", id="logical.claim.provenance")
def _provenance(ctx: ValidationContext) -> list[dict]:
    """An assessed claim (supported/qualified/refuted) that traces to no evidence.
    The same check ``discovery_engine.invariants`` ran inline, now a record."""
    recs: list[dict] = []
    claims = (getattr(ctx, "argument", None) or {}).get("claims") or {}
    for cid, c in claims.items():
        if not isinstance(c, dict):
            continue
        v = c.get("verdict")
        if v in ("supported", "qualified", "refuted") and not (c.get("evidence_refs") or []):
            recs.append(validation_record(
                type="logical", scope="claim", target=cid,
                execution_status="failed", scientific_judgment=None,
                criteria=["evidence_provenance"],
                findings=[f"claim is {v} but traces to no evidence"],
                recommendations=["attach evidence_refs, or downgrade the verdict to unresolved"],
                validator_id="logical.claim.provenance"))
    return recs


@validator(type="narrative", scope="narrative", id="narrative.narrative.coherence")
def _narrative_coherence(ctx: ValidationContext) -> list[dict]:
    """Evidential coherence of the reading — one record summarizing ``audit`` gaps
    (the unsupported transitions the narrative asserts)."""
    gaps = getattr(ctx, "audit", None) or []
    if not gaps:
        return [validation_record(
            type="narrative", scope="narrative", target="narrative",
            execution_status="passed", criteria=["evidential_coherence"],
            validator_id="narrative.narrative.coherence")]
    return [validation_record(
        type="narrative", scope="narrative", target="narrative",
        execution_status="failed", criteria=["evidential_coherence"],
        findings=[g.get("reason", "unsupported transition") for g in gaps],
        recommendations=[(g.get("followup") or {}).get("title", "") for g in gaps],
        validator_id="narrative.narrative.coherence")]
