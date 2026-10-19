from viva_superpowers.study_contract_lint import lint_study_contract


def test_matching_face_no_findings():
    study = {"contract": {"face": {"outputs": {"mass": {"_type": "float", "_units": "fg"}}}}}
    comp = {"outputs": {"mass": {"_type": "float", "_units": "fg"}}}
    assert lint_study_contract(study, comp) == []


def test_unit_mismatch_flagged():
    study = {"contract": {"face": {"outputs": {"mass": {"_type": "float", "_units": "fg"}}}}}
    comp = {"outputs": {"mass": {"_type": "float", "_units": "mol"}}}
    f = lint_study_contract(study, comp)
    assert f and f[0]["check"] == "contract-face" and "unit" in f[0]["message"].lower()


def test_missing_port_flagged():
    study = {"contract": {"face": {"outputs": {"mass": "float"}}}}
    assert lint_study_contract(study, {"outputs": {}})


def test_no_contract_block_no_findings():
    assert lint_study_contract({"name": "x"}, {"outputs": {}}) == []
