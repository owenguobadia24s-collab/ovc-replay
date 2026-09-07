from __future__ import annotations

import json
from pathlib import Path

import pytest

from ovc.research_operations.cbs.development_candidate import build_development_candidate
from ovc.research_operations.cbs.identity import CBSContractError, verify_object
from ovc.research_operations.cbs.preregistration import (
    PROTOCOL_SECTIONS, TERMINAL_OUTCOMES, build_decision_complexity_budget, build_materiality_declaration,
    build_replication_reservation, build_scientific_endpoint_manifest, build_search_exposure_manifest,
    compile_development_protocol, validate_review_frontier_candidate,
)

ROOT = Path(__file__).resolve().parents[3]


def test_endpoint_and_materiality_are_two_estimand_non_scalar_and_pre_result() -> None:
    endpoint = build_scientific_endpoint_manifest(
        reference_audit_endpoint={"denominator":"ALL_FROZEN_B0_REFERENCE_BOUNDARIES"},
        consensus_discovery_endpoint={"denominator":"ALL_ELIGIBLE_TEMPORAL_OPPORTUNITIES"},
        evaluability_burden={"complete_universe":True,"matched_and_full":True},
        terminal_rules={name:{"disposition":name} for name in TERMINAL_OUTCOMES}, frozen_before_results=True,
    )
    materiality = build_materiality_declaration(rules={name:{"typed_change":name} for name in (
        "LOCATION_MIGRATION","DISAPPEARANCE","TOPOLOGY_CHANGE","SUPPORT_CHANGE","INSUFFICIENT_COVERAGE",
        "METHOD_SENSITIVITY","REPRESENTATION_SENSITIVITY","CONTEXT_SENSITIVITY","TRANSPORT_FAILURE")},
        frozen_before_results=True)
    verify_object(endpoint,id_field="scientific_endpoint_manifest_id")
    verify_object(materiality,id_field="materiality_declaration_id")
    assert endpoint["scalar_endpoint"] is None and materiality["scalar_materiality"] is None


def test_complexity_exposure_and_replication_fail_closed() -> None:
    budget=build_decision_complexity_budget(maximum_rules=1,maximum_exception_clauses=0,maximum_context_subsets=0,
                                            allowed_rule_grammar=["TYPED_TERMINAL_DISPOSITION_ONLY"])
    exposure=build_search_exposure_manifest(declared_opportunity_ids=["r1"],attempted_opportunity_ids=[],
                                            known_preplan_exposure_ref="preplan",results_inspected=False)
    reservation=build_replication_reservation(objective_selection_rule={"rule":"FIRST_OWNER_RELEASE_AFTER_R5_EMBARGO"},
        source_generation_condition="SAME_OWNER_GENERATION_OR_PREDECLARED_SUCCESSOR_EQUIVALENCE_REVIEW",
        embargo_state="UNCONSUMED_EMBARGOED",exposure_state="NO_PROTECTED_POPULATION_INSPECTION",selected_after_r5=False)
    assert budget["maximum_exception_clauses"] == 0 and exposure["attempted_opportunity_ids"] == []
    assert reservation["authority_to_execute"] == "CBSI_GR6_REPL_REQUIRED"
    with pytest.raises(CBSContractError,match="REPLICATION_CONTAMINATED"):
        build_replication_reservation(objective_selection_rule={"rule":"x"},source_generation_condition="x",
            embargo_state="UNCONSUMED_EMBARGOED",exposure_state="x",selected_after_r5=True)


def test_protocol_compiler_is_atomic_complete_and_not_authority() -> None:
    sections={name:f"id:{name}" for name in PROTOCOL_SECTIONS}
    bundle=compile_development_protocol(generation=1,sections=sections)
    verify_object(bundle,id_field="development_protocol_bundle_id")
    assert list(bundle["sections"]) == list(PROTOCOL_SECTIONS)
    assert bundle["status"] == "CANDIDATE_NOT_FROZEN_NOT_AUTHORIZED" and bundle["freeze_receipt"] is None
    with pytest.raises(CBSContractError,match="CANDIDATE_INCOMPLETE:source_population"):
        compile_development_protocol(generation=1,sections={**sections,"source_population":"UNRESOLVED"})


