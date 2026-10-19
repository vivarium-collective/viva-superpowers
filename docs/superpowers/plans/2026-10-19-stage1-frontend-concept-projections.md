# Stage 1 Frontend — Concept Projections Plan

> Companion to `2026-10-19-investigation-graph-formalization.md` (Stage 1). The
> backend (`GET /api/concept-overlay` + `DataSource.loadConceptOverlay`) is done
> and committed; this plan covers the §11 visual projections. Unlike Stage 0 /
> the backend, the render tasks are **verified with the app running** (screenshots
> against a genesis workspace that carries `plan_gates`), not by pytest alone.

**Goal:** Let a reviewer toggle the investigation graph between ~13 Concept-level
units and the detailed Study graph — the same underlying record, two resolutions —
and read the investigation as Graph / Narrative / History peer projections (§11).

**Spec:** PDF §11 (Graph projection & interaction semantics), §11.5 (node design at
two resolutions), §11.8 (narrative + history peers), §11.9 (visual semantics).

**Backend already in place:** `GET /api/concept-overlay?investigation=<slug>` →
`{investigation, concepts[], study_verdicts{slug→{verdict,coded,authored,diverges,source}}, diverges[]}`.
`DataSource.loadConceptOverlay(slug)` (live + snapshot-aware URL). Files to touch:
`static/graph-panel.js` (the panel + view toggle), `static/aig-graph.js` (the
renderer), `static/data-source.js` (done), `publish.py` (bake), `templates/`.

## Global constraints
- **Additive / non-destructive to the record.** Expand/collapse and view switching
  change *projection only* (§7.2, §11); they never mutate studies or the DAG.
- **Degrade in the static bundle.** Every new view must render from the baked
  `api/concept-overlay/<slug>.json` (snapshot mode) exactly as from the live route,
  and show the plain Study graph when the overlay is empty (legacy investigations,
  or `viva_superpowers` absent).
- **Visual semantics (§11.9), preserve existing:** edge styles builds_on (blue
  solid) / tests (purple dashed) / motivates (orange mixed dash) / alternative_to
  (gray dashed); keep the existing progress + verdict symbols; show evidence
  maturity compactly WITHOUT implying demonstration/mechanistic/calibrated form one
  quality scale.
- **Collapsed-edge rule (§11.1):** an aggregate Concept→Concept edge is warranted
  when ≥1 constituent Study edge connects the memberships; its label is a
  projection, and the underlying Study edges stay inspectable (drill-down). Never
  imply every member shares the relationship.

## Tasks

### Task 1 — Publish bake (pytest-verifiable)
Bake `api/concept-overlay/<slug>.json` for each investigation in `publish.py`,
mirroring how per-investigation inputs/`needs-attention` are baked (call
`report_views.build_concept_overlay(ws, investigation=slug)` and write the body).
- Test: extend the publish test that asserts per-investigation json files exist →
  assert `api/concept-overlay/<slug>.json` is written and parses to the overlay shape.
- This closes the snapshot path `DataSource.loadConceptOverlay` already points at.

### Task 2 — View toggle in `graph-panel.js` (app-verified)
Add a segmented control: **Concept ▸ Study ▸ Narrative ▸ History** (Graph is the
Concept/Study pair at two resolutions; Narrative + History are peer projections,
§11.8). Default to Concept when an overlay exists, else Study. Persist the choice
per investigation in `localStorage` (try/catch). Switching re-renders from the
same loaded data — no refetch of studies.

### Task 3 — Concept nodes + expand/collapse in `aig-graph.js` (app-verified)
Render each Concept (§11.5) as a restrained container node: title, key question,
member count, principal qualified assessment (the Concept `assessment.verdict`),
and an expand affordance. Expand reveals the constituent Study nodes (existing
claim-chain render) with their four edge types retained; collapse aggregates
external links per the collapsed-edge rule and keeps drill-down. A shared Study
appears under multiple Concepts without duplicating its identity.

### Task 4 — Verdict + divergence surfacing (app-verified)
On each Study node, show the canonical `study_verdicts[slug].verdict`; when
`diverges` is true, render the §-divergence badge (authored vs coded both visible),
reusing the existing `diverges_from_authored` red-headline treatment.

### Task 5 — Narrative + History projections (app-verified)
Narrative: ordered Concept syntheses + contradictions + open questions, each line
linked to its member studies (§11.8). History: timestamped graph/consolidation
revisions. Both are projections of the same records; the viewer must never conflate
narrative order with dependency order.

## Verification
Launch the workbench against a genesis worktree whose investigation carries
`plan_gates` (A1/A2/B/C/D/E) with `PYTHONPATH=<viva-superpowers dev worktree>` so
`concept_overlay` resolves, then screenshot: (a) Concept view shows 6 Concept
nodes; (b) expand C reveals og-self-compartmentation; (c) a divergent study shows
the badge; (d) snapshot bundle renders identically. Use the `run` skill to drive it.

## Status
- DONE: `DataSource.loadConceptOverlay` + `_conceptOverlayUrl` (data-source.js, syntax-checked).
- NEXT: Task 1 (publish bake, pytest) → Tasks 2–5 (render, app-verified).
