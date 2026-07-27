from __future__ import annotations

import hashlib
import json
import os
import shutil
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Mapping

from . import dukascopy_intake as base

GATE = "RPS-G1B"
SLICE_ID = "RPS.DUKASCOPY.GBPUSD.20260622_20260625.v1"
START = datetime(2026, 6, 22, tzinfo=timezone.utc)
END = datetime(2026, 6, 25, tzinfo=timezone.utc)
QUARANTINE_ID = (
    "RPS.DUKASCOPY.GBPUSD.20260622_20260625.v1."
    "20260727T160337Z.38a69acd"
)
EXPECTED_M1_ROWS = 4285
EXPECTED_MISSING = 35
EXPECTED_GAP_RUNS = 24
EXPECTED_H1_ROWS = 72
EXPECTED_COMPLETE_H1 = 64
COMPRESSED_LIMIT = 25 * 1024 * 1024
EXPANDED_LIMIT = 100 * 1024 * 1024
COVERAGE_STATE = "GAPPED"
INVENTORY_SCHEMA = "ovc-rps-g1b-quarantine-checksum-inventory/v1"
EXPECTED_SIZES = {
    "transport/dukascopy-bi5/GBPUSD/2026/05/22/BID_candles_min_1.bi5": 11210,
    "transport/dukascopy-bi5/GBPUSD/2026/05/23/BID_candles_min_1.bi5": 10791,
    "transport/dukascopy-bi5/GBPUSD/2026/05/24/BID_candles_min_1.bi5": 10740,
    "transport/dukascopy-bi5/GBPUSD/2026/05/BID_candles_hour_1.bi5": 6492,
    "transport/dukascopy-bi5/GBPUSD/2026/05/22/ASK_candles_min_1.bi5": 11226,
    "transport/dukascopy-bi5/GBPUSD/2026/05/23/ASK_candles_min_1.bi5": 10748,
    "transport/dukascopy-bi5/GBPUSD/2026/05/24/ASK_candles_min_1.bi5": 11098,
    "transport/dukascopy-bi5/GBPUSD/2026/05/ASK_candles_hour_1.bi5": 6518,
}


class RecoveryError(RuntimeError):
    """Raised when the exact RPS-G1B quarantine recovery cannot complete."""


@dataclass(frozen=True)
class Paths:
    intake: Path
    quarantine: Path
    recovery: Path
    inventory: Path
    final: Path


def utc(value: datetime) -> str:
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def canonical_sha(value: object) -> str:
    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise RecoveryError(f"refusing to overwrite compact evidence: {path}")
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def sha_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def truthy(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "on"}


def assert_operator_local(environ: Mapping[str, str]) -> None:
    if truthy(environ.get("CI")) or truthy(environ.get("GITHUB_ACTIONS")):
        raise RecoveryError(
            "RPS-G1B freeze is prohibited in CI/GitHub Actions"
        )


def resolve_paths(
    repository_root: Path,
    environ: Mapping[str, str],
) -> Paths:
    try:
        external = base._resolve_root(repository_root, environ)
    except base.IntakeError as exc:
        raise RecoveryError(str(exc)) from exc
    intake = external / "prospective-source" / "intake"
    quarantine = intake / "quarantine" / QUARANTINE_ID
    recovery = intake / "recovery" / QUARANTINE_ID
    return Paths(
        intake=intake,
        quarantine=quarantine,
        recovery=recovery,
        inventory=recovery / "quarantine-checksum-inventory.json",
        final=intake / SLICE_ID,
    )


def transport_paths() -> list[str]:
    result: list[str] = []
    for side in ("BID", "ASK"):
        day = START
        while day < END:
            result.append(
                "transport/dukascopy-bi5/"
                + base._m1_relative(day, side)
            )
            day += timedelta(days=1)
        result.append(
            "transport/dukascopy-bi5/"
            + base._h1_relative(START, side)
        )
    return sorted(result)


def expected_files() -> list[str]:
    return sorted(["incident.json", *transport_paths()])


