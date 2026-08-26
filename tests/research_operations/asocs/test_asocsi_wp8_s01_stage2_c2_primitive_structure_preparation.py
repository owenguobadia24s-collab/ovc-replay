from __future__ import annotations

import json
from pathlib import Path

from ovc.research_operations.asocs.stage2_primitive import NOT_EVALUABLE_REASONS, PRIMITIVE_COMPONENTS, validate_reveal_index

ROOT = Path(__file__).resolve().parents[3]
WP8 = ROOT / "docs/programmes/asocs-v0-1/implementation/wp8"
STATE = ROOT / "records/research_operations/asocs/ASOCSI_PROGRAMME_STATE_v0_29_WP8_S01_STAGE2_C2_PRIMITIVE_STRUCTURE_PREPARATION_COMPLETED.json"
POINTER = ROOT / "registries/research_operations/asocs/CURRENT_ASOCSI_STATE_POINTER.json"
NATIVE_ROUTE = "ASOCSI-WP8-S01-STAGE2-C2-NATIVE-OBSERVATION-ROUTE-AMENDMENT"
EXPECTED = ["ASOCS.BLIND.4754b461b4d0fff17a48b9eb","ASOCS.BLIND.66ed33d51319ec6923d4d0a5","ASOCS.BLIND.bc9bf3421a7e26e25f204668","ASOCS.BLIND.b29062d1bc3ebbb66455bef6","ASOCS.BLIND.1f8bc89c69d001ae26eececa","ASOCS.BLIND.08b1a69e8ae7a932252d6c85","ASOCS.BLIND.7c804e44e9649cd5ba7bd0f9","ASOCS.BLIND.2e735b1ba24f0eccd71b0d18","ASOCS.BLIND.b7c0e102063d8f36e0084c3b","ASOCS.BLIND.c5b46b7db1bd2110b2b98c7b","ASOCS.BLIND.539a860dab8f502cd93cad0f","ASOCS.BLIND.770ac4e6a4cffeb24b38dc3d","ASOCS.BLIND.c806f636d7e145093324e254","ASOCS.BLIND.6693a6a9f42409f28e5af384","ASOCS.BLIND.bd0368cea8222d7e4803bedd","ASOCS.BLIND.cdb4dcea08349fd47ba5dd4b","ASOCS.BLIND.eda8205f083aeccdd329b0eb","ASOCS.BLIND.7f651c59741204ac3cf210bc","ASOCS.BLIND.9b251b8cfedc5e9a61396830","ASOCS.BLIND.32819f869b3c3b07dd7f1e2f","ASOCS.BLIND.52bfd1e5b5ac49076e79857b","ASOCS.BLIND.02b2078de685b0c1dca5553d","ASOCS.BLIND.cd6ce56499538e84b15d00a3","ASOCS.BLIND.df8018099acd005f8c7a46ed","ASOCS.BLIND.d95379bbf26c667d05db8cd3"]


