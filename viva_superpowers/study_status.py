"""Back-compat shim — moved to :mod:`discovery_engine.study_status`.

This module now lives in the standalone ``discovery-engine`` package. Prefer
importing from ``discovery_engine.study_status`` directly; this re-export is kept so
existing ``viva_superpowers.study_status`` imports (and the skills) keep working.
"""
import sys as _sys

if __name__ == "__main__":  # `python -m viva_superpowers.study_status` → the real CLI
    import runpy
    runpy.run_module("discovery_engine.study_status", run_name="__main__", alter_sys=True)
else:
    import warnings as _warnings
    _warnings.warn(
        "viva_superpowers.study_status is a back-compat shim; import "
        "discovery_engine.study_status directly (the facade is being retired).",
        DeprecationWarning,
        stacklevel=2,
    )
    from discovery_engine import study_status as _m  # noqa: E402
    _sys.modules[__name__] = _m
