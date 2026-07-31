from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from ovc.opt_b.c1.builder import build as build_c1
from ovc.opt_b.c1.formulas import FORMULA_REGISTRY_ID
from ovc.opt_b.c1.serialization import to_dict as c1_to_dict
from ovc.opt_b.c2.engine import C2ScopeEngine

from . import prospective_compute as common
from .aggregation import aggregate_m1
from .binding import ACTIVE_C2_RELEASE, build_replay_binding, validate_non_activating
from .models import ProspectiveBar, canonical_hash, parse_utc


PROGRAMME_ID = "PD-JUNE-FULL-MONTH-MDR"
PLAN_ID = "OVC-PD-JUNE-FULL-MONTH-MDR.v0.1"
PLAN_VERSION = "0.1+A1+A2"
PACKET_ID = "PD-JUNE-FM-WP2"
AUTHORITY_GATE = "PD-JUNE-FM-G1"
SLICE_ID = "RPS.DUKASCOPY.GBPUSD.20260530_20260703.v1"
SOURCE_START = "2026-05-30T00:00:00Z"
SOURCE_END = "2026-07-03T00:00:00Z"
TARGET_START = "2026-06-01T00:00:00Z"
TARGET_END = "2026-07-01T00:00:00Z"
SOURCE_MANIFEST_LOGICAL_SHA256 = "1578b555f3d5aa2822b603141261f86a047096030e5faacd4380ef2c6d4f52e3"
SOURCE_MANIFEST_FILE_SHA256 = "8080b8def035cb37940b89054287d0c61756149aa7cb4711fc462a0ebbdc1f87"
OPERATION_MODE = "TIME_GATED_REPLAY"
DERIVED_AUTHORITY = "TIME_GATED_REPLAY_DERIVED"
PRICE_SET_ID = "PD-JUNE-FM.PRICESET.GBPUSD.20260530_20260703.v1"
SOURCE_MANIFEST_ID = f"PD-JUNE-FM.SOURCE-MANIFEST.{SOURCE_MANIFEST_LOGICAL_SHA256[:24]}"
C1_SET_ID = "PD-JUNE-FM.C1SET.GBPUSD.20260530_20260703.v1"
C1_MANIFEST_ID = f"PD-JUNE-FM.C1MANIFEST.{canonical_hash({'source': SOURCE_MANIFEST_LOGICAL_SHA256, 'formula': FORMULA_REGISTRY_ID})[:24]}"
EXPANDED_OUTPUT_LIMIT = 512 * 1024 * 1024
CLOCK_SECONDS = {"15M": 15 * 60, "2H_A_L": 2 * 60 * 60}
EXPECTED_COUNTS = {
    "15M": {"total": 2316, "complete": 2231, "incomplete": 85, "target_total": 2112, "target_complete": 2036, "target_incomplete": 76},
    "2H_A_L": {"total": 294, "complete": 248, "incomplete": 46, "target_total": 268, "target_complete": 227, "target_incomplete": 41},
}
EXPECTED_C1_RECORDS = 4958
EXPECTED_TARGET_C1_RECORDS = 4526
EXPECTED_C2_STATES = 9420
EXPECTED_TARGET_C2_STATES = 8598

ComputeError = common.ComputeError


def source_acceptance_index_path(repository_root: Path) -> Path:
    return (
        repository_root
        / "docs"
        / "releases"
        / "pattern-discovery-v0-3"
        / "pd-june-full-month-mdr"
        / "PD_JUNE_FULL_MONTH_MDR_WP1_SOURCE_ACCEPTANCE_INDEX.json"
    )


def classify_timestamp(value: str | datetime) -> str:
    current = parse_utc(value) if isinstance(value, str) else value.astimezone(timezone.utc)
    source_start = parse_utc(SOURCE_START)
    source_end = parse_utc(SOURCE_END)
    target_start = parse_utc(TARGET_START)
    target_end = parse_utc(TARGET_END)
    if current < source_start or current >= source_end:
        return "OUTSIDE_SOURCE"
    if current < target_start:
        return "CONTEXT_PRE_TARGET"
    if current < target_end:
        return "TARGET_JUNE"
    return "CONTEXT_POST_TARGET"


def load_source_acceptance_index(repository_root: Path) -> dict[str, Any]:
    value = common.load_json(
        source_acceptance_index_path(repository_root),
        "INVALID_FULL_MONTH_SOURCE_ACCEPTANCE_INDEX",
    )
    if value.get("schema") != "ovc-pd-june-full-month-mdr-wp1-source-acceptance-index/v1":
        raise ComputeError("source acceptance schema mismatch")
    if value.get("source_slice_id") != SLICE_ID:
        raise ComputeError("source acceptance slice identity mismatch")
    if value.get("effective_plan_version") != PLAN_VERSION:
        raise ComputeError("source acceptance plan version mismatch")
    manifest = value.get("manifest")
    if not isinstance(manifest, dict):
        raise ComputeError("source acceptance manifest binding unavailable")
    required = {
        "logical_sha256": SOURCE_MANIFEST_LOGICAL_SHA256,
        "file_sha256": SOURCE_MANIFEST_FILE_SHA256,
        "coverage_state": "ACCEPTED_WITH_EXPLICIT_PAIRED_PROVIDER_ABSENCE_AND_CENSORING",
        "frozen": True,
        "release_status": "NOT_A_RELEASE",
        "selector_eligibility": "NONE",
        "r2_publication": "DENIED",
        "validation_consumption": "DENIED",
    }
    for key, expected in required.items():
        if manifest.get(key) != expected:
            raise ComputeError(f"source acceptance manifest mismatch:{key}")
    acceptance = value.get("acceptance")
    if not isinstance(acceptance, dict) or acceptance.get("decision") != "PASS":
        raise ComputeError("source acceptance decision is not PASS")
    if acceptance.get("authority_delta") != "LOCAL_FROZEN_SOURCE_ACCEPTANCE_ONLY":
        raise ComputeError("source acceptance authority mismatch")
    return value


