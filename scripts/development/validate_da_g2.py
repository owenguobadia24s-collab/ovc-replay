#!/usr/bin/env python3
"""Validate DA-WP2 universal preflight and DA-G2 court records."""

from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from ovc.development.artifacts import ArtifactRef  # noqa: E402
from ovc.development.preflight import DestinationCheck, PreflightRequest, run_preflight  # noqa: E402
from ovc.development.profiles import load_profile  # noqa: E402


BASELINE = "90ea70f5ee9d706fc34c5186e182034a73e9a230"
TESTED = "5c977bfaf1acb8f2aaeae94f8233fc2fe2783a24"
DA_G2_RUN = 30707486877
GENERIC_RUN = 30707486751
REQUIRED = [
    "contracts/development/OVC_UNIVERSAL_ARTIFACT_PREFLIGHT_CONTRACT_v0_1.md",
    "schemas/development/preflight_request_v0_1.schema.json",
    "schemas/development/preflight_receipt_v0_1.schema.json",
    "src/ovc/development/preflight.py",
    "scripts/development/ovc_preflight.py",
    "tests/development/test_preflight.py",
    "fixtures/development/preflight/profile_pass_v0_1.json",
    "fixtures/development/preflight/refs_pass_v0_1.json",
    "fixtures/development/preflight/input/compact.json",
    "docs/releases/development-acceleration-v0-1/da-wp1/DA_WP1_MERGE_RECEIPT.json",
    "docs/releases/development-acceleration-v0-1/da-g2/DA_G2_GATE_PACKET.json",
    "docs/releases/development-acceleration-v0-1/da-g2/DA_G2_QA_PACKET.json",
    "docs/releases/development-acceleration-v0-1/da-g2/DA_G2_DELEGATED_DECISION.json",
    "registries/development/OVC_DEVELOPMENT_ACCELERATION_PROGRAMME_STATE_v0_1.json",
]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def require_tokens(path: str, tokens: list[str]) -> None:
    body = read(path)
    missing = [token for token in tokens if token not in body]
    if missing:
        raise AssertionError(f"{path}: missing {missing}")


def load_ref() -> ArtifactRef:
    rows = json.loads(read("fixtures/development/preflight/refs_pass_v0_1.json"))
    assert isinstance(rows, list) and len(rows) == 1
    return ArtifactRef(**rows[0])


def assert_runs(rows: list[dict[str, object]]) -> None:
    actual = {(row["run_id"], row["result"]) for row in rows}
    assert (DA_G2_RUN, "PASS") in actual
    assert (GENERIC_RUN, "PASS") in actual


