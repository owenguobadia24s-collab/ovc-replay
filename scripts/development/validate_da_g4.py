#!/usr/bin/env python3
"""Validate the DA-G4 operator-required repository-bot authority packet."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BASELINE = "a561f30506c02dd26175d4a4f9e821d3074735a1"
PROPOSED_DELTA = "NARROW_REPOSITORY_BOT_PROPOSAL_BRANCH_WRITE_FOR_DEVELOPMENT_ACCELERATION_RECEIPTS_ONLY"
REQUIRED = [
    "contracts/development/OVC_REPOSITORY_RECEIPT_BOT_AUTHORITY_PROPOSAL_v0_1.md",
    "schemas/development/repository_bot_authority_profile_v0_1.schema.json",
    "registries/development/OVC_DEVELOPMENT_ACCELERATION_REPOSITORY_BOT_PROPOSAL_v0_1.json",
    "docs/releases/development-acceleration-v0-1/da-wp4/DA_WP4_MERGE_RECEIPT.json",
    "docs/releases/development-acceleration-v0-1/da-g4/DA_G4_GATE_PACKET.json",
    "docs/releases/development-acceleration-v0-1/da-g4/DA_G4_QA_PACKET.json",
    "docs/releases/development-acceleration-v0-1/da-g4/DA_G4_OPERATOR_DECISION_REQUEST.json",
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


def main() -> int:
    missing = [path for path in REQUIRED if not (ROOT / path).is_file()]
    if missing:
        raise AssertionError(f"missing DA-G4 files: {missing}")

    schema = json.loads(read(REQUIRED[1]))
    profile = json.loads(read(REQUIRED[2]))
    receipt = json.loads(read(REQUIRED[3]))
    gate = json.loads(read(REQUIRED[4]))
    qa = json.loads(read(REQUIRED[5]))
    decision = json.loads(read(REQUIRED[6]))
    state = json.loads(read(REQUIRED[8]))

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

    assert profile["schema"] == "ovc-repository-bot-authority-profile/v1"
    assert profile["gate_id"] == "DA-G4"
    assert profile["status"] == "PENDING_OPERATOR_DA_G4"
    assert profile["active"] is False
    assert profile["proposed_authority_delta"] == PROPOSED_DELTA
    assert profile["base_branch"] == "main"
    assert profile["branch_patterns"] == ["bot/ovc-dev-accel-receipts/*"]
    assert profile["allowed_paths"] == [
        "docs/releases/development-acceleration-v0-1/**",
        "registries/development/OVC_DEVELOPMENT_ACCELERATION_PROGRAMME_STATE_v0_1.json",
        "registries/development/OVC_DEVELOPMENT_ACCELERATION_IMPLEMENTATION_REGISTRY_v0_1.yaml",
    ]
    assert profile["allowed_actions"] == [
        "CREATE_BOT_BRANCH",
        "CREATE_OR_UPDATE_ALLOWLISTED_FILES",
        "OPEN_OR_UPDATE_PULL_REQUEST",
    ]
    denied = set(profile["denied_actions"])
    for token in (
        "WRITE_MAIN", "WRITE_NON_BOT_BRANCH", "MERGE_PULL_REQUEST", "APPROVE_PULL_REQUEST",
        "FORCE_PUSH", "REWRITE_HISTORY", "MODIFY_WORKFLOW", "MODIFY_SOURCE_CODE",
        "MODIFY_AUTHORITY_PROFILE", "SELF_APPROVE", "PROVIDER_ACCESS", "R2_WRITE",
        "RELEASE_PUBLICATION", "SELECTOR_MUTATION", "VALIDATION_ACCESS",
        "MARKET_OR_SEMANTIC_MUTATION", "PROBABILITY_RISK_EXPOSURE_OR_EXECUTION_OBJECT",
    ):
        assert token in denied
    assert profile["self_modification"] == "DENIED"
    assert "MAIN_BRANCH_PROTECTION_NO_BOT_BYPASS_VERIFIED" in profile["activation_conditions"]
    assert "REAL_PROPOSAL_BRANCH_SHADOW_PASS" in profile["activation_conditions"]
    assert "FINAL_HEAD_COMPLETE_REPOSITORY_ASSURANCE_PASS" in profile["activation_conditions"]
    assert profile["revocation"]["profile_disable"] == "REQUIRED"
    assert profile["revocation"]["credential_revoke"] == "REQUIRED"
    assert profile["revocation"]["history_rewrite"] == "PROHIBITED"

    assert gate["gate_id"] == "DA-G4"
    assert gate["status"] == "GATE_PREPARATION_PENDING_FINAL_HEAD_CI"
    assert gate["baseline_main_commit"] == BASELINE
    assert gate["candidate_branch"] == "gate/ovc-dev-accel-da-g4"
    assert gate["candidate_commit"] is None
    assert gate["current_authority"]["repository_bot_write"] == "DENIED"
    assert gate["current_authority"]["direct_main_write"] == "PROHIBITED"
    assert gate["current_authority"]["market_authority"] == "NONE"
    assert gate["proposed_authority_delta"]["delta_id"] == PROPOSED_DELTA
    assert gate["proposed_authority_delta"]["current_status"] == "PENDING_OPERATOR_NOT_ACTIVE"
    assert gate["external_artifacts"] == []
    assert gate["external_artifact_hashes"] == "NONE"
    assert gate["unresolved_issues"] == []
    assert gate["recommended_decision"] == "PASS"
    assert gate["allowed_operator_decisions"] == ["PASS", "DEFER", "BLOCK", "QUARANTINE", "SUPERSEDE"]
    assert len(gate["completed_packets"]) == 5
    assert gate["completed_packets"][-1]["merge_commit"] == BASELINE
    assert "MAIN_BRANCH_PROTECTION_NO_BOT_BYPASS_VERIFIED" in profile["activation_conditions"]

    assert qa["status"] == "PASS_STATIC_PENDING_FINAL_HEAD_CI"
    assert qa["baseline_commit"] == BASELINE
    assert qa["candidate_commit"] is None
    assert qa["blocking_issues"] == []
    assert qa["current_repository_bot_write"] == "DENIED"
    assert qa["proposed_authority_delta"] == PROPOSED_DELTA
    assert qa["activation_state_after_operator_pass"] == "APPROVED_FOR_BOUNDED_IMPLEMENTATION_NOT_ACTIVE"
    assert qa["market_authority_delta"] == "NONE"
    assert qa["validation_authority_delta"] == "NONE"
    assert qa["probability_risk_exposure_execution_delta"] == "NONE"

    assert decision["gate_id"] == "DA-G4"
    assert decision["status"] == "PENDING_OPERATOR"
    assert decision["current_authority"] == "REPOSITORY_BOT_WRITE_DENIED"
    assert decision["requested_decision"] == "PASS"
    assert decision["proposed_authority_delta"] == PROPOSED_DELTA
    assert decision["operator_command"] == "OVC APPROVE DA-G4 PASS"
    assert decision["decision_record"] is None
    assert decision["authority_active"] is False

    assert state["current_packet"] == "DA-G4"
    assert state["current_gate"] == "DA-G4"
    assert state["operator_decision_required"] is True
    assert state["baseline_commit"] == BASELINE
    assert state["branch"] == "gate/ovc-dev-accel-da-g4"
    assert state["candidate_commit"] is None
    assert state["authority"]["repository_bot_write"] == "DENIED_PENDING_DA_G4"
    assert state["authority"]["repository_bot_profile"] == "PENDING_OPERATOR_INACTIVE"
    assert state["authority"]["direct_main_write"] == "PROHIBITED"
    packets = {row["packet_id"]: row for row in state["packets"]}
    assert packets["DA-WP4"]["status"] == "COMPLETED"
    assert packets["DA-WP4"]["merge_commit"] == BASELINE
    assert packets["DA-WP5"]["blockers"] == ["DA-G4_OPERATOR_DECISION_PENDING"]
    assert state["operator_gate"]["status"] == "GATE_PREPARATION_PENDING_FINAL_HEAD_CI"
    assert state["operator_gate"]["authority_active"] is False
    assert state["open_concurrent_work"][0]["pull_request"] == 202

    credential_artifacts = REQUIRED[:9]
    bodies = "\n".join(read(path) for path in credential_artifacts)
    for token in ("ghp_", "github_pat_", "-----BEGIN PRIVATE KEY-----", "sk-proj-", "Bearer "):
        assert token not in bodies
    assert '"active": true' not in bodies

    require_tokens(REQUIRED[0], [
        "PROPOSED_PENDING_OPERATOR_DA_G4", "bot/ovc-dev-accel-receipts/*",
        "may not approve or merge", "not a native path sandbox", "Revocation is independent",
        "APPROVED_FOR_BOUNDED_IMPLEMENTATION_NOT_ACTIVE",
    ])
    require_tokens(REQUIRED[7], [
        "gate_id: DA-G4", "current_authority: DENIED", "GATE_PREPARATION_PENDING_FINAL_HEAD_CI",
        "READY_BLOCKED_BY_DA_G4_OPERATOR_DECISION",
    ])
    require_tokens(REQUIRED[9], [
        "test_profile_is_closed_inactive_and_operator_reserved",
        "test_allowlist_is_exact_and_minimal",
        "test_merge_main_self_modification_and_market_authority_are_denied",
        "test_activation_requires_branch_protection_shadow_and_final_assurance",
        "test_no_credentials_or_active_authority_are_materialized",
    ])

    print("DA-G4 gate preparation validation PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
