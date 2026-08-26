import json
from pathlib import Path

from ovc.research_operations.asocs.stage2_native_replay import (
    REPLAY_CLASS,
    canonical_bytes,
    forensic_binding,
)


ROOT = Path(__file__).resolve().parents[3]
WP8 = ROOT / "docs/programmes/asocs-v0-1/implementation/wp8"
RECORDS = ROOT / "records/research_operations/asocs"
REGISTRY = ROOT / "registries/research_operations/asocs"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_forensic_binding_is_audit_only_and_does_not_backfill_provenance():
    record = load(WP8 / "ASOCSI_WP8_S01_STAGE2_C2_NATIVE_OBSERVATION_REPLAY_FORENSIC_BINDING_v0_1.json")
    runtime = forensic_binding()
    for value in (record, runtime):
        assert value["replay_class"] == REPLAY_CLASS
        assert value["price_side"] == {"value": "BID", "classification": "FORENSICALLY_SUPPORTED_NOT_DECLARED"}
        assert value["timestamp_timezone"] == {"value": "UTC", "classification": "FORENSICALLY_SUPPORTED_NOT_DECLARED"}
        assert value["historical_wp1_wp4_provenance_mutated"] is False
        assert value["declared_provider_provenance"] is False
        assert value["active_source_identity"] is False


def test_replay_receipt_binds_exact_inputs_route_merge_and_two_equal_runs():
    execution = load(WP8 / "ASOCSI_WP8_S01_STAGE2_C2_NATIVE_OBSERVATION_REPLAY_EXECUTION_RECEIPT_v0_1.json")
    deterministic = load(WP8 / "ASOCSI_WP8_S01_STAGE2_C2_NATIVE_OBSERVATION_REPLAY_DETERMINISM_RECEIPT_v0_1.json")
    assert execution["route_amendment_integration"]["physical_squash_merge_sha"] == "e0341ed634600e9d68c4ee5696d310c103551cb6"
    assert execution["route_amendment_integration"]["physical_merge_tree"] == "606ce0ceeeec92bc72f6e1332d6bde96be4b1c0d"
    assert execution["exact_inputs"]["c2_package_sha256"] == "150de1997be8801baa59db6d0fe98b11cb21a6b70525b908537aeb31bfd00cc3"
    assert execution["runtime_result"]["independent_run_count"] == 2
    assert deterministic["result"] == "PASS_TWO_INDEPENDENT_IDENTITY_BEARING_REPLAYS_AGREE"
    assert deterministic["identity_bearing_projection_equal"] is True
    assert execution["runtime_result"]["identity_bearing_sha256"] == deterministic["identity_bearing_sha256"]
    assert deterministic["run_a"]["logical_sha256"] != deterministic["run_b"]["logical_sha256"]


def test_reveal_has_actual_native_components_in_exact_order_and_no_gap_fabrication():
    reveal = load(WP8 / "ASOCSI_WP8_S01_STAGE2_C2_NATIVE_OBSERVATION_REPLAY_REVEAL_INDEX_v0_1.json")
    assert reveal["replay_class"] == REPLAY_CLASS
    assert reveal["case_count"] == len(reveal["case_ids"]) == len(reveal["cases"]) == 25
    assert reveal["case_ids"] == [case["case_id"] for case in reveal["cases"]]
    native = [case for case in reveal["cases"] if case["status"] == "C2_NATIVE_OBSERVATION_AVAILABLE"]
    gaps = [case for case in reveal["cases"] if case["status"] == "SOURCE_GAP_C2_NOT_FABRICATED"]
    assert len(native) == 24 and len(gaps) == 1
    assert all("observation" in case and len(case["horizons"]) == 3 for case in native)
    assert all(set(case) >= {"horizons", "levels", "containers", "relation_sets", "relations"} for case in native)
    assert gaps[0]["presentation_ordinal"] == 19
    assert all(gaps[0][key] == [] for key in ("horizons", "levels", "containers", "relation_sets", "relations"))
    assert reveal["human_judgements"] == []
    assert reveal["construct_survival_decision"] == "PROHIBITED_DURING_CASE_REVIEW"
    assert reveal["later_stage_firewall"]["stage3_reveal_started"] is False
    assert reveal["later_stage_firewall"]["c2e_included"] is False
    assert reveal["later_stage_firewall"]["occurrence_context_included"] is False


def test_replacement_workbook_binding_and_template_stop_at_human_boundary():
    template = load(WP8 / "ASOCSI_WP8_S01_STAGE2_C2_NATIVE_OBSERVATION_HUMAN_INPUT_TEMPLATE_v0_1.json")
    artifact = load(WP8 / "ASOCSI_WP8_S01_STAGE2_C2_NATIVE_OBSERVATION_REVIEW_WORKBOOK_ARTIFACT_v0_1.json")
    gate = load(WP8 / "ASOCSI_WP8_S01_STAGE2_C2_NATIVE_OBSERVATION_HUMAN_INPUT_GATE_PACKET_v0_1.json")
    state = load(RECORDS / "ASOCSI_PROGRAMME_STATE_v0_33_WP8_S01_STAGE2_C2_NATIVE_OBSERVATION_HUMAN_ADJUDICATION_GATE_READY.json")
    pointer = load(REGISTRY / "CURRENT_ASOCSI_STATE_POINTER.json")
    assert len(template["cases"]) == 25
    for case in template["cases"]:
        assert case["comparison_evaluability"] is None
        assert case["information_gap_disposition"] is None
        assert all(value is None for value in case["component_judgements"].values())
        assert case["construct_survival_decision"] == "PROHIBITED_DURING_CASE_REVIEW"
    assert artifact["sha256"] == "2577f0273df0d88aa150eed586a7efc47eab2d28aaa61446e0a112413253dbaa"
    assert artifact["workbook_contract"]["actual_c2_components"] == ["HORIZON", "LEVEL", "CONTAINER", "RELATION"]
    assert artifact["workbook_contract"]["human_response_prepopulation"] == "NONE"
    assert gate["status"] == state["status"] == pointer["status"] == "GATE_READY"
    assert gate["authority_required"] == state["authority_required"] == pointer["authority_required"] == "HUMAN_SCIENTIFIC_INPUT"
    assert state["stage2_human_answer_count"] == pointer["stage2_human_answer_count"] == 0
    assert state["stage3_reveal_started"] is pointer["stage3_reveal_started"] is False
    assert pointer["current_state"].endswith(state_path_name())


def state_path_name():
    return "ASOCSI_PROGRAMME_STATE_v0_33_WP8_S01_STAGE2_C2_NATIVE_OBSERVATION_HUMAN_ADJUDICATION_GATE_READY.json"


def test_canonical_serialization_normalises_runtime_sets_without_semantic_mutation():
    assert canonical_bytes({"ids": {"b", "a"}, "nested": ({"z"},)}) == b'{"ids":["a","b"],"nested":[["z"]]}'
