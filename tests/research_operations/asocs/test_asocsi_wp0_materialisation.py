from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def _json(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def test_asocsi_wp0_hash_and_authority_bindings_are_consistent() -> None:
    decision = _json("docs/programmes/asocs-v0-1/implementation/ASOCSI_G0_OPERATOR_DECISION_v0_1.json")
    plan = _json("docs/programmes/asocs-v0-1/implementation/ASOCSI_PLAN_BINDING_v0_1.json")
    frontier = _json("registries/research_operations/asocs/ASOCSI_AUTHORITY_FRONTIER_v0_1.json")
    binding = _json("docs/programmes/asocs-v0-1/implementation/wp0/ASOCSI_WP0_CURRENTNESS_BINDING_v0_1.json")

    assert decision["decision"] == "PASS"
    assert decision["ratified_plan_sha256"] == plan["plan_artifacts"]["revised_1"]["sha256"]
    assert decision["ratified_plan_sha256"] == binding["governing_artifacts"]["implementation_plan_revised_1_sha256"]
    assert decision["governing_design_sha256"] == binding["governing_artifacts"]["design_sha256"]
    assert decision["accepted_pressure_test_sha256"] == binding["governing_artifacts"]["accepted_plan_pressure_test_sha256"]
    assert decision["bound_audit_population"]["sha256"] == binding["governing_artifacts"]["source_csv_sha256"]
    assert frontier["current_authority"]["bounded_repository_implementation"] == "AUTHORIZED_ASOCSI_WP0_THROUGH_WP9_AND_WP10_ONLY"
    assert frontier["source_population"]["active_provider"] is False
    assert frontier["source_population"]["research_role"] == "ASOCS_AUDIT_OUT_OF_ROLE_H1_2026"


def test_asocsi_wp0_resolves_current_active_owners_without_transitive_authority() -> None:
    binding = _json("docs/programmes/asocs-v0-1/implementation/wp0/ASOCSI_WP0_CURRENTNESS_BINDING_v0_1.json")
    c2 = _json("registries/opt_b/c2/vnext/C2_VNEXT_ACTIVE_RUNTIME_AUTHORITY_v0_1.json")
    c2e = _json("registries/authority/C2E_ACTIVE_ENGINE_AUTHORITY_v0_1.json")
    context = _json("registries/implementation/occurrence_context/OCCURRENCE_CONTEXT_ACTIVE_FOUNDATION_AUTHORITY_v0_1.json")
    research_ops = _json("registries/research_operations/ACTIVE_FOUNDATION_AUTHORITY_v0_1.json")
    active_pointer = _json("registries/governance/active_stack/CURRENT_ACTIVE_STACK_POINTER.json")
    c1_text = (ROOT / "registries/opt_b/c1/C1_ACTIVE_SELECTORS.yaml").read_text(encoding="utf-8")

    assert active_pointer["status"] == "COMPLETED"
    assert "selector_set_id: SELECTOR.OPT-B.C1.ROLESET.v0.2" in c1_text
    assert "validation_consumption: LOCKED_UNCONSUMED" in c1_text
    assert c2["authority_id"] == binding["owner_currentness"]["c2_vnext"]["authority_id"]
    assert c2["candidate_family_rule_promotion"] == "NONE"
    assert c2e["active_boundary_pack_id"] == binding["owner_currentness"]["c2e"]["boundary_pack_id"]
    assert context["structural_identity_mutation"] == "DENIED"
    assert research_ops["state"] == binding["owner_currentness"]["research_operations"]["state"]
    assert all(value == "NONE" for value in binding["non_transitivity"].values())


def test_asocsi_wp0_state_points_only_to_wp1_and_starts_no_runtime() -> None:
    state = _json("records/research_operations/asocs/ASOCSI_PROGRAMME_STATE_v0_2_WP0.json")
    pointer = _json("registries/research_operations/asocs/CURRENT_ASOCSI_STATE_POINTER.json")
    qa = _json("docs/programmes/asocs-v0-1/implementation/wp0/ASOCSI_WP0_QA_PACKET_v0_1.json")
    delegated = _json("docs/programmes/asocs-v0-1/implementation/wp0/ASOCSI_G0_MAT_DELEGATED_DECISION_v0_1.json")

    assert state["status"] == "COMPLETED"
    assert state["runtime_implementation_started"] is False
    assert state["next_packet"] == "ASOCSI-WP1"
    current_state = pointer["current_state"]
    assert current_state.startswith("records/research_operations/asocs/ASOCSI_PROGRAMME_STATE_")
    assert (ROOT / current_state).is_file()
    assert pointer["next_packet"] in {"ASOCSI-WP1", "ASOCSI-WP2"}
    assert qa["qa_recommendation"] == "PASS_DELEGATED_ASOCSI_G0_MAT"
    assert qa["blocking_findings"] == []
    assert delegated["decision"] == "PASS"
    assert delegated["authority_delta"] == "NONE"
