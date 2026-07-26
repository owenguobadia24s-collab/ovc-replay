from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path, PurePosixPath
from typing import Any, Mapping


class PriceParentError(ValueError):
    """Raised when an OPT-A price parent is not exact or cannot be joined."""


@dataclass(frozen=True)
class OptAReleaseBinding:
    role: str
    release_id: str
    manifest_id: str
    manifest_sha256: str
    payload_file_count: int
    payload_bytes: int
    price_file_count: int
    scope_file_counts: tuple[tuple[str, str, int], ...]


OPT_A_RELEASE_BINDINGS = {
    "DISCOVERY": OptAReleaseBinding(
        role="DISCOVERY",
        release_id="OPT-A.GBPUSD.DISCOVERY.2021_2023.v2",
        manifest_id="MANIFEST.OPT-A.GBPUSD.DISCOVERY.2021_2023.v2.r2",
        manifest_sha256="0cbcafa9421449574b61bfeec24f634de99cbbbc6e7a53d09ace8f702182ab8c",
        payload_file_count=293,
        payload_bytes=155_632_392,
        price_file_count=144,
        scope_file_counts=(
            ("15M", "ASK", 36),
            ("15M", "BID", 36),
            ("2H_A_L", "ASK", 36),
            ("2H_A_L", "BID", 36),
        ),
    ),
    "DEVELOPMENT": OptAReleaseBinding(
        role="DEVELOPMENT",
        release_id="OPT-A.GBPUSD.DEVELOPMENT.2024.v2",
        manifest_id="MANIFEST.OPT-A.GBPUSD.DEVELOPMENT.2024.v2.r2",
        manifest_sha256="25e1be8a7edb0e96017c45bf35f4e788345f94b22a8ed9bb0874c86338ba64cc",
        payload_file_count=101,
        payload_bytes=52_762_768,
        price_file_count=48,
        scope_file_counts=(
            ("15M", "ASK", 12),
            ("15M", "BID", 12),
            ("2H_A_L", "ASK", 12),
            ("2H_A_L", "BID", 12),
        ),
    ),
}

_CLOCK_MS = {"15M": 15 * 60 * 1000, "2H_A_L": 2 * 60 * 60 * 1000}
_PRICE_PATH_PREFIXES = {
    ("15M", "BID"): "canonical/15M/BID/",
    ("15M", "ASK"): "canonical/15M/ASK/",
    ("2H_A_L", "BID"): "canonical/2H_A_L/BID/",
    ("2H_A_L", "ASK"): "canonical/2H_A_L/ASK/",
}
_CSV_COLUMNS = ["timestamp", "open", "high", "low", "close", "volume"]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_path(value: Any) -> PurePosixPath:
    if not isinstance(value, str) or not value or "\\" in value:
        raise PriceParentError("INVALID_OPT_A_MANIFEST_PATH")
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise PriceParentError(f"UNSAFE_OPT_A_MANIFEST_PATH:{value}")
    return path


