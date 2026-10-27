# Turning the discovery crank

The **discovery crank** is the deterministic engine that tells you *which* gap in
an investigation is load-bearing and *how* to close it. It is the formal version of
"find the one gap that most weakens the headline claim" — instead of ranking gaps by
hand, you let the engine compute the ranked frontier, work the top item, record the
result, and re-crank.

- **Engine (pure, read-only):** [`viva_superpowers/discovery_engine.py`](../../viva_superpowers/discovery_engine.py)
  — `frontier()`, `next_action()`, `closure()`, `invariants()`, `crank()`. Its module
  docstring is the contract.
- **Write/wire CLI:** [`viva_superpowers/discover.py`](../../viva_superpowers/discover.py)
  — the verbs that execute ops and record their results.
- **Spec:** [`docs/rfcs/RFC-0005-narrative-and-argument-layer.md`](../rfcs/RFC-0005-narrative-and-argument-layer.md)
  — the operational algebra (branch / compose / test / synthesize / narrate / audit)
  and the knowledge-clock transition `I_{n+1} = T(aₙ, Iₙ, δₙ)`.

> Not to be confused with [`docs/conventions/discovery.md`](./discovery.md), which is
> bigraph-schema *package* auto-discovery — an unrelated mechanism.

## One turn of the crank

The engine is **pure and deterministic**: the same evidence yields the same frontier,
so a crank is reproducible. One turn:

1. **PROJECT** the cycle — derive verdicts → the claim→claim argument graph → the
   narrative → the audit of unsupported transitions → the synthesis spine → the open calls.
2. **FRONTIER** — the set of unresolved items, each `{kind, target, priority, op, rationale}`,
   sorted by leverage on closure.
3. **NEXT** — the single highest-priority item: what to work on now, and which op resolves it.
4. **CLOSURE** — settled iff every acceptance criterion is met, no narrative gap is open,
   and no challenge is unadjudicated.
5. **INVARIANTS** — the RFC-0005 validity invariants (provenance; epistemic separation;
   counterevidence retention) every turn must preserve.

A human or agent **executes** the recommended op (builds a model, runs a study,
adjudicates, authors an edge), **records** the result with a `discover` write verb, and
the engine **re-projects** and advances. The crank does not do the science; it points at it.

## The entrypoint

```bash
python -m viva_superpowers.discover --workspace <WS> crank <investigation-slug>
```

`crank` prints the closure line, the single next action, and the top of the frontier:

```
closure: OPEN  (unaddressed criteria 0, open gaps 1, open challenges 1, frontier 24)
next: [synthesize] open_challenge on claim:og-self-maintaining-concentrated  — edge … unadjudicated
top frontier:
   80  [synthesize] open_challenge         claim:og-self-maintaining-concentrated
   70  [    branch] narrative_gap          claim:og-precursor-pool → og-spatial-concentration
   60  [     steer] open_decision          publication-scope
   …
```

### All verbs

| Verb | Does |
|---|---|
| `crank <inv>` | frontier + next action + closure (read-only) — **the one you run most** |
| `diagnose <inv>` | **why** the cycle is/isn't progressing — productivity-bottleneck flags (read-only) |
| `status <inv>` | project one cycle, print the summary, no write |
| `cycle <inv> [--no-write]` | run + persist one cycle as a regenerable `knowledge_cycle` cache |
| `set-verdict <study> <verdict> [--rationale …]` | author a canonical verdict (`supported`/`qualified`/`inconclusive`/`refuted`/`unassessed`) |
| `relate <downstream> <upstream> --relation <rel>` | author one epistemic edge (`builds-on`/`tests`/`refutes`/`alternative-to`/`motivates`) |
| `connect <inv> --relation builds-on` | enrich every bare prerequisite across the investigation |
| `resolve <inv> <kind> <target> --rationale "…" [--by study#finding]` | record a resolution that **discharges** a frontier item |

## Frontier kinds → priority → op → how you actually close it

The crank recommends an `op`; each op maps to a concrete executor you already have.
Work the highest priority first.

| Kind (priority) | `op` | Execute it with | Then record |
|---|---|---|---|
| `unaddressed_criterion` (90) | `branch` | open a study that addresses the criterion — `/viva-study propose-followup` + `seed-from-followup`, or add a member via `/viva-investigation` | the study's verdict (`set-verdict`) — a met behavior auto-discharges the criterion (PR #360) |
| `open_challenge` (80) | `synthesize` | adjudicate the alternative/refutation into a justification — author a finding with `/viva-study findings` | `resolve <inv> open_challenge <target> --rationale … --by <study>#<finding>` |
| `narrative_gap` (70) — **edge exists but bare** (a `parent_studies` prerequisite with a `condition` only, no `relation` facet) | `branch` *(mislabeled)* | **don't seed a study** — author the epistemic relation on the *existing* edge: `connect <inv> --relation builds-on` (bulk) or `relate <downstream> <upstream> --relation <rel>` (one edge). A supporting relation closes the gap outright | re-crank; a now-supported transition drops the gap. `resolve` only if you intend to document a non-supporting (e.g. `tests`) continuity |
| `narrative_gap` (70) — **no edge at all** (the transition is genuinely unsupported) | `branch` | supply the missing link — a bridging study (`/viva-study propose-followup` + `seed-from-followup`) | `resolve <inv> narrative_gap <target> --rationale … --by <study>` |
| `open_decision` (60) | `steer` | **the expert decides** — this is the crank's natural hand-back point | resolve the `decisions_needed` in the study (`/viva-study set-conclusion`), then `resolve` |
| `divergence` (50) | `reconcile` | reconcile the authored verdict against the derived roll-up — `/viva-investigation reconcile` + `/viva-study set-verdicts` | the reconciled verdict |
| `open_question` (40) | `test` | evaluate the claim — run/evaluate the study (`/viva-study`) | the outcome (`set-verdict`) |

