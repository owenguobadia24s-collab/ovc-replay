#!/usr/bin/env python3
"""Validate DA-WP4 dry-run closure and DA-G4A court records."""

from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from ovc.development.closure import (  # noqa: E402
    compare_receipt_proposal,
    evaluate_closure,
    load_closure_policy,
    load_closure_snapshot,
    propose_merge_receipt,
)


BASELINE = "51c066cd851f3a222dde04bdd5f2e9769afe7a95"
MERGE_SHA = "3333333333333333333333333333333333333333"
REQUIRED = [
    "contracts/development/OVC_DRY_RUN_CLOSURE_AND_RECEIPT_CONTRACT_v0_1.md",
    "registries/development/OVC_DEVELOPMENT_ACCELERATION_CLOSURE_POLICY_v0_1.json",
    "schemas/development/closure_snapshot_v0_1.schema.json",
    "schemas/development/closure_proposal_v0_1.schema.json",
    "schemas/development/merge_receipt_proposal_v0_1.schema.json",
    "schemas/development/receipt_comparison_v0_1.schema.json",
    "src/ovc/development/closure.py",
    "tests/development/test_closure.py",
    "fixtures/development/closure/closure_snapshot_pass_v0_1.json",
    "fixtures/development/closure/closure_snapshot_block_v0_1.json",
    "fixtures/development/closure/manual_receipt_pass_v0_1.json",
    "docs/releases/development-acceleration-v0-1/da-wp3/DA_WP3_MERGE_RECEIPT.json",
    "docs/releases/development-acceleration-v0-1/da-g4a/DA_G4A_SHADOW_COMPARISON.json",
    "docs/releases/development-acceleration-v0-1/da-g4a/DA_G4A_GATE_PACKET.json",
    "docs/releases/development-acceleration-v0-1/da-g4a/DA_G4A_QA_PACKET.json",
    "docs/releases/development-acceleration-v0-1/da-g4a/DA_G4A_DELEGATED_DECISION.json",
    "registries/development/OVC_DEVELOPMENT_ACCELERATION_PROGRAMME_STATE_v0_1.json",
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
        raise AssertionError(f"missing DA-G4A files: {missing}")

    policy = load_closure_policy(ROOT / REQUIRED[1])
    snapshot = load_closure_snapshot(ROOT / REQUIRED[8])
    blocked_snapshot = load_closure_snapshot(ROOT / REQUIRED[9])
    manual = json.loads(read(REQUIRED[10]))
    evidence = json.loads(read(REQUIRED[12]))
    receipt = json.loads(read(REQUIRED[11]))
    gate = json.loads(read(REQUIRED[13]))
    qa = json.loads(read(REQUIRED[14]))
    decision = json.loads(read(REQUIRED[15]))
    state = json.loads(read(REQUIRED[16]))

    assert receipt["packet_id"] == "DA-WP3"
    assert receipt["squash_merge_sha"] == BASELINE
    assert receipt["decision"] == "PASS"

    for schema_path in REQUIRED[2:6]:
        schema = json.loads(read(schema_path))
        assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
        assert schema["type"] == "object"
        assert schema["additionalProperties"] is False

    closure = evaluate_closure(snapshot, policy)
    proposal = propose_merge_receipt(snapshot, policy, MERGE_SHA)
    comparison = compare_receipt_proposal(proposal, manual)
    blocked = evaluate_closure(blocked_snapshot, policy)
    assert closure["status"] == "PASS"
    assert closure["eligible_for_manual_squash_merge"] is True
    assert closure["authority"]["writes_performed"] is False
    assert closure["authority"]["merge_performed"] is False
    assert proposal["proposal_only"] is True
    assert comparison["status"] == "PASS"
    assert comparison["differences"] == []
    assert comparison["material_fields_equal"] is True
    assert blocked["status"] == "BLOCK"
    assert "REQUIRED_CHECK_NOT_PASS" in blocked["blockers"]
    assert "RESERVED_AUTHORITY_DELTA" in blocked["blockers"]
    assert "DESTRUCTIVE_ROLLBACK" in blocked["blockers"]
    assert evidence["closure_proposal"] == closure
    assert evidence["receipt_proposal"] == proposal
    assert evidence["comparison"] == comparison
    assert evidence["result"] == "PASS"
    assert evidence["repository_bot_write"] == "DENIED_UNTIL_DA_G4"

    assert state["programme_id"] == "OVC-DEV-ACCEL-v0.1"
    assert state["current_packet"] == "DA-WP4"
    assert state["current_gate"] == "DA-G4A"
    assert state["baseline_commit"] == BASELINE
    assert state["branch"] == "build/ovc-dev-accel-closure"
    assert state["authority"]["repository_bot_write"] == "DENIED_UNTIL_DA_G4"
    packets = {row["packet_id"]: row for row in state["packets"]}
    assert packets["DA-WP3"]["status"] == "COMPLETED"
    assert packets["DA-WP3"]["merge_commit"] == BASELINE
    assert packets["DA-WP4"]["status"] == "QA_REVIEW"
    assert packets["DA-WP4"]["authority_delta"] == "DRY_RUN_CLOSURE_AND_RECEIPT_COMPARISON_ONLY"
    assert state["open_concurrent_work"][0]["pull_request"] == 202

    assert gate["gate_id"] == "DA-G4A"
    assert gate["packet_id"] == "DA-WP4"
    assert gate["status"] == "QA_REVIEW"
    assert gate["baseline_commit"] == BASELINE
    assert gate["reserved_authority_delta"] == "NONE"
    assert gate["repository_bot_write"] == "DENIED_UNTIL_OPERATOR_DA_G4"
    assert gate["next_gate"] == "DA-G4"

    assert qa["status"] == "PASS_STATIC_PENDING_FINAL_HEAD_CI"
    assert qa["baseline_commit"] == BASELINE
    assert qa["blocking_issues"] == []
    assert qa["reserved_authority_delta"] == "NONE"
    assert qa["repository_bot_write"] == "DENIED_UNTIL_OPERATOR_DA_G4"

    assert decision["decision"] == "PENDING_CI"
    assert decision["decision_authority"] == "DELEGATED_BY_DA_G0_OPERATOR_APPROVED_PLAN"
    assert decision["baseline_commit"] == BASELINE
    assert decision["reserved_authority_delta"] == "NONE"
    assert decision["repository_bot_write"] == "DENIED_UNTIL_OPERATOR_DA_G4"

    require_tokens(REQUIRED[0], [
        "DRY_RUN_CLOSURE_AND_RECEIPT_COMPARISON_ONLY", "performs no GitHub write",
        "Repository-bot write remains", "exact head", "zero material differences", "DA-G4A", "DA-G4",
    ])
    require_tokens(REQUIRED[6], [
        "POLICY_IDENTITY_MISMATCH", "CHANGED_PATH_NOT_ALLOWED", "REQUIRED_CHECK_NOT_PASS",
        "DESTRUCTIVE_ROLLBACK", "writes_performed", "merge_performed", "compare_receipt_proposal",
    ])
    require_tokens(REQUIRED[7], [
        "test_pass_closure_is_deterministic_and_no_write",
        "test_receipt_proposal_matches_manual_reference",
        "test_block_fixture_surfaces_all_material_failures",
        "test_policy_identity_and_safety_boundaries_fail_closed",
    ])

    print("DA-G4A validation PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
