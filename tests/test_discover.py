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

    assert report["enriched"] == {"bare": ["up"]}  # only the bare one touched
    assert report["needs_relate"] == {}             # no parent_studies-only edges here
    bare = load_yaml(tmp_path / "studies" / "bare" / "study.yaml")
    assert bare["pipeline_gate"]["prerequisites"][0]["relation"] == "builds-on"
    authored = load_yaml(tmp_path / "studies" / "authored" / "study.yaml")
    assert authored["pipeline_gate"]["prerequisites"][0]["relation"] == "refutes"  # left intact


def test_relate_enriches_bare_parent_studies_dict_in_place():
    # A dependency declared only in parent_studies (the legacy backbone) is enriched
    # where it lives — no duplicate canonical pipeline_gate entry is fabricated.
    spec = {"name": "b", "parent_studies": [{"study": "a"}]}
    out = discover.relate(spec, "a", "builds-on")
    assert out["parent_studies"][0] == {"study": "a", "relation": "builds-on"}
    assert "pipeline_gate" not in out
    assert "relation" not in spec["parent_studies"][0]  # non-mutating


def test_relate_enriches_parent_studies_string_in_place():
    # A bare string parent_studies entry is promoted to a {study, relation} edge.
    spec = {"name": "b", "parent_studies": ["a"]}
    out = discover.relate(spec, "a", "tests")
    assert out["parent_studies"][0] == {"study": "a", "relation": "tests"}
    assert "pipeline_gate" not in out
    assert spec["parent_studies"][0] == "a"  # non-mutating


def test_relate_prefers_pipeline_gate_over_parent_studies():
    # When the edge is declared in both fields, the canonical pipeline_gate entry
    # carries the relation; the legacy parent_studies entry is left alone.
    spec = {"name": "b",
            "pipeline_gate": {"prerequisites": [{"study": "a", "condition": "x"}]},
            "parent_studies": [{"study": "a"}]}
    out = discover.relate(spec, "a", "builds-on")
    assert out["pipeline_gate"]["prerequisites"][0]["relation"] == "builds-on"
    assert "relation" not in out["parent_studies"][0]


def test_connect_auto_enriches_pipeline_gate_and_surfaces_parent_studies(tmp_path):
    # connect auto-enriches the canonical field but NEVER blanket-asserts a relation
    # on the ambiguous legacy backbone — it surfaces those for an explicit `relate`.
    (tmp_path / "workspace.yaml").write_text("name: t\n", encoding="utf-8")
    inv = tmp_path / "investigations" / "og"
    inv.mkdir(parents=True)
    save_yaml_atomic(inv / "investigation.yaml", {"studies": ["gated", "legacy"]})
    g = tmp_path / "studies" / "gated"
    g.mkdir(parents=True)
    save_yaml_atomic(g / "study.yaml", {"name": "gated", "pipeline_gate": {
        "prerequisites": [{"study": "up", "condition": "tests-passed"}]}})
    l = tmp_path / "studies" / "legacy"
    l.mkdir(parents=True)
    save_yaml_atomic(l / "study.yaml", {"name": "legacy", "parent_studies": ["up"]})

    report = discover.connect_investigation(tmp_path, "og", "builds-on")

    assert report["enriched"] == {"gated": ["up"]}
    assert report["needs_relate"] == {"legacy": ["up"]}
    assert load_yaml(g / "study.yaml")["pipeline_gate"]["prerequisites"][0]["relation"] == "builds-on"
    assert load_yaml(l / "study.yaml")["parent_studies"] == ["up"]  # untouched


def test_connect_preserves_comments_and_minimizes_churn(tmp_path):
    # The write path is comment-preserving (ruamel round-trip), not a full safe_dump
    # reflow that drops load-bearing annotations.
    (tmp_path / "workspace.yaml").write_text("name: t\n", encoding="utf-8")
    inv = tmp_path / "investigations" / "og"
    inv.mkdir(parents=True)
    save_yaml_atomic(inv / "investigation.yaml", {"studies": ["s"]})
    sdir = tmp_path / "studies" / "s"
    sdir.mkdir(parents=True)
    raw = (
        "name: s  # study name\n"
        "pipeline_gate:\n"
        "  prerequisites:\n"
        "    - study: up  # Canonical DAG edge\n"
        "      condition: tests-passed\n"
    )
    (sdir / "study.yaml").write_text(raw, encoding="utf-8")

    discover.connect_investigation(tmp_path, "og", "builds-on")

    out = (sdir / "study.yaml").read_text(encoding="utf-8")
    assert "# Canonical DAG edge" in out  # load-bearing comment survived
    assert "# study name" in out
    assert "relation: builds-on" in out


def test_resolve_accepts_validation_finding(tmp_path):
    # a validation_finding is a resolvable frontier item — the `resolve` verb must
    # accept its kind (RFC-0007).
    assert "validation_finding" in discover.RESOLUTION_KINDS
    spec = discover.add_resolution({}, "validation_finding", "claim:x", "fixed it")
    assert spec["resolutions"][0]["kind"] == "validation_finding"


def _sugg_cycle(audit=None, verdicts=None):
    return {"audit": audit or [], "knowledge": {"verdicts": verdicts or {}},
            "argument": {"claims": {}}}


