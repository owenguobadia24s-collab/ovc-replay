#!/usr/bin/env python3
"""Measure a non-evidentiary C2P2-RS0 capacity dry run on the executing runner.

This harness consumes only the frozen synthetic C2P ObjectPack fixture. It exercises
identity-bearing pair-work shape, canonical event-ledger/checkpoint serialization and
checkpoint/restart equivalence. It never reads provider, EC1, OPT-C/D or Validation data.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import resource
import tempfile
import time
import tracemalloc

from ovc.opt_b.c2p_v0_2.assertion import create_object_assertion
from ovc.opt_b.c2p_v0_2.checkpoint import build_checkpoint, checkpoint_bytes, restore_checkpoint
from ovc.opt_b.c2p_v0_2.events import build_assertion_genesis_event
from ovc.opt_b.c2p_v0_2.ledger import CanonicalEventLedger

ROOT = Path(__file__).resolve().parents[3]
PACK_PATH = ROOT / "fixtures/opt_b/c2p/v0_2/packs/C2P_SYNTH_OBJECTPACK_MINIMAL_A_v1.json"
CANDIDATE_PACKS = (
    "C2P2-PS0-OP-A-STRICT-CONTINUITY-v1",
    "C2P2-PS0-OP-B-RELATIONAL-CONTINUITY-v1",
    "C2P2-PS0-OP-C-EPISODE-ENRICHED-CONTINUITY-v1",
)
ELIGIBLE_CANDIDATES_MAX = 2048
IDENTITY_PREDICATES_MAX = 16
PAIR_ADJUDICATIONS_MAX = 4_194_304
CHECKPOINT_EVENTS = 384


def digest(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def _synthetic_assertion(seed: str, pack: dict) -> dict:
    members = [digest(f"{seed}-member-{index}") for index in range(3)]
    tracklet = {
        "object_pack_id": pack["object_pack_id"],
        "state": "CONFIRMED",
        "member_candidate_ids": members,
        "first_valid_time": "2026-01-01T00:03:00Z",
        "evaluation_cutoff": "2026-01-01T00:05:00Z",
        "structural_role_id": "LEVEL",
        "geometry_kind_id": "POINT_REFERENCE",
        "hard_scope": {"instrument": "SYNTH", "side": "BID", "scale": "15M", "partition": "RS0-DRY"},
    }
    decision = {
        "object_pack_id": pack["object_pack_id"],
        "terminal_decision": "NEW",
        "candidate_id": members[-1],
        "decision_id": digest(f"{seed}-decision"),
        "first_valid_time": "2026-01-01T00:04:00Z",
        "evaluation_cutoff": "2026-01-01T00:05:00Z",
    }
    return create_object_assertion(tracklet, decision, pack)


def _build_ledger(pack: dict, count: int = CHECKPOINT_EVENTS) -> tuple[CanonicalEventLedger, list[str]]:
    ledger = CanonicalEventLedger()
    assertion_ids: list[str] = []
    for index in range(count):
        seed = f"rs0-dry-{index:04d}"
        obj = _synthetic_assertion(seed, pack)
        event = build_assertion_genesis_event(
            obj,
            pack,
            market_effective_start="2026-01-01T00:00:00Z",
            market_effective_end=None,
            evaluation_cutoff="2026-01-01T00:05:00Z",
            geometry={"coordinate": f"{100 + (index % 100) / 1000:.3f}"},
            state_payload={"dry_run_index": index, "scientific_effect": "NONE"},
            source_hashes=[digest(f"{seed}-source")],
        )
        ledger.append(event)
        assertion_ids.append(obj["object_assertion_id"])
    ledger.verify_integrity()
    return ledger, assertion_ids


def _pair_kernel(candidate_count: int = ELIGIBLE_CANDIDATES_MAX) -> tuple[str, int]:
    """Exercise one exact hard-scope pair-work envelope without scientific predicates."""
    acc = bytearray(32)
    pairs = 0
    for left in range(candidate_count):
        left_bytes = left.to_bytes(4, "big")
        for right in range(left + 1, candidate_count):
            token = hashlib.sha256(left_bytes + right.to_bytes(4, "big")).digest()
            predicate_mask = int.from_bytes(token[:2], "big")
            acc[pairs & 31] ^= predicate_mask & 0xFF
            pairs += 1
    return hashlib.sha256(bytes(acc)).hexdigest(), pairs


def run_measurement() -> dict:
    pack = json.loads(PACK_PATH.read_text(encoding="utf-8"))
    if pack.get("status") != "SYNTHETIC_ONLY_NONEMPIRICAL" or pack.get("real_source_forbidden") is not True:
        raise RuntimeError("RS0_DRY_RUN_SYNTHETIC_FIREWALL_FAILED")

    tracemalloc.start()
    start = time.perf_counter()
    kernel_start = time.perf_counter()
    lane_digests: dict[str, str] = {}
    pair_count = None
    for candidate_pack in CANDIDATE_PACKS:
        kernel_digest, observed_pairs = _pair_kernel()
        lane_digests[candidate_pack] = digest(f"{candidate_pack}:{kernel_digest}")
        pair_count = observed_pairs if pair_count is None else pair_count
        if observed_pairs != pair_count:
            raise RuntimeError("RS0_DRY_RUN_PAIR_COUNT_DRIFT")
    kernel_seconds = time.perf_counter() - kernel_start

    ledger_start = time.perf_counter()
    ledger, assertion_ids = _build_ledger(pack)
    checkpoint = build_checkpoint(ledger, assertion_ids=assertion_ids, index_digest=digest("rs0-dry-index"))
    encoded_checkpoint = checkpoint_bytes(checkpoint)
    restored = restore_checkpoint(checkpoint)
    if restored.canonical_export_bytes() != ledger.canonical_export_bytes() or restored.seal() != ledger.seal():
        raise RuntimeError("RS0_DRY_RUN_CHECKPOINT_RESTART_NOT_EQUIVALENT")
    ledger_seconds = time.perf_counter() - ledger_start

    ledger_export = ledger.canonical_export_bytes()
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        checkpoint_path = root / "checkpoint.json"
        ledger_path = root / "ledger.ndjson"
        checkpoint_path.write_bytes(encoded_checkpoint)
        ledger_path.write_bytes(ledger_export)
        external_storage_growth_bytes = sum(path.stat().st_size for path in (checkpoint_path, ledger_path))

    _, peak_python_bytes = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    wall_seconds = time.perf_counter() - start
    peak_rss_bytes = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss) * 1024
    cpu_count = int(os.cpu_count() or 1)
    concurrency_limit_recommendation = max(1, min(2, cpu_count))
    checkpoint_cadence_work_units = ELIGIBLE_CANDIDATES_MAX // 8

    body = {
        "schema": "ovc-c2p2-rs0-capacity-dry-run-measurement/v1",
        "programme_id": "OVC-C2P2-RS0-SHADOW-EVIDENCE-v0.1",
        "packet_id": "C2P2-RS0-CAPACITY-DRY-RUN-AND-ARTIFACT-BINDING",
        "measurement_class": "MEASURED_SYNTHETIC_RUNNER_NON_EVIDENTIARY",
        "scientific_effect": "NONE",
        "real_source_consumed": False,
        "validation_consumed": False,
        "object_pack_selection_effect": "NONE",
        "synthetic_object_pack_id": pack["object_pack_id"],
        "candidate_pack_labels": list(CANDIDATE_PACKS),
        "reference_envelope": {
            "eligible_candidates_max": ELIGIBLE_CANDIDATES_MAX,
            "identity_predicates_max": IDENTITY_PREDICATES_MAX,
            "pair_adjudications_max": PAIR_ADJUDICATIONS_MAX,
        },
        "workload": {
            "pair_adjudications_per_candidate_pack": pair_count,
            "candidate_pack_count": len(CANDIDATE_PACKS),
            "total_pair_kernel_evaluations": int(pair_count or 0) * len(CANDIDATE_PACKS),
            "checkpoint_event_count": ledger.event_count,
        },
        "measurements": {
            "wall_seconds": wall_seconds,
            "pair_kernel_seconds": kernel_seconds,
            "ledger_checkpoint_seconds": ledger_seconds,
            "peak_python_tracemalloc_bytes": peak_python_bytes,
            "peak_process_rss_bytes": peak_rss_bytes,
            "external_storage_growth_bytes": external_storage_growth_bytes,
            "checkpoint_bytes": len(encoded_checkpoint),
            "ledger_export_bytes": len(ledger_export),
            "cpu_count": cpu_count,
        },
        "checkpoint_restart": {
            "status": "PASS_LOGICAL_AND_BYTE_EQUIVALENCE",
            "checkpoint_id": checkpoint["checkpoint_id"],
            "ledger_digest": ledger.global_digest(),
        },
        "runner_policy_recommendation": {
            "max_concurrency": concurrency_limit_recommendation,
            "checkpoint_cadence_work_units": checkpoint_cadence_work_units,
            "basis": "cpu_count_bounded_to_two_and_eight_checkpoints_per_reference_candidate_partition",
        },
        "lane_digests": lane_digests,
        "semantic_denials": [
            "SAMPLING",
            "REDUCED_PRECISION",
            "POPULATION_CHANGE",
            "PREDICATE_WEAKENING",
            "OBJECTPACK_CHANGE",
        ],
        "environment": {
            "github_actions": os.environ.get("GITHUB_ACTIONS", "").lower() == "true",
            "runner_name": os.environ.get("RUNNER_NAME"),
            "runner_os": os.environ.get("RUNNER_OS"),
            "runner_arch": os.environ.get("RUNNER_ARCH"),
            "python": platform.python_version(),
            "platform": platform.platform(),
            "cpu_count": cpu_count,
        },
    }
    measurement_id = hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
    return {"measurement_id": measurement_id, **body}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    receipt = run_measurement()
    text = json.dumps(receipt, sort_keys=True, separators=(",", ":"))
    if args.output:
        args.output.write_text(text + "\n", encoding="utf-8")
    print("C2P2_RS0_CAPACITY_MEASUREMENT_JSON=" + text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
