"""Canonical verdict vocabulary + projection.

The formalized investigation graph standardizes the several study/card verdict
vocabularies onto ONE canonical vocab. ``canonical_verdict`` projects the coded
study_verdict rollup into that vocab and reconciles it with the authored
``verdict``, never overwriting the author's field and surfacing any divergence.
The result is what gets written to the parallel ``computed_verdict`` slot.

Canonical vocab: ``unassessed | supported | qualified | inconclusive | refuted``.

Pure functions; ``eval``-free; never raises on a malformed/empty spec.
"""
from __future__ import annotations

from viva_superpowers.study_verdict import roll_up_verdict

UNASSESSED = "unassessed"
SUPPORTED = "supported"
QUALIFIED = "qualified"
INCONCLUSIVE = "inconclusive"
REFUTED = "refuted"

CANONICAL = (UNASSESSED, SUPPORTED, QUALIFIED, INCONCLUSIVE, REFUTED)

# study_verdict rollup result -> canonical verdict.
# blocked / not_started carry no scientific verdict yet -> unassessed.
_PROJECT = {
    "passed": SUPPORTED,
    "failed": REFUTED,
    "needs_calibration": QUALIFIED,
    "blocked": UNASSESSED,
    "not_started": UNASSESSED,
}


def project_coded(rollup_result: str) -> str:
    """Project a study_verdict rollup ``result`` into the canonical vocab.

    An unrecognized result is treated as ``unassessed`` (never guess).
    """
    return _PROJECT.get(rollup_result, UNASSESSED)


def canonical_verdict_detail(study_spec: dict) -> dict:
    """Compute the canonical verdict for a study with full provenance.

    Priority: the CODED rollup wins when it carries a verdict; otherwise the
    authored ``verdict`` is used; otherwise ``unassessed``. When both a coded
    and an authored verdict exist and disagree, ``diverges`` is True and the
    coded value is taken (the disagreement is surfaced, not reconciled).

    :returns: ``{verdict, coded, authored, diverges, source}``.
    """
    spec = study_spec if isinstance(study_spec, dict) else {}

    try:
        coded = project_coded((roll_up_verdict(spec) or {}).get("result", ""))
    except Exception:
        coded = UNASSESSED

    authored = spec.get("verdict")
    if authored not in CANONICAL:
        authored = None  # authored uses {supported,qualified,inconclusive,refuted}; null/other -> none

    if coded != UNASSESSED:
        verdict = coded
        source = "coded"
        diverges = authored is not None and authored != coded
    elif authored is not None:
        verdict = authored
        source = "authored"
        diverges = False
    else:
        verdict = UNASSESSED
        source = "none"
        diverges = False

    return {
        "verdict": verdict,
        "coded": coded,
        "authored": authored,
        "diverges": diverges,
        "source": source,
    }


def canonical_verdict(study_spec: dict) -> str:
    """The canonical verdict string for a study (see :func:`canonical_verdict_detail`)."""
    return canonical_verdict_detail(study_spec)["verdict"]
