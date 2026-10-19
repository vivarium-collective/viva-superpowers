"""Tests for viva_superpowers.verdict_vocab.canonical_verdict.

Standardizes the several study verdict vocabularies onto ONE canonical vocab
(unassessed|supported|qualified|inconclusive|refuted), projected from the coded
study_verdict rollup and reconciled with the authored `verdict`. The canonical
value is written to the parallel computed_verdict slot (never over the authored
one); when coded and authored disagree, the divergence is surfaced, not hidden.
"""
from __future__ import annotations

import viva_superpowers.verdict_vocab as vv
from viva_superpowers.verdict_vocab import canonical_verdict, canonical_verdict_detail, project_coded


class TestProjection:
    def test_coded_rollup_maps_to_canonical(self):
        assert project_coded("passed") == "supported"
        assert project_coded("failed") == "refuted"
        assert project_coded("needs_calibration") == "qualified"
        assert project_coded("blocked") == "unassessed"
        assert project_coded("not_started") == "unassessed"

    def test_unknown_rollup_is_unassessed(self):
        assert project_coded("banana") == "unassessed"


class TestCanonicalVerdict:
    def test_unassessed_when_no_signal(self):
        assert canonical_verdict({"name": "x"}) == "unassessed"

    def test_authored_used_when_no_coded_evidence(self):
        d = canonical_verdict_detail({"name": "x", "verdict": "qualified"})
        assert d["verdict"] == "qualified"
        assert d["source"] == "authored"
        assert d["diverges"] is False

    def test_coded_wins_over_authored(self, monkeypatch):
        monkeypatch.setattr(vv, "roll_up_verdict", lambda spec: {"result": "passed"})
        d = canonical_verdict_detail({"name": "x", "verdict": "supported"})
        assert d["verdict"] == "supported"
        assert d["source"] == "coded"
        assert d["diverges"] is False

    def test_divergence_surfaced(self, monkeypatch):
        monkeypatch.setattr(vv, "roll_up_verdict", lambda spec: {"result": "failed"})
        d = canonical_verdict_detail({"name": "x", "verdict": "supported"})
        assert d["verdict"] == "refuted"   # coded wins
        assert d["diverges"] is True       # ... but the disagreement is flagged
        assert d["authored"] == "supported"
        assert d["coded"] == "refuted"

    def test_coded_needs_calibration_is_qualified(self, monkeypatch):
        monkeypatch.setattr(vv, "roll_up_verdict", lambda spec: {"result": "needs_calibration"})
        assert canonical_verdict({"name": "x"}) == "qualified"

    def test_blocked_falls_back_to_authored(self, monkeypatch):
        monkeypatch.setattr(vv, "roll_up_verdict", lambda spec: {"result": "blocked"})
        # no coded verdict yet -> use the authored one
        assert canonical_verdict({"name": "x", "verdict": "inconclusive"}) == "inconclusive"

    def test_never_raises_on_empty(self):
        assert canonical_verdict({}) == "unassessed"
