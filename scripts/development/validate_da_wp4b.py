#!/usr/bin/env python3
"""Validate DA-WP4B implementation, shadow evidence and fail-closed activation."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from ovc.development.receipt_bot import (  # noqa: E402
    evaluate_activation,
    evaluate_work_packet,
    load_policy,
    load_work_packet,
)


BASELINE = "d8a7f07f5abe376b917cf6f95f6e9ccc1864b7c3"
TESTED = "343015c8ced74033a1547b5a5699064d62087ea9"
SHADOW_COMMIT = "0535db3ed4904fa9b2d1a4b6ba3deb9a338ab90e"
AUDIT_SHA256 = "79e29f05f4e34999a6fa23cb5c0ed922a761dbce202b2f568ef97575af2b13d3"
PASS_RUNS = {30751814800, 30751814840, 30751814766, 30751814813, 30752883818}
REQUIRED = [
    "contracts/development/OVC_RECEIPT_BOT_IMPLEMENTATION_CONTRACT_v0_1.md",
    "schemas/development/receipt_bot_work_packet_v0_1.schema.json",
    "schemas/development/receipt_bot_active_profile_v0_1.schema.json",
    "registries/development/OVC_DEVELOPMENT_ACCELERATION_RECEIPT_BOT_POLICY_v0_1.json",
    "registries/development/OVC_DEVELOPMENT_ACCELERATION_RECEIPT_BOT_IMPLEMENTATION_STATE_v0_1.json",
    "src/ovc/development/receipt_bot.py",
    "fixtures/development/receipt_bot/work_packet_pass_v0_1.json",
    "fixtures/development/receipt_bot/work_packet_block_v0_1.json",
    "tests/development/test_receipt_bot.py",
    "docs/releases/development-acceleration-v0-1/da-g4/DA_G4_MERGE_RECEIPT.json",
    "docs/releases/development-acceleration-v0-1/da-wp4b/DA_WP4B_IMPLEMENTATION_PACKET.json",
    "docs/releases/development-acceleration-v0-1/da-wp4b/DA_WP4B_ACTIVATION_EVIDENCE.json",
    "docs/releases/development-acceleration-v0-1/da-wp4b/DA_WP4B_QA_PACKET.json",
    "docs/releases/development-acceleration-v0-1/da-wp4b/DA_WP4B_BLOCKER_RECORD.json",
    "registries/development/OVC_DEVELOPMENT_ACCELERATION_PROGRAMME_STATE_v0_1.json",
    "registries/development/OVC_DEVELOPMENT_ACCELERATION_IMPLEMENTATION_REGISTRY_v0_1.yaml",
    "docs/releases/development-acceleration-v0-1/da-wp4b/DA_G4B_SHADOW_EXTERNAL_AUDIT.json",
    "docs/releases/development-acceleration-v0-1/da-wp4b/DA_G4B_SHADOW_QA_REVIEW.json",
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
    assert PASS_RUNS.issubset(actual)


def main() -> int:
    missing = [path for path in REQUIRED if not (ROOT / path).is_file()]
    if missing:
        raise AssertionError(f"missing DA-WP4B files: {missing}")

    for schema_path in REQUIRED[1:3]:
        schema = json.loads(read(schema_path))
        assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
        assert schema["type"] == "object"
        assert schema["additionalProperties"] is False

    policy = load_policy(ROOT / REQUIRED[3])
    passing = load_work_packet(ROOT / REQUIRED[6])
    blocked_packet = load_work_packet(ROOT / REQUIRED[7])
    plan = evaluate_work_packet(passing, policy)
    blocked = evaluate_work_packet(blocked_packet, policy)
    assert plan["status"] == "PASS"
    assert plan["blockers"] == []
    assert plan["authority"]["active"] is False
    assert plan["authority"]["writes_performed"] is False
    assert plan["authority"]["merge_api_available"] is False
    assert blocked["status"] == "BLOCK"
    assert "STALE_MAIN_SHA" in blocked["blockers"]
    assert "BRANCH_NOT_ALLOWED" in blocked["blockers"]
    assert any(item.startswith("PATH_NOT_ALLOWED:") for item in blocked["blockers"])
    assert "DESTRUCTIVE_ROLLBACK" in blocked["blockers"]

    activation_input = {condition: "PASS" for condition in policy.required_activation_conditions}
    activation_input["MAIN_BRANCH_PROTECTION_NO_BOT_BYPASS_VERIFIED"] = "BLOCKED"
    activation_input["FINAL_HEAD_COMPLETE_REPOSITORY_ASSURANCE_PASS"] = "PENDING"
    activation_input["QA_PASS"] = "BLOCKED"
    activation = evaluate_activation(activation_input, policy)
    assert activation["status"] == "BLOCK"
    assert activation["authority_active"] is False

    state = json.loads(read(REQUIRED[4]))
    merge_receipt = json.loads(read(REQUIRED[9]))
    packet = json.loads(read(REQUIRED[10]))
    activation_record = json.loads(read(REQUIRED[11]))
    qa = json.loads(read(REQUIRED[12]))
    blocker = json.loads(read(REQUIRED[13]))
    programme = json.loads(read(REQUIRED[14]))
    audit = json.loads(read(REQUIRED[16]))
    shadow_qa = json.loads(read(REQUIRED[17]))

    assert merge_receipt["squash_merge_sha"] == BASELINE
    assert merge_receipt["decision"] == "PASS"
    assert merge_receipt["authority_active"] is False

    assert state["baseline_main_commit"] == BASELINE
    assert state["branch"] == "build/ovc-dev-accel-receipt-bot"
    assert state["tested_candidate_commit"] == TESTED
    assert state["status"] == "BLOCKED_ACTIVATION_RULESET_EVIDENCE_AND_FINAL_CI"
    assert state["production_transport"] == "ABSENT_FAIL_CLOSED"
    assert state["credential_state"] == "DEDICATED_REVOCABLE_GITHUB_APP_PROVISIONED_SHADOW_ONLY"
    assert state["authority_active"] is False
    assert len(state["blockers"]) == 2
    assert state["shadow_evidence"]["shadow_pull_request"] == 211
    assert state["shadow_evidence"]["shadow_commit"] == SHADOW_COMMIT
    assert state["shadow_evidence"]["open_unmerged"] is True
    assert_runs(state["tests"])

    assert packet["packet_id"] == "DA-WP4B"
    assert packet["status"] == "IMPLEMENTED_SHADOW_PASS_CANDIDATE_ACTIVATION_BLOCKED"
    assert packet["baseline_main_commit"] == BASELINE

    assert activation_record["activation_evaluation"] == "BLOCK"
    assert activation_record["authority_active"] is False
    assert activation_record["tested_candidate_commit"] == TESTED
    conditions = {row["condition"]: row["result"] for row in activation_record["conditions"]}
    assert conditions["DENIED_ACTION_TESTS_PASS"] == "PASS"
    assert conditions["TOKEN_REDACTION_TESTS_PASS"] == "PASS"
    assert conditions["IDEMPOTENCY_AND_COLLISION_TESTS_PASS"] == "PASS"
    assert conditions["MAIN_BRANCH_PROTECTION_NO_BOT_BYPASS_VERIFIED"] == "BLOCKED"
    assert conditions["REAL_PROPOSAL_BRANCH_SHADOW_PASS"] == "PASS_CANDIDATE"
    assert conditions["FINAL_HEAD_COMPLETE_REPOSITORY_ASSURANCE_PASS"] == "PENDING"
    assert len(activation_record["blockers"]) == 2
    assert activation_record["shadow"]["pull_request"] == 211
    assert activation_record["shadow"]["open_unmerged"] is True
    assert_runs(activation_record["tests"])

    assert qa["status"] == "PASS_IMPLEMENTATION_AND_SHADOW_CANDIDATE_ACTIVATION_BLOCKED"
    assert qa["tested_candidate_commit"] == TESTED
    assert qa["implementation_blocking_issues"] == []
    assert len(qa["activation_blocking_issues"]) == 2
    assert qa["qa_recommendation"] == "PASS_IMPLEMENTATION_AND_SHADOW_CANDIDATE_BLOCK_ACTIVATION"
    assert qa["authority_active"] is False
    assert_runs(qa["tests"])

    assert blocker["status"] == "BLOCKED_ACTIVATION_RULESET_EVIDENCE_AND_FINAL_CI"
    assert len(blocker["resolved_blockers"]) == 2
    assert len(blocker["blockers"]) == 2
    assert blocker["authority_state"] == "APPROVED_FOR_BOUNDED_IMPLEMENTATION_NOT_ACTIVE"
    assert blocker["authority_active"] is False

    audit_bytes = (ROOT / REQUIRED[16]).read_bytes()
    recorded_audit = dict(audit)
    recorded_hash = recorded_audit.pop("external_audit_file_sha256")
    canonical_uploaded = json.dumps(recorded_audit, indent=2).encode("utf-8") + b"\n"
    assert hashlib.sha256(canonical_uploaded).hexdigest() == recorded_hash == AUDIT_SHA256
    assert audit["mode"] == "PRE_ACTIVATION_SHADOW"
    assert audit["operator_connector"] is False
    assert audit["revocable"] is True
    assert audit["permissions"] == {"contents": "write", "pull_requests": "write", "metadata": "read"}
    assert audit["commit_sha"] == SHADOW_COMMIT
    assert audit["pull_request_number"] == 211
    assert audit["authority_active"] is False
    assert audit["production_transport_active"] is False
    assert audit["merge_performed"] is False
    assert audit["approval_performed"] is False
    assert audit["force_push_performed"] is False
    assert audit["history_rewrite_performed"] is False
    assert audit["result"] == "PASS_CANDIDATE_PENDING_QA"
    assert hashlib.sha256(audit_bytes).hexdigest() != AUDIT_SHA256

    assert shadow_qa["shadow_pull_request"] == 211
    assert shadow_qa["shadow_commit"] == SHADOW_COMMIT
    assert shadow_qa["authority_active"] is False
    assert shadow_qa["shadow_pr_must_remain_unmerged"] is True
    assert shadow_qa["verified_conditions"]["DEDICATED_REVOCABLE_IDENTITY_PROVISIONED"] == "PASS"
    assert shadow_qa["verified_conditions"]["REAL_PROPOSAL_BRANCH_SHADOW_PASS"].startswith("PASS_CANDIDATE")
    assert shadow_qa["verified_conditions"]["MAIN_BRANCH_PROTECTION_NO_BOT_BYPASS_VERIFIED"].startswith("BLOCKED")

    assert programme["programme_status"] == "BLOCKED"
    assert programme["current_packet"] == "DA-WP4B"
    assert programme["current_gate"] == "DA-G4B"
    assert programme["candidate_commit"] == TESTED
    assert programme["authority"]["repository_bot_write"] == "APPROVED_FOR_BOUNDED_IMPLEMENTATION_NOT_ACTIVE"
    assert programme["authority"]["repository_bot_profile"] == "APPROVED_INACTIVE"
    assert programme["authority"]["repository_bot_production_transport"] == "ABSENT_FAIL_CLOSED"
    assert programme["authority"]["direct_main_write"] == "PROHIBITED"
    packets = {row["packet_id"]: row for row in programme["packets"]}
    assert packets["DA-WP4B"]["status"] == "BLOCKED"
    assert packets["DA-WP4B"]["candidate_commit"] == TESTED
    assert len(packets["DA-WP4B"]["blockers"]) == 2
    assert programme["activation_gate"]["status"] == "BLOCKED"
    assert programme["activation_gate"]["shadow_pull_request"] == 211
    assert programme["activation_gate"]["authority_active"] is False
    assert programme["next_action"] == "VERIFY_PR209_FINAL_HEAD_CI_AND_OBTAIN_EXACT_RULESET_EXPORT"

    bodies = "\n".join(read(path) for path in REQUIRED[:18])
    assert '"active": true' not in bodies
    assert '"authority_active": true' not in bodies
    assert "production_transport\": \"ACTIVE" not in bodies

    require_tokens(REQUIRED[0], [
        "APPROVED_FOR_BOUNDED_IMPLEMENTATION_NOT_ACTIVE",
        "CREATE_BOT_BRANCH",
        "CREATE_OR_UPDATE_ALLOWLISTED_FILES",
        "OPEN_OR_UPDATE_PULL_REQUEST",
        "no merge, approval",
        "Static implementation or unit tests cannot substitute",
    ])
    require_tokens(REQUIRED[5], [
        "IDEMPOTENCY_COLLISION",
        "STALE_MAIN_SHA",
        "PATH_NOT_ALLOWED",
        "redact_secrets",
        "RepositoryProposalAdapter",
        "merge_api_available",
    ])
    require_tokens(REQUIRED[8], [
        "test_pass_plan_is_deterministic_and_no_write",
        "test_block_fixture_surfaces_all_material_failures",
        "test_idempotent_retry_and_collision",
        "test_activation_blocks_missing_external_evidence",
        "test_recording_adapter_exposes_no_merge_or_approval_method",
    ])
    require_tokens(REQUIRED[15], [
        "packet_id: DA-WP4B",
        "status: BLOCKED",
        "gate_id: DA-G4B",
        "MAIN_BRANCH_PROTECTION_NO_BOT_BYPASS_VERIFIED",
        "REAL_PROPOSAL_BRANCH_SHADOW_PASS",
    ])

    print("DA-WP4B implementation and shadow candidate PASS; activation BLOCKED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
