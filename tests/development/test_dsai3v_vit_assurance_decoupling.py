from __future__ import annotations

import json
import unittest
from pathlib import Path

from ovc.development.head_churn import classify_main_head_movement
from ovc.development.skills.vit_assurance_decoupling import (
    AssuranceDecouplingError,
    PhysicalMainProtectionSnapshot,
    build_aa0_reuse_authorization,
    physical_main_writer_decision,
    validate_aa0_reuse_authorization,
)
from ovc.development.skills.vit_routing import build_vit_lineage_record

ROOT = Path(__file__).resolve().parents[2]
DEFAULT = ROOT / "registries/authority/DEFAULT_EXECUTION_SUBSTRATE.json"
AA_POLICY = ROOT / "registries/development/skills/VIT_ASSURANCE_DECOUPLING_POLICY_v0_1.json"
MAIN_POLICY = ROOT / "registries/development/skills/VIT_PHYSICAL_MAIN_EXCLUSIVITY_v0_1.json"
WORKFLOW = ROOT / ".github/workflows/tests.yml"


def lineage(*, base: str, result: str, blob: str = "a" * 40, generation: str = "GEN") -> dict:
    pip = {
        "schema_version": "packet-integration-payload/v0.1",
        "programme_id": "P",
        "packet_id": "WP1",
        "logical_changes": [{"op": "ADD", "path": "src/example.py", "blob_sha": blob, "mode": "100644"}],
        "authority_manifest_id": "1" * 64,
        "dependency_frontier_id": "2" * 64,
        "completion_transition": {"status": "COMPLETED"},
    }
    return build_vit_lineage_record(
        programme_id="P",
        packet_id="WP1",
        pip_identity_payload=pip,
        train_generation_id=generation,
        ordinal=0,
        predecessor_tree_sha=base,
        result_tree_sha=result,
        apply_profile="INTEGRATION_APPLY_PROFILE_REFERENCE_v0_1",
    )


def movement(classification_paths: list[str]) -> dict:
    footprint = {
        "schema": "ovc-parallel-development-dependency-footprint/v1",
        "programme_id": "P",
        "packet_id": "WP1",
        "plan_id": "PLAN",
        "baseline_main_sha": "3" * 40,
        "dependency_paths": ["contracts/example/**"],
        "semantic_authority_paths": ["registries/authority/example/**"],
        "shared_integration_paths": ["src/ovc/shared/**"],
        "candidate_owned_paths": ["src/example.py"],
        "identity_bindings": [],
        "external_identity_bindings": [],
    }
    return classify_main_head_movement(
        baseline_main_sha="3" * 40,
        current_main_sha="4" * 40,
        changed_main_paths=classification_paths,
        footprint=footprint,
        policy={"global_integration_patterns": [".github/workflows/**", "tests/**"]},
    )


def test_cross_generation_aa0_reuse_is_authorized_for_unchanged_pip_and_integration_movement() -> None:
    old = lineage(base="3" * 40, result="5" * 40, generation="G1")
    new = lineage(base="4" * 40, result="6" * 40, generation="G2")
    receipt = movement(["src/ovc/shared/unrelated.py"])
    record = build_aa0_reuse_authorization(
        previous_lineage=old,
        current_lineage=new,
        head_movement_receipt=receipt,
    )
    assert record["reuse_disposition"] == "PLACEMENT_ONLY_PIP_REUSE"
    assert record["payload_rebuild_required"] is False
    assert validate_aa0_reuse_authorization(record, current_lineage=new) == record["authorization_id"]


def test_semantic_head_movement_cannot_reuse_aa0() -> None:
    old = lineage(base="3" * 40, result="5" * 40, generation="G1")
    new = lineage(base="4" * 40, result="6" * 40, generation="G2")
    receipt = movement(["contracts/example/contract.md"])
    with unittest.TestCase().assertRaisesRegex(AssuranceDecouplingError, "NOT_REUSABLE"):
        build_aa0_reuse_authorization(
            previous_lineage=old,
            current_lineage=new,
            head_movement_receipt=receipt,
        )


