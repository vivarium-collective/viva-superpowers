"""Tests for viva_superpowers.concept_overlay.derive_concepts.

The Concept layer of the formalized investigation graph is DERIVED-FIRST: the
overlay is computed from plan_gates / plan_acts + membership, ephemeral, never
written to YAML. Each derived Concept carries derived=True and the on-disk shape
constrained by investigation.schema.json v3.
"""
from __future__ import annotations

from viva_superpowers.concept_overlay import derive_concepts


def test_derives_one_concept_per_gate():
    inv = {
        "name": "og", "title": "OG",
        "plan_gates": [
            {"id": "A1", "member_studies": ["og-network"]},
            {"id": "C", "member_studies": ["og-energetics", "og-carrier"]},
        ],
    }
    studies = {
        "og-network": {"name": "og-network"},
        "og-energetics": {"name": "og-energetics", "pipeline_gate": {"gate_status": "passed"}},
        "og-carrier": {"name": "og-carrier"},
    }
    concepts = derive_concepts(inv, studies)
    assert [c["from_gate"] for c in concepts] == ["A1", "C"]
    assert concepts[1]["member_studies"] == ["og-energetics", "og-carrier"]
    assert all(c["derived"] is True for c in concepts)
    # ids are valid concept slugs (lowercased gate ids)
    assert [c["id"] for c in concepts] == ["a1", "c"]


def test_no_gates_or_acts_yields_no_concepts():
    assert derive_concepts({"name": "x", "title": "X", "studies": ["a", "b"]}, {}) == []


def test_consolidated_org_state_when_member_has_arms():
    inv = {"name": "og", "title": "OG",
           "plan_gates": [{"id": "D", "member_studies": ["og-heredity"]}]}
    studies = {"og-heredity": {"name": "og-heredity",
                               "arms": [{"source_study": "og-inheritance"}]}}
    assert derive_concepts(inv, studies)[0]["org_state"] == "consolidated"


def test_exploring_org_state_without_arms():
    inv = {"name": "og", "title": "OG",
           "plan_gates": [{"id": "B", "member_studies": ["og-spatial"]}]}
    studies = {"og-spatial": {"name": "og-spatial"}}
    assert derive_concepts(inv, studies)[0]["org_state"] == "exploring"


def test_falls_back_to_plan_acts_when_no_gates():
    inv = {"name": "og", "title": "OG",
           "plan_acts": [{"id": "Act II", "member_studies": ["og-precursor"]}]}
    studies = {"og-precursor": {"name": "og-precursor"}}
    concepts = derive_concepts(inv, studies)
    assert len(concepts) == 1
    assert concepts[0]["from_act"] == "Act II"
    assert concepts[0]["member_studies"] == ["og-precursor"]
    assert concepts[0]["id"] == "act-ii"
    assert "from_gate" not in concepts[0]


def test_derived_concepts_validate_against_schema():
    """Derived concepts conform to the investigation.schema.json v3 concept shape."""
    import json
    from pathlib import Path
    import jsonschema

    inv = {"name": "og", "title": "OG",
           "plan_gates": [{"id": "C", "member_studies": ["og-energetics"]}]}
    concepts = derive_concepts(inv, {"og-energetics": {"name": "og-energetics"}})
    schema_path = (Path(__file__).resolve().parents[1]
                   / "tests" / "fixtures" / "investigation.schema.json")
    if not schema_path.exists():
        # schema lives in viva-template; validate shape structurally instead.
        c = concepts[0]
        assert isinstance(c["id"], str) and c["member_studies"] == ["og-energetics"]
        assert c["org_state"] in {"exploring", "consolidated", "reopened"}
        return
    validator = jsonschema.Draft202012Validator(json.loads(schema_path.read_text()))
    validator.validate({"name": "og", "title": "OG", "schema_version": 3, "concepts": concepts})
