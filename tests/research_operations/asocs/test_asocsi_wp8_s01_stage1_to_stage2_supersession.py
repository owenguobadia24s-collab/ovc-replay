from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[3]
WP8 = ROOT / "docs/programmes/asocs-v0-1/implementation/wp8"
STATE = ROOT / "records/research_operations/asocs"
REG = ROOT / "registries/research_operations/asocs"
SCHEMAS = ROOT / "schemas/research_operations/asocs"
STAGE2_PREP = "ASOCSI-WP8-S01-STAGE2-C2-PRIMITIVE-STRUCTURE-PREPARATION"
STAGE2_HUMAN = "ASOCSI-WP8-S01-STAGE2-C2-PRIMITIVE-STRUCTURE-HUMAN-ADJUDICATION"
NATIVE_ROUTE = "ASOCSI-WP8-S01-STAGE2-C2-NATIVE-OBSERVATION-ROUTE-AMENDMENT"
NATIVE_HUMAN = "ASOCSI-WP8-S01-STAGE2-C2-NATIVE-OBSERVATION-HUMAN-ADJUDICATION"


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_operator_supersession_is_exact_and_reserved():
    decision = load(WP8 / "ASOCSI_WP8_S01_STAGE1_TO_STAGE2_OPERATOR_SUPERSESSION_DECISION_v0_1.json")
    assert decision["authority"] == "OPERATOR"
    assert decision["operator_reserved"] is True
    assert decision["decision"] == "PASS"
    assert decision["scope"]["session"] == 1
    assert decision["scope"]["from_stage"] == "SOURCE_C1_FIDELITY"
    assert decision["scope"]["to_stage"] == "C2_PRIMITIVE_STRUCTURE"
    assert decision["scope"]["historical_stage1_route_disposition"] == "SUPERSEDED_UNCOMPLETED"
    assert decision["scope"]["stage1_scientific_conclusion"] == "NOT_ESTABLISHED"
    assert decision["scope"]["stage1_human_completion_required"] is False
    assert decision["scope"]["stage1_complete_session_freeze_required_for_stage2"] is False
    assert decision["scope"]["stage2_to_stage3_freeze_requirement_changed"] is False


def test_scoped_contract_supersedes_only_stage1_to_stage2_freeze_precondition():
    contract = load(WP8 / "ASOCSI_WP8_S01_STAGE_TRANSITION_SUPERSESSION_CONTRACT_v0_1.json")
    historical = load(WP8 / "ASOCSI_WP8_SESSION_BATCH_EXECUTION_CONTRACT_v0_1.json")
    assert historical["reveal_firewall"]["next_stage_packet_allowed_only_after_current_complete_session_stage_freeze"] is True
    assert contract["forward_supersedes"]["historical_contract_mutated"] is False
    assert contract["forward_supersedes"]["scope"] == "SESSION_1_SOURCE_C1_FIDELITY_TO_C2_PRIMITIVE_STRUCTURE_ONLY"
    assert contract["stage1_disposition"]["status"] == "SUPERSEDED_UNCOMPLETED"
    assert contract["stage1_disposition"]["human_review_completion_required"] is False
    assert contract["stage1_disposition"]["human_input_receipt_required"] is False
    assert contract["stage1_disposition"]["freeze_receipt_required"] is False
    assert contract["stage1_disposition"]["scientific_conclusion"] == "NOT_ESTABLISHED"
    assert contract["stage1_disposition"]["may_be_inferred_from_stage2"] is False
    assert contract["stage2_admission"]["allowed"] is True
    assert contract["unchanged_later_firewall"]["stage2_must_freeze_before_stage3"] is True