def verify_frozen_source(
    repository_root: Path,
    environ: Mapping[str, str],
) -> tuple[Path, dict[str, Any], dict[str, Any]]:
    index = load_source_acceptance_index(repository_root)
    root = common.external_root(repository_root, environ) / "prospective-source" / "intake" / SLICE_ID
    if not root.is_dir():
        raise ComputeError(f"accepted frozen source slice unavailable: {root}")

    compact = {str(item["name"]): item for item in index.get("compact_files", [])}
    if len(compact) != 8:
        raise ComputeError("compact source evidence inventory mismatch")
    for name, item in compact.items():
        relative = name if name == "source-slice-manifest.json" else f"receipts/{name}"
        path = common.safe_file(root, relative)
        if path.stat().st_size != int(item["size_bytes"]):
            raise ComputeError(f"compact evidence size mismatch:{name}")
        if common.sha_file(path) != item["sha256"]:
            raise ComputeError(f"compact evidence SHA-256 mismatch:{name}")

    manifest_path = common.safe_file(root, "source-slice-manifest.json")
    manifest = common.load_json(manifest_path, "INVALID_FULL_MONTH_SOURCE_MANIFEST")
    logical = dict(manifest)
    claimed = logical.pop("manifest_sha256", None)
    if claimed != common.logical_sha(logical) or claimed != SOURCE_MANIFEST_LOGICAL_SHA256:
        raise ComputeError("source manifest logical SHA-256 mismatch")
    if common.sha_file(manifest_path) != SOURCE_MANIFEST_FILE_SHA256:
        raise ComputeError("source manifest file SHA-256 mismatch")
    manifest_required = {
        "slice_id": SLICE_ID,
        "source_window_start_utc": SOURCE_START,
        "source_window_end_exclusive_utc": SOURCE_END,
        "target_start_utc": TARGET_START,
        "target_end_exclusive_utc": TARGET_END,
        "target_eligibility": "TARGET_JUNE_ONLY",
        "coverage_state": "ACCEPTED_WITH_EXPLICIT_PAIRED_PROVIDER_ABSENCE_AND_CENSORING",
        "frozen": True,
        "release_status": "NOT_A_RELEASE",
        "selector_eligibility": "NONE",
        "r2_publication": "DENIED",
        "validation_consumption": "DENIED",
    }
    for key, expected in manifest_required.items():
        if manifest.get(key) != expected:
            raise ComputeError(f"source manifest authority mismatch:{key}")

    inventory = common.load_json(
        common.safe_file(root, "receipts/source-object-inventory.json"),
        "INVALID_FULL_MONTH_SOURCE_OBJECT_INVENTORY",
    )
    if inventory.get("slice_id") != SLICE_ID or inventory.get("source_object_count") != 4:
        raise ComputeError("source-object inventory identity mismatch")
    expected = {str(item["object_id"]): item for item in index.get("source_objects", [])}
    observed = {str(item["object_id"]): item for item in inventory.get("source_objects", [])}
    if set(observed) != set(expected) or len(expected) != 4:
        raise ComputeError("source-object identity inventory mismatch")
    for object_id, item in expected.items():
        actual = observed[object_id]
        for field in (
            "clock", "side", "relative_path", "row_count", "size_bytes", "sha256",
            "schema_fingerprint", "first_timestamp_utc", "last_timestamp_utc",
        ):
            if actual.get(field) != item.get(field):
                raise ComputeError(f"source-object metadata mismatch:{object_id}:{field}")
        path = common.safe_file(root, str(item["relative_path"]))
        if path.stat().st_size != int(item["size_bytes"]):
            raise ComputeError(f"source-object size mismatch:{object_id}")
        if common.sha_file(path) != item["sha256"]:
            raise ComputeError(f"source-object SHA-256 mismatch:{object_id}")
    return root, index, inventory


