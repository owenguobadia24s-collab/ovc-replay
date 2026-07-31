from __future__ import annotations

import hashlib
import json
import os
import platform
import resource
import sqlite3
import sys
import time
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from .index_common import (
    AXES, DEFAULT_WINDOW_CAP, SCHEMA_VERSION, DeclaredSampleRequired, PartitionSpec,
    ReleaseBinding, RO4IndexError, BuildResult, canonical_bytes,
    logical_hash, parse_utc, sha256_file, _load_inventory,
    _read_jsonl, _resolve_verified, _require_no_forbidden, interval_for,
)

def _sqlite_connect(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(path)
    connection.execute("PRAGMA journal_mode=DELETE")
    connection.execute("PRAGMA synchronous=FULL")
    connection.execute("PRAGMA temp_store=FILE")
    connection.execute("PRAGMA foreign_keys=OFF")
    connection.executescript(
        """
        CREATE TABLE metadata(key TEXT PRIMARY KEY, value TEXT NOT NULL);
        CREATE TABLE states(
          state_record_id TEXT PRIMARY KEY,
          release_id TEXT NOT NULL,
          manifest_sha256 TEXT NOT NULL,
          role TEXT NOT NULL,
          instrument TEXT NOT NULL,
          clock TEXT NOT NULL,
          side TEXT NOT NULL,
          evaluation_scope_id TEXT NOT NULL,
          interval_open TEXT NOT NULL,
          interval_close TEXT NOT NULL,
          first_valid_time TEXT NOT NULL,
          axes_json TEXT NOT NULL,
          axis_values_json TEXT NOT NULL,
          parent_c1_record_id TEXT NOT NULL,
          parent_opt_a_bar_id TEXT NOT NULL,
          continuity TEXT NOT NULL,
          source_line INTEGER NOT NULL,
          source_record_sha256 TEXT NOT NULL
        );
        CREATE TABLE transitions(
          transition_id TEXT PRIMARY KEY,
          release_id TEXT NOT NULL,
          role TEXT NOT NULL,
          clock TEXT NOT NULL,
          side TEXT NOT NULL,
          evaluation_scope_id TEXT NOT NULL,
          source_state_id TEXT NOT NULL REFERENCES states(state_record_id),
          target_state_id TEXT NOT NULL REFERENCES states(state_record_id),
          changed_axes_json TEXT NOT NULL,
          first_valid_time TEXT NOT NULL,
          continuity_status TEXT NOT NULL,
          source_line INTEGER NOT NULL,
          source_record_sha256 TEXT NOT NULL
        );
        """
    )
    return connection


def _normalise_axis_values(axes: Mapping[str, Any], context: str) -> dict[str, Any]:
    if set(axes) != set(AXES):
        raise RO4IndexError(f"FIVE_AXIS_SET_MISMATCH:{context}")
    values: dict[str, Any] = {}
    for axis in AXES:
        item = axes[axis]
        if not isinstance(item, dict):
            raise RO4IndexError(f"AXIS_OBJECT_REQUIRED:{context}:{axis}")
        status = item.get("status")
        value = item.get("value")
        if status not in {"EVALUATED", "NOT_EVALUATED", "NOT_EVALUABLE", "CONFLICT", "QUARANTINED"}:
            raise RO4IndexError(f"UNKNOWN_AXIS_STATUS:{context}:{axis}:{status}")
        if status in {"NOT_EVALUATED", "NOT_EVALUABLE", "QUARANTINED"} and value is not None:
            raise RO4IndexError(f"NON_EVALUATED_AXIS_HAS_VALUE:{context}:{axis}")
        if status == "EVALUATED" and value is None:
            raise RO4IndexError(f"EVALUATED_AXIS_MISSING_VALUE:{context}:{axis}")
        if status == "CONFLICT" and value not in {None, "CONFLICT"}:
            raise RO4IndexError(f"CONFLICT_AXIS_VALUE_INVALID:{context}:{axis}")
        values[axis] = value
    return values


def _state_projection(
    row: Mapping[str, Any], binding: ReleaseBinding, spec: PartitionSpec, line_number: int
) -> tuple[Any, ...]:
    _require_no_forbidden(row, f"STATE:{spec.partition_id}:{line_number}")
    required = {
        "c2_state_id",
        "role",
        "clock",
        "side",
        "evaluation_scope_id",
        "first_valid_time",
        "axes",
        "parent_c1_record_id",
        "parent_opt_a_bar_id",
        "c1_release_id",
        "c1_manifest_id",
        "opt_a_release_id",
        "opt_a_manifest_id",
        "continuity",
    }
    missing = sorted(required.difference(row))
    if missing:
        raise RO4IndexError(f"STATE_REQUIRED_FIELD_MISSING:{spec.partition_id}:{line_number}:{','.join(missing)}")
    if row["role"] != spec.role or row["clock"] != spec.clock or row["side"] != spec.side:
        raise RO4IndexError(f"STATE_PARTITION_MISMATCH:{spec.partition_id}:{line_number}")
    if row["evaluation_scope_id"] != spec.evaluation_scope_id:
        raise RO4IndexError(f"STATE_SCOPE_MISMATCH:{spec.partition_id}:{line_number}")
    if row["c1_release_id"] != binding.c1_release_id or row["c1_manifest_id"] != binding.c1_manifest_id:
        raise RO4IndexError(f"STATE_C1_SOURCE_MISMATCH:{spec.partition_id}:{line_number}")
    if row["opt_a_release_id"] != binding.opt_a_release_id or row["opt_a_manifest_id"] != binding.opt_a_manifest_id:
        raise RO4IndexError(f"STATE_OPT_A_SOURCE_MISMATCH:{spec.partition_id}:{line_number}")
    if row["continuity"] not in {"RESET", "CONTIGUOUS"}:
        raise RO4IndexError(f"UNKNOWN_CONTINUITY:{spec.partition_id}:{line_number}")
    state_id = row["c2_state_id"]
    if not isinstance(state_id, str) or not state_id.startswith("c2-state:"):
        raise RO4IndexError(f"INVALID_STATE_ID:{spec.partition_id}:{line_number}")
    first_valid = str(row["first_valid_time"])
    interval_open, interval_close = interval_for(spec.clock, first_valid)
    axes = row["axes"]
    if not isinstance(axes, dict):
        raise RO4IndexError(f"AXES_OBJECT_REQUIRED:{spec.partition_id}:{line_number}")
    values = _normalise_axis_values(axes, f"{spec.partition_id}:{line_number}")
    record_sha = logical_hash(row)
    return (
        state_id,
        binding.release_id,
        binding.manifest_sha256,
        binding.role,
        "GBPUSD",
        spec.clock,
        spec.side,
        spec.evaluation_scope_id,
        interval_open,
        interval_close,
        first_valid,
        json.dumps(axes, sort_keys=True, separators=(",", ":")),
        json.dumps(values, sort_keys=True, separators=(",", ":")),
        str(row["parent_c1_record_id"]),
        str(row["parent_opt_a_bar_id"]),
        str(row["continuity"]),
        line_number,
        record_sha,
    )


def _transition_projection(
    row: Mapping[str, Any], binding: ReleaseBinding, spec: PartitionSpec, line_number: int
) -> tuple[Any, ...]:
    _require_no_forbidden(row, f"TRANSITION:{spec.partition_id}:{line_number}")
    required = {
        "c2_transition_id",
        "role",
        "clock",
        "side",
        "evaluation_scope_id",
        "from_state_id",
        "to_state_id",
        "changed_axes",
        "first_valid_time",
        "status",
    }
    missing = sorted(required.difference(row))
    if missing:
        raise RO4IndexError(f"TRANSITION_REQUIRED_FIELD_MISSING:{spec.partition_id}:{line_number}:{','.join(missing)}")
    if row["role"] != spec.role or row["clock"] != spec.clock or row["side"] != spec.side:
        raise RO4IndexError(f"TRANSITION_PARTITION_MISMATCH:{spec.partition_id}:{line_number}")
    if row["evaluation_scope_id"] != spec.evaluation_scope_id:
        raise RO4IndexError(f"TRANSITION_SCOPE_MISMATCH:{spec.partition_id}:{line_number}")
    if row["status"] != "OBSERVED":
        raise RO4IndexError(f"TRANSITION_STATUS_NOT_OBSERVED:{spec.partition_id}:{line_number}")
    transition_id = row["c2_transition_id"]
    if not isinstance(transition_id, str) or not transition_id.startswith("c2-transition:"):
        raise RO4IndexError(f"INVALID_TRANSITION_ID:{spec.partition_id}:{line_number}")
    axes = row["changed_axes"]
    if not isinstance(axes, list) or not axes or len(set(axes)) != len(axes) or not set(axes).issubset(AXES):
        raise RO4IndexError(f"INVALID_CHANGED_AXES:{spec.partition_id}:{line_number}")
    first_valid = str(row["first_valid_time"])
    parse_utc(first_valid)
    return (
        transition_id,
        binding.release_id,
        binding.role,
        spec.clock,
        spec.side,
        spec.evaluation_scope_id,
        str(row["from_state_id"]),
        str(row["to_state_id"]),
        json.dumps(sorted(axes), separators=(",", ":")),
        first_valid,
        "CONTIGUOUS",
        line_number,
        logical_hash(row),
    )


def _build_partition(
    source_root: Path,
    output_dir: Path,
    spec: PartitionSpec,
    binding: ReleaseBinding,
) -> dict[str, Any]:
    state_path = _resolve_verified(source_root, spec.state_path, spec.state_size_bytes, spec.state_sha256)
    transition_path = _resolve_verified(
        source_root, spec.transition_path, spec.transition_size_bytes, spec.transition_sha256
    )
    temp = output_dir / f".{spec.partition_id}.sqlite.tmp"
    final = output_dir / f"{spec.partition_id}.sqlite"
    temp.unlink(missing_ok=True)
    connection = _sqlite_connect(temp)
    state_digest = hashlib.sha256()
    transition_digest = hashlib.sha256()
    state_count = 0
    transition_count = 0
    state_endpoints: dict[str, tuple[str, str]] = {}
    first_time: str | None = None
    last_time: str | None = None
    try:
        insert_state = "INSERT INTO states VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)"
        batch: list[tuple[Any, ...]] = []
        for line_number, row in _read_jsonl(state_path):
            projected = _state_projection(row, binding, spec, line_number)
            batch.append(projected)
            state_endpoints[projected[0]] = (projected[10], projected[15])
            state_digest.update(canonical_bytes(projected[:-2]))
            timestamp = projected[10]
            first_time = timestamp if first_time is None else min(first_time, timestamp)
            last_time = timestamp if last_time is None else max(last_time, timestamp)
            state_count += 1
            if len(batch) >= 2000:
                connection.executemany(insert_state, batch)
                batch.clear()
        if batch:
            connection.executemany(insert_state, batch)
        if state_count != spec.state_record_count:
            raise RO4IndexError(
                f"STATE_CARDINALITY_MISMATCH:{spec.partition_id}:{state_count}:{spec.state_record_count}"
            )

        insert_transition = "INSERT INTO transitions VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)"
        batch = []
        for line_number, row in _read_jsonl(transition_path):
            projected = _transition_projection(row, binding, spec, line_number)
            source = state_endpoints.get(projected[6])
            target = state_endpoints.get(projected[7])
            if source is None or target is None:
                raise RO4IndexError(f"TRANSITION_ENDPOINT_MISSING:{spec.partition_id}:{line_number}")
            if not source[0] < target[0] or target[0] != projected[9]:
                raise RO4IndexError(f"TRANSITION_ENDPOINT_CHRONOLOGY:{spec.partition_id}:{line_number}")
            if target[1] != "CONTIGUOUS":
                raise RO4IndexError(f"TRANSITION_CROSSES_RESET:{spec.partition_id}:{line_number}")
            batch.append(projected)
            transition_digest.update(canonical_bytes(projected[:-2]))
            transition_count += 1
            if len(batch) >= 2000:
                connection.executemany(insert_transition, batch)
                batch.clear()
        if batch:
            connection.executemany(insert_transition, batch)
        if transition_count != spec.transition_record_count:
            raise RO4IndexError(
                f"TRANSITION_CARDINALITY_MISMATCH:{spec.partition_id}:{transition_count}:{spec.transition_record_count}"
            )
        metadata = {
            "schema": SCHEMA_VERSION,
            "partition_id": spec.partition_id,
            "role": spec.role,
            "clock": spec.clock,
            "side": spec.side,
            "evaluation_scope_id": spec.evaluation_scope_id,
            "release_id": binding.release_id,
            "manifest_sha256": binding.manifest_sha256,
            "state_count": state_count,
            "transition_count": transition_count,
            "first_valid_time": first_time,
            "last_valid_time": last_time,
            "state_logical_hash": state_digest.hexdigest(),
            "transition_logical_hash": transition_digest.hexdigest(),
        }
        metadata["partition_logical_hash"] = logical_hash(metadata)
        connection.executemany(
            "INSERT INTO metadata(key,value) VALUES (?,?)",
            [(key, json.dumps(value, sort_keys=True, separators=(",", ":"))) for key, value in sorted(metadata.items())],
        )
        connection.execute("CREATE INDEX states_time ON states(first_valid_time, state_record_id)")
        connection.execute("CREATE INDEX transitions_time ON transitions(first_valid_time, transition_id)")
        connection.commit()
    except sqlite3.IntegrityError as exc:
        raise RO4IndexError(f"DUPLICATE_OR_FOREIGN_KEY_FAILURE:{spec.partition_id}:{exc}") from exc
    finally:
        connection.close()
    os.replace(temp, final)
    return {
        **metadata,
        "index_file": final.name,
        "index_file_sha256": sha256_file(final),
        "index_size_bytes": final.stat().st_size,
    }


