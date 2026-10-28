"""Back-compat shim — moved to :mod:`discovery_engine.readout_migration`.

This module now lives in the standalone ``discovery-engine`` package. Prefer
importing from ``discovery_engine.readout_migration`` directly; this re-export is kept so
existing ``viva_superpowers.readout_migration`` imports (and the skills) keep working.
"""
import sys as _sys

if __name__ == "__main__":  # `python -m viva_superpowers.readout_migration` → the real CLI
    import runpy
    runpy.run_module("discovery_engine.readout_migration", run_name="__main__", alter_sys=True)
else:
    from discovery_engine import readout_migration as _m  # noqa: E402
    _sys.modules[__name__] = _m
