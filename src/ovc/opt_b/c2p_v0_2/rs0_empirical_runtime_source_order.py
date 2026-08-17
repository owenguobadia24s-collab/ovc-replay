from __future__ import annotations

"""Bounded source-order recovery for the C2P2-RS0 spooled execution adapter.

This layer changes source sequencing only. It preserves every source row byte-for-byte
at the Python mapping level, buffers only one equal-first_valid_time group per input
stream, orders that group by source_record_id, and delegates the global k-way merge
and scientific runtime semantics to the already-qualified spooled adapter.
"""

from typing import Any, Iterable, Iterator, Mapping, Sequence

from .rs0_empirical_runtime_streaming import (
    RS0SpooledRuntimeError,
    merge_canonical_source_streams,
)
from .rs0_empirical_semantics import normalize_candidate_source_row


SOURCE_ORDER_ADAPTER_SCHEMA = "ovc-c2p2-rs0-source-order-recovery-adapter/v1"
SOURCE_ORDER_ADAPTER_ID = "C2P2_RS0_SOURCE_ORDER_RECOVERY_ADAPTER_v0_2"


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
    """Canonicalize only equal-time groups while preserving population and rows.

    Input first_valid_time must be monotonically nondecreasing. Equal-time groups
    may arrive in arbitrary source_record_id order and are buffered one group at a
    time, then emitted in strict source_record_id order. A genuinely decreasing
    first_valid_time fails closed.
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


def merge_source_streams_with_tie_canonicalization(
    streams: Sequence[Iterable[Mapping[str, Any]]],
) -> Iterator[Mapping[str, Any]]:
    """Recover canonical source sequencing without changing scientific semantics."""

    canonical_streams = [canonicalize_equal_time_groups(stream) for stream in streams]
    yield from merge_canonical_source_streams(canonical_streams)
