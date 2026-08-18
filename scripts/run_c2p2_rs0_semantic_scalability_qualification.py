#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import resource
import shutil
import sqlite3
import time
from typing import Any, Iterable

from ovc.opt_b.c2p_v0_2.rs0_empirical_runtime_indexed import run_indexed_empirical_runtime


PROGRAMME_ID = "OVC-C2P2-RS0-SHADOW-EVIDENCE-v0.1"
PACKET_ID = "C2P2-RS0-RUN-RECOVERY-R4"
AUTHORITY_ID = "AUTH.C2P2.RS0.RUN_RECOVERY.R4.v0.1"

FROZEN_EXECUTION_STORAGE_LIMIT = 6_411_935_744
FROZEN_PEAK_MEMORY_LIMIT = 1_160_593_408
R4_PARTIAL_DATABASE_BYTES = 6_415_310_848
PRIOR_QUALIFICATION_DATABASE_BYTES = 5_966_430_208
DIAGNOSTIC_STORAGE_LIMIT = 20 * 1024**3
CHECKPOINT_CADENCE = 4096
SAFETY_FACTOR = 1.25
ROUNDING_QUANTUM = 1024**3

SCOPE_COUNTS = (
    ("ASK", "C2_LEVEL", 558_429),
    ("ASK", "C2_CONTAINER", 186_143),
    ("BID", "C2_LEVEL", 558_429),
    ("BID", "C2_CONTAINER", 186_143),
)
BASE_CARDINALITY = sum(count for _, _, count in SCOPE_COUNTS)

CANDIDATES = (
    {
        "candidate_id": "C2P2-PS0-OP-A-STRICT-CONTINUITY-v3",
        "semantic_candidate_id": "C2P2-PS0-OP-A-STRICT-CONTINUITY-v2",
        "activation_eligible": False,
    },
    {
        "candidate_id": "C2P2-PS0-OP-B-RELATIONAL-CONTINUITY-v3",
        "semantic_candidate_id": "C2P2-PS0-OP-B-RELATIONAL-CONTINUITY-v2",
        "activation_eligible": False,
    },
    {
        "candidate_id": "C2P2-PS0-OP-C-EPISODE-ENRICHED-CONTINUITY-v3",
        "semantic_candidate_id": "C2P2-PS0-OP-C-EPISODE-ENRICHED-CONTINUITY-v2",
        "activation_eligible": False,
    },
)
DEPENDENCIES = {"entries": []}

WIDE_ORIGIN = "SYNTHETIC_R4_CAPACITY_RECOVERY_" + ("X" * 512)
RELATION_TOPOLOGY = [
    "REL_SYNTHETIC_R4_CAPACITY_RECOVERY_PRIMARY",
    "REL_SYNTHETIC_R4_CAPACITY_RECOVERY_SECONDARY",
    "REL_SYNTHETIC_R4_CAPACITY_RECOVERY_TERTIARY",
    "REL_SYNTHETIC_R4_CAPACITY_RECOVERY_QUATERNARY",
]
TIMESTAMP = "2024-01-01T00:00:00Z"


def _level_row(ordinal: int, side: str) -> dict[str, Any]:
    return {
        "schema": "ovc-c2p2-rs0-source-row/v1",
        "source_role": "C2_VNEXT",
        "source_record_id": f"R4REC-L-{side}-{ordinal:010d}",
        "source_record_kind": "C2_LEVEL",
        "instrument": "GBPUSD",
        "side": side,
        "clock": "15M",
        "first_valid_time": TIMESTAMP,
        "evaluation_cutoff": TIMESTAMP,
        "geometry_signature": {
            "horizon_id": "H15",
            "level_type": "SWING_HIGH" if side == "ASK" else "SWING_LOW",
            "value": f"{ordinal:010d}.00001",
            "origin": WIDE_ORIGIN,
            "structural_depth": 3,
        },
        "relation_topology": RELATION_TOPOLOGY,
    }


def _container_row(ordinal: int, side: str) -> dict[str, Any]:
    return {
        "schema": "ovc-c2p2-rs0-source-row/v1",
        "source_role": "C2_VNEXT",
        "source_record_id": f"R4REC-C-{side}-{ordinal:010d}",
        "source_record_kind": "C2_CONTAINER",
        "instrument": "GBPUSD",
        "side": side,
        "clock": "15M",
        "first_valid_time": TIMESTAMP,
        "evaluation_cutoff": TIMESTAMP,
        "geometry_signature": {
            "horizon_id": "H15",
            "kind": "BALANCE_RANGE",
            "lower_value": f"{ordinal:010d}.00000",
            "upper_value": f"{ordinal:010d}.90000",
            "centre": f"{ordinal:010d}.45000",
            "width": "0.90000",
            "origin": WIDE_ORIGIN,
            "structural_depth": 3,
        },
        "relation_topology": RELATION_TOPOLOGY,
    }


