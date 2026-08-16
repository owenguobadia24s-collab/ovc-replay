from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]


def _read(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def test_historical_grun_readiness_v02_remains_preserved_as_blocked_evidence() -> None:
    readiness = _read("docs/releases/c2p-persistent-structural-objects-v0-2/c2p2-rs0/C2P2_RS0_GRUN_READINESS_v0_2.json")
    assert readiness["status"] == "BLOCKED"
    assert set(readiness["blockers"]) == {"RS0_NUMERIC_RESOURCE_BUDGET_NOT_REPRODUCIBLY_MEASURED", "RS0_EXTERNAL_ARTIFACT_ROOT_NOT_BOUND"}


def test_grun_readiness_v03_clears_only_the_two_mechanical_blockers() -> None:
    readiness = _read("docs/releases/c2p-persistent-structural-objects-v0-2/c2p2-rs0/C2P2_RS0_GRUN_READINESS_v0_3.json")
    assert readiness["gate_id"] == "C2P2-RS0-GRUN"
    assert readiness["status"] == "GATE_READY"
    assert readiness["blockers"] == []
    assert readiness["operator_gate_status"] == "READY_FOR_OPERATOR_DECISION"
    assert readiness["recommended_decision"] == "PASS"
    assert readiness["capacity_evidence"]["status"] == "MEASURED_AND_FROZEN"
    assert readiness["capacity_evidence"]["peak_memory_limit_bytes"] == 1160593408
    assert readiness["capacity_evidence"]["external_storage_limit_bytes"] == 6411935744
    assert readiness["external_artifact_root"]["status"] == "EXACT_BOUND"
    assert readiness["authority_firewall"]["active_object_pack"] is None
    assert readiness["authority_firewall"]["validation"] == "LOCKED_UNCONSUMED"


def test_grun_source_snapshot_binds_exact_releases_candidates_and_current_authority() -> None:
    snapshot = _read("docs/releases/c2p-persistent-structural-objects-v0-2/c2p2-rs0/C2P2_RS0_GRUN_SOURCE_AUTHORITY_SNAPSHOT_v0_1.json")
    assert snapshot["upstream_bindings"]["opt_a"]["manifest_sha256"] == "0cbcafa9421449574b61bfeec24f634de99cbbbc6e7a53d09ace8f702182ab8c"
    assert snapshot["upstream_bindings"]["c1"]["manifest_sha256"] == "c9b2eaa826419a510504c016d99072c6015c337a5c2ef435252d5f6ff1db93bf"
    assert snapshot["upstream_bindings"]["c2"]["package_sha256"] == "150de1997be8801baa59db6d0fe98b11cb21a6b70525b908537aeb31bfd00cc3"
    assert snapshot["upstream_bindings"]["c2e"]["boundary_pack_sha256"] == "043c628a3a29372ae478026db307d0d8b2347fcbbc7b06dbb1a3cc345c86e313"
    assert snapshot["candidate_set"]["selection_state"] == "NONE_SELECTED"
    assert snapshot["ec1_authority"]["greal_gate"] == "PASS_BOUNDED"
    assert snapshot["ec1_authority"]["f0_a_execution"] == "HOLD"
    assert snapshot["firewall"]["c2p_real_source_run"] == "DENIED_UNTIL_C2P2_RS0_GRUN_PASS"


def test_grun_packet_is_operator_required_and_cannot_self_activate() -> None:
    packet = _read("docs/releases/c2p-persistent-structural-objects-v0-2/c2p2-rs0/C2P2_RS0_RUN_AUTHORITY_PACKET_v0_2.json")
    state = _read("registries/implementation/c2p_v0_2/C2P2_RS0_STATE_v0_1.json")
    assert packet["decision"] == "PENDING_OPERATOR"
    assert packet["decision_authority"] == "OPERATOR_REQUIRED"
    assert packet["recommended_decision"] == "PASS"
    assert packet["proposed_delta_if_pass"]["real_source_run"] == "ONE_BOUNDED_PREREGISTERED_RS0_SHADOW_RUN"
    assert packet["proposed_delta_if_pass"]["active_object_pack"] is None
    assert packet["proposed_delta_if_pass"]["c2p_activation_authority"] == "NONE"
    assert packet["current_authority"]["validation"] == "LOCKED_UNCONSUMED"
    assert state["status"] == "GATE_READY"
    assert state["authority"]["rs0_real_source_run"] == "DENIED_UNTIL_OPERATOR_GRUN_PASS"
    assert state["mandatory_stop"] == "C2P2-RS0-GRUN_OPERATOR_DECISION"


def test_f0_a_hold_explicitly_allows_grun_readiness_but_not_joint_launch() -> None:
    hold = _read("docs/releases/ec1-dmrp-conformance-v0-1/f0-a/EC1_F0_A_OPERATOR_HOLD_20260816_v0_1.json")
    assert hold["status"] == "HOLD"
    assert hold["c2p2_rs0_grun_readiness"] == "MAY_PROCEED_TO_ITS_OWN_MANDATORY_STOP"
    assert hold["joint_launch"] == "DENIED_WHILE_F0_A_HOLD_ACTIVE"


def test_shadow_result_manifest_schema_preserves_sidecar_firewall() -> None:
    schema = _read("schemas/research_operations/ec1/ec1_c2p_shadow_result_manifest_v0_1.schema.json")
    props = schema["properties"]
    assert props["ec1_scientific_effect"]["const"] == "NONE"
    assert "sealed_state" in schema["required"]
    assert "object_pack_candidate_logical_hash" in schema["required"]
    assert props["source_population"]["properties"]["research_role"]["const"] == "DISCOVERY_SHADOW_ONLY"
