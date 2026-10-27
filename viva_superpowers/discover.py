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
import copy
import datetime as _dt
import hashlib
import re
from io import StringIO
from pathlib import Path

from ruamel.yaml import YAML

from .argument_store import derive_argument, merge_argument
from .investigation_import import investigations_dir, studies_dir
from .knowledge_store import canonical_verdict, derive_knowledge, merge_knowledge
from .narrative import audit, narrate
from .study_io import atomic_write, load_yaml, load_yaml_mapping, save_yaml_atomic
from .synthesis import open_calls, synthesize_gates
from .validation import ValidationContext, run_validators


def _ruamel() -> YAML:
    """Comment-preserving round-trip YAML — the same config the canonicalize/reconcile
    writers use (``study_canonicalize._ruamel``). A ``width`` well past any real line
    keeps long scalars on one line so an edge enrichment is a one-field diff, not a
    whole-file reflow that drops load-bearing ``# …`` annotations."""
    y = YAML()
    y.preserve_quotes = True
    y.width = 4096
    y.indent(mapping=2, sequence=4, offset=2)
    return y


def _set_relation_inplace(spec, upstream: str, relation: str) -> bool:
    """Set the epistemic ``relation`` to ``upstream`` on the edge where it already
    lives, mutating ``spec`` in place (a plain dict OR a ruamel ``CommentedMap``).

    Precedence: the canonical ``pipeline_gate.prerequisites`` entry first, then the
    legacy ``parent_studies`` backbone (a bare ``{study}`` dict, or a plain string
    promoted to ``{study, relation}``). If the dependency is declared nowhere, an
    epistemic-only ``pipeline_gate.prerequisites`` entry is appended. Returns True iff
    a change was made (idempotent: re-setting the same relation is a no-op)."""
    pg = spec.get("pipeline_gate")
    if isinstance(pg, dict):
        for p in pg.get("prerequisites") or []:
            if isinstance(p, dict) and p.get("study") == upstream:
                if p.get("relation") == relation:
                    return False
                p["relation"] = relation
                return True
    ps = spec.get("parent_studies")
    if isinstance(ps, list):
        for i, e in enumerate(ps):
            if isinstance(e, str) and e == upstream:
                ps[i] = {"study": upstream, "relation": relation}
                return True
            if isinstance(e, dict) and e.get("study") == upstream:
                if e.get("relation") == relation:
                    return False
                e["relation"] = relation
                return True
    pg = spec.setdefault("pipeline_gate", {})
    prereqs = pg.setdefault("prerequisites", [])
    prereqs.append({"study": upstream, "relation": relation})
    return True


def _enrich_file(path: Path | str, upstreams: list[str], relation: str) -> list[str]:
    """Load a study.yaml round-trip (comments preserved), set ``relation`` in place for
    each upstream where its edge lives, and write back only if something changed.
    Returns the upstreams actually changed."""
    y = _ruamel()
    text = Path(path).read_text(encoding="utf-8")
    spec = y.load(text) or {}
    changed = [u for u in upstreams if _set_relation_inplace(spec, u, relation)]
    if changed:
        buf = StringIO()
        y.dump(spec, buf)
        atomic_write(path, buf.getvalue())
    return changed

#: the canonical scientific verdict vocabulary a human may author
VERDICT_VOCAB = ("supported", "qualified", "inconclusive", "refuted", "unassessed")

#: the epistemic relation vocabulary a prerequisite edge may carry (RFC-0005 §4).
#: These are the facet ``argument_store`` reads to build claim->claim edges; a bare
#: ``condition: tests-passed`` prerequisite is organizational only and yields no
#: argument edge until its epistemic relation is authored.
EPISTEMIC_RELATIONS = ("builds-on", "tests", "refutes", "alternative-to", "motivates")
# The frontier-item kinds a resolution can discharge (mirror discovery_engine priorities).
RESOLUTION_KINDS = ("unaddressed_criterion", "open_challenge", "narrative_gap",
                    "open_decision", "divergence", "open_question",
                    "validation_finding", "stale_validation")


