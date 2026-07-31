from __future__ import annotations

import hashlib
import json
import sqlite3
import time
from collections import Counter
from pathlib import Path
from typing import Any, Iterator, Mapping

from .index_common import DeclaredSampleRequired, RO4IndexError, canonical_bytes, logical_hash, sha256_file
from .sequence_common import (
    BOUNDARY_SOURCE,
    MAX_STATES,
    MIN_STATES,
    OPERATION_MODE,
    SEQUENCE_AUTHORITY,
    SEQUENCE_POLICY_ID,
    WINDOW_CAP,
    axis_vector,
    changed_axis_set,
    exact_signature_hash,
    metadata,
    sample_hash,
)

WORKSPACE_SCHEMA = "ovc-ro4-g3-sequence-workspace/v1"


def connect_workspace(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.execute("PRAGMA journal_mode=WAL")
    connection.execute("PRAGMA synchronous=NORMAL")
    connection.execute("PRAGMA temp_store=MEMORY")
    connection.execute("PRAGMA cache_size=-512000")
    connection.execute("PRAGMA foreign_keys=ON")
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS workspace_metadata(
          key TEXT PRIMARY KEY,
          value TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS partitions(
          pid INTEGER PRIMARY KEY AUTOINCREMENT,
          partition_id TEXT NOT NULL UNIQUE,
          role TEXT NOT NULL,
          clock TEXT NOT NULL,
          side TEXT NOT NULL,
          evaluation_scope_id TEXT NOT NULL,
          release_id TEXT NOT NULL,
          manifest_sha256 TEXT NOT NULL,
          index_file TEXT NOT NULL,
          index_file_sha256 TEXT NOT NULL,
          state_count INTEGER NOT NULL,
          transition_count INTEGER NOT NULL,
          window_count INTEGER NOT NULL,
          max_calendar_partition_count INTEGER NOT NULL,
          logical_hash TEXT NOT NULL,
          built_at_runtime_seconds REAL NOT NULL
        );
        CREATE TABLE IF NOT EXISTS windows(
          sequence_hash BLOB PRIMARY KEY,
          signature_hash BLOB NOT NULL,
          pid INTEGER NOT NULL REFERENCES partitions(pid) ON DELETE CASCADE,
          calendar_partition TEXT NOT NULL,
          length INTEGER NOT NULL,
          start_index INTEGER NOT NULL,
          end_index INTEGER NOT NULL,
          sample_hash BLOB NOT NULL
        ) WITHOUT ROWID;
        CREATE INDEX IF NOT EXISTS ix_windows_signature ON windows(signature_hash, sequence_hash);
        CREATE INDEX IF NOT EXISTS ix_windows_stratum ON windows(pid, calendar_partition, length, sample_hash);
        CREATE UNIQUE INDEX IF NOT EXISTS ix_windows_position ON windows(pid, start_index, length);
        """
    )
    connection.execute(
        "INSERT OR REPLACE INTO workspace_metadata(key,value) VALUES (?,?)",
        ("schema", json.dumps(WORKSPACE_SCHEMA)),
    )
    connection.commit()
    return connection


def _load_index_manifest(index_dir: Path) -> dict[str, Any]:
    path = index_dir / "index-manifest.json"
    if not path.is_file():
        raise RO4IndexError("RO4_G1_INDEX_MANIFEST_MISSING")
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if manifest.get("authority") != "LOCAL_REPLACEABLE_DERIVED":
        raise RO4IndexError("RO4_G1_AUTHORITY_MISMATCH")
    if manifest.get("validation_consumption") != "LOCKED_UNCONSUMED":
        raise RO4IndexError("VALIDATION_DENIAL_NOT_PRESERVED")
    return manifest


def _partition_spec(index_dir: Path, partition_id: str) -> tuple[dict[str, Any], Path, dict[str, Any]]:
    manifest = _load_index_manifest(index_dir)
    matches = [item for item in manifest["partitions"] if item["partition_id"] == partition_id]
    if len(matches) != 1:
        raise RO4IndexError(f"SEQUENCE_PARTITION_NOT_EXACT:{partition_id}")
    item = matches[0]
    path = index_dir / item["index_file"]
    if not path.is_file() or sha256_file(path) != item["index_file_sha256"]:
        raise RO4IndexError(f"RO4_G1_INDEX_HASH_MISMATCH:{partition_id}")
    return item, path, manifest


def _sequence_hash(
    *,
    meta: Mapping[str, Any],
    calendar_partition: str,
    state_ids: list[str],
    transition_ids: list[str],
    first_valid_at: str,
    last_valid_at: str,
) -> str:
    core = {
        "source_release_id": meta["release_id"],
        "manifest_sha256": meta["manifest_sha256"],
        "role": meta["role"],
        "clock": meta["clock"],
        "side": meta["side"],
        "source_partition_id": meta["partition_id"],
        "evaluation_scope_id": meta["evaluation_scope_id"],
        "calendar_partition": calendar_partition,
        "boundary_source": BOUNDARY_SOURCE,
        "sequence_policy_id": SEQUENCE_POLICY_ID,
        "member_state_ids": state_ids,
        "member_transition_ids": transition_ids,
        "first_valid_at": first_valid_at,
        "last_valid_at": last_valid_at,
        "operation_mode": OPERATION_MODE,
        "authority": SEQUENCE_AUTHORITY,
    }
    return logical_hash(core)


def build_sequence_partition(*, index_dir: Path, workspace_path: Path, partition_id: str) -> dict[str, Any]:
    started = time.perf_counter()
    spec, index_path, source_manifest = _partition_spec(index_dir, partition_id)
    source = sqlite3.connect(index_path)
    try:
        meta = metadata(source)
        if meta["partition_id"] != partition_id:
            raise RO4IndexError(f"SEQUENCE_PARTITION_METADATA_MISMATCH:{partition_id}")
        states = list(
            source.execute(
                "SELECT state_record_id,first_valid_time,axes_json,continuity "
                "FROM states ORDER BY first_valid_time,state_record_id"
            )
        )
        transition_map = {
            (source_id, target_id): (transition_id, changed_json, first_valid_time, continuity)
            for transition_id, source_id, target_id, changed_json, first_valid_time, continuity in source.execute(
                "SELECT transition_id,source_state_id,target_state_id,changed_axes_json,first_valid_time,continuity_status "
                "FROM transitions ORDER BY first_valid_time,transition_id"
            )
        }
    finally:
        source.close()

    workspace = connect_workspace(workspace_path)
    calendar_counts: Counter[str] = Counter()
    partition_digest = hashlib.sha256()
    total_windows = 0
    try:
        workspace.execute("BEGIN IMMEDIATE")
        existing = workspace.execute("SELECT pid FROM partitions WHERE partition_id=?", (partition_id,)).fetchone()
        if existing:
            workspace.execute("DELETE FROM partitions WHERE pid=?", (existing[0],))
        cursor = workspace.execute(
            """
            INSERT INTO partitions(
              partition_id,role,clock,side,evaluation_scope_id,release_id,manifest_sha256,index_file,
              index_file_sha256,state_count,transition_count,window_count,max_calendar_partition_count,
              logical_hash,built_at_runtime_seconds
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                partition_id, meta["role"], meta["clock"], meta["side"], meta["evaluation_scope_id"],
                meta["release_id"], meta["manifest_sha256"], spec["index_file"], spec["index_file_sha256"],
                meta["state_count"], meta["transition_count"], 0, 0, "PENDING", 0.0,
            ),
        )
        pid = int(cursor.lastrowid)
        batch: list[tuple[bytes, bytes, int, str, int, int, int, bytes]] = []

        def emit_segment(segment: list[tuple[int, tuple[Any, ...]]], transitions: list[tuple[str, list[str]]]) -> None:
            nonlocal total_windows
            if len(segment) < MIN_STATES:
                return
            state_axes = [axis_vector(item[1][2]) for item in segment]
            state_ids = [str(item[1][0]) for item in segment]
            state_times = [str(item[1][1]) for item in segment]
            transition_ids = [item[0] for item in transitions]
            changed_sets = [item[1] for item in transitions]
            for local_start in range(len(segment) - 1):
                maximum = min(MAX_STATES, len(segment) - local_start)
                for length in range(MIN_STATES, maximum + 1):
                    local_end = local_start + length
                    ids = state_ids[local_start:local_end]
                    transition_slice = transition_ids[local_start:local_end - 1]
                    axes_slice = state_axes[local_start:local_end]
                    changed_slice = changed_sets[local_start:local_end - 1]
                    calendar_partition = state_times[local_start][:7]
                    seq_hex = _sequence_hash(
                        meta=meta,
                        calendar_partition=calendar_partition,
                        state_ids=ids,
                        transition_ids=transition_slice,
                        first_valid_at=state_times[local_start],
                        last_valid_at=state_times[local_end - 1],
                    )
                    sig_hex = exact_signature_hash(
                        role=meta["role"],
                        clock=meta["clock"],
                        side=meta["side"],
                        evaluation_scope_id=meta["evaluation_scope_id"],
                        state_axes=axes_slice,
                        changed_axes=changed_slice,
                    )
                    global_start = int(segment[local_start][0])
                    global_end = int(segment[local_end - 1][0])
                    sample = sample_hash("RO4.SEQUENCE." + seq_hex)
                    batch.append(
                        (
                            bytes.fromhex(seq_hex), bytes.fromhex(sig_hex), pid, calendar_partition,
                            length, global_start, global_end, sample,
                        )
                    )
                    partition_digest.update(bytes.fromhex(seq_hex))
                    partition_digest.update(bytes.fromhex(sig_hex))
                    calendar_counts[calendar_partition] += 1
                    total_windows += 1
                    if len(batch) >= 25_000:
                        workspace.executemany("INSERT INTO windows VALUES (?,?,?,?,?,?,?,?)", batch)
                        batch.clear()

        segment: list[tuple[int, tuple[Any, ...]]] = []
        segment_transitions: list[tuple[str, list[str]]] = []
        for index, state in enumerate(states):
            if not segment:
                segment = [(index, state)]
                continue
            previous = segment[-1][1]
            transition = transition_map.get((previous[0], state[0]))
            if (
                state[3] == "RESET"
                or transition is None
                or transition[3] != "CONTIGUOUS"
                or transition[2] != state[1]
            ):
                emit_segment(segment, segment_transitions)
                segment = [(index, state)]
                segment_transitions = []
            else:
                segment.append((index, state))
                segment_transitions.append((str(transition[0]), changed_axis_set(str(transition[1]))))
        emit_segment(segment, segment_transitions)
        if batch:
            workspace.executemany("INSERT INTO windows VALUES (?,?,?,?,?,?,?,?)", batch)
        maximum_calendar = max(calendar_counts.values(), default=0)
        if maximum_calendar > WINDOW_CAP:
            raise DeclaredSampleRequired(
                f"SEQUENCE_WINDOW_CAP_EXCEEDED:{partition_id}:{maximum_calendar}:{WINDOW_CAP}"
            )
        runtime = time.perf_counter() - started
        digest = partition_digest.hexdigest()
        workspace.execute(
            """
            UPDATE partitions SET window_count=?,max_calendar_partition_count=?,logical_hash=?,built_at_runtime_seconds=?
            WHERE pid=?
            """,
            (total_windows, maximum_calendar, digest, 0.0, pid),
        )
        workspace.execute(
            "INSERT OR REPLACE INTO workspace_metadata(key,value) VALUES (?,?)",
            ("source_g1_logical_hash", json.dumps(source_manifest["logical_hash"])),
        )
        workspace.execute(
            "INSERT OR REPLACE INTO workspace_metadata(key,value) VALUES (?,?)",
            ("validation_consumption", json.dumps("LOCKED_UNCONSUMED")),
        )
        workspace.commit()
    except Exception:
        workspace.rollback()
        raise
    finally:
        workspace.close()
    return {
        "partition_id": partition_id,
        "window_count": total_windows,
        "max_calendar_partition_count": max(calendar_counts.values(), default=0),
        "logical_hash": partition_digest.hexdigest(),
        "runtime_seconds": round(time.perf_counter() - started, 6),
    }


def workspace_inventory(workspace_path: Path) -> dict[str, Any]:
    connection = connect_workspace(workspace_path)
    try:
        partitions = [
            {
                "partition_id": row[0], "role": row[1], "clock": row[2], "side": row[3],
                "evaluation_scope_id": row[4], "release_id": row[5], "manifest_sha256": row[6],
                "index_file": row[7], "index_file_sha256": row[8], "state_count": row[9],
                "transition_count": row[10], "window_count": row[11],
                "max_calendar_partition_count": row[12], "logical_hash": row[13],
            }
            for row in connection.execute(
                "SELECT partition_id,role,clock,side,evaluation_scope_id,release_id,manifest_sha256,index_file,index_file_sha256,state_count,transition_count,window_count,max_calendar_partition_count,logical_hash,built_at_runtime_seconds FROM partitions ORDER BY partition_id"
            )
        ]
        source_hash_row = connection.execute(
            "SELECT value FROM workspace_metadata WHERE key='source_g1_logical_hash'"
        ).fetchone()
        validation_row = connection.execute(
            "SELECT value FROM workspace_metadata WHERE key='validation_consumption'"
        ).fetchone()
        core = {
            "schema": WORKSPACE_SCHEMA,
            "source_g1_logical_hash": json.loads(source_hash_row[0]) if source_hash_row else None,
            "validation_consumption": json.loads(validation_row[0]) if validation_row else None,
            "sequence_policy_id": SEQUENCE_POLICY_ID,
            "window_cap_per_calendar_partition": WINDOW_CAP,
            "partitions": partitions,
            "window_count": sum(item["window_count"] for item in partitions),
            "sample_state": "FULL_POPULATION_NO_SAMPLING",
        }
        core["logical_hash"] = logical_hash(core)
        return core
    finally:
        connection.close()
