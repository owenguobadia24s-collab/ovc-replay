from __future__ import annotations

from hashlib import sha256
import json
from typing import Any, Iterable, Mapping

from .segmentation import segment_runs

REQUIRED_METHOD_IDS = (
    "C2E_CAUSAL_ADAPTER",
    "RUN_CHANGE_SEGMENTATION",
    "DIRECTIONAL_CHANGE",
    "PELT_REFERENCE",
    "NULL_BOUNDARY_CONTROL",
)


class SegmentationPreregistrationError(ValueError):
    pass


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    ).encode("utf-8")


def logical_sha256(value: Any) -> str:
    return sha256(_canonical(value)).hexdigest()


def _field(item: Any, name: str) -> Any:
    if isinstance(item, Mapping):
        if name not in item:
            raise SegmentationPreregistrationError(f"missing ledger field:{name}")
        return item[name]
    if not hasattr(item, name):
        raise SegmentationPreregistrationError(f"missing ledger field:{name}")
    return getattr(item, name)


def _partition_key(item: Any) -> tuple[str, str, str, str, str]:
    return (
        str(_field(item, "source_release_id")),
        str(_field(item, "instrument_id")),
        str(_field(item, "side")),
        str(_field(item, "scope_id")),
        str(_field(item, "clock_id")),
    )


def compile_uninterrupted_streams(items: Iterable[Any]) -> list[list[dict[str, Any]]]:
    groups: dict[tuple[str, str, str, str, str], list[dict[str, Any]]] = {}
    for item in items:
        row = {
            "record_id": str(_field(item, "record_id")),
            "first_valid_time": str(_field(item, "first_valid_time")),
            "state_key": str(_field(item, "state_key")),
            "reset_reason": _field(item, "reset_reason"),
        }
        if not row["record_id"] or not row["first_valid_time"] or not row["state_key"]:
            raise SegmentationPreregistrationError("record_id, first_valid_time and state_key are required")
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


def run_change_from_c2_ledger(items: Iterable[Any]) -> dict[str, Any]:
    streams = compile_uninterrupted_streams(items)
    all_segments: list[dict[str, Any]] = []
    all_boundaries: list[dict[str, Any]] = []
    for stream_index, stream in enumerate(streams):
        result = segment_runs(stream, state_field="state_key")
        for segment in result["segments"]:
            all_segments.append({"stream_index": stream_index, **segment})
        for boundary in result["boundaries"]:
            all_boundaries.append({"stream_index": stream_index, **boundary})
    payload = {
        "method_id": "RUN_CHANGE_SEGMENTATION",
        "temporal_mode": "ONLINE_CAUSAL",
        "stream_count": len(streams),
        "segments": all_segments,
        "boundaries": all_boundaries,
        "authority_state": "FIXTURE_OR_EXPLICITLY_AUTHORIZED_BOUNDARY_EVIDENCE_ONLY",
    }
    return {**payload, "logical_sha256": logical_sha256(payload)}


def null_boundary_control_from_c2_ledger(items: Iterable[Any]) -> dict[str, Any]:
    streams = compile_uninterrupted_streams(items)
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


def state_change_indicator(items: Iterable[Any]) -> list[list[int]]:
    result: list[list[int]] = []
    for stream in compile_uninterrupted_streams(items):
        values: list[int] = []
        prior: str | None = None
        for row in stream:
            state = row["state_key"]
            values.append(0 if prior is None or state == prior else 1)
            prior = state
        result.append(values)
    return result


def validate_boundary_pack_registry(registry: Mapping[str, Any]) -> str:
    if registry.get("schema") != "ovc-srfdi-segmentation-boundary-pack-registry/v3":
        raise SegmentationPreregistrationError("unexpected registry schema")
    packs = registry.get("packs")
    if not isinstance(packs, list):
        raise SegmentationPreregistrationError("packs list required")
    by_id = {str(pack.get("method_id")): pack for pack in packs if isinstance(pack, Mapping)}
    if tuple(sorted(by_id)) != tuple(sorted(REQUIRED_METHOD_IDS)):
        raise SegmentationPreregistrationError("exact declared segmentation method set required")

    run = by_id["RUN_CHANGE_SEGMENTATION"]
    if run.get("execution_state") != "EXECUTE_T0_BOUNDARY_EVIDENCE":
        raise SegmentationPreregistrationError("run/change execution state drift")
    if run.get("source") != "C2LedgerInput.state_key":
        raise SegmentationPreregistrationError("run/change state source drift")

    dc = by_id["DIRECTIONAL_CHANGE"]
    thresholds = dc.get("threshold_surface")
    if not isinstance(thresholds, list) or not thresholds:
        raise SegmentationPreregistrationError("directional-change threshold surface required")
    if any(float(value) <= 0 for value in thresholds):
        raise SegmentationPreregistrationError("directional-change thresholds must be positive")
    if not str(dc.get("execution_state", "")).startswith("NOT_EXECUTED_"):
        raise SegmentationPreregistrationError("directional-change is not executable in v0.3")

    pelt = by_id["PELT_REFERENCE"]
    penalties = pelt.get("penalty_surface")
    lengths = pelt.get("minimum_segment_length_surface")
    if not isinstance(penalties, list) or not penalties:
        raise SegmentationPreregistrationError("PELT penalty surface required")
    if not isinstance(lengths, list) or not lengths:
        raise SegmentationPreregistrationError("PELT minimum-length surface required")
    if any(float(value) < 0 for value in penalties):
        raise SegmentationPreregistrationError("PELT penalties must be non-negative")
    if any(int(value) <= 0 for value in lengths):
        raise SegmentationPreregistrationError("PELT minimum lengths must be positive")
    if pelt.get("execution_state") != "NOT_EXECUTED_CAPACITY_UNRESOLVED_AT_T0":
        raise SegmentationPreregistrationError("PELT T0 capacity disposition drift")

    null = by_id["NULL_BOUNDARY_CONTROL"]
    if null.get("execution_state") != "EXECUTE_T0_CONTROL":
        raise SegmentationPreregistrationError("null control execution state drift")

    if registry.get("t0_execution_policy", {}).get("silent_method_drop") != "FORBIDDEN":
        raise SegmentationPreregistrationError("silent method drop must be forbidden")
    return logical_sha256(registry)
