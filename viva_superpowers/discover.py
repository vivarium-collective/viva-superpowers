"""Discover cycle — the write/wire layer that drives the RFC-0005/0006 ops.

The knowledge / argument / narrate / audit / synthesize modules are pure
derive-first projections: they take dicts, return dicts, and (by design) persist
nothing. That left four of the six cycle operations unreachable from any verb and
the canonical verdict un-writable — which is why an investigation's study verdicts
read empty even when the gate roll-up would derive them.

This module closes that gap:

* :func:`run_cycle` chains all six ops into ONE projection — one invocation is one
  turn of the discovery cycle (derive verdicts -> derive the argument graph ->
  narrate -> audit for unsupported transitions -> roll up the synthesis spine ->
  collect the open calls). It is pure: give it an ``inv_spec`` and its member
  studies and it returns the whole bundle, authored blocks already merged over the
  derived projection.
* :func:`set_verdict` is the authored canonical-verdict write op the derive-on-read
  layer lacked — it records a human's verdict (and rationale) on a study so
  ``canonical_verdict`` honors it (authored wins).
* :func:`persist_cycle` writes the projection into ``investigation.yaml`` as a
  regenerable ``knowledge_cycle`` cache, WITHOUT touching the sparse authored
  ``knowledge`` / ``argument`` blocks — derive-first stays intact, so the cache can
  always be thrown away and recomputed.
* :func:`load_cycle_inputs` reads an investigation + its member studies from disk.

The science advances by re-running the cycle: fill verdicts -> narrate the arc ->
the audit surfaces the gaps -> close them by extending models/studies -> re-run.
"""
from __future__ import annotations

import argparse
import datetime as _dt
from pathlib import Path
from typing import Any

from .argument_store import derive_argument, merge_argument
from .investigation_import import investigations_dir, studies_dir
from .knowledge_store import canonical_verdict, derive_knowledge, merge_knowledge
from .narrative import audit, narrate
from .study_io import load_yaml, load_yaml_mapping, save_yaml_atomic
from .synthesis import open_calls, synthesize_gates

#: the canonical scientific verdict vocabulary a human may author
VERDICT_VOCAB = ("supported", "qualified", "inconclusive", "refuted", "unassessed")


# ---------------------------------------------------------------------------
# run_cycle — one invocation = one turn of the discovery cycle
# ---------------------------------------------------------------------------

def run_cycle(inv_spec: dict, studies_by_slug: dict[str, dict]) -> dict:
    """Project one full discovery cycle over an investigation + its studies.

    Pure: no disk I/O. Each derived projection is merged over its authored block
    (``inv_spec['knowledge']`` / ``inv_spec['argument']``) with the
    authored-wins / empty-never-clobbers rule, then narrate/audit/synthesize read
    the merged argument graph.
    """
    knowledge = merge_knowledge(inv_spec.get("knowledge"),
                                derive_knowledge(inv_spec, studies_by_slug))
    argument = merge_argument(inv_spec.get("argument"),
                              derive_argument(inv_spec, studies_by_slug))

    narrative = narrate(argument, inv_spec.get("question"), inv_spec.get("audience"))
    gaps = audit(narrative, argument)
    gates = synthesize_gates(inv_spec, argument["claims"])
    calls = open_calls(inv_spec, argument["claims"], gaps)

    return {
        "knowledge": knowledge,
        "argument": argument,
        "narrative": narrative,
        "audit": gaps,
        "gates": gates,
        "open_calls": calls,
    }


# ---------------------------------------------------------------------------
# set_verdict — the authored canonical-verdict write op
# ---------------------------------------------------------------------------

def set_verdict(study_path: Path | str, verdict: str, rationale: str | None = None) -> dict:
    """Author a canonical verdict on a study (authored wins over the derived roll-up).

    Writes ``verdict`` (and, when given, ``verdict_rationale``) into study.yaml and
    returns the resulting :func:`canonical_verdict` record. Raises ``ValueError`` on
    an off-vocabulary verdict.
    """
    if verdict not in VERDICT_VOCAB:
        raise ValueError(f"verdict must be one of {VERDICT_VOCAB}, got {verdict!r}")
    path = Path(study_path)
    spec = load_yaml_mapping(path)
    spec["verdict"] = verdict
    if rationale:
        spec["verdict_rationale"] = rationale
    save_yaml_atomic(path, spec)
    return canonical_verdict(spec)


# ---------------------------------------------------------------------------
# persist_cycle — regenerable cache, authored blocks untouched
# ---------------------------------------------------------------------------