`_MET` verdicts are `("supported", "qualified")` — a **refuted null control** counts as
*met*, because the engine tracks the criterion's named *behavior* outcome, not the
verdict sign (PR #360). Don't branch a new study to "fix" a null control that did its job.

> **The `op` label is advisory, not a command.** It names the RFC-0005 operation kind,
> not the exact executor — read the `target` before acting. The sharpest case is the
> `narrative_gap` split above: the engine labels it `branch`, but when the edge already
> exists and is merely unlabeled, the real fix is `connect`/`relate` (author the
> relation), and seeding a study would fabricate a link that doesn't belong. When a
> whole frontier is one kind, suspect a systematic cause (e.g. every prerequisite edge is
> bare) before working the items one by one.

> **What `connect` actually reaches today (known limitation).** `connect`/`relate`
> enrich only **`pipeline_gate.prerequisites[]`** entries that are already present but
> bare. The narrative reader (`relations.study_relations`) *also* derives edges from
> `parent_studies[]`, so a dependency expressed **only** in `parent_studies` (no
> `pipeline_gate.prerequisites` entry) is invisible to `connect` and its gap will **not**
> close via the recommended op — enrich that edge by hand (`relate <downstream>
> <upstream>`, which appends the canonical prerequisite) until the engine scans both
> fields. So on a real wide DAG, one `connect` clears the prerequisites-stored bare edges
> but leaves parent_studies-only edges and any genuinely-absent edges (real `branch`
> work) behind — re-crank and read the residual rather than assuming zero. Two further
> caveats: `connect --relation builds-on` applies one relation to every bare edge, so
> check none of them are really `tests`/`refutes`/`motivates`; and `connect` currently
> persists via a non-comment-preserving writer, so it reflows the file and drops YAML
> comments. (The toposort-adjacency false positives this detector *used* to emit are
> fixed as of #362 — if you still see sibling-adjacency gaps, your `viva_superpowers` is
> pre-#362; refresh it.)

## What converges, and when to stop

- **Monotone progress.** A **resolution** is an authored record `{kind, target, rationale, by?}`
  the frontier consults for *every* kind; discharging an item drops it and surfaces the next,
  and a resolved item never re-opens. The uniform-resolution mechanism (PR #361) is what makes
  executing the recommended op actually move closure.
- **CLOSED** = no `unaddressed_criterion`, no `narrative_gap`, no `open_challenge`.
  The three lower-priority kinds (`open_decision`, `divergence`, `open_question`) do **not**
  block closure.
- **Stop / hand back** when CLOSED and the only items left are `open_decision` (`steer`) —
  genuine expert calls the crank cannot and should not make for you (publication scope,
  rule-set scope, architecture choices). `divergence` and `open_question` are still
  agent-actionable (reconcile, test) — clear those before handing back.

## Diagnose — why the cycle is (not) progressing

`CLOSED` means the argument is internally settled; it does **not** mean maximum value
was extracted. `discover diagnose <inv>` classifies the residual state into
productivity-bottleneck flags (after the *Perfect Discovery Engine* paper's Table 2),
each with its evidence and the next intervention — computed from the cycle data, no
oracle needed:

- **`task_saturated`** — CLOSED with an empty frontier; genuinely done.
- **`input_limited`** — the frontier is dominated by `steer`/`open_decision` items; the
  investigation is waiting on expert priors/data, not more planning.
- **`planner_limited`** — a large cluster of same-priority actionable items the crank can
  only order by id (no value signal); it can't tell you which to do first.
- **`validation_limited`** — low validator pass-rate / many ungrounded claims (uncited
  bands, unbacked verdicts).
- **`capability_limited`** — a validator errored (a check couldn't run).

The flags are not exclusive. A "CLOSED, frontier 22" investigation routinely diagnoses as
`input_limited` + `planner_limited` + `validation_limited` at once — the real state the
bare closure line hides.

## Preconditions (checklist)

1. **The engine must be importable.** A workspace's own `.venv` often carries a **stale**
   `viva_superpowers` that predates the discover modules. Check:
   ```bash
   <WS>/.venv/bin/python -c "import viva_superpowers, pathlib as p; \
     d=p.Path(viva_superpowers.__file__).parent; \
     print('engine present:', (d/'discover.py').exists() and (d/'discovery_engine.py').exists())"
   ```
   If `False`: refresh the install (`uv pip install -U` the superpowers git `main` into that
   venv), or shadow a checkout that has it via `PYTHONPATH=<superpowers-checkout> <WS>/.venv/bin/python -m viva_superpowers.discover …`.
2. If a crank dies with `TypeError: '>' not supported between instances of 'str' and 'float'`,
   the installed `viva_workspace.canonical_run` is mixing run-timestamp types — shadow a
   fixed `viva-workspace` checkout on `PYTHONPATH` alongside superpowers.
