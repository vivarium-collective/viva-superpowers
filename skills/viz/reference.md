# /viz — figure-design reference

Reference-grade design guidance for `/viz`. The SKILL.md body carries the
operational contract (output location, template, constraints, steps); this file
holds the "which chart, made legible" judgment an author applies when deciding
*what* to draw. The Step/render-path mechanics live separately in
[`docs/conventions/visualizations.md`](../../docs/conventions/visualizations.md).

## Time-series & multi-regime conventions

Reviewers repeatedly ask for these — apply them by default so they don't have to:

- **Interpretable axis units.** Put time in real units (minutes/hours), not raw
  ticks/steps. If the time signal resets per segment (e.g. a per-generation clock),
  **stitch it into one continuous axis** rather than overlaying segments.
- **Mark meaningful boundaries.** Draw light reference lines at the events/regime
  changes a reader needs (cell divisions, interventions, phase transitions) and
  label them once — don't rely on stray gridlines.
- **Focus on the informative window.** When early transients/warm-up distort the
  reading, plot the steady-state window (or per-regime average) and say so in the
  caption, instead of letting the transient dominate the scale.

Use a consistent, distinguishable palette across a study's charts — pick a small
set of colors up front and reuse them by series/condition.

## Make it creative, interactive, and informative

Treat every request as an invitation to design the *best* view of the data, not
the most literal one. Before writing, ask: "what is the one thing this figure
should make undeniable?" Then choose the form that makes it undeniable. A bare
line of one observable vs time almost never clears that bar.

**Default to interactivity (Plotly).** Hover tooltips, a toggleable legend (click
a trace to isolate it), zoom/pan, and — where they fit — range sliders, faceted
small multiples, dropdown/slider controls to switch variable or condition, and
animation frames over time or generation. A reviewer who can *explore* the data
trusts the finding more than one handed a frozen PNG. Reserve matplotlib for
genuinely static / 3D / paper-figure needs.

**Pick the chart type that fits the question — go beyond scatter-vs-time:**

| The finding is about… | Consider |
|---|---|
| A relationship between two dynamic variables | phase portrait / 2D trajectory with time as color |
| Many observables at once | faceted small multiples, or a normalized overlay with a toggleable legend |
| Flows / mass balance / exchange | Sankey or a stacked area of in/out fluxes |
| A grid of conditions × metrics (e.g. report-card axes) | heatmap with a diverging colorscale + hover detail |
| A part-of-whole inventory (e.g. gaps by axis) | sunburst / treemap / grouped bar |
| Distributions across seeds/cells | violin / box / ridgeline, not just a mean line |
| A sweep over a parameter | a line per level with a slider, or a surface |
| Population vs single lineage | shaded variance band + representative trace |

**Make it informative, not just pretty.** Always: a descriptive title that states
the takeaway (not just "cell_mass"), axis labels *with units*, a legend, and —
where it sharpens the reading — reference lines/annotations for thresholds,
targets, division events, or published comparison values. Add a one-line caption
in the HTML so the figure is self-explanatory out of context. Color with intent
(consistent palette across a study; a diverging scale only for signed/centered
data). Downsample very long trajectories to ~500–1000 points so the file stays
light without losing the shape.

**Make it legible — encode the interpretable thing, not a raw number.** A figure
that's informative in principle still fails if the reader can't decode it at a
glance. Hard-won rules:

- **Never clamp a wide-range metric to a floor/ceiling as the bar height.**
  Plotting e.g. median R² clamped to −1 collapses every bad group to one identical
  bar — the reader learns nothing and the value labels collide with the axis. Pick
  a *bounded, monotonic* proxy the reader intuitively understands (e.g. "fraction
  of columns with R² > 0.5", a 0–100 % bar), or a symlog axis, and carry the raw
  value as a text annotation / hover so nothing is hidden. The bar should answer
  the question directly ("how much of this is good?"), not encode a statistic whose
  range is pathological.
- **Keep labels and annotations inside the frame.** `textposition="outside"` on a
  bar that runs to the axis edge (or a downward/negative bar) clips the label.
  Leave axis headroom (e.g. range `[0, 1.18]`) and position labels where they stay
  visible.
- **One figure, one reading.** If you have to squint to tell categories or series
  apart, the encoding is wrong — change the metric, scale, or chart type, don't
  just add a legend.
- **Honest scales.** A log/clamped/normalized axis must not *hide* that values are
  extreme — surface the true magnitude in text or hover so the figure can't be
  misread as better (or worse) than it is.

**Propose, don't just fulfill.** If the literal request would produce a weak
figure, build the better one and say why in your success message ("requested a
cell_mass line; rendered it as a multi-gen accumulation with division markers and
a Beulig target band, which makes the plateau visible"). If you see a second view
that would strengthen the same finding, mention it so the user/reviewer can ask
for it — or, when it's cheap, just build it too.
