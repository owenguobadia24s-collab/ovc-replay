"""Inactive, noncanonical C2 vNext transition classification and raw detectors.

Authority is limited to SHADOW_FROZEN_READ_ONLY by CEAR-G7.  This module has
no activation, threshold, semantic, event, episode, parent, publication,
Validation, probability, risk, exposure or execution authority.
"""
from __future__ import annotations

import copy
import hashlib
import json
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any, Mapping, Sequence

UTC = timezone.utc
CLASSIFIER_ID = "C2AR.TRANSITION.CLASSIFIER.v1"
CLASS_PRECEDENCE = (
    "STRUCTURAL_CHANGE",
    "REFERENCE_IDENTITY_CHANGE",
    "COMPUTABILITY_CHANGE",
    "CATEGORICAL_CHANGE",
    "MEASUREMENT_CHANGE",
    "NO_CHANGE",
)
DETECTOR_IDS = {
    "crossing": "C2.DETECTOR.FIXED_OBJECT_CROSSING.v1",
    "touch": "C2.DETECTOR.PRECISION_TOUCH.v1",
    "container": "C2.DETECTOR.CONTAINER_ENTRY_EXIT.v1",
    "distance": "C2.DETECTOR.RAW_DISTANCE_CHANGE.v1",
    "reference": "C2.DETECTOR.REFERENCE_IDENTITY_CHANGE.v1",
    "structure": "C2.DETECTOR.STRUCTURAL_GRAPH_CHANGE.v1",
}
PROHIBITED_KEYS = {
    "future_value",
    "outcome",
    "probability",
    "risk",
    "exposure",
    "trade",
    "trading",
    "execution",
    "position_size",
    "target",
    "stop",
    "event_id",
    "episode_id",
    "semantic_label",
    "approaching",
    "testing",
    "rejecting",
    "accepting",
}


class TransitionDetectorError(ValueError):
    """Raised when a frozen evidence or authority boundary is violated."""


def _require(condition: bool, marker: str) -> None:
    if not condition:
        raise TransitionDetectorError(marker)


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
            if str(key).lower() in PROHIBITED_KEYS:
                raise TransitionDetectorError(f"PROHIBITED_FIELD:{path}.{key}")
            _scan_prohibited(item, f"{path}.{key}")
    elif isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            _scan_prohibited(item, f"{path}[{index}]")


def _get_path(record: Mapping[str, Any], path: str) -> Any:
    value: Any = record
    for token in path.split("."):
        _require(isinstance(value, Mapping) and token in value, f"MISSING_COMPARISON_PATH:{path}")
        value = value[token]
    return value


def _changed_paths(previous: Mapping[str, Any], current: Mapping[str, Any], paths: Sequence[str]) -> list[str]:
    return sorted(path for path in set(paths) if _get_path(previous, path) != _get_path(current, path))


