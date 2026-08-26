import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
WP8 = ROOT / "docs/programmes/asocs-v0-1/implementation/wp8"
RECORDS = ROOT / "records/research_operations/asocs"
REG = ROOT / "registries/research_operations/asocs"
NATIVE_ROUTE = "ASOCSI-WP8-S01-STAGE2-C2-NATIVE-OBSERVATION-ROUTE-AMENDMENT"
NATIVE_HUMAN = "ASOCSI-WP8-S01-STAGE2-C2-NATIVE-OBSERVATION-HUMAN-ADJUDICATION"


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_stage2_human_adjudication_gate_ready_without_agent_answers():
    template = load(WP8 / "ASOCSI_WP8_S01_STAGE2_C2_PRIMITIVE_STRUCTURE_HUMAN_INPUT_TEMPLATE_v0_1.json")
    reveal = load(WP8 / "ASOCSI_WP8_S01_STAGE2_C2_PRIMITIVE_STRUCTURE_REVEAL_INDEX_v0_1.json")
    artifact = load(WP8 / "ASOCSI_WP8_S01_STAGE2_C2_PRIMITIVE_STRUCTURE_REVIEW_WORKBOOK_ARTIFACT_v0_1.json")
    qa = load(WP8 / "ASOCSI_WP8_S01_STAGE2_C2_PRIMITIVE_STRUCTURE_HUMAN_ADJUDICATION_QA_v0_1.json")
    gate = load(WP8 / "ASOCSI_WP8_S01_STAGE2_C2_PRIMITIVE_STRUCTURE_HUMAN_INPUT_GATE_PACKET_v0_1.json")
    state = load(RECORDS / "ASOCSI_PROGRAMME_STATE_v0_30_WP8_S01_STAGE2_C2_PRIMITIVE_STRUCTURE_HUMAN_ADJUDICATION_GATE_READY.json")
    pointer = load(REG / "CURRENT_ASOCSI_STATE_POINTER.json")
    assert len(template["cases"]) == 25 == len(reveal["case_ids"])
    assert [c["case_id"] for c in template["cases"]] == reveal["case_ids"]
    assert all(c["comparison_evaluability"] is None for c in template["cases"])
    assert all(c["information_gap_disposition"] is None for c in template["cases"])
    assert all(all(v is None for v in c["component_judgements"].values()) for c in template["cases"])
    assert artifact["sha256"] == "8a040ef7067e617589612fa78410e870881e789606350827b78876a787d28d6e"
    assert artifact["byte_size"] == 5973696
    assert artifact["workbook_contract"]["human_response_prepopulation"] == "NONE"
    assert artifact["workbook_contract"]["stage3_reveal_started"] is False
    assert qa["qa_recommendation"] == "PASS" and qa["blocking_findings"] == []
    assert gate["status"] == "GATE_READY" and gate["authority_required"] == "HUMAN_SCIENTIFIC_INPUT"
    assert gate["recommended_decision"] == "DEFER"
    assert state["status"] == "GATE_READY" and state["stage2_human_answer_count"] == 0
    assert state["human_adjudication_started"] is False and state["stage3_reveal_started"] is False

    if pointer["packet_id"] == state["packet_id"]:
        assert pointer["status"] == "GATE_READY"
        assert pointer["stage2_workbook_ready"] is True and pointer["stage3_reveal_started"] is False
    else:
        assert pointer["packet_id"] in {NATIVE_ROUTE, NATIVE_HUMAN}
        assert pointer["stage3_reveal_started"] is False
        if pointer["packet_id"] == NATIVE_ROUTE:
            assert pointer["status"] == "APPROVED"
            assert pointer["repository_effective"] is False
        else:
            assert pointer["status"] == "GATE_READY"
            assert pointer["authority_required"] == "HUMAN_SCIENTIFIC_INPUT"
            assert pointer["stage2_human_answer_count"] == 0


def test_stage2_machine_non_evaluability_is_not_construct_survival():
    reveal = load(WP8 / "ASOCSI_WP8_S01_STAGE2_C2_PRIMITIVE_STRUCTURE_REVEAL_INDEX_v0_1.json")
    assert reveal["construct_survival_decision"] == "PROHIBITED_DURING_CASE_REVIEW"
    assert reveal["extraction_attestation"]["exact_primitive_not_evaluable_anchor_cases"] == 24
    assert reveal["extraction_attestation"]["exact_primitive_evaluable_anchor_cases"] == 0
    assert reveal["later_stage_firewall"]["stage3_reveal_started"] is False
