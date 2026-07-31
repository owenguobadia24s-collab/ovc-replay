from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Mapping, Sequence

from ovc.research_operations.pattern_discovery.full_month_mdr import (
    EXPECTED_SOURCE_END,
    EXPECTED_SOURCE_START,
    PLAN_AMENDMENT_ID,
    SOURCE_SLICE_ID,
    TARGET_END,
    TARGET_START,
    build_source_profile,
    iter_m1_partition_days,
    iter_native_h1_transport_months,
)

from . import dukascopy_intake as base


APPROVED_GATE = "PD-JUNE-FM-G1"
APPROVED_SLICE_ID = SOURCE_SLICE_ID
APPROVED_START = EXPECTED_SOURCE_START
APPROVED_END = EXPECTED_SOURCE_END
COMPRESSED_BYTE_LIMIT = 512 * 1024 * 1024
EXPANDED_BYTE_LIMIT = 2 * 1024 * 1024 * 1024
ADAPTER_VERSION = "1.4.0-pd-june-full-month-mdr-a1"
DATE_TOKEN = "20260530_20260703"
NATIVE_JULY_H1_STATUS = "WAIVED_BY_OPERATOR_A1_PROVIDER_OBJECT_UNAVAILABLE"
POST_TARGET_H1_AUTHORITY = "M1_DERIVED_FROM_COMPLETE_JULY_CONTEXT_BARS"

IntakeError = base.IntakeError
FetchResult = base.FetchResult
Fetcher = base.Fetcher
CandleRow = base.CandleRow


def _utc(value: datetime) -> str:
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _month_end(start: datetime) -> datetime:
    if start.month == 12:
        return start.replace(year=start.year + 1, month=1)
    return start.replace(month=start.month + 1)


def _enforce_limits(*, compressed_bytes: int, expanded_bytes: int) -> None:
    if compressed_bytes > COMPRESSED_BYTE_LIMIT:
        raise IntakeError(
            f"compressed-byte limit exceeded: {compressed_bytes} > {COMPRESSED_BYTE_LIMIT}"
        )
    if expanded_bytes > EXPANDED_BYTE_LIMIT:
        raise IntakeError(
            f"expanded-byte limit exceeded: {expanded_bytes} > {EXPANDED_BYTE_LIMIT}"
        )


def provider_request_plan() -> dict[str, object]:
    profile = build_source_profile()
    m1_days = iter_m1_partition_days(APPROVED_START, APPROVED_END)
    native_h1_months = iter_native_h1_transport_months(APPROVED_START, APPROVED_END)
    objects: list[dict[str, object]] = []
    for side in ("BID", "ASK"):
        for day in m1_days:
            objects.append(
                {
                    "logical_stream": f"M1_{side}",
                    "partition_start_utc": _utc(day),
                    "relative_provider_path": base._m1_relative(day, side),
                    "allow_missing_transport": True,
                }
            )
        for month in native_h1_months:
            objects.append(
                {
                    "logical_stream": f"H1_{side}",
                    "partition_start_utc": _utc(month),
                    "relative_provider_path": base._h1_relative(month, side),
                    "allow_missing_transport": False,
                    "native_coverage_end_exclusive_utc": _utc(TARGET_END),
                }
            )
    return {
        "schema": "ovc-pd-june-full-month-mdr-provider-plan/v1",
        "gate": APPROVED_GATE,
        "slice_id": APPROVED_SLICE_ID,
        "plan_amendment": PLAN_AMENDMENT_ID,
        "target_start_utc": profile["target_start_utc"],
        "target_end_exclusive_utc": profile["target_end_exclusive_utc"],
        "source_start_utc": profile["source_start_utc"],
        "source_end_exclusive_utc": profile["source_end_exclusive_utc"],
        "provider_object_count": len(objects),
        "objects": objects,
        "native_h1_transport_months_utc": ["2026-05", "2026-06"],
        "native_july_h1_transport": NATIVE_JULY_H1_STATUS,
        "post_target_h1_context": POST_TARGET_H1_AUTHORITY,
        "compressed_byte_limit": COMPRESSED_BYTE_LIMIT,
        "expanded_byte_limit": EXPANDED_BYTE_LIMIT,
        "provider_execution_location": "OPERATOR_LOCAL_ONLY",
        "provider_execution_in_ci": "DENIED",
    }


