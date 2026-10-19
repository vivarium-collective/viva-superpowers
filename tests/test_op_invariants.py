"""Tests for viva_superpowers.op_invariants — the generalized fail-loud gate
(RFC-0004 §5 invariants + genesis's 3 audit guards) and the three-graph
classifier (RFC-0004 §2).
"""
from __future__ import annotations

from pathlib import Path

from viva_superpowers.op_invariants import check_concept_integrity
from viva_superpowers.three_graphs import classify_edges


def _ws(tmp_path, inv_text, studies=("og-x", "og-y")):
    ws = tmp_path / "ws"
    inv = ws / "investigations" / "og"
    inv.mkdir(parents=True)
    (inv / "investigation.yaml").write_text(inv_text)
    for s in studies:
        d = ws / "studies" / s
        d.mkdir(parents=True)
        (d / "study.yaml").write_text(f"name: {s}\n")
    return inv


class TestConceptIntegrity:
    def test_clean_concept_passes(self, tmp_path):
        inv = _ws(tmp_path, "name: og\ntitle: OG\nconcepts:\n  - id: grp\n    member_studies: [og-x, og-y]\n    synthesis: s\n    derived: false\n")
        assert check_concept_integrity(inv) == []

    def test_unparseable_yaml_hard_fails(self, tmp_path):
        inv = _ws(tmp_path, "name: og\nrole: a: b: c\n")  # invalid mapping
        viol = check_concept_integrity(inv)
        assert viol and "parse" in viol[0].lower()

    def test_dangling_member_flagged(self, tmp_path):
        inv = _ws(tmp_path, "name: og\ntitle: OG\nconcepts:\n  - id: grp\n    member_studies: [og-x, ghost]\n")
        viol = check_concept_integrity(inv)
        assert any("ghost" in v for v in viol)

    def test_missing_id_flagged(self, tmp_path):
        inv = _ws(tmp_path, "name: og\ntitle: OG\nconcepts:\n  - member_studies: [og-x]\n")
        viol = check_concept_integrity(inv)
        assert any("id" in v for v in viol)

    def test_authored_but_derived_flagged(self, tmp_path):
        inv = _ws(tmp_path, "name: og\ntitle: OG\nconcepts:\n  - id: grp\n    synthesis: authored\n    derived: true\n")
        viol = check_concept_integrity(inv)
        assert any("projection" in v.lower() for v in viol)


class TestThreeGraphs:
    def test_org_edges_from_membership(self):
        inv = {"name": "og", "concepts": [{"id": "grp", "member_studies": ["og-x", "og-y"]}]}
        g = classify_edges(inv, {})
        assert {"from": "og-x", "to": "grp", "kind": "member_of"} in g["E_org"]
        assert {"from": "og-y", "to": "grp", "kind": "member_of"} in g["E_org"]

    def test_sci_edges_from_parent_studies(self):
        studies = {
            "og-y": {"name": "og-y", "parent_studies": [{"study": "og-x", "relation": "builds_on"}]},
            "og-x": {"name": "og-x"},
        }
        g = classify_edges({"name": "og"}, studies)
        assert {"from": "og-x", "to": "og-y", "kind": "builds_on"} in g["E_sci"]

    def test_families_are_disjoint_keys(self):
        g = classify_edges({"name": "og"}, {})
        assert set(g.keys()) == {"E_sci", "E_evid", "E_org", "E_prov"}
