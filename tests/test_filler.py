"""The deterministic baseline filler: interpret_finding from computed evidence."""
import io
import json

import yaml

from viva_superpowers import filler


def _ws(tmp_path, *, explanation=None):
    (tmp_path / "workspace.yaml").write_text("name: test-ws\n")
    sdir = tmp_path / "studies" / "s1"
    sdir.mkdir(parents=True)
    finding = {"id": "f1", "statement": "authored headline",
               "evidence": {"from_test": "t-range", "observed": 59.2, "units": "C"}}
    if explanation is not None:
        finding["explanation"] = explanation
    (sdir / "study.yaml").write_text(yaml.safe_dump({
        "name": "s1",
        "behavior_tests": [{"name": "t-range", "measure": {"path": "settled_T"},
                            "pass_if": {"low": 40.0, "high": 91.0}}],
        "findings": [finding],
    }))
    return tmp_path


def _req(**kw):
    base = {"id": "gr-1", "kind": "interpret_finding", "target": "claim:s1",
            "produces": "finding/v1"}
    base.update(kw)
    return base


def test_fills_interpretation_from_evidence(tmp_path):
    ws = _ws(tmp_path)
    res = filler.fill(_req(), ws_root=ws)
    assert res is not None
    art = res["artifact"]
    assert art["study"] == "s1" and art["finding"] == "f1"
    # factual + run-backed: names the measured value, the band, and the in-band verdict
    assert "59.2" in art["explanation"]
    assert "[40.0, 91.0]" in art["explanation"]
    assert "is within" in art["explanation"]
    assert res["filler"]["kind"] == "deterministic"


def test_applies_through_the_engine_without_touching_evidence(tmp_path):
    ws = _ws(tmp_path)
    from discovery_engine.generation import GenerationRequest, GenerationResult
    from discovery_engine.generation_apply import apply_result
    res = filler.fill(_req(), ws_root=ws)
    out = apply_result(GenerationRequest(**_req()),
                       GenerationResult(request_id=res["request_id"], artifact=res["artifact"]),
                       ws_root=ws, inv_slug="demo")
    assert out["status"] == "applied"
    s = yaml.safe_load((ws / "studies" / "s1" / "study.yaml").read_text())
    f = s["findings"][0]
    assert "is within" in f["explanation"]
    assert f["evidence"]["observed"] == 59.2            # numeric evidence untouched
    assert f["statement"] == "authored headline"        # headline untouched


def test_never_clobbers_an_authored_interpretation(tmp_path):
    ws = _ws(tmp_path, explanation="an expert already wrote this")
    assert filler.fill(_req(), ws_root=ws) is None       # eligible-only: leaves authored prose


def test_none_for_unhandled_kind_or_missing_study(tmp_path):
    ws = _ws(tmp_path)
    assert filler.fill(_req(kind="propose_study"), ws_root=ws) is None
    assert filler.fill(_req(target="claim:nope"), ws_root=ws) is None


def test_main_reads_stdin_writes_stdout(tmp_path, monkeypatch, capsys):
    ws = _ws(tmp_path)
    monkeypatch.chdir(ws)                                # main resolves ws from cwd
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(_req())))
    filler.main()
    out = capsys.readouterr().out
    doc = json.loads(out)
    assert doc["artifact"]["finding"] == "f1" and "is within" in doc["artifact"]["explanation"]
