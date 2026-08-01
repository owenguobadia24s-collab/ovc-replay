#!/usr/bin/env python3
"""Validate DA-WP3 tiered test selection and DA-G3 court records."""

from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from ovc.development.test_selection import load_test_profile_registry, select_test_manifest  # noqa: E402


BASELINE = "19f8f25ee57e0d8e026162229aa235990bbd6491"
TESTED = "fb18864bf477e9b3d0a9d13fe2185c4b6d02b2db"
DA_G3_RUN = 30708043830
SHADOW_RUN = 30708043814
REQUIRED = [
    "contracts/development/OVC_TIERED_TEST_SELECTION_CONTRACT_v0_1.md",
    "registries/development/OVC_DEVELOPMENT_ACCELERATION_TEST_PROFILE_REGISTRY_v0_1.json",
    "schemas/development/test_selection_manifest_v0_1.schema.json",
    "src/ovc/development/test_selection.py",
    "scripts/development/ovc_test_select.py",
    "tests/development/test_test_selection.py",
    "fixtures/development/test_selection/fast_paths.txt",
    "fixtures/development/test_selection/packet_paths.txt",
    "fixtures/development/test_selection/unknown_paths.txt",
    ".github/workflows/ovc-tiered-tests.yml",
    "docs/development-acceleration/TIERED_TEST_OPERATOR_GUIDE_v0_1.md",
    "docs/releases/development-acceleration-v0-1/da-wp2/DA_WP2_MERGE_RECEIPT.json",
    "docs/releases/development-acceleration-v0-1/da-g3/DA_G3_GATE_PACKET.json",
    "docs/releases/development-acceleration-v0-1/da-g3/DA_G3_QA_PACKET.json",
    "docs/releases/development-acceleration-v0-1/da-g3/DA_G3_DELEGATED_DECISION.json",
    "registries/development/OVC_DEVELOPMENT_ACCELERATION_PROGRAMME_STATE_v0_1.json",
]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def require_tokens(path: str, tokens: list[str]) -> None:
    body = read(path)
    missing = [token for token in tokens if token not in body]
    if missing:
        raise AssertionError(f"{path}: missing {missing}")


def paths(name: str) -> list[str]:
    return [line for line in read(f"fixtures/development/test_selection/{name}").splitlines() if line]


def assert_runs(rows: list[dict[str, object]]) -> None:
    actual = {(row["run_id"], row["result"]) for row in rows}
    assert (DA_G3_RUN, "PASS") in actual
    assert (SHADOW_RUN, "PASS") in actual


