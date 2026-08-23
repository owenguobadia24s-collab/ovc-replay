from __future__ import annotations

from collections.abc import Mapping, Sequence
import json
from pathlib import Path
from typing import Any

from ovc.research_operations.canonical import canonical_sha256

from .lifecycle import DEMAND_STATES


_DEMAND_REGISTRY_PATH = (
    Path(__file__).resolve().parents[4]
    / "registries/research_operations/p1cdi/demand_registry.json"
)
_FORBIDDEN_ACTUATION_TARGETS = (
    "DMRP_EXECUTION",
    "IROF_EXECUTION",
    "DSAI_RUN_CONTINUE",
    "SOURCE_REPLAY",
    "PROGRAMME_STATE_MUTATION",
    "TASK_CREATION",
)
_GAP_TO_DEMAND = {
    "REPLICATION_NOT_ATTEMPTED_OR_FAILED": "REPLICATION",
    "SINGLE_REPRESENTATION_ONLY": "ALTERNATE_REPRESENTATION",
    "DEPENDENCE_INCOMPLETE": "INDEPENDENCE_ASSESSMENT",
    "DENOMINATOR_UNKNOWN": "DENOMINATOR_RESOLUTION",
    "CAPACITY_INCOMPLETE": "CAPACITY_COMPLETION",
    "CURRENT_STACK_CANNOT_ANSWER": "MISSING_INFORMATION",
    "STACK_SUFFICIENCY_UNRESOLVED": "STACK_SUFFICIENCY_REVIEW",
}


def _load_registry() -> dict[str, Any]:
    value = json.loads(_DEMAND_REGISTRY_PATH.read_text(encoding="utf-8"))
    if value.get("schema") != "p1cdi-demand-registry/v0.1" or value.get("status") != "CLOSED":
        raise RuntimeError("P1CDI demand registry is not the frozen closed v0.1 registry")
    values = value.get("values")
    if type(values) is not list or not values or len(values) != len(set(values)):
        raise RuntimeError("P1CDI demand registry values are invalid")
    if value.get("route_authority") != "ADVISORY_ONLY" or value.get("actuation") != "DENIED":
        raise RuntimeError("P1CDI demand registry must remain advisory and non-actuating")
    return value


_DEMAND_REGISTRY = _load_registry()
DEMAND_TYPES = tuple(_DEMAND_REGISTRY["values"])


def _exact_string(value: Any, name: str) -> str:
    if type(value) is not str or not value:
        raise ValueError(f"{name} must be a non-empty string")
    return value


def _refs(value: Sequence[str], name: str, *, allow_empty: bool = True) -> list[str]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise ValueError(f"{name} must be a sequence")
    rows = [_exact_string(item, name) for item in value]
    if not allow_empty and not rows:
        raise ValueError(f"{name} must be non-empty")
    if len(rows) != len(set(rows)):
        raise ValueError(f"{name} must not contain duplicates")
    return sorted(rows)


def _logical_id(prefix: str, body: Mapping[str, Any]) -> str:
    return f"p1:{prefix}:{canonical_sha256(body)}"


def build_discovery_demand(
    *,
    generation_refs: Sequence[str],
    demand_type: str,
    required_information: Sequence[str],
    source_evidence_refs: Sequence[str] = (),
    state: str = "OPEN",
    blockers: Sequence[str] = (),
) -> dict[str, Any]:
    dtype = _exact_string(demand_type, "demand_type")
    if dtype not in DEMAND_TYPES:
        raise ValueError(f"unknown P1CDI demand_type: {dtype}")
    demand_state = _exact_string(state, "state")
    if demand_state not in DEMAND_STATES:
        raise ValueError(f"unknown P1CDI demand state: {demand_state}")
    generations = _refs(generation_refs, "generation_refs", allow_empty=False)
    information = _refs(required_information, "required_information", allow_empty=False)
    evidence = _refs(source_evidence_refs, "source_evidence_refs")
    blocking = _refs(blockers, "blockers")
    identity = {
        "generation_refs": generations,
        "demand_type": dtype,
        "required_information": information,
    }
    return {
        "record_type": "P1DiscoveryDemand",
        "schema_version": "0.1",
        "demand_id": _logical_id("demand", identity),
        "generation_refs": generations,
        "demand_type": dtype,
        "state": demand_state,
        "source_evidence_refs": evidence,
        "required_information": information,
        "blockers": blocking,
        "authority_effect": "NONE",
    }


