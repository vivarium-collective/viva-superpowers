"""Contract test: the discovery-engine back-compat facade.

The investigation/study framework and the derive-first discovery cycle moved to
the standalone ``discovery-engine`` package. viva-superpowers keeps thin
re-export shims so ``viva_superpowers.<module>`` imports — and the ``/viva-*``
skills that use them — keep working. That facade is intentionally permanent
public surface.

Each shim does ``from discovery_engine import <module> as _m`` then
``sys.modules[__name__] = _m``, so ``viva_superpowers.<module>`` IS the identical
module object as ``discovery_engine.<module>``. This test discovers every such
shim and asserts that identity, guarding the facade against a broken, copied, or
stale re-export. (The behavioural tests for this code live in discovery-engine's
own suite; this file is the facade contract that stays here.)
"""
from __future__ import annotations

import importlib
import pathlib
import re

import pytest

_PKG = pathlib.Path(__file__).resolve().parent.parent / "viva_superpowers"
# shim body: `from discovery_engine import <target> as _m`  +  `sys.modules[__name__] = _m`
_IMPORT = re.compile(r"^\s*from discovery_engine import (\w+) as _m\b", re.MULTILINE)


def _discover_facade_shims() -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    for f in sorted(_PKG.glob("*.py")):
        txt = f.read_text()
        if "sys.modules[__name__] = _m" not in txt:
            continue
        m = _IMPORT.search(txt)
        if m:
            pairs.append((f.stem, m.group(1)))
    return pairs


_PAIRS = _discover_facade_shims()


def test_facade_shims_are_present():
    # The extraction created 58 discovery-engine facade shims. A sharp drop means
    # the shim mechanism broke (e.g. a bad refactor), not an intentional removal.
    assert len(_PAIRS) >= 50, (
        f"expected the discovery-engine facade shims (~58), found {len(_PAIRS)}"
    )


@pytest.mark.parametrize("shim_name,de_target", _PAIRS, ids=[p[0] for p in _PAIRS])
def test_shim_is_the_identical_discovery_engine_module(shim_name, de_target):
    shim = importlib.import_module(f"viva_superpowers.{shim_name}")
    real = importlib.import_module(f"discovery_engine.{de_target}")
    assert shim is real, (
        f"viva_superpowers.{shim_name} is not discovery_engine.{de_target} "
        "— the facade re-export is broken or stale"
    )