def test_stage2_admission_preserves_exact_frozen_case_and_source_lineage():
    admission = load(WP8 / "ASOCSI_WP8_S01_STAGE_TRANSITION_SUPERSESSION_CONTRACT_v0_1.json")["stage2_admission"]
    assert admission["case_count"] == 25
    assert admission["required_case_order"] == "EXACT_FROZEN_SESSION1_PRESENTATION_ORDER"
    assert admission["required_case_identity"] == "EXACT_FROZEN_SESSION1_CASE_IDS"
    assert admission["required_predecessor_blind_hashes"] is True
    assert admission["required_review_unit_ids"] is True
    assert admission["required_wp7_frozen_human_evidence"] is True
    assert admission["required_source_sha256"] == "210233ec5761bf82998172832bb554ddf10dfeb3099f6bc6488d5bb0f6bec4f2"
    assert admission["required_g1_audit_15m_sha256"] == "df060a22bf8a6c1d990d22af90e189848bd2c5f3090ef65a8c5637e4456bb7d9"
    assert admission["required_g3_observation_trace_sha256"] == "22c856efdd24083d5339d2082ad9714597e326a6f40655bfb82b0afa9899f7dc"
    assert admission["required_g4_review_population_sha256"] == "ff6eb37724aea5b2706666903f7b5a1bc063af8ef9026f4496429b5e33fa15fe"
    assert admission["required_stage1_case_sequence_sha256"] == "7d0f9e48b7b1ccfd44e3c38820c7dba186d0864f1be03c593ed19526ddbda986"


def test_stage2_is_still_human_governed_and_does_not_reveal_later_layers():
    contract = load(WP8 / "ASOCSI_WP8_S01_STAGE_TRANSITION_SUPERSESSION_CONTRACT_v0_1.json")
    authority = load(WP8 / "ASOCSI_WP8_S01_STAGE1_TO_STAGE2_AUTHORITY_MANIFEST_v0_1.json")
    assert contract["stage2_admission"]["stage2_human_judgement_required"] is True
    assert contract["stage2_admission"]["stage2_human_judgement_may_be_synthesized_by_agent"] is False
    assert contract["unchanged_later_firewall"]["c2e_not_revealed_at_stage2"] is True
    assert contract["unchanged_later_firewall"]["occurrence_context_not_revealed_at_stage2"] is True
    assert contract["unchanged_later_firewall"]["construct_survival_decision"] == "PROHIBITED_DURING_CASE_REVIEW"
    assert authority["operator_reserved_authority_used"] is True
    assert "NO_STAGE2_HUMAN_ANSWER_SYNTHESIS" in authority["explicit_denies"]
    assert "NO_STAGE2_TO_STAGE3_FREEZE_BYPASS" in authority["explicit_denies"]


