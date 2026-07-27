from __future__ import annotations

from datetime import datetime, timedelta
from typing import Mapping, Sequence

from . import dukascopy_intake as base
from .gapped_source_contract import (
    COVERAGE_STATE,
    END,
    EXPECTED_COMPLETE_H1,
    EXPECTED_GAP_RUNS,
    EXPECTED_H1_ROWS,
    EXPECTED_M1_ROWS,
    EXPECTED_MISSING,
    RecoveryError,
    SLICE_ID,
    START,
    utc,
)


def expected_minutes() -> list[datetime]:
    result: list[datetime] = []
    cursor = START
    while cursor < END:
        result.append(cursor)
        cursor += timedelta(minutes=1)
    return result


def gap_runs(
    missing: Sequence[datetime],
) -> list[dict[str, object]]:
    ordered = sorted(missing)
    if not ordered:
        return []
    groups: list[list[datetime]] = [[ordered[0]]]
    for timestamp in ordered[1:]:
        if timestamp == groups[-1][-1] + timedelta(minutes=1):
            groups[-1].append(timestamp)
        else:
            groups.append([timestamp])
    return [
        {
            "start_utc": utc(group[0]),
            "end_utc_inclusive": utc(group[-1]),
            "missing_minute_count": len(group),
        }
        for group in groups
    ]


def m1_result(
    rows: Sequence[base.CandleRow],
    side: str,
) -> dict[str, object]:
    timestamps = [row.timestamp_utc for row in rows]
    unique = set(timestamps)
    expected = set(expected_minutes())
    missing = sorted(expected - unique)
    runs = gap_runs(missing)
    duplicates = len(timestamps) - len(unique)
    non_monotonic = sum(
        1
        for left, right in zip(timestamps, timestamps[1:])
        if right <= left
    )
    boundary = (
        bool(timestamps)
        and timestamps[0] == START
        and timestamps[-1] == END - timedelta(minutes=1)
    )
    exact = (
        len(timestamps) == EXPECTED_M1_ROWS
        and len(missing) == EXPECTED_MISSING
        and len(runs) == EXPECTED_GAP_RUNS
    )
    state = (
        "PASS_GAPPED"
        if boundary
        and duplicates == 0
        and non_monotonic == 0
        and exact
        else "BLOCK"
    )
    return {
        "clock": "M1",
        "side": side,
        "row_count": len(timestamps),
        "expected_row_count_without_gaps": len(expected),
        "duplicates": duplicates,
        "non_monotonic": non_monotonic,
        "boundary_complete": boundary,
        "expected_first_timestamp_utc": utc(START),
        "observed_first_timestamp_utc": (
            utc(timestamps[0]) if timestamps else None
        ),
        "expected_last_timestamp_utc": utc(
            END - timedelta(minutes=1)
        ),
        "observed_last_timestamp_utc": (
            utc(timestamps[-1]) if timestamps else None
        ),
        "missing_timestamp_count": len(missing),
        "missing_timestamps_utc": [utc(value) for value in missing],
        "gap_run_count": len(runs),
        "gap_runs": runs,
        "coverage_state": COVERAGE_STATE,
        "repair_performed": False,
        "qa_state": state,
    }


def parent_coverage(
    observed: set[datetime],
    clock: str,
    minutes: int,
) -> dict[str, object]:
    unavailable: list[dict[str, object]] = []
    available: list[str] = []
    cursor = START
    while cursor < END:
        parent_end = min(
            cursor + timedelta(minutes=minutes),
            END,
        )
        members: list[datetime] = []
        member = cursor
        while member < parent_end:
            members.append(member)
            member += timedelta(minutes=1)
        missing = [
            value for value in members if value not in observed
        ]
        if missing:
            unavailable.append(
                {
                    "parent_start_utc": utc(cursor),
                    "parent_end_utc": utc(parent_end),
                    "status": "UNAVAILABLE_INCOMPLETE_M1_PARENT",
                    "missing_m1_timestamps_utc": [
                        utc(value) for value in missing
                    ],
                }
            )
        else:
            available.append(utc(cursor))
        cursor = parent_end
    return {
        "clock": clock,
        "required_m1_members": minutes,
        "available_parent_count": len(available),
        "available_parent_starts_utc": available,
        "unavailable_parent_count": len(unavailable),
        "unavailable_parents": unavailable,
        "incomplete_parent_policy": "EXCLUDE_NO_SYNTHESIS",
        "repair_performed": False,
    }


