from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
WP3 = ROOT / "docs/programmes/c2s-sptoi-v0-1/wp3"
STATE = ROOT / "records/research_operations/spto/C2S_SPTOI_PROGRAMME_STATE_v0_1.json"
MATRIX = ROOT / "records/research_operations/spto/C2S_SPTOI_SOURCE_COMPLETENESS_MATRIX_v0_1.json"
POINTER = ROOT / "registries/implementation/c2s_sptoi_v0_1/CURRENT_STATE_POINTER.json"
FIXTURE_CENSUS = ROOT / "fixtures/research_operations/c2_csm_reference/C2CSM_REFERENCE_FIXTURE_CENSUS_v0_1.json"
ASSESSMENT = WP3 / "C2S_SPTOI_WP3_CANDIDATE_SOURCE_ASSESSMENT_R10S2_v0_1.json"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_source_request_is_one_precise_wp3_g3_alg_quarantine_pause() -> None:
    request = load(WP3 / "C2S_SPTOI_WP3_SOURCE_REQUEST_PACKET_v0_1.json")
    assert request["packet_id"] == "C2S-SPTOI-WP3"
    assert request["gate_id"] == "C2S-SPTOI-G3-ALG"
    assert request["status"] == "SOURCE_CONFLICT_QUARANTINED"
    assert request["missing_component"]["component_id"] == "C2CSM.P3-R5-T2-S2.HISTORICAL.CASE.CORPUS.v0.1"
    assert "five divergent case trajectories" in request["operator_action_required"]
    assert "CONTINUE SOURCE-LIMITED" in request["operator_action_required"]
    assert request["repository_state_preserved"] is True


def test_request_requires_case_trajectories_runtime_bindings_and_expected_ledgers() -> None:
    request = load(WP3 / "C2S_SPTOI_WP3_SOURCE_REQUEST_PACKET_v0_1.json")
    inputs = " ".join(request["missing_component"]["required_inputs"])
    outputs = " ".join(request["missing_component"]["required_expected_outputs"])
    for term in ("high, low and close", "instrument", "timeframe", "syminfo.mintick", "lab-window", "Chart-gap", "cutoff-time"):
        assert term in inputs
    for term in ("P3", "R5", "T2", "S2", "Canonical typed stream", "checkpoint"):
        assert term in outputs


def test_aggregate_evidence_cannot_be_promoted_to_raw_fixture_source() -> None:
    request = load(WP3 / "C2S_SPTOI_WP3_SOURCE_REQUEST_PACKET_v0_1.json")
    census = load(FIXTURE_CENSUS)
    assert census["raw_case_inputs_status"] == "NOT_IN_WP1_OPERATOR_SUPPLIED_SET"
    assert "NO_AGGREGATE_TO_RAW_RECONSTRUCTION" in census["raw_case_inputs_effect"]
    assert any("one aggregate row per case" in item for item in request["not_sufficient"])
    assert request["source_limited_alternative_taken"] is False


def test_fixture_census_identity_and_population_are_preserved() -> None:
    request = load(WP3 / "C2S_SPTOI_WP3_SOURCE_REQUEST_PACKET_v0_1.json")
    evidence = {item["artifact"]: item for item in request["last_known_evidence"]}
    expected = evidence["fixtures/research_operations/c2_csm_reference/C2CSM_REFERENCE_FIXTURE_CENSUS_v0_1.json"]["sha256"]
    assert hashlib.sha256(FIXTURE_CENSUS.read_bytes()).hexdigest() == expected
    requirements = " ".join(request["integrity_requirements"])
    for expected_count in ("15 development cases / 1,392 bars / 245 objects", "10 holdout cases / 936 bars / 163 objects", "25 cases / 2,328 bars / 408 objects"):
        assert expected_count in requirements


