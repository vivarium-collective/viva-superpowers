"""Unified contract audit (RFC-0004 §4, PR-D).

One Findings surface spanning BOTH levels:
- the process-bigraph contract audit (``bigraph_schema.contract_audit`` — the
  SAME Findings the CI ``audit_contracts`` gate emits), and
- the study↔composite ``contract_face_diff`` (does the study's authored
  contract face agree with the composite's?).

So a study's audit and the process gate speak one vocabulary. Version-tolerant:
the process-contract layer is skipped when the typed audit (bigraph-schema
>=1.8) isn't importable, leaving only the pure face diff.
"""
from __future__ import annotations

from viva_superpowers.contract_spine import contract_face_diff


def _finding(severity, code, where, message, source):
    return {"severity": severity, "code": code, "where": where,
            "message": message, "source": source}


def audit_process_contract(contract, core=None) -> list[dict]:
    """Run the bigraph-schema contract audit (the process gate's audit) and return
    its Findings as dicts. Empty list when the typed audit isn't available."""
    try:
        from bigraph_schema import Core, BASE_TYPES, contract_audit as ca
    except Exception:  # noqa: BLE001 — pre-1.8 bigraph-schema: no typed audit
        return []
    try:
        if core is None:
            core = Core(BASE_TYPES)
        rep = ca.audit_contract(core, contract)
    except Exception:  # noqa: BLE001
        return []
    return [_finding(f.severity, f.code, f.where, f.message, "process-contract")
            for f in rep.findings]


def unified_contract_findings(process_contract, study_face=None, core=None) -> list[dict]:
    """The shared audit surface: process-contract audit Findings + the study's
    contract-face diff, as one list."""
    findings = audit_process_contract(process_contract, core=core)
    if study_face is not None:
        pface = getattr(process_contract, "face", None)
        if pface is None and isinstance(process_contract, dict):
            pface = process_contract.get("face")
        for m in contract_face_diff(study_face, pface or {}):
            findings.append(_finding("error", "contract-face", None, m, "study-contract"))
    return findings
