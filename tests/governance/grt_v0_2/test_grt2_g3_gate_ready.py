from __future__ import annotations

import json
from pathlib import Path

from ovc.programme_genesis.grt_v0_2.debt import B0_MEMBER_COUNT, B0_MEMBERSHIP_SHA256, validate_debt_floor
from ovc.programme_genesis.grt_v0_2.serialization import canonical_sha256
from ovc.development.skills.vit_core import DependencyFrontier, IntegrationAuthorityManifest


ROOT = Path(__file__).resolve().parents[3]
G3 = ROOT / "docs/programmes/grt-v0-2/g3"
STATE = ROOT / "registries/implementation/grt_v0_2"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def assert_logical_hash(record: dict) -> None:
    payload = dict(record)
    actual = payload.pop("logical_sha256")
    assert actual == canonical_sha256(payload)


def test_consolidated_g3_packet_stops_at_operator_boundary() -> None:
    gate = load(G3 / "GRT2_G3_GATE_READY_DECISION_PACKET.json")
    qa = load(G3 / "GRT2_G3_GATE_READY_QA_PACKET.json")
    transition = load(G3 / "GRT2_G3_ENFORCEMENT_TRANSITION_PROPOSAL.json")
    assert_logical_hash(gate)
    assert_logical_hash(qa)
    assert_logical_hash(transition)
    assert gate["status"] == "GATE_READY_OPERATOR_REQUIRED"
    assert gate["recommended_decision"] == "PASS"
    assert gate["allowed_operator_decisions"] == ["PASS", "DEFER", "BLOCK", "QUARANTINE", "SUPERSEDE"]
    assert gate["operator_decision"] is None
    assert gate["authority_consumed"] == "NONE"
    assert gate["stop_condition"] == "STOP_FOR_OPERATOR_GRT2_G3_DECISION"
    assert gate["b0_lineage_and_provenance"]["member_count"] == B0_MEMBER_COUNT
    assert gate["b0_lineage_and_provenance"]["membership_sha256"] == B0_MEMBERSHIP_SHA256
    assert gate["b0_lineage_and_provenance"]["unresolved_lineage_count"] == 0
    assert gate["b0_lineage_and_provenance"]["transition_new_debt_count"] == 0
    assert qa["qa_recommendation"] == "PASS"
    assert qa["unresolved_issues"] == []
    assert transition["status"] == "PROPOSED_INACTIVE_OPERATOR_RESERVED"
    assert transition["authority_effect"] == "NONE_PROPOSAL_ONLY"


def test_candidate_floor_is_complete_valid_and_inactive() -> None:
    floor = load(G3 / "GRT2_G3_PROPOSED_DEBT_FLOOR_GENERATION_0.json")
    gate = load(G3 / "GRT2_G3_GATE_READY_DECISION_PACKET.json")
    state = load(STATE / "OVC_GRT2_STATE_v0_15.json")
    validate_debt_floor(floor)
    assert floor["generation"] == 0
    assert len(floor["open_grandfathered_findings"]) == 1628
    assert gate["proposed_debt_floor_generation_0"]["floor_hash"] == floor["floor_hash"]
    assert state["debt_floor_generation"] is None
    assert state["candidate_debt_floor_generation"] == 0
    assert state["candidate_debt_floor_hash"] == floor["floor_hash"]
    assert state["active_enforcement"] == "LIMITED_NEW_ARTIFACT_ENFORCEMENT"
    assert state["constitution_status"] == "PROPOSED_UNADMITTED"
    assert state["operator_decision_required"] is True


def test_historical_gate_ready_state_preserves_no_authority() -> None:
    state = load(STATE / "OVC_GRT2_STATE_v0_15.json")
    assert state["status"] == "GATE_READY_OPERATOR_REQUIRED"
    assert state["authority_effect"] == "NONE_GATE_PREPARATION_ONLY"
    assert_logical_hash(state)


def test_readiness_completion_preserves_exact_tree_and_no_authority() -> None:
    receipt = load(G3 / "GRT2_G3_READINESS_COMPLETION_RECEIPT.json")
    assert_logical_hash(receipt)
    physical = receipt["physical_materialisation"]
    assert physical["exact_tree_equality"] is True
    assert physical["merge_tree"] == physical["qualified_tree"]
    assert receipt["authority_effect"] == "NONE_READINESS_COMPLETION_ONLY"
    assert receipt["constitution_status"] == "PROPOSED_UNADMITTED"
    assert receipt["debt_floor_generation"] is None
    assert receipt["g3_authority"] == "NOT_CONSUMED"
    assert len(physical["post_merge_proof_id"]) == 64
    assert set(physical["receipt_ids"]) == {
        "attachment_id",
        "completion_receipt_id",
        "development_latency_receipt_id",
        "materialisation_receipt_id",
    }
    assert all(len(value) == 64 for value in physical["receipt_ids"].values())


def test_gate_ready_integration_manifests_are_rebuilt_and_authority_inert() -> None:
    gate = load(G3 / "GRT2_G3_GATE_READY_DECISION_PACKET.json")
    authority_binding = load(G3 / "GRT2_G3_GATE_READY_AUTHORITY_MANIFEST.json")
    frontier_binding = load(G3 / "GRT2_G3_GATE_READY_DEPENDENCY_FRONTIER.json")
    authority = IntegrationAuthorityManifest(**{
        **authority_binding["authority_manifest"],
        "authority_sources": tuple(authority_binding["authority_manifest"]["authority_sources"]),
        "reserved_boundaries": tuple(authority_binding["authority_manifest"]["reserved_boundaries"]),
    })
    frontier = DependencyFrontier(**{
        **frontier_binding["dependency_frontier"],
        "dependencies": tuple(frontier_binding["dependency_frontier"]["dependencies"]),
        "owner_bindings": tuple(frontier_binding["dependency_frontier"]["owner_bindings"]),
    })
    assert authority.logical_id == authority_binding["authority_manifest_id"]
    assert frontier.logical_id == frontier_binding["dependency_frontier_id"]
    assert authority.authority_class == "AUTO_EXECUTABLE"
    assert authority.authority_delta == "NONE_GATE_PREPARATION_ONLY"
    assert "GRT2-G3_OPERATOR_DECISION" in authority.reserved_boundaries
    integration = gate["gate_ready_integration_frontier"]
    assert integration["authority_manifest_id"] == authority.logical_id
    assert integration["dependency_frontier_id"] == frontier.logical_id