def coverage_counts(bars: Sequence[ProspectiveBar]) -> dict[str, int]:
    total = len(bars)
    complete = sum(item.quality_state == "COMPLETE" for item in bars)
    incomplete = sum(item.quality_state == "QUARANTINED_INCOMPLETE_PARENT_SET" for item in bars)
    target = [item for item in bars if classify_timestamp(item.start_utc) == "TARGET_JUNE"]
    target_complete = sum(item.quality_state == "COMPLETE" for item in target)
    target_incomplete = sum(item.quality_state == "QUARANTINED_INCOMPLETE_PARENT_SET" for item in target)
    return {
        "total": total,
        "complete": complete,
        "incomplete": incomplete,
        "target_total": len(target),
        "target_complete": target_complete,
        "target_incomplete": target_incomplete,
    }


def complete_segments(bars: Sequence[ProspectiveBar]) -> list[list[ProspectiveBar]]:
    ordered = sorted(bars, key=lambda item: item.start_utc)
    segments: list[list[ProspectiveBar]] = []
    current: list[ProspectiveBar] = []
    expected_seconds = CLOCK_SECONDS[ordered[0].clock] if ordered else 0
    previous_end: str | None = None
    for bar in ordered:
        contiguous = previous_end is None or parse_utc(bar.start_utc) == parse_utc(previous_end)
        if bar.quality_state != "COMPLETE" or not contiguous:
            if current:
                segments.append(current)
                current = []
            previous_end = bar.end_utc if bar.quality_state == "COMPLETE" else None
            continue
        if int((parse_utc(bar.end_utc) - parse_utc(bar.start_utc)).total_seconds()) != expected_seconds:
            raise ComputeError(f"unexpected bar duration:{bar.clock}:{bar.start_utc}")
        current.append(bar)
        previous_end = bar.end_utc
    if current:
        segments.append(current)
    return segments


def build_bars(
    source_root: Path,
    inventory: Mapping[str, Any],
) -> tuple[dict[tuple[str, str], list[ProspectiveBar]], dict[str, str], dict[str, dict[str, int]]]:
    m1_items = {
        str(item["side"]): item
        for item in inventory["source_objects"]
        if item["clock"] == "M1"
    }
    if set(m1_items) != {"BID", "ASK"}:
        raise ComputeError("exact M1 BID/ASK source objects are required")
    built: dict[tuple[str, str], list[ProspectiveBar]] = {}
    source_object_ids = {side: str(item["object_id"]) for side, item in m1_items.items()}
    audits: dict[str, dict[str, int]] = {}
    for side in ("BID", "ASK"):
        rows = common.parse_m1(source_root, m1_items[side])
        for clock in ("15M", "2H_A_L"):
            bars = aggregate_m1(rows, clock=clock, side=side, admissible_cutoff_utc=SOURCE_END)
            counts = coverage_counts(bars)
            if counts != EXPECTED_COUNTS[clock]:
                raise ComputeError(f"coverage propagation mismatch:{clock}:{side}:{counts}")
            built[(clock, side)] = bars
            audits[f"{clock}_{side}"] = counts
    for clock in ("15M", "2H_A_L"):
        bid = [(item.start_utc, item.end_utc, item.quality_state) for item in built[(clock, "BID")]]
        ask = [(item.start_utc, item.end_utc, item.quality_state) for item in built[(clock, "ASK")]]
        if bid != ask:
            raise ComputeError(f"derived BID/ASK bar membership mismatch:{clock}")
    return built, source_object_ids, audits


def price_payload(bar: ProspectiveBar, source_object_id: str) -> dict[str, Any]:
    if bar.quality_state != "COMPLETE" or None in (bar.open, bar.high, bar.low, bar.close, bar.volume):
        raise ComputeError("incomplete parent cannot enter C1")
    source_bar_id = f"pd-june-fm-price:{canonical_hash(bar.logical_dict())}"
    return {
        "operation_mode": OPERATION_MODE,
        "release_id": PRICE_SET_ID,
        "manifest_id": SOURCE_MANIFEST_ID,
        "research_role": "DISCOVERY",
        "instrument_id": "GBPUSD",
        "clock_id": bar.clock,
        "price_side": bar.side,
        "source_bar_id": source_bar_id,
        "open_time": bar.start_utc,
        "close_time": bar.end_utc,
        "first_valid_time": bar.end_utc,
        "open": bar.open,
        "high": bar.high,
        "low": bar.low,
        "close": bar.close,
        "volume": bar.volume,
        "price_increment": "0.00001",
        "admissibility": "HANDOFF_ELIGIBLE",
        "quality_state": "COMPLETE",
        "synthetic": False,
        "selector_state": "NONE",
        "authority_state": DERIVED_AUTHORITY,
        "validation_consumption_state": "DENIED",
        "release_membership": False,
        "parent_source_object_ids": [source_object_id],
        "parent_m1_bar_ids": list(bar.parent_source_object_ids),
    }


