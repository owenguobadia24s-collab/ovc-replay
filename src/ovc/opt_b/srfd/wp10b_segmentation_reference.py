from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Iterable, Mapping, Sequence

from .serialization import logical_sha256, stable_id


class SegmentationReferenceError(ValueError):
    def __init__(self, reason_code: str, detail: str) -> None:
        self.reason_code = reason_code
        self.detail = detail
        super().__init__(f"{reason_code}: {detail}")


def _field(item: Any, name: str) -> Any:
    if isinstance(item, Mapping):
        if name not in item:
            raise SegmentationReferenceError("SEGMENTATION_REFERENCE_SCHEMA_FAILURE", name)
        return item[name]
    if not hasattr(item, name):
        raise SegmentationReferenceError("SEGMENTATION_REFERENCE_SCHEMA_FAILURE", name)
    return getattr(item, name)


def _partition_key(item: Any) -> tuple[str, str, str, str, str]:
    return (
        str(_field(item, "source_release_id")),
        str(_field(item, "instrument_id")),
        str(_field(item, "side")),
        str(_field(item, "scope_id")),
        str(_field(item, "clock_id")),
    )


def _canonical_time(value: Any) -> str:
    text = str(value).strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise SegmentationReferenceError(
            "SEGMENTATION_REFERENCE_SCHEMA_FAILURE", f"invalid first_valid_time:{value}"
        ) from exc
    if parsed.tzinfo is None:
        raise SegmentationReferenceError(
            "SEGMENTATION_REFERENCE_SCHEMA_FAILURE", "timezone-aware first_valid_time required"
        )
    return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _time_key(value: Any) -> datetime:
    text = _canonical_time(value)
    return datetime.fromisoformat(text[:-1] + "+00:00")


def reference_compile_uninterrupted_streams(items: Iterable[Any]) -> list[list[dict[str, Any]]]:
    """Independent transcription of the frozen v0.3 stream contract.

    This function intentionally does not import or call segmentation_prereg or
    segmentation.segment_runs. It is a separately testable reference path for
    execution-binding assurance only.
    """
    groups: dict[tuple[str, str, str, str, str], list[dict[str, Any]]] = {}
    for item in items:
        row = {
            "record_id": str(_field(item, "record_id")),
            "first_valid_time": str(_field(item, "first_valid_time")),
            "state_key": str(_field(item, "state_key")),
            "reset_reason": _field(item, "reset_reason"),
        }
        if not row["record_id"] or not row["first_valid_time"] or not row["state_key"]:
            raise SegmentationReferenceError(
                "SEGMENTATION_REFERENCE_SCHEMA_FAILURE",
                "record_id, first_valid_time and state_key are required",
            )
        groups.setdefault(_partition_key(item), []).append(row)

    streams: list[list[dict[str, Any]]] = []
    for key in sorted(groups):
        rows = sorted(groups[key], key=lambda row: (row["first_valid_time"], row["record_id"]))
        current: list[dict[str, Any]] = []
        for row in rows:
            if row["reset_reason"] is not None and current:
                streams.append(current)
                current = []
            current.append(row)
        if current:
            streams.append(current)
    return streams


