#!/usr/bin/env python3
"""Validate DA-G6 default-workflow adoption operator gate readiness."""

from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]

REQUIRED = [
    "contracts/development/OVC_DEVELOPMENT_ACCELERATION_DEFAULT_WORKFLOW_ADOPTION_PROPOSAL_v0_1.md",
    "schemas/development/default_workflow_adoption_profile_v0_1.schema.json",
    "registries/development/OVC_DEVELOPMENT_ACCELERATION_DEFAULT_WORKFLOW_PROPOSAL_v0_1.json",
    "docs/releases/development-acceleration-v0-1/da-g6/DA_G6_GATE_PACKET.json",
    "docs/releases/development-acceleration-v0-1/da-g6/DA_G6_QA_PACKET.json",
    "docs/releases/development-acceleration-v0-1/da-g6/DA_G6_OPERATOR_DECISION_REQUEST.json",
    "registries/development/OVC_DEVELOPMENT_ACCELERATION_PROGRAMME_STATE_v0_1.json",
    "registries/development/OVC_DEVELOPMENT_ACCELERATION_IMPLEMENTATION_REGISTRY_v0_1.yaml",
    "tests/development/test_da_g6.py",
]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def load(path: str) -> dict[str, object]:
    value = json.loads(read(path))
    assert isinstance(value, dict)
    return value


def main() -> int:
    missing = [path for path in REQUIRED if not (ROOT / path).is_file()]
    if missing:
        raise AssertionError(f"missing DA-G6 files: {missing}")

    schema = load(REQUIRED[1])
    profile = load(REQUIRED[2])
    gate = load(REQUIRED[3])
    qa = load(REQUIRED[4])
    request = load(REQUIRED[5])
    state = load(REQUIRED[6])

    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["type"] == "object"
    assert schema["additionalProperties"] is False
    assert schema["properties"]["status"]["const"] == "PENDING_OPERATOR_DA_G6"
    assert schema["properties"]["active"]["const"] is False

    assert profile["profile_id"] == "OVC.DEVELOPMENT.ACCELERATION.DEFAULT-WORKFLOW.v0.1"
    assert profile["status"] == "PENDING_OPERATOR_DA_G6"
    assert profile["active"] is False
    assert profile["retirement_mode"] == "NON_DESTRUCTIVE_RETIRED_NON_AUTHORITATIVE"
    assert len(profile["retired_mechanics"]) == 5
    assert "OPERATOR_RESERVED_AUTHORITY_REQUIRES_GATE" in profile["exceptions"]

    required_denials = {
        "WRITE_MAIN",
        "BOT_MERGE_PULL_REQUEST",
        "BOT_APPROVE_PULL_REQUEST",
        "FORCE_PUSH",
        "REWRITE_HISTORY",
        "DELETE_ACCEPTED_RECORD",
        "PROVIDER_ACCESS",
        "R2_WRITE",
        "RELEASE_PUBLICATION",
        "SELECTOR_OR_SEMANTIC_MUTATION",
        "ACTIVE_DISCOVERY_DEVELOPMENT_OR_VALIDATION",
        "NEW_MARKET_INSTRUMENT_CLOCK_SIDE_OR_DEPENDENCY",
        "PROBABILITY_RISK_EXPOSURE_OR_EXECUTION_AUTHORITY",
        "UNAPPROVED_AGENT_WRITE_AUTHORITY",
    }
    assert required_denials.issubset(set(profile["permanent_denials"]))

    assert gate["gate_id"] == "DA-G6"
    assert gate["branch"] == "gate/ovc-dev-accel-da-g6"
    assert gate["allowed_decisions"] == ["PASS", "DEFER", "BLOCK", "QUARANTINE", "SUPERSEDE"]
    assert gate["operator_command"] == "OVC APPROVE DA-G6 PASS"
    assert gate["operator_decision_required"] is True
    assert gate["default_workflow_active"] is False
    assert gate["retirement_active"] is False
    assert gate["warnings"] == []
    assert gate["unresolved_issues"] == []
    assert len(gate["completed_packets"]) == 10
    assert len(gate["exact_work_after_approval"]) == 8

    assert request["gate_id"] == "DA-G6"
    assert request["allowed_decisions"] == gate["allowed_decisions"]
    assert request["operator_command"] == gate["operator_command"]
    assert request["operator_decision_required"] is True
    assert request["default_workflow_active"] is False
    assert request["retirement_active"] is False

    assert qa["gate_id"] == "DA-G6"
    assert qa["reserved_authority_delta"] == "OPERATOR_REQUIRED"
    assert qa["warnings"] == []
    assert qa["default_workflow_active"] is False
    assert qa["retirement_active"] is False

    authority = state["authority"]
    assert authority["default_workflow_adoption"] == "DENIED_UNTIL_DA_G6"
    assert authority["direct_main_write"] == "PROHIBITED"
    assert authority["merge_pull_request"] == "PROHIBITED_TO_BOT"
    assert authority["approve_pull_request"] == "PROHIBITED_TO_BOT"
    assert authority["force_push"] == "PROHIBITED"
    assert authority["history_rewrite"] == "PROHIBITED"
    assert authority["market"] == "NONE"
    assert authority["validation"] == "DENIED"
    assert authority["exposure"] == "NONE"
    assert authority["execution"] == "NONE"

    bodies = "\n".join(read(path) for path in REQUIRED)
    assert '"default_workflow_active": true' not in bodies
    assert '"retirement_active": true' not in bodies
    assert '"active": true' not in read(REQUIRED[2])
    assert "force-push" in read(REQUIRED[0])
    assert "No file deletion" in read(REQUIRED[0])
    assert "RETIRED_NON_AUTHORITATIVE" in read(REQUIRED[0])
    for token in ("ghp_", "github_pat_", "-----BEGIN PRIVATE KEY-----", "sk-proj-", "Bearer "):
        assert token not in bodies

    print("DA-G6 operator gate validation PASS; proposal remains inactive")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
