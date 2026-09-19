from pathlib import Path
from viva_superpowers.study_evaluator import _resolve_run_store


def test_resolves_store_path(tmp_path):
    store = tmp_path / "results" / "baseline.zarr"
    store.mkdir(parents=True)
    run = {"name": "baseline", "emitter": "xarray", "store_path": "results/baseline.zarr"}
    # relative to study_dir=tmp_path
    assert _resolve_run_store(run, tmp_path) == str(store)


def test_resolves_generic_store_key(tmp_path):
    store = tmp_path / "s.zarr"
    store.mkdir()
    run = {"name": "b", "store": str(store)}
    assert _resolve_run_store(run, tmp_path) == str(store)


def test_emitter_store_still_preferred(tmp_path):
    good = tmp_path / "emit.zarr"
    good.mkdir()
    other = tmp_path / "sp.zarr"
    other.mkdir()
    run = {"emitter": {"store": str(good)}, "store_path": str(other)}
    assert _resolve_run_store(run, tmp_path) == str(good)
