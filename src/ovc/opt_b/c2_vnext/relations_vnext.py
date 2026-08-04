"""Raw relation, topology and fixed-object transition foundation for C2 vNext.

This module emits measurement facts before interpretation.  It has no active
selector, semantic interaction label, threshold, event, episode or release
authority.
"""
from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping, Sequence

UTC = timezone.utc
PROBE_TYPES = ("POINT", "BODY_SPAN", "BAR_SPAN", "ORDERED_PATH")
EVIDENCE_MODES = ("OHLC_SPAN", "M1_PATH", "TICK_PATH")
POINT_LEVEL_TOPOLOGY = ("BELOW", "EQUAL", "ABOVE")
SPAN_LEVEL_TOPOLOGY = ("ENTIRELY_BELOW", "TOUCHES", "STRADDLES", "ENTIRELY_ABOVE")
POINT_CONTAINER_TOPOLOGY = (
    "BELOW", "ON_LOWER_BOUNDARY", "INSIDE", "ON_UPPER_BOUNDARY", "ABOVE",
)
SPAN_CONTAINER_TOPOLOGY = (
    "ENTIRELY_BELOW", "TOUCHES_LOWER", "CROSSES_LOWER", "INSIDE",
    "TOUCHES_UPPER", "CROSSES_UPPER", "COVERS_CONTAINER", "ENTIRELY_ABOVE",
)
CROSSING_STATUSES = (
    "NO_CROSS", "CROSS_UP", "CROSS_DOWN", "TOUCH_ONLY",
    "SPAN_STRADDLES_PATH_ORDER_UNKNOWN", "INSUFFICIENT_ORDERED_PATH",
)
SCOPE_TYPES = (
    "LOCAL_LEVELS", "PARENT_LEVELS", "LOCAL_MEASUREMENT_CONTAINERS",
    "LOCAL_STRUCTURAL_CONTAINERS", "PARENT_MEASUREMENT_CONTAINERS",
    "PARENT_STRUCTURAL_CONTAINERS",
)


class RelationContractError(ValueError):
    pass


def _require(condition: bool, marker: str) -> None:
    if not condition:
        raise RelationContractError(marker)


def parse_time(value: str | datetime) -> datetime:
    result = value if isinstance(value, datetime) else datetime.fromisoformat(value.replace("Z", "+00:00"))
    _require(result.tzinfo is not None, "TIMEZONE_REQUIRED")
    return result.astimezone(UTC)