def persist_cycle(inv_path: Path | str, inv_spec: dict, result: dict) -> dict:
    """Write the cycle projection into investigation.yaml as ``knowledge_cycle``.

    Re-reads the on-disk spec (so concurrent authored edits are never clobbered),
    sets only the regenerable ``knowledge_cycle`` cache, and atomically rewrites.
    The sparse authored ``knowledge`` / ``argument`` blocks are left alone — the
    cache is derived and may be regenerated at any time.
    """
    path = Path(inv_path)
    on_disk = load_yaml_mapping(path) if path.exists() else dict(inv_spec)
    on_disk["knowledge_cycle"] = {
        "generated_at": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
        "verdicts": result["knowledge"]["verdicts"],
        "concepts": result["knowledge"]["concepts"],
        "claims": result["argument"]["claims"],
        "edges": result["argument"]["edges"],
        "narrative": result["narrative"],
        "audit": result["audit"],
        "gates": result["gates"],
        "open_calls": result["open_calls"],
    }
    save_yaml_atomic(path, on_disk)
    return on_disk["knowledge_cycle"]


# ---------------------------------------------------------------------------
# load_cycle_inputs — read an investigation + its member studies from disk
# ---------------------------------------------------------------------------

def load_cycle_inputs(ws_root: Path | str, slug: str) -> tuple[Path, dict, dict[str, dict]]:
    """Load ``(inv_path, inv_spec, studies_by_slug)`` for an investigation.

    Member studies resolve from the flat ``studies/<slug>/study.yaml`` first, then
    the nested ``<investigations>/<inv>/studies/<slug>/study.yaml`` fallback; a
    member with no spec on disk is skipped (not fatal), matching the derive layer.
    """
    ws = Path(ws_root)
    inv_path = investigations_dir(ws) / slug / "investigation.yaml"
    inv_spec = load_yaml_mapping(inv_path)

    flat = studies_dir(ws)
    nested = investigations_dir(ws) / slug / "studies"
    member_slugs = inv_spec.get("studies") or _slugs_on_disk(flat, nested)

    studies_by_slug: dict[str, dict] = {}
    for s in member_slugs:
        for base in (flat, nested):
            sp = base / s / "study.yaml"
            if sp.exists():
                studies_by_slug[s] = load_yaml(sp)
                break
    return inv_path, inv_spec, studies_by_slug


def _slugs_on_disk(*dirs: Path) -> list[str]:
    seen: list[str] = []
    for d in dirs:
        if d.is_dir():
            for child in sorted(d.iterdir()):
                if (child / "study.yaml").exists() and child.name not in seen:
                    seen.append(child.name)
    return seen


# ---------------------------------------------------------------------------
# A compact summary for the CLI
# ---------------------------------------------------------------------------

def summarize(result: dict) -> str:
    verdicts = result["knowledge"]["verdicts"]
    tally: dict[str, int] = {}
    for rec in verdicts.values():
        tally[rec["verdict"]] = tally.get(rec["verdict"], 0) + 1
    verdict_line = ", ".join(f"{v}={n}" for v, n in sorted(tally.items())) or "none"
    gate_line = ", ".join(f"{g['id']}:{g['verdict']}" for g in result["gates"]) or "none"
    return (
        f"verdicts: {verdict_line}\n"
        f"claims: {len(result['argument']['claims'])}  edges: {len(result['argument']['edges'])}\n"
        f"narrative units: {len(result['narrative']['units'])}  "
        f"limitations: {len(result['narrative']['limitations'])}  "
        f"open_questions: {len(result['narrative']['open_questions'])}\n"
        f"audit gaps: {len(result['audit'])}  open_calls: {len(result['open_calls'])}\n"
        f"plan gates: {gate_line}"
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="viva-discover",
        description="Drive one turn of the RFC-0005/0006 discovery cycle over an investigation.",
    )
    parser.add_argument("--workspace", default=".", help="workspace root (default: cwd)")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_cycle = sub.add_parser("cycle", help="run + persist one discovery cycle")
    p_cycle.add_argument("investigation", help="investigation slug")
    p_cycle.add_argument("--no-write", action="store_true", help="project only, do not persist")

    p_status = sub.add_parser("status", help="project one cycle and print the summary (no write)")
    p_status.add_argument("investigation", help="investigation slug")

    p_sv = sub.add_parser("set-verdict", help="author a canonical verdict on a study")
    p_sv.add_argument("study", help="study slug")
    p_sv.add_argument("verdict", choices=VERDICT_VOCAB)
    p_sv.add_argument("--rationale", default=None)

    args = parser.parse_args(argv)
    ws = Path(args.workspace).resolve()

    if args.cmd in ("cycle", "status"):
        inv_path, inv_spec, studies = load_cycle_inputs(ws, args.investigation)
        result = run_cycle(inv_spec, studies)
        print(summarize(result))
        if args.cmd == "cycle" and not args.no_write:
            persist_cycle(inv_path, inv_spec, result)
            print(f"persisted knowledge_cycle -> {inv_path}")
        return 0

    if args.cmd == "set-verdict":
        sp = studies_dir(ws) / args.study / "study.yaml"
        if not sp.exists():
            parser.error(f"no study.yaml at {sp}")
        rec = set_verdict(sp, args.verdict, args.rationale)
        print(f"{args.study}: verdict={rec['verdict']} source={rec['verdict_source']}")
        return 0

    return 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
