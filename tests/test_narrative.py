"""Tests for viva_superpowers.narrative — Narrate + Audit (RFC-0005 §5, §7.3).

narrate(GE, question, audience) -> N: an ordered projection of the argument graph
(topological over prerequisite+support, ties by id), units = study-level claims,
arm claims excluded. A narrative is a *projection* of GE, never a requirement that
GE be linear.

audit(N, GE) -> gaps: an adjacent transition with no support/prerequisite path is
an unsupported transition; each gap names the missing evidence and a candidate
follow-up study (the investigate<->narrate loop-closer).
"""
from __future__ import annotations

from viva_superpowers.narrative import narrate, audit


def _claim(cid, verdict="supported", **extra):
    c = {"proposition": f"{cid} holds", "verdict": verdict, "evidence_refs": [], "derived": True}
    c.update(extra)
    return cid, c


def _graph(claims, edges):
    return {"claims": dict(claims), "edges": list(edges)}


def _e(a, b, t):
    return {"from": a, "to": b, "type": t}


# ---------------------------------------------------------------------------
# narrate — ordered projection
# ---------------------------------------------------------------------------

class TestNarrate:
    def test_prerequisite_orders_before(self):
        g = _graph([_claim("claim:a"), _claim("claim:b")],
                   [_e("claim:a", "claim:b", "prerequisite")])
        order = [u["claim_id"] for u in narrate(g)["units"]]
        assert order == ["claim:a", "claim:b"]

    def test_support_orders_before(self):
        g = _graph([_claim("claim:x"), _claim("claim:y")],
                   [_e("claim:y", "claim:x", "support")])  # y supports x -> y first
        order = [u["claim_id"] for u in narrate(g)["units"]]
        assert order == ["claim:y", "claim:x"]

    def test_deterministic_tie_break_by_id(self):
        g = _graph([_claim("claim:b"), _claim("claim:a"), _claim("claim:c")], [])
        order = [u["claim_id"] for u in narrate(g)["units"]]
        assert order == ["claim:a", "claim:b", "claim:c"]

    def test_arm_claims_are_not_narrative_units(self):
        g = _graph([_claim("claim:a"), _claim("claim:a:arm1", arm_of="claim:a")], [])
        ids = [u["claim_id"] for u in narrate(g)["units"]]
        assert ids == ["claim:a"]

    def test_units_preserve_evidence_refs(self):
        g = _graph([_claim("claim:a", evidence_refs=["run1", "f1"])], [])
        assert narrate(g)["units"][0]["evidence_refs"] == ["run1", "f1"]

    def test_open_questions_from_unassessed_and_inconclusive(self):
        g = _graph([_claim("claim:a", verdict="unassessed"),
                    _claim("claim:b", verdict="inconclusive"),
                    _claim("claim:c", verdict="supported")], [])
        oq = narrate(g)["open_questions"]
        assert any("claim:a" in q["claim_id"] for q in oq)
        assert any("claim:b" in q["claim_id"] for q in oq)
        assert all(q["claim_id"] != "claim:c" for q in oq)

    def test_limitations_from_rebuttals(self):
        g = _graph([_claim("claim:a", rebuttals=["only in a narrow corner"])], [])
        assert "only in a narrow corner" in narrate(g)["limitations"]

    def test_question_and_audience_carried(self):
        g = _graph([_claim("claim:a")], [])
        n = narrate(g, question="Why?", audience="reviewers")
        assert n["question"] == "Why?" and n["audience"] == "reviewers"


# ---------------------------------------------------------------------------
# audit — unsupported transitions become follow-up requests
# ---------------------------------------------------------------------------

class TestAudit:
    def test_supported_chain_has_no_gaps(self):
        g = _graph([_claim("claim:a"), _claim("claim:b")],
                   [_e("claim:a", "claim:b", "prerequisite")])
        assert audit(narrate(g), g) == []

    def test_transitive_support_path_has_no_gap(self):
        g = _graph([_claim("claim:a"), _claim("claim:b"), _claim("claim:c")],
                   [_e("claim:a", "claim:b", "support"), _e("claim:b", "claim:c", "support")])
        # ordered a,b,c; a->c reachable transitively; adjacent pairs both direct
        assert audit(narrate(g), g) == []

    def test_unsupported_transition_is_a_gap_with_followup(self):
        # two independent claims, no edge -> ordered by id -> adjacent unsupported
        g = _graph([_claim("claim:a"), _claim("claim:b")], [])
        gaps = audit(narrate(g), g)
        assert len(gaps) == 1
        gap = gaps[0]
        assert gap["from"] == "claim:a" and gap["to"] == "claim:b"
        assert "missing_evidence" in gap
        fu = gap["followup"]
        assert fu["id"] and fu["title"] and fu["motivation"]
        assert fu["parent_study"] == "b"  # derived from the target claim's slug

    def test_verdict_escalation_flagged(self):
        g = _graph([_claim("claim:a", verdict="inconclusive"),
                    _claim("claim:b", verdict="supported")], [])
        gap = audit(narrate(g), g)[0]
        assert gap["verdict_escalation"] is True

    def test_challenge_edge_does_not_count_as_support(self):
        # a challenge edge between adjacent claims is NOT a supporting link -> gap
        g = _graph([_claim("claim:a"), _claim("claim:b")],
                   [_e("claim:a", "claim:b", "challenge")])
        assert len(audit(narrate(g), g)) == 1