def _load_object(path: Path, code: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PriceParentError(f"{code}:{path}") from exc
    if not isinstance(value, dict):
        raise PriceParentError(f"{code}:{path}")
    return value


@dataclass(frozen=True)
class VerifiedOptARelease:
    root: Path
    binding: OptAReleaseBinding
    manifest_sha256: str
    declared_paths: frozenset[str]
    price_paths: frozenset[str]


def verify_opt_a_release(root: Path, binding: OptAReleaseBinding) -> VerifiedOptARelease:
    manifest_path = root / "manifest.json"
    if not manifest_path.is_file() or manifest_path.is_symlink():
        raise PriceParentError(f"MISSING_OPT_A_MANIFEST:{manifest_path}")
    manifest_sha = sha256(manifest_path)
    if manifest_sha != binding.manifest_sha256:
        raise PriceParentError(f"OPT_A_MANIFEST_SHA256_MISMATCH:{binding.role}")
    manifest = _load_object(manifest_path, "INVALID_OPT_A_MANIFEST")
    if manifest.get("schema") != "ovc-evidence-release-manifest/v1":
        raise PriceParentError(f"WRONG_OPT_A_MANIFEST_SCHEMA:{binding.role}")
    if manifest.get("release_id") != binding.release_id:
        raise PriceParentError(f"WRONG_OPT_A_RELEASE:{binding.role}")
    if manifest.get("manifest_id") != binding.manifest_id:
        raise PriceParentError(f"WRONG_OPT_A_MANIFEST_ID:{binding.role}")
    files = manifest.get("files")
    if not isinstance(files, list) or len(files) != binding.payload_file_count:
        raise PriceParentError(f"WRONG_OPT_A_PAYLOAD_COUNT:{binding.role}")

    declared: set[str] = set()
    price_paths: set[str] = set()
    scope_counts: Counter[tuple[str, str]] = Counter()
    payload_bytes = 0
    for item in files:
        if not isinstance(item, dict) or set(item) != {"path", "sha256", "size"}:
            raise PriceParentError("INVALID_OPT_A_MANIFEST_ENTRY")
        relative = _safe_path(item["path"])
        key = relative.as_posix()
        if key in declared:
            raise PriceParentError(f"DUPLICATE_OPT_A_MANIFEST_PATH:{key}")
        declared.add(key)
        local = root / "files" / Path(*relative.parts)
        if not local.is_file() or local.is_symlink():
            raise PriceParentError(f"MISSING_OR_UNSAFE_OPT_A_PAYLOAD:{key}")
        if local.stat().st_size != item["size"]:
            raise PriceParentError(f"OPT_A_PAYLOAD_SIZE_MISMATCH:{key}")
        if sha256(local) != item["sha256"]:
            raise PriceParentError(f"OPT_A_PAYLOAD_SHA256_MISMATCH:{key}")
        payload_bytes += local.stat().st_size
        for scope, prefix in _PRICE_PATH_PREFIXES.items():
            if key.startswith(prefix) and key.endswith(".csv"):
                price_paths.add(key)
                scope_counts[scope] += 1
                break

    actual = {
        path.relative_to(root / "files").as_posix()
        for path in (root / "files").rglob("*")
        if path.is_file()
    }
    if actual != declared:
        raise PriceParentError(f"OPT_A_LOCAL_INVENTORY_MISMATCH:{binding.role}")
    if payload_bytes != binding.payload_bytes:
        raise PriceParentError(f"OPT_A_PAYLOAD_BYTES_MISMATCH:{binding.role}")
    if len(price_paths) != binding.price_file_count:
        raise PriceParentError(f"OPT_A_PRICE_FILE_COUNT_MISMATCH:{binding.role}")
    expected_scopes = {(clock, side): count for clock, side, count in binding.scope_file_counts}
    if dict(scope_counts) != expected_scopes:
        raise PriceParentError(f"OPT_A_PRICE_SCOPE_INVENTORY_MISMATCH:{binding.role}")

    descriptor = _load_object(root / "files" / "release-descriptor.json", "INVALID_OPT_A_RELEASE_DESCRIPTOR")
    if descriptor.get("release_id") != binding.release_id or descriptor.get("role") != binding.role:
        raise PriceParentError(f"OPT_A_RELEASE_DESCRIPTOR_BINDING_MISMATCH:{binding.role}")
    if descriptor.get("lifecycle_state") != "RELEASE_FROZEN":
        raise PriceParentError(f"OPT_A_RELEASE_NOT_FROZEN:{binding.role}")
    if binding.role == "VALIDATION" or descriptor.get("validation_consumption") == "LOCKED_UNCONSUMED":
        raise PriceParentError("VALIDATION_PRICE_PARENT_PROHIBITED")

    return VerifiedOptARelease(
        root=root,
        binding=binding,
        manifest_sha256=manifest_sha,
        declared_paths=frozenset(declared),
        price_paths=frozenset(price_paths),
    )


def _decimal(value: Any, code: str) -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise PriceParentError(code) from exc


def _text(value: Decimal) -> str:
    rendered = format(value.normalize(), "f")
    return "0" if rendered in {"", "-0"} else rendered


def _utc_text(timestamp_ms: int) -> str:
    value = datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc)
    return value.isoformat(timespec="seconds").replace("+00:00", "Z")


