from __future__ import annotations

import json
from pathlib import Path

from ovc.development.identity import canonical_sha256
from ovc.development.skills.repository_assurance_continuity import (
    FULL_REFERENCE_REQUIRED,
    build_assurance_dependency_graph,
    build_delta_assurance_plan,
    build_mutation_impact_manifest,
    validate_repository_assurance_generation,
)


ROOT = Path(__file__).resolve().parents[2]
WP6 = ROOT / "docs/releases/development-skills-architecture-v0-3-vit/repository-assurance-continuity/wp6"
REGISTRY = ROOT / "registries/development/skills/REPOSITORY_ASSURANCE_CLAIM_REGISTRY_v0_1.json"
POLICY = ROOT / "registries/development/skills/REPOSITORY_ASSURANCE_CONTINUITY_POLICY_v0_1.json"
STATE = ROOT / "registries/implementation/dsai3v_cipr_rac/OVC_DSAI3V_CIPR_RAC_STATE_v0_2_SHADOW_QUALIFIED_PILOT_PENDING.json"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def assert_role_id(record: dict, field: str, role: str) -> None:
    logical = {key: value for key, value in record.items() if key != field}
    assert record[field] == canonical_sha256(logical, role=role)


def test_wp6_replays_real_planner_against_frozen_multi_lane_payloads() -> None:
    registry = load(REGISTRY)
    policy = load(POLICY)
    generation = load(WP6 / "DSAI3V_RAC_BOOTSTRAP_ASSURANCE_GENERATION_v0_1.json")
    evidence = load(WP6 / "DSAI3V_RAC_WP6_MEASURED_MULTI_LANE_SHADOW_EVIDENCE_v0_1.json")

    graph = build_assurance_dependency_graph(registry["claims"])
    assert graph["graph_id"] == registry["graph_id"] == evidence["claim_graph_id"]
    assert registry["blocking_path_eligible"] is False
    assert registry["completeness"] == "COARSE_CLAIM_FAMILIES_ONLY"
    assert policy["required_check_substitution_active"] is False
    assert policy["runner_cutover_active"] is False
    assert policy["blocking_path_substitution_active"] is False

    validated_generation = validate_repository_assurance_generation(generation)
    assert validated_generation["generation_id"] == evidence["bootstrap_generation_id"]
    assert len(validated_generation["passed_claim_ids"]) == 7

    for candidate in evidence["candidates"]:
        changed_tokens = [f"path:{path}" for path in candidate["changed_paths"]]
        impact = build_mutation_impact_manifest(
            programme_id=candidate["programme_id"],
            packet_id=candidate["packet_id"],
            payload_id=candidate["pip_id"],
            changed_tokens=changed_tokens,
            classified_tokens=changed_tokens,
        )
        assert impact["impact_manifest_id"] == candidate["impact_manifest_id"]
        assert impact["unclassified_tokens"] == []

        plan = build_delta_assurance_plan(
            base_generation=generation,
            graph=graph,
            impact_manifest=impact,
            policy=policy,
        )
        assert plan["plan_id"] == candidate["delta_plan_id"]
        assert plan["reference_required"] is True
        assert plan["reference_reasons"] == [
            "CLAIM:REPOSITORY::UNMAPPED_ASSURANCE_UNIVERSE"
        ]
        assert plan["summary"][FULL_REFERENCE_REQUIRED] == 7
        assert all(
            row["disposition"] == FULL_REFERENCE_REQUIRED
            for row in plan["claim_dispositions"]
        )
        assert candidate["planner"]["invalidation_radius"] == 1.0
        assert candidate["planner"]["inherited_claim_count"] == 0
        assert candidate["planner"]["reference_obligation_omitted"] is False
        assert candidate["canonical_reference"]["tests_conclusion"] == "SUCCESS"
        assert candidate["canonical_reference"]["tiered_conclusion"] == "SUCCESS"
        assert candidate["safety_classification"]["unsafe_omission_false_negative"] is False
        assert candidate["safety_classification"]["unexplained_semantic_mismatch"] is False

    aggregate = evidence["aggregate"]
    assert aggregate["candidate_count"] == 3
    assert aggregate["distinct_programme_count"] == 3
    assert aggregate["canonical_reference_pass_count"] == 3
    assert aggregate["unsafe_omission_false_negative_count"] == 0
    assert aggregate["unexplained_semantic_mismatch_count"] == 0
    assert aggregate["observed_claim_reuse_rate"] == 0.0
    assert aggregate["mean_invalidation_radius"] == 1.0
    assert aggregate["incremental_utility"] == "NOT_ESTABLISHED_COARSE_SENTINEL_FORCES_FULL_REFERENCE"
    assert aggregate["blocking_false_positive_rate"] == "NOT_IDENTIFIABLE_FROM_FULL_SUITE_PASS_ONLY"
    assert_role_id(evidence, "evidence_id", "OVC_RAC_WP6_MEASURED_SHADOW_EVIDENCE")


