from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
WP3 = ROOT / "docs/programmes/c2s-sptoi-v0-1/wp3"
HISTORICAL_STATE = ROOT / "records/research_operations/spto/C2S_SPTOI_PROGRAMME_STATE_v0_1.json"
STATE = ROOT / "records/research_operations/spto/C2S_SPTOI_PROGRAMME_STATE_v0_2.json"
MATRIX = ROOT / "records/research_operations/spto/C2S_SPTOI_SOURCE_COMPLETENESS_MATRIX_v0_2.json"
POINTER = ROOT / "registries/implementation/c2s_sptoi_v0_1/CURRENT_STATE_POINTER.json"
FIXTURE_CENSUS = ROOT / "fixtures/research_operations/c2_csm_reference/C2CSM_REFERENCE_FIXTURE_CENSUS_v0_1.json"
ASSESSMENT = WP3 / "C2S_SPTOI_WP3_CANDIDATE_SOURCE_ASSESSMENT_R10S2_v0_1.json"
AMENDMENT = WP3 / "C2S_SPTOI_WP3_RECOVERY_PRIORITY_AMENDMENT_v0_1.json"
DISPOSITION = WP3 / "C2S_SPTOI_WP3_PARTIAL_SOURCE_LIMITED_DISPOSITION_v0_1.json"
PARITY = WP3 / "C2S_SPTOI_WP3_PARTIAL_SOURCE_LIMITED_PARITY_RECEIPT_v0_1.json"


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


def test_request_prioritises_five_case_trajectories_and_full_parity_evidence() -> None:
    request = load(WP3 / "C2S_SPTOI_WP3_SOURCE_REQUEST_PACKET_v0_1.json")
    inputs = " ".join(request["missing_component"]["required_inputs"])
    outputs = " ".join(request["missing_component"]["required_expected_outputs"])
    for term in ("five priority divergent cases", "instrument", "timeframe", "syminfo.mintick", "lab-window", "Chart-gap", "cutoff-time"):
        assert term in inputs
    for term in ("P3/R5/T2/S2", "canonical typed streams", "checkpoint", "typed-handoff parity"):
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


def test_programme_state_pointer_and_matrix_agree_at_g3_review_boundary() -> None:
    state = load(STATE)
    pointer = load(POINTER)
    matrix = load(MATRIX)
    assert state["packet_id"] == pointer["current_packet"] == matrix["current_packet"] == "C2S-SPTOI-WP3"
    assert pointer["current_gate"] == "C2S-SPTOI-G3-ALG"
    assert state["status"] == pointer["status"] == matrix["families"][0]["status"] == "PARTIAL_SOURCE_LIMITED_G3_ALG_REVIEW_READY"
    assert state["source_completeness_manifest"] == matrix["families"][0]["manifest"]
    assert state["next_packet"] == pointer["next_packet"] == "C2S-SPTOI-WP3"


def test_historical_source_recovery_qa_is_preserved_without_becoming_current() -> None:
    qa = load(WP3 / "C2S_SPTOI_WP3_SOURCE_RECOVERY_QA_v0_1.json")
    assert qa["result"] == "PASS_SOURCE_CONFLICT_QUARANTINED"
    assert qa["checks"]["candidate_raw_case_input_corpus_found"] is True
    assert qa["checks"]["exact_historical_raw_case_input_corpus_found"] is False
    assert qa["checks"]["candidate_aggregate_replay"].startswith("FAIL_EXACT")
    assert qa["checks"]["aggregate_to_raw_reconstruction_attempted"] is False
    assert qa["checks"]["source_limited_alternative_taken"] is False
    assert qa["checks"]["independent_g3_review_started"] is False
    assert qa["checks"]["wp4_released"] is False
    pointer = load(POINTER)
    assert pointer["current_state"] != str(HISTORICAL_STATE.relative_to(ROOT)).replace("\\", "/")


def test_source_recovery_record_grants_no_authority() -> None:
    state = load(STATE)
    pointer = load(POINTER)
    request = load(WP3 / "C2S_SPTOI_WP3_SOURCE_REQUEST_PACKET_v0_1.json")
    assert request["authority_effect"] == "NONE_SOURCE_RECOVERY_RECORD_ONLY"
    assert state["authority_delta"] == "NONE_HISTORICAL_CONFORMANCE_ONLY"
    assert state["gating"]["g3_alg"] == "INDEPENDENT_BLOCKING_REVIEW_IN_PROGRESS"
    assert state["active_c2_authority"] == "NONE"
    assert state["historical_reference_as_current_owner_truth"] == "PROHIBITED"
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
    disposition = load(DISPOSITION)
    assert disposition["quarantined_candidate"]["historical_fixture_promotion"] == "DENIED"
    assert disposition["quarantined_candidate"]["evidentiary_role"] == "CORROBORATING_LATER_CAPTURE_ONLY"


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
    amendment = load(AMENDMENT)
    assert any("presumption" in item for item in amendment["supersession"]["supersedes"])