def build_c1_records(
    bars: Sequence[ProspectiveBar],
    source_object_id: str,
) -> tuple[list[dict[str, Any]], int]:
    records: list[dict[str, Any]] = []
    reset_count = 0
    for segment in complete_segments(bars):
        prior_payload: dict[str, Any] | None = None
        if records:
            reset_count += 1
        for bar in segment:
            current = price_payload(bar, source_object_id)
            c1 = c1_to_dict(build_c1(current, prior_payload))
            eligibility = classify_timestamp(bar.start_utc)
            records.append(
                {
                    "c1_record_id": c1["record_id"],
                    "c1_release_id": C1_SET_ID,
                    "c1_manifest_id": C1_MANIFEST_ID,
                    "opt_a_release_id": PRICE_SET_ID,
                    "opt_a_manifest_id": SOURCE_MANIFEST_ID,
                    "opt_a_manifest_sha256": SOURCE_MANIFEST_LOGICAL_SHA256,
                    "role": "DISCOVERY",
                    "authority_state": DERIVED_AUTHORITY,
                    "instrument": "GBPUSD",
                    "clock": bar.clock,
                    "side": bar.side,
                    "open_time": bar.start_utc,
                    "close_time": bar.end_utc,
                    "first_valid_time": bar.end_utc,
                    "source_path": f"full-month-bars/{bar.clock}/{bar.side}/{bar.bar_id}",
                    "source_bar_id": current["source_bar_id"],
                    "measurements": c1["measurements"],
                    "categorical": c1["categorical"],
                    "null_reasons": c1["null_reasons"],
                    "quality_state": "COMPLETE",
                    "prices": {"open": bar.open, "high": bar.high, "low": bar.low, "close": bar.close},
                    "formula_registry_id": FORMULA_REGISTRY_ID,
                    "source_slice_id": SLICE_ID,
                    "source_manifest_sha256": SOURCE_MANIFEST_LOGICAL_SHA256,
                    "parent_m1_bar_ids": list(bar.parent_source_object_ids),
                    "eligibility_class": eligibility,
                    "target_eligible": eligibility == "TARGET_JUNE",
                    "operation_mode": OPERATION_MODE,
                    "release_membership": False,
                    "selector_eligibility": "NONE",
                    "r2_publication": "DENIED",
                    "validation_consumption": "DENIED",
                    "live_prospective_append": "DENIED",
                }
            )
            prior_payload = current
    return records, reset_count


class ParentEventResolver:
    def __init__(self, events: Iterable[tuple[str, tuple[dict[str, Any], ...]]]):
        self.events = list(events)
        times = [item[0] for item in self.events]
        if times != sorted(times) or len(times) != len(set(times)):
            raise ComputeError("NON_MONOTONIC_PARENT_EVENTS")
        self.index = 0
        self.active: tuple[dict[str, Any], ...] = ()
        self.empty_resolutions = 0

    def __call__(self, record: Mapping[str, Any]) -> tuple[dict[str, Any], ...]:
        local_close = str(record["close_time"])
        while self.index < len(self.events) and self.events[self.index][0] <= local_close:
            self.active = self.events[self.index][1]
            self.index += 1
        if not self.active:
            self.empty_resolutions += 1
        return self.active


def process_scope(
    records: Sequence[Mapping[str, Any]],
    *,
    scope: str,
    parent_resolver: ParentEventResolver | None = None,
    collect_levels: bool = False,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[tuple[str, tuple[dict[str, Any], ...]]], int]:
    engine = C2ScopeEngine(scope)
    states: list[dict[str, Any]] = []
    transitions: list[dict[str, Any]] = []
    snapshots: list[tuple[str, tuple[dict[str, Any], ...]]] = []
    resets = 0
    previous_close: str | None = None
    for record in records:
        if previous_close is not None and str(record["open_time"]) != previous_close:
            engine = C2ScopeEngine(scope)
            resets += 1
        parent_levels = parent_resolver(record) if parent_resolver else ()
        result = engine.process(record, parent_levels=parent_levels)
        eligibility = str(record["eligibility_class"])
        state = dict(result.state)
        state.update(
            {
                "role": "DISCOVERY",
                "active_c2_model_release_id": ACTIVE_C2_RELEASE,
                "operation_mode": OPERATION_MODE,
                "source_slice_id": SLICE_ID,
                "eligibility_class": eligibility,
                "target_eligible": eligibility == "TARGET_JUNE",
                "release_membership": False,
                "live_prospective_append": "DENIED",
            }
        )
        states.append(state)
        if result.transition is not None:
            transition = dict(result.transition)
            transition.update(
                {
                    "role": "DISCOVERY",
                    "clock": record["clock"],
                    "side": record["side"],
                    "evaluation_scope_id": scope,
                    "active_c2_model_release_id": ACTIVE_C2_RELEASE,
                    "operation_mode": OPERATION_MODE,
                    "source_slice_id": SLICE_ID,
                    "eligibility_class": eligibility,
                    "target_eligible": eligibility == "TARGET_JUNE",
                    "release_membership": False,
                    "live_prospective_append": "DENIED",
                }
            )
            transitions.append(transition)
        if collect_levels:
            snapshots.append((str(state["first_valid_time"]), result.levels))
        previous_close = str(record["close_time"])
    return states, transitions, snapshots, resets


def parent_events(
    bars: Sequence[ProspectiveBar],
    snapshots: Sequence[tuple[str, tuple[dict[str, Any], ...]]],
) -> list[tuple[str, tuple[dict[str, Any], ...]]]:
    by_time = {timestamp: levels for timestamp, levels in snapshots}
    result: list[tuple[str, tuple[dict[str, Any], ...]]] = []
    for bar in sorted(bars, key=lambda item: item.end_utc):
        levels = by_time.get(bar.end_utc, ()) if bar.quality_state == "COMPLETE" else ()
        result.append((bar.end_utc, levels))
    return result


