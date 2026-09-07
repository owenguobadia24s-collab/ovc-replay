from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from .identity import CBSContractError, seal_object


TERMINAL_OUTCOMES = (
    "STABLE_SUBSET", "METHOD_SENSITIVE", "REPRESENTATION_SENSITIVE", "CONTEXT_SENSITIVE",
    "TRANSPORT_FAILURE", "BOUNDARY_SUPPORT_UNRESOLVED", "NO_STABLE_BOUNDARY_SUBSET",
    "CAUSAL_ADMISSION_FAIL", "NOT_EVALUABLE",
)

PROTOCOL_SECTIONS = (
    "authority_currentness", "source_population", "c2_owner_generation", "c2e_reference_pack",
    "b0_projection", "comparator_registry", "implementation_identity", "input_projections",
    "support_evaluability", "parameter_surfaces", "tolerance_grid", "representation_graph",
    "context_partitions", "evaluation_universe", "estimands", "region_correspondence",
    "dependence_hierarchy", "null_controls", "primary_inferential_procedure", "endpoint",
    "materiality", "specification_opportunity_ledger", "decision_complexity_budget",
    "search_exposure", "replication_reservation", "prior_exposure", "reviewer_binding",
    "external_artifact_capacity", "rollback",
)


def build_scientific_endpoint_manifest(
    *, reference_audit_endpoint: Mapping[str, Any], consensus_discovery_endpoint: Mapping[str, Any],
    evaluability_burden: Mapping[str, Any], terminal_rules: Mapping[str, Any], frozen_before_results: bool,
) -> dict[str, Any]:
    if not frozen_before_results:
        raise CBSContractError("INVALID_GENERATION:POST_RESULT_ENDPOINT")
    missing = sorted(set(TERMINAL_OUTCOMES) - set(terminal_rules))
    if missing:
        raise CBSContractError(f"CBS_ENDPOINT_INCOMPLETE:{','.join(missing)}")
    if set(reference_audit_endpoint) & {"score", "probability"} or set(consensus_discovery_endpoint) & {"score", "probability"}:
        raise CBSContractError("NO_VOTE_NO_AVERAGE")
    return seal_object(
        {"schema":"ovc-cbs-scientific-endpoint-manifest/v0.1",
         "reference_boundary_audit":dict(reference_audit_endpoint),
         "consensus_boundary_discovery":dict(consensus_discovery_endpoint),
         "estimand_crossing":"FORBIDDEN", "evaluability_burden":dict(evaluability_burden),
         "terminal_rules":{key:terminal_rules[key] for key in TERMINAL_OUTCOMES},
         "scalar_endpoint":None, "frozen_before_results":True}, id_field="scientific_endpoint_manifest_id"
    )


def build_materiality_declaration(*, rules: Mapping[str, Any], frozen_before_results: bool) -> dict[str, Any]:
    required = {"LOCATION_MIGRATION", "DISAPPEARANCE", "TOPOLOGY_CHANGE", "SUPPORT_CHANGE",
                "INSUFFICIENT_COVERAGE", "METHOD_SENSITIVITY", "REPRESENTATION_SENSITIVITY",
                "CONTEXT_SENSITIVITY", "TRANSPORT_FAILURE"}
    missing = sorted(required - set(rules))
    if not frozen_before_results or missing:
        reason = "POST_RESULT_MATERIALITY" if not frozen_before_results else f"MISSING:{','.join(missing)}"
        raise CBSContractError(f"INVALID_GENERATION:{reason}")
    return seal_object(
        {"schema":"ovc-cbs-boundary-stability-materiality-declaration/v0.1",
         "rules":{key:rules[key] for key in sorted(required)}, "scalar_materiality":None,
         "post_result_change":"MEANING_BEARING_SUCCESSOR", "frozen_before_results":True},
        id_field="materiality_declaration_id",
    )


def build_decision_complexity_budget(*, maximum_rules: int, maximum_exception_clauses: int,
                                     maximum_context_subsets: int, allowed_rule_grammar: Sequence[str]) -> dict[str, Any]:
    values = (maximum_rules, maximum_exception_clauses, maximum_context_subsets)
    if any(not isinstance(value, int) or value < 0 for value in values) or not allowed_rule_grammar:
        raise CBSContractError("DECISION_SEARCH_EXPOSURE_FAIL:INVALID_COMPLEXITY_BUDGET")
    return seal_object(
        {"schema":"ovc-cbs-boundary-support-decision-complexity-budget/v0.1",
         "maximum_rules":maximum_rules, "maximum_exception_clauses":maximum_exception_clauses,
         "maximum_context_subsets":maximum_context_subsets,
         "allowed_rule_grammar":sorted(set(allowed_rule_grammar)), "post_result_expansion":"INVALID_GENERATION"},
        id_field="decision_complexity_budget_id",
    )


