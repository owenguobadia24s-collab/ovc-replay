from __future__ import annotations

from typing import Any

from .identity import seal_object
from .multiplicity import build_specification_opportunity_ledger
from .preregistration import (
    TERMINAL_OUTCOMES,
    build_decision_complexity_budget,
    build_materiality_declaration,
    build_replication_reservation,
    build_scientific_endpoint_manifest,
    build_search_exposure_manifest,
    compile_development_protocol,
)
from .projections import build_b0_projection_manifest, build_input_projection_manifest


ACTIVE_PACK = "C2E.BOUNDARY.PACK.043c628a3a29372ae478026db307d0d8"
ACTIVE_PACK_SHA256 = "043c628a3a29372ae478026db307d0d8b2347fcbbc7b06dbb1a3cc345c86e313"
OWNER_GENERATION = "C2VNEXT.OWNER.GENERATION.ASR00.C2AR-PACKAGE-v1.READ-v0.1"
OWNER_READ_AUTHORITY = "AUTH.OPT-B.C2.vNext.OWNER_STRUCTURAL_SNAPSHOT.READ.v0.1"
SOURCE_SCHEMA = "ovc-c2-vnext-owner-structural-snapshot-read/v0.1"


def _source_population() -> dict[str, Any]:
    return seal_object(
        {
            "schema":"ovc-cbs-source-population-candidate/v0.1", "role":"DEVELOPMENT",
            "instrument":"GBPUSD", "sides":["BID","ASK"], "clocks":["15M","2H_A_L"],
            "target_start":"2024-01-01T00:00:00Z", "target_end_exclusive":"2025-01-01T00:00:00Z",
            "opt_a_release_id":"OPT-A.GBPUSD.DEVELOPMENT.2024.v2",
            "opt_a_manifest_id":"MANIFEST.OPT-A.GBPUSD.DEVELOPMENT.2024.v2.r2",
            "opt_a_manifest_sha256":"25e1be8a7edb0e96017c45bf35f4e788345f94b22a8ed9bb0874c86338ba64cc",
            "manifest_bound_payload_objects":101, "manifest_bound_payload_bytes":52762768,
            "provider":"CURRENT_BOUND_OPT_A_PROVIDER", "owner_generation_id":OWNER_GENERATION,
            "owner_read_authority_id":OWNER_READ_AUTHORITY,
            "population_rule":"ALL_MANIFEST_BOUND_TARGET_ELIGIBLE_OWNER_SNAPSHOTS_PRESERVE_NON_TARGET_GAP_CENSOR_AND_MISSINGNESS_IN_DENOMINATOR",
            "source_consumed":False, "authority_to_execute":"CBSI_GREAL_DEV_REQUIRED",
        }, id_field="source_population_candidate_id"
    )


def _b0_projection() -> dict[str, Any]:
    return build_b0_projection_manifest(
        pack_id=ACTIVE_PACK, pack_sha256=ACTIVE_PACK_SHA256,
        action_classes={"BIRTH":"REFERENCE_BOUNDARY", "CONTINUATION":"NON_BOUNDARY_EVENT",
                        "PHASE_MUTATION":"NON_BOUNDARY_EVENT", "RE_PARENT":"REFERENCE_BOUNDARY",
                        "CENSOR_GAP":"SOURCE_GAP", "CENSOR_RELEASE_END":"CENSOR"},
        status="CANDIDATE_DEVELOPMENT_NOT_FROZEN",
    )