class OptAPriceParentIndex:
    """Resolve immutable C1 source links to exact manifest-verified OPT-A rows."""

    def __init__(self, verified: VerifiedOptARelease):
        self.verified = verified
        self._loaded_source_path: str | None = None
        self._rows: dict[int, dict[str, str]] = {}

    def _load_rows(self, source_path: str) -> None:
        if source_path == self._loaded_source_path:
            return
        if source_path not in self.verified.price_paths:
            raise PriceParentError(f"C1_SOURCE_PATH_NOT_MANIFEST_BOUND:{source_path}")
        path = self.verified.root / "files" / Path(*PurePosixPath(source_path).parts)
        rows: dict[int, dict[str, str]] = {}
        with path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            if reader.fieldnames != _CSV_COLUMNS:
                raise PriceParentError(f"OPT_A_PRICE_SCHEMA_MISMATCH:{source_path}")
            previous = -1
            for row in reader:
                try:
                    timestamp_ms = int(row["timestamp"])
                except (TypeError, ValueError) as exc:
                    raise PriceParentError(f"INVALID_OPT_A_TIMESTAMP:{source_path}") from exc
                if timestamp_ms <= previous or timestamp_ms in rows:
                    raise PriceParentError(f"NON_MONOTONIC_OPT_A_PRICE_FILE:{source_path}")
                previous = timestamp_ms
                rows[timestamp_ms] = row
        self._loaded_source_path = source_path
        self._rows = rows

    def join(self, record: Mapping[str, Any], *, c1_release_id: str, c1_manifest_id: str) -> dict[str, Any]:
        role = self.verified.binding.role
        required = {
            "schema",
            "record_id",
            "formula_registry_id",
            "authority_state",
            "role",
            "parent_release_id",
            "parent_manifest_id",
            "parent_manifest_sha256",
            "instrument",
            "clock",
            "price_side",
            "timestamp_ms",
            "source_path",
            "source_bar_id",
            "measurements",
            "categorical",
            "null_reasons",
        }
        missing = sorted(required - set(record))
        if missing:
            raise PriceParentError(f"ACTUAL_C1_FIELD_MISSING:{','.join(missing)}")
        if record["schema"] != "ovc-c1-bar-primitives/v0.1":
            raise PriceParentError("WRONG_ACTUAL_C1_SCHEMA")
        if record["formula_registry_id"] != "C1.FORMULAS.v0.1":
            raise PriceParentError("WRONG_C1_FORMULA_REGISTRY")
        if record["authority_state"] != "CANDIDATE_LOCAL_ONLY":
            raise PriceParentError("IMMUTABLE_C1_RECORD_STATE_MISMATCH")
        if record["role"] != role:
            raise PriceParentError("C1_OPT_A_ROLE_MISMATCH")
        if record["parent_release_id"] != self.verified.binding.release_id:
            raise PriceParentError("C1_OPT_A_RELEASE_MISMATCH")
        if record["parent_manifest_id"] != self.verified.binding.manifest_id:
            raise PriceParentError("C1_OPT_A_MANIFEST_MISMATCH")
        if record["parent_manifest_sha256"] != self.verified.binding.manifest_sha256:
            raise PriceParentError("C1_OPT_A_MANIFEST_SHA256_MISMATCH")
        if record["instrument"] != "GBPUSD":
            raise PriceParentError("WRONG_INSTRUMENT")
        clock = str(record["clock"])
        side = str(record["price_side"])
        if (clock, side) not in _PRICE_PATH_PREFIXES:
            raise PriceParentError("WRONG_PRICE_SCOPE")
        source_path = str(record["source_path"])
        if not source_path.startswith(_PRICE_PATH_PREFIXES[(clock, side)]):
            raise PriceParentError("C1_SOURCE_PATH_SCOPE_MISMATCH")
        timestamp_ms = int(record["timestamp_ms"])
        expected_bar_id = "opt-a:" + hashlib.sha256(
            f"{self.verified.binding.release_id}|{source_path}|{timestamp_ms}".encode()
        ).hexdigest()
        if record["source_bar_id"] != expected_bar_id:
            raise PriceParentError("OPT_A_SOURCE_BAR_ID_MISMATCH")

        self._load_rows(source_path)
        row = self._rows.get(timestamp_ms)
        if row is None:
            raise PriceParentError("OPT_A_PRICE_ROW_NOT_FOUND")
        prices = {name: _decimal(row[name], f"INVALID_OPT_A_{name.upper()}") for name in ("open", "high", "low", "close")}
        if prices["high"] < max(prices["open"], prices["close"]) or prices["low"] > min(prices["open"], prices["close"]):
            raise PriceParentError("INVALID_OPT_A_OHLC_ORDER")

        measurements = record["measurements"]
        categorical = record["categorical"]
        if not isinstance(measurements, Mapping) or len(measurements) != 17:
            raise PriceParentError("ACTUAL_C1_MEASUREMENT_CARDINALITY")
        if not isinstance(categorical, Mapping) or set(categorical) != {"direction"}:
            raise PriceParentError("ACTUAL_C1_CATEGORICAL_CARDINALITY")
        expected_current = {
            "range_abs": prices["high"] - prices["low"],
            "body_signed": prices["close"] - prices["open"],
            "body_abs": abs(prices["close"] - prices["open"]),
            "upper_wick_abs": prices["high"] - max(prices["open"], prices["close"]),
            "lower_wick_abs": min(prices["open"], prices["close"]) - prices["low"],
        }
        for field, expected in expected_current.items():
            if measurements.get(field) != _text(expected):
                raise PriceParentError(f"C1_PRICE_PRIMITIVE_MISMATCH:{field}")
        direction = "UP" if prices["close"] > prices["open"] else "DOWN" if prices["close"] < prices["open"] else "FLAT"
        if categorical.get("direction") != direction:
            raise PriceParentError("C1_DIRECTION_MISMATCH")

        open_time = _utc_text(timestamp_ms)
        close_time = _utc_text(timestamp_ms + _CLOCK_MS[clock])
        return {
            "c1_record_id": record["record_id"],
            "c1_release_id": c1_release_id,
            "c1_manifest_id": c1_manifest_id,
            "opt_a_release_id": self.verified.binding.release_id,
            "opt_a_manifest_id": self.verified.binding.manifest_id,
            "opt_a_manifest_sha256": self.verified.binding.manifest_sha256,
            "role": role,
            "authority_state": f"ACTIVE_{role}",
            "instrument": "GBPUSD",
            "clock": clock,
            "side": side,
            "open_time": open_time,
            "close_time": close_time,
            "first_valid_time": close_time,
            "source_path": source_path,
            "source_bar_id": record["source_bar_id"],
            "measurements": dict(measurements),
            "categorical": dict(categorical),
            "null_reasons": dict(record["null_reasons"]),
            "quality_state": "EXACT_C1_AND_OPT_A_PARENT_VERIFIED",
            "prices": {key: _text(value) for key, value in prices.items()},
        }
