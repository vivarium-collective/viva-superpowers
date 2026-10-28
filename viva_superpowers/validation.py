"""Back-compat shim — moved to :mod:`discovery_engine.validation`.

This module now lives in the standalone ``discovery-engine`` package. Prefer
importing from ``discovery_engine.validation`` directly; this re-export is kept so
existing ``viva_superpowers.validation`` imports (and the skills) keep working.
"""
import sys as _sys

if __name__ == "__main__":  # `python -m viva_superpowers.validation` → the real CLI
    import runpy
    runpy.run_module("discovery_engine.validation", run_name="__main__", alter_sys=True)
else:
    from discovery_engine import validation as _m  # noqa: E402
    _sys.modules[__name__] = _m
