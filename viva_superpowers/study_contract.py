"""Back-compat shim — moved to :mod:`discovery_engine.study_contract`.

This module now lives in the standalone ``discovery-engine`` package. Prefer
importing from ``discovery_engine.study_contract`` directly; this re-export is kept so
existing ``viva_superpowers.study_contract`` imports (and the skills) keep working.
"""
import sys as _sys

if __name__ == "__main__":  # `python -m viva_superpowers.study_contract` → the real CLI
    import runpy
    runpy.run_module("discovery_engine.study_contract", run_name="__main__", alter_sys=True)
else:
    from discovery_engine import study_contract as _m  # noqa: E402
    _sys.modules[__name__] = _m
