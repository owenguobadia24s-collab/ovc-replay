#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import resource
import shutil
import time
from typing import Iterable

from ovc.opt_b.c2p_v0_2.rs0_empirical_runtime_indexed import (
    EVIDENCE_CONTRACT_ID,
    RUNTIME_GENERATION_ID,
    run_indexed_empirical_runtime,
)


CANDIDATE_A = {
    "candidate_id": "C2P2-PS0-OP-A-STRICT-CONTINUITY-v3",
    "semantic_candidate_id": "C2P2-PS0-OP-A-STRICT-CONTINUITY-v2",
    "activation_eligible": False,
}
DEPENDENCIES = {"entries": []}
DEFAULT_STORAGE_LIMIT = 6_411_935_744
FULL_CARDINALITY = 1_505_072


def row(ordinal: int, *, repeated: bool) -> dict:
    value = "1.25000" if repeated else f"{ordinal:07d}.00001"
    return {
        "schema": "ovc-c2p2-rs0-source-row/v1",
        "source_role": "C2_VNEXT",
        "source_record_id": f"SYN-{ordinal:08d}",
        "source_record_kind": "C2_LEVEL",
        "instrument": "GBPUSD",
        "side": "ASK",
        "clock": "15M",
        "first_valid_time": "2024-01-01T00:00:00Z",
        "evaluation_cutoff": "2024-01-01T00:00:00Z",
        "geometry_signature": {
            "horizon_id": "H15",
            "level_type": "SWING_HIGH",
            "value": value,
            "origin": "SYNTHETIC_QUALIFICATION",
            "structural_depth": 1,
        },
        "relation_topology": ["REL-A"],
    }


def rows(count: int, *, repeated: bool) -> Iterable[dict]:
    for ordinal in range(count):
        yield row(ordinal, repeated=repeated)


def peak_rss_bytes() -> int:
    return int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss) * 1024


def run_case(root: Path, *, label: str, count: int, repeated: bool, storage_limit: int) -> dict:
    work = root / label
    if work.exists():
        shutil.rmtree(work)
    before_rss = peak_rss_bytes()
    started = time.perf_counter()
    manifest = run_indexed_empirical_runtime(
        rows(count, repeated=repeated),
        CANDIDATE_A,
        DEPENDENCIES,
        work_dir=work,
        checkpoint_cadence=4096,
        storage_limit_bytes=storage_limit,
    )
    elapsed = time.perf_counter() - started
    after_rss = peak_rss_bytes()
    measurement = {
        "label": label,
        "rows": count,
        "fixture": "REPEATED_MATCH_KEY" if repeated else "ALL_UNIQUE_MATCH_KEYS",
        "elapsed_seconds": elapsed,
        "rows_per_second": count / elapsed if elapsed else None,
        "peak_rss_bytes": after_rss,
        "peak_rss_delta_from_case_start_bytes": max(0, after_rss - before_rss),
        "database_bytes": manifest["database_bytes"],
        "bytes_per_row": manifest["database_bytes"] / count,
        "evaluated_pair_vectors": manifest["counts"]["evaluated_pair_vectors"],
        "negative_coverage_certificates": manifest["counts"]["negative_coverage_certificates"],
        "tracklets": manifest["counts"]["tracklets"],
        "object_assertions": manifest["counts"]["object_assertions"],
        "match_decisions": manifest["counts"]["match_decisions"],
        "storage_limit_bytes": storage_limit,
    }
    shutil.rmtree(work)
    return measurement


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--work-root", type=Path, required=True)
    parser.add_argument("--full-cardinality", type=int, default=FULL_CARDINALITY)
    parser.add_argument("--repeated-cardinality", type=int, default=100_000)
    parser.add_argument("--storage-limit", type=int, default=DEFAULT_STORAGE_LIMIT)
    args = parser.parse_args()

    args.work_root.mkdir(parents=True, exist_ok=True)
    cases = []
    for count in (256, 1024, 4096, 16384):
        cases.append(run_case(
            args.work_root,
            label=f"unique-{count}",
            count=count,
            repeated=False,
            storage_limit=args.storage_limit,
        ))
    cases.append(run_case(
        args.work_root,
        label=f"repeated-{args.repeated_cardinality}",
        count=args.repeated_cardinality,
        repeated=True,
        storage_limit=args.storage_limit,
    ))
    cases.append(run_case(
        args.work_root,
        label=f"unique-full-{args.full_cardinality}",
        count=args.full_cardinality,
        repeated=False,
        storage_limit=args.storage_limit,
    ))

    unique_cases = [case for case in cases if case["fixture"] == "ALL_UNIQUE_MATCH_KEYS"]
    repeated = next(case for case in cases if case["fixture"] == "REPEATED_MATCH_KEY")
    full = unique_cases[-1]
    checks = {
        "all_unique_evaluated_pair_vectors_zero": all(case["evaluated_pair_vectors"] == 0 for case in unique_cases),
        "all_unique_coverage_linear_one_per_row": all(case["negative_coverage_certificates"] == case["rows"] for case in unique_cases),
        "repeated_pair_vectors_linear_upper_bound": repeated["evaluated_pair_vectors"] <= repeated["rows"],
        "full_cardinality_completed_inside_storage_limit": full["database_bytes"] <= args.storage_limit,
        "full_cardinality_exact": full["rows"] == args.full_cardinality,
    }
    status = "PASS" if all(checks.values()) else "FAIL"
    payload = {
        "schema": "ovc-c2p2-rs0-semantic-scalability-capacity-qualification/v1",
        "packet_id": "C2P2-RS0-SEMANTIC-SCALABILITY-RECOVERY",
        "runtime_generation_id": RUNTIME_GENERATION_ID,
        "evidence_contract_id": EVIDENCE_CONTRACT_ID,
        "authority_effect": "NONE_SYNTHETIC_QUALIFICATION_ONLY",
        "real_source_read": False,
        "real_source_execution": False,
        "fresh_run_token": "NONE",
        "selection": "NONE",
        "activation": "NONE",
        "validation": "LOCKED_UNCONSUMED",
        "storage_ceiling_change": "NONE",
        "storage_limit_bytes": args.storage_limit,
        "full_cardinality_target": args.full_cardinality,
        "measurements": cases,
        "checks": checks,
        "status": status,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
