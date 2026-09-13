"""Tests for viva_superpowers.core_compose.register_package_processes.

Covers the historical package-recursion behavior and the additive single-leaf-
module scoping (dotted name -> non-package module, or a module object), which
must register ONLY the classes defined in that exact module and never pull in
sibling modules.
"""

import sys
import textwrap
import importlib

import pytest

from viva_superpowers.core_compose import register_package_processes


class _FakeCore:
    """Minimal stand-in for a process-bigraph core: records register_link calls."""

    def __init__(self):
        self.registered: dict = {}

    def register_link(self, name, obj):
        self.registered[name] = obj


@pytest.fixture
def pkg_on_path(tmp_path, monkeypatch):
    """Build a throwaway package on sys.path:

        regpkg/
            __init__.py
            processes.py        # defines ProcA (Process), StepB (Step); imports SpeciesPlot
            visualizations.py   # defines SpeciesPlot (Step), Helper (plain class)
    """
    root = tmp_path / "regpkg"
    root.mkdir()
    (root / "__init__.py").write_text("")
    (root / "visualizations.py").write_text(textwrap.dedent("""
        import process_bigraph as pb

        class SpeciesPlot(pb.Step):
            pass

        class Helper:  # not a process/step; must never register
            pass
    """))
    (root / "processes.py").write_text(textwrap.dedent("""
        import process_bigraph as pb
        from regpkg.visualizations import SpeciesPlot  # imported, not defined here

        class ProcA(pb.Process):
            pass

        class StepB(pb.Step):
            pass

        NotAClass = 42
    """))

    monkeypatch.syspath_prepend(str(tmp_path))
    # Ensure a clean import each run.
    for name in list(sys.modules):
        if name == "regpkg" or name.startswith("regpkg."):
            del sys.modules[name]
    yield "regpkg"
    for name in list(sys.modules):
        if name == "regpkg" or name.startswith("regpkg."):
            del sys.modules[name]


def test_single_leaf_module_by_dotted_name_scopes_to_that_module(pkg_on_path):
    core = _FakeCore()
    n = register_package_processes(core, "regpkg.processes")
    assert n == 2
    assert set(core.registered) == {"ProcA", "StepB"}
    # SpeciesPlot is imported into processes.py but defined in visualizations —
    # must NOT be registered. Helper is a plain class — must NOT be registered.
    assert "SpeciesPlot" not in core.registered
    assert "Helper" not in core.registered


def test_single_leaf_module_by_module_object(pkg_on_path):
    mod = importlib.import_module("regpkg.processes")
    core = _FakeCore()
    n = register_package_processes(core, mod)
    assert n == 2
    assert set(core.registered) == {"ProcA", "StepB"}


def test_package_recurses_over_sibling_modules(pkg_on_path):
    core = _FakeCore()
    n = register_package_processes(core, "regpkg")
    # Whole-package scan picks up both processes.py and visualizations.py.
    assert set(core.registered) == {"ProcA", "StepB", "SpeciesPlot"}
    assert n == 3


def test_missing_module_is_non_fatal():
    core = _FakeCore()
    assert register_package_processes(core, "no_such_module_xyz") == 0
    assert core.registered == {}
