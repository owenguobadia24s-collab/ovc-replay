"""Inactive, noncanonical C2 vNext formula profiles authorised by CEAR-G6.

The functions in this module project frozen raw evidence into five read-only
axis products.  They contain no numeric thresholds, active selectors,
semantic promotion, probability, risk or execution authority.
"""
from __future__ import annotations

import copy
import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Mapping, Sequence

UTC = timezone.utc
AXIS_ORDER = ("LOCATION", "MOTION", "ORGANISATION", "INTERACTION", "QUALITY")
PROFILE_IDS = {
    "LOCATION": "C2.FORMULA.LOCATION.RAW_GEOMETRY.v1",
    "MOTION": "C2.FORMULA.MOTION.TYPED_HORIZON_DELTA.v1",
    "ORGANISATION": "C2.FORMULA.ORGANISATION.CONTAINER_GRAPH.v1",
    "INTERACTION": "C2.FORMULA.INTERACTION.RAW_TRANSITION_INPUT.v1",
    "QUALITY": "C2.FORMULA.QUALITY.PER_COMPONENT_COMPUTABILITY.v1",
}
PROHIBITED_FIELDS = {
    "future_value", "outcome", "probability", "risk", "exposure",
    "trade", "trading", "execution", "position_size", "target", "stop",
    "winning_object", "best_object", "nearest_object", "fallback_selected",
}


class FormulaProfileError(ValueError):
    pass


def _require(condition: bool, marker: str) -> None:
    if not condition:
        raise FormulaProfileError(marker)


def _parse_time(value: str | datetime) -> datetime:
    result = value if isinstance(value, datetime) else datetime.fromisoformat(value.replace("Z", "+00:00"))
    _require(result.tzinfo is not None, "TIMEZONE_REQUIRED")
    return result.astimezone(UTC)


def _iso(value: str | datetime) -> str:
    return _parse_time(value).isoformat().replace("+00:00", "Z")


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _digest(prefix: str, value: Any) -> str:
    return f"{prefix}.{hashlib.sha256(_canonical(value)).hexdigest()[:24]}"


def _scan_prohibited(value: Any, path: str = "$") -> None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            if str(key).lower() in PROHIBITED_FIELDS:
                raise FormulaProfileError(f"PROHIBITED_FIELD:{path}.{key}")
            _scan_prohibited(item, f"{path}.{key}")
    elif isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            _scan_prohibited(item, f"{path}[{index}]")


def _first_valid_guard(record: Mapping[str, Any], as_of: datetime) -> None:
    value = record.get("first_valid_time") or record.get("as_of_time")
    if value is not None:
        _require(_parse_time(str(value)) <= as_of, "INPUT_NOT_FIRST_VALID_AS_OF")


def _profile(
    *, axis: str, as_of_time: str, input_ids: Sequence[str], facts: Any,
    computable: bool, reason_codes: Sequence[str], source_ids: Sequence[str],
) -> dict[str, Any]:
    _require(axis in AXIS_ORDER, "FORMULA_AXIS")
    as_of = _iso(as_of_time)
    body = {
        "schema": "c2_formula_profile_output/vnext-r1",
        "profile_id": PROFILE_IDS[axis], "axis": axis,
        "freeze_id": "C2AR.INTEGRATED.SHADOW.FREEZE.v1",
        "as_of_time": as_of,
        "input_ids": sorted({str(item) for item in input_ids if item is not None}),
        "source_ids": sorted({str(item) for item in source_ids if item is not None}),
        "computability": "COMPUTABLE" if computable else "NOT_COMPUTABLE",
        "reason_codes": sorted({str(item) for item in reason_codes}),
        "facts": copy.deepcopy(facts),
        "numeric_thresholds": [], "selected_object_id": None,
        "fallback_object_id": None, "semantic_label": None,
        "active": False, "canonical": False,
        "maturity": "SHADOW_FROZEN",
        "authority": "SHADOW_FROZEN_READ_ONLY",
    }
    _scan_prohibited(body)
    body["profile_output_id"] = _digest("C2.FORMULA.OUTPUT", body)
    body["content_sha256"] = hashlib.sha256(_canonical(body)).hexdigest()
    return body