def add_resolution(inv_spec: dict, kind: str, target: str, rationale: str,
                   by: str | None = None) -> dict:
    """Record a resolution ``{kind, target, rationale, by?}`` in an investigation spec —
    the uniform discharge the discovery crank honors for every frontier-item kind. The op
    that produced an artifact (an adjudication, a bridging study, a met criterion) records
    it here, back-referenced via ``by``. Idempotent on ``(kind, target)``: a second call
    updates the record rather than duplicating. A rationale is required — a resolution
    documents *why* an item is discharged, it does not silently suppress it. Returns the
    updated spec (pure; the caller persists)."""
    if kind not in RESOLUTION_KINDS:
        raise ValueError(f"kind must be one of {RESOLUTION_KINDS}, got {kind!r}")
    if not target:
        raise ValueError("target is required (the frontier item's target, as the crank prints it)")
    if not (rationale or "").strip():
        raise ValueError("a rationale is required — a resolution documents why the item is discharged")
    rec = {"kind": kind, "target": target, "rationale": rationale}
    if by:
        rec["by"] = by
    out = dict(inv_spec)
    kept = [r for r in (out.get("resolutions") or [])
            if not (isinstance(r, dict) and r.get("kind") == kind and r.get("target") == target)]
    kept.append(rec)
    out["resolutions"] = kept
    return out


def record_resolution(inv_path: Path | str, kind: str, target: str, rationale: str,
                      by: str | None = None) -> dict:
    """Load an investigation.yaml, add a resolution, save atomically. Returns the record."""
    path = Path(inv_path)
    spec = add_resolution(load_yaml_mapping(path), kind, target, rationale, by)
    save_yaml_atomic(path, spec)
    return spec["resolutions"][-1]


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

    # RFC-0007: run the registered validators over the derived cycle. Each returns
    # typed (type, scope) validation records; the frontier projects the failing ones
    # and invariants() checks execution ⊥ scientific-judgment across them.
    ctx = ValidationContext(inv_spec=inv_spec, studies=studies_by_slug,
                            argument=argument, narrative=narrative, audit=gaps)

    bundle = {
        "knowledge": knowledge,
        "argument": argument,
        "narrative": narrative,
        "audit": gaps,
        "gates": gates,
        "open_calls": calls,
        "validations": run_validators(ctx),
    }
    # Suggestions for new studies (the branch op, made first-class + expert-gated).
    bundle["suggestions"] = suggest_studies(bundle, inv_spec, studies_by_slug)
    return bundle


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
# relate / connect — author the epistemic edges that connect the argument graph
# ---------------------------------------------------------------------------

def relate(study_spec: dict, upstream: str, relation: str) -> dict:
    """Return a NEW study spec with the epistemic ``relation`` to ``upstream`` set.

    The relation is set on the edge where it already lives: a
    ``pipeline_gate.prerequisites`` entry (the canonical gate dependency — it then
    carries both the organizational ``condition`` and the epistemic ``relation``, the
    RFC-0006 unified form) is preferred, then a ``parent_studies`` backbone entry (a
    bare ``{study}`` dict, or a plain string promoted to ``{study, relation}``). Only
    when the dependency is declared nowhere is an epistemic-only prerequisite appended.
    Non-mutating; raises ``ValueError`` on an off-vocabulary relation.
    """
    if relation not in EPISTEMIC_RELATIONS:
        raise ValueError(f"relation must be one of {EPISTEMIC_RELATIONS}, got {relation!r}")
    spec = copy.deepcopy(study_spec)
    _set_relation_inplace(spec, upstream, relation)
    return spec


