#!/usr/bin/env python3
"""Validate approved DA-G4B activation and permanent fail-closed denials."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from ovc.development.receipt_bot import evaluate_activation, evaluate_work_packet, load_policy, load_work_packet  # noqa: E402

BASELINE = "d8a7f07f5abe376b917cf6f95f6e9ccc1864b7c3"
SHADOW_COMMIT = "0535db3ed4904fa9b2d1a4b6ba3deb9a338ab90e"
RULESET_SHA256 = "ed6fe8eb2c030fc185adbf70ae4571fca3fee2f3fbab8002267c8da2b221c0c4"
AUDIT_CANONICAL_SHA256 = "3d21a03d1772491da6cd1722712a816abd200b1f7f69fa76548ffa3b6a6476ea"
ACTIVATION_ID = "4815173d1ec559164072013f20d008f2d3a5b120841e8e6cb0350ee1f1164238"
DECISION_ID = "DA-G4B.OPERATOR.PASS.20260802T163600Z"
ACTIVE_PROFILE = "registries/development/OVC_DEVELOPMENT_ACCELERATION_RECEIPT_BOT_ACTIVE_PROFILE_v0_1.json"
RUNNER = "scripts/development/run_da_receipt_bot.ps1"
REQUIRED = [
    "contracts/development/OVC_RECEIPT_BOT_IMPLEMENTATION_CONTRACT_v0_1.md",
    "schemas/development/receipt_bot_work_packet_v0_1.schema.json",
    "schemas/development/receipt_bot_active_profile_v0_1.schema.json",
    "registries/development/OVC_DEVELOPMENT_ACCELERATION_RECEIPT_BOT_POLICY_v0_1.json",
    "registries/development/OVC_DEVELOPMENT_ACCELERATION_RECEIPT_BOT_IMPLEMENTATION_STATE_v0_1.json",
    ACTIVE_PROFILE,
    "src/ovc/development/receipt_bot.py",
    "fixtures/development/receipt_bot/work_packet_pass_v0_1.json",
    "fixtures/development/receipt_bot/work_packet_block_v0_1.json",
    "docs/releases/development-acceleration-v0-1/da-g4/DA_G4_MERGE_RECEIPT.json",
    "docs/releases/development-acceleration-v0-1/da-wp4b/DA_G4B_OPERATOR_DECISION.json",
    "docs/releases/development-acceleration-v0-1/da-wp4b/DA_G4B_ACTIVATION_EVALUATION.json",
    "docs/releases/development-acceleration-v0-1/da-wp4b/DA_WP4B_ACTIVATION_EVIDENCE.json",
    "docs/releases/development-acceleration-v0-1/da-wp4b/DA_WP4B_QA_PACKET.json",
    "docs/releases/development-acceleration-v0-1/da-wp4b/DA_WP4B_BLOCKER_RECORD.json",
    "registries/development/OVC_DEVELOPMENT_ACCELERATION_PROGRAMME_STATE_v0_1.json",
    "registries/development/OVC_DEVELOPMENT_ACCELERATION_IMPLEMENTATION_REGISTRY_v0_1.yaml",
    "docs/releases/development-acceleration-v0-1/da-wp4b/DA_G4B_SHADOW_EXTERNAL_AUDIT.json",
    "docs/releases/development-acceleration-v0-1/da-wp4b/DA_G4B_SHADOW_QA_REVIEW.json",
    "docs/releases/development-acceleration-v0-1/da-wp4b/main-ruleset.json",
    RUNNER,
]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def load(path: str) -> dict[str, object]:
    value = json.loads(read(path))
    assert isinstance(value, dict)
    return value


def verify_ruleset(path: Path) -> None:
    raw = path.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == RULESET_SHA256
    ruleset = json.loads(raw)
    assert ruleset["enforcement"] == "active"
    assert "refs/heads/main" in ruleset["conditions"]["ref_name"]["include"]
    assert ruleset["bypass_actors"] == []
    assert ruleset["current_user_can_bypass"] == "never"
    rules = {row["type"]: row for row in ruleset["rules"]}
    assert {"deletion", "non_fast_forward", "pull_request", "required_status_checks"}.issubset(rules)
    assert rules["pull_request"]["parameters"]["allowed_merge_methods"] == ["squash"]
    checks = {row["context"] for row in rules["required_status_checks"]["parameters"]["required_status_checks"]}
    assert {"tests", "OVC tiered test selection shadow"}.issubset(checks)


def main() -> int:
    missing = [path for path in REQUIRED if not (ROOT / path).is_file()]
    if missing:
        raise AssertionError(f"missing DA-WP4B activation files: {missing}")

    for schema_path in REQUIRED[1:3]:
        schema = load(schema_path)
        assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
        assert schema["type"] == "object"
        assert schema["additionalProperties"] is False

    policy = load_policy(ROOT / REQUIRED[3])
    passing = evaluate_work_packet(load_work_packet(ROOT / REQUIRED[7]), policy)
    blocked = evaluate_work_packet(load_work_packet(ROOT / REQUIRED[8]), policy)
    assert passing["status"] == "PASS"
    assert passing["authority"]["active"] is False
    assert passing["authority"]["merge_api_available"] is False
    assert blocked["status"] == "BLOCK"
    assert {"STALE_MAIN_SHA", "BRANCH_NOT_ALLOWED", "DESTRUCTIVE_ROLLBACK"}.issubset(blocked["blockers"])

    verify_ruleset(ROOT / REQUIRED[19])
    active = load(ACTIVE_PROFILE)
    decision = load(REQUIRED[10])
    evaluation = load(REQUIRED[11])
    evidence = load(REQUIRED[12])
    qa = load(REQUIRED[13])
    blocker = load(REQUIRED[14])
    state = load(REQUIRED[4])
    programme = load(REQUIRED[15])
    merge_receipt = load(REQUIRED[9])
    audit = load(REQUIRED[17])
    shadow_qa = load(REQUIRED[18])

    assert merge_receipt["squash_merge_sha"] == BASELINE
    assert active == {
        "schema": "ovc-receipt-bot-active-profile/v1",
        "profile_id": "OVC.DEVELOPMENT.ACCELERATION.RECEIPT-BOT.v0.1",
        "source_approved_profile_hash": "e3e13f38dbddbf96da075c4489e2c5e7c7a03b6f42aaa9aa564e0db2813fa0f5",
        "decision_id": "DA-G4.OPERATOR.PASS.20260801T172600Z",
        "status": "ACTIVE",
        "active": True,
        "credential_identity_hash": "45d0cfcc0930db45217a529abef33d004d4cfeeae07b470c1d837ccab27ca3fc",
        "branch_protection_evidence_hash": RULESET_SHA256,
        "proposal_shadow_evidence_hash": AUDIT_CANONICAL_SHA256,
        "activation_evaluation_id": ACTIVATION_ID,
    }
    assert decision["decision_id"] == DECISION_ID
    assert decision["decision"] == "PASS"
    assert decision["authority_active"] is True
    assert decision["merge_authority_granted_to_bot"] is False
    assert evaluation["evaluation_id"] == ACTIVATION_ID
    assert evaluation["status"] == "PASS"
    assert evaluation["authority_active"] is True
    calculated = evaluate_activation({condition: "PASS" for condition in policy.required_activation_conditions}, policy)
    assert calculated["evaluation_id"] == ACTIVATION_ID
    assert calculated["authority_active"] is True

    assert state["authority_active"] is True
    assert state["operator_decision_id"] == DECISION_ID
    assert state["production_transport"].startswith("ACTIVE_FAIL_CLOSED:")
    assert state["shadow_evidence"]["shadow_pull_request"] == 211
    assert state["shadow_evidence"]["shadow_commit"] == SHADOW_COMMIT
    assert state["shadow_evidence"]["open_unmerged"] is True
    assert evidence["authority_active"] is True
    assert evidence["operator_decision_required"] is False
    assert qa["authority_active"] is True
    assert qa["implementation_blocking_issues"] == []
    assert qa["activation_blocking_issues"] == []
    assert blocker["authority_active"] is True
    assert programme["operator_decision_required"] is False
    assert programme["authority"]["repository_bot_write"] == "ACTIVE_BOUNDED_PROPOSAL_BRANCH_ONLY"
    assert programme["authority"]["direct_main_write"] == "PROHIBITED"
    assert programme["activation_gate"]["authority_active"] is True
    assert programme["activation_gate"]["operator_decision_required"] is False

    recorded = dict(audit)
    recorded_hash = recorded.pop("external_audit_file_sha256")
    canonical = json.dumps(recorded, indent=2).encode("utf-8") + b"\n"
    assert hashlib.sha256(canonical).hexdigest() == recorded_hash == AUDIT_CANONICAL_SHA256
    assert audit["pull_request_number"] == 211
    assert audit["commit_sha"] == SHADOW_COMMIT
    assert audit["authority_active"] is False
    assert shadow_qa["shadow_pr_must_remain_unmerged"] is True

    runner = read(RUNNER)
    for token in (
        "DA-G4B.OPERATOR.PASS.20260802T163600Z",
        "bot/ovc-dev-accel-receipts/*",
        "IDEMPOTENCY_COLLISION",
        "STALE_MAIN_SHA",
        "CREATE_OR_UPDATE_ALLOWLISTED_FILES",
        "merge_performed = $false",
        "approval_performed = $false",
        "force_push_performed = $false",
        "history_rewrite_performed = $false",
    ):
        assert token in runner
    assert not re.search(r"/merges(?:\?|\"|'|$)|/reviews(?:\?|\"|'|$)|git\s+push|git\s+merge|reset\s+--hard", runner, re.I)
    for token in ("ghp_", "github_pat_", "-----BEGIN PRIVATE KEY-----", "sk-proj-", "Bearer "):
        assert token not in "\n".join(read(path) for path in REQUIRED if path != RUNNER)

    print("DA-WP4B operator activation PASS; exact bounded authority active; final-head completion may proceed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
