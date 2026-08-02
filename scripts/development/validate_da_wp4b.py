#!/usr/bin/env python3
"""Validate DA-WP4B implementation, exact ruleset evidence and inactive gate state."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from ovc.development.receipt_bot import evaluate_activation, evaluate_work_packet, load_policy, load_work_packet  # noqa: E402

BASELINE = "d8a7f07f5abe376b917cf6f95f6e9ccc1864b7c3"
SHADOW_COMMIT = "0535db3ed4904fa9b2d1a4b6ba3deb9a338ab90e"
RULESET_SHA256 = "ed6fe8eb2c030fc185adbf70ae4571fca3fee2f3fbab8002267c8da2b221c0c4"
AUDIT_CANONICAL_SHA256 = "3d21a03d1772491da6cd1722712a816abd200b1f7f69fa76548ffa3b6a6476ea"
PASS_RUNS = {30755205496, 30755205526, 30755205480, 30755205470, 30755205478}
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
    "docs/releases/development-acceleration-v0-1/da-wp4b/main-ruleset.json",
]

def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")

def passed_runs(rows: list[dict[str, object]]) -> set[int]:
    return {int(row["run_id"]) for row in rows if row["result"] == "PASS"}

def verify_ruleset(path: Path) -> dict[str, object]:
    raw = path.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == RULESET_SHA256
    ruleset = json.loads(raw)
    assert ruleset["source"] == "owenguobadia24s-collab/ovc-replay"
    assert ruleset["enforcement"] == "active"
    assert "refs/heads/main" in ruleset["conditions"]["ref_name"]["include"]
    assert ruleset["bypass_actors"] == []
    assert ruleset["current_user_can_bypass"] == "never"
    rules = {row["type"]: row for row in ruleset["rules"]}
    assert {"deletion", "non_fast_forward", "pull_request", "required_status_checks"}.issubset(rules)
    assert rules["pull_request"]["parameters"]["allowed_merge_methods"] == ["squash"]
    assert rules["pull_request"]["parameters"]["required_review_thread_resolution"] is True
    checks = {row["context"] for row in rules["required_status_checks"]["parameters"]["required_status_checks"]}
    assert {"tests", "OVC tiered test selection shadow"}.issubset(checks)
    assert rules["required_status_checks"]["parameters"]["strict_required_status_checks_policy"] is True
    return ruleset

def main() -> int:
    missing = [p for p in REQUIRED if not (ROOT / p).is_file()]
    if missing:
        raise AssertionError(f"missing DA-WP4B files: {missing}")

    for schema_path in REQUIRED[1:3]:
        schema = json.loads(read(schema_path))
        assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
        assert schema["type"] == "object"
        assert schema["additionalProperties"] is False

    policy = load_policy(ROOT / REQUIRED[3])
    plan = evaluate_work_packet(load_work_packet(ROOT / REQUIRED[6]), policy)
    blocked = evaluate_work_packet(load_work_packet(ROOT / REQUIRED[7]), policy)
    assert plan["status"] == "PASS"
    assert plan["blockers"] == []
    assert plan["authority"]["active"] is False
    assert plan["authority"]["writes_performed"] is False
    assert plan["authority"]["merge_api_available"] is False
    assert blocked["status"] == "BLOCK"
    assert {"STALE_MAIN_SHA", "BRANCH_NOT_ALLOWED", "DESTRUCTIVE_ROLLBACK"}.issubset(blocked["blockers"])
    assert any(item.startswith("PATH_NOT_ALLOWED:") for item in blocked["blockers"])

    verify_ruleset(ROOT / REQUIRED[18])

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
    assert state["production_transport"] == "ABSENT_FAIL_CLOSED"
    assert state["authority_active"] is False
    assert state["shadow_evidence"]["shadow_pull_request"] == 211
    assert state["shadow_evidence"]["shadow_commit"] == SHADOW_COMMIT
    assert state["shadow_evidence"]["open_unmerged"] is True
    assert PASS_RUNS.issubset(passed_runs(state["tests"]))

    assert packet["packet_id"] == "DA-WP4B"
    assert packet["baseline_main_commit"] == BASELINE
    assert activation_record["authority_active"] is False
    assert activation_record["shadow"]["pull_request"] == 211
    assert activation_record["shadow"]["open_unmerged"] is True
    assert PASS_RUNS.issubset(passed_runs(activation_record["tests"]))
    assert qa["implementation_blocking_issues"] == []
    assert qa["authority_active"] is False
    assert PASS_RUNS.issubset(passed_runs(qa["tests"]))
    assert blocker["authority_active"] is False

    recorded = dict(audit)
    recorded_hash = recorded.pop("external_audit_file_sha256")
    canonical = json.dumps(recorded, indent=2).encode("utf-8") + b"\n"
    assert hashlib.sha256(canonical).hexdigest() == recorded_hash == AUDIT_CANONICAL_SHA256
    assert audit["ruleset_evidence_path"] == REQUIRED[18]
    assert audit["ruleset_evidence_sha256"] == RULESET_SHA256
    assert audit["operator_connector"] is False
    assert audit["revocable"] is True
    assert audit["pull_request_number"] == 211
    assert audit["commit_sha"] == SHADOW_COMMIT
    for field in ("authority_active", "production_transport_active", "merge_performed", "approval_performed", "force_push_performed", "history_rewrite_performed"):
        assert audit[field] is False

    assert shadow_qa["shadow_pull_request"] == 211
    assert shadow_qa["shadow_pr_must_remain_unmerged"] is True
    assert shadow_qa["authority_active"] is False
    assert programme["current_packet"] == "DA-WP4B"
    assert programme["current_gate"] == "DA-G4B"
    assert programme["authority"]["repository_bot_profile"] == "APPROVED_INACTIVE"
    assert programme["authority"]["repository_bot_production_transport"] == "ABSENT_FAIL_CLOSED"
    assert programme["authority"]["direct_main_write"] == "PROHIBITED"
    assert programme["activation_gate"]["authority_active"] is False

    activation_input = {condition: "PASS" for condition in policy.required_activation_conditions}
    activation_input["QA_PASS"] = "PENDING_OPERATOR_DECISION"
    activation = evaluate_activation(activation_input, policy)
    assert activation["status"] == "BLOCK"
    assert activation["authority_active"] is False

    bodies = "\n".join(read(path) for path in REQUIRED)
    assert '"active": true' not in bodies
    assert '"authority_active": true' not in bodies
    assert '"production_transport": "ACTIVE"' not in bodies

    print("DA-WP4B implementation, shadow and exact ruleset evidence PASS; activation remains inactive")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
