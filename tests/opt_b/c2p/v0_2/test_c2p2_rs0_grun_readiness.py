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


def test_grun_gate_ready_evidence_is_preserved_after_operator_pass() -> None:
    readiness = _read("docs/releases/c2p-persistent-structural-objects-v0-2/c2p2-rs0/C2P2_RS0_GRUN_READINESS_v0_3.json")
    assert readiness["status"] == "GATE_READY"
    assert readiness["blockers"] == []
    assert readiness["capacity_evidence"]["status"] == "MEASURED_AND_FROZEN"
    assert readiness["external_artifact_root"]["status"] == "EXACT_BOUND"
    assert readiness["authority_firewall"]["active_object_pack"] is None
    assert readiness["authority_firewall"]["validation"] == "LOCKED_UNCONSUMED"


def test_operator_pass_grants_exactly_one_shadow_run_and_no_activation() -> None:
    decision = _read("docs/releases/c2p-persistent-structural-objects-v0-2/c2p2-rs0/C2P2_RS0_GRUN_OPERATOR_DECISION_v0_1.json")
    authority = _read("registries/authority/C2P2_RS0_REAL_SOURCE_SHADOW_RUN_AUTHORITY_v0_1.json")
    packet = _read("docs/releases/c2p-persistent-structural-objects-v0-2/c2p2-rs0/C2P2_RS0_RUN_AUTHORITY_PACKET_v0_3.json")
    state = _read("registries/implementation/c2p_v0_2/C2P2_RS0_STATE_v0_1.json")
    assert decision["decision"] == "PASS"
    assert decision["operator_instruction"] == "OVC APPROVE C2P2-RS0-GRUN PASS"
    assert authority["execution_count_limit"] == 1
    assert authority["execution_count_consumed"] == 0
    assert authority["state"] == "AUTHORISED_NOT_STARTED"
    assert authority["non_transitive_denials"]["objectpack_selection"] == "NONE"
    assert authority["non_transitive_denials"]["c2p_activation"] == "NONE"
    assert authority["non_transitive_denials"]["validation"] == "LOCKED_UNCONSUMED"
    assert packet["decision"] == "PASS"
    assert packet["approved_authority"]["real_source_run"] == "ONE_BOUNDED_PREREGISTERED_RS0_SHADOW_RUN"
    assert packet["approved_authority"]["active_object_pack"] is None
    assert state["status"] == "GATE_READY"
    assert state["packet_id"] == "C2P2-RS0-EXECUTION"
    assert state["authority"]["rs0_real_source_run"] == "AUTHORISED_ONE_RUN_NOT_STARTED_BLOCKED_BEFORE_TOKEN_CONSUMPTION"
    assert state["authority"]["run_authority_consumed"] is False
    assert state["authority"]["run_count_remaining"] == 1
    assert state["mandatory_stop"] == "OPERATOR_AUTHORITY_REQUIRED_FOR_IDENTITY_DEFINING_OBJECTPACK_SEMANTICS"
    assert state["authority"]["active_object_pack"] is None
    assert state["selection_state"] == "COMPARATIVE_SET_ONLY_NO_WINNER"


def test_approval_currentness_review_accepts_only_non_material_main_advances() -> None:
    decision = _read("docs/releases/c2p-persistent-structural-objects-v0-2/c2p2-rs0/C2P2_RS0_GRUN_OPERATOR_DECISION_v0_1.json")
    snapshot = _read("docs/releases/c2p-persistent-structural-objects-v0-2/c2p2-rs0/C2P2_RS0_GRUN_SOURCE_AUTHORITY_SNAPSHOT_v0_1.json")
    currentness = decision["currentness_review"]
    assert currentness["result"] == "PASS_REUSE_GATE_READY_BINDINGS_AND_REANCHOR_PLACEMENT"
    assert currentness["grun_bound_source_authority_candidate_population_cutoff_environment_frozen_capacity_or_artifact_root_changed"] is False
    assert currentness["capacity_portability_review"]["effect"] == "WINDOWS_HOST_PORTABILITY_ONLY"
    assert snapshot["upstream_bindings"]["opt_a"]["manifest_sha256"] == "0cbcafa9421449574b61bfeec24f634de99cbbbc6e7a53d09ace8f702182ab8c"
    assert snapshot["upstream_bindings"]["c1"]["manifest_sha256"] == "c9b2eaa826419a510504c016d99072c6015c337a5c2ef435252d5f6ff1db93bf"
    assert snapshot["upstream_bindings"]["c2"]["package_sha256"] == "150de1997be8801baa59db6d0fe98b11cb21a6b70525b908537aeb31bfd00cc3"
    assert snapshot["upstream_bindings"]["c2e"]["boundary_pack_sha256"] == "043c628a3a29372ae478026db307d0d8b2347fcbbc7b06dbb1a3cc345c86e313"


def test_capacity_and_ec1_firewalls_remain_fail_closed_after_pass() -> None:
    authority = _read("registries/authority/C2P2_RS0_REAL_SOURCE_SHADOW_RUN_AUTHORITY_v0_1.json")
    hold = _read("docs/releases/ec1-dmrp-conformance-v0-1/f0-a/EC1_F0_A_OPERATOR_HOLD_20260816_v0_1.json")
    assert authority["capacity"]["peak_memory_limit_bytes"] == 1160593408
    assert authority["capacity"]["external_storage_limit_bytes"] == 6411935744
    assert authority["capacity"]["concurrency_limit"] == 1
    assert authority["capacity"]["capacity_exceeded"] == "FAIL_CLOSED_RETURN_TO_OPERATOR"
    assert authority["capacity"]["reduced_precision"] == "FORBIDDEN"
    assert authority["non_transitive_denials"]["ec1_candidate_defining_use"] == "FORBIDDEN"
    assert hold["status"] == "HOLD"
    assert hold["joint_launch"] == "DENIED_WHILE_F0_A_HOLD_ACTIVE"


def test_shadow_result_manifest_schema_preserves_sidecar_firewall() -> None:
    schema = _read("schemas/research_operations/ec1/ec1_c2p_shadow_result_manifest_v0_1.schema.json")
    props = schema["properties"]
    assert props["ec1_scientific_effect"]["const"] == "NONE"
    assert "sealed_state" in schema["required"]
    assert "object_pack_candidate_logical_hash" in schema["required"]
    assert props["source_population"]["properties"]["research_role"]["const"] == "DISCOVERY_SHADOW_ONLY"
