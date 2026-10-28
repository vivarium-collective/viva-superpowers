"""Back-compat shim — moved to :mod:`discovery_engine.simulation_set`.

This module now lives in the standalone ``discovery-engine`` package. Prefer
importing from ``discovery_engine.simulation_set`` directly; this re-export is kept so
existing ``viva_superpowers.simulation_set`` imports (and the skills) keep working.
"""
import sys as _sys

if __name__ == "__main__":  # `python -m viva_superpowers.simulation_set` → the real CLI
    import runpy
    runpy.run_module("discovery_engine.simulation_set", run_name="__main__", alter_sys=True)
else:
    from discovery_engine import simulation_set as _m  # noqa: E402
    _sys.modules[__name__] = _m
