# Repo archetypes

Every repo is one of three archetypes. The deciding question is **what other repos depend on
this one FOR.**

| Archetype | Depended on for | Design goal | Core rule |
|---|---|---|---|
| `simulator` | compute (reused engines/composites) | general, config-driven, stable contract | no studies/investigations |
| `workspace` | knowledge (studies/investigations) | clean science that PINS simulators | no vendored engine code |
| `showcase`  | neither — self-contained demonstration | show a capability next to its code | deliberate sim+demo; must still PIN its sims |

## Declare it

Declare the archetype in `pyproject.toml`, so it is a decision rather than an inference that drifts:

```toml
[tool.viva]
kind = "simulator"   # or "workspace" | "showcase"
```

## The rules (enforced by `viva_superpowers.package_audit`)

- **Declared, not inferred.** A repo with no `[tool.viva] kind` is flagged. The catalog can infer a
  kind from counts, but inference drifts — a simulator that gains one study flips to workspace.
  Declaring fixes the archetype.
- **Purity.** A `simulator` carrying studies, or a `workspace` that binds a raw engine (vendoring
  instead of pinning a wrapper), is flagged. `showcase` is the one sanctioned sim+demo combination.
- **Reuse pressure.** A repo reused by >= 2 others must be a pure `simulator` — reuse forces purity;
  studies would drag it toward workspace classification and coupling. (That is why viva-tellurium,
  reused by 9, could not stay a workspace.)

## Separate by default, combine deliberately, never by accident

The separation (pure simulator vs pure workspace) is the default: it protects reuse and keeps the
knowledge layer clean. Combine into a `showcase` only when demonstration is the point and the repo
is not reused for compute. The failure mode these checks prevent is *accidental* combination — a
reused provider that silently accumulated studies.

Run it: `python -m viva_superpowers.package_audit <repo-path-or-name>`
