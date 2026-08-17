from __future__ import annotations

"""Disk-spooled execution adapter for the frozen C2P2-RS0 empirical runtime.

The adapter preserves the v0.1 Candidate–Tracklet–ObjectAssertion reference
semantics while moving population-sized histories and mutable research state to
SQLite.  It is a materialisation strategy only: it does not select or activate
an ObjectPack and it does not grant real-source launch authority.
"""

from hashlib import sha256
import heapq
import json
from pathlib import Path
import sqlite3
from typing import Any, Iterable, Iterator, Mapping, Sequence

from .rs0_empirical_runtime import (
    RUNTIME_BINDING_ID,
    RUNTIME_SCHEMA,
    RS0EmpiricalRuntimeError,
    _append_tracklet,
    _candidate_record,
    _create_assertion,
    _decision,
    _evidence_vector,
    _hash,
    _open_tracklet,
    _scope_key,
    _update_assertion,
)
from .rs0_empirical_semantics import evaluate_pair, normalize_candidate_source_row


ADAPTER_SCHEMA = "ovc-c2p2-rs0-empirical-runtime-spooled-adapter-result/v1"
ADAPTER_ID = "C2P2_RS0_EMPIRICAL_RUNTIME_SPOOLED_ADAPTER_v0_1"
DEFAULT_CHECKPOINT_CADENCE = 256


class RS0SpooledRuntimeError(RS0EmpiricalRuntimeError):
    pass


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _sha256_bytes(value: bytes) -> str:
    return sha256(value).hexdigest()


def _validate_spec(candidate_spec: Mapping[str, Any]) -> str:
    required = {"candidate_id", "semantic_candidate_id", "activation_eligible"}
    if not required.issubset(candidate_spec):
        raise RS0SpooledRuntimeError("RS0_RUNTIME_CANDIDATE_SPEC_INCOMPLETE")
    if candidate_spec.get("activation_eligible") is not False:
        raise RS0SpooledRuntimeError("RS0_RUNTIME_ACTIVATION_FORBIDDEN")
    semantic_id = str(candidate_spec["semantic_candidate_id"])
    if not semantic_id.endswith("-v2"):
        raise RS0SpooledRuntimeError("RS0_RUNTIME_SEMANTIC_PROFILE_INVALID")
    return semantic_id


