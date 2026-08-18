#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import json
import math
from pathlib import Path
import resource
import tracemalloc
from typing import Iterator

from ovc.opt_b.c2p_v0_2.sd_discrimination import (
    CANDIDATE_IDS,
    make_edge,
    run_streaming_discrimination,
)

POPULATION_COUNT = 1_489_144
R5_MAX_REAL_DATABASE_BYTES = 6_637_756_416
R5_APPROVED_MEMORY_LIMIT_BYTES = 1_160_593_408
CHECKPOINT_CADENCE = 4096
GIB = 1024 ** 3
MIB = 1024 ** 2


def round_up(value: int, quantum: int) -> int:
    return int(math.ceil(value / quantum) * quantum)


def synthetic_edges(count: int) -> Iterator[dict]:
    base = datetime(2021, 1, 1, tzinfo=timezone.utc)
    patterns = (
        ("SAME", "DIFFERENT", "SAME"),
        ("DIFFERENT", "SAME", "SAME"),
        ("AMBIGUOUS", "SAME", "DIFFERENT"),
        ("SAME", "SAME", "DIFFERENT"),
    )
    for ordinal in range(count):
        current = base + timedelta(minutes=ordinal)
        prior = current - timedelta(minutes=1)
        cutoff = current + timedelta(minutes=1)
        a, b, c = patterns[ordinal % len(patterns)]
        side = "BID" if ordinal % 2 == 0 else "ASK"
        clock = "15M" if ordinal % 3 else "2H_A_L"
        geometry = "LEVEL" if ordinal % 5 else "CONTAINER"
        role = f"ROLE_{ordinal % 7}"
        yield make_edge(
            prior_source_record_id=f"SYN-P-{ordinal:08d}",
            current_source_record_id=f"SYN-C-{ordinal:08d}",
            first_valid_time=current.isoformat().replace("+00:00", "Z"),
            evaluation_cutoff=cutoff.isoformat().replace("+00:00", "Z"),
            instrument="GBPUSD",
            side=side,
            clock=clock,
            structural_role_id=role,
            geometry_kind_id=geometry,
            candidate_dispositions={CANDIDATE_IDS[0]: a, CANDIDATE_IDS[1]: b, CANDIDATE_IDS[2]: c},
            confirmed_hard_breaks=["REQUIRED_SOURCE_DISCONTINUITY"],
            owner_constitution_evidence={
                "synthetic": True,
                "hard_scope_constant": True,
                "worst_case_all_edges_reviewed": True,
            },
            review_context={
                "prior": {"source_record_id": f"SYN-P-{ordinal:08d}", "first_valid_time": prior.isoformat().replace("+00:00", "Z")},
                "current": {"source_record_id": f"SYN-C-{ordinal:08d}", "first_valid_time": current.isoformat().replace("+00:00", "Z")},
            },
        )


def directory_bytes(root: Path) -> int:
    return sum(path.stat().st_size for path in root.rglob("*") if path.is_file())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--synthetic-edges", type=int, default=20_000)
    args = parser.parse_args()
    if args.synthetic_edges <= 0:
        raise SystemExit("synthetic edge count must be positive")

    root = Path(args.output_dir)
    root.mkdir(parents=True, exist_ok=True)
    if any(root.iterdir()):
        raise SystemExit("qualification output directory must be empty")

    tracemalloc.start()
    summary = run_streaming_discrimination(
        synthetic_edges(args.synthetic_edges),
        output_dir=root,
        blinding_key="C2P2-SD-PRESENTATION-BLIND-v0.1",
    )
    _, traced_peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    rss_peak = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss) * 1024

    measured_output_bytes = directory_bytes(root)
    bytes_per_edge = measured_output_bytes / args.synthetic_edges
    projected_discrimination_bytes = int(math.ceil(bytes_per_edge * POPULATION_COUNT))
    working_storage_basis = R5_MAX_REAL_DATABASE_BYTES + projected_discrimination_bytes + 512 * MIB
    proposed_storage_limit = round_up(int(math.ceil(working_storage_basis * 1.25)), GIB)
    measured_peak_memory = max(traced_peak, rss_peak)
    proposed_memory_limit = max(
        R5_APPROVED_MEMORY_LIMIT_BYTES,
        round_up(int(math.ceil(measured_peak_memory * 1.25)), 256 * MIB),
    )

    qualification = {
        "schema": "ovc-c2p2-scientific-discrimination-wp3-capacity-qualification/v1",
        "programme_id": "OVC-C2P2-SCIENTIFIC-DISCRIMINATION-v0.1",
        "packet_id": "C2P2-SD-WP3",
        "status": "PASS",
        "method": "SYNTHETIC_WORST_CASE_ALL_EDGES_HARD_BREAK_AND_REVIEWED_NO_REAL_SOURCE_READ",
        "synthetic_edge_count": args.synthetic_edges,
        "synthetic_summary": summary,
        "measured_output_bytes": measured_output_bytes,
        "measured_bytes_per_edge": bytes_per_edge,
        "measured_peak_tracemalloc_bytes": traced_peak,
        "measured_peak_rss_bytes": rss_peak,
        "measured_peak_memory_bytes": measured_peak_memory,
        "projection_population_edges": POPULATION_COUNT,
        "projected_discrimination_storage_bytes": projected_discrimination_bytes,
        "r5_real_runtime_max_database_bytes_basis": R5_MAX_REAL_DATABASE_BYTES,
        "workspace_overhead_bytes": 512 * MIB,
        "storage_safety_factor": 1.25,
        "proposed_execution_storage_limit_bytes": proposed_storage_limit,
        "proposed_peak_memory_limit_bytes": proposed_memory_limit,
        "proposed_concurrency_limit": 1,
        "proposed_checkpoint_cadence_source_records": CHECKPOINT_CADENCE,
        "sampling": "FORBIDDEN",
        "reduced_precision": "FORBIDDEN",
        "real_source_read": False,
        "real_source_execution": False,
        "candidate_semantics_changed": False,
        "thresholds_changed": False,
        "selection": "NONE",
        "activation": "NONE",
        "validation": "LOCKED_UNCONSUMED",
        "qualification_limit": "Synthetic storage projection qualifies tooling capacity only; C2P2-SD-GREAL operator approval is still required before any real-source replay.",
    }
    (root / "C2P2_SD_WP3_CAPACITY_QUALIFICATION_v0_1.json").write_text(
        json.dumps(qualification, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(qualification, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
