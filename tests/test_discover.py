"""Tests for viva_superpowers.discover — the wired discovery-cycle driver.

The RFC-0005/0006 ops (knowledge / argument / narrate / audit / synthesize) are
pure derive-first projections with no caller and no persistence. This module is
the write/wire layer:

- ``run_cycle`` chains all six into one projection (one invocation = one cycle);
- ``set_verdict`` is the authored canonical-verdict write op the derive-on-read
  layer lacked (why an investigation's study verdicts read empty);
- ``persist_cycle`` writes a regenerable ``knowledge_cycle`` cache into
  investigation.yaml WITHOUT polluting the sparse authored blocks (derive-first
  stays intact: the authored half is only ever human overrides);
- ``load_cycle_inputs`` reads an investigation + its member studies from disk.
"""
from __future__ import annotations

import pytest

from viva_superpowers import discover
from viva_superpowers.study_io import load_yaml, save_yaml_atomic


def _study(slug, result, **extra):
    spec = {
        "name": slug,
        "behavior_tests": [{"name": "t1"}],
        "runs": [{"name": "r1", "status": "completed", "outcomes": {"t1": {"result": result}}}],
    }
    spec.update(extra)
    return spec


# ---------------------------------------------------------------------------
# run_cycle — the one-invocation projection
# ---------------------------------------------------------------------------

def test_run_cycle_projects_verdicts_claims_narrative_gates():
    studies = {"a": _study("a", "PASS", claim="a holds"),
               "b": _study("b", "FAIL", claim="b fails")}
    inv = {"question": "Q?", "studies": ["a", "b"],
           "plan_gates": [{"id": "G1", "member_studies": ["a", "b"]}]}

    out = discover.run_cycle(inv, studies)

    # canonical verdicts: passing -> supported, failing -> refuted
    assert out["knowledge"]["verdicts"]["a"]["verdict"] == "supported"
    assert out["knowledge"]["verdicts"]["b"]["verdict"] == "refuted"
    # a first-class claim per study
    assert out["argument"]["claims"]["claim:a"]["verdict"] == "supported"
    # narrative units cover both study-level claims
    assert {u["claim_id"] for u in out["narrative"]["units"]} == {"claim:a", "claim:b"}
    # gate rolls up the mixed membership to qualified
    assert out["gates"][0]["verdict"] == "qualified"
    # audit + open_calls are lists (no authored decisions here -> audit/calls derive only)
    assert isinstance(out["audit"], list)
    assert isinstance(out["open_calls"], list)


def test_run_cycle_honors_authored_verdict_block():
    # authored knowledge.verdicts wins over the derived refuted
    studies = {"b": _study("b", "FAIL", claim="b fails")}
    inv = {"studies": ["b"],
           "knowledge": {"verdicts": {"b": {"verdict": "qualified"}}}}
    out = discover.run_cycle(inv, studies)
    assert out["knowledge"]["verdicts"]["b"]["verdict"] == "qualified"


# ---------------------------------------------------------------------------
# set_verdict — the authored write op
# ---------------------------------------------------------------------------

def test_set_verdict_writes_canonical_and_rejects_bad(tmp_path):
    sp = tmp_path / "study.yaml"
    save_yaml_atomic(sp, {"name": "a", "claim": "a holds"})

    rec = discover.set_verdict(sp, "qualified", rationale="scoped to vent regime")
    assert rec["verdict"] == "qualified"
    assert rec["verdict_source"] == "authored"
    on_disk = load_yaml(sp)
    assert on_disk["verdict"] == "qualified"
    assert on_disk["verdict_rationale"] == "scoped to vent regime"

    with pytest.raises(ValueError):
        discover.set_verdict(sp, "mostly-true")


# ---------------------------------------------------------------------------
# persist_cycle — regenerable cache, authored blocks untouched
# ---------------------------------------------------------------------------

