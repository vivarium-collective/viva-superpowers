"""The viva-superpowers filler for the AI-drivable discovery cycle.

A *filler* answers one discovery-engine ``GenerationRequest`` by producing a
``GenerationResult`` — the ``$VIVA_FILLER_CMD`` contract: a request JSON on stdin,
a result JSON on stdout (nothing when this filler can't fill the request). The
discovery engine stays pure: it EMITS requests and APPLIES results; the filler is
a consumer that imports ``discovery_engine``, never the reverse.

This is the **deterministic baseline** filler. It fills an ``interpret_finding``
request by templating a factual, run-backed interpretation from the finding's own
computed evidence — its numeric ``evidence.observed`` versus the cited behavior
test's acceptance band. No LLM, no fabricated numbers: it turns auto-filled
numeric evidence into a reviewer-readable statement instead of an empty slot, and
never overwrites an authored interpretation. The AI filler (``claude -p`` with a
fill skill) plugs into the same seam and supersedes this for prose quality.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path


def _find_workspace(start: Path) -> "Path | None":
    p = start.resolve()
    for cand in [p, *p.parents]:
        if (cand / "workspace.yaml").exists():
            return cand
    return None


def _to_float(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def _band_text(test: dict) -> str:
    pf = (test or {}).get("pass_if") or {}
    if "low" in pf and "high" in pf:
        return f"[{pf['low']}, {pf['high']}]"
    if "op" in pf and "value" in pf:
        return f"{pf['op']} {pf['value']}"
    if "threshold" in pf:
        return f"threshold {pf['threshold']}"
    return "the acceptance criterion"


def _passes(observed, pf: dict) -> "bool | None":
    v = _to_float(observed)
    if v is None or not isinstance(pf, dict):
        return None
    if "low" in pf and "high" in pf:
        return pf["low"] <= v <= pf["high"]
    op, val = pf.get("op"), _to_float(pf.get("value"))
    if op and val is not None:
        return {">": v > val, "<": v < val, ">=": v >= val,
                "<=": v <= val, "==": v == val}.get(op)
    thr = _to_float(pf.get("threshold"))
    return (v >= thr) if thr is not None else None


def fill_interpret_finding(request: dict, ws_root: Path) -> "dict | None":
    """Template a run-backed interpretation for ONE eligible finding of the
    request's target study — a finding with a numeric ``evidence.observed`` and a
    cited ``evidence.from_test`` but no authored ``explanation`` yet. Returns a
    GenerationResult dict, or ``None`` when nothing is eligible."""
    from discovery_engine import study_io
    from discovery_engine.investigation_import import studies_dir

    target = str(request.get("target") or "")
    slug = target.split(":", 1)[1] if target.startswith("claim:") else target
    sp = studies_dir(ws_root) / slug / "study.yaml"
    if not sp.exists():
        return None
    spec = study_io.load_yaml_mapping(sp)
    tests = {t.get("name"): t for t in (spec.get("behavior_tests") or []) if isinstance(t, dict)}
    for f in (spec.get("findings") or []):
        if not isinstance(f, dict):
            continue
        ev = f.get("evidence") or {}
        observed, from_test = ev.get("observed"), ev.get("from_test")
        if _to_float(observed) is None or not from_test:
            continue
        if (f.get("explanation") or "").strip():
            continue                            # already interpreted — never clobber authored prose
        test = tests.get(from_test) or {}
        passed = _passes(observed, test.get("pass_if") or {})
        verdict = ("is within" if passed else "is outside") if passed is not None else "was evaluated against"
        measure = ev.get("measure") or (test.get("measure") or {}).get("path") or from_test
        units = f" {ev['units']}" if ev.get("units") else ""
        explanation = (f"The run-backed measurement of {measure} = {observed}{units} {verdict} the "
                       f"acceptance band {_band_text(test)} for test '{from_test}' — a code-graded "
                       f"result from the study's registered run, not an authored value.")
        return {
            "request_id": request.get("id"),
            "artifact": {"study": slug, "finding": f.get("id") or f.get("name"),
                         "explanation": explanation},
            "filler": {"kind": "deterministic", "id": "viva-fill/interpret_finding"},
            "rationale": "templated from the finding's computed evidence (no LLM)",
        }
    return None


_FILLERS = {"interpret_finding": fill_interpret_finding}


def fill(request: dict, ws_root: "Path | str | None" = None) -> "dict | None":
    """Dispatch one GenerationRequest (dict) to the filler for its kind. Resolves
    the workspace from ``ws_root`` or the cwd. Returns a GenerationResult dict or
    ``None`` (kind not handled, or nothing eligible)."""
    ws = Path(ws_root) if ws_root else _find_workspace(Path.cwd())
    if ws is None:
        return None
    fn = _FILLERS.get(request.get("kind"))
    return fn(request, ws) if fn else None


def main(argv=None) -> int:
    """``$VIVA_FILLER_CMD`` entry: GenerationRequest JSON on stdin → GenerationResult
    JSON on stdout (empty output when this filler can't fill the request)."""
    req = json.load(sys.stdin)
    res = fill(req)
    if res is not None:
        json.dump(res, sys.stdout, default=str)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