def connect_investigation(ws_root: Path | str, slug: str,
                          default_relation: str = "builds-on") -> dict[str, dict[str, list[str]]]:
    """Connect an investigation's narrative arc by authoring the missing epistemic edges.

    *Auto-enriches* every bare prerequisite in the **canonical** field
    (``pipeline_gate.prerequisites`` with no ``relation``) with ``default_relation``,
    persisting each change comment-preserving. Already-authored relations are left intact.

    A dependency declared **only** in the legacy ``parent_studies`` backbone (a plain
    string, or a bare ``{study}`` dict) is **not** blanket-asserted — that field can hold
    organizational parents that are not scientific edges, so defaulting them all to
    ``builds-on`` would over-connect the argument graph. Those are *surfaced* for an
    explicit, intentional :func:`relate` instead of silently skipped.

    Returns ``{"enriched": {slug: [ups]}, "needs_relate": {slug: [ups]}}``.
    """
    if default_relation not in EPISTEMIC_RELATIONS:
        raise ValueError(f"default_relation must be one of {EPISTEMIC_RELATIONS}, got {default_relation!r}")
    _, inv, studies = load_cycle_inputs(ws_root, slug)
    enriched: dict[str, list[str]] = {}
    needs_relate: dict[str, list[str]] = {}
    for s in inv.get("studies") or list(studies):
        spec = studies.get(s)
        if spec is None:
            continue
        pg = spec.get("pipeline_gate") or {}
        prereqs = pg.get("prerequisites") or [] if isinstance(pg, dict) else []
        pg_bare = [p["study"] for p in prereqs
                   if isinstance(p, dict) and p.get("study") and not p.get("relation")]
        pg_slugs = {p["study"] for p in prereqs
                    if isinstance(p, dict) and p.get("study")}
        ps_bare: list[str] = []
        for e in spec.get("parent_studies") or []:
            if isinstance(e, str) and e:
                up = e
            elif isinstance(e, dict) and e.get("study") and not e.get("relation"):
                up = e["study"]
            else:
                continue
            if up not in pg_slugs and up not in ps_bare:
                ps_bare.append(up)
        if pg_bare:
            done = _enrich_file(_study_path(ws_root, slug, s), pg_bare, default_relation)
            if done:
                enriched[s] = done
        if ps_bare:
            needs_relate[s] = ps_bare
    return {"enriched": enriched, "needs_relate": needs_relate}


def _study_path(ws_root: Path | str, slug: str, study: str) -> Path:
    ws = Path(ws_root)
    for base in (studies_dir(ws), investigations_dir(ws) / slug / "studies"):
        sp = base / study / "study.yaml"
        if sp.exists():
            return sp
    return studies_dir(ws) / study / "study.yaml"


# ---------------------------------------------------------------------------
# persist_cycle — regenerable cache, authored blocks untouched
# ---------------------------------------------------------------------------

def build_cycle_state(result: dict, inv_spec: dict) -> dict:
    """Project a **slim, actionable** summary of the cycle — the few dozen lines a
    human, the dashboard, or the next cycle actually needs, instead of the full
    regenerable projection. Carries the cycle's *outputs* that previously never fed
    forward: the value-ranked opportunities, suggestions, diagnosis, validator census,
    and drift. The full `knowledge`/`argument`/`narrative` are recomputable on demand
    via :func:`run_cycle`, so they are not dumped here."""
    from . import discovery_engine as de
    clo = de.closure(result, inv_spec)
    na = de.next_action(result, inv_spec)
    opps = de.opportunities(result, inv_spec)
    diag = de.diagnose(result, inv_spec)
    frontier = de.frontier(result, inv_spec)
    recs = result.get("validations") or []
    census: dict[str, int] = {}
    for r in recs:
        st = (r.get("result") or {}).get("execution_status")
        census[st] = census.get(st, 0) + 1
    sugg = result.get("suggestions") or []
    from .validation import stale_records
    return {
        "generated_at": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
        "closed": clo["closed"],
        "frontier_size": clo["open_items"],
        "next_action": ({"op": na["op"], "kind": na["kind"], "target": na["target"]}
                        if na else None),
        "top_opportunities": [{"source": o["source"], "action": o["action_type"],
                               "score": o["value"]["score"]} for o in opps[:8]],
        "suggestions": {"ready": sum(1 for s in sugg if s.get("status") == "ready"),
                        "awaiting_expert": sum(1 for s in sugg if s.get("status") == "awaiting_expert")},
        "diagnosis": {"flags": [f["flag"] for f in diag["flags"]],
                      "validator_pass_rate": diag["validator_pass_rate"]},
        # the recommendation->action bridge: the next moves + how they'd be executed,
        # for the Decide surface (nothing runs until a human/--autonomous step does).
        "execution_plan": [{"source": p["source"], "action": p["action_type"],
                            "score": p["score"], "consequence": p["consequence"],
                            "command": p["command"]}
                           for p in de.execute_plan(result, inv_spec)[:8]],
        "validator_census": census,
        "drift": {"divergences": sum(1 for i in frontier if i["kind"] == "divergence"),
                  "stale_validations": len(stale_records(recs, inv_spec.get("validation_snapshot")))},
    }


