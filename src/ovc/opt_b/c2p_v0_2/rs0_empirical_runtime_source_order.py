from __future__ import annotations

"""Bounded source-order recovery for the C2P2-RS0 spooled execution adapter.

The exact RS0 C2 source files are envelopes created by the frozen source
materialiser as contiguous source-kind segments (levels, then containers, then
parent observations).  The frozen reference runtime globally sorts the complete
population by ``(first_valid_time, source_record_id)`` before applying any
scientific semantics.  This adapter recovers that ordering without changing
rows or core runtime semantics:

1. validate the documented source-kind segment envelope;
2. treat each contiguous source-kind segment as a logical input stream;
3. buffer only one equal-first_valid_time group inside each logical stream and
   order that group by source_record_id;
4. k-way merge those canonical logical streams.

A genuinely decreasing first_valid_time *within one logical source-kind stream*
still fails closed. Population materialisation, row mutation, sampling and
precision changes remain forbidden.
"""

from collections.abc import Callable
from typing import Any, Iterable, Iterator, Mapping, Sequence

from .rs0_empirical_runtime_streaming import (
    RS0SpooledRuntimeError,
    merge_canonical_source_streams,
)
from .rs0_empirical_semantics import normalize_candidate_source_row


SOURCE_ORDER_ADAPTER_SCHEMA = "ovc-c2p2-rs0-source-order-recovery-adapter/v2"
SOURCE_ORDER_ADAPTER_ID = "C2P2_RS0_SOURCE_ORDER_RECOVERY_ADAPTER_v0_2"
C2_SOURCE_KIND_ORDER = (
    "C2_LEVEL",
    "C2_CONTAINER",
    "C2_PARENT_OBSERVATION",
)


def _flush_equal_time_group(
    group: list[tuple[str, Mapping[str, Any]]],
) -> Iterator[Mapping[str, Any]]:
    previous_source_id: str | None = None
    for source_id, row in sorted(group, key=lambda item: item[0]):
        if previous_source_id is not None and source_id <= previous_source_id:
            raise RS0SpooledRuntimeError(
                f"RS0_SOURCE_ORDER_DUPLICATE_OR_NONUNIQUE_ID:{source_id}"
            )
        previous_source_id = source_id
        yield row


def canonicalize_equal_time_groups(
    stream: Iterable[Mapping[str, Any]],
) -> Iterator[Mapping[str, Any]]:
    """Canonicalize equal-time ties inside one logical source stream.

    ``first_valid_time`` must be monotonically nondecreasing. Equal-time rows
    may arrive in arbitrary source_record_id order and are buffered one time
    group at a time. A genuine time decrease fails closed.
    """

    current_time: str | None = None
    previous_time: str | None = None
    group: list[tuple[str, Mapping[str, Any]]] = []

    for row in stream:
        material = normalize_candidate_source_row(row)
        first_valid_time = str(material["first_valid_time"])
        source_record_id = str(material["source_record_id"])

        if previous_time is not None and first_valid_time < previous_time:
            raise RS0SpooledRuntimeError(
                "RS0_SOURCE_ORDER_FIRST_VALID_TIME_DECREASING"
            )

        if current_time is None:
            current_time = first_valid_time
        elif first_valid_time != current_time:
            yield from _flush_equal_time_group(group)
            group = []
            current_time = first_valid_time

        group.append((source_record_id, row))
        previous_time = first_valid_time

    if group:
        yield from _flush_equal_time_group(group)