def build_c2_outputs(
    c1: Mapping[tuple[str, str], Sequence[Mapping[str, Any]]],
    bars: Mapping[tuple[str, str], Sequence[ProspectiveBar]],
) -> tuple[
    dict[tuple[str, str, str], tuple[list[dict[str, Any]], list[dict[str, Any]]]],
    dict[str, int],
]:
    outputs: dict[tuple[str, str, str], tuple[list[dict[str, Any]], list[dict[str, Any]]]] = {}
    metrics: dict[str, int] = {"scope_resets": 0, "empty_parent_resolutions": 0}
    for side in ("BID", "ASK"):
        two_h_scope = "GBPUSD-2H-A-L-LOCAL-v0.1"
        states, transitions, snapshots, resets = process_scope(
            c1[("2H_A_L", side)], scope=two_h_scope, collect_levels=True
        )
        metrics["scope_resets"] += resets
        outputs[("2H_A_L", side, two_h_scope)] = (states, transitions)

        local_scope = "GBPUSD-15M-LOCAL-v0.1"
        states, transitions, _, resets = process_scope(c1[("15M", side)], scope=local_scope)
        metrics["scope_resets"] += resets
        outputs[("15M", side, local_scope)] = (states, transitions)

        resolver = ParentEventResolver(parent_events(bars[("2H_A_L", side)], snapshots))
        combined_scope = "GBPUSD-15M-WITH-2H-PARENT-v0.1"
        states, transitions, _, resets = process_scope(
            c1[("15M", side)], scope=combined_scope, parent_resolver=resolver
        )
        metrics["scope_resets"] += resets
        metrics["empty_parent_resolutions"] += resolver.empty_resolutions
        outputs[("15M", side, combined_scope)] = (states, transitions)
    return outputs, metrics


def count_markers(value: object, markers: set[str]) -> int:
    if isinstance(value, dict):
        return sum(count_markers(item, markers) for item in value.values())
    if isinstance(value, (list, tuple)):
        return sum(count_markers(item, markers) for item in value)
    return int(isinstance(value, str) and value in markers)


