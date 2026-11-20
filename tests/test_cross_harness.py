"""Cross-harness delivery guard.

The Claude gateway (`skills/orient/SKILL.md`, auto-injected by
`hooks/session-start`) and the harness-neutral gateway (`AGENTS.md`, read by Codex
/ Cursor / others) must not drift apart, and `AGENTS.md` must actually be
harness-neutral. See docs/cross-harness.md.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
AGENTS = ROOT / "AGENTS.md"
ORIENT = ROOT / "skills" / "orient" / "SKILL.md"
CODEX_TOOLS = ROOT / "references" / "codex-tools.md"

# Skills no longer carry a `viva-` prefix, so a bare `/word` regex would also catch
# path fragments (docs/conventions, rigor-checklist.md, …). Match only real skill
# commands, derived from the skills/ dir, by whole word.
_SKILL_NAMES = sorted(p.parent.name for p in (ROOT / "skills").glob("*/SKILL.md"))
_SKILL_CMD = re.compile(r"/(?:" + "|".join(re.escape(n) for n in _SKILL_NAMES) + r")\b")

# The 7 skills whose bodies assume subagent dispatch — codex-tools.md must give
# each an inline fallback (kept in sync with the grep in the PR scope).
_DISPATCH_SKILLS = {
    "expert", "report", "investigation", "study",
    "harden-investigation", "navigate", "orient",
}


def test_agents_and_codex_refs_exist():
    assert AGENTS.is_file(), "AGENTS.md gateway is missing"
    assert CODEX_TOOLS.is_file(), "references/codex-tools.md is missing"


def test_rule_is_present_in_both_gateways():
    rule = "even a 1% chance"
    assert rule in ORIENT.read_text(), "orient lost the 1%-chance Rule"
    assert rule in AGENTS.read_text(), (
        "AGENTS.md must carry the same 1%-chance Rule as orient"
    )


def test_routing_coverage_no_drift():
    """Every /* command orient routes to must also appear in AGENTS.md.

    Adding a route to orient without mirroring it into AGENTS.md fails here.
    """
    orient_cmds = set(_SKILL_CMD.findall(ORIENT.read_text()))
    agents_cmds = set(_SKILL_CMD.findall(AGENTS.read_text()))
    missing = orient_cmds - agents_cmds
    assert not missing, (
        f"AGENTS.md is missing /* commands present in orient: "
        f"{sorted(missing)} — mirror the routing table / skill map."
    )


def test_agents_is_harness_neutral():
    text = AGENTS.read_text()
    # Affirmative: it must tell the reader to open the SKILL.md file (no Skill tool).
    assert "SKILL.md" in text and "open" in text.lower(), (
        "AGENTS.md must instruct opening skills/<name>/SKILL.md (no Claude Skill tool)"
    )
    # It must point at the idiom map.
    assert "codex-tools.md" in text


def test_codex_tools_covers_dispatch_skills():
    text = CODEX_TOOLS.read_text()
    missing = {s for s in _DISPATCH_SKILLS if s not in text}
    assert not missing, (
        f"references/codex-tools.md must give an inline fallback for the "
        f"dispatch-using skills; missing: {sorted(missing)}"
    )
