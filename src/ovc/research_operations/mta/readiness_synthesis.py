from __future__ import annotations

from typing import Any, Mapping

ROUTES = (
    "/flow", "/translation", "/computability", "/context", "/markers",
    "/clusters", "/ro4-comparison", "/readiness", "/capacity",
)
ROUTE_SOURCE = {
    "/flow": "flow_summary",
    "/translation": "translation_summary",
    "/computability": "computability_summary",
    "/context": "context_summary",
    "/markers": "marker_summary",
    "/clusters": "cluster_summary",
    "/ro4-comparison": "ro4_comparison",
    "/readiness": "readiness",
    "/capacity": "capacity",
}

class MTAWP7SynthesisError(ValueError):
    pass

def _require(condition: bool, marker: str) -> None:
    if not condition:
        raise MTAWP7SynthesisError(marker)

def validate_reference(reference: Mapping[str, Any]) -> dict[str, Any]:
    _require(reference.get("schema") == "ovc-mta-wp7-readiness-synthesis-reference/v1", "REFERENCE_SCHEMA_MISMATCH")
    _require((reference.get("programme_id"), reference.get("packet_id"), reference.get("gate_id")) == ("OVC-MTA-v0.2", "MTA-WP7", "MTA-G7"), "REFERENCE_IDENTITY_MISMATCH")
    routes = reference.get("route_registry")
    _require(isinstance(routes, list), "ROUTE_REGISTRY_MISSING")
    observed = tuple(item.get("route") for item in routes if isinstance(item, Mapping))
    _require(observed == ROUTES, "ROUTE_SET_OR_ORDER_MISMATCH")
    readiness = reference.get("readiness")
    _require(isinstance(readiness, Mapping) and set(readiness) == {"clock", "c2e", "c2_5", "c3"}, "READINESS_DOMAINS_MISMATCH")
    _require(readiness["clock"].get("recommended_decision") == "PASS", "CLOCK_RECOMMENDATION_MISMATCH")
    _require(readiness["c2e"].get("recommended_decision") == "PASS", "C2E_RECOMMENDATION_MISMATCH")
    _require(readiness["c2_5"].get("recommended_decision") == "PASS", "C2_5_RECOMMENDATION_MISMATCH")
    _require(readiness["c3"].get("recommended_decision") == "DEFER", "C3_RECOMMENDATION_MISMATCH")
    assessments = readiness["c2_5"].get("rule_assessments")
    _require(isinstance(assessments, Mapping) and len(assessments) == 8, "C2_5_RULE_ACCOUNTING_MISMATCH")
    _require(assessments["LOCAL_PARENT_CONFLICT"]["disposition"] == "BLOCK_NOT_EVALUABLE", "CROSS_SCALE_RULE_ESCAPE")
    _require(assessments["ALIGNMENT_GAINED"]["disposition"] == "BLOCK_NOT_EVALUABLE", "CROSS_SCALE_RULE_ESCAPE")
    _require(assessments["RETURN_INSIDE"]["disposition"] == "DEFER_ZERO_FIRES", "ZERO_FIRE_RULE_ESCAPE")
    _require(assessments["COMPRESSION_TO_DISPLACEMENT"]["disposition"] == "DEFER_ZERO_FIRES", "ZERO_FIRE_RULE_ESCAPE")
    comp = reference.get("computability_summary")
    _require(comp["rule_attempts"] == comp["rule_level_evaluable"] + comp["rule_level_not_evaluable"], "RULE_ATTEMPT_ACCOUNTING_MISMATCH")
    _require(comp["parent_usable_target_resolutions"] == 615 and comp["parent_target_resolutions"] == 4072, "PARENT_USABILITY_MISMATCH")
    clusters = reference.get("cluster_summary")
    _require(clusters["occurrence_count"] == 1779, "OCCURRENCE_COUNT_MISMATCH")
    _require(clusters["sensitivity_counts"]["ROBUST"] == 0, "ROBUSTNESS_MISMATCH")
    ro4 = reference.get("ro4_comparison")
    _require(ro4.get("direct_comparison_status") == "NOT_DETERMINABLE", "RO4_SEPARATION_MISMATCH")
    _require(ro4.get("cross_programme_inconsistency") == "NOT_ESTABLISHED", "RO4_INCONSISTENCY_OVERCLAIM")
    capacity = reference.get("capacity")
    _require(capacity.get("within_artifact_limit") is True and capacity.get("capacity_exceeded_incidents") == 0, "CAPACITY_CONTRACT_FAILURE")
    authority = reference.get("authority")
    denied = {
        "clock_or_continuity_change": "DENIED",
        "formula_threshold_change": "DENIED",
        "marker_or_cluster_semantic_promotion": "DENIED",
        "model_family_candidate_selector_change": "DENIED",
        "c2e_c2_5_c3_activation": "DENIED",
        "validation_consumption": "DENIED",
        "r2_publication": "DENIED",
        "probability_risk_exposure_execution": "NONE",
        "research_write": "DENIED",
    }
    for key, expected in denied.items():
        _require(authority.get(key) == expected, f"AUTHORITY_ESCAPE:{key}")
    _require(reference.get("qa_recommendation") == "PASS_WITH_MATERIAL_FINDINGS", "QA_NOT_PASS")
    _require(reference.get("operator_gate_required_after_g7") is True, "G8_STOP_MISSING")
    return {
        "status": "PASS",
        "routes": len(ROUTES),
        "readiness": {key: readiness[key]["recommended_decision"] for key in ("clock", "c2e", "c2_5", "c3")},
        "operator_gate": "MTA-G8",
    }

def route_payload(reference: Mapping[str, Any], route: str) -> dict[str, Any]:
    validate_reference(reference)
    _require(route in ROUTE_SOURCE, f"ROUTE_NOT_REGISTERED:{route}")
    source = ROUTE_SOURCE[route]
    registry = next(item for item in reference["route_registry"] if item["route"] == route)
    return {
        "route": route,
        "title": registry["title"],
        "status": "AVAILABLE_LOCAL_READ_ONLY",
        "source": source,
        "data": reference[source],
        "authority": reference["authority"],
    }

def validate_fixture(fixture: Mapping[str, Any]) -> dict[str, Any]:
    _require(fixture.get("schema") == "ovc-mta-wp7-route-fixture/v1", "FIXTURE_SCHEMA_MISMATCH")
    _require(tuple(fixture.get("valid_routes", ())) == ROUTES, "FIXTURE_ROUTE_MISMATCH")
    _require(not set(fixture.get("invalid_routes", ())) & set(ROUTES), "FIXTURE_INVALID_ROUTE_COLLISION")
    _require(fixture["expected_readiness"] == {"clock":"PASS","c2e":"PASS","c2_5":"PASS","c3":"DEFER"}, "FIXTURE_READINESS_MISMATCH")
    return {"status": "PASS", "routes": len(ROUTES)}
