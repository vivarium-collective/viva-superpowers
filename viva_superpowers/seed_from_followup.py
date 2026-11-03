"""Back-compat shim — moved to :mod:`discovery_engine.seed_from_followup`.

This module now lives in the standalone ``discovery-engine`` package. Prefer
importing from ``discovery_engine.seed_from_followup`` directly; this re-export is kept so
existing ``viva_superpowers.seed_from_followup`` imports (and the skills) keep working.
"""
import sys as _sys

if __name__ == "__main__":  # `python -m viva_superpowers.seed_from_followup` → the real CLI
    import runpy
    runpy.run_module("discovery_engine.seed_from_followup", run_name="__main__", alter_sys=True)
else:
    import warnings as _warnings
    _warnings.warn(
        "viva_superpowers.seed_from_followup is a back-compat shim; import "
        "discovery_engine.seed_from_followup directly (the facade is being retired).",
        DeprecationWarning,
        stacklevel=2,
    )
    from discovery_engine import seed_from_followup as _m  # noqa: E402
    _sys.modules[__name__] = _m
