"""Back-compat / facade shim — moved to :mod:`discovery_engine.workspace_lint`.

The composed workspace-lint entrypoint (shared report-linter checks + a workspace's
own ``<pkg>.lint_checks.CHECKS``) lives in the standalone ``discovery-engine``
package. Prefer importing from ``discovery_engine.workspace_lint`` directly; this
re-export is kept so ``viva_superpowers.workspace_lint`` (and the thin
``scripts/lint-workspace.py`` shim workspaces use) keep working.
"""
import sys as _sys

if __name__ == "__main__":  # `python -m viva_superpowers.workspace_lint` → the real CLI
    import runpy
    runpy.run_module("discovery_engine.workspace_lint", run_name="__main__", alter_sys=True)
else:
    import warnings as _warnings
    _warnings.warn(
        "viva_superpowers.workspace_lint is a back-compat shim; import "
        "discovery_engine.workspace_lint directly (the facade is being retired).",
        DeprecationWarning,
        stacklevel=2,
    )
    from discovery_engine import workspace_lint as _m  # noqa: E402
    _sys.modules[__name__] = _m
