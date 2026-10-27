"""Formal discovery engine — turn the crank on an investigation.

RFC-0005 gives the operational algebra (branch / compose / test / synthesize /
narrate / audit) and the knowledge-clock transition I_{n+1} = T(a_n, I_n, delta_n).
This module makes the CRANK explicit and robust. One turn:

1. PROJECT the cycle (``discover.run_cycle``): verdicts, argument graph, narrative,
   audit gaps, synthesis spine, open calls.
2. FRONTIER: the set of unresolved items, each typed and PRIORITIZED by leverage on
   closure, each carrying the RECOMMENDED operation to resolve it.
3. NEXT: the single highest-leverage item — what to work on now, and how.
4. CLOSURE: is the investigation settled? (every acceptance criterion met, no open
   narrative gap, no unadjudicated challenge.)
5. INVARIANTS: the RFC-0005 validity invariants that every turn must preserve
   (provenance; epistemic separation; counterevidence retention).

A human, an agent, or software EXECUTES the recommended operation (builds the model,
runs it, researches) and records the result with the ``discover`` write ops
(set_verdict / connect / persist / a new study); the engine then re-projects and
advances. The engine is pure and deterministic — same evidence yields the same
frontier — so the crank is reproducible.

Public API
----------
frontier(cycle_result, inv_spec) -> list[dict]
next_action(cycle_result, inv_spec) -> dict | None
closure(cycle_result, inv_spec) -> dict
invariants(cycle_result) -> list[dict]
crank(cycle_result, inv_spec) -> dict          # one combined report
"""
from __future__ import annotations

from .validation import epistemic_separation_violations


# Frontier priorities (higher = more urgent; a closure-blocker outranks a polish item).
_PRIORITY = {
    "unaddressed_criterion": 90,   # an acceptance criterion not yet met — blocks closure
    "open_challenge": 80,          # an alternative/refutation not yet adjudicated
    "narrative_gap": 70,           # an unsupported transition in the reading
    "open_decision": 60,           # an authored decision awaiting a steer
    "divergence": 50,              # authored verdict disagrees with the coded roll-up
    "validation_finding": 45,      # a registered validator (RFC-0007) reported a failing check
    "open_question": 40,           # an unassessed / inconclusive claim
}
# Recommended operation per item kind (the RFC-0005 op that resolves it).
_OP = {
    "unaddressed_criterion": "branch",   # open a study that addresses the criterion
    "open_challenge": "synthesize",      # adjudicate the alternative into a justification
    "narrative_gap": "branch",           # a follow-up study supplying the missing link
    "open_decision": "steer",            # resolve the decision and propagate
    "divergence": "reconcile",           # reconcile authored vs derived verdict
    "validation_finding": "revise",      # act on the validator's recommendation, then resolve
    "open_question": "test",             # evaluate the claim
}
# open_calls kinds map straight onto frontier kinds.
_CALL_KIND = {"narrative_gap": "narrative_gap", "decision": "open_decision",
              "divergence": "divergence", "open_question": "open_question"}

_MET = ("supported", "qualified")


def _resolution_keys(inv_spec: dict) -> set:
    """``(kind, target)`` pairs the investigation has recorded as resolved.

    A resolution is an authored record ``{kind, target, rationale, by?}`` written by
    the op that discharged the item (e.g. an adjudicated challenge, a bridged narrative
    gap, a met criterion) — the artifact's back-reference to the frontier item it closes.
    ``frontier`` consults this one set for every item kind."""
    out: set = set()
    for r in inv_spec.get("resolutions") or []:
        if isinstance(r, dict) and r.get("kind") and r.get("target"):
            out.add((r["kind"], r["target"]))
    return out