def test_suggest_from_authored_followup_proposal():
    studies = {"a": {"name": "a", "followup_proposals": [
        {"id": "fu1", "title": "Extend A to higher salinity", "motivation": "why"}]}}
    sugg = discover.suggest_studies(_sugg_cycle(), {"studies": ["a"]}, studies)
    s = next(s for s in sugg if s["id"] == "fu1")
    assert s["status"] == "ready" and s["parent_study"] == "a" and s["source"] == "followup_proposal"


def test_suggest_from_narrative_gap_followup():
    cyc = _sugg_cycle(audit=[{"from": "claim:a", "to": "claim:b",
                              "followup": {"id": "disc-b", "title": "Discriminate b",
                                           "motivation": "m", "parent_study": "b"}}])
    sugg = discover.suggest_studies(cyc, {"studies": ["a", "b"]}, {})
    assert any(s["id"] == "disc-b" and s["source"] == "narrative_gap" and s["status"] == "ready"
               for s in sugg)


def test_suggest_gated_on_an_expert_decision():
    inv = {"studies": ["og-ecology"], "executive": {"decisions_needed": [
        {"question": "Agent motion model (og-ecology follow-up): which model?", "context": "c"}]}}
    sugg = discover.suggest_studies(_sugg_cycle(), inv, {"og-ecology": {"name": "og-ecology"}})
    gated = [s for s in sugg if s["source"] == "expert_decision"]
    assert gated and gated[0]["parent_study"] == "og-ecology"
    assert gated[0]["status"] == "awaiting_expert" and gated[0]["awaiting_expert"]


def test_suggest_ignores_a_project_scope_decision():
    inv = {"studies": ["a"], "executive": {"decisions_needed": [
        {"question": "Publication scope: close now or extend?", "context": ""},
        # a project-scope decision that merely MENTIONS a study mid-sentence (after the
        # colon) is not a study suggestion — only a subject-position parenthetical counts.
        {"question": "Scope: close the arc (a -> b) or extend?", "context": ""}]}}
    sugg = discover.suggest_studies(_sugg_cycle(), inv, {"a": {}})
    assert not [s for s in sugg if s["source"] == "expert_decision"]


def test_run_cycle_includes_suggestions():
    inv = {"studies": ["a"], "executive": {"decisions_needed": [
        {"question": "Prior (a): supply it", "context": ""}]}}
    bundle = discover.run_cycle(inv, {"a": {"name": "a"}})
    assert "suggestions" in bundle
    assert any(s["source"] == "expert_decision" for s in bundle["suggestions"])


def test_snapshot_validations_persists_the_accepted_state(tmp_path):
    (tmp_path / "workspace.yaml").write_text("name: t\n", encoding="utf-8")
    inv = tmp_path / "investigations" / "og"
    inv.mkdir(parents=True)
    save_yaml_atomic(inv / "investigation.yaml", {"studies": ["a"]})
    sdir = tmp_path / "studies" / "a"
    sdir.mkdir(parents=True)
    save_yaml_atomic(sdir / "study.yaml", {"name": "a", "claim": "a", "verdict": "supported"})

    snap = discover.snapshot_validations(tmp_path, "og")
    assert snap  # the provenance record (assessed claim, no evidence) was snapshotted
    assert load_yaml(inv / "investigation.yaml")["validation_snapshot"] == snap


def test_run_cycle_includes_validator_records(tmp_path):
    # RFC-0007: run_cycle runs the registered validators and returns their records.
    inv = {"studies": ["a"]}
    # an assessed claim with NO evidence (no runs/findings/tests) -> provenance fires.
    studies = {"a": {"name": "a", "claim": "a holds", "verdict": "supported"}}
    bundle = discover.run_cycle(inv, studies)
    assert "validations" in bundle
    ids = {r["provenance"]["validator_id"] for r in bundle["validations"]}
    assert "logical.claim.provenance" in ids
    assert "narrative.narrative.coherence" in ids


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


def test_add_resolution_appends_a_record():
    from viva_superpowers.discover import add_resolution
    out = add_resolution({"name": "inv"}, "open_challenge", "claim:x",
                         "adjudicated: concordant", by="studyA#finding1")
    rec = out["resolutions"][-1]
    assert rec["kind"] == "open_challenge" and rec["target"] == "claim:x"
    assert rec["rationale"] == "adjudicated: concordant" and rec["by"] == "studyA#finding1"


def test_add_resolution_is_idempotent_on_kind_target():
    from viva_superpowers.discover import add_resolution
    spec = add_resolution({"name": "i"}, "open_challenge", "claim:x", "r1")
    spec = add_resolution(spec, "open_challenge", "claim:x", "r2")  # same key -> update, no duplicate
    matches = [r for r in spec["resolutions"] if r["kind"] == "open_challenge" and r["target"] == "claim:x"]
    assert len(matches) == 1 and matches[0]["rationale"] == "r2"


def test_add_resolution_rejects_unknown_kind():
    import pytest
    from viva_superpowers.discover import add_resolution
    with pytest.raises(ValueError):
        add_resolution({"name": "i"}, "not-a-kind", "claim:x", "r")
