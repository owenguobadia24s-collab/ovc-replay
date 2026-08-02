#!/usr/bin/env python3
"""Validate immutable DA-WP4 dry-run closure and DA-G4A court records."""

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

def main() -> int:
    missing = [p for p in REQUIRED if not (ROOT / p).is_file()]
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
    assert blocked["status"] == "BLOCK"
    assert {"REQUIRED_CHECK_NOT_PASS", "RESERVED_AUTHORITY_DELTA", "DESTRUCTIVE_ROLLBACK"}.issubset(blocked["blockers"])
    assert evidence["closure_proposal"] == closure
    assert evidence["receipt_proposal"] == proposal
    assert evidence["comparison"] == comparison
    assert evidence["result"] == "PASS"

    packets = {row["packet_id"]: row for row in state["packets"]}
    wp4 = packets["DA-WP4"]
    assert wp4["status"] in {"APPROVED", "COMPLETED"}
    assert wp4["baseline_commit"] == BASELINE
    assert wp4["authority_delta"] == "DRY_RUN_CLOSURE_AND_RECEIPT_COMPARISON_ONLY"
    assert wp4["blockers"] == []
    assert wp4["merge_commit"] == "a561f30506c02dd26175d4a4f9e821d3074735a1"
    assert state["authority"]["direct_main_write"] == "PROHIBITED"
    assert state["open_concurrent_work"][0]["pull_request"] == 202

    assert gate["gate_id"] == "DA-G4A"
    assert gate["packet_id"] == "DA-WP4"
    assert gate["recommended_decision"] == "PASS"
    assert gate["reserved_authority_delta"] == "NONE"
    assert qa["qa_recommendation"] == "PASS"
    assert qa["blocking_issues"] == []
    assert decision["decision"] == "PASS"
    assert decision["reserved_authority_delta"] == "NONE"

    print("DA-G4A immutable validation PASS")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