def build_payload(
    output_root: Path,
    *,
    source_root: Path,
    inventory: Mapping[str, Any],
) -> dict[str, Any]:
    bars, source_object_ids, bar_audits = build_bars(source_root, inventory)
    data_paths: list[Path] = []
    for (clock, side), items in sorted(bars.items()):
        path = output_root / "bars" / clock / f"{side}.jsonl"
        common.write_jsonl(path, [
            {**item.logical_dict(), "eligibility_class": classify_timestamp(item.start_utc), "target_eligible": classify_timestamp(item.start_utc) == "TARGET_JUNE"}
            for item in items
        ])
        data_paths.append(path)

    c1_records: dict[tuple[str, str], list[dict[str, Any]]] = {}
    c1_resets = 0
    for (clock, side), items in sorted(bars.items()):
        records, resets = build_c1_records(items, source_object_ids[side])
        c1_records[(clock, side)] = records
        c1_resets += resets
        path = output_root / "c1" / clock / f"{side}.jsonl"
        common.write_jsonl(path, records)
        data_paths.append(path)
    c1_count = sum(len(items) for items in c1_records.values())
    target_c1 = sum(
        item["target_eligible"]
        for records in c1_records.values()
        for item in records
    )
    if c1_count != EXPECTED_C1_RECORDS or target_c1 != EXPECTED_TARGET_C1_RECORDS:
        raise ComputeError(f"C1 population mismatch:{c1_count}:{target_c1}")

    c2_outputs, c2_metrics = build_c2_outputs(c1_records, bars)
    state_count = transition_count = target_state_count = target_transition_count = 0
    algorithmic_not_evaluable_markers = 0
    for (clock, side, scope), (states, transitions) in sorted(c2_outputs.items()):
        slug = scope.replace(".", "_")
        state_path = output_root / "c2" / "states" / clock / side / f"{slug}.jsonl"
        transition_path = output_root / "c2" / "transitions" / clock / side / f"{slug}.jsonl"
        state_count += common.write_jsonl(state_path, states)
        transition_count += common.write_jsonl(transition_path, transitions)
        target_state_count += sum(item["target_eligible"] for item in states)
        target_transition_count += sum(item["target_eligible"] for item in transitions)
        algorithmic_not_evaluable_markers += count_markers(states, {"NOT_EVALUATED", "NOT_EVALUABLE"})
        data_paths.extend((state_path, transition_path))
    if state_count != EXPECTED_C2_STATES or target_state_count != EXPECTED_TARGET_C2_STATES:
        raise ComputeError(f"C2 state population mismatch:{state_count}:{target_state_count}")

    coverage = {
        "schema": "ovc-pd-june-full-month-mdr-wp2-coverage/v1",
        "programme_id": PROGRAMME_ID,
        "packet_id": PACKET_ID,
        "slice_id": SLICE_ID,
        "source_window_start_utc": SOURCE_START,
        "source_window_end_exclusive_utc": SOURCE_END,
        "target_start_utc": TARGET_START,
        "target_end_exclusive_utc": TARGET_END,
        "target_filter_application": "AFTER_FULL_SOURCE_INTERVAL_REPLAY",
        "calendar_boundary_context_seconds_each_side": 172800,
        "source_boundary_insufficiency": 0,
        "provider_gap_policy": "EXPLICIT_INCOMPLETE_PARENT_CENSORING_NO_BRIDGING",
        "bar_results": bar_audits,
        "c1_record_count": c1_count,
        "target_c1_record_count": target_c1,
        "c1_gap_reset_count": c1_resets,
        "c2_state_count": state_count,
        "target_c2_state_count": target_state_count,
        "c2_transition_count": transition_count,
        "target_c2_transition_count": target_transition_count,
        "c2_scope_reset_count": c2_metrics["scope_resets"],
        "empty_parent_resolution_count": c2_metrics["empty_parent_resolutions"],
        "algorithmic_not_evaluable_markers": algorithmic_not_evaluable_markers,
        "repair_performed": False,
        "forward_fill_performed": False,
        "interpolation_performed": False,
        "synthesis_performed": False,
        "incomplete_parent_consumption": "DENIED",
        "qa_state": "PASS_EXPLICIT_PAIRED_SPARSE_CENSORING",
    }
    coverage_path = output_root / "qa" / "coverage.json"
    common.write_json(coverage_path, coverage)
    data_paths.append(coverage_path)

    target_audit = {
        "schema": "ovc-pd-june-full-month-mdr-wp2-target-audit/v1",
        "slice_id": SLICE_ID,
        "target_eligibility": "TARGET_JUNE_ONLY",
        "context_eligibility": "MAY_AND_JULY_CONTEXT_ONLY",
        "target_filter_application": "AFTER_C1_C2_REPLAY",
        "target_c1_record_count": target_c1,
        "target_c2_state_count": target_state_count,
        "target_c2_transition_count": target_transition_count,
        "pre_target_records_retained_for_warmup": True,
        "post_target_records_retained_for_completion": True,
        "window_not_complete_due_solely_to_june_calendar_boundary": 0,
        "provider_gap_censoring_separate": True,
        "release_membership": False,
        "selector_eligibility": "NONE",
    }
    target_path = output_root / "qa" / "target-eligibility.json"
    common.write_json(target_path, target_audit)
    data_paths.append(target_path)

    files = common.file_inventory(output_root, data_paths)
    return {
        "files": files,
        "file_count": len(files),
        "coverage": coverage,
        "target_audit": target_audit,
    }