def evaluate_location_profile(
    relation_sets: Sequence[Mapping[str, Any]],
    relations: Sequence[Mapping[str, Any]], *, as_of_time: str,
) -> dict[str, Any]:
    as_of = _parse_time(as_of_time)
    candidate_ids: set[str] = set()
    relation_ids: set[str] = set()
    exclusions: list[dict[str, Any]] = []
    set_ids: list[str] = []
    for relation_set in relation_sets:
        _first_valid_guard(relation_set, as_of)
        _require(relation_set.get("complete_scoped_inventory") is True, "LOCATION_RELATION_SET_INCOMPLETE")
        _require(relation_set.get("selected_object_id") is None, "LOCATION_HIDDEN_SELECTION")
        _require(relation_set.get("fallback_object_id") is None, "LOCATION_HIDDEN_FALLBACK")
        set_ids.append(str(relation_set["relation_set_id"]))
        candidate_ids.update(str(item) for item in relation_set.get("candidate_object_ids", []))
        relation_ids.update(str(item) for item in relation_set.get("relation_ids", []))
        exclusions.extend(copy.deepcopy(list(relation_set.get("exclusions", []))))
    raw_facts: list[dict[str, Any]] = []
    seen_relation_ids: set[str] = set()
    allowed = (
        "relation_id", "subject_probe_id", "object_kind", "object_id",
        "topology", "signed_distance", "absolute_distance",
        "signed_distance_to_lower", "signed_distance_to_upper",
        "equal_at_source_precision", "source_precision", "mode",
        "first_valid_time",
    )
    for relation in relations:
        _first_valid_guard(relation, as_of)
        rid = str(relation["relation_id"])
        _require(rid not in seen_relation_ids, "DUPLICATE_LOCATION_RELATION")
        seen_relation_ids.add(rid)
        _require(rid in relation_ids, "LOCATION_RELATION_OUTSIDE_DECLARED_SET")
        _require(str(relation["object_id"]) in candidate_ids, "LOCATION_OBJECT_OUTSIDE_DECLARED_SET")
        raw_facts.append({key: copy.deepcopy(relation[key]) for key in allowed if key in relation})
    _require(seen_relation_ids == relation_ids, "LOCATION_DECLARED_RELATION_MISSING")
    raw_facts.sort(key=lambda item: (str(item.get("object_kind")), str(item.get("object_id")), str(item["relation_id"])))
    exclusions.sort(key=lambda item: (str(item.get("reason")), str(item.get("object_id"))))
    computable = bool(raw_facts)
    reasons = [] if computable else ["NO_RAW_RELATION_FACTS"]
    return _profile(
        axis="LOCATION", as_of_time=as_of_time,
        input_ids=[*set_ids, *sorted(relation_ids)],
        source_ids=sorted(candidate_ids), computable=computable, reason_codes=reasons,
        facts={"relations": raw_facts, "exclusions": exclusions, "complete_scoped_inventory": True},
    )


def evaluate_motion_profile(
    horizon_membership: Mapping[str, Any], *, price_delta: float | None,
    relation_deltas: Sequence[Mapping[str, Any]], as_of_time: str,
) -> dict[str, Any]:
    as_of = _parse_time(as_of_time)
    _first_valid_guard(horizon_membership, as_of)
    horizon_id = str(horizon_membership.get("horizon_id") or horizon_membership.get("definition_id") or "")
    _require(bool(horizon_id), "MOTION_HORIZON_ID_REQUIRED")
    membership_status = str(horizon_membership.get("status", "UNKNOWN"))
    delta_facts: list[dict[str, Any]] = []
    for delta in relation_deltas:
        _first_valid_guard(delta, as_of)
        delta_facts.append({
            key: copy.deepcopy(delta[key]) for key in (
                "relation_delta_id", "object_id", "signed_distance_delta",
                "absolute_distance_delta", "absolute_distance_change",
                "previous_topology", "current_topology", "first_valid_time",
            ) if key in delta
        })
    delta_facts.sort(key=lambda item: (str(item.get("object_id")), str(item.get("relation_delta_id"))))
    complete = membership_status in {"COMPLETE", "AVAILABLE", "OK"}
    computable = complete and price_delta is not None
    reasons: list[str] = []
    if not complete:
        reasons.append(f"HORIZON_{membership_status}")
    if price_delta is None:
        reasons.append("PRICE_DELTA_UNAVAILABLE")
    membership_id = str(horizon_membership.get("membership_id") or horizon_membership.get("horizon_membership_id") or horizon_id)
    return _profile(
        axis="MOTION", as_of_time=as_of_time,
        input_ids=[membership_id, *[str(item.get("relation_delta_id")) for item in relation_deltas]],
        source_ids=[horizon_id, *[str(item.get("object_id")) for item in relation_deltas]],
        computable=computable, reason_codes=reasons,
        facts={
            "horizon_id": horizon_id, "membership_status": membership_status,
            "member_observation_ids": sorted(str(item) for item in horizon_membership.get("member_observation_ids", [])),
            "price_delta": price_delta, "relation_deltas": delta_facts,
        },
    )


