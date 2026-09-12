"""Cross-repo core composition helpers for the uniform ``build_core`` convention.

The convention every viva-/pbg- repo follows: its ``build_core(core=None)``
composes the cores of its imported repos (inheriting their registered
processes/types), then registers THIS repo's own types/processes/composites —
so a downstream importer gets everything by calling this repo's ``build_core``.

Two helpers make that turnkey:

- :func:`register_package_processes` — register every process-bigraph-native
  process/step class in a package as a first-class, browsable Registry entry.
  Composites that INSTANTIATE processes directly (rather than referencing them
  by a registered address) never enter the core's name registry, so those
  processes are invisible in the dashboard Registry without this.
- :func:`compose_import_cores` — call each imported repo's ``build_core(core)``
  so its registrations land on the shared core.
"""

from __future__ import annotations

import importlib
import inspect
import pkgutil
from typing import Iterable


def register_package_processes(core, package: str, *, recurse: bool = False) -> int:
    """Register every process-bigraph-native process/step class defined in the
    top-level modules of ``package`` into ``core`` (keyed by class name).

    Filters to real ``process_bigraph.Process`` / ``Step`` subclasses, so
    vivarium-core Steps and unrelated classes are skipped. Best-effort +
    idempotent: a module that fails to import, or a class that fails to register,
    is skipped — never fatal to ``build_core``. Subpackages are not descended
    into unless ``recurse=True`` (kept off by default so a heavy reconstruction
    subpackage isn't imported just to enumerate processes). Returns the count.

    Example::

        from viva_superpowers.core_compose import register_package_processes
        register_package_processes(core, "my_pkg.processes")
    """
    import process_bigraph as _pb

    try:
        pkg = importlib.import_module(package)
    except Exception:
        return 0
    n = 0
    for modinfo in pkgutil.iter_modules(getattr(pkg, "__path__", [])):
        if modinfo.ispkg and not recurse:
            continue
        try:
            mod = importlib.import_module(f"{package}.{modinfo.name}")
        except Exception:
            continue
        for name, obj in vars(mod).items():
            if not (inspect.isclass(obj) and obj.__module__ == mod.__name__):
                continue
            if obj in (_pb.Process, _pb.Step) or not issubclass(obj, (_pb.Process, _pb.Step)):
                continue
            try:
                core.register_link(name, obj)
                n += 1
            except Exception:
                pass
    return n


def compose_import_cores(core, modules: Iterable[str]) -> list[str]:
    """Compose imported repos' cores onto ``core``.

    For each module name in ``modules`` that exposes a ``build_core`` callable,
    call ``build_core(core)`` so its registrations (processes/types) land on the
    shared core. Best-effort: a module that can't be imported, or whose
    ``build_core`` doesn't accept a core argument / raises, is skipped. Returns
    the list of module names successfully composed.

    Example::

        compose_import_cores(core, ["viva_munk", "v2ecoli.core"])
    """
    composed: list[str] = []
    for name in modules:
        try:
            mod = importlib.import_module(name)
            bc = getattr(mod, "build_core", None)
            if bc is None:
                continue
            bc(core)
            composed.append(name)
        except Exception:
            continue
    return composed
