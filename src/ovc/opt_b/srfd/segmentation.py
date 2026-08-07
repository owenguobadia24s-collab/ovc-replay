from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from enum import Enum
from typing import Any, Iterable, Mapping, Sequence

from .serialization import logical_sha256, stable_id


class TemporalMode(str, Enum):
    ONLINE_CAUSAL = "ONLINE_CAUSAL"
    CONFIRMATION_DELAYED = "CONFIRMATION_DELAYED"
    RETROSPECTIVE = "RETROSPECTIVE"


class SegmentationError(ValueError):
    def __init__(self, reason_code: str, detail: str) -> None:
        self.reason_code = reason_code
        self.detail = detail
        super().__init__(f"{reason_code}: {detail}")


def _time(value: Any) -> datetime:
    text = str(value).strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise SegmentationError("TIME_PARENT_NOT_FIRST_VALID", f"invalid time {value}") from exc
    if parsed.tzinfo is None:
        raise SegmentationError("TIME_PARENT_NOT_FIRST_VALID", "timezone-aware time required")
    return parsed.astimezone(timezone.utc)


def _canonical_time(value: Any) -> str:
    return _time(value).isoformat().replace("+00:00", "Z")


def _number(value: Any) -> Decimal:
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise SegmentationError("QA_SCHEMA_FAILURE", f"non-numeric value {value}") from exc
    if not result.is_finite():
        raise SegmentationError("QA_SCHEMA_FAILURE", "non-finite segmentation value")
    return result


