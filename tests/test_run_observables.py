"""P3 Task 1 — resolve a study's latest-run emitted observables.

Best-effort: no run / unreadable run → ``None``, never an exception.
"""
import os

import pytest

from viva_superpowers.run_observables import study_run_observables

GENESIS = "/Users/eranagmon/code/viva-genesis"


@pytest.mark.skipif(
    not os.path.isdir(f"{GENESIS}/workspace/studies/og-00-vent-reactor-baseline"),
    reason="viva-genesis og-00 run fixture not present",
)
def test_observables_from_real_run():
    obs = study_run_observables({"slug": "og-00-vent-reactor-baseline"}, GENESIS)
    assert obs is not None
    assert "temperature" in obs        # declared AND emitted
    assert "pressure" not in obs       # declared in contract.face but never emitted


def test_observables_none_when_no_run(tmp_path):
    assert study_run_observables({"slug": "nope"}, tmp_path) is None
