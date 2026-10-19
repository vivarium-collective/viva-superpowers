import pytest

pytest.importorskip("bigraph_schema.contract_audit")  # typed audit needs bigraph-schema >=1.8

from bigraph_schema.contract import ProcessContract
from viva_superpowers.unified_contract_audit import unified_contract_findings, audit_process_contract


def _contract(units="fg"):
    return ProcessContract(face={"inputs": {}, "outputs": {"mass": {"_type": "float", "_units": units}}})


def test_process_audit_emits_gate_findings():
    # a bad-units contract yields the SAME bad_units Finding the CI gate emits
    f = audit_process_contract(_contract("not_a_unit"))
    assert any(x["code"] == "bad_units" and x["source"] == "process-contract" for x in f)


def test_clean_contract_has_no_bad_units():
    assert not any(x["code"] == "bad_units" for x in audit_process_contract(_contract("fg")))


def test_unified_adds_study_face_diff():
    f = unified_contract_findings(_contract("fg"),
                                  study_face={"outputs": {"mass": {"_type": "float", "_units": "mol"}}})
    assert any(x["source"] == "study-contract" and "unit" in x["message"].lower() for x in f)


def test_unified_is_one_list_both_sources():
    # a bad-units process contract AND a face mismatch → both sources in one list
    f = unified_contract_findings(_contract("not_a_unit"),
                                  study_face={"outputs": {"mass": {"_type": "float", "_units": "mol"}}})
    sources = {x["source"] for x in f}
    assert "process-contract" in sources and "study-contract" in sources
