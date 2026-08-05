"""Bottom-up, outcome-free functional discovery for C2 vNext.

This module implements deterministic research-candidate construction only. It
cannot activate a selector, event, episode, semantic label, release, consumer,
or outcome authority. Legacy rules may be compared only after bottom-up
candidate construction and never enter opportunity, fingerprint, motif,
functional-core, compilation, or scoring dependencies.
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
from collections import Counter, defaultdict
from typing import Any, Iterable, Mapping, Sequence

AUTHORITY = "PROVISIONAL_DISCOVERY_RESEARCH_ONLY"
DISCOVERY_STATUS = "CANDIDATE_METHOD_NOT_ADMITTED_PENDING_CEAR_G10"

OPPORTUNITY_OUTCOMES = {
    "APPLICABLE",
    "NOT_APPLICABLE",
    "COMPUTABLE",
    "NOT_EVALUABLE",
    "CENSORED",
    "CONFLICT",
    "POLICY_UNRESOLVED",
    "AUTHORITY_BLOCKED",
}
RULE_AST_OPERATORS = {
    "ALL_OF",
    "ANY_OF",
    "SEQUENCE",
    "WITHIN_N_OBSERVATIONS",
    "SAME_OBJECT",
    "MEASUREMENT_COMPARISON",
    "RELATION_TRANSITION",
    "RUN_LENGTH",
    "CONTEXT_AVAILABILITY",
}
PROHIBITED_FIELDS = {
    "outcome",
    "outcomes",
    "forward_outcome",
    "future_bar",
    "future_bars",
    "profit",
    "profitability",
    "pnl",
    "mfe",
    "mae",
    "return",
    "returns",
    "probability",
    "risk",
    "exposure",
    "trade",
    "trading",
    "execution",
    "validation",
    "validation_record",
    "retrospective_detector",
    "active_selector",
    "canonical_selector",
    "semantic_label",
    "event_label",
    "episode_label",
    "legacy_trigger",
    "candidatewindow",
    "candidate_window",
}
REQUIRED_VIEW_FIELDS = {
    "discovery_view_id",
    "version",
    "clocks",
    "sides",
    "frames",
    "object_families",
    "continuity_policy_id",
    "sequence_lengths",
    "required_measurements",
    "permitted_input_fields",
    "prohibited_input_fields",
    "active",
    "canonical",
}
REQUIRED_OPPORTUNITY_FIELDS = {
    "source_unit_id",
    "opportunity_type",
    "clock_id",
    "side",
    "frame_id",
    "object_family",
    "first_valid_time",
    "start_condition",
    "ordered_development",
    "ending_structural_effect",
    "duration_observations",
    "path_geometry",
    "object_ids",
    "context_ids",
    "missingness",
    "assurance",
}


class FunctionalDiscoveryError(ValueError):
    """Raised when the v0.3 Part 10 boundary is violated."""


def _require(condition: bool, marker: str) -> None:
    if not condition:
        raise FunctionalDiscoveryError(marker)


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _id(prefix: str, value: Any) -> str:
    return f"{prefix}.{_sha(value)[:24]}"


def _scan_prohibited(value: Any, path: str = "$") -> None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            key_lower = str(key).lower()
            if key_lower in PROHIBITED_FIELDS:
                raise FunctionalDiscoveryError(f"PROHIBITED_DISCOVERY_FIELD:{path}.{key}")
            _scan_prohibited(item, f"{path}.{key}")
    elif isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            _scan_prohibited(item, f"{path}[{index}]")


def _normalise_scalar(value: Any) -> str:
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            raise FunctionalDiscoveryError("NON_FINITE_FEATURE_VALUE")
        return format(value, ".12g")
    return str(value)


def validate_discovery_view(view: Mapping[str, Any]) -> dict[str, Any]:
    """Validate a versioned, inactive discovery-view definition."""
    result = copy.deepcopy(dict(view))
    _scan_prohibited(result)
    missing = sorted(REQUIRED_VIEW_FIELDS - set(result))
    _require(not missing, f"DISCOVERY_VIEW_FIELDS_MISSING:{','.join(missing)}")
    _require(result["active"] is False, "DISCOVERY_VIEW_MUST_BE_INACTIVE")
    _require(result["canonical"] is False, "DISCOVERY_VIEW_MUST_BE_NONCANONICAL")
    _require(bool(result["discovery_view_id"]), "DISCOVERY_VIEW_ID_REQUIRED")
    _require(bool(result["version"]), "DISCOVERY_VIEW_VERSION_REQUIRED")
    for field in ("clocks", "sides", "frames", "object_families", "sequence_lengths", "required_measurements"):
        values = result[field]
        _require(isinstance(values, list) and bool(values), f"DISCOVERY_VIEW_{field.upper()}_REQUIRED")
        _require(len(values) == len({_normalise_scalar(item) for item in values}), f"DISCOVERY_VIEW_{field.upper()}_DUPLICATE")
    permitted = {str(item) for item in result["permitted_input_fields"]}
    prohibited = {str(item).lower() for item in result["prohibited_input_fields"]}
    _require(REQUIRED_OPPORTUNITY_FIELDS.issubset(permitted), "DISCOVERY_VIEW_REQUIRED_INPUT_FIELDS_NOT_PERMITTED")
    _require(PROHIBITED_FIELDS.issubset(prohibited), "DISCOVERY_VIEW_PROHIBITED_FIELDS_INCOMPLETE")
    _require(not {item.lower() for item in permitted}.intersection(PROHIBITED_FIELDS), "DISCOVERY_VIEW_PERMITS_PROHIBITED_FIELD")
    result["clocks"] = sorted(str(item) for item in result["clocks"])
    result["sides"] = sorted(str(item) for item in result["sides"])
    result["frames"] = sorted(str(item) for item in result["frames"])
    result["object_families"] = sorted(str(item) for item in result["object_families"])
    result["sequence_lengths"] = sorted(int(item) for item in result["sequence_lengths"])
    result["required_measurements"] = sorted(str(item) for item in result["required_measurements"])
    result["permitted_input_fields"] = sorted(permitted)
    result["prohibited_input_fields"] = sorted(prohibited)
    result["authority"] = AUTHORITY
    result["method_status"] = DISCOVERY_STATUS
    result["content_sha256"] = _sha({key: value for key, value in result.items() if key != "content_sha256"})
    return result


def _derive_outcome(request: Mapping[str, Any]) -> tuple[str, list[str]]:
    reasons = sorted({str(item) for item in request.get("reason_codes", [])})
    if request.get("authority_status") == "UNAUTHORIZED":
        return "AUTHORITY_BLOCKED", reasons or ["CONSUMER_UNAUTHORIZED"]
    if request.get("policy_status") in {"UNRESOLVED", "MISSING"}:
        return "POLICY_UNRESOLVED", reasons or ["POLICY_UNRESOLVED"]
    if request.get("applicable") is False:
        return "NOT_APPLICABLE", reasons or ["NOT_APPLICABLE"]
    if request.get("conflicted") is True or request.get("computability_status") == "CONFLICTED":
        return "CONFLICT", reasons or ["CONFLICT"]
    if request.get("censored") is True or request.get("computability_status") == "CENSORED":
        return "CENSORED", reasons or ["CENSORED"]
    if request.get("computability_status") != "COMPUTABLE":
        return "NOT_EVALUABLE", reasons or ["NOT_COMPUTABLE"]
    if request.get("emit_applicable_only") is True:
        return "APPLICABLE", reasons
    return "COMPUTABLE", reasons


def build_opportunity_population(
    requests: Sequence[Mapping[str, Any]],
    discovery_view: Mapping[str, Any],
    *,
    registered_scope_id: str,
    input_manifest_sha256: str,
) -> dict[str, Any]:
    """Build exactly one explicit opportunity outcome per requested source unit."""
    view = validate_discovery_view(discovery_view)
    _require(bool(registered_scope_id), "REGISTERED_SCOPE_ID_REQUIRED")
    _require(len(input_manifest_sha256) == 64, "INPUT_MANIFEST_SHA256_REQUIRED")
    permitted = set(view["permitted_input_fields"])
    seen: set[str] = set()
    records: list[dict[str, Any]] = []
    for raw in requests:
        request = copy.deepcopy(dict(raw))
        _scan_prohibited(request)
        missing = sorted(REQUIRED_OPPORTUNITY_FIELDS - set(request))
        _require(not missing, f"OPPORTUNITY_FIELDS_MISSING:{','.join(missing)}")
        source_unit_id = str(request["source_unit_id"])
        _require(bool(source_unit_id), "SOURCE_UNIT_ID_REQUIRED")
        _require(source_unit_id not in seen, "DUPLICATE_SOURCE_UNIT_ID")
        seen.add(source_unit_id)
        unknown = sorted(set(request) - permitted - {
            "applicable", "computability_status", "authority_status", "policy_status",
            "conflicted", "censored", "reason_codes", "emit_applicable_only",
            "numerator_member", "overlap_cluster_ids", "matching_stratum",
        })
        _require(not unknown, f"OPPORTUNITY_UNKNOWN_INPUT_FIELDS:{','.join(unknown)}")
        _require(str(request["clock_id"]) in view["clocks"], "OPPORTUNITY_CLOCK_NOT_ADMITTED")
        _require(str(request["side"]) in view["sides"], "OPPORTUNITY_SIDE_NOT_ADMITTED")
        _require(str(request["frame_id"]) in view["frames"], "OPPORTUNITY_FRAME_NOT_ADMITTED")
        _require(str(request["object_family"]) in view["object_families"], "OPPORTUNITY_OBJECT_FAMILY_NOT_ADMITTED")
        ordered = request["ordered_development"]
        _require(isinstance(ordered, list), "ORDERED_DEVELOPMENT_MUST_BE_LIST")
        _require(len(ordered) in view["sequence_lengths"], "SEQUENCE_LENGTH_NOT_ADMITTED")
        outcome, reasons = _derive_outcome(request)
        _require(outcome in OPPORTUNITY_OUTCOMES, "UNKNOWN_OPPORTUNITY_OUTCOME")
        body: dict[str, Any] = {
            "schema": "c2_discovery_opportunity/vnext-r1",
            "discovery_view_id": view["discovery_view_id"],
            "discovery_view_version": view["version"],
            "registered_scope_id": registered_scope_id,
            "input_manifest_sha256": input_manifest_sha256,
            "source_unit_id": source_unit_id,
            "opportunity_type": str(request["opportunity_type"]),
            "clock_id": str(request["clock_id"]),
            "side": str(request["side"]),
            "frame_id": str(request["frame_id"]),
            "object_family": str(request["object_family"]),
            "first_valid_time": str(request["first_valid_time"]),
            "start_condition": copy.deepcopy(request["start_condition"]),
            "ordered_development": copy.deepcopy(ordered),
            "ending_structural_effect": copy.deepcopy(request["ending_structural_effect"]),
            "duration_observations": int(request["duration_observations"]),
            "path_geometry": copy.deepcopy(request["path_geometry"]),
            "object_ids": sorted({str(item) for item in request["object_ids"]}),
            "context_ids": sorted({str(item) for item in request["context_ids"]}),
            "missingness": copy.deepcopy(request["missingness"]),
            "assurance": copy.deepcopy(request["assurance"]),
            "opportunity_outcome": outcome,
            "reason_codes": reasons,
            "numerator_member": bool(request.get("numerator_member", False)),
            "overlap_cluster_ids": sorted({str(item) for item in request.get("overlap_cluster_ids", [])}),
            "matching_stratum": copy.deepcopy(request.get("matching_stratum", {})),
            "active": False,
            "canonical": False,
            "authority": AUTHORITY,
        }
        _scan_prohibited({key: value for key, value in body.items() if key not in {"opportunity_outcome"}})
        body["opportunity_id"] = _id("C2.OPPORTUNITY", body)
        body["content_sha256"] = _sha(body)
        records.append(body)
    records.sort(key=lambda item: (item["first_valid_time"], item["source_unit_id"], item["opportunity_id"]))
    counts = Counter(item["opportunity_outcome"] for item in records)
    population: dict[str, Any] = {
        "schema": "c2_discovery_opportunity_population/vnext-r1",
        "discovery_view_id": view["discovery_view_id"],
        "registered_scope_id": registered_scope_id,
        "input_manifest_sha256": input_manifest_sha256,
        "requested_count": len(requests),
        "record_count": len(records),
        "outcome_counts": {key: counts.get(key, 0) for key in sorted(OPPORTUNITY_OUTCOMES)},
        "records": records,
        "complete_accounting": len(requests) == len(records),
        "legacy_seed_count": 0,
        "outcome_dependency_count": 0,
        "active": False,
        "canonical": False,
        "authority": AUTHORITY,
    }
    _require(population["complete_accounting"], "OPPORTUNITY_ACCOUNTING_MISMATCH")
    population["population_id"] = _id("C2.OPPORTUNITY.POPULATION", population)
    population["content_sha256"] = _sha(population)
    return population


def _flatten_feature(prefix: str, value: Any, output: dict[str, str]) -> None:
    if isinstance(value, Mapping):
        for key in sorted(value):
            _flatten_feature(f"{prefix}.{key}" if prefix else str(key), value[key], output)
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _flatten_feature(f"{prefix}[{index}]", item, output)
    else:
        output[prefix] = _normalise_scalar(value)


def fingerprint_opportunity(opportunity: Mapping[str, Any], method_pack: Mapping[str, Any]) -> dict[str, Any]:
    """Create a neutral sequence fingerprint from one computable opportunity."""
    _scan_prohibited(method_pack)
    _require(opportunity.get("opportunity_outcome") == "COMPUTABLE", "FINGERPRINT_REQUIRES_COMPUTABLE_OPPORTUNITY")
    _require(method_pack.get("active") is False, "METHOD_PACK_MUST_BE_INACTIVE")
    _require(method_pack.get("canonical") is False, "METHOD_PACK_MUST_BE_NONCANONICAL")
    fingerprint_fields = [str(item) for item in method_pack.get("fingerprint_fields", [])]
    required = [
        "start_condition", "ordered_development", "ending_structural_effect",
        "duration_observations", "path_geometry", "object_ids", "context_ids",
        "missingness", "assurance",
    ]
    _require(set(required).issubset(fingerprint_fields), "METHOD_PACK_NEUTRAL_FINGERPRINT_FIELDS_INCOMPLETE")
    _require(not set(fingerprint_fields).intersection(PROHIBITED_FIELDS), "METHOD_PACK_FINGERPRINT_FIELD_PROHIBITED")
    features: dict[str, str] = {}
    for field in fingerprint_fields:
        _require(field in opportunity, f"FINGERPRINT_SOURCE_FIELD_MISSING:{field}")
        _flatten_feature(field, opportunity[field], features)
    tokens = [f"{key}={features[key]}" for key in sorted(features)]
    body: dict[str, Any] = {
        "schema": "c2_neutral_sequence_fingerprint/vnext-r1",
        "method_pack_id": str(method_pack["method_pack_id"]),
        "method_pack_version": str(method_pack["version"]),
        "opportunity_id": str(opportunity["opportunity_id"]),
        "source_unit_id": str(opportunity["source_unit_id"]),
        "clock_id": str(opportunity["clock_id"]),
        "side": str(opportunity["side"]),
        "frame_id": str(opportunity["frame_id"]),
        "object_family": str(opportunity["object_family"]),
        "first_valid_time": str(opportunity["first_valid_time"]),
        "features": features,
        "tokens": tokens,
        "token_count": len(tokens),
        "active": False,
        "canonical": False,
        "authority": AUTHORITY,
    }
    _scan_prohibited(body)
    body["fingerprint_id"] = _id("C2.FINGERPRINT", body)
    body["content_sha256"] = _sha(body)
    return body


def build_fingerprint_inventory(population: Mapping[str, Any], method_pack: Mapping[str, Any]) -> dict[str, Any]:
    fingerprints = [
        fingerprint_opportunity(item, method_pack)
        for item in population.get("records", [])
        if item.get("opportunity_outcome") == "COMPUTABLE"
    ]
    fingerprints.sort(key=lambda item: (item["first_valid_time"], item["fingerprint_id"]))
    body: dict[str, Any] = {
        "schema": "c2_fingerprint_inventory/vnext-r1",
        "population_id": population["population_id"],
        "method_pack_id": method_pack["method_pack_id"],
        "computable_opportunity_count": population["outcome_counts"].get("COMPUTABLE", 0),
        "fingerprint_count": len(fingerprints),
        "fingerprints": fingerprints,
        "complete_accounting": len(fingerprints) == population["outcome_counts"].get("COMPUTABLE", 0),
        "active": False,
        "canonical": False,
        "authority": AUTHORITY,
    }
    _require(body["complete_accounting"], "FINGERPRINT_ACCOUNTING_MISMATCH")
    body["inventory_id"] = _id("C2.FINGERPRINT.INVENTORY", body)
    body["content_sha256"] = _sha(body)
    return body


def extract_motifs(fingerprint_inventory: Mapping[str, Any], method_pack: Mapping[str, Any]) -> dict[str, Any]:
    """Group fingerprints by a preregistered deterministic token projection."""
    _scan_prohibited(method_pack)
    projection_prefixes = sorted(str(item) for item in method_pack.get("motif_projection_prefixes", []))
    _require(bool(projection_prefixes), "MOTIF_PROJECTION_PREFIXES_REQUIRED")
    minimum_support = int(method_pack.get("minimum_motif_support", 1))
    _require(minimum_support >= 1, "MINIMUM_MOTIF_SUPPORT_INVALID")
    groups: dict[tuple[str, ...], list[dict[str, Any]]] = defaultdict(list)
    for fingerprint in fingerprint_inventory.get("fingerprints", []):
        tokens = tuple(
            token for token in fingerprint["tokens"]
            if any(token.startswith(prefix) for prefix in projection_prefixes)
        )
        _require(bool(tokens), "MOTIF_PROJECTION_EMPTY")
        groups[tokens].append(fingerprint)
    motifs: list[dict[str, Any]] = []
    negatives: list[dict[str, Any]] = []
    for signature in sorted(groups):
        members = sorted(groups[signature], key=lambda item: item["fingerprint_id"])
        base = {
            "signature_tokens": list(signature),
            "member_fingerprint_ids": [item["fingerprint_id"] for item in members],
            "member_opportunity_ids": [item["opportunity_id"] for item in members],
            "support_count": len(members),
        }
        motif_id = _id("C2.MOTIF", base)
        if len(members) < minimum_support:
            negatives.append({
                "negative_id": _id("C2.MOTIF.NEGATIVE", base),
                "motif_candidate_id": motif_id,
                "reason_code": "INSUFFICIENT_SUPPORT",
                **base,
            })
            continue
        motifs.append({
            "schema": "c2_provisional_motif/vnext-r1",
            "motif_id": motif_id,
            "method_pack_id": method_pack["method_pack_id"],
            "signature_tokens": list(signature),
            "member_fingerprint_ids": base["member_fingerprint_ids"],
            "member_opportunity_ids": base["member_opportunity_ids"],
            "support_count": len(members),
            "medoid_fingerprint_id": members[0]["fingerprint_id"],
            "medoid_selection_rule": "LEXICOGRAPHIC_FIRST_WITHIN_EXACT_SIGNATURE",
            "provisional": True,
            "semantic_authority": "NONE",
            "active": False,
            "canonical": False,
            "authority": AUTHORITY,
        })
    body: dict[str, Any] = {
        "schema": "c2_motif_inventory/vnext-r1",
        "fingerprint_inventory_id": fingerprint_inventory["inventory_id"],
        "method_pack_id": method_pack["method_pack_id"],
        "motifs": motifs,
        "negative_candidates": negatives,
        "input_fingerprint_count": fingerprint_inventory["fingerprint_count"],
        "accounted_member_count": sum(item["support_count"] for item in motifs) + sum(item["support_count"] for item in negatives),
        "complete_accounting": fingerprint_inventory["fingerprint_count"] == sum(item["support_count"] for item in motifs) + sum(item["support_count"] for item in negatives),
        "active": False,
        "canonical": False,
        "authority": AUTHORITY,
    }
    _require(body["complete_accounting"], "MOTIF_ACCOUNTING_MISMATCH")
    body["inventory_id"] = _id("C2.MOTIF.INVENTORY", body)
    body["content_sha256"] = _sha(body)
    return body


def _jaccard_distance(left: Iterable[str], right: Iterable[str]) -> float:
    a, b = set(left), set(right)
    if not a and not b:
        return 0.0
    return 1.0 - len(a & b) / len(a | b)


def build_provisional_families(motif_inventory: Mapping[str, Any], method_pack: Mapping[str, Any]) -> dict[str, Any]:
    """Create deterministic provisional families using declared distance and order."""
    threshold = float(method_pack.get("family_distance_threshold", 0.0))
    _require(0.0 <= threshold <= 1.0, "FAMILY_DISTANCE_THRESHOLD_INVALID")
    motifs = sorted(motif_inventory.get("motifs", []), key=lambda item: item["motif_id"])
    unassigned = {item["motif_id"]: item for item in motifs}
    families: list[dict[str, Any]] = []
    while unassigned:
        medoid_id = sorted(unassigned)[0]
        medoid = unassigned.pop(medoid_id)
        members = [medoid]
        for motif_id in sorted(list(unassigned)):
            candidate = unassigned[motif_id]
            distance = _jaccard_distance(medoid["signature_tokens"], candidate["signature_tokens"])
            if distance <= threshold:
                members.append(unassigned.pop(motif_id))
        member_ids = sorted(item["motif_id"] for item in members)
        family_base = {
            "medoid_motif_id": medoid_id,
            "member_motif_ids": member_ids,
            "distance_threshold": threshold,
        }
        families.append({
            "schema": "c2_provisional_family/vnext-r1",
            "family_id": _id("C2.FAMILY", family_base),
            "method_pack_id": method_pack["method_pack_id"],
            "medoid_motif_id": medoid_id,
            "member_motif_ids": member_ids,
            "member_count": len(member_ids),
            "member_opportunity_ids": sorted({
                opportunity_id
                for item in members
                for opportunity_id in item["member_opportunity_ids"]
            }),
            "distance_threshold": threshold,
            "assignment_order": "LEXICOGRAPHIC_MEDOID_THEN_THRESHOLD",
            "outlier_motif_ids": [],
            "provisional": True,
            "semantic_authority": "NONE",
            "active": False,
            "canonical": False,
            "authority": AUTHORITY,
        })
    body: dict[str, Any] = {
        "schema": "c2_provisional_family_inventory/vnext-r1",
        "motif_inventory_id": motif_inventory["inventory_id"],
        "method_pack_id": method_pack["method_pack_id"],
        "families": sorted(families, key=lambda item: item["family_id"]),
        "motif_count": len(motifs),
        "assigned_motif_count": sum(item["member_count"] for item in families),
        "complete_accounting": len(motifs) == sum(item["member_count"] for item in families),
        "active": False,
        "canonical": False,
        "authority": AUTHORITY,
    }
    _require(body["complete_accounting"], "FAMILY_ACCOUNTING_MISMATCH")
    body["inventory_id"] = _id("C2.FAMILY.INVENTORY", body)
    body["content_sha256"] = _sha(body)
    return body


def extract_functional_cores(
    family_inventory: Mapping[str, Any],
    motif_inventory: Mapping[str, Any],
    fingerprint_inventory: Mapping[str, Any],
    method_pack: Mapping[str, Any],
) -> dict[str, Any]:
    """Extract inspectable functional-core matrices without semantic naming."""
    common_threshold = float(method_pack.get("common_component_frequency", 0.75))
    optional_threshold = float(method_pack.get("optional_component_frequency", 0.25))
    _require(0.0 <= optional_threshold <= common_threshold <= 1.0, "FUNCTIONAL_CORE_FREQUENCY_THRESHOLDS_INVALID")
    fingerprints = {item["fingerprint_id"]: item for item in fingerprint_inventory["fingerprints"]}
    motifs = {item["motif_id"]: item for item in motif_inventory["motifs"]}
    cores: list[dict[str, Any]] = []
    for family in family_inventory["families"]:
        member_fingerprint_ids = sorted({
            fingerprint_id
            for motif_id in family["member_motif_ids"]
            for fingerprint_id in motifs[motif_id]["member_fingerprint_ids"]
        })
        member_features = [fingerprints[item]["features"] for item in member_fingerprint_ids]
        feature_keys = sorted({key for feature_map in member_features for key in feature_map})
        matrix: list[dict[str, Any]] = []
        for key in feature_keys:
            values = Counter(feature_map.get(key, "__MISSING__") for feature_map in member_features)
            total = len(member_features)
            distinct = len(values)
            for value, count in sorted(values.items()):
                frequency = count / total
                if distinct == 1 and count == total:
                    classification = "INVARIANT"
                elif distinct > 1 and max(values.values()) / total < common_threshold:
                    classification = "CONTRADICTORY"
                elif frequency >= common_threshold:
                    classification = "COMMON"
                elif frequency >= optional_threshold:
                    classification = "OPTIONAL"
                else:
                    classification = "RARE"
                matrix.append({
                    "feature_key": key,
                    "feature_value": value,
                    "count": count,
                    "frequency": frequency,
                    "classification": classification,
                })
        base = {
            "family_id": family["family_id"],
            "member_fingerprint_ids": member_fingerprint_ids,
            "matrix": matrix,
        }
        cores.append({
            "schema": "c2_functional_core/vnext-r1",
            "functional_core_id": _id("C2.FUNCTIONAL.CORE", base),
            "family_id": family["family_id"],
            "method_pack_id": method_pack["method_pack_id"],
            "member_fingerprint_ids": member_fingerprint_ids,
            "member_opportunity_ids": sorted({
                fingerprints[item]["opportunity_id"] for item in member_fingerprint_ids
            }),
            "member_count": len(member_fingerprint_ids),
            "component_matrix": matrix,
            "classification_counts": dict(sorted(Counter(item["classification"] for item in matrix).items())),
            "semantic_name": None,
            "provisional": True,
            "active": False,
            "canonical": False,
            "authority": AUTHORITY,
        })
    body: dict[str, Any] = {
        "schema": "c2_functional_core_inventory/vnext-r1",
        "family_inventory_id": family_inventory["inventory_id"],
        "method_pack_id": method_pack["method_pack_id"],
        "functional_cores": sorted(cores, key=lambda item: item["functional_core_id"]),
        "family_count": len(family_inventory["families"]),
        "functional_core_count": len(cores),
        "complete_accounting": len(family_inventory["families"]) == len(cores),
        "active": False,
        "canonical": False,
        "authority": AUTHORITY,
    }
    _require(body["complete_accounting"], "FUNCTIONAL_CORE_ACCOUNTING_MISMATCH")
    body["inventory_id"] = _id("C2.FUNCTIONAL.CORE.INVENTORY", body)
    body["content_sha256"] = _sha(body)
    return body


def compile_rule_candidate(functional_core: Mapping[str, Any], method_pack: Mapping[str, Any]) -> dict[str, Any]:
    """Compile invariant/common components into a restricted, non-effective AST."""
    allowed_component_classes = set(method_pack.get("rule_component_classes", ["INVARIANT", "COMMON"]))
    _require(allowed_component_classes.issubset({"INVARIANT", "COMMON", "OPTIONAL", "RARE", "CONTRADICTORY"}), "RULE_COMPONENT_CLASS_INVALID")
    clauses = []
    for item in functional_core["component_matrix"]:
        if item["classification"] not in allowed_component_classes:
            continue
        if item["feature_value"] == "__MISSING__":
            continue
        clauses.append({
            "operator": "MEASUREMENT_COMPARISON",
            "feature_key": item["feature_key"],
            "comparison": "EQUALS",
            "value": item["feature_value"],
        })
    clauses.sort(key=lambda item: (item["feature_key"], item["value"]))
    _require(bool(clauses), "FUNCTIONAL_CORE_HAS_NO_COMPILABLE_COMPONENTS")
    ast = {"operator": "ALL_OF", "clauses": clauses}
    validate_rule_ast(ast)
    body: dict[str, Any] = {
        "schema": "c2_declarative_research_rule_candidate/vnext-r1",
        "functional_core_id": functional_core["functional_core_id"],
        "family_id": functional_core["family_id"],
        "method_pack_id": method_pack["method_pack_id"],
        "ast": ast,
        "source_opportunity_ids": functional_core["member_opportunity_ids"],
        "source_fingerprint_ids": functional_core["member_fingerprint_ids"],
        "first_valid_completion_rule": "AFTER_LAST_REQUIRED_SEQUENCE_COMPONENT_IS_FIRST_VALID",
        "active": False,
        "canonical": False,
        "selector_authority": "NONE",
        "event_authority": "NONE",
        "episode_authority": "NONE",
        "semantic_authority": "NONE",
        "outcome_authority": "NONE",
        "authority": AUTHORITY,
    }
    body["rule_candidate_id"] = _id("C2.RULE.CANDIDATE", body)
    body["content_sha256"] = _sha(body)
    return body


def validate_rule_ast(ast: Mapping[str, Any]) -> None:
    operator = str(ast.get("operator", ""))
    _require(operator in RULE_AST_OPERATORS, "RULE_AST_OPERATOR_NOT_ALLOWED")
    _scan_prohibited(ast)
    if operator in {"ALL_OF", "ANY_OF", "SEQUENCE"}:
        clauses = ast.get("clauses")
        _require(isinstance(clauses, list) and bool(clauses), "RULE_AST_CLAUSES_REQUIRED")
        for clause in clauses:
            validate_rule_ast(clause)
    elif operator == "WITHIN_N_OBSERVATIONS":
        _require(int(ast.get("n", 0)) > 0, "RULE_AST_WITHIN_N_INVALID")
        validate_rule_ast(ast.get("clause", {}))
    elif operator == "SAME_OBJECT":
        _require(bool(ast.get("object_id_field")), "RULE_AST_OBJECT_FIELD_REQUIRED")
    elif operator == "MEASUREMENT_COMPARISON":
        _require(bool(ast.get("feature_key")), "RULE_AST_FEATURE_KEY_REQUIRED")
        _require(ast.get("comparison") in {"EQUALS", "NOT_EQUALS", "GT", "GTE", "LT", "LTE"}, "RULE_AST_COMPARISON_INVALID")
        _require("value" in ast, "RULE_AST_COMPARISON_VALUE_REQUIRED")
    elif operator == "RELATION_TRANSITION":
        _require(bool(ast.get("object_id")), "RULE_AST_RELATION_OBJECT_REQUIRED")
        _require(bool(ast.get("from_topology")) and bool(ast.get("to_topology")), "RULE_AST_RELATION_TOPOLOGY_REQUIRED")
    elif operator == "RUN_LENGTH":
        _require(int(ast.get("minimum", 0)) > 0, "RULE_AST_RUN_LENGTH_INVALID")
    elif operator == "CONTEXT_AVAILABILITY":
        _require(ast.get("required") in {True, False}, "RULE_AST_CONTEXT_REQUIRED_FLAG")


def _compare(left: str, operator: str, right: Any) -> bool:
    if operator == "EQUALS":
        return left == _normalise_scalar(right)
    if operator == "NOT_EQUALS":
        return left != _normalise_scalar(right)
    try:
        left_number = float(left)
        right_number = float(right)
    except (TypeError, ValueError) as exc:
        raise FunctionalDiscoveryError("RULE_NUMERIC_COMPARISON_NON_NUMERIC") from exc
    return {
        "GT": left_number > right_number,
        "GTE": left_number >= right_number,
        "LT": left_number < right_number,
        "LTE": left_number <= right_number,
    }[operator]


def evaluate_rule_ast(ast: Mapping[str, Any], fingerprint: Mapping[str, Any]) -> bool:
    validate_rule_ast(ast)
    operator = ast["operator"]
    if operator == "ALL_OF":
        return all(evaluate_rule_ast(item, fingerprint) for item in ast["clauses"])
    if operator == "ANY_OF":
        return any(evaluate_rule_ast(item, fingerprint) for item in ast["clauses"])
    if operator == "SEQUENCE":
        return all(evaluate_rule_ast(item, fingerprint) for item in ast["clauses"])
    if operator == "WITHIN_N_OBSERVATIONS":
        duration = int(fingerprint["features"].get("duration_observations", "0"))
        return duration <= int(ast["n"]) and evaluate_rule_ast(ast["clause"], fingerprint)
    if operator == "SAME_OBJECT":
        return bool(fingerprint["features"].get(ast["object_id_field"]))
    if operator == "MEASUREMENT_COMPARISON":
        key = ast["feature_key"]
        return key in fingerprint["features"] and _compare(fingerprint["features"][key], ast["comparison"], ast["value"])
    if operator == "RELATION_TRANSITION":
        features = fingerprint["features"]
        return (
            features.get("relation.object_id") == _normalise_scalar(ast["object_id"])
            and features.get("relation.from_topology") == _normalise_scalar(ast["from_topology"])
            and features.get("relation.to_topology") == _normalise_scalar(ast["to_topology"])
        )
    if operator == "RUN_LENGTH":
        return int(fingerprint["features"].get("run_length", "0")) >= int(ast["minimum"])
    if operator == "CONTEXT_AVAILABILITY":
        available = fingerprint["features"].get("context.available") == "TRUE"
        return available is bool(ast["required"])
    raise FunctionalDiscoveryError("RULE_AST_OPERATOR_NOT_IMPLEMENTED")


def evaluate_rule_candidate(
    candidate: Mapping[str, Any],
    population: Mapping[str, Any],
    fingerprint_inventory: Mapping[str, Any],
) -> dict[str, Any]:
    """Evaluate every applicable opportunity with explicit negative outcomes."""
    fingerprints = {item["opportunity_id"]: item for item in fingerprint_inventory["fingerprints"]}
    results: list[dict[str, Any]] = []
    for opportunity in population["records"]:
        source_outcome = opportunity["opportunity_outcome"]
        result = {
            "opportunity_id": opportunity["opportunity_id"],
            "source_unit_id": opportunity["source_unit_id"],
            "rule_candidate_id": candidate["rule_candidate_id"],
            "first_valid_time": opportunity["first_valid_time"],
        }
        if source_outcome == "NOT_APPLICABLE":
            result.update({"evaluation_outcome": "NOT_APPLICABLE", "reason_codes": opportunity["reason_codes"]})
        elif source_outcome == "CENSORED":
            result.update({"evaluation_outcome": "CENSORED", "reason_codes": opportunity["reason_codes"]})
        elif source_outcome == "CONFLICT":
            result.update({"evaluation_outcome": "CONFLICT", "reason_codes": opportunity["reason_codes"]})
        elif source_outcome == "POLICY_UNRESOLVED":
            result.update({"evaluation_outcome": "POLICY_UNRESOLVED", "reason_codes": opportunity["reason_codes"]})
        elif source_outcome == "AUTHORITY_BLOCKED":
            result.update({"evaluation_outcome": "AUTHORITY_BLOCKED", "reason_codes": opportunity["reason_codes"]})
        elif source_outcome != "COMPUTABLE" or opportunity["opportunity_id"] not in fingerprints:
            result.update({"evaluation_outcome": "NOT_EVALUABLE", "reason_codes": opportunity["reason_codes"] or ["FINGERPRINT_UNAVAILABLE"]})
        else:
            matched = evaluate_rule_ast(candidate["ast"], fingerprints[opportunity["opportunity_id"]])
            result.update({"evaluation_outcome": "MATCHED" if matched else "NOT_MATCHED", "reason_codes": []})
        result["evaluation_id"] = _id("C2.RULE.EVALUATION", result)
        results.append(result)
    counts = Counter(item["evaluation_outcome"] for item in results)
    body: dict[str, Any] = {
        "schema": "c2_research_rule_evaluation_population/vnext-r1",
        "rule_candidate_id": candidate["rule_candidate_id"],
        "population_id": population["population_id"],
        "result_count": len(results),
        "outcome_counts": dict(sorted(counts.items())),
        "results": sorted(results, key=lambda item: (item["first_valid_time"], item["evaluation_id"])),
        "complete_accounting": len(results) == population["record_count"],
        "active": False,
        "canonical": False,
        "authority": AUTHORITY,
    }
    _require(body["complete_accounting"], "RULE_EVALUATION_ACCOUNTING_MISMATCH")
    body["evaluation_population_id"] = _id("C2.RULE.EVALUATION.POPULATION", body)
    body["content_sha256"] = _sha(body)
    return body


def build_matched_controls(
    member_opportunity_ids: Sequence[str],
    population: Mapping[str, Any],
    *,
    duration_bin_size: int,
) -> dict[str, Any]:
    """Match controls by exact strata and declared duration bins, never nearest/best."""
    _require(duration_bin_size > 0, "DURATION_BIN_SIZE_INVALID")
    records = {item["opportunity_id"]: item for item in population["records"]}
    members = [records[item] for item in member_opportunity_ids]
    member_set = set(member_opportunity_ids)
    available: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for item in population["records"]:
        if item["opportunity_id"] in member_set or item["opportunity_outcome"] != "COMPUTABLE":
            continue
        stratum = item.get("matching_stratum") or {}
        key = (
            item["clock_id"], item["side"], item["frame_id"], item["object_family"],
            tuple(sorted((str(k), _normalise_scalar(v)) for k, v in stratum.items())),
            item["duration_observations"] // duration_bin_size,
        )
        available[key].append(item)
    for key in available:
        available[key].sort(key=lambda item: item["opportunity_id"])
    matches: list[dict[str, Any]] = []
    unmatched: list[dict[str, Any]] = []
    for member in sorted(members, key=lambda item: item["opportunity_id"]):
        stratum = member.get("matching_stratum") or {}
        key = (
            member["clock_id"], member["side"], member["frame_id"], member["object_family"],
            tuple(sorted((str(k), _normalise_scalar(v)) for k, v in stratum.items())),
            member["duration_observations"] // duration_bin_size,
        )
        candidates = available.get(key, [])
        if not candidates:
            unmatched.append({
                "member_opportunity_id": member["opportunity_id"],
                "reason_code": "NO_CONTROL_IN_EXACT_REGISTERED_STRATUM_AND_DURATION_BIN",
                "matching_key": repr(key),
            })
            continue
        control = candidates.pop(0)
        matches.append({
            "member_opportunity_id": member["opportunity_id"],
            "control_opportunity_id": control["opportunity_id"],
            "matching_key": repr(key),
            "selection_rule": "LEXICOGRAPHIC_FIRST_WITHIN_EXACT_REGISTERED_STRATUM_AND_DURATION_BIN",
        })
    body: dict[str, Any] = {
        "schema": "c2_matched_control_set/vnext-r1",
        "population_id": population["population_id"],
        "member_count": len(members),
        "matched_count": len(matches),
        "unmatched_count": len(unmatched),
        "matches": matches,
        "unmatched_requests": unmatched,
        "duration_bin_size": duration_bin_size,
        "hidden_nearest_or_best_selection": False,
        "active": False,
        "canonical": False,
        "authority": AUTHORITY,
    }
    body["control_set_id"] = _id("C2.MATCHED.CONTROLS", body)
    body["content_sha256"] = _sha(body)
    return body


def build_legacy_benchmark_comparison(
    rule_evaluations: Sequence[Mapping[str, Any]],
    legacy_benchmarks: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Compare legacy match sets after discovery; never feed them upstream."""
    candidate_sets = {
        item["rule_candidate_id"]: {
            result["opportunity_id"]
            for result in item["results"]
            if result["evaluation_outcome"] == "MATCHED"
        }
        for item in rule_evaluations
    }
    mappings: list[dict[str, Any]] = []
    for legacy in sorted(legacy_benchmarks, key=lambda item: str(item["legacy_rule_id"])):
        _require(legacy.get("benchmark_only") is True, "LEGACY_RULE_MUST_BE_BENCHMARK_ONLY")
        legacy_set = {str(item) for item in legacy.get("matched_opportunity_ids", [])}
        comparisons = []
        for candidate_id in sorted(candidate_sets):
            candidate_set = candidate_sets[candidate_id]
            intersection = legacy_set & candidate_set
            union = legacy_set | candidate_set
            comparisons.append({
                "rule_candidate_id": candidate_id,
                "legacy_match_count": len(legacy_set),
                "candidate_match_count": len(candidate_set),
                "intersection_count": len(intersection),
                "jaccard_similarity": 1.0 if not union else len(intersection) / len(union),
                "legacy_only_count": len(legacy_set - candidate_set),
                "candidate_only_count": len(candidate_set - legacy_set),
            })
        mappings.append({
            "legacy_rule_id": str(legacy["legacy_rule_id"]),
            "benchmark_only": True,
            "comparisons": comparisons,
            "operator_disposition": None,
            "allowed_dispositions": [
                "REDISCOVERED", "SPLIT", "MERGED", "PARTIALLY_RECOVERED",
                "NOT_RECOVERED", "CONTRADICTED",
            ],
            "upstream_dependency_count": 0,
        })
    body: dict[str, Any] = {
        "schema": "c2_legacy_rule_benchmark_comparison/vnext-r1",
        "legacy_rule_count": len(mappings),
        "candidate_rule_count": len(candidate_sets),
        "mappings": mappings,
        "legacy_seed_count": 0,
        "legacy_filter_count": 0,
        "legacy_score_count": 0,
        "legacy_stop_count": 0,
        "legacy_promotion_count": 0,
        "active": False,
        "canonical": False,
        "authority": AUTHORITY,
    }
    body["comparison_id"] = _id("C2.LEGACY.BENCHMARK", body)
    body["content_sha256"] = _sha(body)
    return body


