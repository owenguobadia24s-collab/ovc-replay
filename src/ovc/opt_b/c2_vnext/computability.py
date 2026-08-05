"""Inactive, noncanonical computability and population accounting for C2 vNext.

CEAR-G9 authorises deterministic SHADOW_FROZEN_READ_ONLY implementation only.
Availability, computability, assurance, consumer eligibility and authority are
independent dimensions. This module does not activate a consumer, choose a
staleness threshold, apply a canonical overlap adjustment, mutate active C2,
publish, consume Validation, or exercise semantic, probability, risk, exposure,
trading or execution authority.
"""
from __future__ import annotations

import copy
import hashlib
import json
from collections import Counter, defaultdict
from typing import Any, Callable, Iterable, Mapping, Sequence

AUTHORITY = "SHADOW_FROZEN_READ_ONLY"
POLICY_ID = "C2.COMPUTABILITY.CONSUMER.POLICY.v1"
DEPENDENCY_GRAPH_ID = "C2.COMPUTABILITY.DEPENDENCY.GRAPH.v1"
DENOMINATOR_POLICY_ID = "C2.DENOMINATOR.ACCOUNTING.v1"
OVERLAP_POLICY_ID = "C2.OVERLAP.CLAIM_SPECIFIC.v1"

EDGE_TYPES = {"REQUIRED", "OPTIONAL", "WARNING_ONLY", "ALTERNATIVE", "PROHIBITED"}
TERMINAL_DISPOSITIONS = {
    "COMPUTABLE",
    "NOT_COMPUTABLE",
    "NOT_APPLICABLE",
    "CENSORED",
    "CONFLICTED",
}
DEPENDENCY_SUCCESS = {"AVAILABLE", "COMPUTABLE", "ASSURED", "PRESENT"}
DEPENDENCY_FAILURE = {"UNAVAILABLE", "NOT_COMPUTABLE", "CENSORED", "CONFLICTED", "MISSING"}
PROHIBITED_FIELDS = {
    "outcome",
    "profit",
    "profitability",
    "mfe",
    "mae",
    "probability",
    "risk",
    "exposure",
    "trade",
    "trading",
    "execution",
    "validation",
    "active_selector",
    "canonical_selector",
    "semantic_label",
    "event_promotion",
    "episode_promotion",
}
COMPARABILITY_FIELDS = (
    "unit_type",
    "scope_definition",
    "instrument_scope",
    "side_handling",
    "release_id",
    "calendar_id",
    "clock_and_lattice_profile",
    "dependency_graph_id",
    "consumer_policy_id",
    "eligibility_policy_version",
    "denominator_definition",
    "overlap_policy_id",
    "censor_conflict_treatment",
)


class ComputabilityError(ValueError):
    """Raised when the frozen CEAR-G9 contract is violated."""


def _require(condition: bool, marker: str) -> None:
    if not condition:
        raise ComputabilityError(marker)


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _digest(prefix: str, value: Any) -> str:
    return f"{prefix}.{hashlib.sha256(_canonical(value)).hexdigest()[:24]}"


def _scan_prohibited(value: Any, path: str = "$") -> None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            if str(key).lower() in PROHIBITED_FIELDS:
                raise ComputabilityError(f"PROHIBITED_FIELD:{path}.{key}")
            _scan_prohibited(item, f"{path}.{key}")
    elif isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            _scan_prohibited(item, f"{path}[{index}]")


def _dependency_status(value: Mapping[str, Any]) -> str:
    status = str(value.get("status", "MISSING")).upper()
    return status


