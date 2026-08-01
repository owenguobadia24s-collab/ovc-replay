#!/usr/bin/env python3
"""Validate DA-G0 ratification and DA-00 baseline records."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASELINE = "b9e763150858d02cc92d08efbcf2f6668b187a41"
DECISION_ID = "DA-G0.OPERATOR.PASS.20260801T151200Z"

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

    assert decision["decision_id"] == DECISION_ID
    assert decision["decision"] == "PASS"
    assert decision["decision_authority"] == "DIRECT_OPERATOR_OVC_RUN_COMMAND"
    assert decision["baseline_commit"] == BASELINE
    assert decision["repository_bot_write"] == "DENIED_UNTIL_DA_G4"
    assert decision["direct_main_write"] == "PROHIBITED"
    assert decision["market_authority_delta"] == "NONE"

    assert state["programme_id"] == "OVC-DEV-ACCEL-v0.1"
    assert state["baseline_commit"] == BASELINE
    assert state["current_packet"] == "DA-00"
    assert state["operator_decision_id"] == DECISION_ID
    assert state["authority"]["repository_bot_write"] == "DENIED_UNTIL_DA_G4"
    assert state["authority"]["direct_main_write"] == "PROHIBITED"
    assert state["packets"][0]["status"] == "QA_REVIEW"
    assert state["packets"][1]["status"] == "PLANNED"
    assert state["open_concurrent_work"][0]["pull_request"] == 202

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

    assert qa["status"] == "PASS_STATIC_PENDING_FINAL_HEAD_CI"
    assert qa["blocking_issues"] == []
    assert qa["authority_delta"] == "REPOSITORY_RECORDS_ONLY"

    require_tokens(REQUIRED[0], [
        "REPOSITORY_BOT_WRITE", "DENIED", "force-push", "Validation",
        "No history rewrite", "Unknown test impact escalates",
    ])
    require_tokens(REQUIRED[1], [
        "repository_bot_write: DENIED_UNTIL_DA_G4",
        "direct_main_write: PROHIBITED",
        "unknown_impact_policy: ESCALATE_TO_FINAL_HEAD",
        "raw_market_data_in_git: PROHIBITED",
    ])
    require_tokens(REQUIRED[2], [
        "packet_id: DA-00", "packet_id: DA-WP1", "packet_id: DA-WP2",
        "packet_id: DA-WP3", "packet_id: DA-WP4", "packet_id: DA-WP5",
        "current_authority: DENIED",
    ])
    require_tokens(REQUIRED[3], [
        "unknown_path_policy: FINAL_HEAD",
        "ambiguous_dependency_policy: BLOCK_AND_REQUIRE_PROFILE_CORRECTION",
        "reverse_dependency: DENIED",
        "gate_replay_substitution: PROHIBITED",
    ])

    print("DA-G0 validation PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