def _coverage_audit(
    rows: Sequence[CandleRow],
    *,
    clock: str,
    side: str,
) -> dict[str, object]:
    step = timedelta(minutes=1 if clock == "M1" else 60)
    duplicates = 0
    non_monotonic = 0
    weekend_discontinuities: list[dict[str, object]] = []
    unexpected_gaps: list[dict[str, object]] = []
    for left, right in zip(rows, rows[1:]):
        delta = right.timestamp_utc - left.timestamp_utc
        if delta == timedelta(0):
            duplicates += 1
            continue
        if delta < timedelta(0):
            non_monotonic += 1
            continue
        if delta > step:
            item = {
                "after_utc": _utc(left.timestamp_utc),
                "before_utc": _utc(right.timestamp_utc),
                "duration_seconds": int(delta.total_seconds()),
            }
            if base._crosses_weekend(left.timestamp_utc, right.timestamp_utc):
                weekend_discontinuities.append(item)
            else:
                unexpected_gaps.append(item)

    observed_first = rows[0].timestamp_utc if rows else None
    observed_last = rows[-1].timestamp_utc if rows else None
    expected_last = APPROVED_END - step
    start_boundary_accepted = bool(
        observed_first
        and (
            observed_first == APPROVED_START
            or (
                observed_first > APPROVED_START
                and base._crosses_weekend(APPROVED_START, observed_first)
            )
        )
    )
    end_boundary_accepted = bool(
        observed_last
        and (
            observed_last == expected_last
            or (
                observed_last < expected_last
                and base._crosses_weekend(observed_last, expected_last)
            )
        )
    )
    state = (
        "PASS"
        if rows
        and duplicates == 0
        and non_monotonic == 0
        and not unexpected_gaps
        and start_boundary_accepted
        and end_boundary_accepted
        else "BLOCK"
    )
    return {
        "clock": clock,
        "side": side,
        "row_count": len(rows),
        "duplicates": duplicates,
        "non_monotonic": non_monotonic,
        "expected_source_start_utc": _utc(APPROVED_START),
        "observed_first_timestamp_utc": _utc(observed_first) if observed_first else None,
        "start_boundary_accepted": start_boundary_accepted,
        "expected_source_last_timestamp_utc": _utc(expected_last),
        "observed_last_timestamp_utc": _utc(observed_last) if observed_last else None,
        "end_boundary_accepted": end_boundary_accepted,
        "weekend_spanning_discontinuities": weekend_discontinuities,
        "unexpected_intra_session_gaps": unexpected_gaps,
        "qa_state": state,
    }


def _post_target_h1_audit(
    m1_rows: Sequence[CandleRow],
    *,
    side: str,
) -> tuple[list[CandleRow], dict[str, object]]:
    derived = base._aggregate_complete_h1(
        [
            row
            for row in m1_rows
            if TARGET_END <= row.timestamp_utc < APPROVED_END
        ]
    )
    expected: set[datetime] = set()
    cursor = TARGET_END
    while cursor < APPROVED_END:
        expected.add(cursor)
        cursor += timedelta(hours=1)
    observed = set(derived)
    missing = sorted(expected - observed)
    unexpected = sorted(observed - expected)
    state = "PASS" if not missing and not unexpected else "BLOCK"
    audit = {
        "side": side,
        "authority": POST_TARGET_H1_AUTHORITY,
        "native_july_h1_transport": NATIVE_JULY_H1_STATUS,
        "expected_complete_hour_count": len(expected),
        "derived_complete_hour_count": len(observed),
        "missing_hours_utc": [_utc(value) for value in missing],
        "unexpected_hours_utc": [_utc(value) for value in unexpected],
        "qa_state": state,
    }
    return [derived[key] for key in sorted(derived)], audit


