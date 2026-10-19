"""Tests for viva_superpowers.inquiry_ops — the declarative inquiry operations
(RFC-0004 §5): consolidate / split / reopen / assess / narrate.

Each op is a declarative transaction over the Concept Store (preview →
invariant-check → atomic write). All are NON-DESTRUCTIVE: member Study files are
never deleted, prior verdicts/groupings survive in the revision history.
"""
from __future__ import annotations

from pathlib import Path

import yaml

from viva_superpowers.inquiry_ops import consolidate, split, reopen, assess, narrate


def _ws(tmp_path, studies=("og-x", "og-y")):
    ws = tmp_path / "ws"
    inv = ws / "investigations" / "og"
    inv.mkdir(parents=True)
    (inv / "investigation.yaml").write_text("name: og\ntitle: OG\n")
    for s in studies:
        d = ws / "studies" / s
        d.mkdir(parents=True)
        (d / "study.yaml").write_text(f"name: {s}\n")
    return inv


def _concepts(inv_dir):
    spec = yaml.safe_load((inv_dir / "investigation.yaml").read_text()) or {}
    return {c["id"]: c for c in (spec.get("concepts") or [])}


# ---- consolidate (non-destructive) ------------------------------------------

def test_consolidate_groups_without_deleting_studies(tmp_path):
    inv = _ws(tmp_path)
    r = consolidate(inv, "grp", ["og-x", "og-y"], synthesis="grouped")
    assert r["applied"] is True and not r["violations"]
    # member study files survive — non-destructive
    assert (inv.parent.parent / "studies" / "og-x" / "study.yaml").is_file()
    assert (inv.parent.parent / "studies" / "og-y" / "study.yaml").is_file()
    c = _concepts(inv)["grp"]
    assert c["member_studies"] == ["og-x", "og-y"]
    assert c["org_state"] == "consolidated"
    assert c["synthesis"] == "grouped"


def test_consolidate_refuses_missing_study(tmp_path):
    inv = _ws(tmp_path)
    r = consolidate(inv, "grp", ["og-x", "ghost"])
    assert r["applied"] is False and r["violations"]
    assert "grp" not in _concepts(inv)   # nothing written on a violation


def test_consolidate_idempotent(tmp_path):
    inv = _ws(tmp_path)
    consolidate(inv, "grp", ["og-x", "og-y"], synthesis="s")
    consolidate(inv, "grp", ["og-x", "og-y"], synthesis="s")
    cs = [c for c in (yaml.safe_load((inv / "investigation.yaml").read_text())["concepts"]) if c["id"] == "grp"]
    assert len(cs) == 1 and len(cs[0]["revisions"]) == 1


# ---- split (non-destructive, prior grouping recoverable) --------------------

def test_split_partitions_and_preserves_prior(tmp_path):
    inv = _ws(tmp_path)
    consolidate(inv, "grp", ["og-x", "og-y"])
    r = split(inv, "grp", [("grp-a", ["og-x"]), ("grp-b", ["og-y"])])
    assert r["applied"] is True and not r["violations"]
    cs = _concepts(inv)
    assert cs["grp-a"]["member_studies"] == ["og-x"]
    assert cs["grp-b"]["member_studies"] == ["og-y"]
    # prior grouping recoverable from the original concept's revision
    last = cs["grp"]["revisions"][-1]
    assert last["prior_members"] == ["og-x", "og-y"]


def test_split_refuses_uncovered_member(tmp_path):
    inv = _ws(tmp_path)
    consolidate(inv, "grp", ["og-x", "og-y"])
    r = split(inv, "grp", [("grp-a", ["og-x"])])   # og-y left out
    assert r["applied"] is False and r["violations"]


# ---- reopen (prior assessment survives) -------------------------------------

def test_reopen_keeps_prior_assessment(tmp_path):
    inv = _ws(tmp_path)
    consolidate(inv, "grp", ["og-x"])
    assess(inv, "grp", "qualified", "og-x bounds it")
    r = reopen(inv, "grp", "new DIC-cliff evidence", open_question="does it hold at higher DIC?")
    assert r["applied"] is True
    c = _concepts(inv)["grp"]
    assert c["org_state"] == "reopened"
    assert c["assessment"]["verdict"] == "qualified"        # prior assessment retained
    assert "does it hold at higher DIC?" in c["open_questions"]


# ---- assess (never overwrite a prior verdict) -------------------------------

def test_assess_appends_never_overwrites(tmp_path):
    inv = _ws(tmp_path)
    consolidate(inv, "grp", ["og-x"])
    assess(inv, "grp", "supported", "first")
    assess(inv, "grp", "refuted", "second")
    c = _concepts(inv)["grp"]
    assert c["assessment"]["verdict"] == "refuted"          # latest wins on the field
    verdicts = [r.get("assessment", {}).get("verdict") for r in c["revisions"] if r.get("assessment")]
    assert "supported" in verdicts and "refuted" in verdicts  # prior verdict retrievable


def test_assess_rejects_bad_verdict(tmp_path):
    inv = _ws(tmp_path)
    consolidate(inv, "grp", ["og-x"])
    r = assess(inv, "grp", "passed", "x")   # wrong vocab
    assert r["applied"] is False and r["violations"]


# ---- narrate (claims link to member studies) --------------------------------

def test_narrate_links_claims_to_studies(tmp_path):
    inv = _ws(tmp_path)
    consolidate(inv, "grp", ["og-x", "og-y"], synthesis="the grouped synthesis")
    spec = yaml.safe_load((inv / "investigation.yaml").read_text())
    lines = narrate(spec, {})
    grp = next(l for l in lines if l["concept"] == "grp")
    assert grp["synthesis"] == "the grouped synthesis"
    assert grp["member_studies"] == ["og-x", "og-y"]
