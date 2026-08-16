from __future__ import annotations

import hashlib
import json
import os
import resource
import shutil
import tempfile
import time
import tracemalloc
from pathlib import Path
from typing import Any, Mapping

from .assertion import create_object_assertion
from .checkpoint import build_checkpoint
from .events import build_assertion_genesis_event
from .ledger import CanonicalEventLedger


MIB = 1024 * 1024
GIB = 1024 * MIB
DEFAULT_SAMPLE_ASSERTIONS = 256
DEFAULT_CHECKPOINT_CADENCE = 256


def _digest(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def _available_memory_bytes() -> int:
    try:
        pages = int(os.sysconf("SC_AVPHYS_PAGES"))
        page_size = int(os.sysconf("SC_PAGE_SIZE"))
        return pages * page_size
    except (ValueError, OSError, AttributeError):
        return 0


def _peak_rss_bytes() -> int:
    value = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    # Linux reports KiB; macOS reports bytes. GitHub assurance uses Linux, but keep
    # the helper portable enough for local dry-runs.
    if value < 10_000_000:
        return value * 1024
    return value


def _synthetic_pack() -> dict[str, Any]:
    return {
        "object_pack_id": "C2P2-RS0-CAPACITY-SYNTH-PACK-v1",
        "status": "SYNTHETIC_ONLY_NONEMPIRICAL",
        "activation_eligible": False,
        "confirmation": {"minimum_tracklet_members": 3},
    }


def _synthetic_assertion(seed: str, pack: Mapping[str, Any]) -> dict[str, Any]:
    members = [_digest(f"{seed}-{index}") for index in range(3)]
    tracklet = {
        "object_pack_id": pack["object_pack_id"],
        "state": "CONFIRMED",
        "member_candidate_ids": members,
        "first_valid_time": "2026-01-01T00:03:00Z",
        "evaluation_cutoff": "2026-01-01T00:05:00Z",
        "structural_role_id": "LEVEL",
        "geometry_kind_id": "POINT_REFERENCE",
        "hard_scope": {"instrument": "SYNTH", "side": "BID", "scale": "15M", "partition": "RS0_CAPACITY"},
    }
    decision = {
        "object_pack_id": pack["object_pack_id"],
        "terminal_decision": "NEW",
        "candidate_id": members[-1],
        "decision_id": _digest(f"{seed}-decision"),
        "first_valid_time": "2026-01-01T00:04:00Z",
        "evaluation_cutoff": "2026-01-01T00:05:00Z",
    }
    return create_object_assertion(tracklet, decision, pack)


def run_rs0_capacity_dry_run(*, sample_assertions: int = DEFAULT_SAMPLE_ASSERTIONS) -> dict[str, Any]:
    """Measure a bounded synthetic C2P mechanical workload without consuming market evidence.

    The result freezes a conservative *execution ceiling*, not a scientific estimate of
    full-population demand. A future RS0 run that reaches the ceiling must fail closed and
    return for operator review rather than sample, reduce precision, or change semantics.
    """
    if sample_assertions <= 0:
        raise ValueError("sample_assertions must be positive")

    pack = _synthetic_pack()
    disk_before = shutil.disk_usage(tempfile.gettempdir())
    available_memory = _available_memory_bytes()
    rss_before = _peak_rss_bytes()

    tracemalloc.start()
    started = time.perf_counter()
    assertions: list[dict[str, Any]] = []
    events: list[dict[str, Any]] = []
    for index in range(sample_assertions):
        seed = f"RS0-CAP-{index:06d}"
        assertion = _synthetic_assertion(seed, pack)
        assertions.append(assertion)
        events.append(
            build_assertion_genesis_event(
                assertion,
                pack,
                market_effective_start="2026-01-01T00:00:00Z",
                market_effective_end=None,
                evaluation_cutoff="2026-01-01T00:05:00Z",
                geometry={"coordinate": f"{101 + index / 1000:.3f}"},
                state_payload={"capacity_fixture_index": index},
                source_hashes=[_digest(f"{seed}-source")],
            )
        )

    ledger = CanonicalEventLedger.from_events(events)
    checkpoint = build_checkpoint(
        ledger,
        assertion_ids=[item["object_assertion_id"] for item in assertions],
        index_digest=_digest("rs0-capacity-index"),
    )
    ledger_bytes = ledger.canonical_export_bytes()
    checkpoint_bytes = json.dumps(checkpoint, sort_keys=True, separators=(",", ":")).encode("utf-8")
    elapsed = time.perf_counter() - started
    _, py_peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    rss_peak = max(_peak_rss_bytes(), rss_before)
    disk_after = shutil.disk_usage(tempfile.gettempdir())
    free_disk = min(int(disk_before.free), int(disk_after.free))
    artifact_bytes = len(ledger_bytes) + len(checkpoint_bytes)

    # Conservative runner-scoped ceilings. These are intentionally capacity limits,
    # not claims about expected full-run consumption.
    memory_ceiling = max(512 * MIB, rss_peak * 4)
    if available_memory > 0:
        memory_ceiling = min(memory_ceiling, max(512 * MIB, available_memory // 2))
    storage_ceiling = max(2 * GIB, artifact_bytes * 8192)
    if free_disk > 0:
        storage_ceiling = min(storage_ceiling, max(2 * GIB, free_disk // 2))

    return {
        "schema": "ovc-c2p2-rs0-capacity-dry-run/v1",
        "authority_effect": "NONE_NON_EVIDENTIARY_MECHANICAL_ONLY",
        "source_mode": "SYNTHETIC_ONLY_NONEMPIRICAL",
        "real_source_consumed": False,
        "sample": {
            "assertions": sample_assertions,
            "events": len(events),
            "checkpoint_cadence_assertions": min(DEFAULT_CHECKPOINT_CADENCE, sample_assertions),
        },
        "measured": {
            "wall_clock_seconds": round(elapsed, 6),
            "peak_rss_bytes": rss_peak,
            "python_tracemalloc_peak_bytes": int(py_peak),
            "artifact_bytes": artifact_bytes,
            "available_memory_bytes": int(available_memory),
            "free_temp_disk_bytes": int(free_disk),
        },
        "recommended_execution_envelope": {
            "peak_memory_limit_bytes": int(memory_ceiling),
            "external_storage_limit_bytes": int(storage_ceiling),
            "concurrency_limit": 1,
            "checkpoint_cadence_assertions": min(DEFAULT_CHECKPOINT_CADENCE, sample_assertions),
            "capacity_exceeded_disposition": "FAIL_CLOSED_RETURN_TO_OPERATOR",
        },
        "semantic_firewall": {
            "sampling": "FORBIDDEN",
            "reduced_precision": "FORBIDDEN",
            "population_change": "FORBIDDEN",
            "objectpack_change": "FORBIDDEN",
            "candidate_selection": "FORBIDDEN",
            "activation": "FORBIDDEN",
        },
    }


def main() -> int:
    print("C2P2_RS0_CAPACITY_DRY_RUN=" + json.dumps(run_rs0_capacity_dry_run(), sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