def assert_parent_available(
    coverage_result: Mapping[str, object],
    parent_start_utc: str,
) -> None:
    unavailable = coverage_result.get("unavailable_parents")
    if not isinstance(unavailable, list):
        raise RecoveryError(
            "downstream coverage receipt is malformed"
        )
    for item in unavailable:
        if (
            isinstance(item, dict)
            and item.get("parent_start_utc") == parent_start_utc
        ):
            raise RecoveryError(
                "incomplete M1 parent is unavailable and must be "
                f"excluded: {coverage_result.get('clock')} "
                f"{parent_start_utc}"
            )


def evaluate(
    rows: Mapping[
        tuple[str, str],
        Sequence[base.CandleRow],
    ],
) -> tuple[
    dict[str, object],
    dict[str, object],
    dict[str, object],
    dict[str, object],
    bool,
]:
    m1 = [
        m1_result(rows[("M1", side)], side)
        for side in ("BID", "ASK")
    ]
    h1_gap = [
        base._gap_audit(
            rows[("H1", side)],
            clock="H1",
            side=side,
        )
        for side in ("BID", "ASK")
    ]
    pairs = [
        base._bid_ask_audit(
            rows[(clock, "BID")],
            rows[(clock, "ASK")],
            clock=clock,
        )
        for clock in ("M1", "H1")
    ]
    reconciliation = [
        base._h1_reconciliation(
            rows[("M1", side)],
            rows[("H1", side)],
            side=side,
        )
        for side in ("BID", "ASK")
    ]
    bid = {
        row.timestamp_utc for row in rows[("M1", "BID")]
    }
    ask = {
        row.timestamp_utc for row in rows[("M1", "ASK")]
    }
    shared = bid == ask
    coverage_results = [
        parent_coverage(bid, "15M", 15),
        parent_coverage(bid, "H1_M1_DERIVED", 60),
        parent_coverage(bid, "2H", 120),
    ]
    coverage: dict[str, object] = {
        "schema": "ovc-rps-g1b-downstream-coverage/v1",
        "slice_id": SLICE_ID,
        "source_coverage_state": COVERAGE_STATE,
        "shared_m1_timestamp_set": shared,
        "results": coverage_results,
        "repair_performed": False,
        "forward_fill_performed": False,
        "interpolation_performed": False,
        "synthesis_performed": False,
        "incomplete_parent_consumption": "DENIED",
    }
    exact_h1 = all(
        item["row_count"] == EXPECTED_H1_ROWS
        and item["qa_state"] == "PASS"
        for item in h1_gap
    )
    exact_recon = all(
        item["complete_m1_derived_h1_count"]
        == EXPECTED_COMPLETE_H1
        and item["compared_count"] == EXPECTED_COMPLETE_H1
        and not item["missing_native_timestamps"]
        and not item["ohlc_mismatches"]
        and item["qa_state"] == "PASS"
        for item in reconciliation
    )
    exclusion_materialised = all(
        int(item["unavailable_parent_count"]) > 0
        and item["incomplete_parent_policy"]
        == "EXCLUDE_NO_SYNTHESIS"
        for item in coverage_results
    )
    accepted = (
        all(
            item["qa_state"] == "PASS_GAPPED"
            for item in m1
        )
        and exact_h1
        and shared
        and all(
            item["qa_state"] == "PASS"
            for item in pairs
        )
        and exact_recon
        and exclusion_materialised
    )
    gap_receipt = {
        "schema": "ovc-rps-g1b-gap-duplicate-qa/v1",
        "slice_id": SLICE_ID,
        "coverage_state": COVERAGE_STATE,
        "m1_results": m1,
        "native_h1_results": h1_gap,
        "shared_m1_timestamp_set": shared,
        "repair_performed": False,
        "qa_state": "PASS_GAPPED" if accepted else "BLOCK",
    }
    pair_pass = all(
        item["qa_state"] == "PASS" for item in pairs
    )
    pair_receipt = {
        "schema": "ovc-rps-g1b-bid-ask-reconciliation/v1",
        "slice_id": SLICE_ID,
        "results": pairs,
        "qa_state": "PASS" if pair_pass else "BLOCK",
    }
    h1_receipt = {
        "schema": "ovc-rps-g1b-native-h1-reconciliation/v1",
        "slice_id": SLICE_ID,
        "results": reconciliation,
        "qa_state": "PASS" if exact_recon else "BLOCK",
        "repair_authority": "NONE",
    }
    coverage["qa_state"] = (
        "PASS_GAPPED_EXCLUSION"
        if exclusion_materialised
        else "BLOCK"
    )
    return (
        gap_receipt,
        pair_receipt,
        h1_receipt,
        coverage,
        accepted,
    )