def build_gap_demand(
    *,
    condition: str,
    generation_refs: Sequence[str],
    required_information: Sequence[str],
    source_evidence_refs: Sequence[str] = (),
) -> dict[str, Any]:
    condition_name = _exact_string(condition, "condition")
    if condition_name not in _GAP_TO_DEMAND:
        raise ValueError(f"unregistered P1CDI gap condition: {condition_name}")
    return build_discovery_demand(
        generation_refs=generation_refs,
        demand_type=_GAP_TO_DEMAND[condition_name],
        required_information=required_information,
        source_evidence_refs=source_evidence_refs,
    )


def assess_demand_eligibility(
    *, demand: Mapping[str, Any], current_stack_result: str, reason_codes: Sequence[str] = ()
) -> dict[str, Any]:
    if demand.get("record_type") != "P1DiscoveryDemand" or demand.get("authority_effect") != "NONE":
        raise ValueError("a lawful P1DiscoveryDemand is required")
    result = _exact_string(current_stack_result, "current_stack_result")
    if result not in {"RESEARCHABLE", "NOT_RESEARCHABLE", "UNRESOLVED", "BLOCKED"}:
        raise ValueError("current_stack_result is outside the frozen eligibility vocabulary")
    reasons = _refs(reason_codes, "reason_codes")
    body = {"demand_id": _exact_string(demand.get("demand_id"), "demand_id"), "current_stack_result": result, "reason_codes": reasons}
    return {
        "record_type": "P1DemandEligibilityAssessment",
        "schema_version": "0.1",
        "assessment_id": _logical_id("eligibility", body),
        **body,
        "authority_effect": "NONE",
    }


def build_rccr_referral(
    *,
    demand: Mapping[str, Any],
    question: str,
    source_frontier_ref: str,
    rccr_owner_ref: str,
    rccr_result_ref: str | None = None,
) -> dict[str, Any]:
    if demand.get("record_type") != "P1DiscoveryDemand" or demand.get("authority_effect") != "NONE":
        raise ValueError("a lawful P1DiscoveryDemand is required")
    if demand.get("demand_type") not in {"MISSING_INFORMATION", "STACK_SUFFICIENCY_REVIEW"}:
        raise ValueError("RCCR referral requires a missing-information or stack-sufficiency demand")
    result_ref = None if rccr_result_ref is None else _exact_string(rccr_result_ref, "rccr_result_ref")
    body = {
        "demand_id": _exact_string(demand.get("demand_id"), "demand_id"),
        "question": _exact_string(question, "question"),
        "required_information": _refs(demand.get("required_information", ()), "required_information", allow_empty=False),
        "source_frontier_ref": _exact_string(source_frontier_ref, "source_frontier_ref"),
        "rccr_owner_ref": _exact_string(rccr_owner_ref, "rccr_owner_ref"),
        "rccr_result_ref": result_ref,
    }
    identity = {key: value for key, value in body.items() if key != "rccr_result_ref"}
    return {
        "record_type": "P1RCCRReferral",
        "schema_version": "0.1",
        "referral_id": _logical_id("rccr-referral", identity),
        **body,
        "authority_effect": "NONE",
    }


def build_stack_sufficiency_binding(*, demand_id: str, rccr_result_ref: str) -> dict[str, Any]:
    body = {
        "demand_id": _exact_string(demand_id, "demand_id"),
        "rccr_result_ref": _exact_string(rccr_result_ref, "rccr_result_ref"),
    }
    return {
        "record_type": "P1StackSufficiencyBinding",
        "schema_version": "0.1",
        "binding_id": _logical_id("stack-binding", body),
        **body,
        "capability_activation": "DENIED",
        "authority_effect": "NONE",
    }


