from __future__ import annotations

import json
import unittest
from pathlib import Path

from ovc.development.skills.repository_assurance_continuity import (
    ASSURANCE_MODEL_DIVERGENCE,
    FULL_REFERENCE_REQUIRED,
    INHERIT_VALID,
    PASS,
    PLACEMENT_ONLY,
    QUARANTINED,
    RERUN_REQUIRED,
    WIDE_RERUN_REQUIRED,
    RepositoryAssuranceError,
    advance_repository_assurance_generation,
    build_assurance_claim_spec,
    build_assurance_dependency_graph,
    build_candidate_assurance_certificate,
    build_delta_assurance_plan,
    build_mutation_impact_manifest,
    build_reference_reconciliation_receipt,
    build_repository_assurance_generation,
    main_movement_assurance_disposition,
    validate_assurance_claim_spec,
    validate_assurance_dependency_graph,
    validate_candidate_assurance_certificate,
    validate_repository_assurance_generation,
)

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = (
    ROOT
    / "fixtures/development/repository_assurance_continuity/RAC_SYNTHETIC_TRUTH_WORLDS_v0_1.json"
)
POLICY_PATH = (
    ROOT
    / "registries/development/skills/REPOSITORY_ASSURANCE_CONTINUITY_POLICY_v0_1.json"
)
CLAIM_REGISTRY_PATH = (
    ROOT
    / "registries/development/skills/REPOSITORY_ASSURANCE_CLAIM_REGISTRY_v0_1.json"
)
SCHEMA_PATH = (
    ROOT
    / "schemas/development/skills/repository_assurance_continuity_v0_1.schema.json"
)
CONTRACT_PATH = (
    ROOT
    / "contracts/development/v0_5/OVC_DSAI3V_CIPR_REPOSITORY_ASSURANCE_CONTINUITY_AMENDMENT_v0_1.md"
)
PLAN_PATH = (
    ROOT
    / "docs/plans/development/OVC_DSAI3V_CIPR_REPOSITORY_ASSURANCE_CONTINUITY_IMPLEMENTATION_PLAN_v0_1.md"
)
CIPR_CURRENT = ROOT / "registries/implementation/ci_performance/CURRENT_STATE_POINTER.json"
DEFAULT_SUBSTRATE = ROOT / "registries/authority/DEFAULT_EXECUTION_SUBSTRATE.json"


def _claim_from_fixture(row: dict) -> dict:
    return build_assurance_claim_spec(
        claim_id=row["claim_id"],
        claim_class=row["claim_class"],
        dependencies=row["dependencies"],
        harness_id=row["harness_id"],
        execution_profile=row["execution_profile"],
        wide_rerun=row["wide_rerun"],
        unbounded=row["unbounded"],
        reference_only=row["reference_only"],
    )


def _fixture_state() -> tuple[dict, dict, dict]:
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    claims = [_claim_from_fixture(row) for row in fixture["claims"]]
    graph = build_assurance_dependency_graph(claims)
    base = build_repository_assurance_generation(
        repository_tree_sha=fixture["base"]["repository_tree_sha"],
        graph_id=graph["graph_id"],
        policy_id=fixture["policy"]["policy_id"],
        harness_generation_id="HARNESS-v1",
        passed_claim_ids=fixture["base"]["passed_claim_ids"],
        not_evaluable_claim_ids=fixture["base"]["not_evaluable_claim_ids"],
        quarantined_claim_ids=fixture["base"]["quarantined_claim_ids"],
    )
    return fixture, graph, base


def _scenario(fixture: dict, scenario_id: str) -> dict:
    return next(row for row in fixture["scenarios"] if row["scenario_id"] == scenario_id)


def _plan_for(fixture: dict, graph: dict, base: dict, scenario_id: str) -> dict:
    scenario = _scenario(fixture, scenario_id)
    impact = build_mutation_impact_manifest(
        programme_id="RAC-SYNTHETIC",
        packet_id=scenario_id,
        payload_id="f" * 64,
        changed_tokens=scenario["changed_tokens"],
        classified_tokens=scenario.get("classified_tokens", scenario["changed_tokens"]),
    )
    return build_delta_assurance_plan(
        base_generation=base,
        graph=graph,
        impact_manifest=impact,
        policy=fixture["policy"],
    )


