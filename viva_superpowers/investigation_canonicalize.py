"""Back-compat shim — moved to :mod:`discovery_engine.investigation_canonicalize`.

This module now lives in the standalone ``discovery-engine`` package. Prefer
importing from ``discovery_engine.investigation_canonicalize`` directly; this re-export is kept so
existing ``viva_superpowers.investigation_canonicalize`` imports (and the skills) keep working.
"""
import sys as _sys

if __name__ == "__main__":  # `python -m viva_superpowers.investigation_canonicalize` → the real CLI
    import runpy
    runpy.run_module("discovery_engine.investigation_canonicalize", run_name="__main__", alter_sys=True)
else:
    import warnings as _warnings
    _warnings.warn(
        "viva_superpowers.investigation_canonicalize is a back-compat shim; import "
        "discovery_engine.investigation_canonicalize directly (the facade is being retired).",
        DeprecationWarning,
        stacklevel=2,
    )
    from discovery_engine import investigation_canonicalize as _m  # noqa: E402
    _sys.modules[__name__] = _m