def test_review_frontier_is_candidate_only_until_distinct_fresh_reviewer() -> None:
    frontier=validate_review_frontier_candidate(paths_to_hashes={"src/a.py":"0"*40},reviewer_binding={
        "status":"UNBOUND_INDEPENDENT_REVIEW_REQUIRED","implementation_author_disallowed":True,
        "fresh_process_required":True,"conversation_state_forbidden":True})
    assert frontier["review_status"] == "NOT_REVIEWED" and frontier["freeze_eligible"] is False
    with pytest.raises(CBSContractError,match="PREMATURE_REVIEW_BINDING"):
        validate_review_frontier_candidate(paths_to_hashes={"src/a.py":"0"*40},reviewer_binding={"status":"PASS"})


def test_exact_development_candidate_reconstructs_static_protocol_and_all_surfaces() -> None:
    built = build_development_candidate()
    recorded = json.loads((ROOT/"registries/research_operations/cbs/CBSI_WP6_DEVELOPMENT_RESEARCH_PROTOCOL_CANDIDATE_v0_1.json").read_text())
    manifest = json.loads((ROOT/"registries/research_operations/cbs/CBSI_WP6_DEVELOPMENT_CANDIDATE_MANIFEST_SET_v0_1.json").read_text())
    assert built["protocol"] == recorded
    assert built["component_ids"] == manifest["component_ids"]
    assert manifest["declared_surface"] == {"method_configurations":19,"semantic_configurations":19,
        "tolerances_per_clock":4,"representations":3,"contexts":9,"control_classes":6,"estimands":2,
        "decision_rules":1,"exception_clauses":0}
    assert built["components"]["source_population"]["source_consumed"] is False
    assert built["components"]["b0_projection"]["ground_truth"] is False
    assert built["components"]["method_surface"]["exposed_lab_defaults_reused"] is False
    assert built["components"]["search_exposure"]["attempted_opportunity_ids"] == []


def test_pre_g2_currentness_closes_owner_surface_blocker_without_source_consumption() -> None:
    current = json.loads((ROOT/"records/research_operations/cbs/CBSI_WP6_AUTHORITY_CURRENTNESS_MANIFEST_v0_1.json").read_text())
    adoption = json.loads((ROOT/"records/research_operations/cbs/CBSI_WP6_REPLICATION_RESERVATION_ADOPTION_ASSESSMENT_v0_1.json").read_text())
    assert current["status"] == "PASS_CURRENT_PRE_G2"
    assert current["owner_surface_reconciliation"]["status"] == "OWNER_READ_SURFACE_REQUIRED_BLOCKER_CLOSED_FORWARD"
    assert current["source"]["source_consumed"] is False and current["market_envelope"]["validation"] == "LOCKED_UNCONSUMED"
    assert adoption["preplan_lab_reservation"]["adoption"] == "REJECT"
    assert adoption["official_candidate"]["embargo"] == "UNCONSUMED"


def test_revised_1_reason_code_minimum_is_complete() -> None:
    registry = json.loads((ROOT/"registries/research_operations/cbs/CBS_REASON_CODE_REGISTRY_v0_1.json").read_text())
    required = {"RETROSPECTIVE_CAUSAL_JOIN_FORBIDDEN","FVT_BACKDATE_ATTEMPT","CENSOR_NOT_TERMINATION",
        "MEANING_BEARING_SUCCESSOR","KNOWN_EXPOSURE_UNBOUND","OWNER_READ_SURFACE_REQUIRED",
        "PRIMARY_REPRESENTATION_INCOMPLETE","NULL_EXECUTION_UNFROZEN","ALGORITHM_REVIEW_FRONTIER_DRIFT",
        "LAB_SOURCE_ARCHIVE_INCOMPLETE","ARTIFACT_RETENTION_INCOMPLETE",
        "REPLICATION_RESERVATION_ADOPTION_FAIL","AUTHORITY_CURRENTNESS_STALE"}
    assert required <= set(registry["codes"])
