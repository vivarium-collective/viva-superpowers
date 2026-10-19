"""The three graph families, named explicitly (RFC-0004 §2).

One compositional substrate, three distinct graph semantics that must never be
silently interchanged:

- ``E_sci``  — scientific Study↔Study edges (builds_on / tests / motivates /
  alternative_to, + the parent_studies relations).
- ``E_evid`` — evidence→claim relations.
- ``E_org``  — organizational: Study member_of Concept (+ Concept part_of).
- ``E_prov`` — provenance: run/finding generation, attribution, supersession.

classify_edges derives all four from the existing investigation + study fields
(ephemeral, like the linkage index). A process wire is NOT an E_sci edge; Concept
membership is NOT a dynamical coupling.
"""
from __future__ import annotations


def classify_edges(inv_spec: dict, studies_by_slug: dict) -> dict:
    """Derive the four edge families from an investigation + its studies."""
    E_sci: list[dict] = []
    E_evid: list[dict] = []
    E_org: list[dict] = []
    E_prov: list[dict] = []

    # Organizational: Study member_of Concept.
    for c in (inv_spec.get("concepts") or []):
        cid = c.get("id")
        if not cid:
            continue
        for m in (c.get("member_studies") or []):
            E_org.append({"from": m, "to": cid, "kind": "member_of"})

    # Scientific + provenance, from each study.
    for slug, spec in (studies_by_slug or {}).items():
        if not isinstance(spec, dict):
            continue
        for p in (spec.get("parent_studies") or []):
            src = p.get("study")
            if src:
                E_sci.append({"from": src, "to": slug, "kind": p.get("relation") or "builds_on"})
        for src in (spec.get("builds_on") or []):
            E_sci.append({"from": src, "to": slug, "kind": "builds_on"})
        for f in (spec.get("findings") or []):
            prov = f.get("provenance") or {}
            for rid in (prov.get("run_ids") or []):
                E_prov.append({"from": rid, "to": f.get("id") or slug, "kind": "generated_by"})
            # evidence→claim: a finding supports/addresses a proposition
            if f.get("supports"):
                E_evid.append({"from": f.get("id") or slug, "to": f["supports"], "kind": "supports"})

    return {"E_sci": E_sci, "E_evid": E_evid, "E_org": E_org, "E_prov": E_prov}
