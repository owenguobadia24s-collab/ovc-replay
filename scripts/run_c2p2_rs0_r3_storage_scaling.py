from __future__ import annotations

"""Bounded non-evidentiary storage-scaling harness for C2P2-RS0 R3 recovery.

This harness never reads the real-source population and never creates run authority.
It exercises the already-frozen Candidate A runtime on synthetic rows whose exact
geometries are all distinct inside one hard scope. Under the frozen exhaustive
competitor comparison semantics, the expected evidence-vector count is N*(N-1)/2.
"""

import argparse
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sqlite3
from typing import Any

from ovc.opt_b.c2p_v0_2.rs0_empirical_runtime_streaming import run_spooled_empirical_runtime


SCHEMA = "ovc-c2p2-rs0-r3-storage-scaling-measurement/v1"
CANDIDATE_SPEC = {
    "candidate_id": "C2P2-PS0-OP-A-STRICT-CONTINUITY-v3",
    "semantic_candidate_id": "C2P2-PS0-OP-A-STRICT-CONTINUITY-v2",
    "activation_eligible": False,
}
DEPENDENCY_REGISTRY = {
    "schema": "ovc-c2p2-rs0-c2e-dependency-role-registry/v1",
    "entries": [],
    "current_declared_episode_relative_roles": [],
}
TABLES = (
    "processed_source_ids",
    "candidates",
    "tracklets",
    "assertions",
    "decisions",
    "evidence_vectors",
)


def _synthetic_unique_level_rows(count: int) -> list[dict[str, Any]]:
    if count <= 0:
        raise ValueError("count must be positive")
    start = datetime(2021, 1, 1, tzinfo=timezone.utc)
    rows: list[dict[str, Any]] = []
    for index in range(count):
        stamp = (start + timedelta(minutes=15 * index)).isoformat().replace("+00:00", "Z")
        rows.append(
            {
                "schema": "ovc-c2p2-rs0-source-row/v1",
                "source_role": "C2_VNEXT",
                "instrument": "GBPUSD",
                "side": "BID",
                "clock": "15M",
                "first_valid_time": stamp,
                "evaluation_cutoff": stamp,
                "source_record_id": f"SYN-R3-SCALE-{index:08d}",
                "source_record_kind": "C2_LEVEL",
                "geometry_signature": {
                    "horizon_id": "H4",
                    "level_type": "RANGE_HIGH",
                    "value": f"1.{index:08d}",
                    "origin": "C2AR",
                    "structural_depth": None,
                },
                "relation_topology": [],
            }
        )
    return rows


def _sqlite_telemetry(database_path: Path) -> dict[str, Any]:
    connection = sqlite3.connect(database_path)
    try:
        counts = {
            table: connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for table in TABLES
        }
        page_size = connection.execute("PRAGMA page_size").fetchone()[0]
        page_count = connection.execute("PRAGMA page_count").fetchone()[0]
        freelist_count = connection.execute("PRAGMA freelist_count").fetchone()[0]
        evidence_width = connection.execute(
            "SELECT MIN(length(value_json)), AVG(length(value_json)), MAX(length(value_json)) "
            "FROM evidence_vectors"
        ).fetchone()
        decision_width = connection.execute(
            "SELECT MIN(length(value_json)), AVG(length(value_json)), MAX(length(value_json)) "
            "FROM decisions"
        ).fetchone()
        try:
            dbstat_rows = connection.execute(
                "SELECT name, SUM(pgsize) FROM dbstat GROUP BY name ORDER BY name"
            ).fetchall()
            allocation = {str(name): int(size) for name, size in dbstat_rows}
            dbstat_status = "AVAILABLE"
        except sqlite3.DatabaseError:
            allocation = {}
            dbstat_status = "UNAVAILABLE"
        return {
            "table_row_counts": counts,
            "page_size": page_size,
            "page_count": page_count,
            "freelist_count": freelist_count,
            "allocated_page_bytes": page_size * page_count,
            "dbstat_status": dbstat_status,
            "dbstat_bytes_by_object": allocation,
            "evidence_vector_json_bytes": {
                "min": evidence_width[0],
                "avg": evidence_width[1],
                "max": evidence_width[2],
            },
            "decision_json_bytes": {
                "min": decision_width[0],
                "avg": decision_width[1],
                "max": decision_width[2],
            },
        }
    finally:
        connection.close()


def run_scaling_point(count: int, work_dir: Path) -> dict[str, Any]:
    expected_vectors = count * (count - 1) // 2
    manifest = run_spooled_empirical_runtime(
        _synthetic_unique_level_rows(count),
        CANDIDATE_SPEC,
        DEPENDENCY_REGISTRY,
        work_dir=work_dir,
        checkpoint_cadence=max(1, min(16, count)),
        export_streams=False,
        storage_limit_bytes=None,
    )
    database_path = work_dir / "runtime-spool.sqlite3"
    telemetry = _sqlite_telemetry(database_path)
    observed_vectors = telemetry["table_row_counts"]["evidence_vectors"]
    if observed_vectors != expected_vectors:
        raise AssertionError(
            f"evidence-vector scaling mismatch: observed={observed_vectors} expected={expected_vectors}"
        )
    if telemetry["table_row_counts"]["tracklets"] != count:
        raise AssertionError("all-unique strict-continuity fixture must leave one tracklet per row")
    if telemetry["table_row_counts"]["assertions"] != 0:
        raise AssertionError("all-unique strict-continuity fixture must create no assertions")
    return {
        "rows": count,
        "expected_evidence_vectors": expected_vectors,
        "observed_evidence_vectors": observed_vectors,
        "evidence_vector_formula_status": "PASS",
        "runtime_spool_database_bytes": database_path.stat().st_size,
        "manifest_counts": manifest["counts"],
        "telemetry": telemetry,
    }


def run_measurement(output_path: Path, work_root: Path, points: list[int]) -> dict[str, Any]:
    if not points or any(point <= 0 for point in points):
        raise ValueError("all scaling points must be positive")
    measurements = []
    for point in points:
        work_dir = work_root / f"n-{point}"
        if work_dir.exists():
            raise RuntimeError(f"work directory already exists: {work_dir}")
        measurements.append(run_scaling_point(point, work_dir))
    payload = {
        "schema": SCHEMA,
        "packet_id": "C2P2-RS0-RUN-RECOVERY-R3",
        "authority_effect": "NONE_SYNTHETIC_NON_EVIDENTIARY_MECHANICAL_ONLY",
        "real_source_read": False,
        "semantic_runtime": "FROZEN_CANDIDATE_A_ON_SYNTHETIC_ROWS_ONLY",
        "candidate_id": CANDIDATE_SPEC["candidate_id"],
        "semantic_candidate_id": CANDIDATE_SPEC["semantic_candidate_id"],
        "fixture": "ONE_HARD_SCOPE_ALL_UNIQUE_EXACT_GEOMETRIES",
        "expected_scaling": "N*(N-1)/2 evidence vectors",
        "points": points,
        "measurements": measurements,
        "selection": "NONE",
        "activation": "NONE",
        "validation": "LOCKED_UNCONSUMED",
        "fresh_run_token": "NONE",
        "real_source_execution_authority": "NONE",
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--work-root", type=Path, required=True)
    parser.add_argument("--points", nargs="+", type=int, default=[32, 64, 128, 256])
    args = parser.parse_args()
    payload = run_measurement(args.output, args.work_root, args.points)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
