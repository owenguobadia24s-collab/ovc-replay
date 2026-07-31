from __future__ import annotations

import hashlib
import json
import os
import platform
import resource
import sqlite3
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Iterator, Mapping, Sequence

AXES: tuple[str, ...] = (
    "LOCATION",
    "MOTION",
    "ORGANISATION",
    "INTERACTION",
    "QUALITY",
)
ALLOWED_ROLES = {"DISCOVERY", "DEVELOPMENT"}
ALLOWED_CLOCKS = {"15M", "2H_A_L"}
ALLOWED_SIDES = {"BID", "ASK"}
FORBIDDEN_FIELDS = {
    "overall_state",
    "winning_state",
    "overall_transition",
    "winning_axis",
    "future_outcome",
    "outcome",
    "semantic_label",
    "probability",
}
DEFAULT_WINDOW_CAP = 100_000
SCHEMA_VERSION = "ovc-ro4-state-transition-index/v1"


class RO4IndexError(RuntimeError):
    """A blocking source, chronology, authority or determinism failure."""


class DeclaredSampleRequired(RO4IndexError):
    """Ordinary materialisation must stop and an explicit sample manifest is required."""


@dataclass(frozen=True)
class ReleaseBinding:
    role: str
    authority: str
    release_id: str
    manifest_id: str
    manifest_sha256: str
    c1_release_id: str
    c1_manifest_id: str
    opt_a_release_id: str
    opt_a_manifest_id: str
    state_record_count: int
    transition_record_count: int


@dataclass(frozen=True)
class PartitionSpec:
    partition_id: str
    role: str
    clock: str
    side: str
    evaluation_scope_id: str
    state_path: str
    state_sha256: str
    state_size_bytes: int
    state_record_count: int
    transition_path: str
    transition_sha256: str
    transition_size_bytes: int
    transition_record_count: int


@dataclass(frozen=True)
class BuildResult:
    manifest: dict[str, Any]
    benchmark: dict[str, Any]


