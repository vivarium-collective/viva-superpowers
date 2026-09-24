"""The in-place scaffolder (`/viva-workspace --in-place`, promoting an
existing git checkout) must get the same `cli` subpackage that a fresh
`viva-template` scaffold gets — both paths render the same template, but the
in-place path is a separate Python reimplementation (`_inplace_create_pkg`
and friends in scaffold.py) that has to be kept in parity by hand. This file
covers that parity for the `cli/` subpackage + pyproject wiring it adds.

Mirrors test_workspace_scaffold.py's convention: skip if a real viva-template
checkout isn't available at $PBG_TEMPLATE (default ~/code/pbg-template).
"""
from __future__ import annotations

import ast
import os
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

PBG_TEMPLATE = Path(os.environ.get("PBG_TEMPLATE", "~/code/pbg-template")).expanduser().resolve()


@pytest.fixture(autouse=True)
def _check_template_exists():
    if not PBG_TEMPLATE.is_dir():
        pytest.skip(f"pbg-template not found at {PBG_TEMPLATE} (set up Task 9 first)")


def _init_git_repo(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / "README.md").write_text("# demo\n")
    for args in (
        ["git", "init", "-q", "-b", "main"],
        ["git", "config", "user.email", "test@test.com"],
        ["git", "config", "user.name", "test"],
        ["git", "add", "-A"],
        ["git", "commit", "-q", "-m", "init"],
    ):
        subprocess.run(args, cwd=root, check=True)


def _scaffold_in_place(root: Path, plugin_root: Path, name: str) -> None:
    subprocess.run(
        [sys.executable, "-m", "viva_superpowers.scaffold", "workspace",
         "--name", name, "--target", str(root), "--in-place",
         "--template-source", str(PBG_TEMPLATE)],
        check=True, cwd=plugin_root,
    )


def test_inplace_creates_cli_subpackage_and_pyproject_wiring(tmp_path, plugin_root):
    root = tmp_path / "demo-ws"
    _init_git_repo(root)
    _scaffold_in_place(root, plugin_root, "demo-ws")

    pkg = root / "pbg_demo_ws"
    assert (pkg / "cli" / "__init__.py").is_file()
    assert (pkg / "cli" / "__main__.py").is_file()

    pyproject = tomllib.loads((root / "pyproject.toml").read_text())
    assert pyproject["project"]["optional-dependencies"]["cli"] == ["typer", "rich"]
    assert pyproject["project"]["scripts"]["demo-ws"] == "pbg_demo_ws.cli.__main__:main"


def test_inplace_merges_cli_extra_and_scripts_into_existing_pyproject(tmp_path, plugin_root):
    """A repo that already has its own pyproject.toml (no cli extra, no
    [project.scripts]) gets them merged in, not clobbered."""
    root = tmp_path / "demo-ws-merge"
    root.mkdir(parents=True)
    (root / "pyproject.toml").write_text(
        '[project]\n'
        'name = "demo-ws-merge"\n'
        'version = "0.0.0"\n'
        'requires-python = ">=3.11"\n'
        'dependencies = [\n'
        '    "pyyaml",\n'
        ']\n\n'
        '[project.optional-dependencies]\n'
        'dev = ["pytest>=7.4"]\n\n'
        '[build-system]\n'
        'requires = ["hatchling"]\n'
        'build-backend = "hatchling.build"\n'
    )
    (root / "README.md").write_text("# demo\n")
    for args in (
        ["git", "init", "-q", "-b", "main"],
        ["git", "config", "user.email", "test@test.com"],
        ["git", "config", "user.name", "test"],
        ["git", "add", "-A"],
        ["git", "commit", "-q", "-m", "init with existing pyproject"],
    ):
        subprocess.run(args, cwd=root, check=True)

    _scaffold_in_place(root, plugin_root, "demo-ws-merge")

    pyproject = tomllib.loads((root / "pyproject.toml").read_text())
    extras = pyproject["project"]["optional-dependencies"]
    assert extras["cli"] == ["typer", "rich"]
    assert extras["dev"] == ["pytest>=7.4"]  # pre-existing extra untouched
    assert pyproject["project"]["scripts"]["demo-ws-merge"] == "pbg_demo_ws_merge.cli.__main__:main"
    assert pyproject["project"]["dependencies"] == ["pyyaml"] or "pyyaml" in pyproject["project"]["dependencies"]


def test_inplace_cli_main_is_valid_python(tmp_path, plugin_root):
    root = tmp_path / "demo-ws-syntax"
    _init_git_repo(root)
    _scaffold_in_place(root, plugin_root, "demo-ws-syntax")

    main_py = root / "pbg_demo_ws_syntax" / "cli" / "__main__.py"
    ast.parse(main_py.read_text())  # raises SyntaxError on a malformed render
    text = main_py.read_text()
    assert '@app.command(name="run")' in text
    assert "to_composite(" in text
    assert "composite-test-run" not in text  # no dashboard-server dependency
