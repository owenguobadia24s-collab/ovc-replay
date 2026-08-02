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
AUDIT_SHA256 = "3d21a03d1772491da6cd1722712a816abd200b1f7f69fa76548ffa3b6a6476ea"
ACTIVATION_ID = "4815173d1ec559164072013f20d008f2d3a5b120841e8e6cb0350ee1f1164238"
DECISION_ID = "DA-G4B.OPERATOR.PASS.20260802T163600Z"

PATHS = {
    "policy": "registries/development/OVC_DEVELOPMENT_ACCELERATION_RECEIPT_BOT_POLICY_v0_1.json",
    "state": "registries/development/OVC_DEVELOPMENT_ACCELERATION_RECEIPT_BOT_IMPLEMENTATION_STATE_v0_1.json",
    "programme": "registries/development/OVC_DEVELOPMENT_ACCELERATION_PROGRAMME_STATE_v0_1.json",
    "active": "registries/development/OVC_DEVELOPMENT_ACCELERATION_RECEIPT_BOT_ACTIVE_PROFILE_v0_1.json",
    "work_pass": "fixtures/development/receipt_bot/work_packet_pass_v0_1.json",
    "work_block": "fixtures/development/receipt_bot/work_packet_block_v0_1.json",
    "decision": "docs/releases/development-acceleration-v0-1/da-wp4b/DA_G4B_OPERATOR_DECISION.json",
    "evaluation": "docs/releases/development-acceleration-v0-1/da-wp4b/DA_G4B_ACTIVATION_EVALUATION.json",
    "evidence": "docs/releases/development-acceleration-v0-1/da-wp4b/DA_WP4B_ACTIVATION_EVIDENCE.json",
    "qa": "docs/releases/development-acceleration-v0-1/da-wp4b/DA_WP4B_QA_PACKET.json",
    "blocker": "docs/releases/development-acceleration-v0-1/da-wp4b/DA_WP4B_BLOCKER_RECORD.json",
    "audit": "docs/releases/development-acceleration-v0-1/da-wp4b/DA_G4B_SHADOW_EXTERNAL_AUDIT.json",
    "shadow_qa": "docs/releases/development-acceleration-v0-1/da-wp4b/DA_G4B_SHADOW_QA_REVIEW.json",
    "ruleset": "docs/releases/development-acceleration-v0-1/da-wp4b/main-ruleset.json",
    "merge_receipt": "docs/releases/development-acceleration-v0-1/da-g4/DA_G4_MERGE_RECEIPT.json",
    "runner": "scripts/development/run_da_receipt_bot.ps1",
    "active_schema": "schemas/development/receipt_bot_active_profile_v0_1.schema.json",
    "work_schema": "schemas/development/receipt_bot_work_packet_v0_1.schema.json",
}


def text(key: str) -> str:
    return (ROOT / PATHS[key]).read_text(encoding="utf-8")


def data(key: str) -> dict[str, object]:
    value = json.loads(text(key))
    assert isinstance(value, dict)
    return value


