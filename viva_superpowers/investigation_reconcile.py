"""Back-compat shim — moved to :mod:`discovery_engine.investigation_reconcile`.

This module now lives in the standalone ``discovery-engine`` package. Prefer
importing from ``discovery_engine.investigation_reconcile`` directly; this re-export is kept so
existing ``viva_superpowers.investigation_reconcile`` imports (and the skills) keep working.
"""
import sys as _sys

if __name__ == "__main__":  # `python -m viva_superpowers.investigation_reconcile` → the real CLI
    import runpy
    runpy.run_module("discovery_engine.investigation_reconcile", run_name="__main__", alter_sys=True)
else:
    from discovery_engine import investigation_reconcile as _m  # noqa: E402
    _sys.modules[__name__] = _m