def evaluate_organisation_profile(
    container_graph: Mapping[str, Any], *, swing_graph: Mapping[str, Any] | None,
    as_of_time: str,
) -> dict[str, Any]:
    as_of = _parse_time(as_of_time)
    _first_valid_guard(container_graph, as_of)
    _require(container_graph.get("complete_inventory") is True, "ORGANISATION_CONTAINER_INVENTORY_INCOMPLETE")
    _require(container_graph.get("width_derived_tree") is not True, "WIDTH_DERIVED_HIERARCHY_PROHIBITED")
    containers = []
    for item in container_graph.get("containers", []):
        _first_valid_guard(item, as_of)
        containers.append({key: copy.deepcopy(item[key]) for key in (
            "container_id", "family", "kind", "lower_value", "upper_value",
            "width", "centre", "structural_depth", "first_valid_time",
        ) if key in item})
    containers.sort(key=lambda item: str(item.get("container_id")))
    edges = [{key: copy.deepcopy(item[key]) for key in (
        "container_edge_id", "left_container_id", "right_container_id", "relation", "basis",
    ) if key in item} for item in container_graph.get("edges", [])]
    edges.sort(key=lambda item: str(item.get("container_edge_id")))
    swing_summary: dict[str, Any] | None = None
    input_ids = [str(container_graph["container_graph_id"])]
    source_ids = [str(item.get("container_id")) for item in containers]
    if swing_graph is not None:
        _first_valid_guard(swing_graph, as_of)
        swing_summary = {
            "swing_graph_id": swing_graph.get("swing_graph_id"),
            "level_ids": sorted(str(item) for item in swing_graph.get("level_ids", [])),
            "edges": copy.deepcopy(list(swing_graph.get("edges", []))),
        }
        input_ids.append(str(swing_graph.get("swing_graph_id")))
        source_ids.extend(swing_summary["level_ids"])
    computable = bool(containers)
    return _profile(
        axis="ORGANISATION", as_of_time=as_of_time,
        input_ids=input_ids, source_ids=source_ids, computable=computable,
        reason_codes=[] if computable else ["NO_CONTAINER_INVENTORY"],
        facts={"containers": containers, "container_edges": edges, "swing_graph": swing_summary, "complete_inventory": True},
    )


def evaluate_interaction_profile(
    *, relation_deltas: Sequence[Mapping[str, Any]],
    crossing_evidence: Sequence[Mapping[str, Any]],
    reference_changes: Sequence[Mapping[str, Any]], as_of_time: str,
) -> dict[str, Any]:
    as_of = _parse_time(as_of_time)
    deltas: list[dict[str, Any]] = []
    crossings: list[dict[str, Any]] = []
    changes: list[dict[str, Any]] = []
    for item in relation_deltas:
        _first_valid_guard(item, as_of)
        _require(item.get("approaching_label") is None, "APPROACHING_LABEL_PROHIBITED")
        _require(item.get("testing_label") is None, "TESTING_LABEL_PROHIBITED")
        deltas.append({key: copy.deepcopy(item[key]) for key in (
            "relation_delta_id", "object_id", "signed_distance_delta",
            "absolute_distance_delta", "absolute_distance_change",
            "previous_topology", "current_topology", "first_valid_time",
        ) if key in item})
    for item in crossing_evidence:
        _require(item.get("same_fixed_object_required") is True, "CROSSING_FIXED_OBJECT_GUARD_REQUIRED")
        crossings.append({key: copy.deepcopy(item[key]) for key in (
            "crossing_evidence_id", "object_id", "crossing_status", "evidence_mode",
            "path_order_known", "previous_side", "current_side",
        ) if key in item})
    for item in reference_changes:
        _first_valid_guard(item, as_of)
        _require(item.get("is_crossing") is False, "REFERENCE_CHANGE_CANNOT_BE_CROSSING")
        changes.append({key: copy.deepcopy(item[key]) for key in (
            "reference_change_id", "previous_object_id", "current_object_id",
            "first_valid_time", "reason", "is_crossing",
        ) if key in item})
    deltas.sort(key=lambda item: str(item.get("relation_delta_id")))
    crossings.sort(key=lambda item: str(item.get("crossing_evidence_id")))
    changes.sort(key=lambda item: str(item.get("reference_change_id")))
    computable = bool(deltas or crossings or changes)
    input_ids = [
        *[str(item.get("relation_delta_id")) for item in relation_deltas],
        *[str(item.get("crossing_evidence_id")) for item in crossing_evidence],
        *[str(item.get("reference_change_id")) for item in reference_changes],
    ]
    source_ids = [
        *[str(item.get("object_id")) for item in relation_deltas],
        *[str(item.get("object_id")) for item in crossing_evidence],
        *[str(item.get("previous_object_id")) for item in reference_changes],
        *[str(item.get("current_object_id")) for item in reference_changes],
    ]
    return _profile(
        axis="INTERACTION", as_of_time=as_of_time,
        input_ids=input_ids, source_ids=source_ids, computable=computable,
        reason_codes=[] if computable else ["NO_RAW_INTERACTION_EVIDENCE"],
        facts={"relation_deltas": deltas, "crossings": crossings, "reference_changes": changes},
    )