def normalized_inventory(value: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return [
        {"path": str(item["path"]), "size_bytes": int(item["size_bytes"]), "sha256": str(item["sha256"])}
        for item in value
    ]


def quarantine_staging(staging: Path, reason: str) -> Path | None:
    if not staging.exists():
        return None
    root = staging.parent / "quarantine"
    root.mkdir(parents=True, exist_ok=True)
    target = root / f"PD-JUNE-FM-WP2.{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.{uuid.uuid4().hex[:8]}"
    try:
        common.write_json(
            staging / "failure-receipt.json",
            {
                "schema": "ovc-pd-june-full-month-mdr-wp2-failure/v1",
                "programme_id": PROGRAMME_ID,
                "packet_id": PACKET_ID,
                "slice_id": SLICE_ID,
                "reason": reason,
                "provider_network_access_performed": False,
                "release_mutation_performed": False,
                "repair_performed": False,
            },
        )
    except Exception:
        pass
    staging.rename(target)
    return target


def preflight(
    repository_root: Path,
    environ: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    values = os.environ if environ is None else environ
    branch, commit = common.repository_state(repository_root)
    source_root, index, inventory = verify_frozen_source(repository_root, values)
    compute_root = common.external_root(repository_root, values) / "prospective-source" / "compute"
    return {
        "status": "READY_FOR_OPERATOR_LOCAL_FULL_MONTH_C1_C2_REPLAY",
        "programme_id": PROGRAMME_ID,
        "packet_id": PACKET_ID,
        "authority_gate": AUTHORITY_GATE,
        "slice_id": SLICE_ID,
        "repository_branch": branch,
        "code_commit": commit,
        "source_manifest_sha256": SOURCE_MANIFEST_LOGICAL_SHA256,
        "source_object_count": inventory["source_object_count"],
        "m1_rows_per_side": index["qa"]["m1"]["rows_per_side"],
        "target_start_utc": TARGET_START,
        "target_end_exclusive_utc": TARGET_END,
        "source_start_utc": SOURCE_START,
        "source_end_exclusive_utc": SOURCE_END,
        "operation_mode": OPERATION_MODE,
        "provider_network_access_performed": False,
        "output_root_exists": compute_root.exists(),
        "source_root_verified": source_root.is_dir(),
        "deterministic_independent_rerun_required": True,
        "release_status": "NOT_A_RELEASE",
        "selector_eligibility": "NONE",
        "r2_publication": "DENIED",
        "validation_consumption": "DENIED",
        "live_prospective_append": "DENIED",
    }


def execute(
    repository_root: Path,
    *,
    authority_gate: str,
    environ: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    values = os.environ if environ is None else environ
    if authority_gate != AUTHORITY_GATE:
        raise ComputeError(f"exact delegated authority binding required: --gate {AUTHORITY_GATE}")
    if common.truthy(values.get("CI")) or common.truthy(values.get("GITHUB_ACTIONS")):
        raise ComputeError("PD-JUNE-FM-WP2 external replay is prohibited in CI")
    _, code_commit = common.repository_state(repository_root)
    source_root, _, inventory = verify_frozen_source(repository_root, values)
    compute_root = common.external_root(repository_root, values) / "prospective-source" / "compute"
    compute_root.mkdir(parents=True, exist_ok=True)
    staging = compute_root / f".PD-JUNE-FM-WP2.staging.{uuid.uuid4().hex}"
    staging.mkdir(parents=False, exist_ok=False)
    try:
        pass_a = staging / "pass-a"
        pass_b = staging / "pass-b"
        first = build_payload(pass_a, source_root=source_root, inventory=inventory)
        second = build_payload(pass_b, source_root=source_root, inventory=inventory)
        first_inventory = normalized_inventory(first["files"])
        second_inventory = normalized_inventory(second["files"])
        if first_inventory != second_inventory:
            raise ComputeError("deterministic independent rerun mismatch")
        deterministic_hash = common.logical_sha(first_inventory)
        payload = staging / "payload"
        pass_a.rename(payload)
        shutil.rmtree(pass_b)

        manifest_files = [
            {**item, "path": f"payload/{item['path']}"}
            for item in common.file_inventory(payload, [path for path in payload.rglob("*") if path.is_file()])
        ]
        manifest_body = {
            "schema": "ovc-pd-june-full-month-mdr-wp2-output-manifest/v1",
            "programme_id": PROGRAMME_ID,
            "packet_id": PACKET_ID,
            "slice_id": SLICE_ID,
            "source_manifest_sha256": SOURCE_MANIFEST_LOGICAL_SHA256,
            "operation_mode": OPERATION_MODE,
            "target_start_utc": TARGET_START,
            "target_end_exclusive_utc": TARGET_END,
            "source_start_utc": SOURCE_START,
            "source_end_exclusive_utc": SOURCE_END,
            "active_c2_model_release_id": ACTIVE_C2_RELEASE,
            "formula_registry_id": FORMULA_REGISTRY_ID,
            "code_commit": code_commit,
            "deterministic_payload_hash": deterministic_hash,
            "files": manifest_files,
            "file_count": len(manifest_files),
            "release_status": "NOT_A_RELEASE",
            "selector_eligibility": "NONE",
            "r2_publication": "DENIED",
            "validation_consumption": "DENIED",
            "live_prospective_append": "DENIED",
        }
        output_manifest_sha = common.logical_sha(manifest_body)
        output_manifest = {**manifest_body, "output_manifest_sha256": output_manifest_sha}
        output_manifest_path = staging / "output-manifest.json"
        common.write_json(output_manifest_path, output_manifest)

        run_identity = {
            "programme_id": PROGRAMME_ID,
            "packet_id": PACKET_ID,
            "slice_id": SLICE_ID,
            "source_manifest_sha256": SOURCE_MANIFEST_LOGICAL_SHA256,
            "code_commit": code_commit,
            "operation_mode": OPERATION_MODE,
            "output_manifest_sha256": output_manifest_sha,
        }
        run_id = f"PD-JUNE-FM.RUN.{canonical_hash(run_identity)[:24]}"
        run = {
            "schema": "ovc-pd-june-full-month-mdr-wp2-run/v1",
            "run_id": run_id,
            "programme_id": PROGRAMME_ID,
            "packet_id": PACKET_ID,
            "source_slice_id": SLICE_ID,
            "source_manifest_sha256": SOURCE_MANIFEST_LOGICAL_SHA256,
            "code_commit": code_commit,
            "operation_mode": OPERATION_MODE,
            "output_manifest_sha256": output_manifest_sha,
            "deterministic_payload_hash": deterministic_hash,
            "deterministic_independent_rerun": "PASS_BYTE_IDENTICAL",
            "status": "COMPLETE",
        }
        run_path = staging / "replay-run.json"
        common.write_json(run_path, run)

        binding = build_replay_binding(
            source_slice_id=SLICE_ID,
            source_manifest_sha256=SOURCE_MANIFEST_LOGICAL_SHA256,
            compute_run_id=run_id,
            eligible_data_through_utc=SOURCE_END,
            deterministic_replay=True,
            lineage_complete=True,
            gap_state="PAIRED_SPARSE_EXPLICIT_INCOMPLETE_PARENT_CENSORING",
        )
        validate_non_activating(binding)
        binding_path = staging / "prospective-source-binding.json"
        common.write_json(
            binding_path,
            {
                **binding.as_dict(),
                "programme_id": PROGRAMME_ID,
                "packet_id": PACKET_ID,
                "operation_mode": OPERATION_MODE,
                "target_eligibility": "TARGET_JUNE_ONLY",
                "status": "ACCEPTED_FOR_WP3_POPULATION_CONSTRUCTION_CANDIDATE",
                "live_prospective_append": "DENIED",
                "active_research_triage": False,
                "write_authority": False,
            },
        )

        coverage = first["coverage"]
        receipt = {
            "schema": "ovc-pd-june-full-month-mdr-wp2-replay-receipt/v1",
            "run_id": run_id,
            "binding_id": binding.binding_id,
            "programme_id": PROGRAMME_ID,
            "packet_id": PACKET_ID,
            "slice_id": SLICE_ID,
            "source_manifest_sha256": SOURCE_MANIFEST_LOGICAL_SHA256,
            "output_manifest_sha256": output_manifest_sha,
            "output_manifest_file_sha256": common.sha_file(output_manifest_path),
            "replay_run_file_sha256": common.sha_file(run_path),
            "binding_file_sha256": common.sha_file(binding_path),
            "deterministic_payload_hash": deterministic_hash,
            "code_commit": code_commit,
            "operation_mode": OPERATION_MODE,
            "c1_record_count": coverage["c1_record_count"],
            "target_c1_record_count": coverage["target_c1_record_count"],
            "c2_state_count": coverage["c2_state_count"],
            "target_c2_state_count": coverage["target_c2_state_count"],
            "c2_transition_count": coverage["c2_transition_count"],
            "target_c2_transition_count": coverage["target_c2_transition_count"],
            "source_boundary_insufficiency": 0,
            "deterministic_independent_rerun": "PASS_BYTE_IDENTICAL",
            "provider_network_access_performed": False,
            "repair_performed": False,
            "release_status": "NOT_A_RELEASE",
            "selector_eligibility": "NONE",
            "r2_publication": "DENIED",
            "validation_consumption": "DENIED",
            "live_prospective_append": "DENIED",
            "active_research_triage": False,
            "write_authority": False,
            "status": "COMPLETE_LOCAL_WP2_CANDIDATE",
        }
        receipt_path = staging / "replay-receipt.json"
        common.write_json(receipt_path, receipt)

        if common.workspace_size(staging) > EXPANDED_OUTPUT_LIMIT:
            raise ComputeError("PD-JUNE-FM-WP2 expanded output limit exceeded")
        final = compute_root / run_id
        if final.exists():
            raise ComputeError(f"refusing to overwrite existing replay run:{final}")
        staging.rename(final)
        return {
            "status": "COMPLETE_LOCAL_FULL_MONTH_C1_C2_REPLAY_CANDIDATE",
            "run_id": run_id,
            "binding_id": binding.binding_id,
            "slice_id": SLICE_ID,
            "source_manifest_sha256": SOURCE_MANIFEST_LOGICAL_SHA256,
            "output_manifest_sha256": output_manifest_sha,
            "deterministic_payload_hash": deterministic_hash,
            "code_commit": code_commit,
            "operation_mode": OPERATION_MODE,
            "c1_record_count": coverage["c1_record_count"],
            "target_c1_record_count": coverage["target_c1_record_count"],
            "c2_state_count": coverage["c2_state_count"],
            "target_c2_state_count": coverage["target_c2_state_count"],
            "c2_transition_count": coverage["c2_transition_count"],
            "target_c2_transition_count": coverage["target_c2_transition_count"],
            "source_boundary_insufficiency": 0,
            "deterministic_independent_rerun": "PASS_BYTE_IDENTICAL",
            "provider_network_access_performed": False,
            "repair_performed": False,
            "release_status": "NOT_A_RELEASE",
            "selector_eligibility": "NONE",
            "r2_publication": "DENIED",
            "validation_consumption": "DENIED",
            "live_prospective_append": "DENIED",
            "active_research_triage": False,
            "write_authority": False,
            "final_root": str(final),
        }
    except Exception as exc:
        quarantined = quarantine_staging(staging, str(exc))
        suffix = f"; staging quarantined at {quarantined}" if quarantined else ""
        if isinstance(exc, ComputeError):
            raise ComputeError(str(exc) + suffix) from exc
        raise ComputeError(f"unexpected PD-JUNE-FM-WP2 replay failure:{exc}{suffix}") from exc


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(
        description="Operator-local PD-JUNE-FM-WP2 deterministic full-month C1/C2 replay."
    )
    result.add_argument("command", choices=("preflight", "execute"))
    result.add_argument("--repository-root", type=Path, default=Path.cwd())
    result.add_argument("--gate", default=None)
    return result


def main(argv: Sequence[str] | None = None) -> int:
    arguments = parser().parse_args(argv)
    try:
        repository_root = arguments.repository_root.resolve(strict=True)
        if arguments.command == "preflight":
            result = preflight(repository_root)
        else:
            result = execute(repository_root, authority_gate=arguments.gate or "")
    except ComputeError as exc:
        print(f"PD-JUNE-FM-WP2 replay blocked: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