def validate_one_way_rccr_return(
    *, referral: Mapping[str, Any], binding: Mapping[str, Any]
) -> dict[str, Any]:
    if referral.get("record_type") != "P1RCCRReferral" or referral.get("authority_effect") != "NONE":
        raise ValueError("a lawful P1RCCRReferral is required")
    if binding.get("record_type") != "P1StackSufficiencyBinding" or binding.get("authority_effect") != "NONE":
        raise ValueError("a lawful P1StackSufficiencyBinding is required")
    if referral.get("demand_id") != binding.get("demand_id"):
        raise ValueError("RCCR return must bind the exact originating demand")
    result_ref = binding.get("rccr_result_ref")
    if not result_ref:
        raise ValueError("RCCR return must carry an exact owner result reference")
    if referral.get("rccr_result_ref") not in {None, result_ref}:
        raise ValueError("RCCR return conflicts with the referral result reference")
    if binding.get("capability_activation") != "DENIED":
        raise PermissionError("RCCR result cannot activate a P1CDI capability")
    return {
        "record_type": "P1RCCRReturnProjection",
        "schema_version": "0.1",
        "referral_id": referral["referral_id"],
        "demand_id": referral["demand_id"],
        "rccr_result_ref": result_ref,
        "direction": "P1CDI_TO_RCCR_TO_P1CDI",
        "source_scientific_mutation": "DENIED",
        "capability_activation": "DENIED",
        "decision_bearing": False,
        "authority_effect": "NONE",
    }


def build_discovery_work_recommendation(
    *, demand_refs: Sequence[str], reason_trace: Sequence[str]
) -> dict[str, Any]:
    demands = _refs(demand_refs, "demand_refs", allow_empty=False)
    reasons = _refs(reason_trace, "reason_trace", allow_empty=False)
    body = {"demand_refs": demands, "reason_trace": reasons}
    record = {
        "record_type": "P1DiscoveryWorkRecommendation",
        "schema_version": "0.1",
        "recommendation_id": _logical_id("next-discovery-work", body),
        **body,
        "route_class": "ADVISORY_ONLY",
        "actuation": "DENIED",
        "write_capability": "NONE",
        "authority_effect": "NONE",
    }
    assert_non_actuating(record)
    return record


def assert_non_actuating(recommendation: Mapping[str, Any]) -> None:
    required = {
        "record_type": "P1DiscoveryWorkRecommendation",
        "route_class": "ADVISORY_ONLY",
        "actuation": "DENIED",
        "write_capability": "NONE",
        "authority_effect": "NONE",
    }
    for field, expected in required.items():
        if recommendation.get(field) != expected:
            raise PermissionError(f"NEXT_DISCOVERY_WORK non-actuation violated at {field}")
    forbidden_fields = {
        "command",
        "executor",
        "task",
        "run_intent",
        "workflow_dispatch",
        "programme_state_write",
        "source_replay",
        "priority_score",
        "scientific_score",
    }
    present = sorted(forbidden_fields.intersection(recommendation))
    if present:
        raise PermissionError(f"NEXT_DISCOVERY_WORK contains forbidden actuation/scoring fields: {present}")


def build_non_actuation_proof(*, recommendation: Mapping[str, Any]) -> dict[str, Any]:
    assert_non_actuating(recommendation)
    recommendation_id = _exact_string(recommendation.get("recommendation_id"), "recommendation_id")
    body = {
        "recommendation_id": recommendation_id,
        "denied_targets": list(_FORBIDDEN_ACTUATION_TARGETS),
        "route_class": "ADVISORY_ONLY",
    }
    return {
        "record_type": "P1CDINonActuationProof",
        "schema_version": "0.1",
        "proof_id": _logical_id("non-actuation", body),
        **body,
        "result": "PASS_NEGATIVE_REACHABILITY",
        "authority_effect": "NONE",
    }