def test_transition_schema_contract_and_current_programme_state():
    schema = load(SCHEMAS / "asocs_wp8_stage_transition_supersession_v0_1.schema.json")
    contract = load(WP8 / "ASOCSI_WP8_S01_STAGE_TRANSITION_SUPERSESSION_CONTRACT_v0_1.json")
    assert schema["properties"]["schema"]["const"] == contract["schema"]
    for required in schema["required"]:
        assert required in contract
    state = load(STATE / "ASOCSI_PROGRAMME_STATE_v0_28_WP8_S01_STAGE1_TO_STAGE2_TRANSITION_SUPERSESSION_COMPLETED.json")
    pointer = load(REG / "CURRENT_ASOCSI_STATE_POINTER.json")
    current = load(ROOT / pointer["current_state"])
    assert state["status"] == "COMPLETED"
    assert state["stage1_review_route_status"] == "SUPERSEDED_UNCOMPLETED"
    assert state["stage1_scientific_conclusion"] == "NOT_ESTABLISHED"
    assert state["stage2_preparation_authorized"] is True
    assert state["stage2_reveal_started"] is False
    assert state["stage2_human_scientific_input_required"] is True
    assert state["stage2_to_stage3_freeze_requirement_changed"] is False
    assert pointer["packet_id"] == current["packet_id"] and pointer["status"] == current["status"] and pointer["next_packet"] == current["next_packet"]
    if current["packet_id"] == STAGE2_PREP:
        assert pointer["current_state"].endswith("ASOCSI_PROGRAMME_STATE_v0_29_WP8_S01_STAGE2_C2_PRIMITIVE_STRUCTURE_PREPARATION_COMPLETED.json")
        assert current["stage1_review_route_status"] == "SUPERSEDED_UNCOMPLETED"
        assert current["stage1_scientific_conclusion"] == "NOT_ESTABLISHED"
        assert current["stage2_reveal_started"] is True
        assert current["stage2_reveal_prepared"] is True
        assert current["stage2_human_adjudication_started"] is False
        assert current["required_human_input_started"] is False
        assert current["stage2_complete_session_freeze_required_before_stage3"] is True
        assert current["stage3_reveal_started"] is False
        assert pointer["next_packet"] == STAGE2_HUMAN
    elif current["packet_id"] == STAGE2_HUMAN:
        assert pointer["current_state"].endswith("ASOCSI_PROGRAMME_STATE_v0_30_WP8_S01_STAGE2_C2_PRIMITIVE_STRUCTURE_HUMAN_ADJUDICATION_GATE_READY.json")
        assert current["status"] == "GATE_READY"
        assert current["authority_required"] == "HUMAN_SCIENTIFIC_INPUT"
        assert current["stage1_review_route_status"] == "SUPERSEDED_UNCOMPLETED"
        assert current["stage1_scientific_conclusion"] == "NOT_ESTABLISHED"
        assert current["stage2_reveal_started"] is True
        assert current["stage2_reveal_prepared"] is True
        assert current["stage2_human_adjudication_started"] is False
        assert current["required_human_input_started"] is False
        assert current["stage2_human_answer_count"] == 0
        assert current["stage2_complete_session_freeze_required_before_stage3"] is True
        assert current["stage3_reveal_started"] is False
        assert pointer["next_packet"] == STAGE2_HUMAN
    elif current["packet_id"] == NATIVE_ROUTE:
        decision = load(WP8 / "ASOCSI_WP8_S01_STAGE2_C2_NATIVE_OBSERVATION_ROUTE_OPERATOR_DECISION_v0_1.json")
        assert decision["decision"] == "PASS" and decision["operator_reserved"] is True
        assert current["status"] == "APPROVED"
        assert current["authority_required"] == "OPERATOR_REQUIRED_SATISFIED"
        assert current["stage1_review_route_status"] == "SUPERSEDED_UNCOMPLETED"
        assert current["stage1_scientific_conclusion"] == "NOT_ESTABLISHED"
        assert current["stage2_reveal_started"] is True
        assert current["stage2_reveal_prepared"] is True
        assert current["stage2_human_adjudication_started"] is False
        assert current["required_human_input_started"] is False
        assert current["stage2_human_answer_count"] == 0
        assert current["stage2_complete_session_freeze_required_before_stage3"] is True
        assert current["stage3_reveal_started"] is False
        assert current["preserved"]["g3_frozen_generation"] is True
        assert current["preserved"]["g5_blind_evidence"] is True
        assert pointer["next_packet"] == "ASOCSI-WP8-S01-STAGE2-C2-NATIVE-OBSERVATION-REPLAY"
    elif current["packet_id"] == NATIVE_HUMAN:
        assert current["status"] == "GATE_READY"
        assert current["authority_required"] == "HUMAN_SCIENTIFIC_INPUT"
        assert current["stage1_review_route_status"] == "SUPERSEDED_UNCOMPLETED"
        assert current["stage2_reveal_started"] is True
        assert current["stage2_human_adjudication_started"] is False
        assert current["stage2_human_answer_count"] == 0
        assert current["stage3_reveal_started"] is False
        assert pointer["next_packet"] == NATIVE_HUMAN
    else:
        assert pointer["current_state"].endswith("ASOCSI_PROGRAMME_STATE_v0_28_WP8_S01_STAGE1_TO_STAGE2_TRANSITION_SUPERSESSION_COMPLETED.json")
        assert pointer["next_packet"] == STAGE2_PREP


def test_qa_and_dependency_frontier_are_clear_for_stage2_preparation():
    qa = load(WP8 / "ASOCSI_WP8_S01_STAGE1_TO_STAGE2_QA_v0_1.json")
    dep = load(WP8 / "ASOCSI_WP8_S01_STAGE1_TO_STAGE2_DEPENDENCY_FRONTIER_v0_1.json")
    assert qa["qa_recommendation"] == "PASS"
    assert qa["blocking_findings"] == []
    assert dep["next_packet"] == STAGE2_PREP
    assert set(dep["not_required_for_stage2"]) == {"STAGE1_HUMAN_INPUT", "STAGE1_HUMAN_INPUT_RECEIPT", "STAGE1_COMPLETE_SESSION_FREEZE_RECEIPT", "STAGE1_HUMAN_ADJUDICATION"}