def build_synthetic_discovery_bundle(
    requests: Sequence[Mapping[str, Any]],
    discovery_view: Mapping[str, Any],
    method_pack: Mapping[str, Any],
    *,
    registered_scope_id: str,
    input_manifest_sha256: str,
) -> dict[str, Any]:
    """Run the deterministic synthetic pipeline for contract assurance only."""
    population = build_opportunity_population(
        requests,
        discovery_view,
        registered_scope_id=registered_scope_id,
        input_manifest_sha256=input_manifest_sha256,
    )
    fingerprints = build_fingerprint_inventory(population, method_pack)
    motifs = extract_motifs(fingerprints, method_pack)
    families = build_provisional_families(motifs, method_pack)
    cores = extract_functional_cores(families, motifs, fingerprints, method_pack)
    candidates = [compile_rule_candidate(item, method_pack) for item in cores["functional_cores"]]
    evaluations = [evaluate_rule_candidate(item, population, fingerprints) for item in candidates]
    controls = [
        build_matched_controls(item["source_opportunity_ids"], population, duration_bin_size=int(method_pack["control_duration_bin_size"]))
        for item in candidates
    ]
    body: dict[str, Any] = {
        "schema": "c2_synthetic_functional_discovery_bundle/vnext-r1",
        "population": population,
        "fingerprint_inventory": fingerprints,
        "motif_inventory": motifs,
        "family_inventory": families,
        "functional_core_inventory": cores,
        "rule_candidates": candidates,
        "rule_evaluations": evaluations,
        "matched_control_sets": controls,
        "synthetic_only": True,
        "market_population": False,
        "cear_g10_disposition_eligible": False,
        "active": False,
        "canonical": False,
        "authority": AUTHORITY,
    }
    body["bundle_id"] = _id("C2.SYNTHETIC.DISCOVERY.BUNDLE", body)
    body["content_sha256"] = _sha(body)
    return body