def test_programme_state_pointer_and_matrix_stop_at_same_boundary() -> None:
    state = load(STATE)
    pointer = load(POINTER)
    matrix = load(MATRIX)
    assert state["packet_id"] == pointer["current_packet"] == matrix["current_packet"] == "C2S-SPTOI-WP3"
    assert pointer["current_gate"] == "C2S-SPTOI-G3-ALG"
    assert state["status"] == pointer["status"] == matrix["families"][0]["status"] == "SOURCE_CONFLICT_QUARANTINED"
    assert state["source_request_packet"] == matrix["families"][0]["source_request_packet"]
    assert state["next_packet"] == pointer["next_packet"] == "C2S-SPTOI-WP3"


def test_qa_confirms_source_complete_policy_without_claiming_g3_review() -> None:
    qa = load(WP3 / "C2S_SPTOI_WP3_SOURCE_RECOVERY_QA_v0_1.json")
    assert qa["result"] == "PASS_SOURCE_CONFLICT_QUARANTINED"
    assert qa["checks"]["candidate_raw_case_input_corpus_found"] is True
    assert qa["checks"]["exact_historical_raw_case_input_corpus_found"] is False
    assert qa["checks"]["candidate_aggregate_replay"].startswith("FAIL_EXACT")
    assert qa["checks"]["aggregate_to_raw_reconstruction_attempted"] is False
    assert qa["checks"]["source_limited_alternative_taken"] is False
    assert qa["checks"]["independent_g3_review_started"] is False
    assert qa["checks"]["wp4_released"] is False


def test_source_recovery_record_grants_no_authority() -> None:
    state = load(STATE)
    pointer = load(POINTER)
    request = load(WP3 / "C2S_SPTOI_WP3_SOURCE_REQUEST_PACKET_v0_1.json")
    assert request["authority_effect"] == "NONE_SOURCE_RECOVERY_RECORD_ONLY"
    assert state["authority_delta"] == "NONE_HISTORICAL_CONFORMANCE_ONLY"
    assert state["gating"]["g3_alg"] == "BLOCKED_SOURCE_CONFLICT_QUARANTINED_NOT_REVIEWED"
    assert state["validation"] == "LOCKED_UNCONSUMED"
    assert state["semantic_authority"] == "NONE"
    assert state["c2e_boundary_authority"] == "NONE"
    assert state["sff_probability_risk_exposure_execution_authority"] == "NONE"
    assert pointer["protected_source"] == "DENIED"


def test_supplied_r10s2_candidate_is_preserved_and_quarantined() -> None:
    assessment = load(ASSESSMENT)
    candidate = assessment["candidate"]
    classification = assessment["classification"]
    assert candidate["original_filename"] == "R10S2_TRADINGVIEW_RAW.csv"
    assert candidate["sha256"] == "14e462a87fdeeeb839aa498e6152bb626bb2383fedacde1447a87bd34ade4a81"
    assert candidate["size_bytes"] == 1927804
    assert candidate["preserved_hash_verified"] is True
    assert candidate["quarantine_hash_verified"] is True
    assert classification["admission"] == "QUARANTINED_SOURCE_DIVERGENCE"
    assert classification["historical_fixture_promotion"] is False
    assert classification["source_limited_continuation"] is False


def test_candidate_replay_evidence_is_exactly_scoped_to_observed_result() -> None:
    assessment = load(ASSESSMENT)
    inspection = assessment["structural_inspection"]
    replay = assessment["replay_assessment"]
    assert inspection["historical_cases_present"] == 25
    assert inspection["historical_case_bars_present"] == 2328
    assert replay["checkpoint_every"] == 16
    assert replay["aggregate_cells_compared"] == 800
    assert replay["aggregate_cells_equal"] == 794
    assert replay["cases_exact_at_aggregate_surface"] == 20
    assert replay["cases_divergent_at_aggregate_surface"] == 5
    assert len(replay["divergences"]) == 6
    assert assessment["remaining_source_gap"]["all_case_expected_outputs_still_required"] is True