def test_wp6_g3_pass_is_shadow_only_and_pilot_remains_operator_reserved() -> None:
    authority = load(WP6 / "DSAI3V_RAC_WP6_AUTHORITY_MANIFEST_v0_1.json")
    frontier = load(WP6 / "DSAI3V_RAC_WP6_DEPENDENCY_FRONTIER_v0_1.json")
    g3 = load(WP6 / "DSAI3V_RAC_G3_SHADOW_QUALIFICATION_DECISION_v0_1.json")
    pilot = load(WP6 / "DSAI3V_RAC_DELTA_ASSURANCE_PILOT_GATE_PACKET_v0_1.json")
    implementation = load(WP6 / "DSAI3V_RAC_WP6_IMPLEMENTATION_PACKET_v0_1.json")
    state = load(STATE)

    assert_role_id(authority, "authority_manifest_id", "OVC_AUTHORITY_MANIFEST")
    assert_role_id(frontier, "dependency_frontier_id", "OVC_DEPENDENCY_FRONTIER")
    assert_role_id(g3, "decision_id", "OVC_RAC_GATE_DECISION")
    assert_role_id(pilot, "gate_packet_id", "OVC_OPERATOR_GATE_PACKET")
    assert_role_id(implementation, "implementation_packet_id", "OVC_IMPLEMENTATION_PACKET")

    assert g3["gate_class"] == "AUTO_RATIFIABLE"
    assert g3["decision"] == "PASS_SAFE_CONSERVATIVE_SHADOW"
    assert g3["criteria"] == {
        "all_frozen_candidates_final_reference_outcome": True,
        "blocking_path_eligibility_changed": False,
        "bootstrap_main_reference_pass": True,
        "required_check_substitution_active": False,
        "ruleset_mutation": False,
        "runner_cutover_active": False,
        "zero_unexplained_semantic_mismatch": True,
        "zero_unsafe_omission_false_negative": True,
    }
    assert g3["authority_effect"] == "NONE_AUTO_SHADOW_QUALIFICATION_ONLY"

    assert pilot["gate_id"] == "DSAI3V-RAC-G-DELTA-ASSURANCE-PILOT"
    assert pilot["gate_class"] == "OPERATOR_REQUIRED"
    assert pilot["status"] == "PENDING_OPERATOR_DECISION"
    assert pilot["recommended_decision"] == "DEFER"
    assert pilot["authority_effect"] == "NONE_GATE_PREPARATION_ONLY"

    assert implementation["blocking_path_substitution_active"] is False
    assert implementation["required_check_substitution_active"] is False
    assert implementation["runner_cutover_active"] is False
    assert implementation["operator_stop_gate"] == pilot["gate_id"]
    assert state["next_boundary"] == pilot["gate_id"]
    assert state["next_boundary_class"] == "OPERATOR_REQUIRED"
    assert state["pilot_recommendation"] == "DEFER"
    assert state["blocking_path_substitution_active"] is False
