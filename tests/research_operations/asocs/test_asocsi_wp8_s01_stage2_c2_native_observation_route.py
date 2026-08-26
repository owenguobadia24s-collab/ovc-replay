import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
WP8 = ROOT / "docs/programmes/asocs-v0-1/implementation/wp8"
RECORDS = ROOT / "records/research_operations/asocs"
REG = ROOT / "registries/research_operations/asocs"


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_operator_pass_is_bounded_and_historical_approval_record_is_immutable():
    decision = load(WP8 / "ASOCSI_WP8_S01_STAGE2_C2_NATIVE_OBSERVATION_ROUTE_OPERATOR_DECISION_v0_1.json")
    effect = load(WP8 / "ASOCSI_WP8_S01_STAGE2_C2_NATIVE_OBSERVATION_ROUTE_AUTHORITY_EFFECT_v0_1.json")
    state = load(RECORDS / "ASOCSI_PROGRAMME_STATE_v0_32_WP8_S01_STAGE2_C2_NATIVE_OBSERVATION_ROUTE_APPROVED.json")
    pointer = load(REG / "CURRENT_ASOCSI_STATE_POINTER.json")

    assert decision["gate_id"] == "ASOCSI-WP8-S01-STAGE2-C2-NATIVE-OBSERVATION-ROUTE"
    assert decision["decision"] == "PASS" and decision["authority"] == "OPERATOR"
    assert decision["approved_scope"]["replay_class"] == "C2_NATIVE_RUNTIME_AUDIT_REPLAY_NONAUTHORITATIVE"
    assert decision["approved_scope"]["stage3_reveal_before_stage2_freeze"] is False
    assert effect["active_only_after_repository_effective_operator_decision"] is True
    assert "C2_SEMANTIC_THRESHOLD_MODEL_FAMILY_SELECTOR_OR_IMPLEMENTATION_CHANGE" in effect["non_grants"]
    assert "VALIDATION" in effect["non_grants"]
    assert state["status"] == "APPROVED" and state["repository_effective"] is False
    assert pointer["status"] in {"APPROVED", "GATE_READY"}
    if pointer["status"] == "APPROVED":
        assert pointer["repository_effective"] is False
    else:
        assert pointer["repository_effective"] is True
        assert pointer["authority_required"] == "HUMAN_SCIENTIFIC_INPUT"
        assert pointer["replay_complete"] is True
    assert pointer["stage3_reveal_started"] is False
    assert pointer["next_packet"] in {
        "ASOCSI-WP8-S01-STAGE2-C2-NATIVE-OBSERVATION-REPLAY",
        "ASOCSI-WP8-S01-STAGE2-C2-NATIVE-OBSERVATION-HUMAN-ADJUDICATION",
    }


def test_forensic_bid_utc_binding_does_not_backfill_historical_provenance():
    evidence = load(WP8 / "ASOCSI_WP8_S01_STAGE2_C2_NATIVE_OBSERVATION_FORENSIC_EVIDENCE_v0_1.json")
    decision = load(WP8 / "ASOCSI_WP8_S01_STAGE2_C2_NATIVE_OBSERVATION_ROUTE_OPERATOR_DECISION_v0_1.json")

    assert evidence["forensic_binding_candidate"]["price_side"] == "BID"
    assert evidence["forensic_binding_candidate"]["price_side_classification"] == "FORENSICALLY_SUPPORTED_NOT_DECLARED"
    assert evidence["forensic_binding_candidate"]["timestamp_timezone"] == "UTC"
    assert evidence["forensic_binding_candidate"]["timestamp_timezone_classification"] == "FORENSICALLY_SUPPORTED_NOT_DECLARED"
    assert evidence["historical_source_provenance_preserved"]["price_side"] == "UNRESOLVED_SINGLE_STREAM"
    assert evidence["historical_source_provenance_preserved"]["timestamp_timezone"] == "SOURCE_TIMEZONE_UNRESOLVED"
    assert evidence["historical_source_provenance_preserved"]["wp1_wp4_backfill"] == "PROHIBITED"
    assert "DO_NOT_BACKFILL_HISTORICAL_WP1_WP4_SOURCE_PROVENANCE" in decision["prohibitions"]
    assert "DO_NOT_TREAT_BID_OR_UTC_AS_DECLARED_PROVIDER_PROVENANCE" in decision["prohibitions"]


def test_vit_route_contract_preserves_frozen_runtime_and_human_boundary():
    manifest = load(WP8 / "ASOCSI_WP8_S01_STAGE2_C2_NATIVE_OBSERVATION_ROUTE_AUTHORITY_MANIFEST_v0_1.json")
    frontier = load(WP8 / "ASOCSI_WP8_S01_STAGE2_C2_NATIVE_OBSERVATION_ROUTE_DEPENDENCY_FRONTIER_v0_1.json")
    evidence = load(WP8 / "ASOCSI_WP8_S01_STAGE2_C2_NATIVE_OBSERVATION_FORENSIC_EVIDENCE_v0_1.json")

    assert manifest["authority_required"] == "OPERATOR_REQUIRED_SATISFIED"
    assert manifest["agent_may_supply_human_answer"] is False
    assert manifest["human_judgement_authority"] == "HUMAN_REVIEWER_ONLY_NO_AGENT_SYNTHESIS"
    assert manifest["replay_class"] == "C2_NATIVE_RUNTIME_AUDIT_REPLAY_NONAUTHORITATIVE"
    assert "AGENT_SYNTHESIZED_HUMAN_ANSWERS" in manifest["prohibited"]
    assert "STAGE3_REVEAL_BEFORE_REPLACEMENT_STAGE2_FREEZE" in manifest["prohibited"]
    assert frontier["runtime_constraints"]["deterministic_replay_count_required"] == 2
    assert frontier["runtime_constraints"]["meaning_bearing_reimplementation_allowed"] is False
    assert frontier["runtime_constraints"]["result_tuning_allowed"] is False
    assert frontier["runtime_constraints"]["historical_provenance_mutation_allowed"] is False
    assert frontier["runtime_constraints"]["stage3_reveal_started"] is False
    assert frontier["runtime_constraints"]["c2_components"] == ["HORIZON", "LEVEL", "CONTAINER", "RELATION"]
    assert evidence["c2_runtime_binding"]["package_id"] == "C2AR.INTEGRATED.SHADOW.PACKAGE.v1"
    assert evidence["c2_runtime_binding"]["package_sha256"] == "150de1997be8801baa59db6d0fe98b11cb21a6b70525b908537aeb31bfd00cc3"