def persist_cycle(inv_path: Path | str, inv_spec: dict, result: dict) -> dict:
    """Write the slim ``cycle_state`` summary into investigation.yaml.

    Re-reads the on-disk spec (so concurrent authored edits are never clobbered),
    sets only the regenerable ``cycle_state``, and atomically rewrites. The authored
    blocks are left alone. **Retires the old bloated ``knowledge_cycle`` cache** (a
    multi-thousand-line dump of the full projection that nothing read); the full
    projection is recomputable via :func:`run_cycle`.
    """
    path = Path(inv_path)
    on_disk = load_yaml_mapping(path) if path.exists() else dict(inv_spec)
    on_disk.pop("knowledge_cycle", None)  # retire the bloated derived cache (0 readers)
    on_disk["cycle_state"] = build_cycle_state(result, inv_spec)
    save_yaml_atomic(path, on_disk)
    return on_disk["cycle_state"]


def _parent_in_parens(text: str, members: set) -> str | None:
    """The member study a decision names as its *subject*, e.g. 'Agent motion model
    (og-ecology follow-up): …' → 'og-ecology'. Only the parenthetical before the first
    colon counts (the subject position): a project-scope decision that merely mentions a
    study mid-sentence ('Publication scope: … (og-vent-environment -> …)') names no
    subject study and yields None, so it is not turned into a study suggestion."""
    subject = (text or "").split(":", 1)[0]
    for group in re.findall(r"\(([^)]+)\)", subject):
        token = group.strip().split()[0].rstrip(":,.").strip() if group.strip() else ""
        if token in members:
            return token
    return None


def suggest_studies(cycle_result: dict, inv_spec: dict, studies: dict) -> list[dict]:
    """Suggestions for new studies the cycle thinks should run next — the unified,
    expert-in-the-loop 'what to build' view (RFC-0005 branch op, made first-class).

    Each suggestion is ``{id, title, motivation, parent_study, source,
    awaiting_expert, status}``. It gathers the three sources that were scattered
    before: authored ``followup_proposals`` on member studies, the narrative-gap
    ``followup``s the audit derives, and each ``decisions_needed`` entry that names a
    member study in parentheses — the last are **gated on expert input** (``status:
    awaiting_expert``) so a new study is proposed but never seeded until the expert
    answers. Pure/read-only: it proposes, it does not create or run anything."""
    members = set(inv_spec.get("studies") or list(studies))
    out: list[dict] = []
    seen: set[str] = set()

    def add(sid, title, motivation, parent, source, awaiting):
        if not sid or sid in seen:
            return
        seen.add(sid)
        out.append({"id": sid, "title": title or sid, "motivation": motivation or "",
                    "parent_study": parent, "source": source,
                    "awaiting_expert": awaiting,
                    "status": "awaiting_expert" if awaiting else "ready"})

    # 1. authored followup proposals (an expert/agent already proposed the study)
    for slug, spec in (studies or {}).items():
        if not isinstance(spec, dict):
            continue
        for fp in spec.get("followup_proposals") or []:
            if not isinstance(fp, dict) or fp.get("status") in ("seeded", "done", "rejected"):
                continue
            add(fp.get("id"), fp.get("title"), fp.get("motivation"), slug, "followup_proposal", [])

    # 2. narrative-gap followups (the audit's auto-generated bridging studies)
    for g in cycle_result.get("audit") or []:
        fu = (g.get("followup") or {}) if isinstance(g, dict) else {}
        if fu.get("id"):
            add(fu["id"], fu.get("title"), fu.get("motivation"), fu.get("parent_study"),
                "narrative_gap", [])

    # 3. decisions_needed that name a member study → a study gated on that expert input
    ex = inv_spec.get("executive") or {}
    for d in ex.get("decisions_needed") or []:
        q = d.get("question") if isinstance(d, dict) else (d if isinstance(d, str) else None)
        if not q:
            continue
        parent = _parent_in_parens(q, members)
        if not parent:
            continue  # project-scope decision (publication/rule-set scope), not a study
        sid = f"seed-{parent}-{hashlib.sha256(q.encode()).hexdigest()[:6]}"
        add(sid, f"Follow-up to {parent} (pending an expert decision)", q, parent,
            "expert_decision", [q])

    return out


