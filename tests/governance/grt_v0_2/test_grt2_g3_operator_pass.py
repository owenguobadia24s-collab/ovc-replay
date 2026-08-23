from __future__ import annotations

import json
from pathlib import Path

from ovc.development.skills.vit_core import DependencyFrontier, IntegrationAuthorityManifest
from ovc.programme_genesis.grt_v0_2.debt import validate_debt_floor
from ovc.programme_genesis.grt_v0_2.serialization import canonical_sha256

ROOT = Path(__file__).resolve().parents[3]
G3 = ROOT / "docs/programmes/grt-v0-2/g3"
STATE = ROOT / "registries/implementation/grt_v0_2"
AUTH = ROOT / "registries/authority"
GOV = ROOT / "registries/governance/grt_v0_2"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def assert_logical_hash(record: dict) -> None:
    payload = dict(record)
    actual = payload.pop("logical_sha256")
    assert actual == canonical_sha256(payload)


def test_operator_pass_is_exact_and_source_bound() -> None:
    decision = load(G3 / "GRT2_G3_OPERATOR_DECISION.json")
    assert_logical_hash(decision)
    assert decision["gate_id"] == "GRT2-G3"
    assert decision["decision"] == "PASS"
    assert decision["decision_class"] == "OPERATOR_REQUIRED_AUTHORITY_CHANGE"
    assert decision["operator_instruction"] == "OVC APPROVE GRT2-G3"
    assert decision["gate_ready_merge_commit"] == "0287c81400c3a2536096b2a1691d5486096e87b0"
    assert decision["gate_ready_merge_tree"] == "6818abb770c8878af286b011448304c6cc737ff6"
    delta = decision["approved_authority_delta"]
    assert delta["repository_constitution"]["canonical_hash"] == "cac9fc5f0e31db08c4c37153c92a214fcc482414421f34d74c594faec65a71b0"
    assert delta["debt_floor"]["floor_hash"] == "f008cbad6bbb891b18f615aa91f9981fbf71ec874972630d8c6eb38ae1642ba9"
    assert delta["enforcement"]["required_assurance"] == "GRT-EXACT"


def test_active_generation_zero_is_exact_approved_floor_bytes() -> None:
    proposed = load(G3 / "GRT2_G3_PROPOSED_DEBT_FLOOR_GENERATION_0.json")
    active = load(GOV / "debt_floors/GRT_DEBT_FLOOR_G0.json")
    pointer = load(GOV / "GRT_DEBT_FLOOR_CURRENT.json")
    assert active == proposed
    validate_debt_floor(active)
    assert active["generation"] == 0
    assert len(active["open_grandfathered_findings"]) == 1628
    assert active["floor_hash"] == "f008cbad6bbb891b18f615aa91f9981fbf71ec874972630d8c6eb38ae1642ba9"
    assert active["constitution_hash"] == "cac9fc5f0e31db08c4c37153c92a214fcc482414421f34d74c594faec65a71b0"
    assert_logical_hash(pointer)
    assert pointer["generation"] == 0
    assert pointer["floor_hash"] == active["floor_hash"]
    assert pointer["definition"] == "registries/governance/grt_v0_2/debt_floors/GRT_DEBT_FLOOR_G0.json"


def test_activation_authority_consumes_only_operator_approved_g3_delta() -> None:
    authority = load(AUTH / "GRT2_ACTIVE_ENFORCEMENT_AUTHORITY_v0_2.json")
    assert_logical_hash(authority)
    assert authority["authority_status"] == "ACTIVE_ON_MAIN_MATERIALISATION"
    assert authority["enforcement_mode"] == "FULL_GRT_EXACT"
    assert authority["required_integration_assurance"] == "GRT-EXACT"
    assert authority["constitution_status"] == "ACTIVE"
    assert authority["constitution_hash"] == "cac9fc5f0e31db08c4c37153c92a214fcc482414421f34d74c594faec65a71b0"
    assert authority["rule_bundle_hash"] == "7d6c38a3a018f257d0a05f6cfaf0a3082b42f825c2c36335d64544432a960979"
    assert authority["debt_floor_generation"] == 0
    assert authority["no_new_hygiene_debt_required"] is True
    assert authority["rollback_requires_operator_decision"] is True
    assert "Programme Genesis adoption authority" in authority["authority_exclusions"]
    assert "constitutional semantic amendment" in authority["authority_exclusions"]