def main() -> int:
    missing = [path for path in REQUIRED if not (ROOT / path).is_file()]
    if missing:
        raise AssertionError(f"missing DA-G3 files: {missing}")

    registry = load_test_profile_registry(ROOT / REQUIRED[1])
    schema = json.loads(read(REQUIRED[2]))
    receipt = json.loads(read(REQUIRED[11]))
    gate = json.loads(read(REQUIRED[12]))
    qa = json.loads(read(REQUIRED[13]))
    decision = json.loads(read(REQUIRED[14]))
    state = json.loads(read(REQUIRED[15]))

    assert receipt["packet_id"] == "DA-WP2"
    assert receipt["squash_merge_sha"] == BASELINE
    assert receipt["decision"] == "PASS"

    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["type"] == "object"
    assert schema["additionalProperties"] is False
    assert schema["properties"]["final_assurance_required"]["const"] is True
    assert schema["properties"]["gate_replay_substitution"]["const"] == "PROHIBITED"

    assert registry.profile_order == ("FAST", "PACKET", "FINAL_HEAD")
    assert registry.unknown_path_policy == "FINAL_HEAD"
    assert registry.ambiguous_dependency_policy == "BLOCK_AND_REQUIRE_PROFILE_CORRECTION"
    assert registry.final_assurance["complete_repository_suite"] is True
    assert registry.final_assurance["gate_replay_substitution"] == "PROHIBITED"
    assert registry.final_assurance["local_success_substitutes_remote_required_check"] is False

    fast = select_test_manifest(paths("fast_paths.txt"), registry)
    packet = select_test_manifest(paths("packet_paths.txt"), registry)
    unknown = select_test_manifest(paths("unknown_paths.txt"), registry)
    final = select_test_manifest(paths("packet_paths.txt"), registry, stage="FINAL_HEAD")
    replay = select_test_manifest(
        paths("packet_paths.txt"),
        registry,
        stage="GATE_REPLAY",
        gate_id="DA-G3",
        gate_command="PYTHONPATH=src python scripts/development/validate_da_g3.py",
    )
    assert fast["selected_profile"] == "FAST"
    assert packet["selected_profile"] == "PACKET"
    assert unknown["selected_profile"] == "FINAL_HEAD"
    assert unknown["unknown_paths"] == ["src/unregistered/new_component.py"]
    assert final["selected_profile"] == "FINAL_HEAD"
    assert replay["selected_profile"] == "GATE_REPLAY"
    for manifest in (fast, packet, unknown, final, replay):
        assert manifest["status"] == "PASS"
        assert manifest["final_assurance_required"] is True
        assert manifest["final_assurance_profile"] == "FINAL_HEAD"
        assert manifest["gate_replay_substitution"] == "PROHIBITED"
        assert manifest["local_success_substitutes_remote_required_check"] is False
        assert manifest["authority"]["repository_bot_write"] == "DENIED"
        assert manifest["authority"]["direct_main_write"] == "DENIED"

    assert state["programme_id"] == "OVC-DEV-ACCEL-v0.1"
    assert state["current_packet"] == "DA-WP3"
    assert state["current_gate"] == "DA-G3"
    assert state["baseline_commit"] == BASELINE
    assert state["branch"] == "build/ovc-dev-accel-test-profiles"
    assert state["candidate_commit"] == TESTED
    assert state["authority"]["repository_bot_write"] == "DENIED_UNTIL_DA_G4"
    assert state["authority"]["default_workflow_adoption"] == "DENIED_UNTIL_DA_G6"
    packets = {row["packet_id"]: row for row in state["packets"]}
    assert packets["DA-WP2"]["status"] == "COMPLETED"
    assert packets["DA-WP2"]["merge_commit"] == BASELINE
    assert packets["DA-WP3"]["status"] == "APPROVED"
    assert packets["DA-WP3"]["candidate_commit"] == TESTED
    assert packets["DA-WP3"]["blockers"] == []
    assert packets["DA-WP4"]["status"] == "READY_AFTER_DA_WP3_MERGE"
    assert state["open_concurrent_work"][0]["pull_request"] == 202

    assert gate["gate_id"] == "DA-G3"
    assert gate["packet_id"] == "DA-WP3"
    assert gate["status"] == "PASS_APPROVED_PENDING_SQUASH_MERGE"
    assert gate["baseline_commit"] == BASELINE
    assert gate["tested_candidate_commit"] == TESTED
    assert gate["reserved_authority_delta"] == "NONE"
    assert gate["repository_bot_write"] == "DENIED"
    assert gate["default_workflow_adoption"] == "DENIED_UNTIL_DA_G6"
    assert gate["recommended_decision"] == "PASS"
    assert gate["next_packet"] == "DA-WP4"
    assert_runs(gate["tests"])

    assert qa["status"] == "PASS_APPROVED_PENDING_SQUASH_MERGE"
    assert qa["baseline_commit"] == BASELINE
    assert qa["tested_candidate_commit"] == TESTED
    assert qa["blocking_issues"] == []
    assert qa["qa_recommendation"] == "PASS"
    assert qa["reserved_authority_delta"] == "NONE"
    assert qa["repository_bot_write"] == "DENIED"
    assert_runs(qa["tests"])

    assert decision["decision"] == "PASS"
    assert decision["decision_authority"] == "DELEGATED_BY_DA_G0_OPERATOR_APPROVED_PLAN"
    assert decision["baseline_commit"] == BASELINE
    assert decision["tested_candidate_commit"] == TESTED
    assert decision["reserved_authority_delta"] == "NONE"
    assert decision["default_workflow_adoption"] == "DENIED_UNTIL_DA_G6"
    assert_runs(decision["tests"])

    require_tokens(REQUIRED[0], [
        "DETERMINISTIC_TEST_PROFILE_SELECTION", "FAST < PACKET < FINAL_HEAD",
        "unknown path escalates", "GATE_REPLAY", "PROHIBITED", "complete final assurance",
    ])
    require_tokens(REQUIRED[3], [
        "AMBIGUOUS_PATH", "unknown-path-final-head-escalation", "final_assurance_required",
        "gate_replay_substitution", "repository_bot_write", "direct_main_write",
    ])
    require_tokens(REQUIRED[5], [
        "test_unknown_path_escalates_and_never_skips",
        "test_gate_replay_is_orthogonal_and_cannot_substitute",
        "test_ambiguous_highest_priority_rules_block",
        "test_registry_rejects_assurance_weakening_and_bad_requests",
    ])
    require_tokens(REQUIRED[9], [
        "OVC tiered test selection shadow", "test-selection-manifest.json",
        "OVC_SELECTED_PROFILE", "Retain final assurance boundary",
    ])

    print("DA-G3 validation PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
