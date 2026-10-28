"""Back-compat shim — moved to :mod:`discovery_engine.study_io`.

This module now lives in the standalone ``discovery-engine`` package. Prefer
importing from ``discovery_engine.study_io`` directly; this re-export is kept so
existing ``viva_superpowers.study_io`` imports (and the skills) keep working.
"""
import sys as _sys

if __name__ == "__main__":  # `python -m viva_superpowers.study_io` → the real CLI
    import runpy
    runpy.run_module("discovery_engine.study_io", run_name="__main__", alter_sys=True)
else:
    from discovery_engine import study_io as _m  # noqa: E402
    _sys.modules[__name__] = _m