def _write_csv(
    root: Path,
    *,
    clock: str,
    side: str,
    rows: Sequence[CandleRow],
) -> tuple[Path, bytes]:
    path = root / "source-objects" / f"GBPUSD_{clock}_{side}_{DATE_TOKEN}_UTC.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise IntakeError(f"refusing to overwrite source object: {path}")
    lines = [",".join(base.ORDERED_COLUMNS)]
    lines.extend(",".join(row.csv_row()) for row in rows)
    payload = ("\n".join(lines) + "\n").encode("utf-8")
    path.write_bytes(payload)
    return path, payload


def _source_object_id(clock: str, side: str) -> str:
    return f"SRC.DUKASCOPY.GBPUSD.{clock}.{side}.{DATE_TOKEN}.v1"


def _logical_manifest(source_objects: Sequence[dict[str, object]]) -> dict[str, object]:
    manifest: dict[str, object] = {
        "schema": "ovc-pd-june-full-month-mdr-source-manifest/v1",
        "slice_id": APPROVED_SLICE_ID,
        "plan_amendment": PLAN_AMENDMENT_ID,
        "instrument": "GBPUSD",
        "provider": "DUKASCOPY",
        "target_start_utc": _utc(TARGET_START),
        "target_end_exclusive_utc": _utc(TARGET_END),
        "source_window_start_utc": _utc(APPROVED_START),
        "source_window_end_exclusive_utc": _utc(APPROVED_END),
        "target_eligibility": "TARGET_JUNE_ONLY",
        "context_eligibility": "MAY_AND_JULY_CONTEXT_ONLY",
        "native_july_h1_transport": NATIVE_JULY_H1_STATUS,
        "post_target_h1_context": POST_TARGET_H1_AUTHORITY,
        "source_objects": [
            {
                "object_id": item["object_id"],
                "clock": item["clock"],
                "side": item["side"],
                "sha256": item["sha256"],
                "row_count": item["row_count"],
                "construction": item["construction"],
            }
            for item in sorted(
                source_objects,
                key=lambda value: (str(value["clock"]), str(value["side"])),
            )
        ],
        "coverage_state": "ACCEPTED_WITH_EXPLICIT_MARKET_CLOSURES_ONLY",
        "frozen": True,
        "release_status": "NOT_A_RELEASE",
        "selector_eligibility": "NONE",
        "r2_publication": "DENIED",
        "validation_consumption": "DENIED",
    }
    manifest["manifest_sha256"] = base._canonical_sha256(manifest)
    return manifest


def _quarantine(staging: Path, *, reason: str) -> Path | None:
    if not staging.exists():
        return None
    quarantine_root = staging.parent / "quarantine"
    quarantine_root.mkdir(parents=True, exist_ok=True)
    target = quarantine_root / (
        f"{APPROVED_SLICE_ID}."
        f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}."
        f"{uuid.uuid4().hex[:8]}"
    )
    try:
        base._write_json(
            staging / "incident.json",
            {
                "schema": "ovc-pd-june-full-month-mdr-intake-incident/v1",
                "slice_id": APPROVED_SLICE_ID,
                "plan_amendment": PLAN_AMENDMENT_ID,
                "reason": reason,
                "accepted_source_slice_created": False,
                "authority": "NONE",
            },
        )
    except Exception:
        pass
    staging.rename(target)
    return target