def canonical_bytes(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n").encode("utf-8")


def logical_hash(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def safe_relative_path(value: str) -> PurePosixPath:
    if not isinstance(value, str) or not value:
        raise RO4IndexError("INVALID_EMPTY_SOURCE_PATH")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or "." in path.parts or "\\" in value:
        raise RO4IndexError(f"UNSAFE_SOURCE_PATH:{value}")
    return path


def parse_utc(value: str) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise RO4IndexError(f"NON_UTC_FIRST_VALID_TIME:{value!r}")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise RO4IndexError(f"INVALID_FIRST_VALID_TIME:{value}") from exc
    if parsed.tzinfo != timezone.utc:
        raise RO4IndexError(f"NON_UTC_FIRST_VALID_TIME:{value}")
    return parsed


def interval_for(clock: str, first_valid_time: str) -> tuple[str, str]:
    close = parse_utc(first_valid_time)
    if clock == "15M":
        delta = timedelta(minutes=15)
    elif clock == "2H_A_L":
        delta = timedelta(hours=2)
    else:
        raise RO4IndexError(f"UNAUTHORISED_CLOCK:{clock}")
    open_time = close - delta
    return (
        open_time.isoformat().replace("+00:00", "Z"),
        close.isoformat().replace("+00:00", "Z"),
    )


def _read_jsonl(path: Path) -> Iterator[tuple[int, dict[str, Any]]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.endswith("\n"):
                raise RO4IndexError(f"UNTERMINATED_JSONL:{path.name}:{line_number}")
            if not line.strip():
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                raise RO4IndexError(f"INVALID_JSONL:{path.name}:{line_number}") from exc
            if not isinstance(value, dict):
                raise RO4IndexError(f"NON_OBJECT_JSONL:{path.name}:{line_number}")
            yield line_number, value


def _require_no_forbidden(row: Mapping[str, Any], context: str) -> None:
    leaked = sorted(FORBIDDEN_FIELDS.intersection(row))
    if leaked:
        raise RO4IndexError(f"FORBIDDEN_FIELD:{context}:{','.join(leaked)}")


def _load_inventory(path: Path) -> tuple[dict[str, ReleaseBinding], list[PartitionSpec], dict[str, Any]]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if raw.get("schema") != "ovc-ro4-g1-source-inventory/v1":
        raise RO4IndexError("SOURCE_INVENTORY_SCHEMA_MISMATCH")
    if raw.get("validation_consumption") != "LOCKED_UNCONSUMED":
        raise RO4IndexError("VALIDATION_DENIAL_NOT_FROZEN")
    releases: dict[str, ReleaseBinding] = {}
    for item in raw.get("releases", []):
        role = item.get("role")
        if role not in ALLOWED_ROLES:
            # This check happens before any source path is resolved.
            raise RO4IndexError(f"ROLE_DENIED_BEFORE_PATH_RESOLUTION:{role}")
        releases[role] = ReleaseBinding(
            role=role,
            authority=str(item["authority"]),
            release_id=str(item["release_id"]),
            manifest_id=str(item["manifest_id"]),
            manifest_sha256=str(item["manifest_sha256"]),
            c1_release_id=str(item["c1_release_id"]),
            c1_manifest_id=str(item["c1_manifest_id"]),
            opt_a_release_id=str(item["opt_a_release_id"]),
            opt_a_manifest_id=str(item["opt_a_manifest_id"]),
            state_record_count=int(item["state_record_count"]),
            transition_record_count=int(item["transition_record_count"]),
        )
    if set(releases) != ALLOWED_ROLES:
        raise RO4IndexError("EXACT_DISCOVERY_DEVELOPMENT_RELEASE_SET_REQUIRED")
    partitions: list[PartitionSpec] = []
    seen: set[str] = set()
    for item in raw.get("partitions", []):
        role = item.get("role")
        if role not in ALLOWED_ROLES:
            raise RO4IndexError(f"ROLE_DENIED_BEFORE_PATH_RESOLUTION:{role}")
        clock = item.get("clock")
        side = item.get("side")
        if clock not in ALLOWED_CLOCKS:
            raise RO4IndexError(f"UNAUTHORISED_CLOCK:{clock}")
        if side not in ALLOWED_SIDES:
            raise RO4IndexError(f"UNAUTHORISED_SIDE:{side}")
        partition_id = str(item["partition_id"])
        if partition_id in seen:
            raise RO4IndexError(f"DUPLICATE_PARTITION:{partition_id}")
        seen.add(partition_id)
        partitions.append(
            PartitionSpec(
                partition_id=partition_id,
                role=role,
                clock=clock,
                side=side,
                evaluation_scope_id=str(item["evaluation_scope_id"]),
                state_path=str(safe_relative_path(item["state_path"])),
                state_sha256=str(item["state_sha256"]),
                state_size_bytes=int(item["state_size_bytes"]),
                state_record_count=int(item["state_record_count"]),
                transition_path=str(safe_relative_path(item["transition_path"])),
                transition_sha256=str(item["transition_sha256"]),
                transition_size_bytes=int(item["transition_size_bytes"]),
                transition_record_count=int(item["transition_record_count"]),
            )
        )
    if not partitions:
        raise RO4IndexError("NO_PARTITIONS_DECLARED")
    return releases, sorted(partitions, key=lambda x: x.partition_id), raw


def _resolve_verified(root: Path, relative: str, expected_size: int, expected_sha: str) -> Path:
    path = root.joinpath(*safe_relative_path(relative).parts)
    if not path.is_file() or path.is_symlink():
        raise RO4IndexError(f"MISSING_OR_UNSAFE_SOURCE:{relative}")
    actual_size = path.stat().st_size
    if actual_size != expected_size:
        raise RO4IndexError(f"SOURCE_SIZE_MISMATCH:{relative}:{actual_size}:{expected_size}")
    actual_sha = sha256_file(path)
    if actual_sha != expected_sha:
        raise RO4IndexError(f"SOURCE_HASH_MISMATCH:{relative}:{actual_sha}:{expected_sha}")
    return path


