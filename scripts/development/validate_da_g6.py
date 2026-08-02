#!/usr/bin/env python3
"""Validate DA-G6 default-workflow adoption operator gate readiness."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

CONTRACT = "contracts/development/OVC_DEVELOPMENT_ACCELERATION_DEFAULT_WORKFLOW_ADOPTION_PROPOSAL_v0_1.md"
SCHEMA = "schemas/development/default_workflow_adoption_profile_v0_1.schema.json"
PROFILE = "registries/development/OVC_DEVELOPMENT_ACCELERATION_DEFAULT_WORKFLOW_PROPOSAL_v0_1.json"
GATE = "docs/releases/development-acceleration-v0-1/da-g6/DA_G6_GATE_PACKET.json"
QA = "docs/releases/development-acceleration-v0-1/da-g6/DA_G6_QA_PACKET.json"
REQUEST = "docs/releases/development-acceleration-v0-1/da-g6/DA_G6_OPERATOR_DECISION_REQUEST.json"
STATE = "registries/development/OVC_DEVELOPMENT_ACCELERATION_PROGRAMME_STATE_v0_1.json"
REGISTRY = "registries/development/OVC_DEVELOPMENT_ACCELERATION_IMPLEMENTATION_REGISTRY_v0_1.yaml"
TEST = "tests/development/test_da_g6.py"
WORKFLOW = ".github/workflows/development-acceleration-da-g6.yml"
REQUIRED = [CONTRACT, SCHEMA, PROFILE, GATE, QA, REQUEST, STATE, REGISTRY, TEST, WORKFLOW]

CONDITION_KEYS = {
    "sealed_candidate_two_phase_gate",
    "atomic_git_transaction_and_head_budget",
    "one_active_pr_programme_lease",
    "required_check_provenance_and_ruleset_health",
    "canonical_required_pr_runtime",
}


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

    schema = load(SCHEMA)
    profile = load(PROFILE)
    gate = load(GATE)
    qa = load(QA)
    request = load(REQUEST)
    state = load(STATE)
    contract = read(CONTRACT)
    workflow = read(WORKFLOW)

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

    controls = profile["mandatory_acceleration_conditions"]
    assert set(controls) == CONDITION_KEYS
    sealed = controls["sealed_candidate_two_phase_gate"]
    assert sealed["candidate_sha_binding_required"] is True
    assert sealed["post_seal_candidate_mutation"] == "PROHIBITED"
    assert sealed["state_sequence"] == [
        "IMPLEMENTED", "QA_REVIEW", "CANDIDATE_SEALED",
        "OPERATOR_DECISION_PENDING", "MERGED", "RECEIPT_RECORDED",
    ]
    atomic = controls["atomic_git_transaction_and_head_budget"]
    assert atomic["transaction"] == "ONE_BLOB_TREE_COMMIT_FAST_FORWARD_UPDATE"
    assert atomic["maximum_preseal_candidate_head_mutations"] == 2
    assert atomic["maximum_postseal_candidate_head_mutations"] == 0
    lease = controls["one_active_pr_programme_lease"]
    assert lease["maximum_active_continuation_prs"] == 1
    provenance = controls["required_check_provenance_and_ruleset_health"]
    assert provenance["source_identity_mismatch_result"] == "BLOCK"
    assert "expected_check_source_identity" in provenance["required_fields"]
    runtime = controls["canonical_required_pr_runtime"]
    assert runtime == {
        "runner": "ubuntu-latest",
        "python": "3.11",
        "additional_versions": "SCHEDULED_MANUAL_OR_RELEASE_SPECIFIC_UNLESS_EXPLICITLY_REQUIRED",
    }
    assert schema["properties"]["mandatory_acceleration_conditions"]["const"] == controls

    required_denials = {
        "WRITE_MAIN", "BOT_MERGE_PULL_REQUEST", "BOT_APPROVE_PULL_REQUEST",
        "FORCE_PUSH", "REWRITE_HISTORY", "DELETE_ACCEPTED_RECORD",
        "PROVIDER_ACCESS", "R2_WRITE", "RELEASE_PUBLICATION",
        "SELECTOR_OR_SEMANTIC_MUTATION", "ACTIVE_DISCOVERY_DEVELOPMENT_OR_VALIDATION",
        "NEW_MARKET_INSTRUMENT_CLOCK_SIDE_OR_DEPENDENCY",
        "PROBABILITY_RISK_EXPOSURE_OR_EXECUTION_AUTHORITY",
        "UNAPPROVED_AGENT_WRITE_AUTHORITY",
    }
    assert required_denials.issubset(set(profile["permanent_denials"]))

    assert gate["gate_id"] == "DA-G6"
    assert gate["branch"] == "gate/ovc-dev-accel-da-g6"
    assert gate["pull_request"] == 218
    assert gate["allowed_decisions"] == ["PASS", "DEFER", "BLOCK", "QUARANTINE", "SUPERSEDE"]
    assert gate["operator_command"] == "OVC APPROVE DA-G6 PASS"
    assert gate["operator_decision_required"] is True
    assert gate["default_workflow_active"] is False
    assert gate["retirement_active"] is False
    assert gate["warnings"] == []
    assert gate["unresolved_issues"] == []
    assert gate["candidate_protocol"]["post_seal_candidate_mutation"] == "PROHIBITED"
    assert gate["proposed_authority_delta"]["programme_lease"]["predecessor_resolution"] == "MERGED"
    assert gate["proposed_authority_delta"]["programme_lease"]["predecessor_merge_commit"] == "fed2a3c260c24ffcb5d073ccdf51987800d26f22"
    assert gate["proposed_authority_delta"]["canonical_required_pr_runtime"] == {"runner": "ubuntu-latest", "python": "3.11"}
    assert len(gate["proposed_authority_delta"]["mandatory_acceleration_conditions"]) == 5
    assert len(gate["exact_work_after_approval"]) == 8

    assert request["mandatory_conditions"] == gate["proposed_authority_delta"]["mandatory_acceleration_conditions"]
    assert request["candidate_binding"] == "PASS_DECISION_MUST_REFERENCE_EXACT_CANDIDATE_SHA_AND_FAIL_IF_PR_HEAD_MOVES"
    assert request["operator_decision_required"] is True
    assert request["default_workflow_active"] is False
    assert request["retirement_active"] is False

    assert qa["gate_id"] == "DA-G6"
    assert qa["reserved_authority_delta"] == "OPERATOR_REQUIRED"
    assert qa["warnings"] == []
    assert qa["default_workflow_active"] is False
    assert qa["retirement_active"] is False
    assert len(qa["checks"]) == 14

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

    materialized = "\n".join(read(path) for path in (PROFILE, GATE, QA, REQUEST, STATE))
    assert '"default_workflow_active": true' not in materialized
    assert '"retirement_active": true' not in materialized
    assert '"active": true' not in read(PROFILE)
    assert "No file deletion" in contract
    assert "RETIRED_NON_AUTHORITATIVE" in contract
    for heading in (
        "Sealed candidate and two-phase gate protocol",
        "Atomic Git transaction and two-head mutation budget",
        "One-active-PR programme lease",
        "Required-check provenance and ruleset-health preflight",
        "One canonical required PR runtime",
    ):
        assert heading in contract
    assert "python-version: '3.11'" in workflow
    assert "Complete repository suite" not in workflow

    for token in ("ghp_", "github_pat_", "-----BEGIN PRIVATE KEY-----", "sk-proj_", "Bearer "):
        assert token not in materialized

    print("DA-G6 operator gate validation PASS; five controls present and proposal inactive")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