def _ordered_stream(stream: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    values: list[dict[str, Any]] = []
    for item in stream:
        row = dict(item)
        if not str(row.get("record_id", "")).strip():
            raise SegmentationReferenceError(
                "SEGMENTATION_REFERENCE_SCHEMA_FAILURE", "record_id required"
            )
        row["first_valid_time"] = _canonical_time(row.get("first_valid_time"))
        values.append(row)
    return sorted(values, key=lambda row: (_time_key(row["first_valid_time"]), row["record_id"]))


def _segment_payload(members: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    payload = {
        "method_id": "RUN_CHANGE_SEGMENTATION",
        "temporal_mode": "ONLINE_CAUSAL",
        "member_record_ids": [str(item["record_id"]) for item in members],
        "onset_time": members[0]["first_valid_time"],
        "end_time": members[-1]["first_valid_time"],
        "first_valid_time": members[0]["first_valid_time"],
        "censored": False,
        "censor_reason": None,
        "authority_state": "FIXTURE_ONLY",
    }
    return {
        **payload,
        "segment_id": stable_id("SRFD.SEG.", payload),
        "logical_hash": logical_sha256(payload),
    }


def _reference_segment_runs(stream: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    values = _ordered_stream(stream)
    if not values:
        raise SegmentationReferenceError(
            "SEGMENTATION_REFERENCE_SCHEMA_FAILURE", "at least one record required"
        )
    groups: list[list[dict[str, Any]]] = []
    current: list[dict[str, Any]] = []
    last_state: str | None = None
    boundaries: list[dict[str, Any]] = []
    for item in values:
        state = str(item["state_key"])
        if current and state != last_state:
            groups.append(current)
            event_payload = {
                "event_type": "STATE_CHANGE",
                "from_record_id": current[-1]["record_id"],
                "to_record_id": item["record_id"],
                "first_valid_time": item["first_valid_time"],
            }
            boundaries.append(
                {
                    **event_payload,
                    "boundary_id": stable_id("SRFD.BND.", event_payload),
                }
            )
            current = []
        current.append(item)
        last_state = state
    groups.append(current)
    ordered_boundaries = sorted(
        boundaries,
        key=lambda item: (
            _time_key(item["first_valid_time"]),
            str(item.get("event_type", "")),
            str(item.get("boundary_id", "")),
        ),
    )
    return {
        "segments": [_segment_payload(group) for group in groups],
        "boundaries": ordered_boundaries,
    }


def reference_run_change_from_c2_ledger(items: Iterable[Any]) -> dict[str, Any]:
    streams = reference_compile_uninterrupted_streams(items)
    all_segments: list[dict[str, Any]] = []
    all_boundaries: list[dict[str, Any]] = []
    for stream_index, stream in enumerate(streams):
        result = _reference_segment_runs(stream)
        all_segments.extend(
            {"stream_index": stream_index, **segment}
            for segment in result["segments"]
        )
        all_boundaries.extend(
            {"stream_index": stream_index, **boundary}
            for boundary in result["boundaries"]
        )
    payload = {
        "method_id": "RUN_CHANGE_SEGMENTATION",
        "temporal_mode": "ONLINE_CAUSAL",
        "stream_count": len(streams),
        "segments": all_segments,
        "boundaries": all_boundaries,
        "authority_state": "FIXTURE_OR_EXPLICITLY_AUTHORIZED_BOUNDARY_EVIDENCE_ONLY",
    }
    return {**payload, "logical_sha256": logical_sha256(payload)}


def reference_null_boundary_control_from_c2_ledger(items: Iterable[Any]) -> dict[str, Any]:
    streams = reference_compile_uninterrupted_streams(items)
    segments: list[dict[str, Any]] = []
    for stream_index, stream in enumerate(streams):
        first = stream[0]
        last = stream[-1]
        identity = {
            "stream_index": stream_index,
            "first_record_id": first["record_id"],
            "last_record_id": last["record_id"],
            "first_valid_time": first["first_valid_time"],
            "control_first_valid_time": last["first_valid_time"],
        }
        segments.append(
            {
                "segment_id": "SRFD.NULL." + logical_sha256(identity),
                "stream_index": stream_index,
                "start_record_id": first["record_id"],
                "end_record_id": last["record_id"],
                "onset_time": first["first_valid_time"],
                "first_valid_time": last["first_valid_time"],
                "status": "CENSORED_SAMPLE_END",
                "structural_boundary_count": 0,
            }
        )
    payload = {
        "method_id": "NULL_BOUNDARY_CONTROL",
        "temporal_mode": "RETROSPECTIVE_CONTROL",
        "stream_count": len(streams),
        "segments": segments,
        "boundaries": [],
        "authority_state": "FIXTURE_OR_EXPLICITLY_AUTHORIZED_CONTROL_ONLY",
    }
    return {**payload, "logical_sha256": logical_sha256(payload)}


def reference_execute_segmentation(items: Iterable[Any], method_id: str) -> dict[str, Any]:
    values = list(items)
    if method_id == "RUN_CHANGE_SEGMENTATION":
        return reference_run_change_from_c2_ledger(values)
    if method_id == "NULL_BOUNDARY_CONTROL":
        return reference_null_boundary_control_from_c2_ledger(values)
    raise SegmentationReferenceError("UNDECLARED_METHOD_OR_DEPENDENCY", method_id)


def assert_structural_invariants(method_id: str, result: Mapping[str, Any]) -> dict[str, int]:
    counts = {
        "stream_count": int(result["stream_count"]),
        "segment_count": len(result["segments"]),
        "boundary_count": len(result["boundaries"]),
    }
    if method_id == "RUN_CHANGE_SEGMENTATION":
        if counts["segment_count"] != counts["stream_count"] + counts["boundary_count"]:
            raise SegmentationReferenceError(
                "SEGMENTATION_STRUCTURAL_INVARIANT_FAILURE",
                "RUN_CHANGE requires segment_count = stream_count + boundary_count",
            )
    elif method_id == "NULL_BOUNDARY_CONTROL":
        if counts["segment_count"] != counts["stream_count"] or counts["boundary_count"] != 0:
            raise SegmentationReferenceError(
                "SEGMENTATION_STRUCTURAL_INVARIANT_FAILURE",
                "NULL control requires segment_count = stream_count and boundary_count = 0",
            )
    else:
        raise SegmentationReferenceError("UNDECLARED_METHOD_OR_DEPENDENCY", method_id)
    return counts