def _connect(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(path)
    connection.execute("PRAGMA journal_mode=DELETE")
    connection.execute("PRAGMA synchronous=NORMAL")
    connection.execute("PRAGMA temp_store=FILE")
    connection.executescript(
        """
        CREATE TABLE metadata (
            key TEXT PRIMARY KEY,
            value_json TEXT NOT NULL
        );
        CREATE TABLE processed_source_ids (
            ordinal INTEGER PRIMARY KEY,
            source_id TEXT NOT NULL UNIQUE
        );
        CREATE TABLE candidates (
            ordinal INTEGER PRIMARY KEY,
            value_json TEXT NOT NULL
        );
        CREATE TABLE tracklets (
            tracklet_id TEXT PRIMARY KEY,
            ordinal INTEGER NOT NULL UNIQUE,
            scope_key TEXT NOT NULL,
            state TEXT NOT NULL,
            value_json TEXT NOT NULL
        );
        CREATE INDEX tracklets_scope_state_id
            ON tracklets(scope_key, state, tracklet_id);
        CREATE TABLE assertions (
            assertion_id TEXT PRIMARY KEY,
            ordinal INTEGER NOT NULL UNIQUE,
            scope_key TEXT NOT NULL,
            value_json TEXT NOT NULL
        );
        CREATE INDEX assertions_scope_id
            ON assertions(scope_key, assertion_id);
        CREATE TABLE decisions (
            ordinal INTEGER PRIMARY KEY,
            value_json TEXT NOT NULL
        );
        CREATE TABLE evidence_vectors (
            ordinal INTEGER PRIMARY KEY,
            value_json TEXT NOT NULL
        );
        """
    )
    return connection


def _put_metadata(connection: sqlite3.Connection, key: str, value: Any) -> None:
    connection.execute(
        "INSERT OR REPLACE INTO metadata(key, value_json) VALUES (?, ?)",
        (key, _canonical_json(value)),
    )


def _get_metadata(connection: sqlite3.Connection, key: str) -> Any:
    row = connection.execute(
        "SELECT value_json FROM metadata WHERE key = ?", (key,)
    ).fetchone()
    if row is None:
        raise RS0SpooledRuntimeError(f"RS0_SPOOLED_METADATA_MISSING:{key}")
    return json.loads(row[0])


def _insert_ordered(connection: sqlite3.Connection, table: str, ordinal: int, value: Mapping[str, Any]) -> None:
    connection.execute(
        f"INSERT INTO {table}(ordinal, value_json) VALUES (?, ?)",
        (ordinal, _canonical_json(dict(value))),
    )


def _upsert_tracklet(
    connection: sqlite3.Connection,
    tracklet: Mapping[str, Any],
    *,
    next_ordinal: int,
) -> int:
    tracklet_id = str(tracklet["tracklet_id"])
    existing = connection.execute(
        "SELECT ordinal FROM tracklets WHERE tracklet_id = ?", (tracklet_id,)
    ).fetchone()
    if existing is None:
        ordinal = next_ordinal
        next_ordinal += 1
        connection.execute(
            """
            INSERT INTO tracklets(tracklet_id, ordinal, scope_key, state, value_json)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                tracklet_id,
                ordinal,
                _scope_key(tracklet["hard_scope"]),
                str(tracklet["state"]),
                _canonical_json(dict(tracklet)),
            ),
        )
    else:
        connection.execute(
            """
            UPDATE tracklets
            SET scope_key = ?, state = ?, value_json = ?
            WHERE tracklet_id = ?
            """,
            (
                _scope_key(tracklet["hard_scope"]),
                str(tracklet["state"]),
                _canonical_json(dict(tracklet)),
                tracklet_id,
            ),
        )
    return next_ordinal


def _upsert_assertion(
    connection: sqlite3.Connection,
    assertion: Mapping[str, Any],
    *,
    next_ordinal: int,
) -> int:
    assertion_id = str(assertion["object_assertion_id"])
    existing = connection.execute(
        "SELECT ordinal FROM assertions WHERE assertion_id = ?", (assertion_id,)
    ).fetchone()
    if existing is None:
        ordinal = next_ordinal
        next_ordinal += 1
        connection.execute(
            """
            INSERT INTO assertions(assertion_id, ordinal, scope_key, value_json)
            VALUES (?, ?, ?, ?)
            """,
            (
                assertion_id,
                ordinal,
                _scope_key(assertion["hard_scope"]),
                _canonical_json(dict(assertion)),
            ),
        )
    else:
        connection.execute(
            """
            UPDATE assertions
            SET scope_key = ?, value_json = ?
            WHERE assertion_id = ?
            """,
            (
                _scope_key(assertion["hard_scope"]),
                _canonical_json(dict(assertion)),
                assertion_id,
            ),
        )
    return next_ordinal


def _ordered_values(connection: sqlite3.Connection, table: str) -> Iterator[dict[str, Any]]:
    cursor = connection.execute(
        f"SELECT value_json FROM {table} ORDER BY ordinal"
    )
    for (value_json,) in cursor:
        yield json.loads(value_json)


def _final_indexes(connection: sqlite3.Connection) -> dict[str, dict[str, list[str]]]:
    assertion_index: dict[str, list[str]] = {}
    for scope_key, assertion_id in connection.execute(
        "SELECT scope_key, assertion_id FROM assertions ORDER BY scope_key, assertion_id"
    ):
        assertion_index.setdefault(scope_key, []).append(assertion_id)
    tracklet_index: dict[str, list[str]] = {}
    for scope_key, tracklet_id in connection.execute(
        """
        SELECT scope_key, tracklet_id
        FROM tracklets
        WHERE state = 'OPEN'
        ORDER BY scope_key, tracklet_id
        """
    ):
        tracklet_index.setdefault(scope_key, []).append(tracklet_id)
    return {
        "assertion_ids_by_scope": assertion_index,
        "open_tracklet_ids_by_scope": tracklet_index,
    }


def merge_canonical_source_streams(
    streams: Sequence[Iterable[Mapping[str, Any]]],
) -> Iterator[Mapping[str, Any]]:
    """Merge individually canonical source streams without population materialisation."""

    iterators = [iter(stream) for stream in streams]
    previous_keys: list[tuple[str, str] | None] = [None] * len(iterators)
    heap: list[tuple[tuple[str, str], int, Mapping[str, Any]]] = []

    def push_next(index: int) -> None:
        try:
            row = next(iterators[index])
        except StopIteration:
            return
        material = normalize_candidate_source_row(row)
        key = (material["first_valid_time"], material["source_record_id"])
        previous = previous_keys[index]
        if previous is not None and key <= previous:
            raise RS0SpooledRuntimeError(
                f"RS0_SPOOLED_SOURCE_STREAM_NONMONOTONIC:{index}"
            )
        previous_keys[index] = key
        heapq.heappush(heap, (key, index, row))

    for stream_index in range(len(iterators)):
        push_next(stream_index)

    while heap:
        _, stream_index, row = heapq.heappop(heap)
        yield row
        push_next(stream_index)


def run_spooled_empirical_runtime(
    rows: Iterable[Mapping[str, Any]],
    candidate_spec: Mapping[str, Any],
    dependency_registry: Mapping[str, Any],
    *,
    work_dir: str | Path,
    explicit_discontinuity_source_ids: Iterable[str] = (),
    prior_terminal_break_source_ids: Iterable[str] = (),
    checkpoint_cadence: int = DEFAULT_CHECKPOINT_CADENCE,
    export_streams: bool = True,
    storage_limit_bytes: int | None = None,
) -> dict[str, Any]:
    """Execute exact v0.1 semantics with population-sized state spooled to disk.

    ``rows`` must already be in canonical ``(first_valid_time, source_record_id)``
    order.  Use :func:`merge_canonical_source_streams` when multiple canonical
    source files must be interleaved.
    """

    semantic_id = _validate_spec(candidate_spec)
    if checkpoint_cadence <= 0:
        raise RS0SpooledRuntimeError("RS0_SPOOLED_CHECKPOINT_CADENCE_INVALID")

    root = Path(work_dir)
    root.mkdir(parents=True, exist_ok=True)
    database_path = root / "runtime-spool.sqlite3"
    if database_path.exists():
        raise RS0SpooledRuntimeError("RS0_SPOOLED_WORKDIR_NOT_EMPTY")

    connection = _connect(database_path)
    discontinuities = set(explicit_discontinuity_source_ids)
    terminal_breaks = set(prior_terminal_break_source_ids)

    _put_metadata(connection, "candidate_spec", dict(candidate_spec))
    _put_metadata(connection, "runtime_binding_id", RUNTIME_BINDING_ID)
    _put_metadata(connection, "adapter_id", ADAPTER_ID)
    _put_metadata(connection, "selection_state", "UNSELECTED_RESEARCH_CANDIDATE")
    _put_metadata(connection, "activation_state", "NONE")
    _put_metadata(connection, "real_source_launch", "NOT_AUTHORISED_BY_RUNTIME")

    next_candidate = 0
    next_tracklet = 0
    next_assertion = 0
    next_decision = 0
    next_vector = 0
    next_processed = 0
    last_key: tuple[str, str] | None = None

    try:
        for raw_row in rows:
            material = normalize_candidate_source_row(raw_row)
            source_id = str(material["source_record_id"])
            order_key = (str(material["first_valid_time"]), source_id)
            if connection.execute(
                "SELECT 1 FROM processed_source_ids WHERE source_id = ?",
                (source_id,),
            ).fetchone() is not None:
                raise RS0SpooledRuntimeError(
                    f"RS0_RUNTIME_DUPLICATE_SOURCE_RECORD:{source_id}"
                )
            if last_key is not None and order_key <= last_key:
                raise RS0SpooledRuntimeError("RS0_RUNTIME_NONMONOTONIC_RESTART_STREAM")
            connection.execute(
                "INSERT INTO processed_source_ids(ordinal, source_id) VALUES (?, ?)",
                (next_processed, source_id),
            )

            candidate = _candidate_record(candidate_spec, material)
            _insert_ordered(connection, "candidates", next_candidate, candidate)
            next_candidate += 1

            scope = _scope_key(candidate["hard_scope"])
            is_discontinuity = source_id in discontinuities
            is_terminal_break = source_id in terminal_breaks

            assertion_vector_ids: list[str] = []
            eligible_assertions: list[str] = []
            assertion_cursor = connection.execute(
                """
                SELECT assertion_id, value_json
                FROM assertions
                WHERE scope_key = ?
                ORDER BY assertion_id
                """,
                (scope,),
            )
            for assertion_id, value_json in assertion_cursor:
                assertion = json.loads(value_json)
                pair = evaluate_pair(
                    semantic_id,
                    assertion["latest_material"],
                    material,
                    dependency_registry,
                    prior_terminal_break=is_terminal_break,
                    explicit_discontinuity=is_discontinuity,
                )
                vector = _evidence_vector(
                    candidate, "OBJECT_ASSERTION", assertion_id, pair
                )
                _insert_ordered(connection, "evidence_vectors", next_vector, vector)
                next_vector += 1
                assertion_vector_ids.append(vector["evidence_vector_id"])
                if pair["same_object_pair_supported"]:
                    eligible_assertions.append(assertion_id)

            if len(eligible_assertions) > 1:
                decision = _decision(
                    candidate,
                    "AMBIGUOUS",
                    eligible_assertion_ids=eligible_assertions,
                    evidence_vector_ids=assertion_vector_ids,
                )
            elif len(eligible_assertions) == 1:
                assertion_id = eligible_assertions[0]
                value_json = connection.execute(
                    "SELECT value_json FROM assertions WHERE assertion_id = ?",
                    (assertion_id,),
                ).fetchone()[0]
                updated_assertion = _update_assertion(
                    json.loads(value_json), candidate, material
                )
                next_assertion = _upsert_assertion(
                    connection,
                    updated_assertion,
                    next_ordinal=next_assertion,
                )
                decision = _decision(
                    candidate,
                    "UPDATE",
                    eligible_assertion_ids=[assertion_id],
                    evidence_vector_ids=assertion_vector_ids,
                    resulting_subject_id=assertion_id,
                )
            else:
                tracklet_vector_ids: list[str] = []
                eligible_tracklets: list[str] = []
                tracklet_cursor = connection.execute(
                    """
                    SELECT tracklet_id, value_json
                    FROM tracklets
                    WHERE scope_key = ? AND state = 'OPEN'
                    ORDER BY tracklet_id
                    """,
                    (scope,),
                )
                for tracklet_id, value_json in tracklet_cursor:
                    tracklet = json.loads(value_json)
                    pair = evaluate_pair(
                        semantic_id,
                        tracklet["latest_material"],
                        material,
                        dependency_registry,
                        prior_terminal_break=is_terminal_break,
                        explicit_discontinuity=is_discontinuity,
                    )
                    vector = _evidence_vector(
                        candidate, "TRACKLET", tracklet_id, pair
                    )
                    _insert_ordered(
                        connection, "evidence_vectors", next_vector, vector
                    )
                    next_vector += 1
                    tracklet_vector_ids.append(vector["evidence_vector_id"])
                    if pair["same_object_pair_supported"]:
                        eligible_tracklets.append(tracklet_id)

                if is_discontinuity or is_terminal_break:
                    reason = (
                        "RS0_EXPLICIT_SOURCE_DISCONTINUITY"
                        if is_discontinuity
                        else "RS0_PRIOR_TERMINAL_BREAK"
                    )
                    censor_cursor = connection.execute(
                        """
                        SELECT tracklet_id, value_json
                        FROM tracklets
                        WHERE scope_key = ? AND state = 'OPEN'
                        ORDER BY tracklet_id
                        """,
                        (scope,),
                    )
                    censor_rows = list(censor_cursor)
                    for _, value_json in censor_rows:
                        tracklet = json.loads(value_json)
                        tracklet["state"] = "CENSORED"
                        tracklet["reason_codes"] = [reason]
                        next_tracklet = _upsert_tracklet(
                            connection, tracklet, next_ordinal=next_tracklet
                        )
                    eligible_tracklets = []

                all_vector_ids = assertion_vector_ids + tracklet_vector_ids
                if len(eligible_tracklets) > 1:
                    for tracklet_id in eligible_tracklets:
                        value_json = connection.execute(
                            "SELECT value_json FROM tracklets WHERE tracklet_id = ?",
                            (tracklet_id,),
                        ).fetchone()[0]
                        tracklet = json.loads(value_json)
                        tracklet["state"] = "AMBIGUOUS"
                        tracklet["reason_codes"] = [
                            "RS0_EQUAL_LAWFUL_TRACKLET_COMPETITOR"
                        ]
                        next_tracklet = _upsert_tracklet(
                            connection, tracklet, next_ordinal=next_tracklet
                        )
                    decision = _decision(
                        candidate,
                        "AMBIGUOUS",
                        eligible_tracklet_ids=eligible_tracklets,
                        evidence_vector_ids=all_vector_ids,
                    )
                elif len(eligible_tracklets) == 1:
                    tracklet_id = eligible_tracklets[0]
                    value_json = connection.execute(
                        "SELECT value_json FROM tracklets WHERE tracklet_id = ?",
                        (tracklet_id,),
                    ).fetchone()[0]
                    updated = _append_tracklet(
                        json.loads(value_json), candidate, material
                    )
                    next_tracklet = _upsert_tracklet(
                        connection, updated, next_ordinal=next_tracklet
                    )
                    if updated["state"] == "CONFIRMED":
                        assertion = _create_assertion(updated)
                        next_assertion = _upsert_assertion(
                            connection, assertion, next_ordinal=next_assertion
                        )
                        terminal = "GENESIS"
                        subject_id = assertion["object_assertion_id"]
                    else:
                        terminal = "TRACKLET_UPDATE"
                        subject_id = tracklet_id
                    decision = _decision(
                        candidate,
                        terminal,
                        eligible_tracklet_ids=[tracklet_id],
                        evidence_vector_ids=all_vector_ids,
                        resulting_subject_id=subject_id,
                    )
                else:
                    tracklet = _open_tracklet(candidate, material)
                    next_tracklet = _upsert_tracklet(
                        connection, tracklet, next_ordinal=next_tracklet
                    )
                    decision = _decision(
                        candidate,
                        "NEW_TRACKLET",
                        evidence_vector_ids=all_vector_ids,
                        resulting_subject_id=tracklet["tracklet_id"],
                    )

            _insert_ordered(connection, "decisions", next_decision, decision)
            next_decision += 1
            next_processed += 1
            last_key = order_key

            if next_processed % checkpoint_cadence == 0:
                _put_metadata(connection, "last_stream_order_key", list(last_key))
                _put_metadata(connection, "processed_count", next_processed)
                connection.commit()
                if (
                    storage_limit_bytes is not None
                    and database_path.stat().st_size > storage_limit_bytes
                ):
                    raise RS0SpooledRuntimeError(
                        "RS0_SPOOLED_STORAGE_LIMIT_EXCEEDED:"
                        f"{database_path.stat().st_size}>{storage_limit_bytes}"
                    )

        _put_metadata(
            connection,
            "last_stream_order_key",
            list(last_key) if last_key is not None else None,
        )
        _put_metadata(connection, "processed_count", next_processed)
        connection.commit()

        counts = {
            "processed_source_record_ids": next_processed,
            "candidates": next_candidate,
            "tracklets": connection.execute(
                "SELECT COUNT(*) FROM tracklets"
            ).fetchone()[0],
            "object_assertions": connection.execute(
                "SELECT COUNT(*) FROM assertions"
            ).fetchone()[0],
            "match_decisions": next_decision,
            "evidence_vectors": next_vector,
        }
        stream_hashes: dict[str, str] = {}
        stream_specs = (
            ("candidates", "candidates"),
            ("tracklets", "tracklets"),
            ("object_assertions", "assertions"),
            ("match_decisions", "decisions"),
            ("evidence_vectors", "evidence_vectors"),
        )
        for public_name, table in stream_specs:
            digest = sha256()
            output_path = root / f"{public_name}.ndjson"
            handle = output_path.open("wb") if export_streams else None
            try:
                for value in _ordered_values(connection, table):
                    encoded = (_canonical_json(value) + "\n").encode("utf-8")
                    digest.update(encoded)
                    if handle is not None:
                        handle.write(encoded)
            finally:
                if handle is not None:
                    handle.close()
            stream_hashes[public_name] = digest.hexdigest()

        processed_digest = sha256()
        processed_path = root / "processed_source_record_ids.ndjson"
        processed_handle = processed_path.open("wb") if export_streams else None
        try:
            for (source_id,) in connection.execute(
                "SELECT source_id FROM processed_source_ids ORDER BY ordinal"
            ):
                encoded = (_canonical_json(source_id) + "\n").encode("utf-8")
                processed_digest.update(encoded)
                if processed_handle is not None:
                    processed_handle.write(encoded)
        finally:
            if processed_handle is not None:
                processed_handle.close()
        stream_hashes["processed_source_record_ids"] = processed_digest.hexdigest()

        indexes = _final_indexes(connection)
        manifest_body = {
            "schema": ADAPTER_SCHEMA,
            "adapter_id": ADAPTER_ID,
            "runtime_schema": RUNTIME_SCHEMA,
            "runtime_binding_id": RUNTIME_BINDING_ID,
            "object_pack_candidate_id": candidate_spec["candidate_id"],
            "semantic_candidate_id": candidate_spec["semantic_candidate_id"],
            "selection_state": "UNSELECTED_RESEARCH_CANDIDATE",
            "activation_state": "NONE",
            "real_source_launch": "NOT_AUTHORISED_BY_RUNTIME",
            "processed_count": next_processed,
            "last_stream_order_key": list(last_key) if last_key else None,
            "counts": counts,
            "stream_sha256": stream_hashes,
            "indexes_sha256": _hash(indexes),
            "checkpoint_cadence": checkpoint_cadence,
            "database_file": database_path.name,
            "database_bytes": database_path.stat().st_size,
            "storage_limit_bytes": storage_limit_bytes,
            "scientific_effect": "NONE_FROM_ADAPTER",
        }
        manifest = {
            **manifest_body,
            "adapter_result_sha256": _hash(manifest_body),
        }
        (root / "manifest.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return manifest
    finally:
        connection.close()


def materialize_reference_result(work_dir: str | Path) -> dict[str, Any]:
    """Materialise the exact v0.1 result shape for bounded equivalence tests only."""

    root = Path(work_dir)
    connection = sqlite3.connect(root / "runtime-spool.sqlite3")
    try:
        candidate_spec = _get_metadata(connection, "candidate_spec")
        payload = {
            "schema": RUNTIME_SCHEMA,
            "runtime_binding_id": RUNTIME_BINDING_ID,
            "object_pack_candidate_id": candidate_spec["candidate_id"],
            "semantic_candidate_id": candidate_spec["semantic_candidate_id"],
            "selection_state": "UNSELECTED_RESEARCH_CANDIDATE",
            "activation_state": "NONE",
            "real_source_launch": "NOT_AUTHORISED_BY_RUNTIME",
            "processed_source_record_ids": [
                row[0]
                for row in connection.execute(
                    "SELECT source_id FROM processed_source_ids ORDER BY ordinal"
                )
            ],
            "last_stream_order_key": _get_metadata(
                connection, "last_stream_order_key"
            ),
            "candidates": list(_ordered_values(connection, "candidates")),
            "tracklets": list(_ordered_values(connection, "tracklets")),
            "object_assertions": list(_ordered_values(connection, "assertions")),
            "match_decisions": list(_ordered_values(connection, "decisions")),
            "evidence_vectors": list(
                _ordered_values(connection, "evidence_vectors")
            ),
            "indexes": _final_indexes(connection),
        }
        payload["checkpoint_sha256"] = _hash(payload)
        return payload
    finally:
        connection.close()
