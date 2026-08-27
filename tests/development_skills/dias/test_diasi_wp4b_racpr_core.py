from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from ovc.development.identity import canonical_sha256
from ovc.development.skills.dias import DiasContractError
from ovc.development.skills.dias_racpr import (
    AssuranceMemberSatisfactionBinding,
    AssuranceProofExposure,
    AssuranceProofExposureLedger,
    AssuranceProofRequirement,
    CommonModeDependency,
    CommonModeDependencyRegistry,
    FastPathCohort,
    ParentRACInterlockManifest,
    ProofAdmissibilityPolicy,
    ProofCurrentnessAssessment,
    ProofDependencyManifest,
    ProofFrontierCompletenessManifest,
    ReferenceReconciliationSchedule,
    derive_collection_parity,
    profile_assurance_decomposition,
    runtime_compatibility_route,
)


def requirement() -> AssuranceProofRequirement:
    return AssuranceProofRequirement("CLAIM:RUNNER_PARITY", "RAC:PLAN:1", "PIP:1", ("MEMBER:PARITY",), ("IMPLEMENTATION", "HARNESS"), "EXACT_CLOSED_UNIVERSE", ("CLAIM", "DEPENDENCY"), "REFERENCE:UNITTEST")


def test_requirement_is_immutable_content_addressed_and_reference_only() -> None:
    item = requirement()
    assert len(item.requirement_id) == 64
    assert item.authority_mode == "REFERENCE_ONLY"
    with pytest.raises(DiasContractError):
        replace(item, authority_mode="DECISION_BEARING")


def test_dependency_manifest_freezes_every_consumed_dimension() -> None:
    manifest = ProofDependencyManifest("ATTEMPT:1", ("TREE:a",), ("PRODUCER:legacy",), ("HARNESS:pytest",), ("ENV:py314",), ("PROVENANCE:cipr",), ("TOKEN:source",))
    assert len(manifest.manifest_id) == 64
    with pytest.raises(DiasContractError):
        replace(manifest, dependency_tokens=())


def test_frontier_requires_exact_closed_universe_and_rejects_unmapped() -> None:
    exact = ProofFrontierCompletenessManifest("a" * 64, ("A", "B"), ("B", "A"), "EXACT_CLOSED_UNIVERSE")
    assert exact.closed is True
    assert replace(exact, observed_dependencies=("A",)).closed is False
    assert replace(exact, unmapped_sentinel=True).closed is False


def test_currentness_requires_all_nine_dimensions() -> None:
    dimensions = {name: "CURRENT" for name in ("CLAIM", "METHOD", "DEPENDENCY", "HARNESS", "ENVIRONMENT", "POLICY", "PLACEMENT", "OWNER", "SOURCE_ARTIFACT")}
    assessment = ProofCurrentnessAssessment("p" * 64, dimensions, True)
    assert assessment.current is True
    assert replace(assessment, dimension_status={"CLAIM": "CURRENT"}).disposition == "REFERENCE_RERUN_REQUIRED"


def test_admissibility_is_validity_first_and_performance_has_no_semantic_power() -> None:
    policy = ProofAdmissibilityPolicy("POLICY:1", {"CLAIM:RUNNER_PARITY": ("METHOD:SET_EQUAL",)}, ("SET_EQUAL", "CONJUNCTION"))
    kwargs = dict(claim_id="CLAIM:RUNNER_PARITY", method_id="METHOD:SET_EQUAL", semantic_applicability=True, exact_identity=True, completeness=True, independence=True, currentness=True, deterministic_rule_pass=True)
    assert policy.assess(**kwargs) == "REFERENCE_ONLY_PROOF_AVAILABLE"
    kwargs["completeness"] = False
    assert policy.assess(**kwargs) == "REFERENCE_EXECUTION"
    with pytest.raises(DiasContractError):
        replace(policy, performance_can_create_sufficiency=True)


def test_member_binding_cannot_be_decision_bearing() -> None:
    binding = AssuranceMemberSatisfactionBinding(requirement().requirement_id, "MEMBER:PARITY", "CLAIM:RUNNER_PARITY", "METHOD:SET_EQUAL", "p" * 64, ("HARNESS",), "EXACT_CLOSED_UNIVERSE", ("DEPENDENCY",))
    assert len(binding.binding_id) == 64
    with pytest.raises(DiasContractError):
        replace(binding, decision_bearing=True)


def test_collection_membership_parity_is_set_exact_and_duplicate_sensitive() -> None:
    assert derive_collection_parity(("a", "b"), ("b", "a")).result == "PASS"
    assert derive_collection_parity(("a", "a"), ("a",)).result == "NOT_PROVABLE"
    assert derive_collection_parity(("a",), ("a",), ("loader-error",)).result == "NOT_PROVABLE"