def test_claim_and_graph_identity_are_order_independent_for_set_semantics() -> None:
    first = build_assurance_claim_spec(
        claim_id="CLAIM::ORDER",
        claim_class="UNIT",
        dependencies=["owner:A", "path:src/a.py"],
        harness_id="H1",
        execution_profile="DELTA_EXECUTOR",
    )
    second = build_assurance_claim_spec(
        claim_id="CLAIM::ORDER",
        claim_class="UNIT",
        dependencies=["path:src/a.py", "owner:A", "owner:A"],
        harness_id="H1",
        execution_profile="DELTA_EXECUTOR",
    )
    assert first == second
    assert validate_assurance_claim_spec(first) == first

    other = build_assurance_claim_spec(
        claim_id="CLAIM::OTHER",
        claim_class="UNIT",
        dependencies=["path:src/b.py"],
        harness_id="H1",
        execution_profile="DELTA_EXECUTOR",
    )
    graph_a = build_assurance_dependency_graph([first, other])
    graph_b = build_assurance_dependency_graph([other, first])
    assert graph_a == graph_b
    assert validate_assurance_dependency_graph(graph_a) == graph_a


def test_duplicate_claim_and_overlapping_generation_states_fail_closed() -> None:
    claim = build_assurance_claim_spec(
        claim_id="CLAIM::DUP",
        claim_class="UNIT",
        dependencies=["path:src/a.py"],
        harness_id="H1",
        execution_profile="DELTA_EXECUTOR",
    )
    with unittest.TestCase().assertRaisesRegex(
        RepositoryAssuranceError, "ASSURANCE_CLAIM_DUPLICATE"
    ):
        build_assurance_dependency_graph([claim, claim])

    graph = build_assurance_dependency_graph([claim])
    with unittest.TestCase().assertRaisesRegex(
        RepositoryAssuranceError, "CLAIM_STATE_OVERLAP"
    ):
        build_repository_assurance_generation(
            repository_tree_sha="a" * 40,
            graph_id=graph["graph_id"],
            policy_id="P",
            harness_generation_id="H1",
            passed_claim_ids=["CLAIM::DUP"],
            quarantined_claim_ids=["CLAIM::DUP"],
        )


def test_disjoint_mutation_reuses_unaffected_claims_and_runs_delta_only() -> None:
    fixture, graph, base = _fixture_state()
    plan = _plan_for(fixture, graph, base, "DISJOINT_A")
    dispositions = {
        row["claim_id"]: row["disposition"] for row in plan["claim_dispositions"]
    }
    assert dispositions == _scenario(fixture, "DISJOINT_A")["expected"]
    assert plan["reference_required"] is False
    assert plan["payload_rebuild_required"] is False

    certificate = build_candidate_assurance_certificate(
        plan=plan,
        executed_results={"CLAIM::A": PASS},
    )
    assert certificate["inherited_claim_ids"] == ["CLAIM::B", "CLAIM::SHARED"]
    assert certificate["executed_claim_ids"] == ["CLAIM::A"]
    assert validate_candidate_assurance_certificate(certificate) == certificate[
        "certificate_id"
    ]


def test_shared_owner_change_selects_wide_rerun_without_global_replay() -> None:
    fixture, graph, base = _fixture_state()
    plan = _plan_for(fixture, graph, base, "SHARED_OWNER")
    dispositions = {
        row["claim_id"]: row["disposition"] for row in plan["claim_dispositions"]
    }
    assert dispositions == _scenario(fixture, "SHARED_OWNER")["expected"]
    assert dispositions["CLAIM::SHARED"] == WIDE_RERUN_REQUIRED
    assert plan["reference_required"] is False


