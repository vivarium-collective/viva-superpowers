"""Back-compat shim — moved to :mod:`discovery_engine.scaffold`.

This module now lives in the standalone ``discovery-engine`` package. Prefer
importing from ``discovery_engine.scaffold`` directly; this re-export is kept so
existing ``viva_superpowers.scaffold`` imports (and the skills) keep working.
"""
import sys as _sys

if __name__ == "__main__":  # `python -m viva_superpowers.scaffold` → the real CLI
    import runpy
    # The CLI (`cli()` click group) lives in discovery_engine.integration.scaffold; the
    # discovery_engine.scaffold alias only re-exports the module object and has no
    # ``if __name__ == "__main__"`` block, so running IT as __main__ is a no-op. Point at
    # the module that actually invokes the CLI.
    runpy.run_module("discovery_engine.integration.scaffold", run_name="__main__", alter_sys=True)
else:
    from discovery_engine import scaffold as _m  # noqa: E402
    _sys.modules[__name__] = _m
