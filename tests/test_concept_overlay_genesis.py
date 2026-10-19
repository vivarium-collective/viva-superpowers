"""Prove the Concept overlay + canonical verdict against the real genesis gate spine.

The origins-of-life-vent investigation consolidated ~49 studies onto a 6-gate
spine (A1/A2/B/C/D/E). This test pins derive_concepts + canonical_verdict to
that real spine shape. The gate structure below is the investigation's spine
metadata (not workspace run data), kept inline so the test is CI-stable and
does not vendor a real workspace file. A skip-if-present live smoke runs the
same assertion against the on-disk workspace when it is current.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from viva_superpowers.concept_overlay import derive_concepts
from viva_superpowers.verdict_vocab import canonical_verdict, CANONICAL

# The real origins-of-life-vent gate spine (origin/main), id -> member study slugs.
GENESIS_GATES = [
    {"id": "A1", "member_studies": ["og-vent-environment", "og-network-persistence"]},
    {"id": "A2", "member_studies": ["og-autocatalysis-a2"]},
    {"id": "B", "member_studies": ["og-network-rescue"]},
    {"id": "C", "member_studies": ["og-self-compartmentation"]},
    {"id": "D", "member_studies": ["og-reproduction", "og-evolvability"]},
    {"id": "E", "member_studies": ["og-energetics", "og-ecology", "og-independence"]},
]


def _stub_studies():
    studies = {}
    for g in GENESIS_GATES:
        for slug in g["member_studies"]:
            studies[slug] = {"name": slug}
    # the compartmentation study is the known already-consolidated (arms-bearing) one
    studies["og-self-compartmentation"]["arms"] = [{"source_study": "og-32"}]
    return studies


def test_derives_one_concept_per_genesis_gate():
    inv = {"name": "origins-of-life-vent", "title": "Origins of Life (vent)",
           "plan_gates": GENESIS_GATES}
    concepts = derive_concepts(inv, _stub_studies())

    assert [c["from_gate"] for c in concepts] == ["A1", "A2", "B", "C", "D", "E"]
    assert [c["id"] for c in concepts] == ["a1", "a2", "b", "c", "d", "e"]
    # every gate's members carried through, none dropped
    assert concepts[0]["member_studies"] == ["og-vent-environment", "og-network-persistence"]
    assert concepts[5]["member_studies"] == ["og-energetics", "og-ecology", "og-independence"]
    # the arms-bearing compartmentation gate reads as consolidated
    assert next(c for c in concepts if c["from_gate"] == "C")["org_state"] == "consolidated"


def test_canonical_verdict_runs_over_every_genesis_member():
    studies = _stub_studies()
    for slug, spec in studies.items():
        v = canonical_verdict(spec)
        assert v in CANONICAL, f"{slug} -> {v!r}"


def test_concept_store_roundtrip_on_genesis_gate(tmp_path):
    """Author a synthesis for gate C on the real genesis spine: it persists as a
    revision, overlays the derived overlay (keeping derived members), marks the
    concept authored, and leaves the other gates purely derived."""
    import yaml
    from viva_superpowers.concept_store import write_concept, load_concepts

    d = tmp_path / "investigations" / "origins-of-life-vent"
    d.mkdir(parents=True)
    (d / "investigation.yaml").write_text(yaml.safe_dump({
        "name": "origins-of-life-vent", "title": "OG", "plan_gates": GENESIS_GATES,
    }))

    changed = write_concept(
        d, "c",
        synthesis="Compartmentation qualified; og-32 bilayer PMF-resolved.",
        assessment={"verdict": "qualified", "basis": "og-32 bilayer"},
        by="Eran", note="authored after C consolidation",
    )
    assert changed is True

    spec = yaml.safe_load((d / "investigation.yaml").read_text())
    merged = {c["id"]: c for c in load_concepts(spec, _stub_studies())}
    c = merged["c"]
    assert c["synthesis"].startswith("Compartmentation qualified")
    assert c["assessment"]["verdict"] == "qualified"
    assert c["member_studies"] == ["og-self-compartmentation"]   # derived members kept
    assert c["derived"] is False
    stored = next(x for x in spec["concepts"] if x["id"] == "c")
    assert len(stored["revisions"]) == 1 and stored["revisions"][0]["note"].startswith("authored")
    assert merged["a1"]["derived"] is True                       # other gates stay derived


def test_live_genesis_workspace_when_current():
    """If a CURRENT genesis workspace is on disk (carries plan_gates), derive
    one Concept per gate from it. Skipped when the local checkout is stale or
    absent (it then lacks plan_gates)."""
    import yaml  # pyyaml ships with the workspace tooling

    inv_path = Path.home() / "code" / "viva-genesis" / "workspace" / \
        "investigations" / "origins-of-life-vent" / "investigation.yaml"
    if not inv_path.exists():
        pytest.skip("genesis workspace not on disk")
    spec = yaml.safe_load(inv_path.read_text())
    gates = spec.get("plan_gates") or []
    if not gates:
        pytest.skip("local genesis checkout is stale (no plan_gates)")

    concepts = derive_concepts(spec, {})
    assert len(concepts) == len(gates)
    assert all(c["derived"] is True for c in concepts)
