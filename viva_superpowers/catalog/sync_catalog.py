"""Regenerate the canonical module registry (modules.json) from GitHub.

This is the single source of truth for the dashboard's "available modules"
catalog. Run it to re-curate the list (it overwrites the package resource
``viva_superpowers/catalog/modules.json`` in place):

    python3 -m viva_superpowers.catalog.sync_catalog

Refreshes GitHub-derived metadata for the modules already tracked in
modules.json (matched by their source **repo**, so repo renames don't drop
them), plus any still-``pbg-``-named org repos (stragglers mid-rename) and the
explicitly listed extras (v2ecoli, spatio-flux, viva-munk). Re-emits
modules.json sorted by name.

The module set used to be discovered purely by the ``pbg-`` repo-name prefix.
Now that modules are being renamed to ``viva-*`` — indistinguishable from the
many other ``viva-*`` org repos (docs, apps, investigations) — the tracked set
is sourced from the existing modules.json instead, and the install ``name`` /
import ``package`` are **curator-owned** (preserved across a re-sync, since a
repo's dist name may still lag its repo name during the migration). Other
curator-authored fields (e.g. ``system_dependencies.checks``) are preserved too.

Requires `gh` CLI authenticated against GitHub. To add/remove a module from
the ecosystem registry, re-run this (or hand-edit modules.json) and release
pbg-superpowers — every workspace's dashboard reads it via
``viva_superpowers.catalog.load_registry``. A removed entry simply stops
being an org repo (e.g. pbg-physicell, which never had a backing repo, is
not re-added).
"""
from __future__ import annotations
import json
import re
import subprocess
import sys
from pathlib import Path


ORG = "vivarium-collective"
# Non-pbg-* repos that are genuine process-bigraph extensions (Processes,
# Steps, Types) workspaces install via pyproject + import in composites.
# Listed here because the auto-pull filter is `name.startswith("pbg-")`;
# extension packages without that prefix would otherwise be invisible to
# the catalog. Keep this list tight — workspace-y repos (vEcoli*,
# multiscale-bioprocess, etc.) and infrastructure (bigraph-*, sms-*)
# do NOT belong here.
EXTRAS = ["v2ecoli", "spatio-flux", "viva-munk"]
EXCLUDE = {"pbg-superpowers", "pbg-template", "viva-superpowers", "viva-template"}


def _gh_list_org(org: str) -> list[dict]:
    r = subprocess.run(
        ["gh", "repo", "list", org, "--limit", "200",
         "--json", "name,description,url,defaultBranchRef"],
        capture_output=True, text=True, check=True,
    )
    return json.loads(r.stdout)


def _package_name(repo_name: str) -> str:
    """pbg-cellpack → pbg_cellpack; spatio-flux → spatio_flux; v2ecoli → v2ecoli."""
    return repo_name.replace("-", "_")


def _display_name(repo_name: str) -> str:
    """Viva-branded label shown in the workbench UI, decoupled from the
    still-``pbg-``-named GitHub repos / PyPI packages so installs keep
    resolving against ``name``/``package``/``source`` unchanged.

    ``pbg-cellpack`` → ``viva-cellpack``; already-viva or non-``pbg-`` names
    (``Viva-munk`` → ``viva-munk``, ``spatio-flux``, ``v2ecoli``) pass through
    with only a lower-case normalization of a leading ``Viva``.
    """
    if repo_name.startswith("pbg-"):
        return "viva-" + repo_name[len("pbg-"):]
    if repo_name.lower().startswith("viva"):
        return repo_name[:1].lower() + repo_name[1:]
    return repo_name


_TAG_HINTS = (
    ("whole-cell", "whole-cell"),
    ("ecoli",      "ecoli"),
    ("microbial",  "microbial"),
    ("spatial",    "spatial"),
    ("agent-based", "agent-based"),
    ("multicellular", "multicellular"),
    ("morphogenesis", "morphogenesis"),
    ("cytoskeleton", "cytoskeleton"),
    ("membrane",   "membrane"),
    ("vesicle",    "membrane"),
    ("micelle",    "membrane"),
    ("particle",   "particle"),
    ("reaction-diffusion", "reaction-diffusion"),
    ("rule-based", "rule-based"),
    ("metabolism", "metabolism"),
    ("metabolic",  "metabolism"),
    ("fba",        "fba"),
    ("stochastic", "stochastic"),
    ("sbml",       "sbml"),
    ("antimony",   "sbml"),
    ("ode",        "ode"),
    ("kinetics",   "kinetics"),
    ("kinetic",    "kinetics"),
    ("coarse-grained", "coarse-grained"),
    ("mesoscale",  "mesoscale"),
    ("pde",        "pde"),
    ("finite-volume", "pde"),
    ("cfd",        "cfd"),
    ("bioreactor", "bioreactor"),
    ("lammps",     "lammps"),
    ("bonds",      "md"),
    ("md",         "md"),
    ("molecular dynamics", "md"),
    ("composite",  "composite"),
    ("packing",    "structure"),
    ("nfsim",      "rule-based"),
    ("bionetgen",  "rule-based"),
    ("compucell",  "agent-based"),
    ("v2ecoli",    "ecoli"),
    ("vcell",      "pde"),
    ("yalla",      "agent-based"),
    ("smoldyn",    "stochastic"),
    ("medyan",     "cytoskeleton"),
    ("readdy",     "particle"),
    ("flux",       "metabolism"),
)