def test_unclassified_and_global_harness_mutations_escalate_to_reference() -> None:
    fixture, graph, base = _fixture_state()
    for scenario_id in ("UNCLASSIFIED_MUTATION", "GLOBAL_HARNESS_CHANGE"):
        plan = _plan_for(fixture, graph, base, scenario_id)
        assert plan["reference_required"] is True
        assert {
            row["disposition"] for row in plan["claim_dispositions"]
        } == {FULL_REFERENCE_REQUIRED}
        with unittest.TestCase().assertRaisesRegex(
            RepositoryAssuranceError, "REFERENCE_REQUIRED"
        ):
            build_candidate_assurance_certificate(
                plan=plan,
                executed_results={},
            )
        certificate = build_candidate_assurance_certificate(
            plan=plan,
            executed_results={},
            reference_result=PASS,
        )
        assert certificate["status"] == PASS


def test_not_evaluable_or_quarantined_claim_cannot_be_bypassed_by_reference() -> None:
    fixture, graph, base = _fixture_state()
    blocked = build_repository_assurance_generation(
        repository_tree_sha=base["repository_tree_sha"],
        graph_id=graph["graph_id"],
        policy_id=fixture["policy"]["policy_id"],
        harness_generation_id="HARNESS-v1",
        passed_claim_ids=["CLAIM::A", "CLAIM::B"],
        quarantined_claim_ids=["CLAIM::SHARED"],
    )
    plan = build_delta_assurance_plan(
        base_generation=blocked,
        graph=graph,
        impact_manifest=build_mutation_impact_manifest(
            programme_id="P",
            packet_id="WP",
            payload_id="f" * 64,
            changed_tokens=["harness:pytest-runner-v2"],
        ),
        policy=fixture["policy"],
    )
    assert any(
        row["claim_id"] == "CLAIM::SHARED"
        and row["disposition"] == QUARANTINED
        for row in plan["claim_dispositions"]
    )
    with unittest.TestCase().assertRaisesRegex(
        RepositoryAssuranceError, "QUARANTINED"
    ):
        build_candidate_assurance_certificate(
            plan=plan,
            executed_results={},
            reference_result=PASS,
        )


def test_reference_divergence_blocks_successor_generation() -> None:
    fixture, graph, base = _fixture_state()
    plan = _plan_for(fixture, graph, base, "DISJOINT_A")
    certificate = build_candidate_assurance_certificate(
        plan=plan,
        executed_results={"CLAIM::A": PASS},
    )
    scenario = _scenario(fixture, "REFERENCE_DIVERGENCE")
    receipt = build_reference_reconciliation_receipt(
        certificate=certificate,
        reference_results=scenario["reference_results"],
        expected_claim_ids=[claim["claim_id"] for claim in graph["claims"]],
    )
    assert receipt["status"] == ASSURANCE_MODEL_DIVERGENCE
    with unittest.TestCase().assertRaisesRegex(
        RepositoryAssuranceError, "DIVERGENCE_BLOCKS"
    ):
        advance_repository_assurance_generation(
            physical_tree_sha="b" * 40,
            graph=graph,
            policy_id=fixture["policy"]["policy_id"],
            harness_generation_id="HARNESS-v1",
            certificate=certificate,
            reconciliation_receipt=receipt,
            completeness="COMPLETE_FOR_DECLARED_CLAIM_UNIVERSE",
        )

    passing = build_reference_reconciliation_receipt(
        certificate=certificate,
        reference_results={claim["claim_id"]: PASS for claim in graph["claims"]},
        expected_claim_ids=[claim["claim_id"] for claim in graph["claims"]],
    )
    successor = advance_repository_assurance_generation(
        physical_tree_sha="b" * 40,
        graph=graph,
        policy_id=fixture["policy"]["policy_id"],
        harness_generation_id="HARNESS-v1",
        certificate=certificate,
        reconciliation_receipt=passing,
        completeness="COMPLETE_FOR_DECLARED_CLAIM_UNIVERSE",
    )
    assert successor["repository_tree_sha"] == "b" * 40
    assert set(successor["passed_claim_ids"]) == {
        claim["claim_id"] for claim in graph["claims"]
    }
    assert validate_repository_assurance_generation(successor) == successor


