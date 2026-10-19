"""Declarative inquiry operations over the Concept Store (RFC-0004 §5).

consolidate / split / reopen / assess / narrate are declarative transactions:
each previews its change, checks its scientific invariants, and (on commit)
applies an atomic write via ``concept_store.write_concept``. All are
NON-DESTRUCTIVE — member Study files are never deleted, and prior verdicts /
groupings survive in the Concept's revision history. This supersedes the
destructive ``/viva-consolidate`` of RFC-0003.

Every op returns ``{op, concept_id, summary, violations, applied}``. With
``commit=False`` it previews (computes violations, writes nothing). A non-empty
``violations`` blocks the write (a failed op leaves the prior graph usable).
"""
from __future__ import annotations

from pathlib import Path

import yaml

from viva_superpowers.concept_store import write_concept, load_concepts

_CANONICAL_VERDICTS = ("unassessed", "supported", "qualified", "inconclusive", "refuted")


def _studies_dir(inv_dir) -> Path:
    # inv_dir = <ws>/investigations/<slug>  →  <ws>/studies
    return Path(inv_dir).parent.parent / "studies"


def _missing_studies(inv_dir, refs) -> list:
    sd = _studies_dir(inv_dir)
    return [r for r in refs if not (sd / r / "study.yaml").is_file()]


def _load(inv_dir) -> dict:
    p = Path(inv_dir) / "investigation.yaml"
    return (yaml.safe_load(p.read_text(encoding="utf-8")) or {}) if p.is_file() else {}


def _member_studies(inv_dir, concept_id) -> list:
    for c in (_load(inv_dir).get("concepts") or []):
        if c.get("id") == concept_id:
            return list(c.get("member_studies") or [])
    return []


def _result(op, concept_id, summary, violations, applied) -> dict:
    return {"op": op, "concept_id": concept_id, "summary": summary,
            "violations": violations, "applied": applied}


def consolidate(inv_dir, concept_id, study_refs, *, synthesis=None, title=None,
                by=None, commit=True) -> dict:
    """Group Study references into a Concept and author a synthesis — NON-destructively.

    Invariant: every referenced Study must exist (consolidation groups, never
    deletes sources). The member ``study.yaml`` files are left untouched.
    """
    study_refs = list(study_refs)
    violations = []
    missing = _missing_studies(inv_dir, study_refs)
    if missing:
        violations.append(f"non-destructive: member studies not found (would lose sources): {missing}")
    summary = f"group {len(study_refs)} studies into concept '{concept_id}' (non-destructive)"
    applied = False
    if commit and not violations:
        write_concept(inv_dir, concept_id, member_studies=study_refs, org_state="consolidated",
                      synthesis=synthesis or f"Groups {', '.join(study_refs)}.", title=title,
                      by=by, note=f"consolidated {', '.join(study_refs)}")
        applied = True
    return _result("consolidate", concept_id, summary, violations, applied)


def split(inv_dir, concept_id, partition, *, by=None, commit=True) -> dict:
    """Partition a Concept's members into sub-Concepts; the prior grouping is
    recorded on the original Concept's revision history (recoverable)."""
    items = list(partition.items()) if isinstance(partition, dict) else list(partition)
    sub_ids = [sid for sid, _ in items]
    all_sub = [r for _, refs in items for r in refs]
    prior = _member_studies(inv_dir, concept_id)

    violations = []
    missing = _missing_studies(inv_dir, all_sub)
    if missing:
        violations.append(f"non-destructive: studies not found: {missing}")
    uncovered = [m for m in prior if m not in all_sub]
    if uncovered:
        violations.append(f"split must cover all prior members; uncovered: {uncovered}")

    summary = f"split '{concept_id}' into {sub_ids}"
    applied = False
    if commit and not violations:
        for sid, refs in items:
            write_concept(inv_dir, sid, member_studies=list(refs), org_state="consolidated",
                          by=by, note=f"split from {concept_id}")
        write_concept(inv_dir, concept_id, org_state="reopened", by=by,
                      note=f"split into {sub_ids}",
                      extra={"prior_members": prior, "split_into": sub_ids})
        applied = True
    return _result("split", concept_id, summary, violations, applied)


def reopen(inv_dir, concept_id, reason, *, open_question=None, by=None, commit=True) -> dict:
    """Resume inquiry on a Concept: mark it ``reopened`` + log the reason. The
    prior assessment is retained (not cleared); a new open question is appended."""
    summary = f"reopen '{concept_id}': {reason}"
    applied = False
    if commit:
        oq = None
        if open_question:
            existing = []
            for c in (_load(inv_dir).get("concepts") or []):
                if c.get("id") == concept_id:
                    existing = list(c.get("open_questions") or [])
                    break
            oq = existing + [open_question]
        write_concept(inv_dir, concept_id, org_state="reopened", open_questions=oq,
                      by=by, note=f"reopened: {reason}")
        applied = True
    return _result("reopen", concept_id, summary, [], applied)


def assess(inv_dir, concept_id, verdict, basis, *, finding_refs=None, by=None, commit=True) -> dict:
    """Write a versioned Assessment on a Concept from cited Findings. The prior
    verdict is NEVER overwritten — it survives in the revision history."""
    violations = []
    if verdict not in _CANONICAL_VERDICTS:
        violations.append(f"verdict '{verdict}' not in canonical vocab {_CANONICAL_VERDICTS}")
    assessment = {"verdict": verdict, "basis": basis}
    if finding_refs:
        assessment["finding_refs"] = list(finding_refs)
    summary = f"assess '{concept_id}': {verdict}"
    applied = False
    if commit and not violations:
        write_concept(inv_dir, concept_id, assessment=assessment, by=by, note=f"assessed {verdict}")
        applied = True
    return _result("assess", concept_id, summary, violations, applied)


def narrate(inv_spec: dict, studies_by_slug: dict | None = None) -> list:
    """Project the Concept syntheses into an ordered, evidence-linked narrative.
    Each entry carries the Concept's synthesis + its member Studies, so every
    claim stays linked to its evidence."""
    out = []
    for c in load_concepts(inv_spec, studies_by_slug or {}):
        out.append({
            "concept": c.get("id"),
            "title": c.get("title"),
            "synthesis": c.get("synthesis"),
            "assessment": c.get("assessment"),
            "member_studies": c.get("member_studies") or [],
            "open_questions": c.get("open_questions") or [],
        })
    return out
