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
from types import ModuleType
from typing import Iterable


def _register_module_processes(core, mod, _pb) -> int:
    """Register the process-bigraph-native classes *defined in* ``mod``.

    Only classes whose ``__module__`` equals ``mod.__name__`` are considered, so
    classes the module merely imports from elsewhere are skipped. Best-effort +
    idempotent: a class that fails to register is skipped. Returns the count.
    """
    n = 0
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


def register_package_processes(core, package, *, recurse: bool = False) -> int:
    """Register every process-bigraph-native process/step class into ``core``
    (keyed by class name).

    ``package`` may be:

    - a package (a dotted name resolving to a module that has ``__path__``): its
      top-level modules are enumerated and every process/step class *defined in*
      each is registered — the historical behavior. Subpackages are not descended
      into unless ``recurse=True`` (kept off by default so a heavy reconstruction
      subpackage isn't imported just to enumerate processes).
    - a single leaf module (a dotted name resolving to a module with no
      ``__path__``, e.g. ``"my_pkg.processes"``, **or** an already-imported module
      object): ONLY the process/step classes *defined in that exact module* are
      registered — sibling modules (e.g. ``my_pkg.visualizations``) are not
      imported or scanned. This lets a repo whose processes live in one
      ``processes.py`` module scope registration precisely. ``recurse`` is
      ignored for a leaf module.

    Filters to real ``process_bigraph.Process`` / ``Step`` subclasses, so
    vivarium-core Steps and unrelated classes are skipped. "Defined in" means the
    class's ``__module__`` matches the scanned module, so classes merely imported
    into a module are not registered. Best-effort + idempotent: a module that
    fails to import, or a class that fails to register, is skipped — never fatal
    to ``build_core``. Returns the count.

    Example::

        from viva_superpowers.core_compose import register_package_processes
        register_package_processes(core, "my_pkg.processes")   # single module
        register_package_processes(core, "my_pkg", recurse=True)  # whole package
    """
    import process_bigraph as _pb

    if isinstance(package, ModuleType):
        pkg = package
    else:
        try:
            pkg = importlib.import_module(package)
        except Exception:
            return 0

    # A leaf module (no __path__) is scoped to itself: register only its own
    # classes and never touch sibling modules.
    pkg_path = getattr(pkg, "__path__", None)
    if not pkg_path:
        return _register_module_processes(core, pkg, _pb)

    n = 0
    for modinfo in pkgutil.iter_modules(pkg_path):
        if modinfo.ispkg and not recurse:
            continue
        try:
            mod = importlib.import_module(f"{pkg.__name__}.{modinfo.name}")
        except Exception:
            continue
        n += _register_module_processes(core, mod, _pb)
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
