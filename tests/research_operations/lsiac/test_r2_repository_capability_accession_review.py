import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
R2 = ROOT / "docs" / "programmes" / "lsiac-v0-1" / "r2"
STATE = ROOT / "records" / "research_operations" / "lsiac" / "LSIAC_PROGRAMME_STATE_v0_17.json"


def _json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_r2_repo_census_reuses_irof_and_preserves_source_limits():
    census = _json(R2 / "LSIAC_R2_REPOSITORY_CAPABILITY_CENSUS_v0_1.json")
    conclusion = census["conclusion"]
    assert conclusion["generic_execution_backbone_missing"] is False
    assert conclusion["critical_owner_source_handoff_missing"] is True
    assert conclusion["new_generic_transport_framework_required"] is False
    assert "IROF" in conclusion["recommended_reuse"]

    by_id = {row["capability_id"]: row for row in census["capabilities"]}
    active = by_id["REPO-ACTIVE-STRUCTURAL-SPINE"]
    assert active["current_market_envelope"]["instrument"] == "GBPUSD"
    assert set(active["current_market_envelope"]["clocks"]) == {"15M", "2H_A_L"}
    blocked = by_id["REPO-C2S-SPTO-CONTINUOUS-STREAM"]
    assert blocked["owner_stream_binding"] == "ABSENT"
    assert blocked["adapter_implementation"] == "NONE"


def test_r2_laboratory_census_separates_durable_machinery_from_research_programmes():
    census = _json(R2 / "LSIAC_R2_LABORATORY_DURABLE_CAPABILITY_CENSUS_v0_1.json")
    by_id = {row["candidate_id"]: row for row in census["candidates"]}

    assert by_id["LAB-RRSCG-R2-CONSTRAINT-KERNEL"]["accession_posture"] == "ACCESSION_CANDIDATE"
    assert by_id["LAB-RRSCG-D9-OBSERVER-STATE-DYNAMICS"]["candidate_class"] == "OBSERVER_FACULTY"
    assert by_id["LAB-RRSCG-D10-REDUCER"]["supersession_scope"].startswith("D9_SUPERSEDED_FORWARD_AT_REDUCER_LAYER_ONLY")
    assert by_id["LAB-REPRESENTATION-ROBUSTNESS-PROGRAMME"]["accession_posture"].startswith("EXCLUDED_NORMAL_RESEARCH")
    assert by_id["LAB-RRSCG-OBSERVER-STATE-GEOMETRY-NOMINATION"]["accession_posture"].startswith("EXCLUDED_AS_NOMINATION")
    assert by_id["LAB-AOEC"]["accession_posture"].startswith("DEFER")


def test_r2_gap_matrix_has_owner_handoff_before_rrscg_and_no_new_generic_runner():
    matrix = _json(R2 / "LSIAC_R2_REPOSITORY_GAP_AND_ACCESSION_MATRIX_v0_1.json")
    by_id = {row["gap_id"]: row for row in matrix["rows"]}

    assert by_id["LSIAC-R2-GAP-01"]["disposition"] == "HANDOFF_REQUIREMENT"
    assert by_id["LSIAC-R2-GAP-01"]["lsiac_may_implement_owner_truth"] is False
    assert by_id["LSIAC-R2-GAP-02"]["disposition"] == "ALREADY_PRESENT_REUSE"
    assert by_id["LSIAC-R2-GAP-03"]["priority"] == "P1_AFTER_OWNER_READ_SURFACE"
    assert by_id["LSIAC-R2-GAP-04"]["priority"] == "P1_AFTER_OWNER_READ_SURFACE"
    assert by_id["LSIAC-R2-GAP-08"]["disposition"] == "NO_NEW_FRAMEWORK"

    combined_limits = " ".join(by_id["LSIAC-R2-GAP-06"]["hard_limits"])
    assert "TV120_NATIVE" in combined_limits
    assert "2H_A_L" in combined_limits


def test_r2_review_has_no_authority_expansion():
    matrix = _json(R2 / "LSIAC_R2_REPOSITORY_GAP_AND_ACCESSION_MATRIX_v0_1.json")
    assert matrix["authority_delta"] == "NONE_REVIEW_ONLY"
    assert all(row["authority_effect_now"] == "NONE" for row in matrix["rows"])

    state = _json(STATE)
    assert state["authority_delta"] == "NONE_CAPABILITY_GAP_REVIEW_ONLY"
    assert state["active_discovery_development_validation_authority"] == "NONE"
    assert state["validation"] == "LOCKED_UNCONSUMED"
    assert state["publication"] == "NONE"
    assert state["probability_risk_exposure_e_h_execution_authority"] == "NONE"


def test_r2_recommended_frontier_is_capability_first():
    state = _json(STATE)
    frontier = set(state["recommended_accession_frontier"])
    assert "RRSCG_R2_CONTINUATION_CONSTRAINT_KERNEL" in frontier
    assert "RRSCG_D9_CONSTRAINT_STATE_GEOMETRY_KINEMATICS" in frontier
    assert "RRSCG_D10_REDUCER_SUBCOMPONENT" in frontier
    assert "MULTICLOCK_COORDINATE_ALIGNMENT_CORRESPONDENCE" in frontier
    assert "MULTICLOCK_NEGATIVE_KNOWLEDGE" in frontier
    assert "REPRESENTATION_ROBUSTNESS" not in frontier
    assert state["generic_execution_backbone"] == "REUSE_IROF_NO_NEW_GENERIC_RUNNER"