def frontier(cycle_result: dict, inv_spec: dict) -> list[dict]:
    """The prioritized set of unresolved items. Each item is
    ``{kind, target, priority, op, rationale}``; the list is sorted by priority
    (descending), ties broken by a stable key so the crank is deterministic."""
    verdicts = (cycle_result.get("knowledge") or {}).get("verdicts") or {}
    edges = (cycle_result.get("argument") or {}).get("edges") or []
    resolved = _resolution_keys(inv_spec)
    items: list[dict] = []
    seen: set[tuple] = set()

    def add(kind, target, rationale):
        key = (kind, target)
        # Uniform resolution: one check discharges a frontier item of ANY kind. An op
        # that produced its artifact records a resolution {kind, target, …}; until then
        # the item is raised. This closes the knowledge-clock loop — the action aₙ a
        # cycle performs feeds the next frontier — for every kind, not just acceptance.
        if key in seen or key in resolved:
            return
        seen.add(key)
        items.append({"kind": kind, "target": target, "priority": _PRIORITY.get(kind, 30),
                      "op": _OP.get(kind, "test"), "rationale": rationale})

    behaviors = (cycle_result.get("knowledge") or {}).get("behaviors") or {}
    # 1. acceptance criteria. A criterion {study, behavior} is MET when its NAMED
    #    behavior's test PASSED — independent of the study's roll-up verdict. This keeps
    #    the two axes (progress ⊥ verdict) orthogonal: an adversarial null control, whose
    #    designed success is a `refuted` verdict AND whose acceptance behavior passed, is a
    #    met criterion, not an open frontier item. With no behavior outcome recorded, it
    #    falls back to the verdict (a non-supported/qualified verdict is unmet).
    for c in inv_spec.get("acceptance_criteria") or []:
        study = c.get("study") if isinstance(c, dict) else (c if isinstance(c, str) else None)
        if not study:
            continue
        behavior = c.get("behavior") if isinstance(c, dict) else None
        beh_result = (behaviors.get(study) or {}).get(behavior) if behavior else None
        if beh_result == "PASS":
            continue  # the named acceptance behavior passed → criterion met
        v = (verdicts.get(study) or {}).get("verdict")
        if v not in _MET:
            add("unaddressed_criterion", study,
                (f"acceptance criterion '{behavior}' on {study} not met "
                 f"(behavior: {beh_result or 'no-run'}, verdict: {v or 'none'})"
                 if behavior else
                 f"acceptance criterion on {study} not met (verdict: {v or 'none'})"))

    # 2. unadjudicated challenge edges (an alternative/refutation left open)
    for e in edges:
        if e.get("type") == "challenge":
            add("open_challenge", e.get("to"),
                f"challenge {e.get('from')} -> {e.get('to')} ({e.get('relation')}) unadjudicated")

    # 3. the derived open calls (narrative gaps, decisions, divergences, open questions)
    for call in cycle_result.get("open_calls") or []:
        kind = _CALL_KIND.get(call.get("kind"))
        if not kind:
            continue
        refs = call.get("refs") or []
        target = refs[0] if refs else (call.get("title") or kind)
        add(kind, target, call.get("title") or "")

    # 4. validator findings (RFC-0007): a registered validator reported a failing
    #    check. Records already surfaced by another path (narrative coherence is
    #    raised as a narrative_gap via open_calls) are skipped so they are not
    #    double-counted; the rest enter the frontier, resolvable like any item.
    for rec in cycle_result.get("validations") or []:
        if not isinstance(rec, dict):
            continue
        # Only frontier-surfacing validators reach the actionable crank; "standing"
        # validators (rigor, band provenance) are feedback, shown elsewhere, and never
        # flood the frontier. (A record with no surface defaults to frontier.)
        if rec.get("surfaces", "frontier") != "frontier":
            continue
        # Only failed/errored records are actionable; an `inconclusive` record is
        # standing feedback (e.g. a rigor WARN) and stays off the frontier.
        if (rec.get("result") or {}).get("execution_status") not in ("failed", "error"):
            continue
        if rec.get("type") == "narrative":
            continue
        findings = rec.get("findings") or []
        add("validation_finding", rec.get("target"),
            f"[{rec.get('type')}/{rec.get('scope')}] "
            + ("; ".join(str(f) for f in findings) if findings else "validation failed"))

    items.sort(key=lambda x: (-x["priority"], str(x["kind"]), str(x["target"])))
    return items


def next_action(cycle_result: dict, inv_spec: dict) -> dict | None:
    """The single highest-leverage unresolved item (or ``None`` when closed)."""
    f = frontier(cycle_result, inv_spec)
    return f[0] if f else None


def closure(cycle_result: dict, inv_spec: dict) -> dict:
    """Is the investigation settled? Closed iff no acceptance criterion is unmet, no
    narrative gap is open, and no challenge is unadjudicated — the machine-checkable
    form of the RFC-0005 closure condition."""
    f = frontier(cycle_result, inv_spec)
    unaddressed = [i["target"] for i in f if i["kind"] == "unaddressed_criterion"]
    gaps = [i for i in f if i["kind"] == "narrative_gap"]
    challenges = [i for i in f if i["kind"] == "open_challenge"]
    return {
        "closed": not unaddressed and not gaps and not challenges,
        "unaddressed_criteria": unaddressed,
        "open_gaps": len(gaps),
        "open_challenges": len(challenges),
        "open_items": len(f),
    }


def invariants(cycle_result: dict) -> list[dict]:
    """Validity-invariant violations to flag each turn (RFC-0005 §"validity invariants").

    - provenance: an assessed claim (supported/qualified/refuted) with no evidence_refs.
    - epistemic_separation (RFC-0007): a validation record whose type establishes
      execution correctness only (structural/computational/visual) yet asserts a
      scientific judgment — a passing check standing in for biological truth.
    """
    out: list[dict] = []
    claims = (cycle_result.get("argument") or {}).get("claims") or {}
    for cid, c in claims.items():
        if not isinstance(c, dict):
            continue
        v = c.get("verdict")
        if v in ("supported", "qualified", "refuted") and not (c.get("evidence_refs") or []):
            out.append({"invariant": "provenance", "target": cid,
                        "detail": f"claim is {v} but traces to no evidence"})
    out.extend(epistemic_separation_violations(cycle_result.get("validations") or []))
    return out


def crank(cycle_result: dict, inv_spec: dict) -> dict:
    """One combined crank report: the frontier, the next action, closure, invariants."""
    return {
        "closure": closure(cycle_result, inv_spec),
        "next_action": next_action(cycle_result, inv_spec),
        "frontier": frontier(cycle_result, inv_spec),
        "invariant_violations": invariants(cycle_result),
    }


def summarize(report: dict) -> str:
    c = report["closure"]
    lines = [
        f"closure: {'CLOSED' if c['closed'] else 'OPEN'}  "
        f"(unaddressed criteria {len(c['unaddressed_criteria'])}, "
        f"open gaps {c['open_gaps']}, open challenges {c['open_challenges']}, "
        f"frontier {c['open_items']})",
    ]
    na = report["next_action"]
    if na:
        lines.append(f"next: [{na['op']}] {na['kind']} on {na['target']}  — {na['rationale']}")
    else:
        lines.append("next: — nothing open; the investigation is settled.")
    inv = report["invariant_violations"]
    if inv:
        lines.append(f"invariant violations: {len(inv)} "
                     f"({', '.join(sorted({v['invariant'] for v in inv}))})")
    lines.append("top frontier:")
    for i in report["frontier"][:8]:
        lines.append(f"  {i['priority']:>3}  [{i['op']:>10}] {i['kind']:<22} {i['target']}")
    return "\n".join(lines)
