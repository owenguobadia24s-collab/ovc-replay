from __future__ import annotations

from fractions import Fraction
from hashlib import sha256
import json
from typing import Any, Mapping, Sequence

REQUIRED_METRICS = (
    "RESIDUAL_RATE_WITH_DENOMINATOR",
    "AMBIGUITY_RATE_WITH_DENOMINATOR",
    "CROSS_SENSITIVITY_SURVIVAL_WITH_DENOMINATOR",
    "CROSS_METHOD_CORRESPONDENCE_WITH_DENOMINATOR",
    "CHRONOLOGICAL_STABILITY_WITH_DENOMINATOR",
)

H1_START = "2026-06-01T00:00:00Z"
H1_END = "2026-06-16T00:00:00Z"
H2_END = "2026-07-01T00:00:00Z"


class StabilityMetricPreregistrationError(ValueError):
    pass


def logical_sha256(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")
    return sha256(raw).hexdigest()


def validate_metric_registry(registry: Mapping[str, Any]) -> str:
    if registry.get("schema") != "ovc-srfdi-stability-metric-spec-registry/v4":
        raise StabilityMetricPreregistrationError("unexpected registry schema")
    if tuple(registry.get("metric_order", ())) != REQUIRED_METRICS:
        raise StabilityMetricPreregistrationError("exact stability metric order required")
    specs = registry.get("stability_metric_specs")
    if not isinstance(specs, Mapping) or set(specs) != set(REQUIRED_METRICS):
        raise StabilityMetricPreregistrationError("exact stability metric spec set required")
    for metric in REQUIRED_METRICS:
        spec = specs[metric]
        if not isinstance(spec, Mapping):
            raise StabilityMetricPreregistrationError(f"{metric}: mapping required")
        if not str(spec.get("numerator_rule", "")).strip() or not str(spec.get("denominator_rule", "")).strip():
            raise StabilityMetricPreregistrationError(f"{metric}: numerator and denominator rules required")
    if not str(specs["AMBIGUITY_RATE_WITH_DENOMINATOR"].get("ambiguity_event_rule", "")).strip():
        raise StabilityMetricPreregistrationError("ambiguity event rule required")
    for metric in ("CROSS_SENSITIVITY_SURVIVAL_WITH_DENOMINATOR", "CROSS_METHOD_CORRESPONDENCE_WITH_DENOMINATOR"):
        if not str(specs[metric].get("correspondence_rule", "")).strip():
            raise StabilityMetricPreregistrationError(f"{metric}: correspondence rule required")
    if specs["CHRONOLOGICAL_STABILITY_WITH_DENOMINATOR"].get("chronology_partition_rule") != "FIXED_HALF_OPEN_PARTITIONS_H1_2026-06-01T00:00:00Z_TO_2026-06-16T00:00:00Z_AND_H2_2026-06-16T00:00:00Z_TO_2026-07-01T00:00:00Z":
        raise StabilityMetricPreregistrationError("chronology partition drift")
    common = registry.get("common_contract", {})
    if common.get("forced_resolution") != "FORBIDDEN" or common.get("hidden_composite") != "FORBIDDEN":
        raise StabilityMetricPreregistrationError("forced resolution or hidden composite enabled")
    return logical_sha256(registry)


def _families(catalog: Mapping[str, Any]) -> dict[str, set[str]]:
    result: dict[str, set[str]] = {}
    for family in catalog.get("families", []):
        family_id = str(family["family_id"])
        members = {str(value) for value in family.get("member_ids", [])}
        if members:
            result[family_id] = members
    return dict(sorted(result.items()))


def _domain(catalog: Mapping[str, Any]) -> set[str]:
    ids: set[str] = set()
    for members in _families(catalog).values():
        ids.update(members)
    ids.update(str(value) for value in catalog.get("residual_ids", []))
    ids.update(str(value) for value in catalog.get("noise_ids", []))
    return ids


def _rate(metric_id: str, numerator: int, denominator: int, *, zero_reason: str) -> dict[str, Any]:
    return {
        "metric_id": metric_id,
        "numerator": numerator,
        "denominator": denominator,
        "rate": None if denominator == 0 else f"{numerator}/{denominator}",
        "reason_code": zero_reason if denominator == 0 else None,
    }


def residual_rate(catalog: Mapping[str, Any]) -> dict[str, Any]:
    families = _families(catalog)
    assigned = set().union(*families.values()) if families else set()
    residual = {str(value) for value in catalog.get("residual_ids", [])} | {str(value) for value in catalog.get("noise_ids", [])}
    domain = assigned | residual
    return _rate("RESIDUAL_RATE_WITH_DENOMINATOR", len(residual), len(domain), zero_reason="EMPTY_ASSIGNMENT_DOMAIN")


def ambiguity_rate(anchor: Mapping[str, Any], counterpart: Mapping[str, Any]) -> dict[str, Any]:
    left = _families(anchor); right = _families(counterpart)
    common = _domain(anchor) & _domain(counterpart)
    numerator = 0; denominator = 0; ambiguous: list[dict[str, Any]] = []
    for family_id, members in left.items():
        anchor_common = members & common
        if not anchor_common:
            continue
        ranked: list[tuple[Fraction, str]] = []
        for other_id, other_members in right.items():
            inter = len(anchor_common & other_members & common)
            if inter == 0:
                continue
            union = len((anchor_common | (other_members & common)))
            ranked.append((Fraction(inter, union), other_id))
        if not ranked:
            continue
        denominator += len(anchor_common)
        best = max(score for score, _ in ranked)
        tied = sorted(other_id for score, other_id in ranked if score == best and score > 0)
        if len(tied) > 1:
            numerator += len(anchor_common)
            ambiguous.append({"anchor_family_id": family_id, "counterpart_family_ids": tied, "max_jaccard": f"{best.numerator}/{best.denominator}"})
    result = _rate("AMBIGUITY_RATE_WITH_DENOMINATOR", numerator, denominator, zero_reason="NO_POSITIVE_CORRESPONDENCE_DOMAIN")
    result["ambiguous_families"] = ambiguous
    return result


def family_survival_rate(anchor: Mapping[str, Any], counterpart: Mapping[str, Any], *, metric_id: str) -> dict[str, Any]:
    if metric_id not in {"CROSS_SENSITIVITY_SURVIVAL_WITH_DENOMINATOR", "CROSS_METHOD_CORRESPONDENCE_WITH_DENOMINATOR"}:
        raise StabilityMetricPreregistrationError("unsupported family correspondence metric")
    left = _families(anchor); right = _families(counterpart)
    common = _domain(anchor) & _domain(counterpart)
    numerator = 0; denominator = 0
    for members in left.values():
        anchor_common = members & common
        if not anchor_common:
            continue
        denominator += 1
        if metric_id == "CROSS_SENSITIVITY_SURVIVAL_WITH_DENOMINATOR":
            matched = any(anchor_common <= (other & common) for other in right.values())
        else:
            matched = any(anchor_common == (other & common) for other in right.values())
        numerator += int(matched)
    return _rate(metric_id, numerator, denominator, zero_reason="NO_ANCHOR_FAMILY_OPPORTUNITY")


def qualifies_adjacent_sensitivity(left: Mapping[str, Any], right: Mapping[str, Any], ladders: Mapping[str, Sequence[Any]]) -> bool:
    for key in ("representation_id", "distance_id", "family_method_id"):
        if left.get(key) != right.get(key):
            return False
    lp = dict(left.get("parameters", {})); rp = dict(right.get("parameters", {}))
    if set(lp) != set(rp):
        return False
    changed = [key for key in sorted(lp) if lp[key] != rp[key]]
    if len(changed) != 1:
        return False
    key = changed[0]
    ladder = [str(value) for value in ladders.get(key, ())]
    if str(lp[key]) not in ladder or str(rp[key]) not in ladder:
        return False
    return abs(ladder.index(str(lp[key])) - ladder.index(str(rp[key]))) == 1


def qualifies_cross_method(left: Mapping[str, Any], right: Mapping[str, Any]) -> bool:
    return (
        left.get("representation_id") == right.get("representation_id")
        and left.get("distance_id") == right.get("distance_id")
        and left.get("family_method_id") != right.get("family_method_id")
        and left.get("shared_minimum_support") == right.get("shared_minimum_support")
    )


def chronological_stability(catalog: Mapping[str, Any], record_first_valid_time: Mapping[str, str]) -> dict[str, Any]:
    numerator = 0; denominator = 0
    for members in _families(catalog).values():
        times = sorted(str(record_first_valid_time[item]) for item in members if item in record_first_valid_time and H1_START <= str(record_first_valid_time[item]) < H2_END)
        if not times:
            continue
        denominator += 1
        in_h1 = any(H1_START <= value < H1_END for value in times)
        in_h2 = any(H1_END <= value < H2_END for value in times)
        numerator += int(in_h1 and in_h2)
    result = _rate("CHRONOLOGICAL_STABILITY_WITH_DENOMINATOR", numerator, denominator, zero_reason="NO_DISCOVERED_FAMILY_IN_BENCHMARK_WINDOW")
    result["chronology_partitions"] = [[H1_START, H1_END], [H1_END, H2_END]]
    result["interpretation"] = "DESCRIPTIVE_FAMILY_TEMPORAL_SPAN_NOT_INDEPENDENT_HALF_SAMPLE_REFIT_STABILITY"
    return result
