"""Tests for viva_superpowers.concept_store — the Concept-as-Store layer (RFC-0004 §3).

load_concepts merges the AUTHORED concept record (synthesis/assessment/revisions)
over the DERIVED overlay (member_studies/org_state from plan_gates), authored
winning, never clobbering. write_concept persists the authored half with a
comment-preserving ruamel round-trip + an append-only revision history.
"""
from __future__ import annotations

from pathlib import Path

from viva_superpowers.concept_store import load_concepts, write_concept


# ---- load_concepts: merge authored over derived -----------------------------

def _inv_with_gate_and_authored():
    return {
        "name": "og", "title": "OG",
        "plan_gates": [{"id": "C", "member_studies": ["og-self-compartmentation"]}],
        "concepts": [
            {"id": "c", "synthesis": "Compartmentation qualified under MD.",
             "assessment": {"verdict": "qualified", "basis": "og-32 bilayer"}},
            {"id": "cross-cutting-specificity", "synthesis": "vent specificity control",
             "member_studies": ["og-vent-specificity"]},
        ],
    }


def test_authored_overlays_derived_keeping_derived_members():
    studies = {"og-self-compartmentation": {"name": "og-self-compartmentation"}}
    merged = {c["id"]: c for c in load_concepts(_inv_with_gate_and_authored(), studies)}
    c = merged["c"]
    assert c["from_gate"] == "C"                                   # derived provenance kept
    assert c["member_studies"] == ["og-self-compartmentation"]      # derived members kept
    assert c["synthesis"] == "Compartmentation qualified under MD." # authored wins
    assert c["assessment"]["verdict"] == "qualified"
    assert c["derived"] is False                                   # authored -> not derived


def test_authored_only_concept_included():
    merged = {c["id"]: c for c in load_concepts(_inv_with_gate_and_authored(), {})}
    x = merged["cross-cutting-specificity"]
    assert x["member_studies"] == ["og-vent-specificity"]
    assert x["derived"] is False


def test_pure_derived_concept_marked_derived():
    inv = {"name": "og", "title": "OG",
           "plan_gates": [{"id": "A1", "member_studies": ["og-network"]}]}
    merged = {c["id"]: c for c in load_concepts(inv, {})}
    assert merged["a1"]["derived"] is True


def test_empty_authored_member_studies_does_not_clobber_derived():
    inv = _inv_with_gate_and_authored()
    inv["concepts"][0]["member_studies"] = []   # authored empty must not wipe derived
    merged = {c["id"]: c for c in load_concepts(inv, {"og-self-compartmentation": {}})}
    assert merged["c"]["member_studies"] == ["og-self-compartmentation"]


# ---- write_concept: persist authored half + revision history ----------------

def _write_inv(tmp_path, text):
    d = tmp_path / "investigations" / "og"
    d.mkdir(parents=True)
    (d / "investigation.yaml").write_text(text)
    return d


def test_write_creates_concept_and_revision(tmp_path):
    d = _write_inv(tmp_path, "name: og\ntitle: OG\n")
    write_concept(d, "heredity", synthesis="Inheritance holds.", by="Eran", note="first")
    import yaml
    spec = yaml.safe_load((d / "investigation.yaml").read_text())
    c = next(c for c in spec["concepts"] if c["id"] == "heredity")
    assert c["synthesis"] == "Inheritance holds."
    assert c["derived"] is False
    assert len(c["revisions"]) == 1
    assert c["revisions"][0]["synthesis"] == "Inheritance holds."
    assert c["revisions"][0]["note"] == "first"


def test_write_is_idempotent_on_identical_content(tmp_path):
    d = _write_inv(tmp_path, "name: og\ntitle: OG\n")
    write_concept(d, "heredity", synthesis="X", note="n")
    write_concept(d, "heredity", synthesis="X", note="n")   # identical -> no new revision
    import yaml
    c = next(c for c in yaml.safe_load((d / "investigation.yaml").read_text())["concepts"]
             if c["id"] == "heredity")
    assert len(c["revisions"]) == 1


def test_write_appends_revision_on_change(tmp_path):
    d = _write_inv(tmp_path, "name: og\ntitle: OG\n")
    write_concept(d, "heredity", synthesis="X")
    write_concept(d, "heredity", synthesis="Y", note="reopened")
    import yaml
    c = next(c for c in yaml.safe_load((d / "investigation.yaml").read_text())["concepts"]
             if c["id"] == "heredity")
    assert c["synthesis"] == "Y"
    assert len(c["revisions"]) == 2


def test_write_preserves_comments_and_siblings(tmp_path):
    d = _write_inv(tmp_path, (
        "name: og\ntitle: OG\n"
        "concepts:\n"
        "  - id: sibling   # keep me\n"
        "    synthesis: untouched\n"
    ))
    write_concept(d, "heredity", synthesis="new")
    raw = (d / "investigation.yaml").read_text()
    assert "# keep me" in raw                     # comment preserved
    import yaml
    spec = yaml.safe_load(raw)
    sib = next(c for c in spec["concepts"] if c["id"] == "sibling")
    assert sib["synthesis"] == "untouched"        # sibling unclobbered