def test_activation_state_preserves_preg3_pointer_until_wp4() -> None:
    prior = load(STATE / "OVC_GRT2_STATE_v0_15.json")
    activation = load(STATE / "OVC_GRT2_STATE_v0_16.json")
    pointer = load(STATE / "CURRENT_STATE_POINTER.json")
    assert_logical_hash(activation)
    assert prior["status"] == "GATE_READY_OPERATOR_REQUIRED"
    assert prior["operator_decision_required"] is True
    assert pointer["current_state"] == "registries/implementation/grt_v0_2/OVC_GRT2_STATE_v0_15.json"
    assert pointer["status"] == "GATE_READY_OPERATOR_REQUIRED"
    assert activation["operator_decision"] == "PASS"
    assert activation["operator_decision_required"] is False
    assert activation["status"] == "APPROVED_PENDING_MAIN_MATERIALISATION"
    assert activation["next_packet"] == "GRT2-WP4"
    assert activation["next_gate"] == "GRT2-G4"
    assert "PRE_G3_POINTER_INTENTIONALLY_PRESERVED" in activation["current_projection_status"]


def test_activation_revalidation_and_fail_closed_rollback_are_explicit() -> None:
    revalidation = load(G3 / "GRT2_G3_ACTIVATION_REVALIDATION.json")
    transaction = load(G3 / "GRT2_G3_ACTIVATION_TRANSACTION.json")
    rollback = load(G3 / "GRT2_G3_ROLLBACK_BUNDLE.json")
    stabilization = load(G3 / "GRT2_POST_G3_STABILIZATION_LEDGER.json")
    for record in (revalidation, transaction, rollback, stabilization):
        assert_logical_hash(record)
    assert revalidation["main_moved_after_gate_ready"] is True
    assert revalidation["activation_predecessor_commit"] == "4890bdab207923b1da86cd2c280a12be473a7832"
    assert revalidation["activation_predecessor_tree"] == "d4331e65fb0156bfe7f8a13cac5cc541922acb88"
    assert revalidation["status"] == "PENDING_CI_EXACT_REVALIDATION"
    assert transaction["required_pre_merge_proof"]["profile"] == "GRT-EXACT"
    assert transaction["required_pre_merge_proof"]["base_snapshot_must_equal_approved_floor"] is True
    assert transaction["required_pre_merge_proof"]["candidate_snapshot_must_equal_generation_0_floor"] is True
    assert transaction["current_state_projection"]["pre_g3_pointer_preserved"] is True
    assert rollback["same_constitution_qualified_rollback_runtime"] is None
    assert rollback["fail_closed_mode"] == "BLOCK_NORMAL_INTEGRATIONS"
    assert "force-push" in rollback["forbidden"]
    assert stabilization["duration_calendar_days"] == 30
    assert stabilization["status"] == "STARTS_ON_G3_ACTIVATION_MERGE"


def test_activation_integration_binding_consumes_operator_authority_without_expansion() -> None:
    auth_binding = load(G3 / "GRT2_G3_ACTIVATION_AUTHORITY_MANIFEST.json")
    dep_binding = load(G3 / "GRT2_G3_ACTIVATION_DEPENDENCY_FRONTIER.json")
    auth = IntegrationAuthorityManifest(**{
        **auth_binding["authority_manifest"],
        "authority_sources": tuple(auth_binding["authority_manifest"]["authority_sources"]),
        "reserved_boundaries": tuple(auth_binding["authority_manifest"]["reserved_boundaries"]),
    })
    dep = DependencyFrontier(**{
        **dep_binding["dependency_frontier"],
        "dependencies": tuple(dep_binding["dependency_frontier"]["dependencies"]),
        "owner_bindings": tuple(dep_binding["dependency_frontier"]["owner_bindings"]),
    })
    assert auth.logical_id == auth_binding["authority_manifest_id"]
    assert dep.logical_id == dep_binding["dependency_frontier_id"]
    assert auth.authority_class == "AUTO_EXECUTABLE"
    assert auth.authority_delta == "NONE"
    assert "CONSTITUTION_SEMANTIC_AMENDMENT" in auth.reserved_boundaries
    assert dep.predecessor_requirement == "PHYSICAL_MATERIALISATION_REQUIRED"


def test_required_grt_exact_is_inside_existing_serialized_final_integration_lane() -> None:
    workflow = (ROOT / ".github/workflows/ovc-tiered-tests.yml").read_text(encoding="utf-8")
    assert "group: ovc-main-integration-lane-v1" in workflow
    assert "Acquire one-writer lease and late-bind current physical main" in workflow
    assert "Run required GRT-EXACT against the exact late-bound integration tree" in workflow
    assert "scripts/governance/grt_v0_2/grt_exact.py" in workflow
    assert "Run mandatory SIQ/PDC exact-final assurance inside lease" in workflow
    assert "Run lightweight GRT integration readiness" in workflow
    assert "scripts/governance/grt_v0_2/grt_integration_readiness.py" in workflow
    assert "Bind exact late-placement IntegrationAdmissionReceipt" in workflow
