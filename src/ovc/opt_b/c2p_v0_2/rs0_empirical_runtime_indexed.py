from __future__ import annotations

"""Indexed outcome-equivalent C2P2-RS0 research sidecar.

This generation preserves frozen Candidate/Tracklet/ObjectAssertion lifecycle and
terminal-match semantics while replacing exhaustive impossible-competitor evidence
with one replay-verifiable negative-coverage certificate per candidate observation.
It is synthetic-qualification only and grants no real-source, selection, activation,
Validation, publication, probability, risk, exposure, trading, execution or agent-write authority.
"""

import json
from pathlib import Path
import sqlite3
from typing import Any, Iterable, Iterator, Mapping

from .rs0_empirical_runtime import (
    RUNTIME_BINDING_ID,
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


RUNTIME_GENERATION_ID = "C2P2_RS0_INDEXED_OUTCOME_EQUIVALENT_RUNTIME_v0_2"
EVIDENCE_CONTRACT_ID = "C2P2_RS0_NEGATIVE_COVERAGE_CERTIFICATE_v0_2"
ADAPTER_SCHEMA = "ovc-c2p2-rs0-indexed-outcome-equivalent-runtime/v2"
NEGATIVE_COVERAGE_STORAGE_SCHEMA = "COMPACT_TYPED_V1"
DEFAULT_CHECKPOINT_CADENCE = 1024

THEOREM_BY_SEMANTIC_ID = {
    "C2P2-PS0-OP-A-STRICT-CONTINUITY-v2": "A_EXACT_GEOMETRY_IS_NECESSARY",
    "C2P2-PS0-OP-B-RELATIONAL-CONTINUITY-v2": "B_OWNER_CLASS_AND_TOPOLOGY_ARE_NECESSARY",
    "C2P2-PS0-OP-C-EPISODE-ENRICHED-CONTINUITY-v2": "C_OWNER_CLASS_IS_NECESSARY_WITH_FROZEN_EMPTY_C2E_DEPENDENCY",
}


class RS0IndexedRuntimeError(RS0EmpiricalRuntimeError):
    pass


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":"))


def _validate_spec(candidate_spec: Mapping[str, Any], dependency_registry: Mapping[str, Any]) -> str:
    required = {"candidate_id", "semantic_candidate_id", "activation_eligible"}
    if not required.issubset(candidate_spec):
        raise RS0IndexedRuntimeError("RS0_INDEXED_CANDIDATE_SPEC_INCOMPLETE")
    if candidate_spec.get("activation_eligible") is not False:
        raise RS0IndexedRuntimeError("RS0_INDEXED_ACTIVATION_FORBIDDEN")
    semantic_id = str(candidate_spec["semantic_candidate_id"])
    if semantic_id not in THEOREM_BY_SEMANTIC_ID:
        raise RS0IndexedRuntimeError("RS0_INDEXED_SEMANTIC_PROFILE_INVALID")
    if dependency_registry.get("entries") != []:
        raise RS0IndexedRuntimeError("RS0_INDEXED_REQUIRES_FROZEN_EMPTY_C2E_DEPENDENCY_REGISTRY")
    return semantic_id


def necessary_match_key(semantic_id: str, material: Mapping[str, Any]) -> str:
    if semantic_id == "C2P2-PS0-OP-A-STRICT-CONTINUITY-v2":
        payload = {"semantic_id": semantic_id, "geometry_signature": material["geometry_signature"]}
    elif semantic_id == "C2P2-PS0-OP-B-RELATIONAL-CONTINUITY-v2":
        payload = {
            "semantic_id": semantic_id,
            "source_record_kind": material["source_record_kind"],
            "owner_geometry_class": material["owner_geometry_class"],
            "relation_topology": material["relation_topology"],
        }
    elif semantic_id == "C2P2-PS0-OP-C-EPISODE-ENRICHED-CONTINUITY-v2":
        payload = {
            "semantic_id": semantic_id,
            "source_record_kind": material["source_record_kind"],
            "owner_geometry_class": material["owner_geometry_class"],
        }
    else:
        raise RS0IndexedRuntimeError("RS0_INDEXED_SEMANTIC_PROFILE_INVALID")
    return _hash({"schema": "ovc-c2p2-rs0-necessary-match-key/v2", **payload})