def _ordered(records: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    values = [dict(item) for item in records]
    for item in values:
        if not str(item.get("record_id", "")).strip():
            raise SegmentationError("QA_SCHEMA_FAILURE", "record_id required")
        item["first_valid_time"] = _canonical_time(item.get("first_valid_time"))
    return sorted(values, key=lambda item: (_time(item["first_valid_time"]), item["record_id"]))


def _segment_payload(method_id: str, mode: TemporalMode, members: Sequence[Mapping[str, Any]], *, censored: bool = False, censor_reason: str | None = None) -> dict[str, Any]:
    ids = [str(item["record_id"]) for item in members]
    payload = {
        "method_id": method_id,
        "temporal_mode": mode.value,
        "member_record_ids": ids,
        "onset_time": members[0]["first_valid_time"],
        "end_time": members[-1]["first_valid_time"],
        "first_valid_time": members[-1]["first_valid_time"] if mode == TemporalMode.RETROSPECTIVE else members[0]["first_valid_time"],
        "censored": censored,
        "censor_reason": censor_reason,
        "authority_state": "FIXTURE_ONLY",
    }
    return {**payload, "segment_id": stable_id("SRFD.SEG.", payload), "logical_hash": logical_sha256(payload)}


def segment_runs(records: Iterable[Mapping[str, Any]], *, state_field: str) -> dict[str, Any]:
    values = _ordered(records)
    if not values:
        raise SegmentationError("QA_SCHEMA_FAILURE", "at least one record required")
    groups: list[list[dict[str, Any]]] = []
    current: list[dict[str, Any]] = []
    last: Any = object()
    boundaries: list[dict[str, Any]] = []
    for item in values:
        if state_field not in item:
            raise SegmentationError("REP_REQUIRED_DIMENSION_MISSING", state_field)
        state = item[state_field]
        if current and state != last:
            groups.append(current)
            event_payload = {
                "event_type": "STATE_CHANGE",
                "from_record_id": current[-1]["record_id"],
                "to_record_id": item["record_id"],
                "first_valid_time": item["first_valid_time"],
            }
            boundaries.append({**event_payload, "boundary_id": stable_id("SRFD.BND.", event_payload)})
            current = []
        current.append(item)
        last = state
    groups.append(current)
    segments = [_segment_payload("RUN_CHANGE_SEGMENTATION", TemporalMode.ONLINE_CAUSAL, group) for group in groups]
    return {
        "method_id": "RUN_CHANGE_SEGMENTATION",
        "temporal_mode": TemporalMode.ONLINE_CAUSAL.value,
        "segments": segments,
        "boundary_events": order_boundary_events(boundaries),
        "authority_state": "FIXTURE_ONLY",
    }


def directional_change(records: Iterable[Mapping[str, Any]], *, value_field: str, threshold: Any) -> dict[str, Any]:
    values = _ordered(records)
    if len(values) < 2:
        raise SegmentationError("QA_SCHEMA_FAILURE", "directional change needs at least two observations")
    limit = _number(threshold)
    if limit <= 0:
        raise SegmentationError("DIST_INVALID_PARAMETER", "directional-change threshold must be positive")
    prices = [_number(item.get(value_field)) for item in values]
    extreme_index = 0
    direction: str | None = None
    events: list[dict[str, Any]] = []
    for index in range(1, len(values)):
        price = prices[index]
        extreme = prices[extreme_index]
        if direction is None:
            if price - extreme >= limit:
                direction = "UP"
                payload = {"event_type":"DIRECTIONAL_CHANGE_UP","onset_record_id":values[extreme_index]["record_id"],"confirmation_record_id":values[index]["record_id"],"onset_time":values[extreme_index]["first_valid_time"],"first_valid_time":values[index]["first_valid_time"],"threshold":str(limit)}
                events.append({**payload,"boundary_id":stable_id("SRFD.BND.",payload)})
                extreme_index = index
            elif extreme - price >= limit:
                direction = "DOWN"
                payload = {"event_type":"DIRECTIONAL_CHANGE_DOWN","onset_record_id":values[extreme_index]["record_id"],"confirmation_record_id":values[index]["record_id"],"onset_time":values[extreme_index]["first_valid_time"],"first_valid_time":values[index]["first_valid_time"],"threshold":str(limit)}
                events.append({**payload,"boundary_id":stable_id("SRFD.BND.",payload)})
                extreme_index = index
            elif abs(price - extreme) > 0:
                extreme_index = index if price < extreme else extreme_index
        elif direction == "UP":
            if price > extreme:
                extreme_index = index
            elif extreme - price >= limit:
                payload = {"event_type":"DIRECTIONAL_CHANGE_DOWN","onset_record_id":values[extreme_index]["record_id"],"confirmation_record_id":values[index]["record_id"],"onset_time":values[extreme_index]["first_valid_time"],"first_valid_time":values[index]["first_valid_time"],"threshold":str(limit)}
                events.append({**payload,"boundary_id":stable_id("SRFD.BND.",payload)})
                direction = "DOWN"; extreme_index = index
        else:
            if price < extreme:
                extreme_index = index
            elif price - extreme >= limit:
                payload = {"event_type":"DIRECTIONAL_CHANGE_UP","onset_record_id":values[extreme_index]["record_id"],"confirmation_record_id":values[index]["record_id"],"onset_time":values[extreme_index]["first_valid_time"],"first_valid_time":values[index]["first_valid_time"],"threshold":str(limit)}
                events.append({**payload,"boundary_id":stable_id("SRFD.BND.",payload)})
                direction = "UP"; extreme_index = index
    return {"method_id":"DIRECTIONAL_CHANGE","temporal_mode":TemporalMode.CONFIRMATION_DELAYED.value,"boundary_events":order_boundary_events(events),"authority_state":"FIXTURE_ONLY"}


def pelt_reference(values: Sequence[Any], *, penalty: Any) -> dict[str, Any]:
    """Small exact retrospective penalised-SSE reference for fixture benchmarking.

    This is deliberately not exposed as causal C2E state. It is a standard-library
    dynamic-programming reference suitable only for bounded fixture populations.
    """
    signal = [_number(value) for value in values]
    n = len(signal)
    if n == 0:
        raise SegmentationError("QA_SCHEMA_FAILURE", "signal required")
    beta = _number(penalty)
    if beta < 0:
        raise SegmentationError("DIST_INVALID_PARAMETER", "penalty must be non-negative")
    prefix = [Decimal("0")]
    prefix_sq = [Decimal("0")]
    for value in signal:
        prefix.append(prefix[-1] + value)
        prefix_sq.append(prefix_sq[-1] + value * value)
    def cost(start: int, end: int) -> Decimal:
        count = Decimal(end - start)
        total = prefix[end] - prefix[start]
        total_sq = prefix_sq[end] - prefix_sq[start]
        return total_sq - (total * total / count)
    best = [Decimal("Infinity")] * (n + 1)
    path: list[list[int]] = [[] for _ in range(n + 1)]
    best[0] = -beta
    for end in range(1, n + 1):
        candidates: list[tuple[Decimal, list[int], int]] = []
        for start in range(0, end):
            score = best[start] + cost(start, end) + beta
            changes = path[start] + ([start] if start else [])
            candidates.append((score, changes, start))
        score, changes, _ = min(candidates, key=lambda item: (item[0], item[1], item[2]))
        best[end] = score
        path[end] = changes
    points = path[n]
    starts = [0] + points
    ends = points + [n]
    return {
        "method_id": "PELT_REFERENCE",
        "temporal_mode": TemporalMode.RETROSPECTIVE.value,
        "changepoints": points,
        "segments": [{"start_index": start, "end_index_exclusive": end} for start, end in zip(starts, ends)],
        "objective": format(best[n], "f"),
        "authority_state": "FIXTURE_ONLY",
    }


def assert_temporal_join_allowed(source_mode: str | TemporalMode, target_mode: str | TemporalMode) -> None:
    source = TemporalMode(source_mode)
    target = TemporalMode(target_mode)
    if source == TemporalMode.RETROSPECTIVE and target in {TemporalMode.ONLINE_CAUSAL, TemporalMode.CONFIRMATION_DELAYED}:
        raise SegmentationError("QA_RETROSPECTIVE_ISOLATION_FAILURE", "retrospective result cannot write or masquerade as causal evidence")


def lineage_event(kind: str, *, parent_ids: Sequence[str], child_ids: Sequence[str]) -> dict[str, Any]:
    relation = kind.upper()
    if relation not in {"SPLIT", "MERGE", "NEST", "REPARENT"}:
        raise SegmentationError("QA_SCHEMA_FAILURE", f"unsupported lineage relation {kind}")
    payload = {"relation":relation,"parent_ids":sorted(set(parent_ids)),"child_ids":sorted(set(child_ids)),"append_only":True}
    return {**payload,"lineage_edge_id":stable_id("SRFD.LINEAGE.",payload)}


def censor_segment(segment: Mapping[str, Any], *, reason: str) -> dict[str, Any]:
    payload = {key:value for key,value in segment.items() if key not in {"segment_id","logical_hash","censored","censor_reason"}}
    payload.update({"censored":True,"censor_reason":reason})
    return {**payload,"segment_id":stable_id("SRFD.SEG.",payload),"logical_hash":logical_sha256(payload)}


def order_boundary_events(events: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    values = [dict(item) for item in events]
    return sorted(values, key=lambda item: (_time(item["first_valid_time"]), str(item.get("event_type", "")), str(item.get("boundary_id", ""))))