def test_recovery_priority_amendment_does_not_presume_historical_stream_exports() -> None:
    amendment = load(AMENDMENT)
    request = load(WP3 / "C2S_SPTOI_WP3_SOURCE_REQUEST_PACKET_v0_1.json")
    state = load(STATE)
    assert amendment["operator_amendment"]["primary_irreplaceable_missing_source"] == "THE_FIVE_DIVERGENT_ORIGINAL_CASE_TRAJECTORIES"
    assert len(amendment["priority_case_ids"]) == 5
    assert amendment["historical_stream_export_search"]["status"] == "NOT_FOUND_EXISTENCE_NOT_ESTABLISHED"
    assert amendment["historical_stream_export_search"]["existence_inference"] == "NOT_MADE"
    assert "five divergent case trajectories" in request["operator_action_required"]
    assert state["source_recovery_for_missing_five"] == "STOPPED_BY_OPERATOR"
    assert state["source_completeness_status"] == "PARTIAL_SOURCE_LIMITED_HISTORICAL_CASE_EVIDENCE"


def test_conditional_complete_route_preserves_every_parity_requirement() -> None:
    amendment = load(AMENDMENT)
    determination = amendment["contract_determination"]
    conditions = " ".join(determination["complete_conditions"])
    exclusions = " ".join(determination["not_sufficient"])
    assert determination["answer"] == "YES_CONDITIONALLY"
    for term in (
        "exact original trajectories",
        "all 32 source-exact terminal census fields",
        "historical, fresh-process and checkpoint/restart",
        "Canonical typed bytes and identities",
        "append-only succession ledger",
        "EngineR4/newEngineR4/stepR4 typed handoff",
        "Independent C2S-SPTOI-G3-ALG review records COMPLETE",
    ):
        assert term in conditions
    assert "PARTIAL_SOURCE_LIMITED without explicit operator instruction" in exclusions
    assert amendment["operator_amendment"]["parity_criteria_may_be_weakened"] is False


def test_current_disposition_is_narrow_and_forbids_reconstruction() -> None:
    disposition = load(DISPOSITION)
    limitation = disposition["historical_limitation"]
    assert disposition["decision"] == "AUTHORISE_PARTIAL_SOURCE_LIMITED"
    assert len(limitation["case_ids"]) == 5
    assert limitation["source_recovery"] == "STOPPED_BY_OPERATOR_FOR_THESE_FIVE_CASES"
    assert limitation["trajectory_synthesis_repair_or_interpolation"] == "PROHIBITED"
    assert limitation["missing_event_chronology_inference"] == "PROHIBITED"
    assert limitation["missing_succession_ledger_inference"] == "PROHIBITED"
    assert "DISCOVERY" in limitation["re_entry_condition"]
    assert len(disposition["preserved_divergences"]) == 6


def test_corroboration_is_not_historical_parity_and_goldens_remain_frozen() -> None:
    disposition = load(DISPOSITION)
    corroboration = disposition["corroborating_evidence_only"]
    assert corroboration["cases_exact_at_aggregate_surface"] == "20/25"
    assert corroboration["aggregate_field_concordance"] == "794/800"
    assert corroboration["historical_exact_parity_claim"] is False
    assert corroboration["full_typed_stream_parity_claim"] is False
    assert {item["sha256"] for item in disposition["frozen_historical_terminal_goldens"]} == {
        "69c255faf5e7bf14cf61833abee4480f48b3c841d6ed857d68f6d1817136dce1",
        "6721f81697cc80875a51406962bb104a1c2d29fb223f2d6876a55b0f97f8e90a",
    }


def test_parity_receipt_maps_all_frozen_modes_and_scope_without_relaxation() -> None:
    receipt = load(PARITY)
    assert receipt["criteria_weakened"] is False
    assert {item["mode"] for item in receipt["mode_results"]} == {
        "HISTORICAL_FIXTURE_REPLAY",
        "FRESH_PROCESS_REPLAY",
        "CHECKPOINT_RESTART_REPLAY",
        "SERIALIZED_OUTPUT_IDENTITY",
        "TYPED_HANDOFF_SURFACE_PARITY",
    }
    historical = receipt["mode_results"][0]
    assert historical["result"] == "PARTIAL_SOURCE_LIMITED_NOT_EVALUABLE_FOR_EXACT_25_CASE_CORPUS"
    assert historical["passed_claimed"] is False
    assert len(receipt["comparison_scope_results"]) == 9
    assert all(item["source_exact_mechanics"] == "PASS" for item in receipt["comparison_scope_results"])
    assert all(item["historical_25_case_stream"] == "PARTIAL_SOURCE_LIMITED" for item in receipt["comparison_scope_results"])
    assert receipt["active_c2_authority"] == "NONE"
