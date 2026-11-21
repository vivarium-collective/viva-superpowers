# /report — worked example

A reference-grade walkthrough of a Pass A finding cascade, kept out of the SKILL
body. The checks that produce it (A1–A8) are specified in
[`SKILL.md`](SKILL.md); this is what their output looks like end-to-end.

## Example Pass A finding cascade (from a recent session)

```
$ /report

== Pass A: reviewer-readiness audit ==
  blocking:  0
  warning:   2
  info:      1

[warning] verdict→chart mismatch:
  investigations/multiscale-bioprocess/investigation.yaml:354
  cites .../charts/00_preliminary_v2ecoli_vs_beulig_gap.svg as primary,
  but that chart is listed in
  studies/mbp-05-palsson-benchmark/study.yaml.preliminary_findings.companion_charts.
  Recommend: promote .../charts/02_v2ecoli_vs_beulig_batch_actual.svg (the
  load-bearing chart per the same study yaml) and demote 00 to a
  companion_chart link in the verdict.

[warning] numerical drift:
  Verdict says "Beulig 50-80 gDW/L batch-phase endpoint".
  Chart 02's meta.json interpretation says "Beulig batch peak ≈ 9.6 g/L".
  Recommend: update the verdict line to "9.6 g/L peak (batch); the
  50-80 g/L is the fed-batch endpoint."

[info] 7 commits ahead of origin/main; last:
  decefdc feat(mbp-05): plateau-diagnostic chart 02 from 175-min salvaged trajectory
  395fc94 doc(mbp-05): correct preliminary finding to Beulig batch peak 9.6 g/L
  ...

Suggested follow-ups before sending to reviewer:
  1. Run cpa=1e9 with --no-single-daughters for one generation
     — would let chart 02 show "both daughters accumulates while single
     plateaus" empirically (currently chart only shows the single side).
     Effort: ~10 min sim + 5 min chart re-render.
  2. Resolve "mbp-03 entry into Build still gated by upstream PR" in
     decisions_needed — git log --grep "pbg-bioreactor-transport-fork"
     shows no movement; either remove the decision or update it to "still
     gated as of <date>".
     Effort: single-line edit.
  3. mbp-04..06 still phase=Design; chart panels render empty. Consider
     either rolling them into a "Planned next" section of the verdict OR
     adding a sentence per study about its status.
     Effort: single-file edit.

Render anyway? (Pass B and render are next.)
```

Each finding gives the reviewer-facing surface, the exact YAML location, and the
proposed fix. The suggested follow-ups distinguish "you can do this in five
minutes" from "blocked on someone else."