def classify_transition(
    previous: Mapping[str, Any],
    current: Mapping[str, Any],
    *,
    previous_time: str,
    current_time: str,
    profile_id: str,
    scope_id: str,
    measurement_fields: Sequence[str] = (),
    categorical_fields: Sequence[str] = (),
    reference_fields: Sequence[str] = (),
    structural_fields: Sequence[str] = (),
    computability_fields: Sequence[str] = (),
) -> dict[str, Any]:
    """Classify raw evidence differences without assigning market semantics."""
    _scan_prohibited(previous)
    _scan_prohibited(current)
    before = _parse_time(previous_time)
    after = _parse_time(current_time)
    _require(before < after, "TRANSITION_CHRONOLOGY_REQUIRED")
    _require(bool(profile_id), "PROFILE_ID_REQUIRED")
    _require(bool(scope_id), "SCOPE_ID_REQUIRED")
    previous_id = str(previous.get("record_id") or previous.get("profile_output_id") or "")
    current_id = str(current.get("record_id") or current.get("profile_output_id") or "")
    _require(bool(previous_id and current_id), "TRANSITION_RECORD_IDS_REQUIRED")
    if previous.get("profile_id") is not None:
        _require(str(previous["profile_id"]) == profile_id, "PREVIOUS_PROFILE_MISMATCH")
    if current.get("profile_id") is not None:
        _require(str(current["profile_id"]) == profile_id, "CURRENT_PROFILE_MISMATCH")
    if previous.get("scope_id") is not None:
        _require(str(previous["scope_id"]) == scope_id, "PREVIOUS_SCOPE_MISMATCH")
    if current.get("scope_id") is not None:
        _require(str(current["scope_id"]) == scope_id, "CURRENT_SCOPE_MISMATCH")

    changes = {
        "measurements": _changed_paths(previous, current, measurement_fields),
        "categories": _changed_paths(previous, current, categorical_fields),
        "references": _changed_paths(previous, current, reference_fields),
        "structure": _changed_paths(previous, current, structural_fields),
        "computability": _changed_paths(previous, current, computability_fields),
    }
    classes: list[str] = []
    if changes["measurements"]:
        classes.append("MEASUREMENT_CHANGE")
    if changes["categories"]:
        classes.append("CATEGORICAL_CHANGE")
    if changes["references"]:
        classes.append("REFERENCE_IDENTITY_CHANGE")
    if changes["structure"]:
        classes.append("STRUCTURAL_CHANGE")
    if changes["computability"]:
        classes.append("COMPUTABILITY_CHANGE")
    if not classes:
        classes.append("NO_CHANGE")
    classes = [item for item in CLASS_PRECEDENCE if item in classes]
    body = {
        "schema": "c2_transition_record/vnext-r1",
        "classifier_id": CLASSIFIER_ID,
        "previous_record_id": previous_id,
        "current_record_id": current_id,
        "previous_time": _iso(previous_time),
        "current_time": _iso(current_time),
        "profile_id": profile_id,
        "scope_id": scope_id,
        "classes": classes,
        "primary_class": classes[0],
        "changed_paths": changes,
        "computability": "COMPUTABLE",
        "reason_codes": [],
        "active": False,
        "canonical": False,
        "semantic_authority": "NONE",
        "authority": "SHADOW_FROZEN_READ_ONLY",
    }
    body["transition_id"] = _digest("C2.TRANSITION", body)
    return body


def _detector_output(
    detector_id: str,
    *,
    as_of_time: str,
    object_ids: Sequence[str],
    outputs: Sequence[str],
    computable: bool,
    reason_codes: Sequence[str],
    evidence: Mapping[str, Any],
) -> dict[str, Any]:
    _scan_prohibited(evidence)
    _require(detector_id in DETECTOR_IDS.values(), "UNKNOWN_DETECTOR_ID")
    body = {
        "schema": "c2_raw_detector_output/vnext-r1",
        "detector_id": detector_id,
        "as_of_time": _iso(as_of_time),
        "object_ids": sorted({str(item) for item in object_ids if item}),
        "outputs": sorted({str(item) for item in outputs}),
        "computability": "COMPUTABLE" if computable else "NOT_COMPUTABLE",
        "reason_codes": sorted({str(item) for item in reason_codes}),
        "evidence": copy.deepcopy(dict(evidence)),
        "numeric_thresholds": [],
        "active": False,
        "canonical": False,
        "semantic_authority": "NONE",
        "authority": "SHADOW_FROZEN_READ_ONLY",
    }
    _require(bool(body["outputs"]), "DETECTOR_OUTPUT_REQUIRED")
    body["detector_output_id"] = _digest("C2.DETECTOR.OUTPUT", body)
    return body


def _quantized(value: Any, precision: int) -> Decimal:
    _require(isinstance(precision, int) and 0 <= precision <= 18, "SOURCE_PRECISION_INVALID")
    try:
        return Decimal(str(value)).quantize(Decimal(1).scaleb(-precision))
    except (InvalidOperation, ValueError) as exc:
        raise TransitionDetectorError("NUMERIC_VALUE_INVALID") from exc


