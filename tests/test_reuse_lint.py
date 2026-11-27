"""The engine-reuse check: flag raw engine imports that bypass an existing viva-* wrapper."""
from pathlib import Path
from viva_superpowers.package_audit import _reuse_findings, ENGINE_WRAPPERS


def _pkg(tmp_path: Path, name: str, body: str) -> list[Path]:
    d = tmp_path / name
    d.mkdir()
    (d / "__init__.py").write_text("")
    (d / "engine.py").write_text(body)
    return [d]


def test_flags_raw_engine_without_wrapper(tmp_path):
    dirs = _pkg(tmp_path, "mysim", "import cobra\n\ndef fba(): ...\n")
    found = _reuse_findings(dirs, dep_names={"numpy", "cobra"}, project_name="mysim")
    assert found == [("cobra", "viva-cobra", "engine.py")]


def test_from_import_is_detected(tmp_path):
    dirs = _pkg(tmp_path, "mysim", "from tellurium import loada\n")
    found = _reuse_findings(dirs, dep_names={"tellurium"}, project_name="mysim")
    assert ("tellurium", "viva-tellurium", "engine.py") in found


def test_not_flagged_when_wrapper_is_a_dependency(tmp_path):
    dirs = _pkg(tmp_path, "mysim", "import cobra\n")
    assert _reuse_findings(dirs, dep_names={"viva-cobra"}, project_name="mysim") == []
    # underscore form of the dist name also counts
    assert _reuse_findings(dirs, dep_names={"viva_cobra"}, project_name="mysim") == []


def test_wrapper_repo_is_exempt_from_its_own_engine(tmp_path):
    # viva-cobra itself binds cobra — that is correct, not a finding
    dirs = _pkg(tmp_path, "viva_cobra", "import cobra\n")
    assert _reuse_findings(dirs, dep_names={"cobra"}, project_name="viva-cobra") == []


def test_unwrapped_engine_is_ignored(tmp_path):
    dirs = _pkg(tmp_path, "mysim", "import numpy\nimport scipy\n")
    assert _reuse_findings(dirs, dep_names=set(), project_name="mysim") == []


def test_map_covers_the_core_engines():
    for raw in ("tellurium", "cobra", "fipy", "smoldyn", "pymunk", "cmaboss", "dolfinx"):
        assert raw in ENGINE_WRAPPERS and ENGINE_WRAPPERS[raw].startswith(("viva-", "vivarium-"))