def test_payload_change_cannot_reuse_aa0() -> None:
    old = lineage(base="3" * 40, result="5" * 40, blob="a" * 40, generation="G1")
    new = lineage(base="4" * 40, result="6" * 40, blob="b" * 40, generation="G2")
    with unittest.TestCase().assertRaisesRegex(AssuranceDecouplingError, "PIP_CHANGED"):
        build_aa0_reuse_authorization(
            previous_lineage=old,
            current_lineage=new,
            head_movement_receipt=movement(["docs/unrelated.json"]),
        )


def test_physical_main_protection_requires_no_bypass_and_vit_readiness() -> None:
    protection = PhysicalMainProtectionSnapshot(
        enforcement="active",
        required_status_checks=("OVC merge readiness",),
        allowed_merge_methods=("squash",),
        bypass_actor_count=0,
        pull_request_required=True,
        non_fast_forward_prohibited=True,
        deletion_prohibited=True,
    )
    protection.validate()
    bad = PhysicalMainProtectionSnapshot(
        enforcement="active",
        required_status_checks=("OVC merge readiness",),
        allowed_merge_methods=("squash",),
        bypass_actor_count=1,
        pull_request_required=True,
        non_fast_forward_prohibited=True,
        deletion_prohibited=True,
    )
    with unittest.TestCase().assertRaisesRegex(AssuranceDecouplingError, "BYPASS"):
        bad.validate()


def test_only_existing_vit_controller_through_siq_is_lawful_writer() -> None:
    protection = PhysicalMainProtectionSnapshot(
        enforcement="active",
        required_status_checks=("OVC merge readiness",),
        allowed_merge_methods=("squash",),
        bypass_actor_count=0,
        pull_request_required=True,
        non_fast_forward_prohibited=True,
        deletion_prohibited=True,
    )
    assert physical_main_writer_decision(
        writer_identity="DSAI_VIT_PHYSICAL_CONTROLLER",
        physical_gateway="DSAI_SIQ_EXISTING_SERIALIZED_GATEWAY",
        vit_lineage_valid=True,
        merge_readiness_pass=True,
        protection=protection,
    ) == "ALLOW_EXISTING_VIT_SIQ_MATERIALISATION_PATH"
    assert physical_main_writer_decision(
        writer_identity="PACKET_DIRECT_WRITER",
        physical_gateway="DSAI_SIQ_EXISTING_SERIALIZED_GATEWAY",
        vit_lineage_valid=True,
        merge_readiness_pass=True,
        protection=protection,
    ) == "DENY_NON_VIT_MAIN_WRITER"


def test_default_substrate_binds_assurance_decoupling_and_physical_exclusivity() -> None:
    default = json.loads(DEFAULT.read_text(encoding="utf-8"))
    aa = json.loads(AA_POLICY.read_text(encoding="utf-8"))
    main = json.loads(MAIN_POLICY.read_text(encoding="utf-8"))
    assert default["assurance_decoupling"]["policy"].endswith("VIT_ASSURANCE_DECOUPLING_POLICY_v0_1.json")
    assert default["assurance_decoupling"]["placement_only_main_movement_full_aa0_rerun"] is False
    assert default["physical_main_exclusivity"]["exclusive_writer_identity"] == "DSAI_VIT_PHYSICAL_CONTROLLER"
    assert default["physical_main_exclusivity"]["required_ruleset_id"] == 20229411
    assert aa["status"] == "ACTIVE_ON_MATERIALISATION"
    assert main["github_ruleset"]["bypass_actor_count"] == 0
    assert main["github_ruleset"]["required_status_checks"] == ["OVC merge readiness"]


def test_ci_uses_pip_bound_aa0_cache_and_live_ruleset_preflight() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")
    # G5 PASS adds one read-only assurance-planning restore; the three established
    # AA0 execution surfaces remain the only cache writers.
    assert text.count("actions/cache/restore@v4") == 4
    assert text.count("actions/cache/save@v4") == 3
    assert "VIT-AA0-Reuse-B64" not in text  # marker parsing belongs to the Python preflight
    assert "vit_assurance_preflight.py" in text
    assert text.count("GITHUB_TOKEN: ${{ github.token }}") >= 2
    assert "PLACEMENT_ONLY_PIP_REUSE" in text
    assert "EXACT_GENERATION_REUSE" in text
    assert "OVC_PHYSICAL_MAIN_EXCLUSIVITY=PASS" in text
    assert "OVC merge readiness" in text
    assert "rulesets/{ruleset_id}" in text
    assert "bypass.length !== 0" in text
