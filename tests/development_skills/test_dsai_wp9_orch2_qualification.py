from __future__ import annotations

import json
from pathlib import Path

from ovc.development.skills import (
    build_orch2_interruption_reconciliation,
    evaluate_delegated_gate,
    qualify_orch2_single_packet_cycle,
)

ROOT = Path(__file__).resolve().parents[2]
A = "a" * 40
B = "b" * 40
C = "c" * 40


def _cycle(**overrides):
    values = {
        "packet_id": "DSAI-WP9-PILOT-001",
        "packet_class": "LOW_RISK_IMPLEMENTATION",
        "enabled_packet_classes": ["LOW_RISK_IMPLEMENTATION"],
        "serial_slot_available": True,
        "baseline_main_sha": A,
        "current_main_sha": A,
        "head_sha": B,
        "required_checks": {"tests": "success", "runner-parity": "success", "pytest-unittest-parity": "success"},
        "qa_status": "PASS",
        "changed_paths": ["src/ovc/development/skills/pilot.py"],
        "scope_id": "DSAI-WP9.PILOT.001",
        "gate_class": "AUTO_EXECUTABLE",
        "authority_delta": "NONE",
        "acceptance_conditions_pass": True,
        "prerequisites_satisfied": True,
        "g9a_trusted": True,
        "g9b_orch2_authority": True,
        "blocking_warnings": [],
        "unresolved_reviews": [],
        "remediation_actions": [],
        "simulated_result_main_sha": C,
    }
    values.update(overrides)
    return qualify_orch2_single_packet_cycle(**values)


def test_wholly_non_reserved_gate_is_only_projected_auto_ratifiable():
    row = evaluate_delegated_gate(
        gate_class="AUTO_EXECUTABLE",
        authority_delta="NONE",
        acceptance_conditions_pass=True,
        qa_status="PASS",
        prerequisites_satisfied=True,
    )
    assert row["status"] == "AUTO_RATIFIABLE"
    assert row["delegated_decision_effective"] is False
    assert row["authority_effect"] == "NONE"


def test_operator_or_authority_delta_gate_stops_before_merge():
    operator = evaluate_delegated_gate(
        gate_class="OPERATOR_REQUIRED",
        authority_delta="NONE",
        acceptance_conditions_pass=True,
        qa_status="PASS",
        prerequisites_satisfied=True,
    )
    assert operator["status"] == "STOP_BEFORE_MERGE"
    assert "OPERATOR_RESERVED_GATE" in operator["reason_codes"]

    authority = evaluate_delegated_gate(
        gate_class="AUTO_EXECUTABLE",
        authority_delta="TRUSTED_PROMOTION",
        acceptance_conditions_pass=True,
        qa_status="PASS",
        prerequisites_satisfied=True,
    )
    assert authority["status"] == "STOP_BEFORE_MERGE"
    assert "AUTHORITY_DELTA_NOT_AUTO_EXECUTABLE" in authority["reason_codes"]


def test_golden_single_packet_cycle_is_serial_sandbox_only():
    row = _cycle()
    assert row["status"] == "SANDBOX_PASS"
    assert row["concurrency"] == "SERIAL_REQUIRED"
    assert row["execution_mode"] == "SANDBOX_ONLY_PRE_G9B"
    assert row["gate_evaluation"]["status"] == "AUTO_RATIFIABLE"
    assert row["merge_preparation"]["status"] == "READY_FOR_REVALIDATION"
    assert row["merge_revalidation"]["status"] == "PASS_REVALIDATED"
    assert row["merge_execution_intent"]["status"] == "ELIGIBLE"
    assert row["sandbox_merge_receipt"]["status"] == "PASS"
    assert row["sandbox_merge_receipt"]["simulation_only"] is True
    assert row["automatic_merge_performed"] is False
    assert row["repository_side_effect_performed"] is False


def test_g9a_g9b_packet_class_and_serial_barriers_fail_closed():
    cases = [
        ({"g9a_trusted": False}, "DSAI_G9A_TRUST_REQUIRED"),
        ({"g9b_orch2_authority": False}, "DSAI_G9B_ORCH2_AUTHORITY_REQUIRED"),
        ({"packet_class": "UNDECLARED"}, "PACKET_CLASS_NOT_ENABLED"),
        ({"serial_slot_available": False}, "SERIAL_SLOT_NOT_AVAILABLE"),
    ]
    for overrides, reason in cases:
        row = _cycle(**overrides)
        assert row["status"] == "BLOCK"
        assert reason in row["reason_codes"]
        assert row["repository_side_effect_performed"] is False


