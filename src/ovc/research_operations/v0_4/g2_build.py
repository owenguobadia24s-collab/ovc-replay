from __future__ import annotations

import json
import platform
import sqlite3
import time
from collections import Counter
from pathlib import Path
from typing import Any, Iterator

from .g2_common import (
    AUTHORITY, BANNER, G2BuildResult, _metadata, _peak_rss_bytes, _stream_hash,
    _verified_parts, _write_gzip_jsonl, _write_json,
)
from .g2_matrix_conflict import _conflict_records, _matrix_records
from .g2_persistence_cross_scale import _iter_cross_scale_records, _iter_persistence_records
from .index_common import RO4IndexError, canonical_bytes, logical_hash, sha256_file


def build_g2_evidence(
    *,
    index_dir: Path,
    output_dir: Path,
    benchmark_path: Path | None = None,
    reference_machine: str = "LOCAL_REFERENCE_RUNNER",
    storage: str = "LOCAL_EXTERNAL_ARTIFACT_ROOT",
) -> G2BuildResult:
    index_dir = index_dir.resolve()
    manifest_path = index_dir / "index-manifest.json"
    if not manifest_path.is_file():
        raise RO4IndexError("RO4_G1_INDEX_MANIFEST_MISSING")
    source_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if source_manifest.get("authority") != "LOCAL_REPLACEABLE_DERIVED":
        raise RO4IndexError("RO4_G1_AUTHORITY_MISMATCH")
    if source_manifest.get("validation_consumption") != "LOCKED_UNCONSUMED":
        raise RO4IndexError("VALIDATION_DENIAL_NOT_PRESERVED")
    parts = _verified_parts(index_dir, source_manifest)
    output_dir.mkdir(parents=True, exist_ok=True)
    filenames = {
        "matrices": "transition-matrices.json",
        "persistence": "persistence-runs.jsonl.gz",
        "conflicts": "conflict-runs.json",
        "cross_scale": "cross-scale-alignment.jsonl.gz",
    }
    for filename in [*filenames.values(), "g2-manifest.json"]:
        (output_dir / filename).unlink(missing_ok=True)

    started = time.perf_counter()
    artifacts: list[dict[str, Any]] = []

    matrix_records: list[dict[str, Any]] = []
    conflict_records: list[dict[str, Any]] = []
    for part, path in parts:
        source = sqlite3.connect(path)
        try:
            meta = _metadata(source)
            matrix_records.extend(_matrix_records(source, part["partition_id"]))
            conflict_records.extend(_conflict_records(source, meta))
        finally:
            source.close()

    matrix_stream_hash = _stream_hash(matrix_records)
    matrix_wrapper = {
        "schema": "ovc-ro4-g2-transition-matrix-set/v1",
        "authority": AUTHORITY,
        "source_g1_logical_hash": source_manifest["logical_hash"],
        "banner": BANNER,
        "records": matrix_records,
        "record_stream_sha256": matrix_stream_hash,
    }
    matrix_wrapper["logical_hash"] = logical_hash(matrix_wrapper)
    matrix_artifact = _write_json(output_dir / filenames["matrices"], matrix_wrapper)
    matrix_artifact.update(artifact_type="matrices", logical_hash=matrix_wrapper["logical_hash"])
    artifacts.append(matrix_artifact)

    conflict_stream_hash = _stream_hash(conflict_records)
    conflict_wrapper = {
        "schema": "ovc-ro4-g2-conflict-run-set/v1",
        "authority": AUTHORITY,
        "source_g1_logical_hash": source_manifest["logical_hash"],
        "records": conflict_records,
        "record_stream_sha256": conflict_stream_hash,
    }
    conflict_wrapper["logical_hash"] = logical_hash(conflict_wrapper)
    conflict_artifact = _write_json(output_dir / filenames["conflicts"], conflict_wrapper)
    conflict_artifact.update(artifact_type="conflicts", logical_hash=conflict_wrapper["logical_hash"])
    artifacts.append(conflict_artifact)

    def persistence_records() -> Iterator[dict[str, Any]]:
        for _, path in parts:
            source = sqlite3.connect(path)
            try:
                meta = _metadata(source)
                yield from _iter_persistence_records(source, meta)
            finally:
                source.close()

    persistence_artifact = _write_gzip_jsonl(
        output_dir / filenames["persistence"], persistence_records()
    )
    persistence_artifact.update(
        artifact_type="persistence",
        logical_hash=logical_hash(
            {
                "artifact_type": "persistence",
                "source_g1_logical_hash": source_manifest["logical_hash"],
                "record_count": persistence_artifact["record_count"],
                "record_stream_sha256": persistence_artifact["record_stream_sha256"],
            }
        ),
    )
    artifacts.append(persistence_artifact)

    relation_counts = Counter()

    def cross_records() -> Iterator[dict[str, Any]]:
        for record in _iter_cross_scale_records(index_dir, source_manifest):
            for item in record["axis_relations"].values():
                relation_counts[item["relation"]] += 1
            yield record

    cross_artifact = _write_gzip_jsonl(
        output_dir / filenames["cross_scale"], cross_records()
    )
    cross_artifact.update(
        artifact_type="cross_scale",
        logical_hash=logical_hash(
            {
                "artifact_type": "cross_scale",
                "source_g1_logical_hash": source_manifest["logical_hash"],
                "record_count": cross_artifact["record_count"],
                "record_stream_sha256": cross_artifact["record_stream_sha256"],
            }
        ),
    )
    artifacts.append(cross_artifact)

    counts = {
        "matrices": len(matrix_records),
        "persistence_runs": persistence_artifact["record_count"],
        "conflict_runs": len(conflict_records),
        "cross_scale_projections": cross_artifact["record_count"],
    }
    manifest_core = {
        "schema": "ovc-ro4-g2-evidence-manifest/v1",
        "authority": AUTHORITY,
        "source_g1_logical_hash": source_manifest["logical_hash"],
        "source_g1_manifest_sha256": sha256_file(manifest_path),
        "validation_consumption": "LOCKED_UNCONSUMED",
        "artifacts": sorted(artifacts, key=lambda item: item["artifact_type"]),
        "counts": counts,
        "cross_scale_relation_counts": dict(sorted(relation_counts.items())),
        "banner": BANNER,
        "matched_real_controls": "REQUIRED_AND_MATERIALISED_FOR_ALL_CONFLICT_RUNS",
        "composite_or_winner": "PROHIBITED",
        "count_presentation": "EXACT_COUNT_WITH_VISIBLE_ELIGIBLE_DENOMINATOR",
    }
    manifest_core["logical_hash"] = logical_hash(manifest_core)
    (output_dir / "g2-manifest.json").write_bytes(canonical_bytes(manifest_core))

    runtime = time.perf_counter() - started
    benchmark = {
        "benchmark_id": "RO4-G2-FULL-EVIDENCE",
        "machine": reference_machine,
        "os": f"{platform.system()} {platform.release()}",
        "python": platform.python_version(),
        "storage": storage,
        "runtime_seconds": round(runtime, 6),
        "peak_rss_bytes": _peak_rss_bytes(),
        "output_size_bytes": sum(item["size_bytes"] for item in artifacts),
        "counts": counts,
        "logical_hash": manifest_core["logical_hash"],
        "status": "PASS",
    }
    if benchmark_path is not None:
        benchmark_path.parent.mkdir(parents=True, exist_ok=True)
        benchmark_path.write_bytes(canonical_bytes(benchmark))
    return G2BuildResult(manifest=manifest_core, benchmark=benchmark)

