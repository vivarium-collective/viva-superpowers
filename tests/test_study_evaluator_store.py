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


def test_falls_back_to_shared_runs_db_for_a_storeless_entry(tmp_path, monkeypatch):
    # `vivarium-workbench run study` writes into <study_dir>/runs.db but can leave the run
    # entry with no store pointer; resolve to that shared DB when the entry's run_id is in it.
    import viva_superpowers.run_registry as rr
    shared = tmp_path / "runs.db"
    shared.write_bytes(b"")
    monkeypatch.setattr(rr, "list_runs", lambda p: [{"run_id": "run-xyz"}])
    assert _resolve_run_store({"name": "run-xyz"}, tmp_path) == str(shared)


def test_no_shared_fallback_when_run_id_absent(tmp_path, monkeypatch):
    import viva_superpowers.run_registry as rr
    (tmp_path / "runs.db").write_bytes(b"")
    monkeypatch.setattr(rr, "list_runs", lambda p: [{"run_id": "other"}])
    assert _resolve_run_store({"name": "run-xyz"}, tmp_path) is None