def safe_file(root: Path, relative: str) -> Path:
    candidate = root / Path(relative)
    if candidate.is_symlink() or not candidate.is_file():
        raise RecoveryError(
            f"required regular quarantine file unavailable: {relative}"
        )
    resolved_root = root.resolve(strict=True)
    resolved = candidate.resolve(strict=True)
    try:
        resolved.relative_to(resolved_root)
    except ValueError as exc:
        raise RecoveryError(
            f"quarantine file escapes exact root: {relative}"
        ) from exc
    return resolved


def inspect(paths: Paths) -> list[dict[str, object]]:
    if not paths.quarantine.is_dir():
        raise RecoveryError(
            f"exact June quarantine unavailable: {paths.quarantine}"
        )
    expected = expected_files()
    observed = sorted(
        path.relative_to(paths.quarantine).as_posix()
        for path in paths.quarantine.rglob("*")
        if path.is_file()
    )
    if observed != expected:
        raise RecoveryError(
            "exact quarantine inventory mismatch; "
            f"missing={sorted(set(expected) - set(observed))}, "
            f"unexpected={sorted(set(observed) - set(expected))}"
        )
    try:
        incident = json.loads(
            safe_file(paths.quarantine, "incident.json").read_text(
                encoding="utf-8"
            )
        )
    except (OSError, json.JSONDecodeError) as exc:
        raise RecoveryError(
            "invalid June quarantine incident.json"
        ) from exc
    if incident.get("slice_id") != SLICE_ID:
        raise RecoveryError(
            "quarantine incident slice identity mismatch"
        )
    if incident.get("accepted_source_slice_created") is not False:
        raise RecoveryError(
            "quarantine incident does not prove non-acceptance"
        )
    records: list[dict[str, object]] = []
    for relative in expected:
        path = safe_file(paths.quarantine, relative)
        size = path.stat().st_size
        pinned = EXPECTED_SIZES.get(relative)
        if pinned is not None and size != pinned:
            raise RecoveryError(
                "transport size differs from operator evidence for "
                f"{relative}: {size} != {pinned}"
            )
        records.append(
            {
                "relative_path": relative,
                "size_bytes": size,
                "sha256": sha_file(path),
            }
        )
    return records


def preflight(
    repository_root: Path,
    environ: Mapping[str, str] | None = None,
) -> dict[str, object]:
    values = os.environ if environ is None else environ
    paths = resolve_paths(repository_root, values)
    records = inspect(paths)
    if paths.final.exists() and any(paths.final.iterdir()):
        raise RecoveryError(
            f"approved slice destination contains material: {paths.final}"
        )
    return {
        "status": "READY_FOR_CHECKSUM_INVENTORY",
        "gate": GATE,
        "slice_id": SLICE_ID,
        "quarantine_id": QUARANTINE_ID,
        "file_count": len(records),
        "inventory_exists": paths.inventory.is_file(),
        "provider_network_access_performed": False,
        "coverage_candidate": COVERAGE_STATE,
    }


def build_inventory(
    repository_root: Path,
    environ: Mapping[str, str] | None = None,
) -> dict[str, object]:
    values = os.environ if environ is None else environ
    paths = resolve_paths(repository_root, values)
    records = inspect(paths)
    compressed = sum(
        int(item["size_bytes"])
        for item in records
        if str(item["relative_path"]).startswith("transport/")
    )
    if compressed > COMPRESSED_LIMIT:
        raise RecoveryError(
            "compressed-byte limit exceeded by exact June quarantine"
        )
    payload: dict[str, object] = {
        "schema": INVENTORY_SCHEMA,
        "gate_candidate": GATE,
        "slice_id": SLICE_ID,
        "quarantine_id": QUARANTINE_ID,
        "source_window_start_utc": utc(START),
        "source_window_end_utc": utc(END),
        "files": records,
        "file_count": len(records),
        "compressed_transport_bytes": compressed,
        "compressed_byte_limit": COMPRESSED_LIMIT,
        "expanded_byte_limit": EXPANDED_LIMIT,
        "source_mutation_performed": False,
        "provider_network_access_performed": False,
    }
    payload["inventory_sha256"] = canonical_sha(payload)
    write_json(paths.inventory, payload)
    return {
        "status": "CHECKSUM_INVENTORY_FROZEN",
        "slice_id": SLICE_ID,
        "quarantine_id": QUARANTINE_ID,
        "inventory_sha256": payload["inventory_sha256"],
        "file_count": len(records),
        "provider_network_access_performed": False,
    }