def _default_runner(command: str, ws_root: Path | str) -> dict:
    """Run a consequential executor command as a subprocess in the workspace, capturing
    its outcome. This is the real sim/seed invocation the autonomous bridge makes."""
    import subprocess
    proc = subprocess.run(command, shell=True, cwd=str(ws_root),
                          capture_output=True, text=True, timeout=3600)
    return {"returncode": proc.returncode,
            "ok": proc.returncode == 0,
            "tail": (proc.stdout or proc.stderr or "")[-400:]}


def execute_action(ws_root: Path | str, inv_slug: str, *, autonomous: bool = False,
                   runner=None) -> dict:
    """The bridge's execution step: take the top value-ranked action and carry it out,
    gated by consequence.

    - A side-effect-free action (``auto_safe``, e.g. re-snapshot) always runs.
    - A consequential action (``simulation`` / ``simulation+study`` — run a study, seed
      one) runs **only** with ``autonomous=True``, by invoking its real executor command
      as a subprocess (``runner``, injectable for tests); the outcome is recorded.
    - A ``review`` (verdict overwrite) or ``human-only`` (expert decision / adjudication)
      action never auto-runs — it is handed back.

    Executed actions are appended to the investigation's ``executed_actions`` log and the
    frontier is re-derived so the caller sees the change. Returns a record of what
    happened."""
    from . import discovery_engine as de
    inv_path, inv_spec, studies = load_cycle_inputs(ws_root, inv_slug)
    before = de.closure(run_cycle(inv_spec, studies), inv_spec)["open_items"]
    plan = de.execute_plan(run_cycle(inv_spec, studies), inv_spec)
    if not plan:
        return {"status": "nothing-to-do", "frontier": before}
    top = plan[0]
    rec = {"action": top["action_type"], "source": top["source"], "command": top["command"],
           "consequence": top["consequence"], "score": top["score"]}

    if top["auto_safe"]:
        snap = snapshot_validations(ws_root, inv_slug)
        rec["status"] = "executed"
        rec["outcome"] = {"ok": True, "detail": f"snapshot-validations: {len(snap)} records accepted"}
    elif top["consequence"] in ("simulation", "simulation+study"):
        if not autonomous:
            rec["status"] = "gated"
            rec["outcome"] = {"ok": None, "detail": "consequential — re-run with --autonomous to execute"}
        else:
            rec["outcome"] = (runner or _default_runner)(top["command"], ws_root)
            rec["status"] = "executed" if rec["outcome"].get("ok") else "failed"
    else:  # review / human-only
        rec["status"] = "gated-human"
        rec["outcome"] = {"ok": None, "detail": f"{top['consequence']} — needs a human decision"}

    if rec["status"] == "executed":
        _append_executed(inv_path, rec)
        _, inv2, studies2 = load_cycle_inputs(ws_root, inv_slug)
        rec["frontier_before"] = before
        rec["frontier_after"] = de.closure(run_cycle(inv2, studies2), inv2)["open_items"]
    return rec