def preflight(
    *,
    repository_root: Path,
    environ: Mapping[str, str] | None = None,
) -> dict[str, object]:
    values = os.environ if environ is None else environ
    root = base._resolve_root(repository_root, values)
    final_root = root / "prospective-source" / "intake" / APPROVED_SLICE_ID
    if final_root.exists() and any(final_root.iterdir()):
        raise IntakeError(
            f"approved slice destination already contains material: {final_root}"
        )
    plan = provider_request_plan()
    return {
        "status": "READY_FOR_OPERATOR_LOCAL_EXECUTION",
        "gate": APPROVED_GATE,
        "slice_id": APPROVED_SLICE_ID,
        "plan_amendment": PLAN_AMENDMENT_ID,
        "source_window_start_utc": _utc(APPROVED_START),
        "source_window_end_exclusive_utc": _utc(APPROVED_END),
        "target_start_utc": _utc(TARGET_START),
        "target_end_exclusive_utc": _utc(TARGET_END),
        "provider_object_count": plan["provider_object_count"],
        "streams": ["M1_BID", "M1_ASK", "H1_BID", "H1_ASK"],
        "native_july_h1_transport": NATIVE_JULY_H1_STATUS,
        "post_target_h1_context": POST_TARGET_H1_AUTHORITY,
        "compressed_byte_limit": COMPRESSED_BYTE_LIMIT,
        "expanded_byte_limit": EXPANDED_BYTE_LIMIT,
        "provider_network_access_performed": False,
        "provider_execution_location": "OPERATOR_LOCAL_ONLY",
        "final_destination_exists_empty": final_root.exists(),
    }