def _infer_tags(name: str, description: str | None) -> list[str]:
    """Match tag hints against name + description, using word boundaries to
    avoid false positives (e.g. 'mODEl' wrongly matching 'ode')."""
    text = f"{name} {description or ''}".lower()
    tags: list[str] = []
    for hint, tag in _TAG_HINTS:
        if re.search(rf"\b{re.escape(hint)}\b", text) and tag not in tags:
            tags.append(tag)
    return tags


def _entry(repo: dict) -> dict:
    name = repo["name"]
    ref = (repo.get("defaultBranchRef") or {}).get("name") or "main"
    return {
        "name": name,
        "display_name": _display_name(name),
        "description": (repo.get("description") or "").strip(),
        "source": f"https://github.com/{ORG}/{name}.git",
        "ref": ref,
        "package": _package_name(name),
        "homepage": repo.get("url") or f"https://github.com/{ORG}/{name}",
        "tags": _infer_tags(name, repo.get("description")),
    }


# Fields that this script owns — it overwrites them on every run from the
# GitHub metadata. Any OTHER field on an existing entry is curator-owned and
# must be preserved across a re-sync — otherwise running this script eats
# curation. The install `name` and import `package` are curator-owned (NOT
# here): during the pbg->viva migration a repo's dist/install name may lag its
# repo name, so they must not be clobbered by the repo name. A brand-new entry
# still gets both from `_entry` (keyed off the repo name) as a sensible default.
_AUTO_KEYS = frozenset({
    "display_name", "description", "source", "ref", "homepage", "tags",
})


def _repo_of(entry: dict) -> str:
    """The GitHub repo basename backing an entry, from its `source` URL
    (falling back to `name`). This is the stable key across a repo rename."""
    src = (entry.get("source") or "").rstrip("/")
    if src.endswith(".git"):
        src = src[: -len(".git")]
    return src.rsplit("/", 1)[-1] if src else (entry.get("name") or "")


def _merge_extras(fresh: dict, existing: dict | None) -> dict:
    """Return `fresh` augmented with any non-auto fields from `existing`.

    Auto fields (the ones derived from GitHub on each run) always come from
    `fresh`. Curator-authored fields like `checks` survive a re-sync. New
    entries (no existing) pass through unchanged.
    """
    if not existing:
        return fresh
    out = dict(fresh)
    for key, value in existing.items():
        if key not in _AUTO_KEYS:
            out[key] = value
    return out


def main() -> int:
    repos = _gh_list_org(ORG)
    by_name = {r["name"]: r for r in repos}

    out_path = Path(__file__).parent / "modules.json"
    existing: list[dict] = []
    if out_path.is_file():
        try:
            existing = [
                e for e in json.loads(out_path.read_text(encoding="utf-8"))
                if isinstance(e, dict) and e.get("name")
            ]
        except (json.JSONDecodeError, OSError):
            existing = []
    existing_by_repo = {_repo_of(e): e for e in existing}

    # The module set = repos we already track (keyed by their backing repo, so
    # a rename doesn't drop them) + the explicit extras. We no longer discover
    # modules by a `pbg-`/`viva-` name prefix: modules are being renamed to
    # `viva-*` and are then indistinguishable from the many other `viva-*` org
    # repos (docs, apps, investigations), so a prefix scan would pull in
    # non-modules. New modules are added by hand-editing modules.json (or via
    # EXTRAS); this script refreshes GitHub metadata for the curated set.
    repo_names: set[str] = set(existing_by_repo)
    repo_names |= set(EXTRAS)
    repo_names -= EXCLUDE

    out: list[dict] = []
    missing: list[str] = []
    for repo in sorted(repo_names):
        gh = by_name.get(repo)
        existing_entry = existing_by_repo.get(repo)
        if gh is None:
            # Repo not in the org listing (e.g. deleted). Keep the existing
            # curated entry verbatim rather than silently dropping it.
            if existing_entry is not None:
                out.append(existing_entry)
                missing.append(repo)
            else:
                print(f"warning: '{repo}' not found on {ORG} and not in catalog", file=sys.stderr)
            continue
        out.append(_merge_extras(_entry(gh), existing_entry))
    out.sort(key=lambda e: e["name"].lower())

    out_path.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n")
    print(f"wrote {len(out)} entries to {out_path}")
    if missing:
        print(f"  kept {len(missing)} entries whose repo is not in the org listing "
              f"(archived/renamed/deleted): {', '.join(missing)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