def inspect_source_kind_segments(
    stream: Iterable[Mapping[str, Any]],
    *,
    kind_order: Sequence[str] = C2_SOURCE_KIND_ORDER,
) -> dict[str, Any]:
    """Validate the frozen materialiser's contiguous source-kind envelope.

    Time decreases are permitted only at a transition to a later documented
    source-kind segment. Within any one kind, first_valid_time must remain
    monotonically nondecreasing. Re-entry into an earlier kind fails closed.
    """

    kind_positions = {kind: index for index, kind in enumerate(kind_order)}
    current_kind_position = -1
    previous_kind: str | None = None
    previous_raw_time: str | None = None
    previous_time_by_kind: dict[str, str] = {}
    rows_by_kind = {kind: 0 for kind in kind_order}
    rows_by_side: dict[str, int] = {}
    rows_by_clock: dict[str, int] = {}
    transitions: list[dict[str, str]] = []
    boundary_time_decreases = 0
    raw_rows = 0

    for row in stream:
        material = normalize_candidate_source_row(row)
        source_kind = str(row.get("source_record_kind") or "")
        if source_kind not in kind_positions:
            raise RS0SpooledRuntimeError(
                f"RS0_SOURCE_ORDER_UNEXPECTED_SOURCE_KIND:{source_kind}"
            )
        position = kind_positions[source_kind]
        if position < current_kind_position:
            raise RS0SpooledRuntimeError(
                f"RS0_SOURCE_ORDER_KIND_SEGMENT_REENTRY:{source_kind}"
            )
        if position > current_kind_position:
            if previous_kind is not None:
                transitions.append({"from": previous_kind, "to": source_kind})
            current_kind_position = position

        first_valid_time = str(material["first_valid_time"])
        previous_kind_time = previous_time_by_kind.get(source_kind)
        if previous_kind_time is not None and first_valid_time < previous_kind_time:
            raise RS0SpooledRuntimeError(
                f"RS0_SOURCE_ORDER_FIRST_VALID_TIME_DECREASING_WITHIN_KIND:{source_kind}"
            )
        if previous_raw_time is not None and first_valid_time < previous_raw_time:
            if source_kind == previous_kind:
                raise RS0SpooledRuntimeError(
                    f"RS0_SOURCE_ORDER_FIRST_VALID_TIME_DECREASING_WITHIN_KIND:{source_kind}"
                )
            boundary_time_decreases += 1

        previous_time_by_kind[source_kind] = first_valid_time
        previous_raw_time = first_valid_time
        previous_kind = source_kind
        rows_by_kind[source_kind] += 1
        side = str(row.get("side") or "")
        clock = str(row.get("clock") or "")
        rows_by_side[side] = rows_by_side.get(side, 0) + 1
        rows_by_clock[clock] = rows_by_clock.get(clock, 0) + 1
        raw_rows += 1

    if raw_rows == 0:
        raise RS0SpooledRuntimeError("RS0_SOURCE_ORDER_EMPTY_SOURCE_ENVELOPE")

    observed_kinds = [kind for kind in kind_order if rows_by_kind[kind] > 0]
    return {
        "schema": "ovc-c2p2-rs0-source-kind-segment-inspection/v1",
        "raw_rows": raw_rows,
        "kind_order": list(kind_order),
        "observed_kinds": observed_kinds,
        "rows_by_kind": rows_by_kind,
        "rows_by_side": dict(sorted(rows_by_side.items())),
        "rows_by_clock": dict(sorted(rows_by_clock.items())),
        "segment_transitions": transitions,
        "boundary_time_decreases": boundary_time_decreases,
        "within_kind_time_decreases": 0,
        "status": "PASS",
    }


def filter_source_kind(
    stream: Iterable[Mapping[str, Any]],
    expected_kind: str,
    *,
    allowed_kinds: Sequence[str] = C2_SOURCE_KIND_ORDER,
) -> Iterator[Mapping[str, Any]]:
    """Project one documented logical source-kind stream without row mutation."""

    allowed = set(allowed_kinds)
    if expected_kind not in allowed:
        raise RS0SpooledRuntimeError(
            f"RS0_SOURCE_ORDER_EXPECTED_KIND_INVALID:{expected_kind}"
        )
    for row in stream:
        source_kind = str(row.get("source_record_kind") or "")
        if source_kind not in allowed:
            raise RS0SpooledRuntimeError(
                f"RS0_SOURCE_ORDER_UNEXPECTED_SOURCE_KIND:{source_kind}"
            )
        if source_kind == expected_kind:
            yield row


def logical_streams_from_factories(
    stream_factories: Sequence[Callable[[], Iterable[Mapping[str, Any]]]],
    *,
    kind_order: Sequence[str] = C2_SOURCE_KIND_ORDER,
) -> list[Iterable[Mapping[str, Any]]]:
    """Create canonical logical streams from immutable re-readable envelopes."""

    logical_streams: list[Iterable[Mapping[str, Any]]] = []
    for factory in stream_factories:
        for source_kind in kind_order:
            logical_streams.append(
                canonicalize_equal_time_groups(
                    filter_source_kind(factory(), source_kind, allowed_kinds=kind_order)
                )
            )
    return logical_streams


def merge_source_factories_with_kind_segmentation(
    stream_factories: Sequence[Callable[[], Iterable[Mapping[str, Any]]]],
    *,
    kind_order: Sequence[str] = C2_SOURCE_KIND_ORDER,
) -> Iterator[Mapping[str, Any]]:
    """Recover exact frozen-runtime canonical order from source envelopes."""

    yield from merge_canonical_source_streams(
        logical_streams_from_factories(stream_factories, kind_order=kind_order)
    )


def merge_source_streams_with_tie_canonicalization(
    streams: Sequence[Iterable[Mapping[str, Any]]],
) -> Iterator[Mapping[str, Any]]:
    """Legacy helper for already-logical monotone streams used by qualification."""

    canonical_streams = [canonicalize_equal_time_groups(stream) for stream in streams]
    yield from merge_canonical_source_streams(canonical_streams)
