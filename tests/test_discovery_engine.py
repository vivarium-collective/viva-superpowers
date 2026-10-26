"""Tests for viva_superpowers.discovery_engine — the formal discovery crank.

The engine turns one cycle projection (run_cycle's output) + the investigation spec
into a prioritized FRONTIER of unresolved items, each with a recommended operation;
a single NEXT action; a CLOSURE check; and validity-INVARIANT checks. It is pure and
deterministic (same evidence -> same frontier), so turning the crank is reproducible.
"""
from __future__ import annotations

from viva_superpowers import discovery_engine as de


def _cycle(open_calls=None, edges=None, verdicts=None, behaviors=None):
    return {
        "knowledge": {"verdicts": verdicts or {}, "behaviors": behaviors or {}},
        "argument": {"claims": {}, "edges": edges or []},
        "narrative": {"units": []},
        "audit": [],
        "gates": [],
        "open_calls": open_calls or [],
    }


def test_frontier_prioritizes_criteria_over_gaps_over_divergence():
    cyc = _cycle(
        open_calls=[
            {"kind": "narrative_gap", "title": "gap A->B", "refs": ["claim:a", "claim:b"]},
            {"kind": "divergence", "title": "claim c diverges", "refs": ["claim:c"]},
        ],
        verdicts={"sref": {"verdict": "refuted"}, "sok": {"verdict": "supported"}},
    )
    inv = {"acceptance_criteria": [{"study": "sref", "behavior": "x"},
                                   {"study": "sok", "behavior": "y"}]}
    f = de.frontier(cyc, inv)
    kinds = [i["kind"] for i in f]
    # unaddressed criterion (sref refuted) ranks first; addressed (sok supported) absent
    assert kinds[0] == "unaddressed_criterion"
    assert f[0]["target"] == "sref"
    assert f[0]["op"] == "branch"
    # priority order: criterion > narrative_gap > divergence
    assert kinds.index("unaddressed_criterion") < kinds.index("narrative_gap") < kinds.index("divergence")
    # addressed criterion sok produced no item
    assert "sok" not in [i["target"] for i in f]


def test_criterion_met_when_named_behavior_passes_despite_refuted_verdict():
    # A null / adversarial-control study: refuting the null is the DESIGNED success,
    # and its acceptance behavior passed. Acceptance must track the behavior outcome,
    # not the verdict sign — so the criterion is MET and raises no frontier item.
    cyc = _cycle(verdicts={"nullctl": {"verdict": "refuted"}},
                 behaviors={"nullctl": {"rejects-generic": "PASS"}})
    inv = {"acceptance_criteria": [{"study": "nullctl", "behavior": "rejects-generic"}]}
    f = de.frontier(cyc, inv)
    assert "nullctl" not in [i["target"] for i in f if i["kind"] == "unaddressed_criterion"]
    assert de.closure(cyc, inv)["closed"] is True


def test_criterion_unmet_when_named_behavior_fails():
    # The named behavior failed → the criterion is unmet regardless of verdict.
    cyc = _cycle(verdicts={"s": {"verdict": "refuted"}},
                 behaviors={"s": {"b": "FAIL"}})
    inv = {"acceptance_criteria": [{"study": "s", "behavior": "b"}]}
    f = de.frontier(cyc, inv)
    assert "s" in [i["target"] for i in f if i["kind"] == "unaddressed_criterion"]


def test_criterion_falls_back_to_verdict_when_no_behavior_outcome():
    # Backward-compatible: with no behavior outcome recorded, a non-met verdict still flags.
    cyc = _cycle(verdicts={"s": {"verdict": "refuted"}})  # behaviors empty
    inv = {"acceptance_criteria": [{"study": "s", "behavior": "b"}]}
    assert "s" in [i["target"] for i in de.frontier(cyc, inv) if i["kind"] == "unaddressed_criterion"]


def test_frontier_flags_open_challenge_edges():
    cyc = _cycle(edges=[{"from": "claim:alt", "to": "claim:main", "type": "challenge", "relation": "refutes"},
                        {"from": "claim:p", "to": "claim:main", "type": "prerequisite", "relation": "builds-on"}])
    f = de.frontier(cyc, {})
    ch = [i for i in f if i["kind"] == "open_challenge"]
    assert len(ch) == 1 and ch[0]["target"] == "claim:main" and ch[0]["op"] == "synthesize"


def test_next_action_is_highest_priority_or_none():
    cyc = _cycle(open_calls=[{"kind": "divergence", "title": "d", "refs": ["claim:c"]}])
    assert de.next_action(cyc, {})["kind"] == "divergence"
    # a fully-resolved cycle yields no action
    assert de.next_action(_cycle(), {}) is None


def test_closure_requires_no_criteria_gaps_or_challenges():
    # open: an unaddressed criterion
    cyc = _cycle(verdicts={"sref": {"verdict": "refuted"}})
    inv = {"acceptance_criteria": [{"study": "sref", "behavior": "x"}]}
    c = de.closure(cyc, inv)
    assert c["closed"] is False and c["unaddressed_criteria"] == ["sref"]
    # closed: criterion met, no gaps/challenges
    cyc2 = _cycle(verdicts={"sok": {"verdict": "qualified"}})
    inv2 = {"acceptance_criteria": [{"study": "sok", "behavior": "x"}]}
    assert de.closure(cyc2, inv2)["closed"] is True


def test_invariants_flags_unprovenanced_and_divergence_hidden():
    # a supported claim with no evidence_refs violates the provenance invariant
    cyc = _cycle()
    cyc["argument"]["claims"] = {
        "claim:a": {"verdict": "supported", "evidence_refs": []},
        "claim:b": {"verdict": "supported", "evidence_refs": ["f1"]},
    }
    v = de.invariants(cyc)
    assert any(x["invariant"] == "provenance" and x["target"] == "claim:a" for x in v)
    assert not any(x["target"] == "claim:b" for x in v)
