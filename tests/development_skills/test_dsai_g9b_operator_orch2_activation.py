from __future__ import annotations

import json
from pathlib import Path

from ovc.development.skills import resolve_orch2_authority

ROOT = Path(__file__).resolve().parents[2]
DECISION = ROOT / "records/development/skills/DSAI_G9B_OPERATOR_ORCH2_ACTIVATION_PASS_20260812T205400+0100.json"
PREDECISION = ROOT / "docs/releases/development-skills-architecture-v0-1/dsai-wp9/DSAI_G9B_ORCH2_ACTIVATION_DECISION_PACKET.json"
AUTHORITY = ROOT / "registries/development/skills/orch2_low_risk_authority_v0_1.json"
AUTHORITY_SCHEMA = ROOT / "schemas/development/skills/orch2_active_authority_v0_1.schema.json"
CANDIDATE = ROOT / "registries/development/skills/orch2_activation_candidate_v0_1.json"
STATE = ROOT / "registries/implementation/dsai/OVC_DSAI_STATE_v0_26.json"
POINTER = ROOT / "registries/implementation/dsai/CURRENT_STATE_POINTER.json"


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_operator_command_materialises_exact_bounded_orch2_pass():
    decision = _load(DECISION)
    assert decision["gate_id"] == "DSAI-G9B"
    assert decision["decision"] == "PASS"
    assert decision["operator_command"] == "OVC APPROVE DSAI-G9B PASS ORCH2"
    assert decision["decision_baseline_main"] == "eed45f432f6661431fc546fc365aa3f043092697"
    activation = decision["activation"]
    assert activation["enabled_packet_classes"] == ["LOW_RISK_IMPLEMENTATION"]
    assert activation["concurrency"] == "SERIAL_REQUIRED"
    assert activation["auto_ratification"] == "WHOLLY_AUTO_EXECUTABLE_GATES_ONLY"
    assert activation["required_authority_delta"] == "NONE"
    assert activation["merge_target"] == "main"
    assert activation["merge_method"] == "squash"
    assert activation["direct_main_mutation"] is False
    assert activation["force_push"] is False
    assert activation["history_rewrite"] is False


def test_predecision_and_candidate_remain_immutable_historical_evidence():
    predecision = _load(PREDECISION)
    candidate = _load(CANDIDATE)["entries"][0]
    assert predecision["decision"] == "PENDING_OPERATOR"
    assert predecision["recommended_decision"] == "PASS"
    assert candidate["effective"] is False
    assert candidate["g9b_authority"] == "NOT_GRANTED"
    assert candidate["activation_gate"] == "DSAI-G9B"


def test_active_authority_registry_is_exact_low_risk_serial_and_closed_by_schema():
    authority = _load(AUTHORITY)
    schema = _load(AUTHORITY_SCHEMA)
    assert authority["schema"] == "ovc-dsai-orch2-authority/v1"
    assert authority["gate_id"] == "DSAI-G9B"
    assert authority["approved"] is True
    assert authority["effective"] is True
    assert authority["repository_effectivity_condition"] == "AUTHORITY_RECORD_PRESENT_ON_MAIN"
    assert authority["enabled_packet_classes"] == ["LOW_RISK_IMPLEMENTATION"]
    assert authority["concurrency"] == "SERIAL_REQUIRED"
    assert authority["gate_policy"]["required_authority_delta"] == "NONE"
    assert authority["integration_policy"]["target_branch"] == "main"
    assert authority["integration_policy"]["merge_method"] == "squash"
    assert authority["integration_policy"]["direct_main_mutation"] is False
    assert authority["integration_policy"]["force_push"] is False
    assert authority["integration_policy"]["history_rewrite"] is False
    assert authority["validation"] == "DENIED"
    assert schema["additionalProperties"] is False
    assert schema["properties"]["effective"]["const"] is True


def test_authority_resolver_requires_record_on_main_and_exact_packet_class():
    authority = _load(AUTHORITY)

    off_main = resolve_orch2_authority(
        authority=authority,
        packet_class="LOW_RISK_IMPLEMENTATION",
        record_present_on_main=False,
    )
    assert off_main["status"] == "BLOCK"
    assert off_main["g9b_orch2_authority"] is False
    assert "AUTHORITY_RECORD_NOT_PRESENT_ON_MAIN" in off_main["reason_codes"]

    wrong_class = resolve_orch2_authority(
        authority=authority,
        packet_class="UNDECLARED",
        record_present_on_main=True,
    )
    assert wrong_class["status"] == "BLOCK"
    assert "PACKET_CLASS_NOT_ENABLED" in wrong_class["reason_codes"]

    active = resolve_orch2_authority(
        authority=authority,
        packet_class="LOW_RISK_IMPLEMENTATION",
        record_present_on_main=True,
    )
    assert active["status"] == "ACTIVE_AUTHORIZED"
    assert active["g9b_orch2_authority"] is True
    assert active["reason_codes"] == ["EXACT_G9B_ORCH2_AUTHORITY_ACTIVE"]
    assert active["authority_effect"] == "READ_ONLY_RESOLUTION"


def test_programme_state_records_approval_without_premature_branch_effectivity():
    state = _load(STATE)
    assert state["programme_status"] == "WP9_G9B_PASS_ORCH2_APPROVED_PENDING_MAIN_INTEGRATION_ASSURANCE"
    assert state["packet_updates"]["DSAI-WP9"]["g9b_decision"] == "PASS_OPERATOR_ORCH2"
    assert state["orch2_authority"]["approved"] is True
    assert state["orch2_authority"]["record_effective_when_present_on_main"] is True
    assert state["orch2_authority"]["present_on_main"] is False
    assert state["authority"]["orch_2"] == "OPERATOR_APPROVED_PENDING_AUTHORITY_RECORD_MAIN_INTEGRATION"
    assert state["authority"]["automatic_merge"] is False
    assert state["authority"]["direct_main_mutation"] is False
    assert state["authority"]["force_push"] is False
    assert state["authority"]["history_rewrite"] is False
    assert state["authority"]["validation"] == "DENIED"
    assert state["mandatory_stop"]["active"] is False

    pointer = _load(POINTER)
    assert pointer["programme_id"] == "OVC-DSAI-v0.1"
    assert pointer["schema"] == "ovc-programme-current-state-pointer/v1"
    assert str(pointer["current_state"]).startswith("OVC_DSAI_STATE_v0_")
    assert str(pointer["status"]).strip()
    assert pointer["next_packet"] in {"DSAI-WP9", "DSAI-WP10", "DSAI-WP11", None}
    if pointer["next_packet"] is None:
        assert pointer["status"] == "IMPLEMENTED_ORCH2_BOUNDED_PILOTED"
