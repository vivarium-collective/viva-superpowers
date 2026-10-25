"""Derive the investigation knowledge store — Concepts + canonical Verdicts.

This is the derive-first half of the process-bigraph knowledge layer. A `Concept`
is a persistent, revisable synthesis-grouping over member Studies; a canonical
`Verdict` record keeps the Progress (execution) and Verdict (scientific) axes
INDEPENDENT — operation/execution success never sets a scientific verdict.

The derived projection here is read-only: it writes nothing into study.yaml or
investigation.yaml. An authored half (persisted in the investigation's
`knowledge` block) is merged over it by `merge_knowledge` (authored wins, derived
fills, empty never clobbers). Concept *grouping* is an epistemic act performed by
the slice-2 `consolidate` op — the derived projection seeds one singleton Concept
per Study.

Public API
----------
canonical_verdict(study_spec) -> dict
    {verdict, verdict_source, diverges, rationale, evidence_refs[, progress]}.
derive_knowledge(inv_spec, studies_by_slug) -> dict
    {"concepts": {concept_id: {...}}, "verdicts": {slug: {...}}}.
merge_knowledge(authored, derived) -> dict
    Section-wise, entry-wise merge with the authored-wins / empty-never-clobbers
    rule.
"""
from __future__ import annotations

from typing import Any

from .study_verdict import roll_up_verdict


# ---------------------------------------------------------------------------
# Vocabularies
# ---------------------------------------------------------------------------

#: coded roll_up_verdict.result  ->  canonical scientific verdict
_CANON: dict[str, str] = {
    "passed": "supported",
    "failed": "refuted",
    "needs_calibration": "qualified",
    "blocked": "unassessed",
    "not_started": "unassessed",
}

#: authored study.yaml `verdict` values that are already canonical
_AUTHORED_OK = {"supported", "qualified", "inconclusive", "refuted"}

#: the Progress axis — projected verbatim from study.yaml `execution_status`
_PROGRESS_OK = {"proposed", "planned", "running", "completed", "failed"}

#: values that never clobber an existing one during a merge
_EMPTY = (None, "", [], {})


# ---------------------------------------------------------------------------
# Canonical verdict (per study)
# ---------------------------------------------------------------------------

def canonical_verdict(study_spec: dict) -> dict:
    """Canonical Verdict record for one study, two axes kept independent.

    The derived verdict comes from the coded test roll-up; an authored
    ``verdict`` in study.yaml wins when present. ``progress`` is projected
    separately from ``execution_status`` and never feeds the verdict — a failed
    execution is not a refuted hypothesis, and a completed run may be refuted.
    """
    derived = _CANON.get(roll_up_verdict(study_spec).get("result"), "unassessed")

    authored = study_spec.get("verdict")
    authored = authored if authored in _AUTHORED_OK else None

    verdict = authored or derived
    source = "authored" if authored else "derived"
    diverges = bool(authored) and authored != derived

    if authored:
        rationale = "Authored verdict recorded in study.yaml."
    else:
        rationale = f"Derived from coded test roll-up (result: {derived})."

    out: dict[str, Any] = {
        "verdict": verdict,
        "verdict_source": source,
        "diverges": diverges,
        "rationale": rationale,
        "evidence_refs": _finding_ids(study_spec),
    }

    progress = study_spec.get("execution_status")
    if progress in _PROGRESS_OK:
        out["progress"] = progress

    return out


def _finding_ids(spec: dict) -> list[str]:
    ids: list[str] = []
    for f in spec.get("findings") or []:
        if isinstance(f, dict) and f.get("id"):
            ids.append(str(f["id"]))
    return ids


def _concept_question(spec: dict, slug: str) -> str:
    """A singleton Concept's unifying question — the study's own question, never
    fabricated. Falls back through the real authored fields before the slug."""
    purpose = spec.get("purpose")
    candidates = [
        spec.get("question"),
        purpose.get("question") if isinstance(purpose, dict) else None,
        spec.get("claim"),
        spec.get("title"),
    ]
    for c in candidates:
        if isinstance(c, str) and c.strip():
            return c
    return f"Study {slug}"


# ---------------------------------------------------------------------------
# Derive the knowledge projection for an investigation
# ---------------------------------------------------------------------------

def derive_knowledge(inv_spec: dict, studies_by_slug: dict[str, dict]) -> dict:
    """Project the read-only knowledge store from canonical membership + findings.

    ``verdicts`` carries a canonical verdict for every member study that has a
    spec; a member listed in ``studies[]`` with no spec is skipped, not fatal.
    ``concepts`` seeds one derived singleton Concept per study — grouping into
    themed Concepts is the slice-2 ``consolidate`` act.
    """
    member_slugs = inv_spec.get("studies") or list(studies_by_slug.keys())

    concepts: dict[str, dict] = {}
    verdicts: dict[str, dict] = {}
    for slug in member_slugs:
        spec = studies_by_slug.get(slug)
        if spec is None:
            continue
        verdicts[slug] = canonical_verdict(spec)
        concepts[slug] = {
            "question": _concept_question(spec, slug),
            "study_refs": [slug],
            "synthesis": None,
            "org_state": "exploring",
            "derived": True,
        }

    return {"concepts": concepts, "verdicts": verdicts}


# ---------------------------------------------------------------------------
# Merge authored over derived
# ---------------------------------------------------------------------------

def merge_knowledge(authored: dict | None, derived: dict | None) -> dict:
    """Merge the authored knowledge half over the derived projection.

    Authored wins field-by-field, derived fills, and an empty authored value
    never clobbers a derived one. Applied per section (concepts, verdicts) and
    per entry; an authored-only entry is added.
    """
    out: dict[str, dict] = {}
    for section in ("concepts", "verdicts"):
        a = (authored or {}).get(section) or {}
        d = (derived or {}).get(section) or {}
        merged = {k: dict(v) for k, v in d.items()}
        for key, a_entry in a.items():
            merged[key] = _merge_entry(merged.get(key), a_entry)
        out[section] = merged
    return out


def _merge_entry(derived_entry: dict | None, authored_entry: dict | None) -> dict:
    result = dict(derived_entry or {})
    for k, v in (authored_entry or {}).items():
        if v in _EMPTY:
            continue
        result[k] = v
    return result
