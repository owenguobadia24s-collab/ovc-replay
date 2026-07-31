from __future__ import annotations

import json
import sqlite3
from collections import Counter
from typing import Any, Mapping

from .g2_common import (AUTHORITY, CONFLICT_PREDICATE_ID, MISSING_STATUSES, _axis_token)
from .index_common import AXES, RO4IndexError, logical_hash

def _matrix_records(source: sqlite3.Connection, partition_id: str) -> list[dict[str, Any]]:
    counters = {axis: Counter() for axis in AXES}
    eligible = Counter()
    missing = Counter()
    excluded = Counter()
    total = int(source.execute("SELECT COUNT(*) FROM transitions").fetchone()[0])
    query = """
      SELECT s1.axes_json, s2.axes_json
      FROM transitions t
      JOIN states s1 ON s1.state_record_id=t.source_state_id
      JOIN states s2 ON s2.state_record_id=t.target_state_id
      ORDER BY t.first_valid_time, t.transition_id
    """
    for source_axes_json, target_axes_json in source.execute(query):
        source_axes = json.loads(source_axes_json)
        target_axes = json.loads(target_axes_json)
        for axis in AXES:
            left_status, left_value = _axis_token(source_axes, axis)
            right_status, right_value = _axis_token(target_axes, axis)
            if left_status in MISSING_STATUSES or right_status in MISSING_STATUSES:
                missing[axis] += 1
                continue
            if left_value is None or right_value is None:
                missing[axis] += 1
                continue
            eligible[axis] += 1
            counters[axis][(left_status, left_value, right_status, right_value)] += 1

    records: list[dict[str, Any]] = []
    for axis in AXES:
        cells: list[dict[str, Any]] = []
        ordered = sorted(counters[axis].items(), key=lambda item: tuple(str(value) for value in item[0]))
        for (from_status, from_value, to_status, to_value), count in ordered:
            cell_identity = (
                f"{partition_id}|{axis}|{from_status}:{from_value}"
                f"->{to_status}:{to_value}"
            )
            cells.append(
                {
                    "count": count,
                    "eligible_denominator": eligible[axis],
                    "excluded_count": excluded[axis],
                    "missing_count": missing[axis],
                    "slice_identity": cell_identity,
                    "display_style": "UNIFORM_NON_DATA_DRIVEN_IDENTITY_ORDERED",
                    "display_text": f"{count} of {eligible[axis]} eligible records",
                }
            )
        if eligible[axis] + missing[axis] + excluded[axis] != total:
            raise RO4IndexError(f"MATRIX_COUNT_CONSERVATION_FAILURE:{partition_id}:{axis}")
        core = {
            "authority": AUTHORITY,
            "matrix_id": f"RO4.MATRIX.{partition_id}.{axis}",
            "slice_identity": partition_id,
            "axis": axis,
            "cells": cells,
            "total_transition_count": total,
            "eligible_denominator": eligible[axis],
            "missing_count": missing[axis],
            "excluded_count": excluded[axis],
            "sort_order": "FROZEN_IDENTITY_ORDER",
        }
        core["logical_hash"] = logical_hash(core)
        records.append(core)
    return records


def _matched_control_map(source: sqlite3.Connection) -> dict[tuple[Any, ...], tuple[str, str]]:
    controls: dict[tuple[Any, ...], tuple[str, str]] = {}
    query = "SELECT state_record_id,first_valid_time,axes_json FROM states ORDER BY first_valid_time,state_record_id"
    for state_id, first_valid_time, axes_json in source.execute(query):
        axes = json.loads(axes_json)
        if axes["QUALITY"].get("status") == "CONFLICT":
            continue
        key = tuple(
            (axis, axes[axis].get("status"), axes[axis].get("value"))
            for axis in AXES
            if axis != "QUALITY"
        )
        controls.setdefault(key, (first_valid_time, state_id))
    return controls


def _conflict_record(
    active: list[tuple[str, str, dict[str, Any]]],
    meta: Mapping[str, Any],
    controls: Mapping[tuple[Any, ...], tuple[str, str]],
) -> dict[str, Any]:
    ids = [item[0] for item in active]
    axes_first = active[0][2]
    key = tuple(
        (axis, axes_first[axis].get("status"), axes_first[axis].get("value"))
        for axis in AXES
        if axis != "QUALITY"
    )
    candidate = controls.get(key)
    if candidate is None:
        raise RO4IndexError(f"MATCHED_REAL_CONTROL_REQUIRED:{meta['partition_id']}:{ids[0]}")
    missingness: list[str] = []
    evidence: list[dict[str, Any]] = []
    for state_id, first_valid_time, axes in active:
        evidence.append(
            {
                "slice_identity": meta["partition_id"],
                "role": meta["role"],
                "clock": meta["clock"],
                "side": meta["side"],
                "state_id": state_id,
                "first_valid_time": first_valid_time,
                "axis_values": {axis: axes[axis] for axis in AXES},
            }
        )
        for axis in AXES:
            if axes[axis].get("status") in MISSING_STATUSES:
                missingness.append(f"{state_id}:{axis}:{axes[axis].get('status')}")
    core = {
        "authority": AUTHORITY,
        "predicate_id": CONFLICT_PREDICATE_ID,
        "source_release_id": meta["release_id"],
        "participating_axes": ["LOCATION", "QUALITY"],
        "start_state_id": ids[0],
        "end_state_id": ids[-1],
        "evidence": evidence,
        "missingness": sorted(set(missingness)),
        "matched_control_ids": [candidate[1]],
    }
    core["conflict_run_id"] = "RO4.CONFLICT." + logical_hash(core)
    core["logical_hash"] = logical_hash(core)
    return core


def _conflict_records(source: sqlite3.Connection, meta: Mapping[str, Any]) -> list[dict[str, Any]]:
    controls = _matched_control_map(source)
    active: list[tuple[str, str, dict[str, Any]]] = []
    records: list[dict[str, Any]] = []

    def flush() -> None:
        nonlocal active
        if active:
            records.append(_conflict_record(active, meta, controls))
            active = []

    query = (
        "SELECT state_record_id,first_valid_time,axes_json,continuity "
        "FROM states ORDER BY first_valid_time,state_record_id"
    )
    for state_id, first_valid_time, axes_json, continuity in source.execute(query):
        axes = json.loads(axes_json)
        conflict = (
            axes["QUALITY"].get("status") == "CONFLICT"
            and axes["QUALITY"].get("reason_code") == "AMBIGUOUS_BOUNDARY"
        )
        if continuity == "RESET":
            flush()
        if conflict:
            active.append((state_id, first_valid_time, axes))
        else:
            flush()
    flush()
    return records
