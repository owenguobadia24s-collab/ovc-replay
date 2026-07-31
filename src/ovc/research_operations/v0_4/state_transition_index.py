from __future__ import annotations

import hashlib
import json
import os
import platform
import resource
import sqlite3
import sys
import time
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from .index_common import (
    DEFAULT_WINDOW_CAP, BuildResult, DeclaredSampleRequired, RO4IndexError,
    canonical_bytes, logical_hash, sha256_file, _load_inventory,
)
from .index_partition import _build_partition

def _memory_total_bytes() -> int:
    try:
        pages = os.sysconf("SC_PHYS_PAGES")
        page_size = os.sysconf("SC_PAGE_SIZE")
        return int(pages * page_size)
    except (AttributeError, ValueError, OSError):
        return 1


def _peak_rss_bytes() -> int:
    usage = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    # Linux reports KiB; macOS reports bytes.
    return int(usage if sys.platform == "darwin" else usage * 1024)


def assess_window_cardinality(
    state_count: int,
    window_lengths: Sequence[int],
    *,
    cap: int = DEFAULT_WINDOW_CAP,
    declared_sample_manifest: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    if state_count < 0 or not window_lengths or any(length <= 0 for length in window_lengths):
        raise RO4IndexError("INVALID_WINDOW_CARDINALITY_INPUT")
    total = sum(max(0, state_count - length + 1) for length in window_lengths)
    if total > cap and declared_sample_manifest is None:
        raise DeclaredSampleRequired(f"WINDOW_CAP_EXCEEDED:{total}:{cap}:DECLARED_SAMPLE_MODE_REQUIRED")
    mode = "FULL" if total <= cap else "DECLARED_SAMPLE_MODE"
    if mode == "DECLARED_SAMPLE_MODE":
        if declared_sample_manifest.get("mode") != "DECLARED_SAMPLE_MODE":
            raise RO4IndexError("DECLARED_SAMPLE_MANIFEST_MODE_REQUIRED")
        if declared_sample_manifest.get("authority") != "SAMPLED_NON_CANONICAL_EXPLORATORY":
            raise RO4IndexError("DECLARED_SAMPLE_AUTHORITY_MISMATCH")
    return {"state_count": state_count, "window_lengths": list(window_lengths), "window_count": total, "cap": cap, "mode": mode}


def deterministic_sample_ids(
    sequence_ids: Iterable[str],
    *,
    sample_size: int,
    sampling_policy_id: str,
    sampling_version: str,
) -> list[str]:
    if sample_size < 0 or not sampling_policy_id or not sampling_version:
        raise RO4IndexError("INVALID_DECLARED_SAMPLE_POLICY")
    ranked = sorted(
        (
            hashlib.sha256((value + sampling_policy_id + sampling_version).encode("utf-8")).hexdigest(),
            value,
        )
        for value in sequence_ids
    )
    return [value for _, value in ranked[:sample_size]]


def build_full_index(
    *,
    source_root: Path,
    inventory_path: Path,
    output_dir: Path,
    benchmark_path: Path | None = None,
    selected_partition: str | None = None,
    reference_machine: str = "LOCAL_REFERENCE_RUNNER",
    storage: str = "LOCAL_EXTERNAL_ARTIFACT_ROOT",
) -> BuildResult:
    releases, partitions, inventory = _load_inventory(inventory_path)
    source_root = source_root.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    if selected_partition is not None:
        partitions = [item for item in partitions if item.partition_id == selected_partition]
        if not partitions:
            raise RO4IndexError(f"UNKNOWN_INCREMENTAL_PARTITION:{selected_partition}")
    before_hashes = {
        item.name: sha256_file(item)
        for item in output_dir.glob("*.sqlite")
        if item.is_file() and item.name != f"{selected_partition}.sqlite"
    }
    started = time.perf_counter()
    built: list[dict[str, Any]] = []
    for spec in partitions:
        built.append(_build_partition(source_root, output_dir, spec, releases[spec.role]))
    runtime = time.perf_counter() - started
    after_hashes = {
        name: sha256_file(output_dir / name)
        for name in before_hashes
        if (output_dir / name).is_file()
    }
    unchanged_preserved = before_hashes == after_hashes
    if not unchanged_preserved:
        raise RO4IndexError("INCREMENTAL_UNCHANGED_HASH_DRIFT")

    all_partition_metadata: list[dict[str, Any]] = []
    for path in sorted(output_dir.glob("*.sqlite")):
        connection = sqlite3.connect(path)
        try:
            metadata = {key: json.loads(value) for key, value in connection.execute("SELECT key,value FROM metadata")}
        finally:
            connection.close()
        metadata.update(
            {
                "index_file": path.name,
                "index_file_sha256": sha256_file(path),
                "index_size_bytes": path.stat().st_size,
            }
        )
        all_partition_metadata.append(metadata)
    manifest_core = {
        "schema": "ovc-ro4-g1-index-manifest/v1",
        "source_inventory_sha256": sha256_file(inventory_path),
        "source_inventory_logical_hash": logical_hash(inventory),
        "operation": "INCREMENTAL_PARTITION" if selected_partition else "FULL_INDEX",
        "selected_partition": selected_partition,
        "partitions": sorted(all_partition_metadata, key=lambda x: x["partition_id"]),
        "state_record_count": sum(int(item["state_count"]) for item in all_partition_metadata),
        "transition_record_count": sum(int(item["transition_count"]) for item in all_partition_metadata),
        "validation_consumption": "LOCKED_UNCONSUMED",
        "sampling_mode": "FULL_CORPUS_NO_SAMPLING",
        "authority": "LOCAL_REPLACEABLE_DERIVED",
    }
    manifest_core["logical_hash"] = logical_hash(manifest_core)
    manifest_path = output_dir / "index-manifest.json"
    manifest_path.write_bytes(canonical_bytes(manifest_core))
    benchmark = {
        "benchmark_id": "RO4-G1-FULL-INDEX" if selected_partition is None else f"RO4-G1-INCREMENTAL-{selected_partition}",
        "machine": reference_machine,
        "os": f"{platform.system()} {platform.release()}",
        "python": platform.python_version(),
        "memory_bytes": _memory_total_bytes(),
        "storage": storage,
        "source_counts": {
            "partitions_built": len(built),
            "states_built": sum(int(item["state_count"]) for item in built),
            "transitions_built": sum(int(item["transition_count"]) for item in built),
            "full_index_states": manifest_core["state_record_count"],
            "full_index_transitions": manifest_core["transition_record_count"],
        },
        "operation": "FULL_INDEX" if selected_partition is None else "INCREMENTAL_PARTITION",
        "runtime_seconds": round(runtime, 6),
        "peak_rss_bytes": _peak_rss_bytes(),
        "logical_hash": manifest_core["logical_hash"],
        "status": "PASS" if runtime <= (600 if selected_partition is None else 90) else "WARN_PERFORMANCE_TARGET",
        "unchanged_hashes_preserved": unchanged_preserved if selected_partition else None,
        "partition_id": selected_partition,
    }
    if benchmark_path is not None:
        benchmark_path.parent.mkdir(parents=True, exist_ok=True)
        benchmark_path.write_bytes(canonical_bytes(benchmark))
    return BuildResult(manifest=manifest_core, benchmark=benchmark)


def validate_index(output_dir: Path, inventory_path: Path) -> dict[str, Any]:
    releases, specs, _ = _load_inventory(inventory_path)
    expected = {spec.partition_id: spec for spec in specs}
    manifest_path = output_dir / "index-manifest.json"
    if not manifest_path.is_file():
        raise RO4IndexError("INDEX_MANIFEST_MISSING")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("sampling_mode") != "FULL_CORPUS_NO_SAMPLING":
        raise RO4IndexError("SILENT_SAMPLING_DETECTED")
    parts = manifest.get("partitions")
    if not isinstance(parts, list) or {item.get("partition_id") for item in parts} != set(expected):
        raise RO4IndexError("INDEX_PARTITION_SET_MISMATCH")
    state_total = 0
    transition_total = 0
    for item in parts:
        spec = expected[item["partition_id"]]
        path = output_dir / item["index_file"]
        if not path.is_file() or sha256_file(path) != item["index_file_sha256"]:
            raise RO4IndexError(f"INDEX_FILE_HASH_MISMATCH:{spec.partition_id}")
        connection = sqlite3.connect(path)
        try:
            states = int(connection.execute("SELECT COUNT(*) FROM states").fetchone()[0])
            transitions = int(connection.execute("SELECT COUNT(*) FROM transitions").fetchone()[0])
            missing = int(
                connection.execute(
                    """
                    SELECT COUNT(*) FROM transitions t
                    LEFT JOIN states s1 ON s1.state_record_id=t.source_state_id
                    LEFT JOIN states s2 ON s2.state_record_id=t.target_state_id
                    WHERE s1.state_record_id IS NULL OR s2.state_record_id IS NULL
                    """
                ).fetchone()[0]
            )
        finally:
            connection.close()
        if states != spec.state_record_count or transitions != spec.transition_record_count or missing:
            raise RO4IndexError(f"INDEX_CARDINALITY_OR_ENDPOINT_FAILURE:{spec.partition_id}")
        state_total += states
        transition_total += transitions
    if state_total != sum(binding.state_record_count for binding in releases.values()):
        raise RO4IndexError("RELEASE_STATE_TOTAL_MISMATCH")
    if transition_total != sum(binding.transition_record_count for binding in releases.values()):
        raise RO4IndexError("RELEASE_TRANSITION_TOTAL_MISMATCH")
    core = dict(manifest)
    declared = core.pop("logical_hash", None)
    if logical_hash(core) != declared:
        raise RO4IndexError("INDEX_MANIFEST_LOGICAL_HASH_MISMATCH")
    return {
        "status": "PASS",
        "partitions": len(parts),
        "state_record_count": state_total,
        "transition_record_count": transition_total,
        "logical_hash": declared,
    }
