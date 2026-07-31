from __future__ import annotations

import gzip
import hashlib
import json
import resource
import sqlite3
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Iterator, Mapping

from .index_common import AXES, RO4IndexError, canonical_bytes, logical_hash, sha256_file

AUTHORITY = "LOCAL_READ_ONLY_DERIVED"
BANNER = (
    "DESCRIPTIVE COUNTS ONLY - counts are not probabilities, likelihoods, "
    "forecasts or transition expectations."
)
MISSING_STATUSES = {"NOT_EVALUATED", "NOT_EVALUABLE", "QUARANTINED"}
CONFLICT_PREDICATE_ID = "C2.CONFLICT.AMBIGUOUS_BOUNDARY.v0.1"


@dataclass(frozen=True)
class G2BuildResult:
    manifest: dict[str, Any]
    benchmark: dict[str, Any]


def _peak_rss_bytes() -> int:
    value = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return int(value if sys.platform == "darwin" else value * 1024)


def _metadata(source: sqlite3.Connection) -> dict[str, Any]:
    return {key: json.loads(value) for key, value in source.execute("SELECT key,value FROM metadata")}


def _axis_token(axes: Mapping[str, Any], axis: str) -> tuple[str, Any]:
    item = axes[axis]
    return str(item.get("status")), item.get("value")


def _verified_parts(index_dir: Path, source_manifest: Mapping[str, Any]) -> list[tuple[dict[str, Any], Path]]:
    result: list[tuple[dict[str, Any], Path]] = []
    for part in sorted(source_manifest["partitions"], key=lambda item: item["partition_id"]):
        path = index_dir / part["index_file"]
        if not path.is_file() or sha256_file(path) != part["index_file_sha256"]:
            raise RO4IndexError(f"RO4_G1_INDEX_HASH_MISMATCH:{part['partition_id']}")
        result.append((part, path))
    return result

def _write_json(path: Path, wrapper: dict[str, Any]) -> dict[str, Any]:
    path.write_bytes(canonical_bytes(wrapper))
    return {
        "file": path.name,
        "sha256": sha256_file(path),
        "size_bytes": path.stat().st_size,
        "record_count": len(wrapper["records"]),
        "record_stream_sha256": wrapper["record_stream_sha256"],
    }


def _write_gzip_jsonl(path: Path, records: Iterable[dict[str, Any]]) -> dict[str, Any]:
    count = 0
    digest = hashlib.sha256()
    with path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, compresslevel=1, mtime=0) as handle:
            for record in records:
                line = canonical_bytes(record)
                digest.update(line)
                handle.write(line)
                count += 1
    return {
        "file": path.name,
        "sha256": sha256_file(path),
        "size_bytes": path.stat().st_size,
        "record_count": count,
        "record_stream_sha256": digest.hexdigest(),
    }


def _stream_hash(records: Iterable[dict[str, Any]]) -> str:
    digest = hashlib.sha256()
    for record in records:
        digest.update(canonical_bytes(record))
    return digest.hexdigest()



def _iter_gzip_jsonl(path: Path) -> Iterator[dict[str, Any]]:
    with gzip.open(path, "rt", encoding="utf-8", newline="") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.endswith("\n"):
                raise RO4IndexError(f"UNTERMINATED_G2_JSONL:{path.name}:{line_number}")
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise RO4IndexError(f"INVALID_G2_JSONL:{path.name}:{line_number}") from exc
            if not isinstance(record, dict):
                raise RO4IndexError(f"NON_OBJECT_G2_JSONL:{path.name}:{line_number}")
            yield record


def _validate_record_hash(record: Mapping[str, Any], context: str) -> None:
    core = dict(record)
    declared = core.pop("logical_hash", None)
    identity = None
    prefix = None
    if "run_id" in core:
        identity = core.pop("run_id")
        prefix = "RO4.RUN."
    elif "projection_id" in core:
        identity = core.pop("projection_id")
        prefix = "RO4.XSCALE."
    expected = logical_hash(core)
    if expected != declared or (identity is not None and identity != prefix + expected):
        raise RO4IndexError(f"G2_RECORD_LOGICAL_HASH_MISMATCH:{context}")