def load_inventory(paths: Paths) -> dict[str, object]:
    if not paths.inventory.is_file():
        raise RecoveryError(
            "checksum inventory unavailable; run inventory first"
        )
    try:
        payload = json.loads(
            paths.inventory.read_text(encoding="utf-8")
        )
    except (OSError, json.JSONDecodeError) as exc:
        raise RecoveryError(
            "invalid quarantine checksum inventory"
        ) from exc
    logical = dict(payload)
    claimed = logical.pop("inventory_sha256", None)
    if claimed != canonical_sha(logical):
        raise RecoveryError(
            "quarantine checksum inventory logical hash mismatch"
        )
    if payload.get("schema") != INVENTORY_SCHEMA:
        raise RecoveryError(
            "unsupported checksum inventory schema"
        )
    if (
        payload.get("slice_id") != SLICE_ID
        or payload.get("quarantine_id") != QUARANTINE_ID
    ):
        raise RecoveryError(
            "checksum inventory identity mismatch"
        )
    if payload.get("files") != inspect(paths):
        raise RecoveryError(
            "quarantine bytes changed after checksum inventory freeze"
        )
    if int(payload["compressed_transport_bytes"]) > COMPRESSED_LIMIT:
        raise RecoveryError(
            "compressed-byte limit exceeded by pinned quarantine"
        )
    return payload


def copy_pinned(
    paths: Paths,
    staging: Path,
    inventory: Mapping[str, object],
) -> None:
    files = inventory.get("files")
    if not isinstance(files, list):
        raise RecoveryError("checksum inventory files are invalid")
    for item in files:
        if not isinstance(item, dict):
            raise RecoveryError("checksum inventory file entry is invalid")
        relative = str(item["relative_path"])
        # The source incident remains immutable in the original quarantine.
        # Its hash is retained in the checksum receipt but it is not relabelled
        # into the accepted source slice.
        if relative == "incident.json":
            continue
        source = safe_file(paths.quarantine, relative)
        target = staging / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        if (
            target.stat().st_size != int(item["size_bytes"])
            or sha_file(target) != item["sha256"]
        ):
            raise RecoveryError(
                f"copy-on-verify mismatch for {relative}"
            )


def month_end(start: datetime) -> datetime:
    if start.month == 12:
        return start.replace(
            year=start.year + 1,
            month=1,
            day=1,
        )
    return start.replace(month=start.month + 1, day=1)


def decode_rows(
    staging: Path,
) -> dict[tuple[str, str], list[base.CandleRow]]:
    rows: dict[tuple[str, str], list[base.CandleRow]] = {}
    for side in ("BID", "ASK"):
        combined: list[base.CandleRow] = []
        day = START
        while day < END:
            relative = base._m1_relative(day, side)
            data = base._decompress(
                (
                    staging
                    / "transport"
                    / "dukascopy-bi5"
                    / relative
                ).read_bytes(),
                identity=relative,
            )
            combined.extend(
                base._decode_candles(
                    data,
                    base=day,
                    partition_end=day + timedelta(days=1),
                    identity=relative,
                    accepted_start=START,
                    accepted_end=END,
                )
            )
            day += timedelta(days=1)
        rows[("M1", side)] = combined
        relative = base._h1_relative(START, side)
        month_start = START.replace(day=1)
        data = base._decompress(
            (
                staging
                / "transport"
                / "dukascopy-bi5"
                / relative
            ).read_bytes(),
            identity=relative,
        )
        rows[("H1", side)] = base._decode_candles(
            data,
            base=month_start,
            partition_end=month_end(month_start),
            identity=relative,
            accepted_start=START,
            accepted_end=END,
        )
    return rows
