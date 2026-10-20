"""Tests for viva_superpowers.contract_spine.contract_face_diff (RFC-0004 §4, T4).

The structural/type/unit diff between a study's AUTHORED contract face and the
composite's actual contract face — the contract-level never-fabricate check.
Pure; no runtime dependency (the unit-typed ProcessContract wires T1–T3 are gated
on landing bigraph-schema 1.8.x, see the module docstring).
"""
from __future__ import annotations

from viva_superpowers.contract_spine import contract_face_diff


def test_matching_faces_no_violations():
    f = {"outputs": {"mass": {"_type": "float", "_units": "fg"}}}
    assert contract_face_diff(f, f) == []


def test_string_typed_match():
    f = {"inputs": {"ca": "float"}, "outputs": {"pth": "float"}}
    assert contract_face_diff(f, f) == []


def test_missing_port_flagged():
    study = {"outputs": {"mass": "float"}}
    comp = {"outputs": {}}
    v = contract_face_diff(study, comp)
    assert any("mass" in x for x in v)


def test_type_mismatch_flagged():
    study = {"outputs": {"mass": "float"}}
    comp = {"outputs": {"mass": "integer"}}
    v = contract_face_diff(study, comp)
    assert any("type" in x.lower() for x in v)


def test_unit_mismatch_flagged():
    study = {"outputs": {"mass": {"_type": "float", "_units": "fg"}}}
    comp = {"outputs": {"mass": {"_type": "float", "_units": "mol"}}}
    v = contract_face_diff(study, comp)
    assert any("unit" in x.lower() for x in v)


def test_does_not_flag_when_study_omits_units():
    # a study that doesn't declare units for a port is not a mismatch (it's silent,
    # not contradictory); only a declared disagreement is a violation.
    study = {"outputs": {"mass": "float"}}
    comp = {"outputs": {"mass": {"_type": "float", "_units": "fg"}}}
    assert contract_face_diff(study, comp) == []
