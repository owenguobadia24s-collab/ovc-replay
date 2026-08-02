#!/usr/bin/env python3
"""Validate immutable DA-G0/DA-00 records after later programme advances."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASELINE = "b9e763150858d02cc92d08efbcf2f6668b187a41"
DECISION_ID = "DA-G0.OPERATOR.PASS.20260801T151200Z"
CURRENT_PACKET_IDS = {
    "DA-00", "DA-WP1", "DA-WP2", "DA-WP3", "DA-WP4", "DA-G4", "DA-WP4B", "DA-WP5",
}
REQUIRED = [
    "contracts/development/OVC_DEVELOPMENT_ACCELERATION_AUTHORITY_CONTRACT_v0_1.md",
    "registries/development/OVC_DEVELOPMENT_ACCELERATION_BASELINE_PROFILE_v0_1.yaml",
    "registries/development/OVC_DEVELOPMENT_ACCELERATION_IMPLEMENTATION_REGISTRY_v0_1.yaml",
    "registries/development/OVC_DEVELOPMENT_ACCELERATION_DEPENDENCY_MAP_v0_1.yaml",
    "registries/development/OVC_DEVELOPMENT_ACCELERATION_PROGRAMME_STATE_v0_1.json",
    "docs/releases/development-acceleration-v0-1/da-00/DA_00_BASELINE_METRICS_PACKET.json",
    "docs/releases/development-acceleration-v0-1/da-g0/DA_G0_OPERATOR_DECISION.json",
    "docs/releases/development-acceleration-v0-1/da-g0/DA_G0_GATE_PACKET.json",
    "docs/releases/development-acceleration-v0-1/da-g0/DA_G0_QA_PACKET.json",
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
        raise AssertionError(f"missing DA-G0 files: {missing}")

    state = json.loads(read(REQUIRED[4]))
    metrics = json.loads(read(REQUIRED[5]))
    decision = json.loads(read(REQUIRED[6]))
    gate = json.loads(read(REQUIRED[7]))
    qa = json.loads(read(REQUIRED[8]))

    # DA-G0 court records remain immutable even after later gates advance.
    assert decision["decision_id"] == DECISION_ID
    assert decision["decision"] == "PASS"
    assert decision["decision_authority"] == "DIRECT_OPERATOR_OVC_RUN_COMMAND"
    assert decision["baseline_commit"] == BASELINE
    assert decision["repository_bot_write"] == "DENIED_UNTIL_DA_G4"
    assert decision["direct_main_write"] == "PROHIBITED"
    assert decision["market_authority_delta"] == "NONE"

    # Current programme state may lawfully advance through DA-G4/DA-G4B, but
    # the original DA-G0 denial and every permanent safety boundary must persist.
    assert state["programme_id"] == "OVC-DEV-ACCEL-v0.1"
    assert state["current_packet"] in CURRENT_PACKET_IDS
    assert DECISION_ID in state["operator_decision_history"]
    authority = state["authority"]
    repository_bot_write = authority["repository_bot_write"]
    assert repository_bot_write in {
        "DENIED_UNTIL_DA_G4",
        "APPROVED_FOR_BOUNDED_IMPLEMENTATION_NOT_ACTIVE",
        "ACTIVE_BOUNDED_PROPOSAL_BRANCH_ONLY",
    }
    if repository_bot_write == "APPROVED_FOR_BOUNDED_IMPLEMENTATION_NOT_ACTIVE":
        assert authority["repository_bot_profile"] == "APPROVED_INACTIVE"
        assert authority["repository_bot_production_transport"] == "ABSENT_FAIL_CLOSED"
    if repository_bot_write == "ACTIVE_BOUNDED_PROPOSAL_BRANCH_ONLY":
        assert authority["repository_bot_profile"] == "ACTIVE_EXACT_APPROVED_PROFILE"
        assert authority["repository_bot_production_transport"] == "ACTIVE_FAIL_CLOSED"
        assert authority["merge_pull_request"] == "PROHIBITED_TO_BOT"
        assert authority["approve_pull_request"] == "PROHIBITED_TO_BOT"
        assert "DA-G4B.OPERATOR.PASS.20260802T163600Z" in state["operator_decision_history"]
        assert state["activation_gate"]["recorded_decision"] == "PASS"
        assert state["activation_gate"]["authority_active"] is True
    assert authority["direct_main_write"] == "PROHIBITED"
    assert authority["force_push"] == "PROHIBITED"
    assert authority["history_rewrite"] == "PROHIBITED"
    assert authority["market"] == "NONE"
    assert authority["validation"] == "DENIED"
    assert authority["exposure"] == "NONE"
    assert authority["execution"] == "NONE"

    packet_by_id = {row["packet_id"]: row for row in state["packets"]}
    assert set(packet_by_id) == CURRENT_PACKET_IDS
    assert packet_by_id["DA-00"]["baseline_commit"] == BASELINE
    assert packet_by_id["DA-00"]["status"] in {"APPROVED", "COMPLETED"}
    assert packet_by_id["DA-00"]["blockers"] == []
    assert packet_by_id["DA-WP1"]["status"] in {"PLANNED", "RUNNING", "QA_REVIEW", "APPROVED", "COMPLETED"}
    assert packet_by_id["DA-G4"]["status"] == "COMPLETED"
    assert packet_by_id["DA-WP4B"]["status"] in {"RUNNING", "IMPLEMENTED", "QA_REVIEW", "GATE_READY", "APPROVED", "BLOCKED", "COMPLETED"}
    assert any(row["pull_request"] == 202 for row in state["open_concurrent_work"])

    impl = metrics["implementation_prs"]
    receipts = metrics["receipt_prs"]
    agg = metrics["aggregates"]
    assert [row["pr"] for row in impl] == [177, 180, 185, 191, 197, 200]
    assert [row["pr"] for row in receipts] == [178, 182, 186, 192, 199, 201]
    assert sum(row["elapsed_seconds"] for row in impl) == 4433
    assert sum(row["elapsed_seconds"] for row in receipts) == 1265
    assert sum(row["declared_workflow_runs"] for row in impl) == 16
    assert sum(row["declared_workflow_runs"] for row in receipts) == 12
    assert agg["one_purpose_receipt_pr_share"] == 0.5
    assert metrics["acceptance_targets"]["final_assurance_reduction_allowed"] == 0

    assert gate["gate_id"] == "DA-G0"
    assert gate["decision"] == "PASS"
    assert gate["baseline_commit"] == BASELINE
    assert gate["reserved_authority_delta"] == "NONE"
    assert gate["current_open_pull_requests"] == [202]
    assert gate["next_packet"] == "DA-WP1"
    assert qa["status"] == "PASS_APPROVED_PENDING_SQUASH_MERGE"
    assert qa["blocking_issues"] == []
    assert qa["authority_delta"] == "REPOSITORY_RECORDS_ONLY"
    assert qa["reserved_authority_delta"] == "NONE"

    require_tokens(REQUIRED[0], ["REPOSITORY_BOT_WRITE", "DENIED", "force-push", "Validation", "rewrite history", "Unknown test impact escalates"])
    require_tokens(REQUIRED[1], ["repository_bot_write: DENIED_UNTIL_DA_G4", "direct_main_write: PROHIBITED", "unknown_impact_policy: ESCALATE_TO_FINAL_HEAD", "raw_market_data_in_git: PROHIBITED"])
    require_tokens(REQUIRED[2], ["packet_id: DA-00", "packet_id: DA-WP1", "packet_id: DA-WP2", "packet_id: DA-WP3", "packet_id: DA-WP4", "packet_id: DA-WP5", "current_authority: DENIED"])
    require_tokens(REQUIRED[3], ["unknown_path_policy: FINAL_HEAD", "ambiguous_dependency_policy: BLOCK_AND_REQUIRE_PROFILE_CORRECTION", "reverse_dependency: DENIED", "gate_replay_substitution: PROHIBITED"])

    print("DA-G0 validation PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
