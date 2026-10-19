"""Derive the Concept overlay of the formalized investigation graph.

A Concept is a persistent, revisable synthesis-grouping over member Studies —
the layer between Investigation and Study. Per the design, the overlay is
DERIVED-FIRST: computed from ``plan_gates`` / ``plan_acts`` + membership,
ephemeral (never written to YAML), and only hand-authored where derivation
can't reach. Every derived Concept carries ``derived: True`` and conforms to
the ``concepts[]`` shape in investigation.schema.json (v3).

Pure functions only — no I/O, no network, no mutation of the inputs.
"""
from __future__ import annotations

import re

_ORG_EXPLORING = "exploring"
_ORG_CONSOLIDATED = "consolidated"


def _slug(raw: str) -> str:
    """Lowercase + hyphenate an arbitrary gate/act id into a concept-slug.

    Matches the investigation.schema concept ``id`` pattern ^[a-z0-9][a-z0-9_-]*$.
    """
    s = re.sub(r"[^a-z0-9_-]+", "-", str(raw).strip().lower()).strip("-_")
    return s or "concept"


def _org_state(member_slugs: list[str], studies_by_slug: dict) -> str:
    """A gate/act whose membership includes an arms-bearing (already-consolidated)
    study reads as ``consolidated``; otherwise it is still ``exploring``.

    (Refined in later stages; this is the cheap derived signal.)
    """
    for slug in member_slugs:
        study = studies_by_slug.get(slug) or {}
        if study.get("arms"):
            return _ORG_CONSOLIDATED
    return _ORG_EXPLORING


def _concept_from_group(group: dict, *, source_key: str, studies_by_slug: dict) -> dict:
    """Build one derived Concept from a plan_gates gate or a plan_acts act.

    ``source_key`` is ``from_gate`` or ``from_act`` — the provenance of the
    derived grouping.
    """
    raw_id = group.get("id") or group.get("name") or group.get("title") or ""
    members = list(group.get("member_studies") or [])
    concept = {
        "id": _slug(raw_id),
        source_key: raw_id,
        "member_studies": members,
        "org_state": _org_state(members, studies_by_slug),
        "derived": True,
    }
    title = group.get("title") or group.get("name")
    if title and title != raw_id:
        concept["title"] = title
    return concept


def derive_concepts(inv_spec: dict, studies_by_slug: dict) -> list[dict]:
    """Derive the ephemeral Concept overlay for one investigation.

    Preference order:
      1. ``plan_gates`` — one Concept per gate (``from_gate``);
      2. else ``plan_acts`` — one Concept per act (``from_act``);
      3. else ``[]`` (a legacy investigation with no spine yields no Concepts).

    :param inv_spec: the investigation.yaml dict.
    :param studies_by_slug: {study_slug: study_spec_dict} for the investigation's members.
    :returns: a list of derived Concept dicts (``derived: True``), in spine order.
    """
    gates = inv_spec.get("plan_gates") or []
    if gates:
        return [
            _concept_from_group(g, source_key="from_gate", studies_by_slug=studies_by_slug)
            for g in gates
            if isinstance(g, dict)
        ]

    acts = inv_spec.get("plan_acts") or []
    if acts:
        return [
            _concept_from_group(a, source_key="from_act", studies_by_slug=studies_by_slug)
            for a in acts
            if isinstance(a, dict)
        ]

    return []