def _input_projections() -> dict[str, Any]:
    projections = [
        build_input_projection_manifest(
            comparator_id="B1", profile_id="B1_C2_RAW_TYPED_SIGNATURE_DEVELOPMENT_CANDIDATE_v0.1",
            source_schema=SOURCE_SCHEMA,
            fields=["snapshot_id","observation_id","interval_end","first_valid_time","continuity",
                    "projection_eligibility","component_refs","component_availability","owner_records"],
            transforms=[{"id":"CANONICAL_OWNER_TYPED_SIGNATURE","order":"FIELD_CATALOG_AND_OWNER_SCHEMA",
                         "missing":"PRESERVE_TYPED"}], scaling="NONE", missingness="ABSTAIN_TYPED_NO_IMPUTATION",
            representation="C2_RAW_TYPED", first_valid_time_field="first_valid_time",
            exposure_classification="PROSPECTIVE_DISTINCT_FROM_EXPOSED_B1_STATE_TRANSITION_V1",
        )
    ]
    for method in ("B2", "B3"):
        projections.append(build_input_projection_manifest(
            comparator_id=method, profile_id=f"{method}_OWNER_MOTION_PRICE_DELTA_DEVELOPMENT_CANDIDATE_v0.1",
            source_schema=SOURCE_SCHEMA,
            fields=["snapshot_id","observation_id","interval_end","first_valid_time","continuity",
                    "projection_eligibility","owner_records.formula_profiles","component_availability"],
            transforms=[{"id":"EXACT_MOTION_PRICE_DELTA","path":"owner_records.formula_profiles.MOTION.facts.price_delta"},
                        {"id":"CAUSAL_PREFIX_ROBUST_SCALE","calibration_prefix_fraction":"0.05",
                         "quantile_definition":"TYPE_1"}],
            scaling="ABSOLUTE_DELTA_OVER_PREFIX_MEDIAN_ABSOLUTE_NONZERO_DELTA",
            missingness="SEGMENT_AT_BREAK_ABSTAIN_TYPED_NO_IMPUTATION",
            representation="C2_RAW_TYPED_NUMERIC_MOTION_DELTA", first_valid_time_field="first_valid_time",
            exposure_classification="PROSPECTIVE_NORMALISED_RULE_EXPOSED_LAB_GRID_NOT_REUSED",
        ))
    return seal_object(
        {"schema":"ovc-cbs-development-input-projection-candidate-set/v0.1", "manifests":projections,
         "hidden_fields":"FORBIDDEN", "owner_field_catalog_blob":"8e3e130c298aec8c24fbe15bffb400fd958235fc",
         "status":"CANDIDATE_NOT_FROZEN"}, id_field="projection_candidate_set_id"
    )


