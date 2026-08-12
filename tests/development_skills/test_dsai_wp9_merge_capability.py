from __future__ import annotations

import json
from pathlib import Path

from ovc.development.skills import (
    BaseFreshnessPolicy,
    build_merge_execution_intent,
    build_merge_recovery_record,
    build_skill_release_bundle,
    git_packet_dry_run,
    prepare_merge_candidate,
    revalidate_merge_candidate,
    simulate_squash_merge,
)

ROOT = Path(__file__).resolve().parents[2]
A = "a" * 40
B = "b" * 40
C = "c" * 40
RELEASE = "OVC-SKILL-014@0.2.0+sha256:e000ce135ff4e9a17d4f29ddfb61ba5bd3474fdd9f89e7e9814bf43eee5deff5"


def _prepare(**overrides):
    values = {
        "pull_request_number": 9001,
        "base_branch": "main",
        "base_sha": A,
        "head_sha": B,
        "required_checks": {"tests": "success", "OVC merge readiness": "success"},
        "qa_status": "PASS",
        "changed_paths": ["src/ovc/development/skills/merge_capability.py"],
        "scope_id": "DSAI-WP9.TEST",
        "authority_delta": "NONE",
        "auto_ratifiable": True,
        "operator_required": False,
        "prerequisites_satisfied": True,
        "blocking_warnings": [],
        "unresolved_reviews": [],
    }
    values.update(overrides)
    return prepare_merge_candidate(**values)


def _revalidate(prepared, **overrides):
    values = {
        "current_base_sha": A,
        "current_head_sha": B,
        "required_checks": {"tests": "success", "OVC merge readiness": "success"},
        "qa_status": "PASS",
        "changed_paths": ["src/ovc/development/skills/merge_capability.py"],
        "scope_id": "DSAI-WP9.TEST",
        "authority_delta": "NONE",
        "auto_ratifiable": True,
        "operator_required": False,
        "prerequisites_satisfied": True,
        "blocking_warnings": [],
        "unresolved_reviews": [],
    }
    values.update(overrides)
    return revalidate_merge_candidate(prepared, **values)


def test_exact_skill_release_rebuild_and_historical_merge_denial_remain_separate():
    fields = {
        "capability_ids": ["GIT_PACKET_MANAGEMENT"],
        "execution_mode": "SHADOW_OR_SANDBOX_PRE_G9A_G9B",
        "implementation_entrypoint": "ovc.development.skills.merge_capability:prepare_merge_candidate",
        "input_contract_id": "DSAI.WP9.GIT_MERGE_CAPABILITY.INPUT.v1",
        "output_contract_id": "ovc-dsai-merge-preparation/v1",
        "tool_profile_id": "WP9-GIT-MERGE-PREPARE",
        "write_permission": "DENY_PRE_G9A_G9B",
        "merge_execution_requires": ["DSAI-G9A_TRUSTED_TUPLE", "DSAI-G9B_ORCH2_PACKET_CLASS"],
        "force_push": "FORBIDDEN",
        "history_rewrite": "FORBIDDEN",
        "failure_policy": "FAIL_CLOSED",
        "authority_effect": "NONE",
    }
    rebuilt = build_skill_release_bundle(
        skill_id="OVC-SKILL-014",
        logical_name="ovc-git-packet-manager",
        semantic_version="0.2.0",
        fields=fields,
        field_classification={key: "NORMATIVE" for key in fields},
        source_refs=["OVC-DSA-DESIGN-SPEC-0.1-REVISED-1-RATIFIED", "OVC-DSAI-IMPLEMENTATION-PLAN-0.2"],
    )
    assert rebuilt["release_id"] == RELEASE

    fresh = BaseFreshnessPolicy().assess(
        baseline_main_sha=A,
        current_main_sha=A,
        commit_distance=0,
        elapsed_minutes=1,
        dependency_or_write_overlap=False,
        mutating=True,
        merge_candidate=False,
    )
    historical = git_packet_dry_run(actions=["MERGE"], paths=["src/ovc/x.py"], freshness=fresh)
    assert historical["status"] == "BLOCK"
    assert historical["merge_capability"] == "DISABLED_UNTRUSTED"


def test_golden_prepare_and_exact_revalidation_are_side_effect_free():
    prepared = _prepare()
    assert prepared["status"] == "READY_FOR_REVALIDATION"
    assert prepared["merge_authority"] == "NONE"
    assert prepared["automatic_merge"] is False
    assert prepared["side_effect_performed"] is False

    revalidated = _revalidate(prepared)
    assert revalidated["status"] == "PASS_REVALIDATED"
    assert revalidated["side_effect_performed"] is False
    assert revalidated["merge_authority"] == "NONE"


def test_prepare_blocks_failed_assurance_or_reserved_authority():
    cases = [
        ({"required_checks": {"tests": "failure"}}, "REQUIRED_CHECK_NOT_PASS"),
        ({"qa_status": "FAIL"}, "QA_NOT_PASS"),
        ({"authority_delta": "TRUSTED_PROMOTION"}, "AUTHORITY_DELTA_NOT_AUTO_EXECUTABLE"),
        ({"operator_required": True}, "OPERATOR_RESERVED_AUTHORITY_PRESENT"),
        ({"blocking_warnings": ["warning"]}, "BLOCKING_WARNING_PRESENT"),
        ({"unresolved_reviews": ["review-1"]}, "UNRESOLVED_REVIEW_PRESENT"),
    ]
    for overrides, reason in cases:
        row = _prepare(**overrides)
        assert row["status"] == "BLOCK"
        assert reason in row["reason_codes"]
        assert row["side_effect_performed"] is False


