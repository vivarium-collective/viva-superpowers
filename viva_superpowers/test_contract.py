"""Back-compat shim — moved to :mod:`discovery_engine.test_contract`.

This module now lives in the standalone ``discovery-engine`` package. Prefer
importing from ``discovery_engine.test_contract`` directly; this re-export is kept so
existing ``viva_superpowers.test_contract`` imports (and the skills) keep working.
"""
import sys as _sys

if __name__ == "__main__":  # `python -m viva_superpowers.test_contract` → the real CLI
    import runpy
    runpy.run_module("discovery_engine.test_contract", run_name="__main__", alter_sys=True)
else:
    from discovery_engine import test_contract as _m  # noqa: E402
    _sys.modules[__name__] = _m
