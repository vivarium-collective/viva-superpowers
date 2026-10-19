"""The generalized fail-loud invariant gate (RFC-0004 §5; genesis's 3 audit guards).

check_concept_integrity audits an investigation's Concept layer against the hard
invariants the declarative operations must preserve: the investigation.yaml must
parse (guard 1), every Concept carries a stable id (identity), every member Study
resolves on disk (dangling-edge / non-destructive), and authored content is never
marked derived (projection correctness). Returns a list of violation strings
(empty = clean). Pure read; used as an op post-condition and by the report lint.
"""
from __future__ import annotations

from pathlib import Path

import yaml


def check_concept_integrity(inv_dir) -> list[str]:
    inv_path = Path(inv_dir) / "investigation.yaml"
    try:
        spec = yaml.safe_load(inv_path.read_text(encoding="utf-8"))
    except Exception as e:  # noqa: BLE001 — guard 1: a silently-skipped parse is worse than none
        return [f"investigation.yaml does not parse (hard fail): {e}"]
    if not isinstance(spec, dict):
        return ["investigation.yaml does not parse to a mapping (hard fail)"]

    studies_dir = Path(inv_dir).parent.parent / "studies"
    violations: list[str] = []
    for c in (spec.get("concepts") or []):
        if not isinstance(c, dict):
            violations.append("concept entry is not a mapping")
            continue
        cid = c.get("id")
        if not cid:
            violations.append("concept missing id (identity invariant)")
            continue
        for m in (c.get("member_studies") or []):
            if not (studies_dir / str(m) / "study.yaml").is_file():
                violations.append(
                    f"concept '{cid}' member study '{m}' not found (dangling edge / non-destructive)")
        if (c.get("synthesis") or c.get("assessment")) and c.get("derived") is True:
            violations.append(
                f"concept '{cid}' carries authored content but is marked derived:true (projection correctness)")
    return violations