def test_revalidation_blocks_every_material_drift():
    prepared = _prepare()
    cases = [
        ({"current_base_sha": C}, "BASE_SHA_DRIFT"),
        ({"current_head_sha": C}, "HEAD_SHA_DRIFT"),
        ({"required_checks": {"tests": "success"}}, "CHECK_SET_OR_RESULT_DRIFT"),
        ({"qa_status": "FAIL"}, "QA_STATUS_DRIFT"),
        ({"changed_paths": ["src/ovc/other.py"]}, "SCOPE_PATH_DRIFT"),
        ({"scope_id": "OTHER"}, "SCOPE_ID_DRIFT"),
        ({"authority_delta": "TRUSTED_PROMOTION"}, "AUTHORITY_DELTA_DRIFT"),
        ({"auto_ratifiable": False}, "AUTO_RATIFIABLE_DRIFT"),
        ({"operator_required": True}, "OPERATOR_AUTHORITY_DRIFT"),
        ({"prerequisites_satisfied": False}, "PREREQUISITE_DRIFT"),
        ({"blocking_warnings": ["warning"]}, "WARNING_SET_DRIFT"),
        ({"unresolved_reviews": ["review-1"]}, "REVIEW_SET_DRIFT"),
    ]
    for overrides, reason in cases:
        row = _revalidate(prepared, **overrides)
        assert row["status"] == "BLOCK"
        assert reason in row["reason_codes"]
        assert row["side_effect_performed"] is False


def test_execution_intent_requires_both_reserved_gates_and_packet_class():
    revalidated = _revalidate(_prepare())
    no_g9a = build_merge_execution_intent(revalidated, g9a_trusted=False, g9b_orch2_authority=False, packet_class_enabled=True)
    assert no_g9a["status"] == "BLOCK"
    assert "DSAI_G9A_TRUST_REQUIRED" in no_g9a["reason_codes"]
    assert "DSAI_G9B_ORCH2_AUTHORITY_REQUIRED" in no_g9a["reason_codes"]

    no_g9b = build_merge_execution_intent(revalidated, g9a_trusted=True, g9b_orch2_authority=False, packet_class_enabled=True)
    assert no_g9b["status"] == "BLOCK"
    assert "DSAI_G9B_ORCH2_AUTHORITY_REQUIRED" in no_g9b["reason_codes"]

    disabled_class = build_merge_execution_intent(revalidated, g9a_trusted=True, g9b_orch2_authority=True, packet_class_enabled=False)
    assert disabled_class["status"] == "BLOCK"
    assert "PACKET_CLASS_NOT_ENABLED" in disabled_class["reason_codes"]

    synthetic_authorized = build_merge_execution_intent(revalidated, g9a_trusted=True, g9b_orch2_authority=True, packet_class_enabled=True)
    assert synthetic_authorized["status"] == "ELIGIBLE"
    assert synthetic_authorized["side_effect_authorized"] is True
    assert synthetic_authorized["side_effect_performed"] is False
    assert synthetic_authorized["execution_adapter"] == "EXTERNAL_TOOL_BROKER_ONLY"


def test_simulated_merge_and_interruption_recovery_never_touch_repository():
    revalidated = _revalidate(_prepare())
    intent = build_merge_execution_intent(revalidated, g9a_trusted=True, g9b_orch2_authority=True, packet_class_enabled=True)
    receipt = simulate_squash_merge(intent, result_main_sha=C)
    assert receipt["status"] == "PASS"
    assert receipt["simulation_only"] is True
    assert receipt["side_effect_performed"] is False

    before = build_merge_recovery_record(merge_plan_id=revalidated["merge_plan_id"], phase="EXECUTE", side_effect_observed=False)
    after = build_merge_recovery_record(merge_plan_id=revalidated["merge_plan_id"], phase="EXECUTE", side_effect_observed=True)
    assert before["status"] == "SAFE_TO_RETRY_FROM_PREPARE"
    assert after["status"] == "BLOCK_RECONCILIATION_REQUIRED"
    assert before["automatic_retry"] is False
    assert after["automatic_retry"] is False


def test_wp9_registry_and_schema_preserve_no_authority_boundary():
    registry = json.loads((ROOT / "registries/development/skills/wp9_git_merge_candidate_v0_1.json").read_text(encoding="utf-8"))
    row = registry["entries"][0]
    assert row["release_id"] == RELEASE
    assert row["trusted"] is False
    assert row["selection_eligible"] is False
    assert row["merge_authority"] == "NONE"
    assert row["automatic_merge"] is False
    assert row["promotion_gate"] == "DSAI-G9A"
    assert row["activation_gate"] == "DSAI-G9B"

    schema = json.loads((ROOT / "schemas/development/skills/merge_preparation_v0_1.schema.json").read_text(encoding="utf-8"))
    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["additionalProperties"] is False
    assert schema["properties"]["snapshot"]["additionalProperties"] is False

    fixture = json.loads((ROOT / "fixtures/development_skills/wp9_merge_capability_cases_v0_1.json").read_text(encoding="utf-8"))
    assert len(fixture["cases"]) >= 14
    assert fixture["authority_effect"] == "NONE"
