from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Iterator, Mapping

from .g2_common import AUTHORITY, MISSING_STATUSES, _axis_token, _metadata
from .index_common import AXES, RO4IndexError, logical_hash

def _persistence_record(
    meta: Mapping[str, Any],
    run_type: str,
    axis: str | None,
    members: list[tuple[str, str]],
    termination: str,
) -> dict[str, Any]:
    ids = [item[0] for item in members]
    core: dict[str, Any] = {
        "authority": AUTHORITY,
        "run_type": run_type,
        "source_release_id": meta["release_id"],
        "role": meta["role"],
        "clock": meta["clock"],
        "side": meta["side"],
        "start_state_id": ids[0],
        "end_state_id": ids[-1],
        "member_state_ids": ids,
        "duration_records": len(ids),
        "termination_reason": termination,
    }
    if axis is not None:
        core["axis"] = axis
    content_hash = logical_hash(core)
    core["run_id"] = "RO4.RUN." + content_hash
    core["logical_hash"] = content_hash
    return core


def _iter_persistence_records(source: sqlite3.Connection, meta: Mapping[str, Any]) -> Iterator[dict[str, Any]]:
    active: dict[str, tuple[Any, list[tuple[str, str]]]] = {}
    rows = source.execute(
        "SELECT state_record_id,first_valid_time,axes_json,continuity "
        "FROM states ORDER BY first_valid_time,state_record_id"
    )
    for state_id, first_valid_time, axes_json, continuity in rows:
        axes = json.loads(axes_json)
        tokens: dict[str, Any] = {axis: _axis_token(axes, axis) for axis in AXES}
        tokens["FULL_VECTOR"] = tuple((axis, *tokens[axis]) for axis in AXES)
        for key, token in tokens.items():
            axis = None if key == "FULL_VECTOR" else key
            run_type = "FULL_VECTOR" if key == "FULL_VECTOR" else "SINGLE_AXIS"
            prior = active.get(key)
            break_due_gap = continuity == "RESET"
            if prior is None:
                active[key] = (token, [(state_id, first_valid_time)])
                continue
            prior_token, members = prior
            if break_due_gap or token != prior_token:
                termination = "GAP" if break_due_gap else (
                    "VECTOR_CHANGE" if key == "FULL_VECTOR" else "AXIS_CHANGE"
                )
                yield _persistence_record(meta, run_type, axis, members, termination)
                active[key] = (token, [(state_id, first_valid_time)])
            else:
                members.append((state_id, first_valid_time))
    for key, (_, members) in active.items():
        axis = None if key == "FULL_VECTOR" else key
        run_type = "FULL_VECTOR" if key == "FULL_VECTOR" else "SINGLE_AXIS"
        yield _persistence_record(meta, run_type, axis, members, "CENSORED_END")


def _partition_map(index_dir: Path, source_manifest: Mapping[str, Any]) -> dict[tuple[str, str, str], Path]:
    result: dict[tuple[str, str, str], Path] = {}
    for item in source_manifest["partitions"]:
        key = (item["role"], item["side"], item["clock"])
        if item.get("evaluation_scope_id") not in {
            "GBPUSD-15M-LOCAL-v0.1",
            "GBPUSD-2H-A-L-LOCAL-v0.1",
        }:
            continue
        if key in result:
            raise RO4IndexError(f"CROSS_SCALE_PARTITION_AMBIGUOUS:{key}")
        result[key] = index_dir / item["index_file"]
    return result


def _iter_cross_scale_records(
    index_dir: Path,
    source_manifest: Mapping[str, Any],
) -> Iterator[dict[str, Any]]:
    partitions = _partition_map(index_dir, source_manifest)
    for role in ("DISCOVERY", "DEVELOPMENT"):
        for side in ("BID", "ASK"):
            local = partitions.get((role, side, "15M"))
            parent = partitions.get((role, side, "2H_A_L"))
            if local is None or parent is None:
                raise RO4IndexError(f"CROSS_SCALE_PARTITION_MISSING:{role}:{side}")
            lc = sqlite3.connect(local)
            pc = sqlite3.connect(parent)
            try:
                local_meta = _metadata(lc)
                parent_rows = list(
                    pc.execute(
                        "SELECT first_valid_time,state_record_id,axes_json "
                        "FROM states ORDER BY first_valid_time,state_record_id"
                    )
                )
                parent_index = -1
                active_parent: tuple[str, str, str] | None = None
                prior_parent_id: str | None = None
                local_query = (
                    "SELECT first_valid_time,state_record_id,axes_json "
                    "FROM states ORDER BY first_valid_time,state_record_id"
                )
                for first_valid_time, local_state_id, local_axes_json in lc.execute(local_query):
                    while (
                        parent_index + 1 < len(parent_rows)
                        and parent_rows[parent_index + 1][0] <= first_valid_time
                    ):
                        parent_index += 1
                        active_parent = parent_rows[parent_index]
                    local_axes = json.loads(local_axes_json)
                    parent_state_id: str | None = None
                    parent_time: str | None = None
                    parent_axes: dict[str, Any] | None = None
                    if active_parent is not None:
                        parent_time, parent_state_id, parent_axes_json = active_parent
                        parent_axes = json.loads(parent_axes_json)
                    relations: dict[str, dict[str, Any]] = {}
                    for axis in AXES:
                        left = _axis_token(local_axes, axis)
                        if parent_axes is None:
                            right = ("NOT_EVALUABLE", None)
                            relation = "MISSING"
                        else:
                            right = _axis_token(parent_axes, axis)
                            if left[0] in MISSING_STATUSES or right[0] in MISSING_STATUSES:
                                relation = "MISSING"
                            elif left == right:
                                relation = "ALIGNED"
                            else:
                                relation = "DIVERGENT"
                        relations[axis] = {
                            "relation": relation,
                            "local_status": left[0],
                            "local_value": left[1],
                            "parent_status": right[0],
                            "parent_value": right[1],
                        }
                    core = {
                        "authority": AUTHORITY,
                        "source_release_id": local_meta["release_id"],
                        "role": role,
                        "side": side,
                        "first_valid_time": first_valid_time,
                        "local_clock": "15M",
                        "parent_clock": "2H_A_L",
                        "local_state_id": local_state_id,
                        "parent_state_id": parent_state_id,
                        "parent_first_valid_time": parent_time,
                        "parent_changed": parent_state_id != prior_parent_id,
                        "axis_relations": relations,
                    }
                    content_hash = logical_hash(core)
                    core["projection_id"] = "RO4.XSCALE." + content_hash
                    core["logical_hash"] = content_hash
                    prior_parent_id = parent_state_id
                    yield core
            finally:
                lc.close()
                pc.close()
