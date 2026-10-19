"""Tests for the L4 verdict re-grade (viva_superpowers.study_audit)."""
import json

from viva_superpowers.card_grade import grade_card, verdict_json
from viva_superpowers.study_audit import audit_workspace

_STUDY = "name: s\n"


def _ws(tmp_path):
    (tmp_path / "workspace.yaml").write_text("name: t\n", encoding="utf-8")
    d = tmp_path / "studies" / "s"
    d.mkdir(parents=True)
    (d / "study.yaml").write_text(_STUDY, encoding="utf-8")
    return d


def _write_verdict(sdir, measured, stored_overall):
    """Real grade_card output (reference 10, 5% tol) serialized via verdict_json,
    with each axis carrying its recompute inputs; `overall` overridden."""
    criterion = {"type": "rel_tol", "reference": 10.0, "tol_rel": 0.05}
    ref = {"axes": {"x": {"label": "X", "group": "G", "criterion": criterion}}}
    v = verdict_json(grade_card({"x": measured}, ref))
    for grp in v["groups"].values():
        for ax in grp["axes"]:
            ax["criterion"] = criterion
            ax["measured"] = measured
    v["overall"] = stored_overall
    rc = sdir / "viz" / "report_card"
    rc.mkdir(parents=True)
    (rc / "c.verdict.json").write_text(json.dumps(v), encoding="utf-8")


def _regrade(tmp_path):
    report = audit_workspace(tmp_path)
    return [c for a in report.studies for c in a.checks if c.name == "verdict-regrade"]


def test_stale_verdict_json_fails_regrade(tmp_path):
    sdir = _ws(tmp_path)
    _write_verdict(sdir, 20.0, "within_tol")  # 20 vs 10 -> mismatch
    checks = _regrade(tmp_path)
    assert len(checks) == 1
    c = checks[0]
    assert (c.level, c.status, c.tier) == ("L4", "fail", "hard")


def test_matching_verdict_passes(tmp_path):
    sdir = _ws(tmp_path)
    _write_verdict(sdir, 20.0, "mismatch")
    checks = _regrade(tmp_path)
    assert [c.status for c in checks] == ["pass"]


def test_no_run_abstains(tmp_path):
    _ws(tmp_path)
    assert _regrade(tmp_path) == []
