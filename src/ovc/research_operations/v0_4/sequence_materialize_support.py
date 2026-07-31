from __future__ import annotations

import hashlib
import heapq
import json
import sqlite3
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterator, Mapping

from .index_common import AXES, RO4IndexError, logical_hash, sha256_file
from .sequence_common import (
    BANNER,
    BOUNDARY_SOURCE,
    CANDIDATE_AUTHORITY,
    CONTROL_REGISTRY_ID,
    COUNT_BANNER,
    DISTANCE_REGISTRY_ID,
    OPERATION_MODE,
    SEQUENCE_AUTHORITY,
    SEQUENCE_POLICY_ID,
    blind_id,
    count_cell,
    diversity_audit,
    iter_gzip_jsonl,
    recurrence_id,
    sequence_id,
    signature_id,
    write_gzip_jsonl,
    write_json,
)
from .sequence_workspace import connect_workspace, workspace_inventory

REPRESENTATIVE_MEMBER_LIMIT = 8
REVIEW_CANDIDATE_COUNT = 20


def _hex(value: bytes) -> str:
    return value.hex()


def _seq(value: bytes) -> str:
    return sequence_id(_hex(value))


def _sig(value: bytes) -> str:
    return signature_id(_hex(value))


def _partition_map(connection: sqlite3.Connection) -> dict[int, dict[str, Any]]:
    return {
        int(row[0]): {
            "pid": int(row[0]), "partition_id": row[1], "role": row[2], "clock": row[3], "side": row[4],
            "evaluation_scope_id": row[5], "release_id": row[6], "manifest_sha256": row[7],
            "index_file": row[8], "index_file_sha256": row[9],
        }
        for row in connection.execute(
            "SELECT pid,partition_id,role,clock,side,evaluation_scope_id,release_id,manifest_sha256,index_file,index_file_sha256 FROM partitions ORDER BY partition_id"
        )
    }


def _prepare_counts(connection: sqlite3.Connection) -> None:
    connection.execute("DROP TABLE IF EXISTS temp.signature_counts")
    connection.execute("CREATE TEMP TABLE signature_counts(signature_hash BLOB PRIMARY KEY, member_count INTEGER NOT NULL) WITHOUT ROWID")
    connection.execute(
        "INSERT INTO signature_counts SELECT signature_hash,COUNT(*) FROM windows GROUP BY signature_hash"
    )
    connection.execute("CREATE INDEX IF NOT EXISTS ix_temp_signature_count ON signature_counts(member_count)")


def _control_pools(
    connection: sqlite3.Connection,
) -> tuple[
    dict[tuple[int, int], list[tuple[bytes, bytes, int, str]]],
    dict[tuple[int, int], list[tuple[bytes, bytes, int, str]]],
    dict[tuple[int, int, str], list[tuple[bytes, bytes, int, str]]],
    dict[tuple[int, int], int],
]:
    unique: dict[tuple[int, int], list[tuple[bytes, bytes, int, str]]] = defaultdict(list)
    population: dict[tuple[int, int], list[tuple[bytes, bytes, int, str]]] = defaultdict(list)
    month_pool: dict[tuple[int, int, str], list[tuple[bytes, bytes, int, str]]] = defaultdict(list)
    denominators: dict[tuple[int, int], int] = Counter()
    query = """
      SELECT w.sequence_hash,w.signature_hash,w.pid,w.calendar_partition,w.length,w.start_index,w.sample_hash,s.member_count
      FROM windows w JOIN signature_counts s ON s.signature_hash=w.signature_hash
      ORDER BY w.pid,w.length,w.sample_hash,w.sequence_hash
    """
    for seq_hash, sig_hash, pid, month, length, start_index, _, member_count in connection.execute(query):
        key = (int(pid), int(length))
        denominators[key] = denominators.get(key, 0) + 1
        item = (seq_hash, sig_hash, int(start_index), str(month))
        if len(population[key]) < 32:
            population[key].append(item)
        month_key = (int(pid), int(length), str(month))
        if len(month_pool[month_key]) < 4:
            month_pool[month_key].append(item)
        if int(member_count) == 1 and len(unique[key]) < 16:
            unique[key].append(item)
    return unique, population, month_pool, denominators


def _position_control(
    connection: sqlite3.Connection,
    *,
    pid: int,
    start_index: int,
    length: int,
    candidate_signature: bytes,
    offsets: tuple[int, ...],
) -> tuple[bytes, bytes, int, str] | None:
    for offset in offsets:
        row = connection.execute(
            "SELECT sequence_hash,signature_hash,start_index,calendar_partition FROM windows WHERE pid=? AND start_index=? AND length=?",
            (pid, start_index + offset, length),
        ).fetchone()
        if row and row[1] != candidate_signature:
            return (row[0], row[1], int(row[2]), str(row[3]))
    return None


def _different_month_control(
    month_pool: Mapping[tuple[int, int, str], list[tuple[bytes, bytes, int, str]]],
    *, pid: int, length: int, month: str, candidate_signature: bytes,
) -> tuple[bytes, bytes, int, str] | None:
    for (pool_pid, pool_length, pool_month), items in sorted(month_pool.items()):
        if pool_pid != pid or pool_length != length or pool_month == month:
            continue
        for item in items:
            if item[1] != candidate_signature:
                return item
    return None


def _choose_not_signature(
    items: list[tuple[bytes, bytes, int, str]], candidate_signature: bytes
) -> tuple[bytes, bytes, int, str] | None:
    return next((item for item in items if item[1] != candidate_signature), None)
