#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import resource
import shutil
import time

from ovc.opt_b.c2p_v0_2.rs0_empirical_runtime_streaming import (
    ADAPTER_ID,
    run_spooled_empirical_runtime,
)


REGISTRY = {
    "schema": "ovc-c2p2-rs0-c2e-dependency-role-registry/v1",
    "entries": [],
    "current_declared_episode_relative_roles": [],
}
CANDIDATE_A = {
    "candidate_id": "C2P2-PS0-OP-A-STRICT-CONTINUITY-v3",
    "semantic_candidate_id": "C2P2-PS0-OP-A-STRICT-CONTINUITY-v2",
    "activation_eligible": False,
}
DEFAULT_ROWS = 1_505_072
DEFAULT_MEMORY_LIMIT = 1_160_593_408
DEFAULT_STORAGE_LIMIT = 6_411_935_744


def synthetic_rows(count: int):
    base = datetime(2021, 1, 1, tzinfo=timezone.utc)
    for index in range(count):
        timestamp = base + timedelta(minutes=15 * index)
        iso = timestamp.isoformat(timespec="seconds").replace("+00:00", "Z")
        yield {
            "schema": "ovc-c2p2-rs0-source-row/v1",
            "source_role": "C2_VNEXT",
            "instrument": "GBPUSD",
            "side": "BID",
            "clock": "15M",
            "first_valid_time": iso,
            "evaluation_cutoff": iso,
            "source_record_id": f"RS0CAP{index:08d}",
            "source_record_kind": "C2_LEVEL",
            "geometry_signature": {
                "horizon_id": "H4",
                "level_type": "RANGE_HIGH",
                "value": "1.25000",
                "origin": "C2AR_SYNTH_CAPACITY_RECOVERY",
                "structural_depth": None,
            },
            "relation_topology": ["ABOVE"],
        }


def peak_rss_bytes() -> int:
    return int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss) * 1024


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rows", type=int, default=DEFAULT_ROWS)
    parser.add_argument("--memory-limit", type=int, default=DEFAULT_MEMORY_LIMIT)
    parser.add_argument("--storage-limit", type=int, default=DEFAULT_STORAGE_LIMIT)
    parser.add_argument("--work-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    if args.rows <= 0:
        raise SystemExit("rows must be positive")
    args.work_dir.mkdir(parents=True, exist_ok=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)

    resource.setrlimit(resource.RLIMIT_AS, (args.memory_limit, args.memory_limit))
    started = time.perf_counter()
    manifest = run_spooled_empirical_runtime(
        synthetic_rows(args.rows),
        CANDIDATE_A,
        REGISTRY,
        work_dir=args.work_dir,
        checkpoint_cadence=256,
        export_streams=False,
        storage_limit_bytes=args.storage_limit,
    )
    wall_seconds = time.perf_counter() - started
    peak = peak_rss_bytes()
    database_bytes = int(manifest["database_bytes"])
    disk = shutil.disk_usage(args.work_dir)

    status = "PASS" if (
        manifest["processed_count"] == args.rows
        and manifest["counts"]["candidates"] == args.rows
        and manifest["counts"]["match_decisions"] == args.rows
        and peak <= args.memory_limit
        and database_bytes <= args.storage_limit
        and manifest["selection_state"] == "UNSELECTED_RESEARCH_CANDIDATE"
        and manifest["activation_state"] == "NONE"
        and manifest["real_source_launch"] == "NOT_AUTHORISED_BY_RUNTIME"
    ) else "FAIL"

    receipt = {
        "schema": "ovc-c2p2-rs0-runtime-capacity-recovery-measurement/v1",
        "programme_id": "OVC-C2P2-RS0-SHADOW-EVIDENCE-v0.1",
        "packet_id": "C2P2-RS0-RUNTIME-CAPACITY-REMEDIATION",
        "measurement_class": "FULL_CARDINALITY_SYNTHETIC_NON_EVIDENTIARY",
        "status": status,
        "adapter_id": ADAPTER_ID,
        "candidate_id": CANDIDATE_A["candidate_id"],
        "synthetic_rows": args.rows,
        "real_source_consumed": False,
        "scientific_effect": "NONE",
        "selection_state": manifest["selection_state"],
        "activation_state": manifest["activation_state"],
        "memory": {
            "peak_rss_bytes": peak,
            "limit_bytes": args.memory_limit,
            "headroom_bytes": args.memory_limit - peak,
        },
        "storage": {
            "runtime_spool_database_bytes": database_bytes,
            "limit_bytes": args.storage_limit,
            "headroom_bytes": args.storage_limit - database_bytes,
            "runner_free_bytes_after_measurement": disk.free,
        },
        "workload": {
            "processed_source_record_ids": manifest["counts"]["processed_source_record_ids"],
            "candidates": manifest["counts"]["candidates"],
            "tracklets": manifest["counts"]["tracklets"],
            "object_assertions": manifest["counts"]["object_assertions"],
            "match_decisions": manifest["counts"]["match_decisions"],
            "evidence_vectors": manifest["counts"]["evidence_vectors"],
            "checkpoint_cadence": manifest["checkpoint_cadence"],
        },
        "stream_sha256": manifest["stream_sha256"],
        "indexes_sha256": manifest["indexes_sha256"],
        "adapter_result_sha256": manifest["adapter_result_sha256"],
        "wall_seconds": wall_seconds,
        "frozen_denials": {
            "sampling": "FORBIDDEN",
            "reduced_precision": "FORBIDDEN",
            "population_change": "FORBIDDEN",
            "objectpack_change": "FORBIDDEN",
            "selection": "NONE",
            "activation": "NONE",
            "real_source_rerun": "NOT_AUTHORISED",
        },
    }
    args.output.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(receipt, sort_keys=True))
    return 0 if status == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
