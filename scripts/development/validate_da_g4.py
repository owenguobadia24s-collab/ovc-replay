#!/usr/bin/env python3
"""Validate the operator-approved, still-inactive DA-G4 authority record."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BASELINE = "a561f30506c02dd26175d4a4f9e821d3074735a1"
TESTED = "a6a642192663033b412ba48bd891e3d84e886a87"
PROPOSAL_SHA256 = "e3e13f38dbddbf96da075c4489e2c5e7c7a03b6f42aaa9aa564e0db2813fa0f5"
PROPOSED_DELTA = "NARROW_REPOSITORY_BOT_PROPOSAL_BRANCH_WRITE_FOR_DEVELOPMENT_ACCELERATION_RECEIPTS_ONLY"
RUNS = {30710409242, 30710409313, 30710409322}
REQUIRED = [
    "contracts/development/OVC_REPOSITORY_RECEIPT_BOT_AUTHORITY_PROPOSAL_v0_1.md",
    "schemas/development/repository_bot_authority_profile_v0_1.schema.json",
    "registries/development/OVC_DEVELOPMENT_ACCELERATION_REPOSITORY_BOT_PROPOSAL_v0_1.json",
    "registries/development/OVC_DEVELOPMENT_ACCELERATION_REPOSITORY_BOT_APPROVED_PROFILE_v0_1.json",
    "docs/releases/development-acceleration-v0-1/da-wp4/DA_WP4_MERGE_RECEIPT.json",
    "docs/releases/development-acceleration-v0-1/da-g4/DA_G4_GATE_PACKET.json",
    "docs/releases/development-acceleration-v0-1/da-g4/DA_G4_QA_PACKET.json",
    "docs/releases/development-acceleration-v0-1/da-g4/DA_G4_OPERATOR_DECISION_REQUEST.json",
    "docs/releases/development-acceleration-v0-1/da-g4/DA_G4_OPERATOR_DECISION.json",
    "registries/development/OVC_DEVELOPMENT_ACCELERATION_IMPLEMENTATION_REGISTRY_v0_1.yaml",
    "registries/development/OVC_DEVELOPMENT_ACCELERATION_PROGRAMME_STATE_v0_1.json",
    "tests/development/test_da_g4.py",
]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def require_tokens(path: str, tokens: list[str]) -> None:
    body = read(path)
    missing = [token for token in tokens if token not in body]
    if missing:
        raise AssertionError(f"{path}: missing {missing}")


def assert_runs(rows: list[dict[str, object]]) -> None:
    actual = {int(row["run_id"]) for row in rows if row["result"] == "PASS"}
    assert RUNS.issubset(actual)


def main() -> int:
    missing = [path for path in REQUIRED if not (ROOT / path).is_file()]
    if missing:
        raise AssertionError(f"missing DA-G4 files: {missing}")

    schema = json.loads(read(REQUIRED[1]))
    proposal = json.loads(read(REQUIRED[2]))
    approved = json.loads(read(REQUIRED[3]))
    receipt = json.loads(read(REQUIRED[4]))
    gate = json.loads(read(REQUIRED[5]))
    qa = json.loads(read(REQUIRED[6]))
    request = json.loads(read(REQUIRED[7]))
    decision = json.loads(read(REQUIRED[8]))
    state = json.loads(read(REQUIRED[10]))

    assert receipt["packet_id"] == "DA-WP4"
    assert receipt["gate_id"] == "DA-G4A"
    assert receipt["decision"] == "PASS"
    assert receipt["squash_merge_sha"] == BASELINE

    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["type"] == "object"
    assert schema["additionalProperties"] is False
    assert schema["properties"]["status"]["const"] == "PENDING_OPERATOR_DA_G4"
    assert schema["properties"]["active"]["const"] is False
    assert schema["properties"]["proposed_authority_delta"]["const"] == PROPOSED_DELTA

    assert proposal["schema"] == "ovc-repository-bot-authority-profile/v1"
    assert proposal["gate_id"] == "DA-G4"
    assert proposal["status"] == "PENDING_OPERATOR_DA_G4"
    assert proposal["active"] is False
    assert proposal["proposed_authority_delta"] == PROPOSED_DELTA
    assert proposal["base_branch"] == "main"
    assert proposal["branch_patterns"] == ["bot/ovc-dev-accel-receipts/*"]
    assert proposal["allowed_paths"] == [
        "docs/releases/development-acceleration-v0-1/**",
        "registries/development/OVC_DEVELOPMENT_ACCELERATION_PROGRAMME_STATE_v0_1.json",
        "registries/development/OVC_DEVELOPMENT_ACCELERATION_IMPLEMENTATION_REGISTRY_v0_1.yaml",
    ]
    assert proposal["allowed_actions"] == [
        "CREATE_BOT_BRANCH",
        "CREATE_OR_UPDATE_ALLOWLISTED_FILES",
        "OPEN_OR_UPDATE_PULL_REQUEST",
    ]

    assert approved["status"] == "APPROVED_FOR_BOUNDED_IMPLEMENTATION_NOT_ACTIVE"
    assert approved["active"] is False
    assert approved["implementation_authorized"] is True
    assert approved["proposal_profile_sha256"] == PROPOSAL_SHA256
    assert approved["approved_authority_delta"] == PROPOSED_DELTA
    assert approved["credential_state"] == "NOT_PROVISIONED"
    assert approved["writer_adapter_state"] == "NOT_IMPLEMENTED"
    assert approved["main_branch_protection_verification"] == "PENDING"
    assert approved["real_proposal_branch_shadow"] == "PENDING"

    denied = set(proposal["denied_actions"])
    approved_denied = set(approved["permanent_denials"])
    for token in (
        "WRITE_MAIN", "WRITE_NON_BOT_BRANCH", "MERGE_PULL_REQUEST", "APPROVE_PULL_REQUEST",
        "FORCE_PUSH", "REWRITE_HISTORY", "MODIFY_WORKFLOW", "MODIFY_SOURCE_CODE",
        "MODIFY_AUTHORITY_PROFILE", "SELF_APPROVE", "PROVIDER_ACCESS", "R2_WRITE",
        "RELEASE_PUBLICATION", "SELECTOR_MUTATION", "VALIDATION_ACCESS",
        "MARKET_OR_SEMANTIC_MUTATION", "PROBABILITY_RISK_EXPOSURE_OR_EXECUTION_OBJECT",
    ):
        assert token in denied
        assert token in approved_denied
    assert proposal["self_modification"] == "DENIED"
    for condition in (
        "MAIN_BRANCH_PROTECTION_NO_BOT_BYPASS_VERIFIED",
        "REAL_PROPOSAL_BRANCH_SHADOW_PASS",
        "FINAL_HEAD_COMPLETE_REPOSITORY_ASSURANCE_PASS",
        "DENIED_ACTION_TESTS_PASS",
        "TOKEN_REDACTION_TESTS_PASS",
        "REVOCATION_TESTS_PASS",
    ):
        assert condition in proposal["activation_conditions"]
        assert condition in approved["activation_conditions"]

    assert gate["gate_id"] == "DA-G4"
    assert gate["status"] == "APPROVED_PENDING_SQUASH_MERGE"
    assert gate["baseline_main_commit"] == BASELINE
    assert gate["candidate_branch"] == "gate/ovc-dev-accel-da-g4"
    assert gate["tested_candidate_commit"] == TESTED
    assert gate["current_authority"]["repository_bot_write"] == "APPROVED_FOR_BOUNDED_IMPLEMENTATION_NOT_ACTIVE"
    assert gate["current_authority"]["direct_main_write"] == "PROHIBITED"
    assert gate["current_authority"]["market_authority"] == "NONE"
    assert gate["approved_authority_delta"]["delta_id"] == PROPOSED_DELTA
    assert gate["approved_authority_delta"]["current_status"] == "APPROVED_FOR_BOUNDED_IMPLEMENTATION_NOT_ACTIVE"
    assert gate["approved_authority_delta"]["proposal_profile_sha256"] == PROPOSAL_SHA256
    assert gate["external_artifacts"] == []
    assert gate["external_artifact_hashes"] == "NONE"
    assert gate["unresolved_issues"] == []
    assert gate["recorded_decision"] == "PASS"
    assert gate["decision_id"] == "DA-G4.OPERATOR.PASS.20260801T172600Z"
    assert gate["next_packet"] == "DA-WP4B"
    assert_runs(gate["tests"])

    assert qa["status"] == "PASS_APPROVED_PENDING_SQUASH_MERGE"
    assert qa["baseline_commit"] == BASELINE
    assert qa["tested_candidate_commit"] == TESTED
    assert qa["blocking_issues"] == []
    assert qa["qa_recommendation"] == "PASS_OPERATOR_APPROVED_FOR_BOUNDED_IMPLEMENTATION_NOT_ACTIVE"
    assert qa["current_repository_bot_write"] == "APPROVED_FOR_BOUNDED_IMPLEMENTATION_NOT_ACTIVE"
    assert qa["approved_authority_delta"] == PROPOSED_DELTA
    assert qa["operator_decision"] == "PASS"
    assert qa["authority_active"] is False
    assert qa["market_authority_delta"] == "NONE"
    assert qa["validation_authority_delta"] == "NONE"
    assert qa["probability_risk_exposure_execution_delta"] == "NONE"
    assert_runs(qa["tests"])

    assert request["gate_id"] == "DA-G4"
    assert request["status"] == "DECIDED_PASS"
    assert request["requested_decision"] == "PASS"
    assert request["operator_command"] == "OVC APPROVE DA-G4 PASS"
    assert request["decision_id"] == "DA-G4.OPERATOR.PASS.20260801T172600Z"
    assert request["authority_active"] is False
    assert_runs(request["readiness_tests"])

    assert decision["decision"] == "PASS"
    assert decision["decision_authority"] == "OPERATOR"
    assert decision["operator_command"] == "OVC APPROVE DA-G4 PASS"
    assert decision["tested_candidate_commit"] == TESTED
    assert decision["proposal_profile_sha256"] == PROPOSAL_SHA256
    assert decision["approved_profile_state"] == "APPROVED_FOR_BOUNDED_IMPLEMENTATION_NOT_ACTIVE"
    assert decision["implementation_authorized"] is True
    assert decision["authority_active"] is False
    assert decision["next_packet"] == "DA-WP4B"
    assert_runs(decision["gate_readiness_tests"])

    assert state["current_packet"] == "DA-G4"
    assert state["current_gate"] == "DA-G4"
    assert state["operator_decision_required"] is False
    assert state["operator_decision_id"] == "DA-G4.OPERATOR.PASS.20260801T172600Z"
    assert state["baseline_commit"] == BASELINE
    assert state["branch"] == "gate/ovc-dev-accel-da-g4"
    assert state["candidate_commit"] == TESTED
    assert state["authority"]["repository_bot_write"] == "APPROVED_FOR_BOUNDED_IMPLEMENTATION_NOT_ACTIVE"
    assert state["authority"]["repository_bot_profile"] == "APPROVED_INACTIVE"
    assert state["authority"]["direct_main_write"] == "PROHIBITED"
    packets = {row["packet_id"]: row for row in state["packets"]}
    assert packets["DA-WP4"]["status"] == "COMPLETED"
    assert packets["DA-WP4"]["merge_commit"] == BASELINE
    assert packets["DA-WP4B"]["status"] == "READY_AFTER_DA_G4_MERGE"
    assert packets["DA-WP5"]["blockers"] == ["DA-WP4B_NOT_COMPLETED"]
    assert state["operator_gate"]["status"] == "APPROVED_PENDING_SQUASH_MERGE"
    assert state["operator_gate"]["recorded_decision"] == "PASS"
    assert state["operator_gate"]["authority_active"] is False
    assert state["next_action"] == "SQUASH_MERGE_PR_208_THEN_BEGIN_DA_WP4B"
    assert state["open_concurrent_work"][0]["pull_request"] == 202

    credential_artifacts = REQUIRED[:11]
    bodies = "\n".join(read(path) for path in credential_artifacts)
    for token in ("ghp_", "github_pat_", "-----BEGIN PRIVATE KEY-----", "sk-proj-", "Bearer "):
        assert token not in bodies
    assert '"active": true' not in bodies

    require_tokens(REQUIRED[0], [
        "PROPOSED_PENDING_OPERATOR_DA_G4", "bot/ovc-dev-accel-receipts/*",
        "may not approve or merge", "not a native path sandbox", "Revocation is independent",
        "APPROVED_FOR_BOUNDED_IMPLEMENTATION_NOT_ACTIVE",
    ])
    require_tokens(REQUIRED[9], [
        "gate_id: DA-G4", "status: APPROVED_PENDING_SQUASH_MERGE",
        "APPROVED_FOR_BOUNDED_IMPLEMENTATION_NOT_ACTIVE", "DA-WP4B",
    ])
    require_tokens(REQUIRED[11], [
        "test_profile_is_closed_inactive_and_operator_reserved",
        "test_allowlist_is_exact_and_minimal",
        "test_merge_main_self_modification_and_market_authority_are_denied",
        "test_activation_requires_branch_protection_shadow_and_final_assurance",
        "test_no_credentials_or_active_authority_are_materialized",
    ])

    print("DA-G4 approved inactive authority validation PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
