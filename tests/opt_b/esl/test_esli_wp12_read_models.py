import pytest

from ovc.opt_b.esl.read_models import ESLReadModelError, assert_projection_fidelity, build_esl_read_model


def _source():
    projections = {
        "occurrence":{"occurrence_id":"occ:1","partial":True},
        "evidence_frontier":{"frontier_id":"ef:1"},
        "states":{"availability":"AVAILABLE","evaluability":"NOT_EVALUABLE"},
        "sri":None,
        "organisation":{"status":"NO_STABLE_ORGANISATION"},
        "constraint":None,
        "qualification":{"status":"EMPIRICALLY_OBSERVED"},
        "ast":{"ast_id":"ast:1","resolution":"PARTIAL"},
        "render":{"text":"x","authoritative":False},
    }
    authority = {"source_record":"auth:1","runtime":"INACTIVE_REFERENCE","authority_effect":"NONE"}
    return projections, authority


def test_wp12_projection_is_read_only_and_faithful():
    projections, authority = _source()
    model = build_esl_read_model(source_refs=["occ:1","auth:1"], projections=projections, authority=authority, lineage_refs=["lin:1"])
    assert model["projection_mode"] == "READ_ONLY"
    assert model["calculation_policy"] == "NO_FRONTEND_SCIENTIFIC_CALCULATION"
    assert model["authority_effect"] == "NONE"
    assert_projection_fidelity(read_model=model, expected=projections)


def test_wp12_identity_is_deterministic_under_ref_ordering():
    projections, authority = _source()
    a = build_esl_read_model(source_refs=["b","a"], projections=projections, authority=authority, lineage_refs=["z","y"])
    b = build_esl_read_model(source_refs=["a","b"], projections=projections, authority=authority, lineage_refs=["y","z"])
    assert a["read_model_id"] == b["read_model_id"]


def test_wp12_rejects_frontend_scientific_calculation_and_authority_uplift():
    projections, authority = _source()
    projections["qualification"] = {"candidate_strength":0.9}
    with pytest.raises(ESLReadModelError, match="FRONTEND_SCIENTIFIC_CALCULATION_FORBIDDEN"):
        build_esl_read_model(source_refs=["occ:1"], projections=projections, authority=authority)
    projections, _ = _source()
    with pytest.raises(ESLReadModelError, match="READ_MODEL_CANNOT_GRANT_AUTHORITY"):
        build_esl_read_model(source_refs=["occ:1"], projections=projections, authority={"authority_effect":"GRANTED"})


def test_wp12_unknown_projection_surface_fails_closed():
    projections, authority = _source()
    projections["new_science"] = {"x":1}
    with pytest.raises(ESLReadModelError, match="READ_MODEL_UNKNOWN_PROJECTION"):
        build_esl_read_model(source_refs=["occ:1"], projections=projections, authority=authority)