def j(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_stage2_reveal_index_is_exact_primitive_only() -> None:
    reveal = j(WP8 / "ASOCSI_WP8_S01_STAGE2_C2_PRIMITIVE_STRUCTURE_REVEAL_INDEX_v0_1.json")
    validate_reveal_index(reveal)
    assert reveal["case_ids"] == EXPECTED
    assert [b["case_id"] for b in reveal["case_bindings"]] == EXPECTED
    assert [b["presentation_ordinal"] for b in reveal["case_bindings"]] == list(range(1, 26))
    assert all(len(b["predecessor_blind_record_sha256"]) == 64 for b in reveal["case_bindings"])
    assert all(b["review_unit_id"].startswith("asocs:") for b in reveal["case_bindings"])
    anchors = [b for b in reveal["case_bindings"] if b["kind"] == "ANCHOR_15M"]
    gaps = [b for b in reveal["case_bindings"] if b["kind"] == "SOURCE_GAP"]
    assert len(anchors) == 24 and len(gaps) == 1
    assert all(len(b["trace_sha256"]) == 64 for b in anchors)
    assert gaps[0]["case_id"] == "ASOCS.BLIND.9b251b8cfedc5e9a61396830"
    assert reveal["revealed_evidence_surface"] == ["C2_HORIZON_MEMBERSHIP","C2_LEVEL_CANDIDATES_AND_EMITTED_LEVELS","C2_CONTAINER_PAIRING_CANDIDATES_AND_DISPOSITIONS","C2_RELATION_INVENTORY"]
    assert tuple(reveal["frozen_primitive_profile"]) == PRIMITIVE_COMPONENTS
    for key, record in reveal["frozen_primitive_profile"].items():
        assert record["construct"] == key and record["disposition"] == "NOT_EVALUABLE"
        assert tuple(record["reason_codes"]) == NOT_EVALUABLE_REASONS
        assert record["active"] is False and record["canonical"] is False and record["publication"] is False


def test_no_stage3_or_upper_reveal_and_no_stage1_backfill() -> None:
    reveal = j(WP8 / "ASOCSI_WP8_S01_STAGE2_C2_PRIMITIVE_STRUCTURE_REVEAL_INDEX_v0_1.json")
    text = json.dumps(reveal)
    for forbidden in ["C2_FORMULA","C2_TRANSITION","C2_PARENT_CONTEXT","C2_COMPUTABILITY","C2E_EPISODE","C2E_PHASE","OCCURRENCE_CONTEXT_ATTACHMENT"]:
        assert forbidden not in text
    assert reveal["stage1_review_route_status"] == "SUPERSEDED_UNCOMPLETED"
    assert reveal["stage1_scientific_conclusion"] == "NOT_ESTABLISHED"
    assert reveal["human_judgements"] == []
    assert reveal["later_stage_firewall"]["stage2_complete_session_freeze_required_before_stage3"] is True
    assert reveal["later_stage_firewall"]["stage3_reveal_started"] is False


def test_human_template_has_25_empty_reviewer_placeholders_and_state_stops() -> None:
    template = j(WP8 / "ASOCSI_WP8_S01_STAGE2_C2_PRIMITIVE_STRUCTURE_HUMAN_INPUT_TEMPLATE_v0_1.json")
    state = j(STATE)
    pointer = j(POINTER)
    assert [c["case_id"] for c in template["cases"]] == EXPECTED
    assert len(template["cases"]) == 25
    for case in template["cases"]:
        assert case["comparison_evaluability"] is None
        assert case["information_gap_disposition"] is None
        assert case["construct_survival_decision"] == "PROHIBITED_DURING_CASE_REVIEW"
        assert all(v is None for v in case["component_judgements"].values())
    assert template["submission_rules"]["no_agent_answer_synthesis"] is True
    assert state["status"] == "COMPLETED" and state["human_scientific_input_boundary"] is True
    assert state["required_human_input_started"] is False and state["stage2_human_adjudication_started"] is False
    assert state["stage3_reveal_started"] is False
    if pointer["packet_id"] == state["packet_id"]:
        assert pointer["next_packet"] == state["next_packet"]
    else:
        assert pointer["packet_id"] == NATIVE_ROUTE
        assert pointer["status"] == "APPROVED"
        assert pointer["repository_effective"] is False
        assert pointer["stage3_reveal_started"] is False
        current = j(ROOT / pointer["current_state"])
        decision = j(WP8 / "ASOCSI_WP8_S01_STAGE2_C2_NATIVE_OBSERVATION_ROUTE_OPERATOR_DECISION_v0_1.json")
        assert decision["decision"] == "PASS" and decision["operator_reserved"] is True
        assert decision["approved_scope"]["historical_stage2_questionnaire_disposition"] == "SUPERSEDED_UNCOMPLETED"
        assert current["stage2_abstract_questionnaire_status"] == "OPERATOR_APPROVED_FORWARD_SUPERSESSION_PENDING_REPOSITORY_EFFECT"
        assert current["stage3_reveal_started"] is False


def test_qa_pass_and_judgement_schema_prohibits_construct_survival() -> None:
    qa = j(WP8 / "ASOCSI_WP8_S01_STAGE2_C2_PRIMITIVE_STRUCTURE_QA_v0_1.json")
    schema = j(ROOT / "schemas/research_operations/asocs/asocs_c2_primitive_structure_judgement_v0_1.schema.json")
    assert qa["qa_recommendation"] == "PASS" and qa["blocking_findings"] == []
    assert qa["next_boundary"] == "HUMAN_SCIENTIFIC_INPUT"
    assert schema["properties"]["construct_survival_decision"]["const"] == "PROHIBITED_DURING_CASE_REVIEW"
    assert set(schema["properties"]["component_judgements"]["properties"]) == {"HORIZON","LEVEL","CONTAINER","RELATION"}