def evaluate_quality_profile(
    components: Sequence[Mapping[str, Any]], *, as_of_time: str,
) -> dict[str, Any]:
    as_of = _parse_time(as_of_time)
    records: list[dict[str, Any]] = []
    seen: set[str] = set()
    for component in components:
        _first_valid_guard(component, as_of)
        component_id = str(component["component_id"])
        _require(component_id not in seen, "DUPLICATE_QUALITY_COMPONENT")
        seen.add(component_id)
        records.append({
            "component_id": component_id,
            "status": str(component.get("status", "NOT_COMPUTABLE")),
            "reason_codes": sorted(str(item) for item in component.get("reason_codes", [])),
            "source_ids": sorted(str(item) for item in component.get("source_ids", [])),
            "censored": bool(component.get("censored", False)),
            "ambiguous": bool(component.get("ambiguous", False)),
            "conflict": bool(component.get("conflict", False)),
        })
    records.sort(key=lambda item: item["component_id"])
    computable = bool(records)
    return _profile(
        axis="QUALITY", as_of_time=as_of_time,
        input_ids=sorted(seen), source_ids=[source for item in records for source in item["source_ids"]],
        computable=computable, reason_codes=[] if computable else ["NO_COMPONENT_QUALITY_RECORDS"],
        facts={"components": records, "global_collapsed_status": None},
    )


def build_formula_bundle(outputs: Sequence[Mapping[str, Any]], *, as_of_time: str) -> dict[str, Any]:
    by_axis: dict[str, Mapping[str, Any]] = {}
    as_of = _parse_time(as_of_time)
    for output in outputs:
        _scan_prohibited(output)
        axis = str(output.get("axis"))
        _require(axis in AXIS_ORDER, "BUNDLE_UNKNOWN_AXIS")
        _require(axis not in by_axis, "BUNDLE_DUPLICATE_AXIS")
        _require(output.get("profile_id") == PROFILE_IDS[axis], "BUNDLE_PROFILE_ID_MISMATCH")
        _require(output.get("active") is False and output.get("canonical") is False, "BUNDLE_ACTIVE_OR_CANONICAL_PROFILE")
        _require(output.get("numeric_thresholds") == [], "BUNDLE_NUMERIC_THRESHOLD_PROHIBITED")
        _require(_parse_time(str(output["as_of_time"])) <= as_of, "BUNDLE_FUTURE_PROFILE")
        by_axis[axis] = output
    missing = [axis for axis in AXIS_ORDER if axis not in by_axis]
    _require(not missing, f"BUNDLE_MISSING_AXES:{','.join(missing)}")
    ordered_ids = [str(by_axis[axis]["profile_output_id"]) for axis in AXIS_ORDER]
    computable_count = sum(1 for axis in AXIS_ORDER if by_axis[axis]["computability"] == "COMPUTABLE")
    status = "COMPLETE" if computable_count == len(AXIS_ORDER) else "NOT_COMPUTABLE" if computable_count == 0 else "PARTIAL_NOT_COMPUTABLE"
    body = {
        "schema": "c2_formula_profile_bundle/vnext-r1",
        "bundle_id": _digest("C2.FORMULA.BUNDLE", {"as_of_time": _iso(as_of_time), "output_ids": ordered_ids}),
        "freeze_id": "C2AR.INTEGRATED.SHADOW.FREEZE.v1",
        "as_of_time": _iso(as_of_time), "axis_order": list(AXIS_ORDER),
        "profile_output_ids": ordered_ids,
        "axis_computability": {axis: by_axis[axis]["computability"] for axis in AXIS_ORDER},
        "status": status, "active": False, "canonical": False,
        "selected_profile_id": None, "fallback_profile_id": None,
        "numeric_thresholds": [], "semantic_label": None,
        "authority": "SHADOW_FROZEN_READ_ONLY",
    }
    body["content_sha256"] = hashlib.sha256(_canonical(body)).hexdigest()
    return body
