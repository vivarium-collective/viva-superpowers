"""Back-compat shim — moved to :mod:`discovery_engine.investigation_import`.

This module now lives in the standalone ``discovery-engine`` package. Prefer
importing from ``discovery_engine.investigation_import`` directly; this re-export is kept so
existing ``viva_superpowers.investigation_import`` imports (and the skills) keep working.
"""
import sys as _sys

if __name__ == "__main__":  # `python -m viva_superpowers.investigation_import` → the real CLI
    import runpy
    runpy.run_module("discovery_engine.investigation_import", run_name="__main__", alter_sys=True)
else:
    from discovery_engine import investigation_import as _m  # noqa: E402
    _sys.modules[__name__] = _m
