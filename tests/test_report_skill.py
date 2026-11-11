"""Guard test for the /viva-report skill (engine-native-skills migration, Phase 2).

Supersedes the Phase 2.1d "thin client of the workbench dashboard API" contract.
The three deterministic passes (lint, readout-migrate, render) now run through the
`discover` CLI (`python -m discovery_engine.discover`) directly, so /viva-report
lints and renders with the dashboard server DOWN. Each verb wraps the identical
engine function the old `/api/*` endpoint wrapped, so output is unchanged — only
the transport.

The still-critical guards are KEPT: the skill must drive the engine via the CLI,
not inline engine compute (`test_no_inline_plugin_compute`), and must not
reimplement override-key derivation / override-log writing (that lives inside the
engine — `test_no_client_side_override_reimplementation`).
"""
from __future__ import annotations

from pathlib import Path

import pytest

_SKILL = Path(__file__).resolve().parents[1] / "skills" / "viva-report" / "SKILL.md"


@pytest.fixture
def skill_text() -> str:
    return _SKILL.read_text(encoding="utf-8")


def test_skill_file_exists():
    assert _SKILL.is_file(), "skills/viva-report/SKILL.md must exist"


def test_references_lint_backend(skill_text):
    # Pass B linter runs engine-native via the discover CLI (server-free).
    assert "discover" in skill_text
    assert "lint --json" in skill_text


def test_references_readout_migrate_backend(skill_text):
    # Pass B½ canonicalization via `discover readout-migrate <slug> --write`.
    assert "readout-migrate" in skill_text


def test_references_render_backend(skill_text):
    # Render via `discover report`, with byte-stable (--today) and forced
    # (--force, logs overrides in-engine) renders as CLI flags — not
    # reimplemented client-side.
    assert "discover" in skill_text
    assert "report" in skill_text
    assert "--today" in skill_text
    assert "--force" in skill_text


def test_no_inline_plugin_compute(skill_text):
    """2.1d rewire: zero in-process viva_superpowers consumer sites for the
    3 rewired ops (report_linter, readout_migration, report render).

    A SKILL.md is a program — `from viva_superpowers.X import Y` and
    `python -m viva_superpowers.X` (beyond the untouched bootstrap/deferred
    call sites) are hard-blocker consumer sites, not prose.
    """
    assert "python -m discovery_engine.reporting.linter" not in skill_text
    assert "from discovery_engine.study.readout_migration" not in skill_text
    assert "from discovery_engine.reporting.report import" not in skill_text
    assert "from discovery_engine.reporting.report import render_workspace_report" not in skill_text
    assert "render_workspace_report(" not in skill_text
    assert "from vivarium_workbench.lib.report import" not in skill_text


def test_no_client_side_override_reimplementation(skill_text):
    """The whole point of the 2.1d endpoint enhancement: override-key
    derivation / override-log writing must live server-side only. If the
    skill starts hashing/deriving override keys or writing
    report-lint-overrides.json itself, the endpoints were bypassed.
    """
    assert "hashlib" not in skill_text
    assert "write_override(" not in skill_text
    assert "load_overrides(" not in skill_text
    assert "apply_overrides(" not in skill_text
    assert "_override_key(" not in skill_text


def test_server_is_optional_for_deterministic_passes(skill_text):
    # The deterministic passes (lint / readout-migrate / render) are engine-native
    # and need no server. The URL is resolved only if a dashboard is already
    # running (for the optional Pass A needs-attention enrichment + the UI tail),
    # via the workspace.yaml walk-up + .pbg/server/server-info idiom; its absence
    # is no longer an error.
    assert "workspace.yaml" in skill_text
    assert ".pbg/server/server-info" in skill_text
    assert "server_preflight" in skill_text


def test_bootstrap_call_sites_untouched(skill_text):
    # The paths bootstrap now imports the engine module directly
    # (discovery_engine.paths) rather than through the viva_superpowers facade
    # shim — Stage A of retiring the facade: skills depend on discovery_engine
    # for engine modules, not on the re-export.
    assert "python -m discovery_engine.paths --env" in skill_text
    assert "python -m viva_superpowers.paths --env" not in skill_text
    # Phase 2.1j rewired the dashboard-restart site to the vwb CLI (the plugin's
    # server manager viva_superpowers.workbench was deleted).
    assert "vwb server-restart" in skill_text
    assert "python -m viva_superpowers.workbench" not in skill_text
