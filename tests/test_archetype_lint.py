"""Repo-archetype checks: declared kind + studies detection (purity + reuse-pressure
are exercised against real repos; the network reuse-pressure path degrades gracefully)."""
from viva_superpowers.package_audit import _declared_kind, _has_studies, VIVA_KINDS


def test_declared_kind_reads_tool_viva():
    assert _declared_kind({"tool": {"viva": {"kind": "simulator"}}}) == "simulator"
    assert _declared_kind({"tool": {"viva": {}}}) is None
    assert _declared_kind({"tool": {}}) is None
    assert _declared_kind({}) is None


def test_the_three_archetypes():
    assert set(VIVA_KINDS) == {"simulator", "workspace", "showcase"}


def test_has_studies_detects_study_yaml(tmp_path):
    assert _has_studies(tmp_path) is False
    d = tmp_path / "workspace" / "studies" / "s1"
    d.mkdir(parents=True)
    (d / "study.yaml").write_text("name: s1\n")
    assert _has_studies(tmp_path) is True


def test_has_studies_detects_investigation_dirs(tmp_path):
    (tmp_path / "investigations").mkdir()
    assert _has_studies(tmp_path) is True


def test_has_studies_false_for_pure_package(tmp_path):
    pkg = tmp_path / "mypkg"; pkg.mkdir()
    (pkg / "__init__.py").write_text("")
    (pkg / "engine.py").write_text("x = 1\n")
    assert _has_studies(tmp_path) is False