def detect_fixed_object_crossing(
    *,
    object_id: str,
    object_value: Any,
    ordered_path: Sequence[Mapping[str, Any]],
    source_precision: int,
    as_of_time: str,
    evidence_mode: str,
) -> dict[str, Any]:
    """Detect directional crossing only from a strictly ordered M1/tick path."""
    detector_id = DETECTOR_IDS["crossing"]
    if evidence_mode not in {"M1", "TICK"}:
        return _detector_output(
            detector_id,
            as_of_time=as_of_time,
            object_ids=[object_id],
            outputs=["INSUFFICIENT_ORDERED_PATH"],
            computable=False,
            reason_codes=["EVIDENCE_MODE_HAS_NO_DIRECTIONAL_PATH_AUTHORITY"],
            evidence={"evidence_mode": evidence_mode, "path_count": len(ordered_path)},
        )
    if len(ordered_path) < 2:
        return _detector_output(
            detector_id,
            as_of_time=as_of_time,
            object_ids=[object_id],
            outputs=["INSUFFICIENT_ORDERED_PATH"],
            computable=False,
            reason_codes=["AT_LEAST_TWO_ORDERED_POINTS_REQUIRED"],
            evidence={"evidence_mode": evidence_mode, "path_count": len(ordered_path)},
        )
    target = _quantized(object_value, source_precision)
    times: list[datetime] = []
    signs: list[int] = []
    values: list[str] = []
    for point in ordered_path:
        _require("time" in point and "value" in point, "ORDERED_PATH_POINT_INVALID")
        times.append(_parse_time(str(point["time"])))
        value = _quantized(point["value"], source_precision)
        values.append(str(value))
        signs.append(-1 if value < target else 1 if value > target else 0)
    if any(left >= right for left, right in zip(times, times[1:])):
        return _detector_output(
            detector_id,
            as_of_time=as_of_time,
            object_ids=[object_id],
            outputs=["INSUFFICIENT_ORDERED_PATH"],
            computable=False,
            reason_codes=["PATH_NOT_STRICTLY_ORDERED"],
            evidence={"evidence_mode": evidence_mode, "path_count": len(ordered_path)},
        )
    nonzero = [value for value in signs if value]
    outputs: list[str] = []
    for left, right in zip(nonzero, nonzero[1:]):
        if left < right:
            outputs.append("CROSS_UP")
        elif left > right:
            outputs.append("CROSS_DOWN")
    if not outputs:
        outputs.append("TOUCH_ONLY" if 0 in signs else "NO_CROSS")
    return _detector_output(
        detector_id,
        as_of_time=as_of_time,
        object_ids=[object_id],
        outputs=outputs,
        computable=True,
        reason_codes=[],
        evidence={
            "evidence_mode": evidence_mode,
            "source_precision": source_precision,
            "object_value": str(target),
            "ordered_times": [_iso(item) for item in times],
            "ordered_values": values,
            "relative_signs": signs,
            "same_immutable_object": True,
            "ohlc_directional_authority": False,
        },
    )


def detect_precision_touch(
    *, object_id: str, probe_id: str, raw_topology: str, source_precision: int, as_of_time: str
) -> dict[str, Any]:
    _require(isinstance(source_precision, int) and source_precision >= 0, "SOURCE_PRECISION_INVALID")
    if raw_topology in {"EQUAL", "AT_LOWER", "AT_UPPER", "TOUCH"}:
        output = "TOUCH"
    elif raw_topology in {"BELOW", "ABOVE", "INSIDE", "OUTSIDE"}:
        output = "NO_TOUCH"
    else:
        return _detector_output(
            DETECTOR_IDS["touch"], as_of_time=as_of_time, object_ids=[object_id],
            outputs=["NOT_COMPUTABLE"], computable=False,
            reason_codes=["RAW_TOPOLOGY_UNRECOGNISED_OR_AMBIGUOUS"],
            evidence={"probe_id": probe_id, "raw_topology": raw_topology, "source_precision": source_precision},
        )
    return _detector_output(
        DETECTOR_IDS["touch"], as_of_time=as_of_time, object_ids=[object_id],
        outputs=[output], computable=True, reason_codes=[],
        evidence={"probe_id": probe_id, "raw_topology": raw_topology, "source_precision": source_precision, "proximity_substitution": False},
    )


