"""Concept-as-Store: merge the authored Concept record over the derived overlay,
and persist the authored half with a comment-preserving, append-only revision
history (RFC-0004 §3).

A Concept is a hybrid knowledge Store: the *derived* half (member_studies,
org_state, verdict projection) is recomputed from plan_gates + evidence; the
*authored* half (synthesis, assessment, open_questions, and its revision
history) is durable human content that must never be clobbered by re-derivation.

- ``load_concepts`` produces the merged view (authored wins, derived fills).
- ``write_concept`` persists authored fields via a ruamel round-trip and appends
  a revision snapshot (deduped against the last), so reopening/re-synthesizing
  preserves prior interpretation.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from viva_superpowers.concept_overlay import derive_concepts

# Values that must NOT overlay a derived field (empty authored field ≠ a clobber).
_EMPTY = (None, "", [], {})
_REV_KEYS = ("by", "synthesis", "assessment", "note")


def load_concepts(inv_spec: dict, studies_by_slug: dict) -> list[dict]:
    """Merge authored ``concepts[]`` over the derived overlay.

    Derived concepts (from ``derive_concepts``) supply member_studies/org_state/
    provenance; an authored concept with the same ``id`` overlays its non-empty
    fields (synthesis/assessment/title/…) and marks the result ``derived: False``.
    Authored concepts with no derived counterpart are included as-is. An empty
    authored field never clobbers a derived one.
    """
    derived = {c["id"]: c for c in derive_concepts(inv_spec, studies_by_slug)}
    authored: dict = {}
    for c in (inv_spec.get("concepts") or []):
        if isinstance(c, dict) and c.get("id"):
            authored[c["id"]] = c

    out: list[dict] = []
    order = list(derived.keys()) + [cid for cid in authored if cid not in derived]
    for cid in order:
        base = dict(derived.get(cid) or {})
        auth = authored.get(cid)
        if auth:
            for k, v in auth.items():
                if v not in _EMPTY:
                    base[k] = v
            base["derived"] = False
        else:
            base.setdefault("derived", True)
        base.setdefault("id", cid)
        out.append(base)
    return out


def _same_revision(prev, rev) -> bool:
    """True if ``rev`` matches ``prev`` on authored content (ignoring the timestamp)."""
    if not prev:
        return False
    return all(prev.get(k) == rev.get(k) for k in _REV_KEYS)


def write_concept(
    inv_dir,
    concept_id: str,
    *,
    synthesis: str | None = None,
    assessment: dict | None = None,
    open_questions: list | None = None,
    member_studies: list | None = None,
    org_state: str | None = None,
    title: str | None = None,
    note: str | None = None,
    by: str | None = None,
    at: str | None = None,
    extra: dict | None = None,
) -> bool:
    """Persist the authored half of a Concept into ``investigation.yaml``.

    Comment-preserving (ruamel round-trip); creates the concept if absent; sets
    the provided authored/structural fields; marks ``derived: False``; appends a
    revision snapshot (of the interpretation + any ``extra``) unless it
    duplicates the last. ``member_studies``/``org_state``/``title`` are structural
    (not interpretation) and are not required to carry a revision. Returns True if
    the file changed.
    """
    from ruamel.yaml import YAML

    inv_path = Path(inv_dir) / "investigation.yaml"
    yaml = YAML()
    yaml.preserve_quotes = True
    with open(inv_path, encoding="utf-8") as f:
        data = yaml.load(f) or {}

    concepts = data.get("concepts")
    if concepts is None:
        concepts = []
        data["concepts"] = concepts

    concept = None
    for c in concepts:
        if isinstance(c, dict) and c.get("id") == concept_id:
            concept = c
            break
    if concept is None:
        concept = {"id": concept_id}
        concepts.append(concept)

    structural = False
    if synthesis is not None:
        concept["synthesis"] = synthesis
    if assessment is not None:
        concept["assessment"] = assessment
    if open_questions is not None:
        concept["open_questions"] = open_questions
    if member_studies is not None:
        concept["member_studies"] = list(member_studies)
        structural = True
    if org_state is not None:
        concept["org_state"] = org_state
        structural = True
    if title is not None:
        concept["title"] = title
        structural = True
    concept["derived"] = False

    rev: dict = {"at": at or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
    if by:
        rev["by"] = by
    if synthesis is not None:
        rev["synthesis"] = synthesis
    if assessment is not None:
        rev["assessment"] = assessment
    if note:
        rev["note"] = note
    if extra:
        rev.update(extra)

    rev_has_content = bool(by or synthesis is not None or assessment is not None or note or extra)

    revisions = concept.get("revisions")
    if revisions is None:
        revisions = []
        concept["revisions"] = revisions

    appended = rev_has_content and not _same_revision(revisions[-1] if revisions else None, rev)
    if appended:
        revisions.append(rev)

    if not (structural or appended):
        return False  # nothing new to record; leave the file untouched

    tmp = inv_path.with_suffix(".yaml.tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        yaml.dump(data, f)
    tmp.replace(inv_path)
    return True
