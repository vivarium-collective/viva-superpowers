"""Study-level contract lint (RFC-0004 §4, PR-B/D).

Diffs a study's AUTHORED ``contract.face`` against the composite's resolved
contract face, surfacing type/unit/port disagreements as lint findings. Pure —
the caller supplies the composite face (resolved via bigraph-schema
``resolve_contract`` at integration time). Only a DECLARED disagreement is
flagged; a study with no ``contract:`` block yields no findings.
"""
from __future__ import annotations

from viva_superpowers.contract_spine import contract_face_diff


def lint_study_contract(study_spec: dict, composite_face: dict) -> list[dict]:
    """Return contract-face lint findings for one study.

    :param study_spec: the study.yaml dict (reads ``contract.face``).
    :param composite_face: the composite's resolved contract face
        (``{inputs:{port:type}, outputs:{port:type}}``).
    :returns: ``[{severity, check, message}, ...]`` (empty when the study
        declares no contract face or the faces agree).
    """
    contract = (study_spec or {}).get("contract") or {}
    study_face = contract.get("face")
    if not isinstance(study_face, dict):
        return []
    return [
        {"severity": "error", "check": "contract-face", "message": m}
        for m in contract_face_diff(study_face, composite_face or {})
    ]