def _connect(path: Path, *, create: bool) -> sqlite3.Connection:
    connection = sqlite3.connect(path)
    connection.execute("PRAGMA journal_mode=DELETE")
    connection.execute("PRAGMA synchronous=NORMAL")
    connection.execute("PRAGMA temp_store=FILE")
    if create:
        connection.executescript(
            """
            CREATE TABLE metadata (key TEXT PRIMARY KEY, value_json TEXT NOT NULL);
            CREATE TABLE processed_source_ids (ordinal INTEGER PRIMARY KEY, source_id TEXT NOT NULL UNIQUE);
            CREATE TABLE candidates (ordinal INTEGER PRIMARY KEY, value_json TEXT NOT NULL);
            CREATE TABLE tracklets (
                tracklet_id TEXT PRIMARY KEY, ordinal INTEGER NOT NULL UNIQUE,
                scope_key TEXT NOT NULL, match_key TEXT NOT NULL, state TEXT NOT NULL,
                value_json TEXT NOT NULL
            );
            CREATE INDEX tracklets_scope_match_state_id ON tracklets(scope_key, match_key, state, tracklet_id);
            CREATE INDEX tracklets_scope_state_id_v2 ON tracklets(scope_key, state, tracklet_id);
            CREATE TABLE assertions (
                assertion_id TEXT PRIMARY KEY, ordinal INTEGER NOT NULL UNIQUE,
                scope_key TEXT NOT NULL, match_key TEXT NOT NULL, value_json TEXT NOT NULL
            );
            CREATE INDEX assertions_scope_match_id ON assertions(scope_key, match_key, assertion_id);
            CREATE TABLE decisions (ordinal INTEGER PRIMARY KEY, value_json TEXT NOT NULL);
            CREATE TABLE evaluated_pair_vectors (ordinal INTEGER PRIMARY KEY, value_json TEXT NOT NULL);
            CREATE TABLE negative_coverage (
                ordinal INTEGER PRIMARY KEY,
                match_key TEXT NOT NULL,
                assertion_total INTEGER NOT NULL,
                assertion_examined INTEGER NOT NULL,
                tracklet_total INTEGER,
                tracklet_examined INTEGER,
                global_blocker TEXT
            );
            """
        )
    return connection


def _put_metadata(connection: sqlite3.Connection, key: str, value: Any) -> None:
    connection.execute("INSERT OR REPLACE INTO metadata(key, value_json) VALUES (?, ?)", (key, _canonical_json(value)))


def _get_metadata(connection: sqlite3.Connection, key: str) -> Any:
    row = connection.execute("SELECT value_json FROM metadata WHERE key = ?", (key,)).fetchone()
    if row is None:
        raise RS0IndexedRuntimeError(f"RS0_INDEXED_METADATA_MISSING:{key}")
    return json.loads(row[0])


def _next_ordinal(connection: sqlite3.Connection, table: str) -> int:
    return int(connection.execute(f"SELECT COALESCE(MAX(ordinal), -1) + 1 FROM {table}").fetchone()[0])


def _insert_ordered(connection: sqlite3.Connection, table: str, ordinal: int, value: Mapping[str, Any]) -> None:
    connection.execute(f"INSERT INTO {table}(ordinal, value_json) VALUES (?, ?)", (ordinal, _canonical_json(dict(value))))


