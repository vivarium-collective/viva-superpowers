"""Back-compat shim — moved to :mod:`discovery_engine.workspace_yaml`.

This module now lives in the standalone ``discovery-engine`` package. Prefer
importing from ``discovery_engine.workspace_yaml`` directly; this re-export is kept so
existing ``viva_superpowers.workspace_yaml`` imports (and the skills) keep working.
"""
import sys as _sys

if __name__ == "__main__":  # `python -m viva_superpowers.workspace_yaml` → the real CLI
    import runpy
    runpy.run_module("discovery_engine.workspace_yaml", run_name="__main__", alter_sys=True)
else:
    import warnings as _warnings
    _warnings.warn(
        "viva_superpowers.workspace_yaml is a back-compat shim; import "
        "discovery_engine.workspace_yaml directly (the facade is being retired).",
        DeprecationWarning,
        stacklevel=2,
    )
    from discovery_engine import workspace_yaml as _m  # noqa: E402
    _sys.modules[__name__] = _m