def detect_container_entry_exit(
    *, container_id: str, previous_topology: str, current_topology: str,
    positive_width: bool, as_of_time: str
) -> dict[str, Any]:
    detector_id = DETECTOR_IDS["container"]
    if not positive_width:
        return _detector_output(
            detector_id, as_of_time=as_of_time, object_ids=[container_id],
            outputs=["NOT_COMPUTABLE"], computable=False,
            reason_codes=["POSITIVE_WIDTH_CONTAINER_REQUIRED"],
            evidence={"previous_topology": previous_topology, "current_topology": current_topology, "same_container_id": True},
        )
    boundary = {"AT_LOWER", "AT_UPPER", "EQUAL"}
    mapping = {
        ("BELOW", "INSIDE"): "ENTRY_FROM_BELOW",
        ("ABOVE", "INSIDE"): "ENTRY_FROM_ABOVE",
        ("INSIDE", "BELOW"): "EXIT_TO_BELOW",
        ("INSIDE", "ABOVE"): "EXIT_TO_ABOVE",
        ("INSIDE", "INSIDE"): "REMAIN_INSIDE",
        ("BELOW", "BELOW"): "REMAIN_OUTSIDE",
        ("ABOVE", "ABOVE"): "REMAIN_OUTSIDE",
    }
    if previous_topology in boundary or current_topology in boundary:
        output, computable, reasons = "BOUNDARY_ONLY", True, []
    elif (previous_topology, current_topology) in mapping:
        output, computable, reasons = mapping[(previous_topology, current_topology)], True, []
    else:
        output, computable, reasons = "NOT_COMPUTABLE", False, ["TOPOLOGY_PAIR_REQUIRES_ORDERED_INTRABAR_PATH_OR_IS_AMBIGUOUS"]
    return _detector_output(
        detector_id, as_of_time=as_of_time, object_ids=[container_id],
        outputs=[output], computable=computable, reason_codes=reasons,
        evidence={
            "previous_topology": previous_topology,
            "current_topology": current_topology,
            "same_container_id": True,
            "positive_width": positive_width,
            "acceptance_or_rejection_authority": False,
        },
    )


def detect_raw_distance_change(
    *, object_id: str, previous_object_id: str, absolute_distance_delta: Any | None,
    relation_delta_id: str, as_of_time: str
) -> dict[str, Any]:
    detector_id = DETECTOR_IDS["distance"]
    if object_id != previous_object_id:
        return _detector_output(
            detector_id, as_of_time=as_of_time, object_ids=[previous_object_id, object_id],
            outputs=["NOT_COMPUTABLE"], computable=False,
            reason_codes=["SAME_IMMUTABLE_OBJECT_REQUIRED"],
            evidence={"relation_delta_id": relation_delta_id, "same_object_id": False},
        )
    if absolute_distance_delta is None:
        return _detector_output(
            detector_id, as_of_time=as_of_time, object_ids=[object_id],
            outputs=["NOT_COMPUTABLE"], computable=False,
            reason_codes=["ABSOLUTE_DISTANCE_DELTA_REQUIRED"],
            evidence={"relation_delta_id": relation_delta_id, "same_object_id": True},
        )
    delta = Decimal(str(absolute_distance_delta))
    output = "DISTANCE_DECREASED" if delta < 0 else "DISTANCE_INCREASED" if delta > 0 else "DISTANCE_UNCHANGED"
    return _detector_output(
        detector_id, as_of_time=as_of_time, object_ids=[object_id],
        outputs=[output], computable=True, reason_codes=[],
        evidence={"relation_delta_id": relation_delta_id, "absolute_distance_delta": str(delta), "same_object_id": True, "approaching_label_authority": False},
    )