def build_search_exposure_manifest(*, declared_opportunity_ids: Sequence[str], attempted_opportunity_ids: Sequence[str],
                                   known_preplan_exposure_ref: str, results_inspected: bool) -> dict[str, Any]:
    declared = sorted(set(declared_opportunity_ids)); attempted = sorted(set(attempted_opportunity_ids))
    if set(attempted) - set(declared):
        raise CBSContractError("DECISION_SEARCH_EXPOSURE_FAIL:UNDECLARED_ATTEMPT")
    return seal_object(
        {"schema":"ovc-cbs-decision-pack-search-exposure-manifest/v0.1",
         "declared_opportunity_ids":declared, "attempted_opportunity_ids":attempted,
         "known_preplan_exposure_ref":known_preplan_exposure_ref, "results_inspected":results_inspected,
         "complete_ledger_required":True, "exception_after_results":"INVALID_GENERATION"},
        id_field="search_exposure_manifest_id",
    )


def build_replication_reservation(*, objective_selection_rule: Mapping[str, Any], source_generation_condition: str,
                                  embargo_state: str, exposure_state: str, selected_after_r5: bool) -> dict[str, Any]:
    if selected_after_r5:
        raise CBSContractError("REPLICATION_CONTAMINATED")
    if not objective_selection_rule or not source_generation_condition or embargo_state != "UNCONSUMED_EMBARGOED":
        raise CBSContractError("REPLICATION_RESERVATION_ADOPTION_FAIL")
    return seal_object(
        {"schema":"ovc-cbs-replication-reservation-manifest/v0.1",
         "reservation_type":"OBJECTIVE_FUTURE_SELECTION_RULE", "objective_selection_rule":dict(objective_selection_rule),
         "source_generation_condition":source_generation_condition, "embargo_state":embargo_state,
         "exposure_state":exposure_state, "selection_before_r5":True,
         "consumed_c0b_eligible":False, "authority_to_execute":"CBSI_GR6_REPL_REQUIRED"},
        id_field="replication_reservation_manifest_id",
    )


def compile_development_protocol(*, generation: int, sections: Mapping[str, Any]) -> dict[str, Any]:
    missing = [name for name in PROTOCOL_SECTIONS if name not in sections]
    unresolved = [name for name in PROTOCOL_SECTIONS if sections.get(name) in (None, "", "UNRESOLVED", "PENDING")]
    if missing or unresolved:
        names = sorted(set(missing + unresolved))
        raise CBSContractError(f"CBS_PREREGISTRATION_CANDIDATE_INCOMPLETE:{','.join(names)}")
    return seal_object(
        {"schema":"ovc-cbs-development-research-protocol-bundle/v0.1",
         "programme_id":"C2E-BOUNDARY-STABILITY-0001", "generation":generation,
         "role":"DEVELOPMENT", "sections":{name:sections[name] for name in PROTOCOL_SECTIONS},
         "status":"CANDIDATE_NOT_FROZEN_NOT_AUTHORIZED", "freeze_receipt":None,
         "real_source_execution":"DENIED_PENDING_CBSI_G2_ALG_AND_CBSI_GREAL_DEV",
         "scientific_claim_effect":"NONE", "c2e_owner_effect":"NONE"},
        id_field="development_protocol_bundle_id",
    )


def validate_review_frontier_candidate(*, paths_to_hashes: Mapping[str, str], reviewer_binding: Mapping[str, Any]) -> dict[str, Any]:
    if not paths_to_hashes or any(len(value) != 40 and len(value) != 64 for value in paths_to_hashes.values()):
        raise CBSContractError("ALGORITHM_REVIEW_FRONTIER_DRIFT:INVALID_HASH")
    if reviewer_binding.get("status") != "UNBOUND_INDEPENDENT_REVIEW_REQUIRED":
        raise CBSContractError("INDEPENDENT_REVIEW_FAIL:PREMATURE_REVIEW_BINDING")
    return seal_object(
        {"schema":"ovc-cbs-algorithm-review-frontier-candidate/v0.1",
         "paths_to_hashes":dict(sorted(paths_to_hashes.items())), "reviewer_binding":dict(reviewer_binding),
         "review_status":"NOT_REVIEWED", "g2_pass":False, "freeze_eligible":False},
        id_field="algorithm_review_frontier_candidate_id",
    )