def main() -> int:
    missing = [path for path in PATHS.values() if not (ROOT / path).is_file()]
    assert not missing, f"missing DA-WP4B activation files: {missing}"

    for key in ("active_schema", "work_schema"):
        schema = data(key)
        assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
        assert schema["type"] == "object"
        assert schema["additionalProperties"] is False

    policy = load_policy(ROOT / PATHS["policy"])
    passing = evaluate_work_packet(load_work_packet(ROOT / PATHS["work_pass"]), policy)
    blocked = evaluate_work_packet(load_work_packet(ROOT / PATHS["work_block"]), policy)
    assert passing["status"] == "PASS"
    assert passing["authority"]["active"] is False
    assert passing["authority"]["merge_api_available"] is False
    assert blocked["status"] == "BLOCK"
    assert {"STALE_MAIN_SHA", "BRANCH_NOT_ALLOWED", "DESTRUCTIVE_ROLLBACK"}.issubset(blocked["blockers"])

    raw_ruleset = (ROOT / PATHS["ruleset"]).read_bytes()
    assert hashlib.sha256(raw_ruleset).hexdigest() == RULESET_SHA256
    ruleset = json.loads(raw_ruleset)
    assert ruleset["enforcement"] == "active"
    assert ruleset["bypass_actors"] == []
    assert ruleset["current_user_can_bypass"] == "never"
    assert "refs/heads/main" in ruleset["conditions"]["ref_name"]["include"]
    rule_types = {row["type"] for row in ruleset["rules"]}
    assert {"deletion", "non_fast_forward", "pull_request", "required_status_checks"}.issubset(rule_types)

    active = data("active")
    assert active["active"] is True
    assert active["status"] == "ACTIVE"
    assert active["branch_protection_evidence_hash"] == RULESET_SHA256
    assert active["proposal_shadow_evidence_hash"] == AUDIT_SHA256
    assert active["activation_evaluation_id"] == ACTIVATION_ID

    decision = data("decision")
    evaluation = data("evaluation")
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

    state = data("state")
    programme = data("programme")
    evidence = data("evidence")
    qa = data("qa")
    blocker = data("blocker")
    assert state["baseline_main_commit"] == BASELINE
    assert state["operator_decision_id"] == DECISION_ID
    assert state["authority_active"] is True
    assert state["production_transport"].startswith("ACTIVE_FAIL_CLOSED:")
    assert state["shadow_evidence"]["shadow_pull_request"] == 211
    assert state["shadow_evidence"]["shadow_commit"] == SHADOW_COMMIT
    assert state["shadow_evidence"]["open_unmerged"] is True
    assert programme["operator_decision_required"] is False
    assert programme["authority"]["repository_bot_write"] == "ACTIVE_BOUNDED_PROPOSAL_BRANCH_ONLY"
    assert programme["authority"]["direct_main_write"] == "PROHIBITED"
    assert programme["activation_gate"]["authority_active"] is True
    assert programme["activation_gate"]["operator_decision_required"] is False
    assert evidence["authority_active"] is True
    assert qa["authority_active"] is True
    assert qa["implementation_blocking_issues"] == []
    assert qa["activation_blocking_issues"] == []
    assert blocker["authority_active"] is True
    assert data("merge_receipt")["squash_merge_sha"] == BASELINE

    audit = data("audit")
    recorded = dict(audit)
    recorded_hash = recorded.pop("external_audit_file_sha256")
    canonical = json.dumps(recorded, indent=2).encode("utf-8") + b"\n"
    assert hashlib.sha256(canonical).hexdigest() == recorded_hash == AUDIT_SHA256
    assert audit["pull_request_number"] == 211
    assert audit["commit_sha"] == SHADOW_COMMIT
    assert audit["authority_active"] is False
    assert data("shadow_qa")["shadow_pr_must_remain_unmerged"] is True

    runner = text("runner")
    for token in (
        DECISION_ID,
        "bot/ovc-dev-accel-receipts/*",
        "IDEMPOTENCY_COLLISION",
        "STALE_MAIN_SHA",
        "merge_performed = $false",
        "approval_performed = $false",
        "force_push_performed = $false",
        "history_rewrite_performed = $false",
    ):
        assert token in runner, token
    assert not re.search(r"/merges(?:\?|\"|'|$)|/reviews(?:\?|\"|'|$)|git\s+(?:push|merge|reset)", runner, re.I)

    record_keys = ("active", "decision", "evaluation", "evidence", "qa", "blocker", "state", "programme", "audit", "shadow_qa")
    records = "\n".join(text(key) for key in record_keys)
    for token in ("ghp_", "github_pat_", "-----BEGIN PRIVATE KEY-----", "sk-proj-", "Bearer "):
        assert token not in records

    print("DA-WP4B operator activation PASS; exact bounded authority active; final-head completion may proceed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