def iso(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def digest(prefix: str, value: Any, length: int = 24) -> str:
    return f"{prefix}.{hashlib.sha256(canonical_bytes(value)).hexdigest()[:length]}"


def _number(value: Any, marker: str) -> float:
    _require(isinstance(value, (int, float)) and not isinstance(value, bool), marker)
    return float(value)


def _equal_at_precision(left: float, right: float, precision: int) -> bool:
    _require(isinstance(precision, int) and precision >= 0, "PRECISION")
    return round(left, precision) == round(right, precision)


@dataclass(frozen=True)
class NormalizationScale:
    scale_id: str
    value: float
    unit: str
    policy_id: str
    source_id: str
    first_valid_time: str
    maturity: str = "SHADOW_EXPERIMENT"
    active: bool = False
    canonical: bool = False

    def __post_init__(self) -> None:
        _require(self.value > 0, "NORMALIZATION_SCALE_POSITIVE")
        _require(bool(self.scale_id) and bool(self.unit) and bool(self.policy_id), "NORMALIZATION_SCALE_IDENTITY")
        _require(bool(self.source_id), "NORMALIZATION_SCALE_SOURCE")
        parse_time(self.first_valid_time)
        _require(self.maturity == "SHADOW_EXPERIMENT", "NORMALIZATION_SCALE_MATURITY")
        _require(not self.active, "NORMALIZATION_SCALE_ACTIVATION_DENIED")
        _require(not self.canonical, "CANONICAL_NORMALIZATION_SCALE_DENIED")


def point_probe(*, value: float, source_record_id: str, first_valid_time: str, probe_label: str = "CLOSE") -> dict[str, Any]:
    body = {
        "probe_type": "POINT", "probe_label": probe_label,
        "value": _number(value, "POINT_VALUE"),
        "source_record_id": source_record_id,
        "first_valid_time": iso(parse_time(first_valid_time)),
    }
    return {"probe_id": digest("C2.RELATION.PROBE", body), **body}


def span_probe(
    *,
    low: float,
    high: float,
    source_record_id: str,
    first_valid_time: str,
    probe_type: str,
) -> dict[str, Any]:
    _require(probe_type in {"BODY_SPAN", "BAR_SPAN"}, "SPAN_PROBE_TYPE")
    low_value = _number(low, "SPAN_LOW")
    high_value = _number(high, "SPAN_HIGH")
    _require(low_value <= high_value, "SPAN_ORDER")
    body = {
        "probe_type": probe_type, "low": low_value, "high": high_value,
        "source_record_id": source_record_id,
        "first_valid_time": iso(parse_time(first_valid_time)),
    }
    return {"probe_id": digest("C2.RELATION.PROBE", body), **body}


def bar_probes(observation: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    for key in ("open", "high", "low", "close", "observation_id", "first_valid_time"):
        _require(key in observation, f"OBSERVATION_FIELD_REQUIRED:{key}")
    open_value = _number(observation["open"], "OPEN_VALUE")
    close_value = _number(observation["close"], "CLOSE_VALUE")
    return {
        "OPEN": point_probe(value=open_value, source_record_id=str(observation["observation_id"]), first_valid_time=str(observation["first_valid_time"]), probe_label="OPEN"),
        "CLOSE": point_probe(value=close_value, source_record_id=str(observation["observation_id"]), first_valid_time=str(observation["first_valid_time"]), probe_label="CLOSE"),
        "BODY_SPAN": span_probe(low=min(open_value, close_value), high=max(open_value, close_value), source_record_id=str(observation["observation_id"]), first_valid_time=str(observation["first_valid_time"]), probe_type="BODY_SPAN"),
        "BAR_SPAN": span_probe(low=_number(observation["low"], "LOW_VALUE"), high=_number(observation["high"], "HIGH_VALUE"), source_record_id=str(observation["observation_id"]), first_valid_time=str(observation["first_valid_time"]), probe_type="BAR_SPAN"),
    }


def _normalized_values(signed_distance: float, scales: Sequence[NormalizationScale], *, as_of_time: str) -> list[dict[str, Any]]:
    as_of = parse_time(as_of_time)
    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    for scale in scales:
        _require(scale.scale_id not in seen, "DUPLICATE_NORMALIZATION_SCALE")
        seen.add(scale.scale_id)
        _require(parse_time(scale.first_valid_time) <= as_of, "NORMALIZATION_SCALE_NOT_FIRST_VALID")
        result.append({
            "scale_id": scale.scale_id, "scale_value": scale.value,
            "scale_unit": scale.unit, "policy_id": scale.policy_id,
            "source_id": scale.source_id,
            "normalized_signed_distance": signed_distance / scale.value,
            "normalized_absolute_distance": abs(signed_distance) / scale.value,
            "active": False, "canonical": False,
        })
    return result


def relate_point_to_level(
    probe: Mapping[str, Any],
    level: Mapping[str, Any],
    *,
    precision: int,
    scales: Sequence[NormalizationScale] = (),
    mode: str = "CAUSAL_AS_OF",
) -> dict[str, Any]:
    _require(probe.get("probe_type") == "POINT", "POINT_PROBE_REQUIRED")
    _require(mode in {"CAUSAL_AS_OF", "RETROSPECTIVE_AUDIT"}, "RELATION_MODE")
    probe_time = parse_time(str(probe["first_valid_time"]))
    level_time = parse_time(str(level["first_valid_time"]))
    if mode == "CAUSAL_AS_OF":
        _require(level_time <= probe_time, "LEVEL_NOT_FIRST_VALID_AS_OF")
    subject = _number(probe["value"], "POINT_VALUE")
    object_value = _number(level["value"], "LEVEL_VALUE")
    signed = subject - object_value
    equal = _equal_at_precision(subject, object_value, precision)
    topology = "EQUAL" if equal else "BELOW" if signed < 0 else "ABOVE"
    identity = {
        "probe_id": probe["probe_id"], "object_id": level["level_id"],
        "mode": mode, "precision": precision,
    }
    body = {
        "relation_id": digest("C2.RELATION.LEVEL.POINT", identity),
        "subject_probe_id": probe["probe_id"], "object_kind": "LEVEL",
        "object_id": level["level_id"], "object_value": object_value,
        "signed_distance": signed, "absolute_distance": abs(signed),
        "distance_sign_convention": "SUBJECT_MINUS_OBJECT",
        "equal_at_source_precision": equal, "source_precision": precision,
        "topology": topology,
        "normalizations": _normalized_values(signed, scales, as_of_time=str(probe["first_valid_time"])),
        "first_valid_time": str(probe["first_valid_time"]),
        "mode": mode, "semantic_label": None,
        "authority": "RAW_RELATION_FACT_ONLY",
    }
    return body


def relate_span_to_level(span: Mapping[str, Any], level: Mapping[str, Any], *, precision: int, mode: str = "CAUSAL_AS_OF") -> dict[str, Any]:
    _require(span.get("probe_type") in {"BODY_SPAN", "BAR_SPAN"}, "SPAN_PROBE_REQUIRED")
    if mode == "CAUSAL_AS_OF":
        _require(parse_time(str(level["first_valid_time"])) <= parse_time(str(span["first_valid_time"])), "LEVEL_NOT_FIRST_VALID_AS_OF")
    low = _number(span["low"], "SPAN_LOW")
    high = _number(span["high"], "SPAN_HIGH")
    value = _number(level["value"], "LEVEL_VALUE")
    low_equal = _equal_at_precision(low, value, precision)
    high_equal = _equal_at_precision(high, value, precision)
    if high < value and not high_equal:
        topology = "ENTIRELY_BELOW"
    elif low > value and not low_equal:
        topology = "ENTIRELY_ABOVE"
    elif low_equal or high_equal or (low == high and _equal_at_precision(low, value, precision)):
        topology = "TOUCHES"
    else:
        topology = "STRADDLES"
    identity = {"probe_id": span["probe_id"], "object_id": level["level_id"], "precision": precision, "mode": mode}
    return {
        "relation_id": digest("C2.RELATION.LEVEL.SPAN", identity),
        "subject_probe_id": span["probe_id"], "object_kind": "LEVEL",
        "object_id": level["level_id"], "span_low": low, "span_high": high,
        "object_value": value, "topology": topology,
        "path_crossing_claim": None,
        "first_valid_time": str(span["first_valid_time"]), "mode": mode,
        "semantic_label": None, "authority": "RAW_TOPOLOGY_FACT_ONLY",
    }


def relate_point_to_container(probe: Mapping[str, Any], container: Mapping[str, Any], *, precision: int, mode: str = "CAUSAL_AS_OF") -> dict[str, Any]:
    _require(probe.get("probe_type") == "POINT", "POINT_PROBE_REQUIRED")
    if mode == "CAUSAL_AS_OF":
        _require(parse_time(str(container["first_valid_time"])) <= parse_time(str(probe["first_valid_time"])), "CONTAINER_NOT_FIRST_VALID_AS_OF")
    value = _number(probe["value"], "POINT_VALUE")
    lower = _number(container["lower_value"], "CONTAINER_LOWER")
    upper = _number(container["upper_value"], "CONTAINER_UPPER")
    _require(lower < upper, "CONTAINER_POSITIVE_WIDTH")
    if _equal_at_precision(value, lower, precision):
        topology = "ON_LOWER_BOUNDARY"
    elif _equal_at_precision(value, upper, precision):
        topology = "ON_UPPER_BOUNDARY"
    elif value < lower:
        topology = "BELOW"
    elif value > upper:
        topology = "ABOVE"
    else:
        topology = "INSIDE"
    identity = {"probe_id": probe["probe_id"], "object_id": container["container_id"], "precision": precision, "mode": mode}
    return {
        "relation_id": digest("C2.RELATION.CONTAINER.POINT", identity),
        "subject_probe_id": probe["probe_id"], "object_kind": "CONTAINER",
        "object_id": container["container_id"], "lower_value": lower, "upper_value": upper,
        "signed_distance_to_lower": value - lower,
        "signed_distance_to_upper": value - upper,
        "topology": topology, "source_precision": precision,
        "first_valid_time": str(probe["first_valid_time"]), "mode": mode,
        "semantic_label": None, "authority": "RAW_RELATION_FACT_ONLY",
    }


def relate_span_to_container(span: Mapping[str, Any], container: Mapping[str, Any], *, precision: int, mode: str = "CAUSAL_AS_OF") -> dict[str, Any]:
    _require(span.get("probe_type") in {"BODY_SPAN", "BAR_SPAN"}, "SPAN_PROBE_REQUIRED")
    if mode == "CAUSAL_AS_OF":
        _require(parse_time(str(container["first_valid_time"])) <= parse_time(str(span["first_valid_time"])), "CONTAINER_NOT_FIRST_VALID_AS_OF")
    low = _number(span["low"], "SPAN_LOW")
    high = _number(span["high"], "SPAN_HIGH")
    lower = _number(container["lower_value"], "CONTAINER_LOWER")
    upper = _number(container["upper_value"], "CONTAINER_UPPER")
    lower_touch = _equal_at_precision(low, lower, precision) or _equal_at_precision(high, lower, precision)
    upper_touch = _equal_at_precision(low, upper, precision) or _equal_at_precision(high, upper, precision)
    if high < lower and not lower_touch:
        topology = "ENTIRELY_BELOW"
    elif low > upper and not upper_touch:
        topology = "ENTIRELY_ABOVE"
    elif low <= lower and high >= upper:
        topology = "COVERS_CONTAINER"
    elif lower < low and high < upper:
        topology = "INSIDE"
    elif lower_touch and high <= lower:
        topology = "TOUCHES_LOWER"
    elif upper_touch and low >= upper:
        topology = "TOUCHES_UPPER"
    elif low < lower < high < upper:
        topology = "CROSSES_LOWER"
    elif lower < low < upper < high:
        topology = "CROSSES_UPPER"
    elif lower_touch:
        topology = "TOUCHES_LOWER"
    elif upper_touch:
        topology = "TOUCHES_UPPER"
    else:
        topology = "INSIDE"
    identity = {"probe_id": span["probe_id"], "object_id": container["container_id"], "precision": precision, "mode": mode}
    return {
        "relation_id": digest("C2.RELATION.CONTAINER.SPAN", identity),
        "subject_probe_id": span["probe_id"], "object_kind": "CONTAINER",
        "object_id": container["container_id"], "span_low": low, "span_high": high,
        "lower_value": lower, "upper_value": upper, "topology": topology,
        "path_crossing_claim": None,
        "first_valid_time": str(span["first_valid_time"]), "mode": mode,
        "semantic_label": None, "authority": "RAW_TOPOLOGY_FACT_ONLY",
    }


def fixed_object_crossing(
    *,
    object_id: str,
    object_value: float,
    previous_value: float,
    current_value: float,
    previous_time: str,
    current_time: str,
    precision: int,
    evidence_mode: str,
    ordered_path: Sequence[float] | None = None,
) -> dict[str, Any]:
    _require(evidence_mode in EVIDENCE_MODES, "EVIDENCE_MODE")
    previous_time_dt = parse_time(previous_time)
    current_time_dt = parse_time(current_time)
    _require(previous_time_dt < current_time_dt, "CROSSING_CHRONOLOGY")
    object_value = _number(object_value, "OBJECT_VALUE")
    previous_value = _number(previous_value, "PREVIOUS_VALUE")
    current_value = _number(current_value, "CURRENT_VALUE")
    previous_equal = _equal_at_precision(previous_value, object_value, precision)
    current_equal = _equal_at_precision(current_value, object_value, precision)
    previous_side = 0 if previous_equal else -1 if previous_value < object_value else 1
    current_side = 0 if current_equal else -1 if current_value < object_value else 1
    path_order_known = evidence_mode in {"M1_PATH", "TICK_PATH"}
    ordered_values = [previous_value, current_value] if ordered_path is None else [_number(item, "PATH_VALUE") for item in ordered_path]
    if evidence_mode == "OHLC_SPAN":
        if min(previous_value, current_value) < object_value < max(previous_value, current_value):
            status = "SPAN_STRADDLES_PATH_ORDER_UNKNOWN"
        elif previous_equal or current_equal:
            status = "TOUCH_ONLY"
        else:
            status = "NO_CROSS"
    elif len(ordered_values) < 2:
        status = "INSUFFICIENT_ORDERED_PATH"
    else:
        status = "NO_CROSS"
        for left, right in zip(ordered_values, ordered_values[1:]):
            left_side = 0 if _equal_at_precision(left, object_value, precision) else -1 if left < object_value else 1
            right_side = 0 if _equal_at_precision(right, object_value, precision) else -1 if right < object_value else 1
            if left_side < 0 and right_side > 0:
                status = "CROSS_UP"
                break
            if left_side > 0 and right_side < 0:
                status = "CROSS_DOWN"
                break
            if left_side != 0 and right_side == 0:
                status = "TOUCH_ONLY"
    body = {
        "object_id": object_id, "object_value": object_value,
        "previous_value": previous_value, "current_value": current_value,
        "previous_time": iso(previous_time_dt), "current_time": iso(current_time_dt),
        "previous_side": previous_side, "current_side": current_side,
        "evidence_mode": evidence_mode, "path_order_known": path_order_known,
        "ordered_path_count": len(ordered_values) if path_order_known else None,
        "crossing_status": status, "same_fixed_object_required": True,
        "semantic_label": None, "authority": "RAW_CROSSING_EVIDENCE_ONLY",
    }
    return {"crossing_evidence_id": digest("C2.RELATION.CROSSING", body), **body}


def reference_change_record(*, previous_object_id: str, current_object_id: str, first_valid_time: str, reason: str) -> dict[str, Any]:
    _require(previous_object_id != current_object_id, "REFERENCE_CHANGE_REQUIRES_DIFFERENT_OBJECT")
    body = {
        "previous_object_id": previous_object_id,
        "current_object_id": current_object_id,
        "first_valid_time": iso(parse_time(first_valid_time)),
        "reason": reason, "is_crossing": False,
        "authority": "REFERENCE_IDENTITY_CHANGE_ONLY",
    }
    return {"reference_change_id": digest("C2.RELATION.REFERENCE.CHANGE", body), **body}


def temporal_relation_delta(previous: Mapping[str, Any], current: Mapping[str, Any]) -> dict[str, Any]:
    _require(previous.get("object_id") == current.get("object_id"), "RELATION_DELTA_REQUIRES_SAME_OBJECT")
    _require(parse_time(str(previous["first_valid_time"])) < parse_time(str(current["first_valid_time"])), "RELATION_DELTA_CHRONOLOGY")
    _require("signed_distance" in previous and "signed_distance" in current, "RELATION_DELTA_DISTANCE_REQUIRED")
    signed_delta = float(current["signed_distance"]) - float(previous["signed_distance"])
    absolute_delta = float(current["absolute_distance"]) - float(previous["absolute_distance"])
    body = {
        "object_id": current["object_id"],
        "previous_relation_id": previous["relation_id"],
        "current_relation_id": current["relation_id"],
        "signed_distance_delta": signed_delta,
        "absolute_distance_delta": absolute_delta,
        "absolute_distance_change": "DECREASED" if absolute_delta < 0 else "INCREASED" if absolute_delta > 0 else "UNCHANGED",
        "previous_topology": previous["topology"],
        "current_topology": current["topology"],
        "first_valid_time": current["first_valid_time"],
        "approaching_label": None, "testing_label": None,
        "authority": "RAW_TEMPORAL_RELATION_FACT_ONLY",
    }
    return {"relation_delta_id": digest("C2.RELATION.DELTA", body), **body}


def build_relation_set(
    *,
    scope_type: str,
    subject_observation_id: str,
    candidate_object_ids: Sequence[str],
    relations: Sequence[Mapping[str, Any]],
    exclusions: Sequence[Mapping[str, Any]],
    as_of_time: str,
    mode: str = "CAUSAL_AS_OF",
) -> dict[str, Any]:
    _require(scope_type in SCOPE_TYPES, "RELATION_SCOPE_TYPE")
    _require(mode in {"CAUSAL_AS_OF", "RETROSPECTIVE_AUDIT"}, "RELATION_MODE")
    candidates = list(candidate_object_ids)
    _require(len(candidates) == len(set(candidates)), "DUPLICATE_RELATION_CANDIDATE")
    related = [str(item["object_id"]) for item in relations]
    excluded = [str(item["object_id"]) for item in exclusions]
    _require(not (set(related) & set(excluded)), "RELATION_AND_EXCLUSION_OVERLAP")
    _require(set(related) | set(excluded) == set(candidates), "RELATION_SET_INCOMPLETE")
    for exclusion in exclusions:
        _require(bool(exclusion.get("reason")), "RELATION_EXCLUSION_REASON_REQUIRED")
    body = {
        "scope_type": scope_type, "subject_observation_id": subject_observation_id,
        "candidate_object_ids": sorted(candidates),
        "relation_ids": sorted(str(item["relation_id"]) for item in relations),
        "exclusions": sorted([copy.deepcopy(dict(item)) for item in exclusions], key=lambda item: (item["reason"], item["object_id"])),
        "as_of_time": iso(parse_time(as_of_time)), "mode": mode,
        "complete_scoped_inventory": True, "selected_object_id": None,
        "fallback_object_id": None, "semantic_interaction_label": None,
        "authority": "SCOPED_RELATION_INVENTORY_ONLY",
    }
    return {"relation_set_id": digest("C2.RELATION.SET", body), **body}


def assert_causal_relation(record: Mapping[str, Any]) -> None:
    _require(record.get("mode") == "CAUSAL_AS_OF", "CAUSAL_RELATION_MODE_REQUIRED")
    _require(record.get("semantic_label") is None, "SEMANTIC_RELATION_LABEL_PROHIBITED")
    _require("outcome" not in record and "future_value" not in record, "CAUSAL_RELATION_FUTURE_FIELD")


def build_legacy_relation_crosswalk(legacy_records: Sequence[Mapping[str, Any]], relations: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    index: dict[tuple[str, str], list[str]] = {}
    for relation in relations:
        key = (str(relation["object_id"]), str(relation["topology"]))
        index.setdefault(key, []).append(str(relation["relation_id"]))
    output: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw in legacy_records:
        legacy_id = str(raw["legacy_relation_id"])
        _require(legacy_id not in seen, "DUPLICATE_LEGACY_RELATION")
        seen.add(legacy_id)
        matches = sorted(index.get((str(raw["object_id"]), str(raw["raw_topology"])), []))
        body = {
            "legacy_relation_id": legacy_id,
            "object_id": raw["object_id"], "raw_topology": raw["raw_topology"],
            "matched_relation_ids": matches,
            "match_status": "MATCHED_UNIQUE" if len(matches) == 1 else "MATCHED_MULTIPLE" if len(matches) > 1 else "UNMATCHED",
            "legacy_interpretive_label": raw.get("interpretive_label"),
            "interpretive_label_promoted": False,
            "legacy_mutated": False, "authority": "AUDIT_ONLY",
        }
        output.append({"crosswalk_id": digest("C2.RELATION.LEGACY.XWALK", body), **body})
    output.sort(key=lambda item: item["legacy_relation_id"])
    return output