def execute_intake(
    *,
    repository_root: Path,
    gate: str,
    environ: Mapping[str, str] | None = None,
    fetcher: Fetcher = base._request,
) -> dict[str, object]:
    values = os.environ if environ is None else environ
    if gate != APPROVED_GATE:
        raise IntakeError(
            f"exact operator approval binding required: --gate {APPROVED_GATE}"
        )
    base._assert_operator_local(values)
    root = base._resolve_root(repository_root, values)
    intake_parent = root / "prospective-source" / "intake"
    intake_parent.mkdir(parents=True, exist_ok=True)
    final_root = intake_parent / APPROVED_SLICE_ID
    if final_root.exists():
        if any(final_root.iterdir()):
            raise IntakeError(
                f"refusing to overwrite existing intake destination: {final_root}"
            )
        final_root.rmdir()
    staging = intake_parent / f".{APPROVED_SLICE_ID}.staging.{uuid.uuid4().hex}"
    staging.mkdir(parents=False, exist_ok=False)

    compressed_bytes = 0
    expanded_bytes = 0
    transport_receipts: list[dict[str, object]] = []
    rows_by_stream: dict[tuple[str, str], list[CandleRow]] = {}
    native_h1_by_side: dict[str, list[CandleRow]] = {}
    post_target_h1_audits: list[dict[str, object]] = []
    try:
        for side in ("BID", "ASK"):
            combined_m1: list[CandleRow] = []
            for day in iter_m1_partition_days(APPROVED_START, APPROVED_END):
                relative = base._m1_relative(day, side)
                result = fetcher(relative, True)
                cached = None
                if result.status == "DOWNLOADED":
                    compressed_bytes += result.size_bytes
                    _enforce_limits(
                        compressed_bytes=compressed_bytes,
                        expanded_bytes=expanded_bytes,
                    )
                    cached = base._store_transport(staging, result)
                    data = base._decompress(result.body, identity=relative)
                    expanded_bytes += len(data)
                    _enforce_limits(
                        compressed_bytes=compressed_bytes,
                        expanded_bytes=expanded_bytes,
                    )
                    combined_m1.extend(
                        base._decode_candles(
                            data,
                            base=day,
                            partition_end=day + timedelta(days=1),
                            identity=relative,
                            accepted_start=APPROVED_START,
                            accepted_end=APPROVED_END,
                        )
                    )
                transport_receipts.append(
                    {
                        "logical_stream": f"M1_{side}",
                        "relative_provider_path": relative,
                        "status": result.status,
                        "url": result.url,
                        "sha256": result.sha256,
                        "size_bytes": result.size_bytes,
                        "etag": result.etag,
                        "last_modified": result.last_modified,
                        "cached_relative_path": cached,
                    }
                )
            combined_m1 = sorted(combined_m1, key=lambda row: row.timestamp_utc)
            rows_by_stream[("M1", side)] = combined_m1

            native_h1: list[CandleRow] = []
            for month in iter_native_h1_transport_months(APPROVED_START, APPROVED_END):
                relative = base._h1_relative(month, side)
                result = fetcher(relative, False)
                if result.status != "DOWNLOADED":
                    raise IntakeError(
                        f"required native H1 provider object unavailable: {relative}"
                    )
                compressed_bytes += result.size_bytes
                _enforce_limits(
                    compressed_bytes=compressed_bytes,
                    expanded_bytes=expanded_bytes,
                )
                cached = base._store_transport(staging, result)
                data = base._decompress(result.body, identity=relative)
                expanded_bytes += len(data)
                _enforce_limits(
                    compressed_bytes=compressed_bytes,
                    expanded_bytes=expanded_bytes,
                )
                native_h1.extend(
                    base._decode_candles(
                        data,
                        base=month,
                        partition_end=_month_end(month),
                        identity=relative,
                        accepted_start=APPROVED_START,
                        accepted_end=TARGET_END,
                    )
                )
                transport_receipts.append(
                    {
                        "logical_stream": f"H1_{side}",
                        "relative_provider_path": relative,
                        "status": result.status,
                        "url": result.url,
                        "sha256": result.sha256,
                        "size_bytes": result.size_bytes,
                        "etag": result.etag,
                        "last_modified": result.last_modified,
                        "cached_relative_path": cached,
                        "accepted_interval_is_bounded_subset_of_monthly_transport": True,
                        "native_coverage_end_exclusive_utc": _utc(TARGET_END),
                    }
                )
            native_h1 = sorted(native_h1, key=lambda row: row.timestamp_utc)
            native_h1_by_side[side] = native_h1
            post_target_h1, post_target_audit = _post_target_h1_audit(
                combined_m1,
                side=side,
            )
            post_target_h1_audits.append(post_target_audit)
            rows_by_stream[("H1", side)] = sorted(
                [*native_h1, *post_target_h1],
                key=lambda row: row.timestamp_utc,
            )

        if any(not rows for rows in rows_by_stream.values()):
            missing = [
                f"{clock}_{side}"
                for (clock, side), rows in rows_by_stream.items()
                if not rows
            ]
            raise IntakeError(
                "one or more logical streams contain no accepted rows: "
                + ", ".join(missing)
            )

        coverage_results = [
            _coverage_audit(rows, clock=clock, side=side)
            for (clock, side), rows in sorted(rows_by_stream.items())
        ]
        pair_results = [
            base._bid_ask_audit(
                rows_by_stream[(clock, "BID")],
                rows_by_stream[(clock, "ASK")],
                clock=clock,
            )
            for clock in ("M1", "H1")
        ]
        h1_results: list[dict[str, object]] = []
        for side in ("BID", "ASK"):
            reconciliation = base._h1_reconciliation(
                [
                    row
                    for row in rows_by_stream[("M1", side)]
                    if row.timestamp_utc < TARGET_END
                ],
                native_h1_by_side[side],
                side=side,
            )
            post_target = next(
                item for item in post_target_h1_audits if item["side"] == side
            )
            reconciliation.update(
                {
                    "native_coverage_end_exclusive_utc": _utc(TARGET_END),
                    "native_july_h1_transport": NATIVE_JULY_H1_STATUS,
                    "post_target_h1_context": POST_TARGET_H1_AUTHORITY,
                    "post_target_derived_h1_count": post_target[
                        "derived_complete_hour_count"
                    ],
                    "post_target_missing_hours_utc": post_target["missing_hours_utc"],
                }
            )
            if post_target["qa_state"] != "PASS":
                reconciliation["qa_state"] = "BLOCK"
            h1_results.append(reconciliation)
        if any(
            item["qa_state"] != "PASS"
            for item in coverage_results + pair_results + h1_results + post_target_h1_audits
        ):
            raise IntakeError("source QA did not pass; workspace must be quarantined")

        source_objects: list[dict[str, object]] = []
        for (clock, side), rows in sorted(rows_by_stream.items()):
            path, payload = _write_csv(
                staging,
                clock=clock,
                side=side,
                rows=rows,
            )
            expanded_bytes += len(payload)
            _enforce_limits(
                compressed_bytes=compressed_bytes,
                expanded_bytes=expanded_bytes,
            )
            construction = (
                "NATIVE_M1_PROVIDER_TRANSPORTS"
                if clock == "M1"
                else "NATIVE_MAY_JUNE_PLUS_M1_DERIVED_JULY_CONTEXT"
            )
            source_objects.append(
                {
                    "object_id": _source_object_id(clock, side),
                    "clock": clock,
                    "side": side,
                    "construction": construction,
                    "sha256": hashlib.sha256(payload).hexdigest(),
                    "size_bytes": len(payload),
                    "row_count": len(rows),
                    "first_timestamp_utc": _utc(rows[0].timestamp_utc),
                    "last_timestamp_utc": _utc(rows[-1].timestamp_utc),
                    "schema_fingerprint": base._schema_fingerprint(),
                    "relative_path": path.relative_to(staging).as_posix(),
                }
            )

        base._write_json(
            staging / "receipts" / "provider-request-plan.json",
            provider_request_plan(),
        )
        base._write_json(
            staging / "receipts" / "provider-request-receipt.json",
            {
                "schema": "ovc-pd-june-full-month-mdr-provider-request-receipt/v1",
                "gate": APPROVED_GATE,
                "slice_id": APPROVED_SLICE_ID,
                "plan_amendment": PLAN_AMENDMENT_ID,
                "adapter": base.ADAPTER,
                "adapter_version": ADAPTER_VERSION,
                "transport_objects": transport_receipts,
                "native_july_h1_transport": NATIVE_JULY_H1_STATUS,
                "post_target_h1_context": POST_TARGET_H1_AUTHORITY,
                "compressed_bytes": compressed_bytes,
                "compressed_byte_limit": COMPRESSED_BYTE_LIMIT,
                "expanded_bytes_before_receipts": expanded_bytes,
                "expanded_byte_limit": EXPANDED_BYTE_LIMIT,
                "provider_network_location": "OPERATOR_LOCAL_ONLY",
                "ci_network_access": "DENIED",
            },
        )
        base._write_json(
            staging / "receipts" / "source-object-inventory.json",
            {
                "schema": "ovc-pd-june-full-month-mdr-source-object-inventory/v1",
                "slice_id": APPROVED_SLICE_ID,
                "plan_amendment": PLAN_AMENDMENT_ID,
                "source_object_count": len(source_objects),
                "source_objects": source_objects,
            },
        )
        base._write_json(
            staging / "receipts" / "coverage-gap-duplicate-qa.json",
            {
                "schema": "ovc-pd-june-full-month-mdr-coverage-qa/v1",
                "slice_id": APPROVED_SLICE_ID,
                "plan_amendment": PLAN_AMENDMENT_ID,
                "results": coverage_results,
                "post_target_h1_derivation": post_target_h1_audits,
                "qa_state": "PASS",
                "repair_performed": False,
            },
        )
        base._write_json(
            staging / "receipts" / "bid-ask-reconciliation.json",
            {
                "schema": "ovc-pd-june-full-month-mdr-bid-ask-reconciliation/v1",
                "slice_id": APPROVED_SLICE_ID,
                "results": pair_results,
                "qa_state": "PASS",
            },
        )
        base._write_json(
            staging / "receipts" / "native-h1-reconciliation.json",
            {
                "schema": "ovc-pd-june-full-month-mdr-native-h1-reconciliation/v1",
                "slice_id": APPROVED_SLICE_ID,
                "plan_amendment": PLAN_AMENDMENT_ID,
                "results": h1_results,
                "qa_state": "PASS",
                "repair_authority": "NONE",
                "native_july_h1_transport": NATIVE_JULY_H1_STATUS,
                "post_target_h1_context": POST_TARGET_H1_AUTHORITY,
            },
        )
        manifest = _logical_manifest(source_objects)
        manifest_path = staging / "source-slice-manifest.json"
        base._write_json(manifest_path, manifest)
        manifest_file_sha = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
        expanded_before_freeze = base._workspace_size(staging)
        _enforce_limits(
            compressed_bytes=compressed_bytes,
            expanded_bytes=expanded_before_freeze,
        )
        base._write_json(
            staging / "receipts" / "freeze-receipt.json",
            {
                "schema": "ovc-pd-june-full-month-mdr-freeze-receipt/v1",
                "slice_id": APPROVED_SLICE_ID,
                "plan_amendment": PLAN_AMENDMENT_ID,
                "manifest_sha256": manifest["manifest_sha256"],
                "manifest_file_sha256": manifest_file_sha,
                "source_object_count": 4,
                "compressed_bytes": compressed_bytes,
                "expanded_bytes_excluding_freeze_receipt": expanded_before_freeze,
                "frozen": True,
                "release_status": "NOT_A_RELEASE",
                "selector_eligibility": "NONE",
                "r2_publication": "DENIED",
                "validation_consumption": "DENIED",
                "canonical_discovery_append": "DENIED",
                "native_july_h1_transport": NATIVE_JULY_H1_STATUS,
                "post_target_h1_context": POST_TARGET_H1_AUTHORITY,
            },
        )
        expanded_final = base._workspace_size(staging)
        _enforce_limits(
            compressed_bytes=compressed_bytes,
            expanded_bytes=expanded_final,
        )
        staging.rename(final_root)
        return {
            "status": "FROZEN_LOCAL_SOURCE_SLICE",
            "gate": APPROVED_GATE,
            "slice_id": APPROVED_SLICE_ID,
            "plan_amendment": PLAN_AMENDMENT_ID,
            "manifest_sha256": manifest["manifest_sha256"],
            "manifest_file_sha256": manifest_file_sha,
            "source_object_count": 4,
            "compressed_bytes": compressed_bytes,
            "expanded_bytes": expanded_final,
            "final_root": str(final_root),
            "release_status": "NOT_A_RELEASE",
            "selector_eligibility": "NONE",
            "r2_publication": "DENIED",
            "validation_consumption": "DENIED",
            "native_july_h1_transport": NATIVE_JULY_H1_STATUS,
            "post_target_h1_context": POST_TARGET_H1_AUTHORITY,
        }
    except Exception as exc:
        quarantined = _quarantine(staging, reason=str(exc))
        suffix = f"; quarantined at {quarantined}" if quarantined else ""
        if isinstance(exc, IntakeError):
            raise IntakeError(str(exc) + suffix) from exc
        raise IntakeError(f"unexpected intake failure: {exc}{suffix}") from exc


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Operator-local full-month MDR Dukascopy intake; provider execution "
            "is denied in CI and writes only under OVC_EXTERNAL_ARTIFACT_ROOT."
        )
    )
    parser.add_argument("command", choices=("plan", "preflight", "execute"))
    parser.add_argument("--repository-root", type=Path, default=Path.cwd())
    parser.add_argument(
        "--gate",
        default=None,
        help=f"Required for execute; must equal {APPROVED_GATE}.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    arguments = _parser().parse_args(argv)
    try:
        repository_root = arguments.repository_root.resolve(strict=True)
        if arguments.command == "plan":
            result = provider_request_plan()
        elif arguments.command == "preflight":
            result = preflight(repository_root=repository_root)
        else:
            result = execute_intake(
                repository_root=repository_root,
                gate=arguments.gate or "",
            )
    except IntakeError as exc:
        print(f"PD-JUNE-FM-WP1 intake blocked: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