def _insert_coverage(
    connection: sqlite3.Connection,
    ordinal: int,
    *,
    match_key: str,
    assertion_total: int,
    assertion_examined: int,
    tracklet_total: int | None,
    tracklet_examined: int | None,
    global_blocker: str | None,
) -> None:
    connection.execute(
        """
        INSERT INTO negative_coverage(
            ordinal, match_key, assertion_total, assertion_examined,
            tracklet_total, tracklet_examined, global_blocker
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            ordinal,
            match_key,
            assertion_total,
            assertion_examined,
            tracklet_total,
            tracklet_examined,
            global_blocker,
        ),
    )


def _scope_counts(connection: sqlite3.Connection) -> tuple[dict[str, int], dict[str, int]]:
    assertions = {str(scope): int(count) for scope, count in connection.execute("SELECT scope_key, COUNT(*) FROM assertions GROUP BY scope_key")}
    open_tracklets = {str(scope): int(count) for scope, count in connection.execute("SELECT scope_key, COUNT(*) FROM tracklets WHERE state = 'OPEN' GROUP BY scope_key")}
    return assertions, open_tracklets


def _upsert_tracklet(connection: sqlite3.Connection, semantic_id: str, tracklet: Mapping[str, Any], *, next_ordinal: int, open_counts: dict[str, int]) -> int:
    tracklet_id = str(tracklet["tracklet_id"])
    scope = _scope_key(tracklet["hard_scope"])
    match_key = necessary_match_key(semantic_id, tracklet["latest_material"])
    existing = connection.execute("SELECT ordinal, state, scope_key FROM tracklets WHERE tracklet_id = ?", (tracklet_id,)).fetchone()
    new_state = str(tracklet["state"])
    if existing is None:
        ordinal = next_ordinal
        next_ordinal += 1
        connection.execute(
            "INSERT INTO tracklets(tracklet_id, ordinal, scope_key, match_key, state, value_json) VALUES (?, ?, ?, ?, ?, ?)",
            (tracklet_id, ordinal, scope, match_key, new_state, _canonical_json(dict(tracklet))),
        )
        if new_state == "OPEN":
            open_counts[scope] = open_counts.get(scope, 0) + 1
    else:
        _, old_state, old_scope = existing
        connection.execute(
            "UPDATE tracklets SET scope_key = ?, match_key = ?, state = ?, value_json = ? WHERE tracklet_id = ?",
            (scope, match_key, new_state, _canonical_json(dict(tracklet)), tracklet_id),
        )
        if old_state == "OPEN" and new_state != "OPEN":
            open_counts[str(old_scope)] = open_counts.get(str(old_scope), 0) - 1
        elif old_state != "OPEN" and new_state == "OPEN":
            open_counts[scope] = open_counts.get(scope, 0) + 1
    return next_ordinal


def _upsert_assertion(connection: sqlite3.Connection, semantic_id: str, assertion: Mapping[str, Any], *, next_ordinal: int, assertion_counts: dict[str, int]) -> int:
    assertion_id = str(assertion["object_assertion_id"])
    scope = _scope_key(assertion["hard_scope"])
    match_key = necessary_match_key(semantic_id, assertion["latest_material"])
    existing = connection.execute("SELECT ordinal FROM assertions WHERE assertion_id = ?", (assertion_id,)).fetchone()
    if existing is None:
        ordinal = next_ordinal
        next_ordinal += 1
        connection.execute(
            "INSERT INTO assertions(assertion_id, ordinal, scope_key, match_key, value_json) VALUES (?, ?, ?, ?, ?)",
            (assertion_id, ordinal, scope, match_key, _canonical_json(dict(assertion))),
        )
        assertion_counts[scope] = assertion_counts.get(scope, 0) + 1
    else:
        connection.execute(
            "UPDATE assertions SET scope_key = ?, match_key = ?, value_json = ? WHERE assertion_id = ?",
            (scope, match_key, _canonical_json(dict(assertion)), assertion_id),
        )
    return next_ordinal


def _ordered_values(connection: sqlite3.Connection, table: str) -> Iterator[dict[str, Any]]:
    for (value_json,) in connection.execute(f"SELECT value_json FROM {table} ORDER BY ordinal"):
        yield json.loads(value_json)


def _coverage_certificate(candidate: Mapping[str, Any], *, semantic_id: str, scope: str, match_key: str, assertion_total: int, assertion_examined: int, tracklet_total: int | None, tracklet_examined: int | None, global_blocker: str | None) -> dict[str, Any]:
    payload = {
        "schema": "ovc-c2p2-rs0-negative-coverage-certificate/v2",
        "evidence_contract_id": EVIDENCE_CONTRACT_ID,
        "runtime_generation_id": RUNTIME_GENERATION_ID,
        "object_pack_candidate_id": candidate["object_pack_candidate_id"],
        "candidate_id": candidate["candidate_id"],
        "semantic_candidate_id": semantic_id,
        "hard_scope_key": scope,
        "necessary_match_key": match_key,
        "necessary_predicate_theorem_id": THEOREM_BY_SEMANTIC_ID[semantic_id],
        "global_blocker": global_blocker,
        "assertions": {
            "scope_total": assertion_total,
            "examined": assertion_examined,
            "pruned_by_necessary_key_or_global_blocker": assertion_total - assertion_examined,
        },
        "open_tracklets": (
            {
                "scope_total": tracklet_total,
                "examined": tracklet_examined,
                "pruned_by_necessary_key_or_global_blocker": tracklet_total - tracklet_examined,
            }
            if tracklet_total is not None and tracklet_examined is not None
            else "NOT_REACHED_BY_REFERENCE_CONTROL_FLOW"
        ),
        "claim": "ALL_OMITTED_COMPETITORS_FAIL_A_FROZEN_NECESSARY_PREDICATE_OR_CURRENT_GLOBAL_BLOCKER",
        "audit_mode": "DETERMINISTIC_REPLAY_VERIFIABLE_NO_IMPOSSIBLE_PAIR_MATERIALISATION",
    }
    return {**payload, "coverage_certificate_sha256": _hash(payload)}


def _coverage_values(connection: sqlite3.Connection, semantic_id: str) -> Iterator[dict[str, Any]]:
    query = """
        SELECT
            c.value_json,
            n.match_key,
            n.assertion_total,
            n.assertion_examined,
            n.tracklet_total,
            n.tracklet_examined,
            n.global_blocker
        FROM negative_coverage AS n
        JOIN candidates AS c ON c.ordinal = n.ordinal
        ORDER BY n.ordinal
    """
    for (
        candidate_json,
        match_key,
        assertion_total,
        assertion_examined,
        tracklet_total,
        tracklet_examined,
        global_blocker,
    ) in connection.execute(query):
        candidate = json.loads(candidate_json)
        yield _coverage_certificate(
            candidate,
            semantic_id=semantic_id,
            scope=_scope_key(candidate["hard_scope"]),
            match_key=str(match_key),
            assertion_total=int(assertion_total),
            assertion_examined=int(assertion_examined),
            tracklet_total=(int(tracklet_total) if tracklet_total is not None else None),
            tracklet_examined=(int(tracklet_examined) if tracklet_examined is not None else None),
            global_blocker=(str(global_blocker) if global_blocker is not None else None),
        )


def _final_indexes(connection: sqlite3.Connection) -> dict[str, dict[str, list[str]]]:
    assertion_index: dict[str, list[str]] = {}
    for scope_key, assertion_id in connection.execute("SELECT scope_key, assertion_id FROM assertions ORDER BY scope_key, assertion_id"):
        assertion_index.setdefault(str(scope_key), []).append(str(assertion_id))
    tracklet_index: dict[str, list[str]] = {}
    for scope_key, tracklet_id in connection.execute("SELECT scope_key, tracklet_id FROM tracklets WHERE state = 'OPEN' ORDER BY scope_key, tracklet_id"):
        tracklet_index.setdefault(str(scope_key), []).append(str(tracklet_id))
    return {"assertion_ids_by_scope": assertion_index, "open_tracklet_ids_by_scope": tracklet_index}


def run_indexed_empirical_runtime(
    rows: Iterable[Mapping[str, Any]],
    candidate_spec: Mapping[str, Any],
    dependency_registry: Mapping[str, Any],
    *,
    work_dir: str | Path,
    explicit_discontinuity_source_ids: Iterable[str] = (),
    prior_terminal_break_source_ids: Iterable[str] = (),
    checkpoint_cadence: int = DEFAULT_CHECKPOINT_CADENCE,
    storage_limit_bytes: int | None = None,
    resume: bool = False,
) -> dict[str, Any]:
    semantic_id = _validate_spec(candidate_spec, dependency_registry)
    if checkpoint_cadence <= 0:
        raise RS0IndexedRuntimeError("RS0_INDEXED_CHECKPOINT_CADENCE_INVALID")

    root = Path(work_dir)
    root.mkdir(parents=True, exist_ok=True)
    database_path = root / "runtime-indexed.sqlite3"
    create = not database_path.exists()
    if not create and not resume:
        raise RS0IndexedRuntimeError("RS0_INDEXED_WORKDIR_NOT_EMPTY")

    connection = _connect(database_path, create=create)
    discontinuities = set(explicit_discontinuity_source_ids)
    terminal_breaks = set(prior_terminal_break_source_ids)

    if create:
        _put_metadata(connection, "candidate_spec", dict(candidate_spec))
        _put_metadata(connection, "runtime_binding_id", RUNTIME_BINDING_ID)
        _put_metadata(connection, "runtime_generation_id", RUNTIME_GENERATION_ID)
        _put_metadata(connection, "evidence_contract_id", EVIDENCE_CONTRACT_ID)
        _put_metadata(connection, "negative_coverage_storage_schema", NEGATIVE_COVERAGE_STORAGE_SCHEMA)
        _put_metadata(connection, "selection_state", "UNSELECTED_RESEARCH_CANDIDATE")
        _put_metadata(connection, "activation_state", "NONE")
        _put_metadata(connection, "real_source_launch", "FORBIDDEN_BY_AUTHORITY")
        _put_metadata(connection, "last_stream_order_key", None)
        _put_metadata(connection, "processed_count", 0)
        connection.commit()
    else:
        if _get_metadata(connection, "candidate_spec") != dict(candidate_spec):
            raise RS0IndexedRuntimeError("RS0_INDEXED_RESUME_CANDIDATE_SPEC_MISMATCH")
        if _get_metadata(connection, "runtime_generation_id") != RUNTIME_GENERATION_ID:
            raise RS0IndexedRuntimeError("RS0_INDEXED_RESUME_GENERATION_MISMATCH")
        if _get_metadata(connection, "evidence_contract_id") != EVIDENCE_CONTRACT_ID:
            raise RS0IndexedRuntimeError("RS0_INDEXED_RESUME_EVIDENCE_CONTRACT_MISMATCH")
        if _get_metadata(connection, "negative_coverage_storage_schema") != NEGATIVE_COVERAGE_STORAGE_SCHEMA:
            raise RS0IndexedRuntimeError("RS0_INDEXED_RESUME_COVERAGE_STORAGE_SCHEMA_MISMATCH")

    next_candidate = _next_ordinal(connection, "candidates")
    next_tracklet = _next_ordinal(connection, "tracklets")
    next_assertion = _next_ordinal(connection, "assertions")
    next_decision = _next_ordinal(connection, "decisions")
    next_vector = _next_ordinal(connection, "evaluated_pair_vectors")
    next_coverage = _next_ordinal(connection, "negative_coverage")
    next_processed = _next_ordinal(connection, "processed_source_ids")
    last_raw = _get_metadata(connection, "last_stream_order_key")
    last_key = tuple(last_raw) if last_raw is not None else None
    assertion_counts, open_counts = _scope_counts(connection)

    try:
        for raw_row in rows:
            material = normalize_candidate_source_row(raw_row)
            source_id = str(material["source_record_id"])
            order_key = (str(material["first_valid_time"]), source_id)
            if connection.execute("SELECT 1 FROM processed_source_ids WHERE source_id = ?", (source_id,)).fetchone() is not None:
                raise RS0IndexedRuntimeError(f"RS0_RUNTIME_DUPLICATE_SOURCE_RECORD:{source_id}")
            if last_key is not None and order_key <= last_key:
                raise RS0IndexedRuntimeError("RS0_RUNTIME_NONMONOTONIC_RESTART_STREAM")

            connection.execute("INSERT INTO processed_source_ids(ordinal, source_id) VALUES (?, ?)", (next_processed, source_id))
            candidate = _candidate_record(candidate_spec, material)
            _insert_ordered(connection, "candidates", next_candidate, candidate)
            next_candidate += 1

            scope = _scope_key(candidate["hard_scope"])
            match_key = necessary_match_key(semantic_id, material)
            is_discontinuity = source_id in discontinuities
            is_terminal_break = source_id in terminal_breaks
            global_blocker = (
                "RS0_EXPLICIT_SOURCE_DISCONTINUITY" if is_discontinuity
                else "RS0_PRIOR_TERMINAL_BREAK" if is_terminal_break
                else None
            )

            assertion_total = assertion_counts.get(scope, 0)
            assertion_rows = []
            if global_blocker is None:
                assertion_rows = list(connection.execute(
                    "SELECT assertion_id, value_json FROM assertions WHERE scope_key = ? AND match_key = ? ORDER BY assertion_id",
                    (scope, match_key),
                ))
            assertion_vector_ids: list[str] = []
            eligible_assertions: list[str] = []
            for assertion_id, value_json in assertion_rows:
                assertion = json.loads(value_json)
                pair = evaluate_pair(semantic_id, assertion["latest_material"], material, dependency_registry)
                vector = _evidence_vector(candidate, "OBJECT_ASSERTION", str(assertion_id), pair)
                _insert_ordered(connection, "evaluated_pair_vectors", next_vector, vector)
                next_vector += 1
                assertion_vector_ids.append(vector["evidence_vector_id"])
                if pair["same_object_pair_supported"]:
                    eligible_assertions.append(str(assertion_id))

            if len(eligible_assertions) > 1:
                decision = _decision(candidate, "AMBIGUOUS", eligible_assertion_ids=eligible_assertions, evidence_vector_ids=assertion_vector_ids)
                tracklet_total = None
                tracklet_examined = None
            elif len(eligible_assertions) == 1:
                assertion_id = eligible_assertions[0]
                value_json = connection.execute("SELECT value_json FROM assertions WHERE assertion_id = ?", (assertion_id,)).fetchone()[0]
                updated_assertion = _update_assertion(json.loads(value_json), candidate, material)
                next_assertion = _upsert_assertion(
                    connection, semantic_id, updated_assertion,
                    next_ordinal=next_assertion, assertion_counts=assertion_counts,
                )
                decision = _decision(candidate, "UPDATE", eligible_assertion_ids=[assertion_id], evidence_vector_ids=assertion_vector_ids, resulting_subject_id=assertion_id)
                tracklet_total = None
                tracklet_examined = None
            else:
                tracklet_total = open_counts.get(scope, 0)
                tracklet_rows = []
                if global_blocker is None:
                    tracklet_rows = list(connection.execute(
                        "SELECT tracklet_id, value_json FROM tracklets WHERE scope_key = ? AND match_key = ? AND state = 'OPEN' ORDER BY tracklet_id",
                        (scope, match_key),
                    ))
                tracklet_examined = len(tracklet_rows)
                tracklet_vector_ids: list[str] = []
                eligible_tracklets: list[str] = []
                for tracklet_id, value_json in tracklet_rows:
                    tracklet = json.loads(value_json)
                    pair = evaluate_pair(semantic_id, tracklet["latest_material"], material, dependency_registry)
                    vector = _evidence_vector(candidate, "TRACKLET", str(tracklet_id), pair)
                    _insert_ordered(connection, "evaluated_pair_vectors", next_vector, vector)
                    next_vector += 1
                    tracklet_vector_ids.append(vector["evidence_vector_id"])
                    if pair["same_object_pair_supported"]:
                        eligible_tracklets.append(str(tracklet_id))

                if global_blocker is not None:
                    censor_rows = list(connection.execute(
                        "SELECT tracklet_id, value_json FROM tracklets WHERE scope_key = ? AND state = 'OPEN' ORDER BY tracklet_id",
                        (scope,),
                    ))
                    for _, value_json in censor_rows:
                        tracklet = json.loads(value_json)
                        tracklet["state"] = "CENSORED"
                        tracklet["reason_codes"] = [global_blocker]
                        next_tracklet = _upsert_tracklet(
                            connection, semantic_id, tracklet,
                            next_ordinal=next_tracklet, open_counts=open_counts,
                        )
                    eligible_tracklets = []

                all_vector_ids = assertion_vector_ids + tracklet_vector_ids
                if len(eligible_tracklets) > 1:
                    for tracklet_id in eligible_tracklets:
                        value_json = connection.execute("SELECT value_json FROM tracklets WHERE tracklet_id = ?", (tracklet_id,)).fetchone()[0]
                        tracklet = json.loads(value_json)
                        tracklet["state"] = "AMBIGUOUS"
                        tracklet["reason_codes"] = ["RS0_EQUAL_LAWFUL_TRACKLET_COMPETITOR"]
                        next_tracklet = _upsert_tracklet(
                            connection, semantic_id, tracklet,
                            next_ordinal=next_tracklet, open_counts=open_counts,
                        )
                    decision = _decision(candidate, "AMBIGUOUS", eligible_tracklet_ids=eligible_tracklets, evidence_vector_ids=all_vector_ids)
                elif len(eligible_tracklets) == 1:
                    tracklet_id = eligible_tracklets[0]
                    value_json = connection.execute("SELECT value_json FROM tracklets WHERE tracklet_id = ?", (tracklet_id,)).fetchone()[0]
                    updated = _append_tracklet(json.loads(value_json), candidate, material)
                    next_tracklet = _upsert_tracklet(
                        connection, semantic_id, updated,
                        next_ordinal=next_tracklet, open_counts=open_counts,
                    )
                    if updated["state"] == "CONFIRMED":
                        assertion = _create_assertion(updated)
                        next_assertion = _upsert_assertion(
                            connection, semantic_id, assertion,
                            next_ordinal=next_assertion, assertion_counts=assertion_counts,
                        )
                        terminal = "GENESIS"
                        subject_id = assertion["object_assertion_id"]
                    else:
                        terminal = "TRACKLET_UPDATE"
                        subject_id = tracklet_id
                    decision = _decision(candidate, terminal, eligible_tracklet_ids=[tracklet_id], evidence_vector_ids=all_vector_ids, resulting_subject_id=subject_id)
                else:
                    tracklet = _open_tracklet(candidate, material)
                    next_tracklet = _upsert_tracklet(
                        connection, semantic_id, tracklet,
                        next_ordinal=next_tracklet, open_counts=open_counts,
                    )
                    decision = _decision(candidate, "NEW_TRACKLET", evidence_vector_ids=all_vector_ids, resulting_subject_id=tracklet["tracklet_id"])

            _insert_coverage(
                connection,
                next_coverage,
                match_key=match_key,
                assertion_total=assertion_total,
                assertion_examined=len(assertion_rows),
                tracklet_total=tracklet_total,
                tracklet_examined=tracklet_examined,
                global_blocker=global_blocker,
            )
            next_coverage += 1
            _insert_ordered(connection, "decisions", next_decision, decision)
            next_decision += 1

            next_processed += 1
            last_key = order_key
            if next_processed % checkpoint_cadence == 0:
                _put_metadata(connection, "last_stream_order_key", list(last_key))
                _put_metadata(connection, "processed_count", next_processed)
                connection.commit()
                if storage_limit_bytes is not None and database_path.stat().st_size > storage_limit_bytes:
                    raise RS0IndexedRuntimeError(
                        "RS0_INDEXED_STORAGE_LIMIT_EXCEEDED:"
                        f"{database_path.stat().st_size}>{storage_limit_bytes}"
                    )

        _put_metadata(connection, "last_stream_order_key", list(last_key) if last_key is not None else None)
        _put_metadata(connection, "processed_count", next_processed)
        connection.commit()

        counts = {
            "processed_source_record_ids": next_processed,
            "candidates": next_candidate,
            "tracklets": int(connection.execute("SELECT COUNT(*) FROM tracklets").fetchone()[0]),
            "object_assertions": int(connection.execute("SELECT COUNT(*) FROM assertions").fetchone()[0]),
            "match_decisions": next_decision,
            "evaluated_pair_vectors": next_vector,
            "negative_coverage_certificates": next_coverage,
        }
        manifest_body = {
            "schema": ADAPTER_SCHEMA,
            "runtime_generation_id": RUNTIME_GENERATION_ID,
            "evidence_contract_id": EVIDENCE_CONTRACT_ID,
            "negative_coverage_storage_schema": NEGATIVE_COVERAGE_STORAGE_SCHEMA,
            "legacy_runtime_binding_id": RUNTIME_BINDING_ID,
            "object_pack_candidate_id": candidate_spec["candidate_id"],
            "semantic_candidate_id": candidate_spec["semantic_candidate_id"],
            "selection_state": "UNSELECTED_RESEARCH_CANDIDATE",
            "activation_state": "NONE",
            "real_source_launch": "FORBIDDEN_BY_AUTHORITY",
            "processed_count": next_processed,
            "last_stream_order_key": list(last_key) if last_key else None,
            "counts": counts,
            "indexes_sha256": _hash(_final_indexes(connection)),
            "checkpoint_cadence": checkpoint_cadence,
            "database_file": database_path.name,
            "database_bytes": database_path.stat().st_size,
            "storage_limit_bytes": storage_limit_bytes,
            "scientific_effect": "NONE_SYNTHETIC_QUALIFICATION_SIDECAR_ONLY",
            "equivalence_target": "TERMINAL_AND_LIFECYCLE_EQUIVALENCE_WITH_VERSIONED_NEGATIVE_EVIDENCE_CONTRACT",
        }
        manifest = {**manifest_body, "adapter_result_sha256": _hash(manifest_body)}
        (root / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return manifest
    finally:
        connection.close()


def materialize_outcome_result(work_dir: str | Path) -> dict[str, Any]:
    root = Path(work_dir)
    connection = sqlite3.connect(root / "runtime-indexed.sqlite3")
    try:
        candidate_spec = _get_metadata(connection, "candidate_spec")
        semantic_id = str(candidate_spec["semantic_candidate_id"])
        if _get_metadata(connection, "negative_coverage_storage_schema") != NEGATIVE_COVERAGE_STORAGE_SCHEMA:
            raise RS0IndexedRuntimeError("RS0_INDEXED_COVERAGE_STORAGE_SCHEMA_MISMATCH")
        return {
            "schema": ADAPTER_SCHEMA,
            "runtime_generation_id": RUNTIME_GENERATION_ID,
            "evidence_contract_id": EVIDENCE_CONTRACT_ID,
            "legacy_runtime_binding_id": RUNTIME_BINDING_ID,
            "object_pack_candidate_id": candidate_spec["candidate_id"],
            "semantic_candidate_id": semantic_id,
            "processed_source_record_ids": [row[0] for row in connection.execute("SELECT source_id FROM processed_source_ids ORDER BY ordinal")],
            "last_stream_order_key": _get_metadata(connection, "last_stream_order_key"),
            "candidates": list(_ordered_values(connection, "candidates")),
            "tracklets": list(_ordered_values(connection, "tracklets")),
            "object_assertions": list(_ordered_values(connection, "assertions")),
            "match_decisions": list(_ordered_values(connection, "decisions")),
            "evaluated_pair_vectors": list(_ordered_values(connection, "evaluated_pair_vectors")),
            "negative_coverage_certificates": list(_coverage_values(connection, semantic_id)),
            "indexes": _final_indexes(connection),
            "selection_state": "UNSELECTED_RESEARCH_CANDIDATE",
            "activation_state": "NONE",
            "real_source_launch": "FORBIDDEN_BY_AUTHORITY",
        }
    finally:
        connection.close()
