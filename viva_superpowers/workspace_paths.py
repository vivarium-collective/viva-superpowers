"""Back-compat shim — moved to :mod:`discovery_engine.workspace_paths`.

This module now lives in the standalone ``discovery-engine`` package. Prefer
importing from ``discovery_engine.workspace_paths`` directly; this re-export is kept so
existing ``viva_superpowers.workspace_paths`` imports (and the skills) keep working.
"""
import sys as _sys

if __name__ == "__main__":  # `python -m viva_superpowers.workspace_paths` → the real CLI
    import runpy
    runpy.run_module("discovery_engine.workspace_paths", run_name="__main__", alter_sys=True)
else:
    import warnings as _warnings
    _warnings.warn(
        "viva_superpowers.workspace_paths is a back-compat shim; import "
        "discovery_engine.workspace_paths directly (the facade is being retired).",
        DeprecationWarning,
        stacklevel=2,
    )
    from discovery_engine import workspace_paths as _m  # noqa: E402
    _sys.modules[__name__] = _m
