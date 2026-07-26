#!/usr/bin/env python3
"""Validate the RO2-G0 design packet and retained boundaries against the current court record."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

REQUIRED = [
    "contracts/research_operations/v0_2/OVC_RO2_AUTHORITY_CONTRACT_v0_1.md",
    "registries/research_operations/v0_2/RO2_ROLE_ACCESS_POLICY_v0_1.yaml",
    "registries/research_operations/v0_2/RO2_DEPENDENCY_POLICY_v0_1.yaml",
    "registries/research_operations/v0_2/RO2_IMPLEMENTATION_REGISTRY_v0_1.yaml",
    "registries/research_operations/v0_2/RO2_TYPED_OBJECT_AND_SCHEMA_CATALOGUE_v0_1.yaml",
    "registries/research_operations/v0_2/RO2_QA_CHECK_REGISTRY_v0_1.yaml",
    "fixtures/research_operations/v0_2/RO2_FIXTURE_MATRIX_v0_1.yaml",
    "docs/research-console/v0_3/RO2_CONSOLE_V0_3_PROJECTION_MAP_v0_1.md",
    "docs/releases/research-operations-foundation-v0-2/ro2-00/RO2_00_BASELINE_HASH_PACKET.json",
    "docs/releases/research-operations-foundation-v0-2/ro2-g0/RO2_G0_GATE_PACKET.json",
    "docs/releases/research-operations-foundation-v0-2/ro2-g0/RO2_G0_OPERATOR_REVIEW.md",
    "docs/CURRENT_STATUS.md",
    "registries/authority/ACTIVE_AUTHORITY.yaml",
]


def require_tokens(path: str, tokens: list[str]) -> None:
    text = (ROOT / path).read_text(encoding="utf-8")
    missing = [token for token in tokens if token not in text]
    if missing:
        raise AssertionError(f"{path}: missing tokens {missing}")


def main() -> int:
    missing_paths = [path for path in REQUIRED if not (ROOT / path).is_file()]
    if missing_paths:
        raise AssertionError(f"missing required RO2-G0 files: {missing_paths}")

    baseline = json.loads((ROOT / REQUIRED[8]).read_text(encoding="utf-8"))
    gate = json.loads((ROOT / REQUIRED[9]).read_text(encoding="utf-8"))

    # RO2-G0 remains pinned to the C2-G4 court record that existed when design froze.
    assert baseline["court_record_tip"] == "85d2638d36c5039c35d2d49fcdb499dd48e7b354"
    assert baseline["c2_g4_replay"]["state_records"] == 404434
    assert baseline["c2_g4_replay"]["transition_records"] == 323910
    assert baseline["retained_authority"]["validation_consumption"] == "LOCKED_UNCONSUMED"
    assert baseline["retained_authority"]["selector"] == "NONE"
    assert baseline["retained_authority"]["activation"] == "NONE"

    assert gate["decision"] == "PASS_DESIGN_FREEZE"
    assert gate["authority_delta"] == "DESIGN_CANON_ONLY"
    assert gate["checks"]["runtime_implementation_started"] == "NO"
    assert gate["retained"]["validation_consumption"] == "LOCKED_UNCONSUMED"
    assert gate["retained"]["c2_candidate_release"] == "NONE"
    assert gate["retained"]["c2_publication"] == "NONE"
    assert gate["retained"]["c2_selector"] == "NONE"
    assert gate["retained"]["c2_activation"] == "NONE"

    require_tokens(REQUIRED[0], ["FROZEN_DESIGN_ONLY", "No runtime indexer", "LOCKED_UNCONSUMED"])
    require_tokens(REQUIRED[1], ["validation_guard: DENY_BEFORE_PATH_RESOLUTION", "content_resolution: DENY"])
    require_tokens(REQUIRED[2], ["OPT_A_V2_VALIDATION_CONTENT", "GIT_PRIMARY_BRANCH", "R2_CANONICAL"])
    require_tokens(REQUIRED[3], ["RO2_G0_PASS_DESIGN_FREEZE", "NOT_STARTED_REQUIRES_SEPARATE_INSTRUCTION"])
    require_tokens(REQUIRED[4], ["RO2.ReplayFrame", "RO2.ConsoleResearchProjection", "Validation content identifiers may not be emitted"])
    require_tokens(REQUIRED[5], ["RO2-QA-002", "RO2-QA-004", "RO2-QA-011"])
    require_tokens(REQUIRED[6], ["validation_row_resolution_attempt", "prospective_frame_contains_post_cutoff_record", "attempted_git_r2_selector_or_threshold_write"])
    require_tokens(REQUIRED[7], ["Research workspace remains fixture-only", "Validation content must never be resolved"])

    # Later C2 gates may freeze candidates and approve exact publication while preserving
    # the RO2 boundary. Publication execution, selector, activation and Validation access
    # remain separately controlled.
    require_tokens(
        "docs/CURRENT_STATUS.md",
        [
            "### C2-G4 exact-parent replay",
            "C2-G4 result: `PASS_LOCAL_REPLAY`",
            "PASS_LOCAL_CANDIDATE_RELEASE_FROZEN",
            "PASS_PUBLICATION_READY_OPERATOR_APPROVED_EXACT_RELEASES_ONLY",
            "publication execution: `NOT_YET_EXECUTED`",
            "Validation remains `LOCKED_UNCONSUMED`",
        ],
    )
    require_tokens(
        "registries/authority/ACTIVE_AUTHORITY.yaml",
        [
            "C2_PUB_G0_PASS_PUBLICATION_AUTHORISED_NO_REMOTE_WRITE_NO_C2_AUTHORITY",
            "local_candidate_release: FROZEN_DISCOVERY_AND_DEVELOPMENT_LOCAL_ONLY",
            "publication: AUTHORISED_EXACT_RELEASES_ONLY",
            "publication_executed: false",
            "selector: NONE",
            "activation: NONE",
            "validation_consumption: LOCKED_UNCONSUMED",
        ],
    )

    print("PASS: RO2-G0 design packet remains valid against the reconciled C2 publication-readiness court record")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AssertionError, json.JSONDecodeError, OSError) as exc:
        print(f"BLOCK: {exc}", file=sys.stderr)
        raise SystemExit(1)