def test_assurance_gate_and_current_main_failures_block():
    cases = [
        ({"current_main_sha": C}, "MAIN_HEAD_CHURN"),
        ({"gate_class": "OPERATOR_REQUIRED"}, "GATE_NOT_AUTO_RATIFIABLE"),
        ({"authority_delta": "TRUSTED_PROMOTION"}, "GATE_NOT_AUTO_RATIFIABLE"),
        ({"acceptance_conditions_pass": False}, "GATE_NOT_AUTO_RATIFIABLE"),
        ({"qa_status": "FAIL"}, "GATE_NOT_AUTO_RATIFIABLE"),
        ({"required_checks": {"tests": "failure"}}, "MERGE_PREPARATION_BLOCKED"),
        ({"prerequisites_satisfied": False}, "GATE_NOT_AUTO_RATIFIABLE"),
        ({"blocking_warnings": ["warning"]}, "GATE_NOT_AUTO_RATIFIABLE"),
        ({"unresolved_reviews": ["review"]}, "GATE_NOT_AUTO_RATIFIABLE"),
    ]
    for overrides, reason in cases:
        row = _cycle(**overrides)
        assert row["status"] == "BLOCK"
        assert reason in row["reason_codes"]


def test_merge_races_block_at_exact_revalidation():
    base_race = _cycle(revalidation_base_sha=C)
    assert base_race["status"] == "BLOCK"
    assert "MERGE_REVALIDATION_BLOCKED" in base_race["reason_codes"]
    assert "BASE_SHA_DRIFT" in base_race["merge_revalidation"]["reason_codes"]

    head_race = _cycle(revalidation_head_sha=C)
    assert head_race["status"] == "BLOCK"
    assert "MERGE_REVALIDATION_BLOCKED" in head_race["reason_codes"]
    assert "HEAD_SHA_DRIFT" in head_race["merge_revalidation"]["reason_codes"]


def test_remediation_is_bounded_and_cannot_weaken_frozen_controls():
    safe = _cycle(remediation_actions=["FIX_IMPLEMENTATION_DEFECT"])
    assert safe["status"] == "SANDBOX_PASS"
    assert len(safe["remediation_records"]) == 1
    assert safe["remediation_records"][0]["authority_delta"] == "NONE"

    forbidden = _cycle(remediation_actions=["TEST_WEAKEN"])
    assert forbidden["status"] == "BLOCK"
    assert "FORBIDDEN_REMEDIATION_ACTION" in forbidden["reason_codes"]
    assert forbidden["remediation_records"] == []


def test_interruption_recovery_requires_reconciliation_after_possible_side_effect():
    pre = build_orch2_interruption_reconciliation(merge_plan_id="d" * 64, side_effect_observed=False)
    assert pre["status"] == "SAFE_TO_RETRY_FROM_PREPARE"
    post = build_orch2_interruption_reconciliation(merge_plan_id="d" * 64, side_effect_observed=True)
    assert post["status"] == "BLOCK_RECONCILIATION_REQUIRED"
    assert post["automatic_retry"] is False
    assert post["force_push"] is False
    assert post["history_rewrite"] is False


def test_orch2_contract_registry_schema_and_fixture_are_pre_g9b_non_authoritative():
    contract = json.loads((ROOT / "contracts/development/skills/orch2_single_packet_authority_v0_1.json").read_text(encoding="utf-8"))
    assert contract["authority_effect"] == "NONE_PRE_G9B"
    assert contract["candidate_policy"]["concurrency"] == "SERIAL_REQUIRED"
    assert contract["candidate_policy"]["candidate_enabled_packet_classes"] == ["LOW_RISK_IMPLEMENTATION"]

    registry = json.loads((ROOT / "registries/development/skills/orch2_activation_candidate_v0_1.json").read_text(encoding="utf-8"))
    candidate = registry["entries"][0]
    assert candidate["effective"] is False
    assert candidate["g9b_authority"] == "NOT_GRANTED"
    assert candidate["automatic_merge"] == "INACTIVE_PENDING_G9B"
    assert candidate["direct_main_mutation"] is False

    schema = json.loads((ROOT / "schemas/development/skills/orch2_single_packet_sandbox_v0_1.schema.json").read_text(encoding="utf-8"))
    assert schema["additionalProperties"] is False
    assert schema["properties"]["repository_side_effect_performed"]["const"] is False

    fixtures = json.loads((ROOT / "fixtures/development_skills/wp9_orch2_single_packet_cases_v0_1.json").read_text(encoding="utf-8"))
    assert fixtures["authority_effect"] == "NONE"
    assert len(fixtures["cases"]) >= 19
