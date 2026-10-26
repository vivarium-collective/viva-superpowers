"""investigation_reconcile.py — detect + mechanically apply investigation drift
after a structural edit (studies removed / added / merged).

Deterministic / AI-free, mirroring the ``finding_observations.py`` split:
``detect_drift`` is pure (no writes); ``apply_mechanical`` drops STRUCTURED
references to removed studies via the comment-preserving ruamel round-trip and
leaves PROSE for the host agent to rewrite (guided by the ``/viva-investigation
reconcile`` skill section). Idempotent.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import yaml

from viva_superpowers.investigation_import import (
    investigations_dir,
    studies_dir,
    investigation_members,
)


@dataclass
class DriftItem:
    kind: str          # member_missing_on_disk | orphan_on_disk | prose_ref_to_removed | structured_ref_to_removed
    where: str         # dotted path / location
    detail: str
    suggested_action: str


def _inv_yaml(ws_root: Path, inv_slug: str) -> Path:
    return investigations_dir(ws_root) / inv_slug / "investigation.yaml"


def _declared_members(spec: dict, inv_yaml: Path) -> list[str]:
    """Union of every place a member is named: `members:` AND `studies:` (pre-canonical)
    AND the investigation_members() resolver (acceptance_criteria / at_a_glance)."""
    out: list[str] = []
    for key in ("members", "studies"):
        for x in (spec.get(key) or []):
            if isinstance(x, str):
                out.append(x)
            elif isinstance(x, dict) and x.get("study"):
                out.append(x["study"])
    try:
        out += investigation_members(inv_yaml)
    except Exception:  # noqa: BLE001 — resolver is best-effort; never fail detection
        pass
    seen, res = set(), []
    for s in out:
        if s not in seen:
            seen.add(s)
            res.append(s)
    return res


def _on_disk_members(ws_root: Path, inv_slug: str) -> set[str]:
    """Studies that physically exist for this investigation: nested
    <inv>/studies/<slug>/ or flat studies/<slug>/ whose study.yaml back-refs the inv."""
    found: set[str] = set()
    nested = investigations_dir(ws_root) / inv_slug / "studies"
    if nested.is_dir():
        for p in nested.iterdir():
            if (p / "study.yaml").is_file():
                found.add(p.name)
    flat = studies_dir(ws_root)
    if flat.is_dir():
        for p in flat.iterdir():
            sy = p / "study.yaml"
            if not sy.is_file():
                continue
            try:
                d = yaml.safe_load(sy.read_text()) or {}
            except Exception:  # noqa: BLE001
                d = {}
            if d.get("investigation") == inv_slug:
                found.add(p.name)
    return found


def _texts(val):
    if isinstance(val, str):
        yield val
    elif isinstance(val, list):
        for x in val:
            if isinstance(x, str):
                yield x


def _at_a_glance_studies(aag) -> list[str]:
    if isinstance(aag, dict):
        return [x if isinstance(x, str) else (x or {}).get("study")
                for x in (aag.get("studies") or [])]
    if isinstance(aag, list):
        return [(x or {}).get("study") if isinstance(x, dict) else x for x in aag]
    return []


def detect_drift(ws_root, inv_slug: str) -> list[DriftItem]:
    """Deterministically detect drift between an investigation's declared members
    and what exists on disk, plus narrative references to removed studies. Pure."""
    ws_root = Path(ws_root)
    inv_yaml = _inv_yaml(ws_root, inv_slug)
    spec = yaml.safe_load(inv_yaml.read_text()) or {}

    declared = _declared_members(spec, inv_yaml)
    on_disk = _on_disk_members(ws_root, inv_slug)
    removed = [s for s in declared if s not in on_disk]
    orphan = sorted(on_disk - set(declared))

    items: list[DriftItem] = []
    for s in removed:
        items.append(DriftItem("member_missing_on_disk", f"{inv_slug}.members",
                               f"declared member '{s}' has no study on disk (removed?)",
                               f"drop '{s}' from the member list, or restore the study"))
    for s in orphan:
        items.append(DriftItem("orphan_on_disk", f"studies/{s}",
                               f"study '{s}' exists on disk but is not a declared member",
                               f"add '{s}' to the member list, or remove the study"))

    sa = spec.get("scientific_argument") or {}
    ex = spec.get("executive") or {}
    prose_sources = {
        "executive.what_is_this": ex.get("what_is_this"),
        "executive.verdict": ex.get("verdict"),
        "biological_story": spec.get("biological_story"),
        "scientific_argument.evidence_for": sa.get("evidence_for"),
        "scientific_argument.evidence_against": sa.get("evidence_against"),
        "scientific_argument.key_figures": sa.get("key_figures"),
    }
    aag_studies = _at_a_glance_studies(spec.get("at_a_glance"))
    for s in removed:
        pat = re.compile(r"\b" + re.escape(s) + r"\b")
        for where, val in prose_sources.items():
            hit = any(pat.search(t) or (f"studies/{s}/" in t) for t in _texts(val))
            if hit:
                items.append(DriftItem("prose_ref_to_removed", where,
                                       f"text references removed study '{s}'",
                                       "confirm, then rewrite the prose to the surviving/new studies"))
        if s in aag_studies:
            items.append(DriftItem("structured_ref_to_removed", "at_a_glance",
                                   f"at_a_glance lists removed study '{s}'",
                                   f"drop '{s}' from at_a_glance"))
        for ac in (spec.get("acceptance_criteria") or []):
            if isinstance(ac, dict) and ac.get("study") == s:
                items.append(DriftItem("structured_ref_to_removed", "acceptance_criteria",
                                       f"acceptance_criteria references removed study '{s}'",
                                       "drop or repoint the criterion"))
    return items