def evaluate_component(
    *,
    component_id: str,
    profile_id: str,
    unit_id: str,
    as_of_time: str,
    dependency_edges: Sequence[Mapping[str, Any]],
    dependency_results: Mapping[str, Mapping[str, Any]],
    applicable: bool = True,
    requested: bool = True,
    censored: bool = False,
    conflict_reason_codes: Sequence[str] = (),
    assurance_status: str = "NOT_ASSESSED",
    source_ids: Sequence[str] = (),
    age_evidence: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Evaluate technical computability without selecting a consumer.

    Failures propagate only through exact declared edges. Optional and warning
    edges never block a raw component. ALTERNATIVE edges are grouped by an
    explicit ``group_id`` and require at least one successful member.
    """
    _require(bool(component_id), "COMPONENT_ID_REQUIRED")
    _require(bool(profile_id), "PROFILE_ID_REQUIRED")
    _require(bool(unit_id), "UNIT_ID_REQUIRED")
    _require(bool(as_of_time), "AS_OF_TIME_REQUIRED")
    _scan_prohibited(dependency_edges)
    _scan_prohibited(dependency_results)
    _scan_prohibited(age_evidence or {})

    edge_ids: set[str] = set()
    normalized_edges: list[dict[str, Any]] = []
    required_failures: list[str] = []
    prohibited_present: list[str] = []
    warnings: list[str] = []
    alternative_groups: dict[str, list[str]] = defaultdict(list)
    alternative_success: dict[str, list[str]] = defaultdict(list)
    dependency_evidence: list[dict[str, Any]] = []

    for raw_edge in dependency_edges:
        edge = copy.deepcopy(dict(raw_edge))
        dependency_id = str(edge.get("dependency_id", ""))
        edge_type = str(edge.get("edge_type", "")).upper()
        _require(bool(dependency_id), "DEPENDENCY_ID_REQUIRED")
        _require(dependency_id not in edge_ids, "DUPLICATE_DEPENDENCY_ID")
        _require(edge_type in EDGE_TYPES, "UNKNOWN_DEPENDENCY_EDGE_TYPE")
        edge_ids.add(dependency_id)
        edge["dependency_id"] = dependency_id
        edge["edge_type"] = edge_type
        result = copy.deepcopy(dict(dependency_results.get(dependency_id, {"status": "MISSING"})))
        status = _dependency_status(result)
        present = status not in {"MISSING", "UNAVAILABLE", "NOT_COMPUTABLE", "NOT_APPLICABLE"}
        successful = status in DEPENDENCY_SUCCESS
        evidence = {
            "dependency_id": dependency_id,
            "edge_type": edge_type,
            "status": status,
            "reason_codes": sorted({str(item) for item in result.get("reason_codes", [])}),
        }
        dependency_evidence.append(evidence)
        normalized_edges.append(edge)

        if edge_type == "REQUIRED" and not successful:
            required_failures.append(dependency_id)
        elif edge_type == "OPTIONAL" and not successful:
            warnings.append(f"OPTIONAL_DEPENDENCY_UNAVAILABLE:{dependency_id}")
        elif edge_type == "WARNING_ONLY" and not successful:
            warnings.append(f"WARNING_DEPENDENCY_UNAVAILABLE:{dependency_id}")
        elif edge_type == "PROHIBITED" and present:
            prohibited_present.append(dependency_id)
        elif edge_type == "ALTERNATIVE":
            group_id = str(edge.get("group_id", ""))
            _require(bool(group_id), "ALTERNATIVE_GROUP_ID_REQUIRED")
            alternative_groups[group_id].append(dependency_id)
            if successful:
                alternative_success[group_id].append(dependency_id)

    unsatisfied_groups = sorted(
        group_id for group_id in alternative_groups if not alternative_success[group_id]
    )
    reasons: list[str] = []
    if not requested:
        availability_status = "NOT_REQUESTED"
        computability_status = "NOT_APPLICABLE"
        reasons.append("NOT_REQUESTED")
    elif not applicable:
        availability_status = "AVAILABLE"
        computability_status = "NOT_APPLICABLE"
        reasons.append("NOT_APPLICABLE")
    elif conflict_reason_codes or prohibited_present:
        availability_status = "AVAILABLE"
        computability_status = "CONFLICTED"
        reasons.extend(str(item) for item in conflict_reason_codes)
        reasons.extend(f"PROHIBITED_DEPENDENCY_PRESENT:{item}" for item in prohibited_present)
    elif censored:
        availability_status = "AVAILABLE"
        computability_status = "CENSORED"
        reasons.append("SOURCE_CENSORED")
    elif required_failures or unsatisfied_groups:
        availability_status = "AVAILABLE"
        computability_status = "NOT_COMPUTABLE"
        reasons.extend(f"DEPENDENCY_NOT_COMPUTABLE:{item}" for item in sorted(required_failures))
        reasons.extend(f"ALTERNATIVE_GROUP_UNSATISFIED:{item}" for item in unsatisfied_groups)
    else:
        availability_status = "AVAILABLE"
        computability_status = "COMPUTABLE"

    body: dict[str, Any] = {
        "schema": "c2_computability_record/vnext-r1",
        "component_id": component_id,
        "profile_id": profile_id,
        "unit_id": unit_id,
        "as_of_time": as_of_time,
        "availability_status": availability_status,
        "computability_status": computability_status,
        "assurance_status": str(assurance_status).upper(),
        "consumer_policy_id": None,
        "consumer_eligibility_status": "NOT_EVALUATED",
        "authority_status": "UNAUTHORIZED",
        "dependency_graph_id": DEPENDENCY_GRAPH_ID,
        "dependency_edges": sorted(normalized_edges, key=lambda item: (item["edge_type"], item["dependency_id"])),
        "dependency_results": sorted(dependency_evidence, key=lambda item: item["dependency_id"]),
        "missing_dependency_ids": sorted(required_failures),
        "satisfied_alternative_groups": {
            key: sorted(value) for key, value in sorted(alternative_success.items()) if value
        },
        "reason_codes": sorted(set(reasons)),
        "warnings": sorted(set(warnings)),
        "age_evidence": copy.deepcopy(dict(age_evidence or {})),
        "source_ids": sorted({str(item) for item in source_ids}),
        "active": False,
        "canonical": False,
        "authority": AUTHORITY,
    }
    body["record_id"] = _digest("C2.COMPUTABILITY", body)
    body["content_sha256"] = hashlib.sha256(_canonical(body)).hexdigest()
    return body


def apply_consumer_policy(
    record: Mapping[str, Any],
    policy: Mapping[str, Any],
    *,
    consumer_authorized: bool = False,
) -> dict[str, Any]:
    """Apply one exact non-active consumer policy to one component record."""
    _scan_prohibited(policy)
    result = copy.deepcopy(dict(record))
    policy_id = str(policy.get("consumer_policy_id", ""))
    _require(bool(policy_id), "CONSUMER_POLICY_ID_REQUIRED")
    _require(policy_id != "ACTIVE", "ACTIVE_CONSUMER_POLICY_PROHIBITED")
    _require(policy.get("active") is False, "CONSUMER_POLICY_MUST_BE_INACTIVE")
    _require(policy.get("canonical") is False, "CONSUMER_POLICY_MUST_BE_NONCANONICAL")
    _require("numeric_staleness_threshold" not in policy, "NUMERIC_STALENESS_THRESHOLD_PROHIBITED")
    _require("freshness_threshold" not in policy, "NUMERIC_FRESHNESS_THRESHOLD_PROHIBITED")

    reasons = set(str(item) for item in result.get("reason_codes", []))
    eligibility = "ELIGIBLE"
    if result.get("computability_status") != "COMPUTABLE":
        eligibility = "INELIGIBLE"
        reasons.add("COMPONENT_NOT_COMPUTABLE")
    if bool(policy.get("assurance_required", False)) and result.get("assurance_status") != "ASSURED":
        eligibility = "INELIGIBLE"
        reasons.add("ASSURANCE_REQUIRED")
    required_age_dimensions = [str(item) for item in policy.get("required_age_dimensions", [])]
    age_evidence = result.get("age_evidence") or {}
    for dimension in required_age_dimensions:
        if dimension not in age_evidence:
            eligibility = "INELIGIBLE"
            reasons.add(f"AGE_EVIDENCE_UNAVAILABLE:{dimension}")
    if policy.get("staleness_policy_id") and not age_evidence:
        eligibility = "INELIGIBLE"
        reasons.add("AGE_EVIDENCE_UNAVAILABLE")
    if not consumer_authorized:
        eligibility = "INELIGIBLE"
        reasons.add("CONSUMER_UNAUTHORIZED")

    result["consumer_policy_id"] = policy_id
    result["consumer_eligibility_status"] = eligibility
    result["authority_status"] = "AUTHORIZED" if consumer_authorized else "UNAUTHORIZED"
    result["eligibility_policy_version"] = str(policy.get("version", "1"))
    result["staleness_policy_id"] = policy.get("staleness_policy_id")
    result["reason_codes"] = sorted(reasons)
    result["active"] = False
    result["canonical"] = False
    result["authority"] = AUTHORITY
    result.pop("content_sha256", None)
    result["record_id"] = _digest("C2.CONSUMER.ELIGIBILITY", result)
    result["content_sha256"] = hashlib.sha256(_canonical(result)).hexdigest()
    return result


def build_denominator_record(
    records: Sequence[Mapping[str, Any]],
    *,
    scope_id: str,
    scope_definition: str,
    unit_type: str,
    consumer_policy_id: str,
    overlap_policy_id: str = OVERLAP_POLICY_ID,
    numerator_selector: Callable[[Mapping[str, Any]], bool] | None = None,
    denominator_selector: Callable[[Mapping[str, Any]], bool] | None = None,
    release_id: str = "SHADOW",
    calendar_id: str = "OVC.CALENDAR",
    clock_and_lattice_profile: str = "DECLARED",
    instrument_scope: str = "DECLARED",
    side_handling: str = "SEPARATE",
    censor_conflict_treatment: str = "EXCLUDE_FROM_DENOMINATOR_REPORT_SEPARATELY",
) -> dict[str, Any]:
    """Build explicit population accounting without silent row removal."""
    _require(bool(scope_id), "SCOPE_ID_REQUIRED")
    _require(bool(scope_definition), "SCOPE_DEFINITION_REQUIRED")
    _require(unit_type in {"OBSERVATION", "TRANSITION_PAIR", "OBJECT_TRACK", "WINDOW", "BUNDLE", "RELATION", "DETECTOR_OUTPUT"}, "UNSUPPORTED_UNIT_TYPE")
    _require(bool(consumer_policy_id), "CONSUMER_POLICY_ID_REQUIRED")
    _require(bool(overlap_policy_id), "OVERLAP_POLICY_ID_REQUIRED")
    rows = [copy.deepcopy(dict(item)) for item in records]
    ids = [str(item.get("record_id", item.get("unit_id", ""))) for item in rows]
    _require(all(ids), "RECORD_OR_UNIT_ID_REQUIRED")
    _require(len(ids) == len(set(ids)), "DUPLICATE_POPULATION_UNIT")

    population_count = len(rows)
    requested_count = sum(item.get("availability_status") != "NOT_REQUESTED" for item in rows)
    not_requested_count = population_count - requested_count
    not_applicable_count = sum(item.get("computability_status") == "NOT_APPLICABLE" and item.get("availability_status") != "NOT_REQUESTED" for item in rows)
    applicable_rows = [
        item for item in rows
        if item.get("availability_status") != "NOT_REQUESTED" and item.get("computability_status") != "NOT_APPLICABLE"
    ]
    applicable_count = len(applicable_rows)
    computable_count = sum(item.get("computability_status") == "COMPUTABLE" for item in applicable_rows)
    not_computable_count = sum(item.get("computability_status") == "NOT_COMPUTABLE" for item in applicable_rows)
    censored_count = sum(item.get("computability_status") == "CENSORED" for item in applicable_rows)
    conflicted_count = sum(item.get("computability_status") == "CONFLICTED" for item in applicable_rows)
    _require(
        applicable_count == computable_count + not_computable_count + censored_count + conflicted_count,
        "TERMINAL_DISPOSITION_PARTITION_MISMATCH",
    )
    available_count = sum(item.get("availability_status") == "AVAILABLE" for item in rows)
    assured_count = sum(item.get("assurance_status") == "ASSURED" for item in rows)
    eligible_rows = [item for item in rows if item.get("consumer_eligibility_status") == "ELIGIBLE"]
    eligible_count = len(eligible_rows)
    _require(eligible_count <= computable_count, "ELIGIBLE_EXCEEDS_COMPUTABLE")
    denominator_selector = denominator_selector or (lambda item: item.get("consumer_eligibility_status") == "ELIGIBLE")
    numerator_selector = numerator_selector or (lambda item: bool(item.get("numerator_member", False)))
    included_rows = [item for item in rows if denominator_selector(item)]
    numerator_rows = [item for item in included_rows if numerator_selector(item)]
    included_count = len(included_rows)
    denominator_count = included_count
    numerator_count = len(numerator_rows)
    _require(included_count <= eligible_count, "INCLUDED_EXCEEDS_ELIGIBLE")
    _require(numerator_count <= denominator_count, "NUMERATOR_EXCEEDS_DENOMINATOR")

    counts = {
        "population_count": population_count,
        "requested_count": requested_count,
        "not_requested_count": not_requested_count,
        "applicable_count": applicable_count,
        "not_applicable_count": not_applicable_count,
        "available_count": available_count,
        "computable_count": computable_count,
        "not_computable_count": not_computable_count,
        "censored_count": censored_count,
        "conflicted_count": conflicted_count,
        "assured_count": assured_count,
        "eligible_count": eligible_count,
        "included_count": included_count,
        "numerator_count": numerator_count,
        "denominator_count": denominator_count,
    }
    body: dict[str, Any] = {
        "schema": "c2_denominator_record/vnext-r1",
        "scope_id": scope_id,
        "scope_definition": scope_definition,
        "unit_type": unit_type,
        "consumer_policy_id": consumer_policy_id,
        "dependency_graph_id": DEPENDENCY_GRAPH_ID,
        "eligibility_policy_version": "1",
        "denominator_definition": "EXACT_CONSUMER_ELIGIBLE_INCLUDED_UNITS",
        "numerator_definition": "EXACT_INCLUDED_UNITS_MATCHING_DECLARED_NUMERATOR_SELECTOR",
        "overlap_policy_id": overlap_policy_id,
        "censor_conflict_treatment": censor_conflict_treatment,
        "instrument_scope": instrument_scope,
        "side_handling": side_handling,
        "release_id": release_id,
        "calendar_id": calendar_id,
        "clock_and_lattice_profile": clock_and_lattice_profile,
        "counts": counts,
        "population_unit_ids": sorted(ids),
        "included_unit_ids": sorted(str(item.get("record_id", item.get("unit_id"))) for item in included_rows),
        "numerator_unit_ids": sorted(str(item.get("record_id", item.get("unit_id"))) for item in numerator_rows),
        "partition_checks": {
            "population_equals_requested_plus_not_requested": population_count == requested_count + not_requested_count,
            "requested_equals_applicable_plus_not_applicable": requested_count == applicable_count + not_applicable_count,
            "applicable_equals_terminal_dispositions": applicable_count == computable_count + not_computable_count + censored_count + conflicted_count,
            "eligible_lte_computable": eligible_count <= computable_count,
            "included_lte_eligible": included_count <= eligible_count,
            "numerator_lte_denominator": numerator_count <= denominator_count,
        },
        "rate": None if denominator_count == 0 else numerator_count / denominator_count,
        "raw_counts_separate_from_rate": True,
        "active": False,
        "canonical": False,
        "authority": AUTHORITY,
    }
    _require(all(body["partition_checks"].values()), "DENOMINATOR_RECONCILIATION_FAILED")
    body["denominator_record_id"] = _digest("C2.DENOMINATOR", body)
    body["content_sha256"] = hashlib.sha256(_canonical(body)).hexdigest()
    return body


def build_overlap_report(
    raw_unit_ids: Sequence[str],
    clusters: Sequence[Mapping[str, Any]],
    *,
    claim_id: str,
    unit_type: str,
    cluster_policy_id: str,
) -> dict[str, Any]:
    """Retain raw units and expose claim-specific cluster membership.

    This function reports cluster counts only. It never chooses canonical
    weights, deduplicates the raw population or produces a numerical adjustment.
    """
    _require(bool(claim_id), "CLAIM_ID_REQUIRED")
    _require(bool(cluster_policy_id), "CLUSTER_POLICY_ID_REQUIRED")
    raw = [str(item) for item in raw_unit_ids]
    _require(all(raw), "RAW_UNIT_ID_REQUIRED")
    _require(len(raw) == len(set(raw)), "DUPLICATE_RAW_UNIT_ID")
    raw_set = set(raw)
    seen_clusters: set[str] = set()
    normalized: list[dict[str, Any]] = []
    memberships: Counter[str] = Counter()
    for value in clusters:
        cluster = copy.deepcopy(dict(value))
        cluster_id = str(cluster.get("cluster_id", ""))
        cluster_type = str(cluster.get("cluster_type", ""))
        members = sorted({str(item) for item in cluster.get("member_unit_ids", [])})
        _require(bool(cluster_id), "CLUSTER_ID_REQUIRED")
        _require(cluster_id not in seen_clusters, "DUPLICATE_CLUSTER_ID")
        _require(cluster_type in {"SHARED_OBSERVATION", "SHARED_WINDOW", "SHARED_OBJECT_TRACK", "SHARED_BUNDLE", "BID_ASK_PAIR", "SHARED_EPISODE"}, "UNKNOWN_CLUSTER_TYPE")
        _require(bool(members), "EMPTY_CLUSTER_PROHIBITED")
        _require(set(members).issubset(raw_set), "CLUSTER_MEMBER_OUTSIDE_RAW_POPULATION")
        if cluster_type == "SHARED_EPISODE":
            _require(cluster.get("episode_authority") == "SEPARATELY_AUTHORIZED", "SHARED_EPISODE_AUTHORITY_REQUIRED")
        seen_clusters.add(cluster_id)
        memberships.update(members)
        normalized.append({
            "cluster_id": cluster_id,
            "cluster_type": cluster_type,
            "member_unit_ids": members,
            "claim_id": claim_id,
            "unit_type": unit_type,
            "cluster_policy_id": cluster_policy_id,
        })
    body: dict[str, Any] = {
        "schema": "c2_overlap_report/vnext-r1",
        "claim_id": claim_id,
        "unit_type": unit_type,
        "cluster_policy_id": cluster_policy_id,
        "raw_unit_ids": sorted(raw),
        "raw_unit_count": len(raw),
        "cluster_count": len(normalized),
        "clustered_unique_unit_count": len(memberships),
        "unclustered_unit_ids": sorted(raw_set - set(memberships)),
        "multi_cluster_unit_ids": sorted(item for item, count in memberships.items() if count > 1),
        "clusters": sorted(normalized, key=lambda item: item["cluster_id"]),
        "canonical_weighting_selected": False,
        "canonical_deduplication_selected": False,
        "numeric_adjustment_selected": False,
        "raw_population_mutated": False,
        "active": False,
        "canonical": False,
        "authority": AUTHORITY,
    }
    body["overlap_report_id"] = _digest("C2.OVERLAP", body)
    body["content_sha256"] = hashlib.sha256(_canonical(body)).hexdigest()
    return body


def compare_population_records(left: Mapping[str, Any], right: Mapping[str, Any]) -> dict[str, Any]:
    """Fail closed when denominator or overlap bases differ."""
    mismatches = [field for field in COMPARABILITY_FIELDS if left.get(field) != right.get(field)]
    body = {
        "schema": "c2_population_comparison/vnext-r1",
        "left_id": left.get("denominator_record_id"),
        "right_id": right.get("denominator_record_id"),
        "status": "COMPARABLE" if not mismatches else "NOT_COMPARABLE",
        "mismatch_fields": sorted(mismatches),
        "reason_codes": sorted(f"POLICY_OR_UNIT_MISMATCH:{field}" for field in mismatches),
        "active": False,
        "canonical": False,
        "authority": AUTHORITY,
    }
    body["comparison_id"] = _digest("C2.POPULATION.COMPARISON", body)
    body["content_sha256"] = hashlib.sha256(_canonical(body)).hexdigest()
    return body


def project_legacy_quality(records: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Create a transparent, non-governing legacy compatibility projection."""
    statuses = Counter(str(item.get("computability_status", "UNKNOWN")) for item in records)
    body: dict[str, Any] = {
        "schema": "c2_legacy_quality_compatibility_projection/vnext-r1",
        "source_record_ids": sorted(str(item.get("record_id", "")) for item in records),
        "component_status_counts": dict(sorted(statuses.items())),
        "source_reason_codes": sorted({
            str(reason)
            for item in records
            for reason in item.get("reason_codes", [])
        }),
        "global_quality_status": None,
        "governing": False,
        "may_drive_eligibility": False,
        "may_drive_denominator_inclusion": False,
        "may_hide_component_status": False,
        "active": False,
        "canonical": False,
        "authority": AUTHORITY,
    }
    body["projection_id"] = _digest("C2.LEGACY.QUALITY", body)
    body["content_sha256"] = hashlib.sha256(_canonical(body)).hexdigest()
    return body