def detect_reference_identity_change(
    *, previous_reference_id: str, current_reference_id: str, reference_kind: str, as_of_time: str
) -> dict[str, Any]:
    output = "REFERENCE_CHANGED" if previous_reference_id != current_reference_id else "REFERENCE_UNCHANGED"
    return _detector_output(
        DETECTOR_IDS["reference"], as_of_time=as_of_time,
        object_ids=[previous_reference_id, current_reference_id], outputs=[output],
        computable=True, reason_codes=[],
        evidence={
            "previous_reference_id": previous_reference_id,
            "current_reference_id": current_reference_id,
            "reference_kind": reference_kind,
            "is_crossing": False,
        },
    )


def _edge_id(edge: Any) -> str:
    if isinstance(edge, Mapping):
        return str(edge.get("edge_id") or edge.get("container_edge_id") or edge.get("swing_edge_id") or _digest("EDGE", edge))
    return str(edge)


def detect_structural_graph_change(
    *, previous_graph: Mapping[str, Any], current_graph: Mapping[str, Any],
    supersessions: Sequence[Mapping[str, str]] = (), as_of_time: str
) -> dict[str, Any]:
    detector_id = DETECTOR_IDS["structure"]
    previous_id = str(previous_graph.get("graph_id") or previous_graph.get("container_graph_id") or previous_graph.get("swing_graph_id") or "")
    current_id = str(current_graph.get("graph_id") or current_graph.get("container_graph_id") or current_graph.get("swing_graph_id") or "")
    if previous_graph.get("complete_inventory") is not True or current_graph.get("complete_inventory") is not True:
        return _detector_output(
            detector_id, as_of_time=as_of_time, object_ids=[previous_id, current_id],
            outputs=["NOT_COMPUTABLE"], computable=False,
            reason_codes=["COMPLETE_GRAPH_INVENTORIES_REQUIRED"],
            evidence={"previous_graph_id": previous_id, "current_graph_id": current_id},
        )
    previous_nodes = {str(item) for item in previous_graph.get("node_ids", [])}
    current_nodes = {str(item) for item in current_graph.get("node_ids", [])}
    previous_edges = {_edge_id(item) for item in previous_graph.get("edges", [])}
    current_edges = {_edge_id(item) for item in current_graph.get("edges", [])}
    previous_depths = {str(key): value for key, value in dict(previous_graph.get("depths", {})).items()}
    current_depths = {str(key): value for key, value in dict(current_graph.get("depths", {})).items()}
    superseded = {(str(item["previous_id"]), str(item["current_id"])) for item in supersessions}
    removed_nodes = previous_nodes - current_nodes
    superseded_previous = {left for left, _ in superseded}
    unexplained_removed = removed_nodes - superseded_previous
    outputs: list[str] = []
    if current_nodes - previous_nodes:
        outputs.append("NODE_ADDED")
    if superseded:
        outputs.append("NODE_SUPERSEDED")
    if current_edges - previous_edges:
        outputs.append("EDGE_ADDED")
    if previous_edges - current_edges:
        outputs.append("EDGE_REMOVED")
    shared_depths = previous_depths.keys() & current_depths.keys()
    depth_changed = sorted(key for key in shared_depths if previous_depths[key] != current_depths[key])
    if depth_changed:
        outputs.append("DEPTH_CHANGED")
    reasons: list[str] = []
    computable = not unexplained_removed
    if unexplained_removed:
        outputs.append("NOT_COMPUTABLE")
        reasons.append("REMOVED_NODE_REQUIRES_EXPLICIT_SUPERSESSION")
    if not outputs:
        outputs.append("NO_STRUCTURAL_CHANGE")
    return _detector_output(
        detector_id, as_of_time=as_of_time, object_ids=[previous_id, current_id],
        outputs=outputs, computable=computable, reason_codes=reasons,
        evidence={
            "previous_graph_id": previous_id,
            "current_graph_id": current_id,
            "nodes_added": sorted(current_nodes - previous_nodes),
            "nodes_removed": sorted(removed_nodes),
            "supersessions": [{"previous_id": left, "current_id": right} for left, right in sorted(superseded)],
            "edges_added": sorted(current_edges - previous_edges),
            "edges_removed": sorted(previous_edges - current_edges),
            "depths_changed": depth_changed,
            "complete_inventories": True,
            "regime_authority": False,
        },
    )