def _method_surface(b0: dict[str, Any], projection_set: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    projection_ids = {row["comparator_id"]: row["projection_id"] for row in projection_set["manifests"]}

    def config(identifier: str, family: str, parameters: dict[str, Any], representation: str) -> dict[str, Any]:
        projection_id = b0["b0_projection_id"] if family == "B0" else projection_ids.get(family, "B9_CONTROL")
        return {"configuration_id":identifier, "method_family_id":family, "projection_id":projection_id,
                "parameters":parameters, "representation_id":representation,
                "context_id":"ALL_DECLARED_CONTEXTS", "state":"DECLARED"}

    configurations = [
        config("B0-DEV-CANDIDATE", "B0", {"event_classes":"EXACT_B0_PROJECTION"}, "C2E_OWNER_TYPED_EVENT"),
        config("B1-DEV-CANDIDATE", "B1", {"change":"EXACT_TYPED_SIGNATURE_INEQUALITY"}, "C2_RAW_TYPED"),
    ]
    for quantile in ("Q25", "Q50", "Q75", "Q90"):
        configurations.append(config(f"B2-{quantile}", "B2",
            {"threshold":quantile,"calibration":"FIRST_5_PERCENT_TYPE_1_ABS_NONZERO"},
            "C2_RAW_TYPED_NUMERIC_MOTION_DELTA"))
    for multiplier in (1, 2, 4, 8):
        for minimum in (2, 4, 8):
            configurations.append(config(f"B3-L{multiplier}-M{minimum}", "B3",
                {"penalty_multiplier":multiplier,"base":"PREFIX_VARIANCE_TIMES_LOG_N","min_segment_length":minimum},
                "C2_RAW_TYPED_NUMERIC_MOTION_DELTA"))
    configurations.append(config("B9-DEV-CANDIDATE", "B9", {"boundaries":0}, "CONTROL"))
    surface = seal_object(
        {"schema":"ovc-cbs-development-method-parameter-surface/v0.1", "configurations":configurations,
         "core_methods":["B0","B1","B2","B3","B9"],
         "conditional_methods":{"B4":"NOT_EVALUABLE","B5":"NOT_EVALUABLE","B6":"NOT_EVALUABLE",
                                "B7":"NOT_EVALUABLE","B8":"REFERENCE_ONLY_NOT_GROUND_TRUTH"},
         "minimum_temporal_class_diversity":["OWNER_DEFINED_ONLINE_CAUSAL","ONLINE_CAUSAL",
                                               "CONFIRMATION_DELAYED","RETROSPECTIVE","CONTROL"],
         "configuration_count":len(configurations), "best_configuration_selection":"FORBIDDEN",
         "exposed_lab_defaults_reused":False}, id_field="method_parameter_surface_id"
    )
    return surface, build_specification_opportunity_ledger(configurations)


def _tolerance_representation_context() -> dict[str, Any]:
    return seal_object(
        {"schema":"ovc-cbs-tolerance-representation-context-candidate/v0.1",
         "tolerances":[{"clock":"15M","opportunity_intervals":[0,1,2,4],"seconds":[0,900,1800,3600]},
                       {"clock":"2H_A_L","opportunity_intervals":[0,1,2,4],"seconds":[0,7200,14400,28800]}],
         "representations":[{"id":"C2_RAW_TYPED","role":"PRIMARY","source":"DIRECT_OWNER_PUBLIC"},
                            {"id":"C2_RAW_TYPED_NUMERIC_MOTION_DELTA","role":"METHOD_REQUIRED_SUBPROJECTION",
                             "source":"DIRECT_OWNER_PUBLIC_EMBEDDED_SCHEMA"},
                            {"id":"C2_TOPOLOGY_COUNT_VECTOR","role":"REPRESENTATION_CHALLENGE",
                             "source":"LAWFULLY_DERIVED_COUNTS_NO_OWNER_SEMANTIC_INFERENCE"}],
         "contexts":["ALL","SIDE_BID","SIDE_ASK","CLOCK_15M","CLOCK_2H_A_L","UTC_Q1","UTC_Q2","UTC_Q3","UTC_Q4"],
         "region_rule":"CONNECTED_COMPONENTS_UNDER_EACH_TOLERANCE_NO_MEAN_TIMESTAMP",
         "matching_rule":"MAX_CARDINALITY_THEN_MIN_DISPLACEMENT_STABLE_TIE_DIRECTIONAL_ONE_TO_ONE_FIRST",
         "all_surfaces_retained":True, "best_surface_selection":"FORBIDDEN"},
        id_field="tolerance_representation_context_manifest_id"
    )


def _controls() -> dict[str, Any]:
    return seal_object(
        {"schema":"ovc-cbs-development-null-execution-candidate-set/v0.1",
         "controls":[
             {"id":"B9","class":"NO_SEGMENTATION","algorithm":"ZERO_BOUNDARIES_PRESERVE_SOURCE_EVENTS","seed":None},
             {"id":"SHIFT","class":"BOUNDARY_PRESERVING_SHIFT","algorithm":"CYCLIC_SHIFT_WITHIN_OWNER_CONTINUITY_SEGMENT","seed":19001},
             {"id":"BLOCK","class":"DEPENDENCE_PRESERVING_OFFSET_OR_BLOCK","algorithm":"FIXED_LENGTH_BLOCK_ROTATION_WITHIN_SEGMENT","seed":19002},
             {"id":"PARAMETER","class":"PARAMETER_NEIGHBOUR","algorithm":"EXECUTE_COMPLETE_ADJACENT_DECLARED_GRID_NO_SELECTION","seed":None},
             {"id":"REPRESENTATION","class":"REPRESENTATION_PERTURBATION","algorithm":"CANONICAL_EQUIVALENT_ENCODING_PLUS_DECLARED_TOPOLOGY_COUNT_CHALLENGE","seed":19003},
             {"id":"CONTEXT","class":"CONTEXT_TIME_PARTITION","algorithm":"PREDECLARED_SIDE_CLOCK_UTC_QUARTER_PARTITIONS","seed":None}],
         "break_censor_policy":"PRESERVE_TYPED_NEVER_SHIFT_ACROSS_BREAK",
         "output_completeness":"ALL_CONTROL_CONFIGURATION_OPPORTUNITIES",
         "adequacy":"PRESERVE_AND_DESTROY_STATEMENTS_REQUIRED_PER_RUN", "b9_substitution":"FORBIDDEN",
         "post_result_selection":"INVALID_GENERATION"}, id_field="null_control_candidate_set_id"
    )


def _endpoint_materiality() -> tuple[dict[str, Any], dict[str, Any]]:
    endpoint = build_scientific_endpoint_manifest(
        reference_audit_endpoint={"population":"ALL_EXACT_B0_REFERENCE_REGIONS_AND_ALL_ELIGIBLE_OPPORTUNITIES",
                                  "output":"FULL_TOLERANCE_DIRECTIONAL_CORRESPONDENCE_AND_UNMATCHED_SURFACES",
                                  "ground_truth":False},
        consensus_discovery_endpoint={"population":"ALL_ELIGIBLE_TEMPORAL_OPPORTUNITIES",
                                      "output":"SYMMETRIC_REGIONS_FAMILY_FACTORISED_SUPPORT_AND_DISAGREEMENT",
                                      "c2e_privileged":False},
        evaluability_burden={"complete_opportunity_denominator":True,"matched_support":True,
                             "full_population":True,"core_temporal_diversity":True,"null_adequacy":True},
        terminal_rules={name:{"rule":"EMIT_EXACT_TYPED_DISPOSITION_WHEN_PRECONDITIONS_MET",
                              "no_cross_estimand_implication":True} for name in TERMINAL_OUTCOMES},
        frozen_before_results=True,
    )
    materiality = build_materiality_declaration(rules={
        "LOCATION_MIGRATION":{"material_when":"MATCH_CLASS_OR_DISPLACEMENT_BIN_CHANGES_ON_ANY_DECLARED_TOLERANCE","canonical_timestamp":None},
        "DISAPPEARANCE":{"material_when":"PREVIOUSLY_MATCHED_FAMILY_HAS_NO_ESTIMATE_ACROSS_COMPLETE_DECLARED_TOLERANCE_SURFACE"},
        "TOPOLOGY_CHANGE":{"material_when":"ONE_TO_ONE_SPLIT_MERGE_UNMATCHED_OR_AMBIGUOUS_CLASS_CHANGES"},
        "SUPPORT_CHANGE":{"material_when":"SUPPORTING_METHOD_FAMILY_OR_DEPENDENCE_CLUSTER_SET_CHANGES"},
        "INSUFFICIENT_COVERAGE":{"material_when":"UNIVERSE_INCOMPLETE_OR_MATCHED_AND_FULL_MISSING_OR_CORE_DIVERSITY_FAILS"},
        "METHOD_SENSITIVITY":{"material_when":"DECLARED_METHOD_FAMILY_DISPOSITIONS_CONFLICT_ON_MATCHED_SUPPORT"},
        "REPRESENTATION_SENSITIVITY":{"material_when":"DISPOSITION_OR_TOPOLOGY_CHANGES_ACROSS_DECLARED_REPRESENTATIONS"},
        "CONTEXT_SENSITIVITY":{"material_when":"DISPOSITION_OR_SUPPORT_SET_CHANGES_ACROSS_PREDECLARED_CONTEXTS"},
        "TRANSPORT_FAILURE":{"material_when":"SIDE_OR_CLOCK_TRANSPORT_FAILS_AFTER_MATCHED_AND_FULL_ACCOUNTING"},
    }, frozen_before_results=True)
    return endpoint, materiality


def build_development_candidate() -> dict[str, Any]:
    source = _source_population(); b0 = _b0_projection(); projections = _input_projections()
    methods, opportunity = _method_surface(b0, projections)
    tolerance = _tolerance_representation_context(); controls = _controls(); endpoint, materiality = _endpoint_materiality()
    complexity = build_decision_complexity_budget(
        maximum_rules=1, maximum_exception_clauses=0, maximum_context_subsets=0,
        allowed_rule_grammar=["ALL_CORE_FAMILY_EXECUTIONS_REQUIRED","ALL_DECLARED_SURFACES_RETAINED",
                              "TYPED_TERMINAL_DISPOSITION_ONLY"])
    exposure = build_search_exposure_manifest(
        declared_opportunity_ids=["R5-CANDIDATE-RULE-01-CONSERVATIVE-ALL-SURFACES"], attempted_opportunity_ids=[],
        known_preplan_exposure_ref="records/research_operations/cbs/CBSI_PRE_PLAN_EXPOSURE_MANIFEST_v0_1.json",
        results_inspected=False)
    replication = build_replication_reservation(
        objective_selection_rule={"instrument":"GBPUSD","sides":["BID","ASK"],"clocks":["15M","2H_A_L"],
            "provider_rule":"SAME_CURRENT_BOUND_OPT_A_PROVIDER",
            "interval_rule":"FIRST_COMPLETE_12_CALENDAR_MONTHS_BEGINNING_ON_OR_AFTER_2027-01-01",
            "validation_exclusion":"ANY_VALIDATION_PARTITION_OR_OBJECT_FORBIDDEN",
            "source_object_rule":"ALL_OBJECTS_IN_FIRST_OWNER_ADMITTED_COMPLETE_MANIFEST_SATISFYING_RULE"},
        source_generation_condition="SAME_C2_OWNER_GENERATION_OR_PREDECLARED_SUCCESSOR_EQUIVALENCE_AND_FRESH_G2_REVIEW",
        embargo_state="UNCONSUMED_EMBARGOED",
        exposure_state="NO_PROTECTED_POPULATION_INSPECTION_BEFORE_CBSI_GR6_REPL", selected_after_r5=False)
    components = {"source_population":source, "b0_projection":b0, "input_projections":projections,
                  "method_surface":methods, "specification_opportunity_ledger":opportunity,
                  "tolerance_representation_context":tolerance, "null_controls":controls,
                  "endpoint":endpoint, "materiality":materiality, "decision_complexity_budget":complexity,
                  "search_exposure":exposure, "replication_reservation":replication}
    identity_fields = {
        "source_population":"source_population_candidate_id", "b0_projection":"b0_projection_id",
        "input_projections":"projection_candidate_set_id", "method_surface":"method_parameter_surface_id",
        "specification_opportunity_ledger":"specification_ledger_id",
        "tolerance_representation_context":"tolerance_representation_context_manifest_id",
        "null_controls":"null_control_candidate_set_id", "endpoint":"scientific_endpoint_manifest_id",
        "materiality":"materiality_declaration_id", "decision_complexity_budget":"decision_complexity_budget_id",
        "search_exposure":"search_exposure_manifest_id", "replication_reservation":"replication_reservation_manifest_id",
    }
    ids = {name: row[identity_fields[name]] for name, row in components.items()}
    sections: dict[str, Any] = {
        "authority_currentness":"CBSI_WP6_AUTHORITY_CURRENTNESS_MANIFEST_v0_1",
        "source_population":ids["source_population"], "c2_owner_generation":OWNER_GENERATION,
        "c2e_reference_pack":{"pack_id":ACTIVE_PACK,"pack_sha256":ACTIVE_PACK_SHA256},
        "b0_projection":ids["b0_projection"], "comparator_registry":"CBS_COMPARATOR_REGISTRY_v0_1",
        "implementation_identity":"CBSI_WP6_ALGORITHM_REVIEW_FRONTIER_CANDIDATE_v0_1",
        "input_projections":ids["input_projections"], "support_evaluability":"CBSI_WP2_SUPPORT_MANIFESTS_v0_1",
        "parameter_surfaces":ids["method_surface"], "tolerance_grid":ids["tolerance_representation_context"],
        "representation_graph":ids["tolerance_representation_context"],
        "context_partitions":ids["tolerance_representation_context"],
        "evaluation_universe":"ALL_MANIFEST_BOUND_OWNER_OPPORTUNITIES_FORMED_BEFORE_DETECTION_COUNT_CONSERVATION_REQUIRED",
        "estimands":["REFERENCE_BOUNDARY_AUDIT","CONSENSUS_BOUNDARY_DISCOVERY"],
        "region_correspondence":"WP4_REGION_FIRST_DIRECTIONAL_ONE_TO_ONE_SPLIT_MERGE_UNMATCHED_AMBIGUOUS",
        "dependence_hierarchy":"METHOD_FAMILY_THEN_DEPENDENCE_CLUSTER_DUPLICATE_INVARIANT_NO_VOTE",
        "null_controls":ids["null_controls"],
        "primary_inferential_procedure":"DETERMINISTIC_TYPED_ALL_SURFACES_NO_BEST_RESULT_SELECTION_NO_SCALAR_ESTIMATOR",
        "endpoint":ids["endpoint"], "materiality":ids["materiality"],
        "specification_opportunity_ledger":ids["specification_opportunity_ledger"],
        "decision_complexity_budget":ids["decision_complexity_budget"], "search_exposure":ids["search_exposure"],
        "replication_reservation":ids["replication_reservation"],
        "prior_exposure":"CBSI_PRE_PLAN_EXPOSURE_MANIFEST_v0_1",
        "reviewer_binding":"CBSI_G2_ALG_REVIEWER_BINDING_REQUIREMENT_v0_1",
        "external_artifact_capacity":"CBSI_EXTERNAL_ARTIFACT_CAPACITY_BINDING_v0_1",
        "rollback":"FORWARD_SUPERSEDE_PRESERVE_ALL_BYTES_LEDGERS_AND_PARTIAL_EVIDENCE",
    }
    protocol = compile_development_protocol(generation=1, sections=sections)
    return {"components":components, "component_ids":ids, "protocol":protocol}