def test_persist_cycle_writes_cache_without_polluting_authored(tmp_path):
    inv_path = tmp_path / "investigation.yaml"
    inv = {"question": "Q?", "studies": ["a"]}
    save_yaml_atomic(inv_path, inv)

    out = discover.run_cycle(inv, {"a": _study("a", "PASS", claim="a holds")})
    discover.persist_cycle(inv_path, inv, out)

    on_disk = load_yaml(inv_path)
    assert on_disk["knowledge_cycle"]["verdicts"]["a"]["verdict"] == "supported"
    assert on_disk["knowledge_cycle"]["narrative"]["units"]
    # derive-first stays sparse: the authored blocks are NOT written by a cycle
    assert "knowledge" not in on_disk
    assert "argument" not in on_disk


# ---------------------------------------------------------------------------
# load_cycle_inputs — read inv + member studies from disk
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# relate / connect — author the epistemic edges that connect the argument graph
# ---------------------------------------------------------------------------

def test_relate_sets_facet_on_existing_prereq_keeping_condition():
    spec = {"name": "b", "pipeline_gate": {"prerequisites": [
        {"study": "a", "condition": "tests-passed"}]}}
    out = discover.relate(spec, "a", "builds-on")
    entry = out["pipeline_gate"]["prerequisites"][0]
    assert entry["relation"] == "builds-on"
    assert entry["condition"] == "tests-passed"  # organizational facet kept
    # non-mutating
    assert "relation" not in spec["pipeline_gate"]["prerequisites"][0]


def test_relate_appends_epistemic_only_when_absent():
    spec = {"name": "b"}
    out = discover.relate(spec, "a", "tests")
    assert out["pipeline_gate"]["prerequisites"] == [{"study": "a", "relation": "tests"}]


def test_relate_rejects_bad_relation():
    with pytest.raises(ValueError):
        discover.relate({"name": "b"}, "a", "depends-on")


def test_connect_enriches_only_bare_prereqs(tmp_path):
    (tmp_path / "workspace.yaml").write_text("name: t\n", encoding="utf-8")
    inv_dir = tmp_path / "investigations" / "og"
    inv_dir.mkdir(parents=True)
    save_yaml_atomic(inv_dir / "investigation.yaml", {"studies": ["bare", "authored"]})
    for slug, rel in (("bare", None), ("authored", "refutes")):
        sdir = tmp_path / "studies" / slug
        sdir.mkdir(parents=True)
        prereq = {"study": "up", "condition": "tests-passed"}
        if rel:
            prereq["relation"] = rel
        save_yaml_atomic(sdir / "study.yaml",
                         {"name": slug, "pipeline_gate": {"prerequisites": [prereq]}})

    report = discover.connect_investigation(tmp_path, "og", "builds-on")

    assert report == {"bare": ["up"]}  # only the bare one touched
    bare = load_yaml(tmp_path / "studies" / "bare" / "study.yaml")
    assert bare["pipeline_gate"]["prerequisites"][0]["relation"] == "builds-on"
    authored = load_yaml(tmp_path / "studies" / "authored" / "study.yaml")
    assert authored["pipeline_gate"]["prerequisites"][0]["relation"] == "refutes"  # left intact


def test_load_cycle_inputs_reads_inv_and_studies(tmp_path):
    (tmp_path / "workspace.yaml").write_text("name: t\n", encoding="utf-8")
    inv_dir = tmp_path / "investigations" / "og"
    inv_dir.mkdir(parents=True)
    save_yaml_atomic(inv_dir / "investigation.yaml", {"question": "Q?", "studies": ["a"]})
    sdir = tmp_path / "studies" / "a"
    sdir.mkdir(parents=True)
    save_yaml_atomic(sdir / "study.yaml", _study("a", "PASS", claim="a holds"))

    inv_path, inv_spec, studies = discover.load_cycle_inputs(tmp_path, "og")
    assert inv_path == inv_dir / "investigation.yaml"
    assert inv_spec["question"] == "Q?"
    assert studies["a"]["claim"] == "a holds"