def _append_executed(inv_path: Path | str, record: dict) -> None:
    """Append an execution record to the investigation's ``executed_actions`` log (an
    audit trail of what the bridge ran). Re-reads on disk, writes only this field."""
    path = Path(inv_path)
    on_disk = load_yaml_mapping(path) if path.exists() else {}
    log = list(on_disk.get("executed_actions") or [])
    log.append({"action": record["action"], "source": record["source"],
                "command": record["command"], "status": record["status"],
                "outcome": (record.get("outcome") or {}).get("detail")
                or ("ok" if (record.get("outcome") or {}).get("ok") else "see runner output"),
                "at": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")})
    on_disk["executed_actions"] = log
    save_yaml_atomic(path, on_disk)


def summarize_suggestions(suggestions: list[dict]) -> str:
    ready = [s for s in suggestions if s["status"] == "ready"]
    awaiting = [s for s in suggestions if s["status"] == "awaiting_expert"]
    lines = [f"suggested studies: {len(suggestions)}  ({len(ready)} ready, "
             f"{len(awaiting)} awaiting expert input)"]
    if ready:
        lines.append("ready to seed:")
        for s in ready:
            lines.append(f"  {s['id']}  {s['title']}"
                         + (f"  (builds on {s['parent_study']})" if s.get("parent_study") else "")
                         + f"  [{s['source']}]")
    if awaiting:
        lines.append("awaiting expert input (resolve the decision, then seed):")
        for s in awaiting:
            lines.append(f"  {s['id']}  (builds on {s.get('parent_study')})")
            for q in s["awaiting_expert"]:
                lines.append(f"      needs: {q}")
    if not suggestions:
        lines.append("  none — no new studies proposed this cycle.")
    return "\n".join(lines)


def snapshot_validations(ws_root: Path | str, slug: str) -> dict:
    """Persist the current validation records' signatures as the investigation's
    accepted ``validation_snapshot`` (RFC-0007 Phase 4). Later cycles compare a fresh
    re-derivation against it; drift surfaces as a ``stale_validation`` frontier item
    (an accepted judgment an upstream model/run change moved past). Returns the
    snapshot. Like :func:`persist_cycle`, re-reads on-disk so authored edits are not
    clobbered and writes only this regenerable cache."""
    from .validation import snapshot_of
    inv_path, inv_spec, studies = load_cycle_inputs(ws_root, slug)
    snap = snapshot_of(run_cycle(inv_spec, studies)["validations"])
    path = Path(inv_path)
    on_disk = load_yaml_mapping(path) if path.exists() else dict(inv_spec)
    on_disk["validation_snapshot"] = snap
    save_yaml_atomic(path, on_disk)
    return snap


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

    p_snap = sub.add_parser("snapshot-validations",
                            help="accept the current validation state; later drift is flagged stale")
    p_snap.add_argument("investigation", help="investigation slug")

    p_diag = sub.add_parser("diagnose",
                            help="classify the crank's productivity bottlenecks (why it is/isn't progressing)")
    p_diag.add_argument("investigation", help="investigation slug")

    p_sugg = sub.add_parser("suggest",
                            help="suggest new studies to run next, each with the expert input it needs")
    p_sugg.add_argument("investigation", help="investigation slug")

    p_opp = sub.add_parser("opportunities",
                           help="rank the frontier by value — what is most valuable to investigate next")
    p_opp.add_argument("investigation", help="investigation slug")

    p_exec = sub.add_parser("execute",
                            help="the recommendation→action bridge: show (or, with --execute, run) the next action")
    p_exec.add_argument("investigation", help="investigation slug")
    p_exec.add_argument("--execute", action="store_true",
                        help="actually run the top action when it is side-effect-free (else print its gated command)")
    p_exec.add_argument("--autonomous", action="store_true",
                        help="also run a CONSEQUENTIAL top action (seed a study / run a simulation) and record the outcome")

    p_sv = sub.add_parser("set-verdict", help="author a canonical verdict on a study")
    p_sv.add_argument("study", help="study slug")
    p_sv.add_argument("verdict", choices=VERDICT_VOCAB)
    p_sv.add_argument("--rationale", default=None)

    p_rel = sub.add_parser("relate", help="author an epistemic relation downstream <- upstream")
    p_rel.add_argument("downstream", help="the study whose prerequisite is being labelled")
    p_rel.add_argument("upstream", help="the study it relates to")
    p_rel.add_argument("--relation", choices=EPISTEMIC_RELATIONS, default="builds-on")

    p_conn = sub.add_parser("connect", help="enrich every bare prerequisite across an investigation")
    p_conn.add_argument("investigation", help="investigation slug")
    p_conn.add_argument("--relation", choices=EPISTEMIC_RELATIONS, default="builds-on")

    p_crank = sub.add_parser("crank", help="turn the discovery crank: frontier + next action + closure")
    p_crank.add_argument("investigation", help="investigation slug")

    p_res = sub.add_parser("resolve", help="record a resolution that discharges a frontier item")
    p_res.add_argument("investigation", help="investigation slug")
    p_res.add_argument("kind", choices=RESOLUTION_KINDS, help="the frontier-item kind to discharge")
    p_res.add_argument("target", help="the item's target, as the crank prints it (e.g. 'claim:og-x' or a study slug)")
    p_res.add_argument("--rationale", required=True, help="why the item is discharged (the adjudication / bridge)")
    p_res.add_argument("--by", default=None, help="the artifact that resolves it (e.g. study#finding)")

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

    if args.cmd == "relate":
        sp = studies_dir(ws) / args.downstream / "study.yaml"
        if not sp.exists():
            parser.error(f"no study.yaml at {sp}")
        _enrich_file(sp, [args.upstream], args.relation)
        print(f"{args.downstream} <-{args.relation}- {args.upstream}")
        return 0

    if args.cmd == "connect":
        report = connect_investigation(ws, args.investigation, args.relation)
        enriched, needs_relate = report["enriched"], report["needs_relate"]
        n = sum(len(v) for v in enriched.values())
        print(f"enriched {n} bare prerequisite(s) with '{args.relation}' across "
              f"{len(enriched)} studies:")
        for s, ups in enriched.items():
            print(f"  {s}: {', '.join(ups)}")
        if needs_relate:
            print("\nparent_studies-only dependencies — NOT auto-asserted (verify each is a "
                  "scientific edge, then author it explicitly):")
            for s, ups in needs_relate.items():
                for up in ups:
                    print(f"  discover --workspace {args.workspace} relate {s} {up} "
                          f"--relation {args.relation}")
        return 0

    if args.cmd == "resolve":
        inv_path = investigations_dir(ws) / args.investigation / "investigation.yaml"
        if not inv_path.exists():
            parser.error(f"no investigation.yaml at {inv_path}")
        rec = record_resolution(inv_path, args.kind, args.target, args.rationale, args.by)
        print(f"resolved [{rec['kind']}] {rec['target']}"
              + (f"  (by {rec['by']})" if rec.get("by") else "")
              + f"  — {rec['rationale']}")
        return 0

    if args.cmd == "crank":
        from . import discovery_engine
        _, inv_spec, studies = load_cycle_inputs(ws, args.investigation)
        result = run_cycle(inv_spec, studies)
        print(discovery_engine.summarize(discovery_engine.crank(result, inv_spec)))
        return 0

    if args.cmd == "snapshot-validations":
        snap = snapshot_validations(ws, args.investigation)
        print(f"accepted validation snapshot: {len(snap)} record(s) "
              f"— later drift surfaces as stale_validation")
        return 0

    if args.cmd == "diagnose":
        from . import discovery_engine
        _, inv_spec, studies = load_cycle_inputs(ws, args.investigation)
        result = run_cycle(inv_spec, studies)
        diag = discovery_engine.diagnose(result, inv_spec)
        print(discovery_engine.summarize_diagnosis(diag))
        return 0

    if args.cmd == "suggest":
        _, inv_spec, studies = load_cycle_inputs(ws, args.investigation)
        result = run_cycle(inv_spec, studies)
        print(summarize_suggestions(result["suggestions"]))
        return 0

    if args.cmd == "opportunities":
        from . import discovery_engine
        _, inv_spec, studies = load_cycle_inputs(ws, args.investigation)
        result = run_cycle(inv_spec, studies)
        opps = discovery_engine.opportunities(result, inv_spec)
        print(discovery_engine.summarize_opportunities(opps))
        return 0

    if args.cmd == "execute":
        from . import discovery_engine
        _, inv_spec, studies = load_cycle_inputs(ws, args.investigation)
        plan = discovery_engine.execute_plan(run_cycle(inv_spec, studies), inv_spec)
        print(discovery_engine.summarize_execute_plan(plan))
        if (args.execute or args.autonomous) and plan:
            rec = execute_action(ws, args.investigation, autonomous=args.autonomous)
            print(f"\n[{rec['status']}] {rec['action']} on {rec['source']}: "
                  f"{(rec.get('outcome') or {}).get('detail') or (rec.get('outcome') or {})}")
            if rec.get("status") == "executed" and "frontier_after" in rec:
                print(f"  frontier: {rec['frontier_before']} → {rec['frontier_after']} (re-cranked)")
        return 0

    return 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