def test_main_movement_is_placement_only_when_dependency_frontier_is_disjoint() -> None:
    fixture, _, _ = _fixture_state()
    placement = _scenario(fixture, "PLACEMENT_ONLY_MAIN_MOVEMENT")
    assert main_movement_assurance_disposition(
        changed_tokens=placement["changed_tokens"],
        candidate_dependency_tokens=placement["candidate_dependency_tokens"],
        policy=fixture["policy"],
    ) == PLACEMENT_ONLY

    intersecting = _scenario(fixture, "DEPENDENCY_MAIN_MOVEMENT")
    assert main_movement_assurance_disposition(
        changed_tokens=intersecting["changed_tokens"],
        candidate_dependency_tokens=intersecting["candidate_dependency_tokens"],
        policy=fixture["policy"],
    ) == RERUN_REQUIRED

    assert main_movement_assurance_disposition(
        changed_tokens=["path:.github/workflows/tests.yml"],
        candidate_dependency_tokens=["path:src/a.py"],
        policy=fixture["policy"],
    ) == FULL_REFERENCE_REQUIRED


def test_coarse_repository_registry_is_valid_but_cannot_substitute_for_reference() -> None:
    registry = json.loads(CLAIM_REGISTRY_PATH.read_text(encoding="utf-8"))
    policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
    claims = [validate_assurance_claim_spec(row) for row in registry["claims"]]
    graph = build_assurance_dependency_graph(claims)
    assert graph["graph_id"] == registry["graph_id"]
    assert registry["blocking_path_eligible"] is False
    assert registry["completeness"] == "COARSE_CLAIM_FAMILIES_ONLY"

    base = build_repository_assurance_generation(
        repository_tree_sha="c" * 40,
        graph_id=graph["graph_id"],
        policy_id=policy["policy_id"],
        harness_generation_id="OVC-PYTEST-CANONICAL-RUNNER-v1",
        passed_claim_ids=[claim["claim_id"] for claim in claims],
        completeness=registry["completeness"],
    )
    plan = build_delta_assurance_plan(
        base_generation=base,
        graph=graph,
        impact_manifest=build_mutation_impact_manifest(
            programme_id="P",
            packet_id="WP",
            payload_id="d" * 64,
            changed_tokens=["path:src/ovc/research_operations/example.py"],
        ),
        policy=policy,
    )
    assert plan["reference_required"] is True
    assert "CLAIM:REPOSITORY::UNMAPPED_ASSURANCE_UNIVERSE" in plan[
        "reference_reasons"
    ]


def test_repository_artifacts_preserve_current_physical_and_cipr_boundaries() -> None:
    policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    current_cipr = json.loads(CIPR_CURRENT.read_text(encoding="utf-8"))
    default = json.loads(DEFAULT_SUBSTRATE.read_text(encoding="utf-8"))
    contract = CONTRACT_PATH.read_text(encoding="utf-8")
    plan = PLAN_PATH.read_text(encoding="utf-8")

    assert policy["blocking_path_substitution_active"] is False
    assert policy["required_check_substitution_active"] is False
    assert policy["runner_cutover_active"] is False
    assert policy["current_cipr_binding"]["cutover_consumed"] is False
    assert policy["physical_integration"]["parallel_physical_merge"] is False
    assert current_cipr["operator_stop_gate"] == "CIPR-G5-POST-PYT-CONSOLIDATED-CUTOVER"
    assert default["physical_main_exclusivity"]["exclusive_writer_identity"] == "DSAI_VIT_PHYSICAL_CONTROLLER"
    assert default["execution_policy"]["parallel_physical_merge"] is False

    required_defs = {
        "AssuranceClaimSpec",
        "AssuranceDependencyGraph",
        "RepositoryAssuranceGeneration",
        "MutationImpactManifest",
        "DeltaAssurancePlan",
        "CandidateAssuranceCertificate",
        "ReferenceReconciliationReceipt",
    }
    assert required_defs.issubset(schema["$defs"])
    assert "System Atlas may later project assurance state read-only" in contract
    assert "DSAI3V-RAC-G-DELTA-ASSURANCE-PILOT" in contract
    assert "LIVE_BLOCKING_PATH_UNCHANGED" in plan
    assert ".github/workflows/tests.yml" in plan