@pytest.mark.parametrize(
    "equivalent,closed,residual,expected",
    [
        (True, True, False, "DERIVED_PROOF_REFERENCE_ONLY"),
        (False, True, True, "RESIDUAL_EXECUTION_REFERENCE_ONLY"),
        (False, False, True, "REFERENCE_EXECUTION"),
    ],
)
def test_runtime_compatibility_routes_to_derived_residual_or_reference(equivalent: bool, closed: bool, residual: bool, expected: str) -> None:
    assert runtime_compatibility_route(environment_equivalent=equivalent, dependency_frontier_closed=closed, residual_dependency_complete=residual) == expected


def test_profile_assurance_requires_all_four_owner_admitted_atoms() -> None:
    atoms = {"SELECTION": "PASS", "SELECTED_EXECUTION": "PASS", "ORCHESTRATION_VALIDATION": "PASS", "BOUNDARY_PRESERVATION": "PASS"}
    assert profile_assurance_decomposition(atoms) == "DECOMPOSED_PROOF_REFERENCE_ONLY"
    del atoms["BOUNDARY_PRESERVATION"]
    assert profile_assurance_decomposition(atoms) == "REFERENCE_EXECUTION"


def test_reconciliation_debt_forces_reference_route() -> None:
    schedule = ReferenceReconciliationSchedule("COLLECTION_PARITY", ("METHOD_CHANGE", "HARNESS_CHANGE"), 10, 3600, 11, 5)
    assert schedule.debt_exceeded is True
    assert schedule.route == "REFERENCE_EXECUTION"


def test_common_mode_false_agreement_requires_fixture_and_third_path() -> None:
    valid = CommonModeDependency("canonical-id", True, True, True, "MUTANT:canonical-id", "THIRD_PATH:independent-canonicalizer")
    CommonModeDependencyRegistry((valid,))
    with pytest.raises(DiasContractError):
        CommonModeDependencyRegistry((replace(valid, independent_third_path=None),))


def test_exposure_ledger_is_reconstructable_but_not_decision_bearing() -> None:
    exposure = AssuranceProofExposure("proof", "certificate", "1" * 40, "2" * 40, "RAG:1", False)
    ledger = AssuranceProofExposureLedger((exposure,))
    assert ledger.affected_generations("proof") == ("RAG:1",)
    with pytest.raises(DiasContractError):
        AssuranceProofExposureLedger((replace(exposure, decision_bearing=True),))


def test_parent_rac_interlock_is_shadow_only_and_contamination_prohibited() -> None:
    interlock = ParentRACInterlockManifest("PILOT_REBASELINED_ACTIVE", False, None, True)
    assert interlock.decision_bearing_allowed is False
    with pytest.raises(DiasContractError):
        replace(interlock, contamination_permitted=True)
    with pytest.raises(DiasContractError):
        replace(interlock, parent_general_pass=True)


def test_fast_path_cohort_is_frozen_before_observation_with_reason_coded_exclusions() -> None:
    cohort = FastPathCohort(("PIP:ordinary-1", "PIP:ordinary-2"), {"PIP:security": "SECURITY_INCIDENT_ROUTE"}, True)
    assert cohort.target_p90_seconds == 60
    with pytest.raises(DiasContractError):
        replace(cohort, frozen_before_observation=False)


def test_wp4b_court_record_is_reference_only_and_advances_to_wp5() -> None:
    root = Path(__file__).resolve().parents[3]
    wp4b = root / "docs/programmes/dias-v0-1/wp4b"
    authority = json.loads((wp4b / "DIASI_WP4B_VIT_AUTHORITY_MANIFEST.json").read_text(encoding="utf-8"))
    frontier = json.loads((wp4b / "DIASI_WP4B_VIT_DEPENDENCY_FRONTIER.json").read_text(encoding="utf-8"))
    interlock = json.loads((wp4b / "DIASI_WP4B_PARENT_RAC_INTERLOCK_MANIFEST.json").read_text(encoding="utf-8"))
    assert canonical_sha256(authority["payload"]) == authority["logical_id"]
    assert canonical_sha256(frontier["payload"]) == frontier["logical_id"]
    assert interlock["decision_bearing_substitution"] == "DENIED"
    assert interlock["parent_rac_evidence_contamination"] == "PROHIBITED"
    pointer = json.loads((root / "registries/implementation/dias_v0_1/CURRENT_STATE_POINTER.json").read_text(encoding="utf-8"))
    state = json.loads((root / pointer["current_state"]).read_text(encoding="utf-8"))
    assert state["next_packet"] == "DIASI-WP5"
    assert state["proof_substitution"] is False