def main() -> int:
    missing = [path for path in REQUIRED if not (ROOT / path).is_file()]
    if missing:
        raise AssertionError(f"missing DA-G2 files: {missing}")

    state = json.loads(read(REQUIRED[13]))
    gate = json.loads(read(REQUIRED[10]))
    qa = json.loads(read(REQUIRED[11]))
    decision = json.loads(read(REQUIRED[12]))
    receipt = json.loads(read(REQUIRED[9]))

    assert receipt["packet_id"] == "DA-WP1"
    assert receipt["squash_merge_sha"] == BASELINE
    assert receipt["decision"] == "PASS"

    assert state["programme_id"] == "OVC-DEV-ACCEL-v0.1"
    assert state["current_packet"] == "DA-WP2"
    assert state["current_gate"] == "DA-G2"
    assert state["baseline_commit"] == BASELINE
    assert state["branch"] == "build/ovc-dev-accel-preflight"
    assert state["candidate_commit"] == TESTED
    assert state["authority"]["repository_bot_write"] == "DENIED_UNTIL_DA_G4"
    assert state["authority"]["direct_main_write"] == "PROHIBITED"
    packets = {row["packet_id"]: row for row in state["packets"]}
    assert packets["DA-WP1"]["status"] == "COMPLETED"
    assert packets["DA-WP1"]["merge_commit"] == BASELINE
    assert packets["DA-WP2"]["status"] == "APPROVED"
    assert packets["DA-WP2"]["candidate_commit"] == TESTED
    assert packets["DA-WP2"]["blockers"] == []
    assert packets["DA-WP2"]["authority_delta"] == "FAIL_CLOSED_EXECUTION_GUARD"
    assert packets["DA-WP3"]["status"] == "READY"
    assert state["open_concurrent_work"][0]["pull_request"] == 202

    assert gate["gate_id"] == "DA-G2"
    assert gate["packet_id"] == "DA-WP2"
    assert gate["status"] == "PASS_APPROVED_PENDING_SQUASH_MERGE"
    assert gate["baseline_commit"] == BASELINE
    assert gate["tested_candidate_commit"] == TESTED
    assert gate["reserved_authority_delta"] == "NONE"
    assert gate["repository_bot_write"] == "DENIED"
    assert gate["recommended_decision"] == "PASS"
    assert gate["next_packet"] == "DA-WP3"
    assert_runs(gate["tests"])

    assert qa["status"] == "PASS_APPROVED_PENDING_SQUASH_MERGE"
    assert qa["baseline_commit"] == BASELINE
    assert qa["tested_candidate_commit"] == TESTED
    assert qa["blocking_issues"] == []
    assert qa["qa_recommendation"] == "PASS"
    assert qa["authority_delta"] == "FAIL_CLOSED_EXECUTION_GUARD"
    assert qa["reserved_authority_delta"] == "NONE"
    assert_runs(qa["tests"])

    assert decision["decision"] == "PASS"
    assert decision["decision_authority"] == "DELEGATED_BY_DA_G0_OPERATOR_APPROVED_PLAN"
    assert decision["baseline_commit"] == BASELINE
    assert decision["tested_candidate_commit"] == TESTED
    assert decision["reserved_authority_delta"] == "NONE"
    assert decision["repository_bot_write"] == "DENIED"
    assert_runs(decision["tests"])

    for schema_path in REQUIRED[1:3]:
        schema = json.loads(read(schema_path))
        assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
        assert schema["type"] == "object"
        assert schema["additionalProperties"] is False

    require_tokens(REQUIRED[0], [
        "FAIL_CLOSED_EXECUTION_GUARD", "read-only", "ABSENT_OR_EMPTY",
        "No-write guarantee", "under 30 seconds", "write R2", "consume Validation",
    ])
    require_tokens(REQUIRED[3], [
        "UNSUPPORTED_IDENTITY_POLICY", "DESTINATION_COLLISION", "writes_performed",
        "provider_access", "direct_main_write", "force_push",
    ])
    require_tokens(REQUIRED[5], [
        "test_pass_is_deterministic_root_independent_and_read_only",
        "test_exact_bytes_schema_and_profile_mismatches_block",
        "test_destination_collisions_and_invalid_roots_block",
        "test_cli_pass_and_block_exit_codes",
    ])

    profile = load_profile(ROOT / REQUIRED[6])
    request = PreflightRequest(
        profile,
        (load_ref(),),
        (
            DestinationCheck("new-output", "outputs/new-packet", "ABSENT"),
            DestinationCheck("empty-output", "outputs/empty-packet", "ABSENT_OR_EMPTY"),
        ),
    )
    with tempfile.TemporaryDirectory() as raw_a, tempfile.TemporaryDirectory() as raw_b:
        destination_a = Path(raw_a)
        destination_b = Path(raw_b)
        (destination_a / "outputs/empty-packet").mkdir(parents=True)
        (destination_b / "outputs/empty-packet").mkdir(parents=True)
        result_a = run_preflight(ROOT / "fixtures/development/preflight", destination_a, request)
        result_b = run_preflight(ROOT / "fixtures/development/preflight", destination_b, request)
    assert result_a["status"] == "PASS"
    assert result_a == result_b
    assert result_a["authority"]["writes_performed"] is False
    assert result_a["authority"]["repository_bot_write"] == "DENIED"

    print("DA-G2 validation PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
