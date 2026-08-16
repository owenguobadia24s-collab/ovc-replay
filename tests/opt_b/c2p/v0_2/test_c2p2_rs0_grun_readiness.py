from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]


def _read(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def test_c2p2_rs0_grun_readiness_fails_closed_until_measured_budget_and_artifact_root() -> None:
    readiness = _read(
        "docs/releases/c2p-persistent-structural-objects-v0-2/c2p2-rs0/"
        "C2P2_RS0_GRUN_READINESS_v0_2.json"
    )
    assert readiness["gate_id"] == "C2P2-RS0-GRUN"
    assert readiness["status"] == "BLOCKED"
    assert readiness["operator_gate_status"] == "NOT_READY_FOR_PASS_DECISION"
    assert readiness["recommended_decision"] == "BLOCK"
    assert set(readiness["blockers"]) == {
        "RS0_NUMERIC_RESOURCE_BUDGET_NOT_REPRODUCIBLY_MEASURED",
        "RS0_EXTERNAL_ARTIFACT_ROOT_NOT_BOUND",
    }
    assert readiness["capacity_evidence"]["rs0_numeric_budget_status"] == "INCOMPLETE"
    assert readiness["external_artifact_root"]["status"] == "UNRESOLVED_FOR_RS0_RUN_GENERATION"
    assert readiness["authority_firewall"]["active_object_pack"] is None
    assert readiness["authority_firewall"]["ec1_scientific_authority_effect"] == "NONE"
    assert readiness["authority_firewall"]["validation"] == "LOCKED_UNCONSUMED"


def test_exact_current_upstream_bindings_are_frozen_in_readiness_record() -> None:
    readiness = _read(
        "docs/releases/c2p-persistent-structural-objects-v0-2/c2p2-rs0/"
        "C2P2_RS0_GRUN_READINESS_v0_2.json"
    )
    bindings = readiness["resolved_upstream_bindings"]
    assert bindings["opt_a"]["manifest_sha256"] == "0cbcafa9421449574b61bfeec24f634de99cbbbc6e7a53d09ace8f702182ab8c"
    assert bindings["c1"]["manifest_sha256"] == "c9b2eaa826419a510504c016d99072c6015c337a5c2ef435252d5f6ff1db93bf"
    assert bindings["c2"]["package_sha256"] == "150de1997be8801baa59db6d0fe98b11cb21a6b70525b908537aeb31bfd00cc3"
    assert bindings["c2e"]["boundary_pack_logical_sha256"] == "043c628a3a29372ae478026db307d0d8b2347fcbbc7b06dbb1a3cc345c86e313"
    assert bindings["occurrence_context"]["authority_blob_sha"] == "c6714b42fa378f0f533fdf2caf89c3ed4bec4942"


def test_f0_a_operator_hold_is_materialized_without_revoking_greal_authority() -> None:
    hold = _read("docs/releases/ec1-dmrp-conformance-v0-1/f0-a/EC1_F0_A_OPERATOR_HOLD_20260816_v0_1.json")
    pointer = _read("registries/implementation/ec1_dmrp_v0_1/CURRENT_STATE_POINTER.json")
    greal = _read("registries/implementation/ec1_dmrp_v0_1/DMRPI_GREAL_EC1_STATE.json")
    assert hold["status"] == "HOLD"
    assert hold["f0_a_execution"] == "DENIED_WHILE_HOLD_ACTIVE"
    assert hold["dmrpi_greal_ec1_authority"] == "PRESERVED_AUTHORISED_BOUNDED_NOT_REVOKED"
    assert pointer["status"] == "COMPLETED"
    assert pointer["last_merge_commit"] == "a26bc19d76ed3ebd3def43a23468404e976f84eb"
    assert pointer["execution_hold"]["packet_id"] == "F0-A"
    assert pointer["execution_hold"]["status"] == "HOLD"
    assert greal["status"] == "COMPLETED"
    assert greal["merge_commit"] == "a26bc19d76ed3ebd3def43a23468404e976f84eb"


def test_shadow_result_manifest_schema_preserves_sidecar_firewall() -> None:
    schema = _read("schemas/research_operations/ec1/ec1_c2p_shadow_result_manifest_v0_1.schema.json")
    props = schema["properties"]
    assert props["ec1_scientific_effect"]["const"] == "NONE"
    assert "sealed_state" in schema["required"]
    assert "object_pack_candidate_logical_hash" in schema["required"]
    assert props["source_population"]["properties"]["research_role"]["const"] == "DISCOVERY_SHADOW_ONLY"
