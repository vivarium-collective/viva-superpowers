"""The contract spine (RFC-0004 §4): ground a study's acceptance tests in the
composite's process contracts.

This module holds the *pure*, runtime-independent wire — ``contract_face_diff``,
the structural/type/unit diff between a study's AUTHORED contract face and the
composite's actual contract face (the contract-level never-fabricate check).

The remaining wires generalize the study↔composite seam from an existence-check
to a type/unit/shape check, and are GATED on landing bigraph-schema 1.8.x (the
typed ``ProcessContract`` with port-type ``_units``) onto the pinned version
(today's venv is 1.4.5, face-only). When that lands:
  T1  ``available_observables`` returns each leaf's {type, units, bounds} (via core.access).
  T2  ``validate_readouts`` compares a readout's units/shape to the leaf type (core._compute_unit_scale).
  T3  ``test_contract`` bands carry + reconcile a unit before the margin.
These are deliberately not implemented here until the dependency is available, so
nothing claims a unit check it cannot yet perform.
"""
from __future__ import annotations


def _type_of(spec) -> str | None:
    if isinstance(spec, str):
        return spec
    if isinstance(spec, dict):
        return spec.get("_type") or spec.get("type")
    return None


def _units_of(spec):
    if isinstance(spec, dict):
        return spec.get("_units") or spec.get("units")
    return None


def contract_face_diff(study_face: dict, composite_face: dict) -> list[str]:
    """Diff a study's authored contract ``face`` against the composite's ``face``.

    A ``face`` is ``{inputs: {port: typespec}, outputs: {port: typespec}}`` where
    a typespec is a type string or a dict carrying ``_type``/``_units``. Flags:
    a port the study declares that the composite lacks; a declared type
    disagreement; a declared unit disagreement. A port the study leaves
    under-specified (no units) is silent, not a violation — only a declared
    disagreement is flagged (never fabricate a mismatch).
    """
    study_face = study_face or {}
    composite_face = composite_face or {}
    violations: list[str] = []
    for side in ("inputs", "outputs"):
        s_ports = study_face.get(side) or {}
        c_ports = composite_face.get(side) or {}
        for port, s_spec in s_ports.items():
            if port not in c_ports:
                violations.append(f"{side} port '{port}' declared by the study is not in the composite contract")
                continue
            c_spec = c_ports[port]
            s_type, c_type = _type_of(s_spec), _type_of(c_spec)
            if s_type is not None and c_type is not None and s_type != c_type:
                violations.append(f"{side} port '{port}' type mismatch: study={s_type!r} vs composite={c_type!r}")
            s_units, c_units = _units_of(s_spec), _units_of(c_spec)
            if s_units is not None and c_units is not None and s_units != c_units:
                violations.append(f"{side} port '{port}' units mismatch: study={s_units!r} vs composite={c_units!r}")
    return violations
