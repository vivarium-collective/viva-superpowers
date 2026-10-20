"""Resolve a study's latest-run emitted observables.

The study↔composite face reconciliation (P3) checks a study's declared
``contract.face`` against what its simulation actually produces — which is the
set of *observables* the latest run emitted, read via
:class:`viva_emitters.RunReader`.

Best-effort throughout: a study with no run, a registry without an
``emitter_path``, or an unreadable emitter all yield ``None`` rather than
raising, so a report lint never breaks on a missing or malformed run.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Optional, Set


def _study_dir(study_spec: dict, ws_root) -> Optional[Path]:
    slug = (study_spec or {}).get("slug") or (study_spec or {}).get("name")
    if not slug:
        return None
    try:
        from viva_superpowers.workspace_paths import study_dir
        return Path(study_dir(ws_root, slug))
    except Exception:  # noqa: BLE001 - fall back to the conventional layout
        candidate = Path(ws_root) / "workspace" / "studies" / slug
        return candidate if candidate.is_dir() else None


def _latest_run_store(study_dir: Path) -> Optional[Path]:
    """The emitter store of the study's latest run.

    Prefers the run registry's ``emitter_path``; falls back to the newest run
    artifact under ``canonical-runs/`` / ``sims/`` (``run.db`` first, then a run
    directory for parquet/xarray backends). ``None`` when nothing is found.
    """
    try:
        from viva_superpowers.run_registry import latest_run
        row = latest_run(study_dir / "runs.db") or {}
        emitter_path = row.get("emitter_path")
        if emitter_path:
            path = Path(emitter_path)
            if not path.is_absolute():
                path = study_dir / path
            if path.exists():
                return path
    except Exception:  # noqa: BLE001 - registry missing/broken → fall through
        pass

    dbs = []
    dirs = []
    for parent in ("canonical-runs", "sims"):
        base = study_dir / parent
        if not base.is_dir():
            continue
        dbs.extend(base.glob("*/run.db"))
        dirs.extend(child for child in base.glob("*") if child.is_dir())
    if dbs:
        return max(dbs, key=lambda p: p.stat().st_mtime)
    if dirs:
        return max(dirs, key=lambda p: p.stat().st_mtime)
    return None


def study_run_observables(study_spec: dict, ws_root) -> Optional[Set[str]]:
    """The emitted observable names of the study's latest run, or ``None``.

    ``None`` when the study has no resolvable run or the emitter can't be read.
    """
    try:
        from viva_emitters import RunReader

        study_dir = _study_dir(study_spec, ws_root)
        if study_dir is None:
            return None
        store = _latest_run_store(study_dir)
        if store is None:
            return None
        observables = RunReader.open(str(store)).observables()
        return set(observables) if observables else None
    except Exception:  # noqa: BLE001 - best-effort: an unreadable run yields None
        return None