def rows() -> Iterable[dict[str, Any]]:
    ordinal = 0
    for side, source_kind, count in SCOPE_COUNTS:
        factory = _level_row if source_kind == "C2_LEVEL" else _container_row
        for _ in range(count):
            yield factory(ordinal, side)
            ordinal += 1
    if ordinal != BASE_CARDINALITY:
        raise RuntimeError(f"R4_RECOVERY_SYNTHETIC_CARDINALITY_DRIFT:{ordinal}!={BASE_CARDINALITY}")


def peak_rss_bytes() -> int:
    return int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss) * 1024


def sqlite_telemetry(database_path: Path) -> dict[str, Any]:
    connection = sqlite3.connect(database_path)
    try:
        table_counts = {}
        for table in (
            "processed_source_ids",
            "candidates",
            "tracklets",
            "assertions",
            "decisions",
            "evaluated_pair_vectors",
            "negative_coverage",
        ):
            table_counts[table] = int(connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
        page_size = int(connection.execute("PRAGMA page_size").fetchone()[0])
        page_count = int(connection.execute("PRAGMA page_count").fetchone()[0])
        freelist_count = int(connection.execute("PRAGMA freelist_count").fetchone()[0])
        allocation = {}
        dbstat_status = "AVAILABLE"
        try:
            for name, pgsize in connection.execute(
                "SELECT name, SUM(pgsize) FROM dbstat GROUP BY name ORDER BY name"
            ):
                allocation[str(name)] = int(pgsize)
        except sqlite3.OperationalError:
            dbstat_status = "UNAVAILABLE_ON_RUNNER"
        return {
            "table_counts": table_counts,
            "page_size": page_size,
            "page_count": page_count,
            "freelist_count": freelist_count,
            "page_allocated_bytes": page_size * page_count,
            "dbstat_status": dbstat_status,
            "dbstat_allocated_bytes_by_object": allocation,
        }
    finally:
        connection.close()


def run_case(root: Path, candidate: dict[str, Any], diagnostic_storage_limit: int) -> dict[str, Any]:
    candidate_id = str(candidate["candidate_id"])
    work = root / candidate_id
    if work.exists():
        shutil.rmtree(work)
    before_rss = peak_rss_bytes()
    started = time.perf_counter()
    manifest = run_indexed_empirical_runtime(
        rows(),
        candidate,
        DEPENDENCIES,
        work_dir=work,
        checkpoint_cadence=CHECKPOINT_CADENCE,
        storage_limit_bytes=diagnostic_storage_limit,
    )
    elapsed = time.perf_counter() - started
    after_rss = peak_rss_bytes()
    database_path = work / manifest["database_file"]
    database_bytes = database_path.stat().st_size
    telemetry = sqlite_telemetry(database_path)
    measurement = {
        "candidate_id": candidate_id,
        "semantic_candidate_id": candidate["semantic_candidate_id"],
        "status": "PASS",
        "source_mode": "SYNTHETIC_ONLY_NONEMPIRICAL",
        "rows": BASE_CARDINALITY,
        "elapsed_seconds": elapsed,
        "rows_per_second": BASE_CARDINALITY / elapsed if elapsed else None,
        "peak_rss_bytes": after_rss,
        "peak_rss_delta_from_case_start_bytes": max(0, after_rss - before_rss),
        "database_bytes": database_bytes,
        "bytes_per_source_record": database_bytes / BASE_CARDINALITY,
        "manifest_counts": manifest["counts"],
        "sqlite": telemetry,
        "diagnostic_storage_limit_bytes": diagnostic_storage_limit,
        "frozen_execution_storage_limit_bytes": FROZEN_EXECUTION_STORAGE_LIMIT,
    }
    shutil.rmtree(work)
    return measurement


def round_up(value: int, quantum: int = ROUNDING_QUANTUM) -> int:
    if value < 0 or quantum <= 0:
        raise ValueError("R4_RECOVERY_ROUNDING_INPUT_INVALID")
    return ((value + quantum - 1) // quantum) * quantum


def proposed_storage_ceiling(max_measured_database_bytes: int) -> int:
    high_water = max(int(max_measured_database_bytes), R4_PARTIAL_DATABASE_BYTES)
    required = math.ceil(high_water * SAFETY_FACTOR)
    return round_up(required)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--work-root", type=Path, required=True)
    parser.add_argument(
        "--diagnostic-storage-limit",
        type=int,
        default=DIAGNOSTIC_STORAGE_LIMIT,
    )
    args = parser.parse_args()

    if args.diagnostic_storage_limit <= FROZEN_EXECUTION_STORAGE_LIMIT:
        raise SystemExit("R4_RECOVERY_DIAGNOSTIC_LIMIT_MUST_EXCEED_FROZEN_EXECUTION_LIMIT")

    args.work_root.mkdir(parents=True, exist_ok=True)
    resource.setrlimit(
        resource.RLIMIT_AS,
        (FROZEN_PEAK_MEMORY_LIMIT, FROZEN_PEAK_MEMORY_LIMIT),
    )

    measurements = []
    for candidate in CANDIDATES:
        measurements.append(run_case(args.work_root, candidate, args.diagnostic_storage_limit))

    max_database_bytes = max(row["database_bytes"] for row in measurements)
    max_peak_rss_bytes = max(row["peak_rss_bytes"] for row in measurements)
    proposed_ceiling = proposed_storage_ceiling(max_database_bytes)

    checks = {
        "all_three_candidates_completed": len(measurements) == 3
        and all(row["status"] == "PASS" for row in measurements),
        "all_cases_exact_frozen_base_cardinality": all(
            row["rows"] == BASE_CARDINALITY for row in measurements
        ),
        "synthetic_high_water_bounds_r4_observed_partial_database": (
            max_database_bytes >= R4_PARTIAL_DATABASE_BYTES
        ),
        "all_cases_inside_diagnostic_measurement_ceiling": all(
            row["database_bytes"] <= args.diagnostic_storage_limit for row in measurements
        ),
        "all_cases_inside_frozen_memory_ceiling": max_peak_rss_bytes <= FROZEN_PEAK_MEMORY_LIMIT,
        "proposed_ceiling_has_at_least_25pct_measured_margin": (
            proposed_ceiling >= math.ceil(max_database_bytes * SAFETY_FACTOR)
        ),
        "proposed_ceiling_has_at_least_25pct_r4_observed_margin": (
            proposed_ceiling >= math.ceil(R4_PARTIAL_DATABASE_BYTES * SAFETY_FACTOR)
        ),
        "frozen_execution_storage_ceiling_not_enacted": (
            FROZEN_EXECUTION_STORAGE_LIMIT == 6_411_935_744
        ),
    }
    status = "PASS" if all(checks.values()) else "FAIL"

    payload = {
        "schema": "ovc-c2p2-rs0-r4-capacity-recovery-qualification/v1",
        "programme_id": PROGRAMME_ID,
        "packet_id": PACKET_ID,
        "authority_id": AUTHORITY_ID,
        "authority_effect": "NONE_SYNTHETIC_NON_EVIDENTIARY_QUALIFICATION_ONLY",
        "real_source_read": False,
        "real_source_execution": False,
        "fresh_run_token": "NONE",
        "selection": "NONE",
        "activation": "NONE",
        "validation": "LOCKED_UNCONSUMED",
        "source_change": "NONE",
        "candidate_generation_change": "NONE",
        "scientific_semantics_change": "NONE",
        "predicate_or_threshold_change": "NONE",
        "sampling": "FORBIDDEN",
        "reduced_precision": "FORBIDDEN",
        "frozen_execution_storage_limit_bytes": FROZEN_EXECUTION_STORAGE_LIMIT,
        "frozen_execution_peak_memory_limit_bytes": FROZEN_PEAK_MEMORY_LIMIT,
        "storage_ceiling_change": "PROPOSED_ONLY_OPERATOR_REQUIRED_NOT_ENACTED",
        "diagnostic_storage_limit_bytes": args.diagnostic_storage_limit,
        "base_candidate_cardinality": BASE_CARDINALITY,
        "scope_counts": {
            f"{side}|{source_kind}": count for side, source_kind, count in SCOPE_COUNTS
        },
        "fixture": {
            "wide_origin_padding_characters": 512,
            "relation_topology_width": len(RELATION_TOPOLOGY),
            "candidate_a": "UNIQUE_EXACT_GEOMETRY_WITH_WIDE_PAYLOAD",
            "candidate_b": "CONCENTRATED_OWNER_CLASS_AND_TOPOLOGY_WITH_UNIQUE_NUMERIC_GEOMETRY",
            "candidate_c": "CONCENTRATED_OWNER_CLASS_WITH_UNIQUE_NUMERIC_GEOMETRY",
        },
        "r4_observed": {
            "partial_database_bytes": R4_PARTIAL_DATABASE_BYTES,
            "frozen_storage_limit_bytes": FROZEN_EXECUTION_STORAGE_LIMIT,
            "over_limit_bytes": R4_PARTIAL_DATABASE_BYTES - FROZEN_EXECUTION_STORAGE_LIMIT,
            "prior_qualification_database_bytes": PRIOR_QUALIFICATION_DATABASE_BYTES,
        },
        "measurements": measurements,
        "max_measured_database_bytes": max_database_bytes,
        "max_measured_peak_rss_bytes": max_peak_rss_bytes,
        "safety_factor": SAFETY_FACTOR,
        "rounding_quantum_bytes": ROUNDING_QUANTUM,
        "proposed_execution_storage_limit_bytes": proposed_ceiling,
        "proposed_execution_storage_limit_status": "OPERATOR_REQUIRED_NOT_ENACTED",
        "checks": checks,
        "status": status,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
