from __future__ import annotations

import csv
import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Iterable, Iterator


PROGRAMME_ID = "OVC-OPT-A-V2-IMPLEMENTATION-PLAN-0.2"
PROVIDER = "DUKASCOPY"
INSTRUMENT = "GBPUSD"
DOWNLOADER_VERSION = "dukascopy-node@1.46.4+ovc-wp4.1"
ORDERED_COLUMNS = ["timestamp", "open", "high", "low", "close", "volume"]
LOGICAL_TYPES = ["unix_ms", "decimal", "decimal", "decimal", "decimal", "decimal"]
ROLE_RELEASES = {
    "DISCOVERY": "OPT-A.GBPUSD.DISCOVERY.2021_2023.v2",
    "DEVELOPMENT": "OPT-A.GBPUSD.DEVELOPMENT.2024.v2",
    "VALIDATION": "OPT-A.GBPUSD.VALIDATION.2025.v2",
}


class PopulationIntakeError(ValueError):
    """Raised when a provider object violates the frozen WP3 contract."""


@dataclass(frozen=True)
class SourceSpec:
    year_month: str
    interval_start: datetime
    interval_end: datetime
    research_role: str
    target_release_id: str
    native_timeframe: str
    price_side: str

    @property
    def intake_id(self) -> str:
        return (
            f"INTAKE.DUKASCOPY.GBPUSD.{self.native_timeframe}."
            f"{self.price_side}.{self.year_month}.v1"
        )

    @property
    def source_object_id(self) -> str:
        return (
            f"SRC.DUKASCOPY.GBPUSD.{self.native_timeframe}."
            f"{self.price_side}.{self.year_month}.v1"
        )

    @property
    def relative_csv_path(self) -> Path:
        return Path(
            "source",
            self.research_role.lower(),
            self.native_timeframe.lower(),
            self.price_side.lower(),
            f"GBPUSD_{self.native_timeframe}_{self.price_side}_{self.year_month}_UTC.csv",
        )

    @property
    def relative_intake_record_path(self) -> Path:
        return Path("records", "intake", f"{self.intake_id}.json")

    @property
    def relative_identity_path(self) -> Path:
        return Path("records", "source_identity", f"{self.source_object_id}.json")


def _utc_iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_year_month(year_month: str) -> tuple[int, int]:
    try:
        year_text, month_text = year_month.split("-", 1)
        year, month = int(year_text), int(month_text)
    except (ValueError, TypeError) as exc:
        raise PopulationIntakeError(f"invalid year-month: {year_month!r}") from exc
    if year not in range(2021, 2026) or month not in range(1, 13):
        raise PopulationIntakeError(f"year-month outside WP4 population: {year_month}")
    return year, month


def _month_bounds(year_month: str) -> tuple[datetime, datetime]:
    year, month = _parse_year_month(year_month)
    start = datetime(year, month, 1, tzinfo=timezone.utc)
    if month == 12:
        end = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
    else:
        end = datetime(year, month + 1, 1, tzinfo=timezone.utc)
    return start, end


def role_for_month(year_month: str) -> str:
    year, _ = _parse_year_month(year_month)
    if year <= 2023:
        return "DISCOVERY"
    if year == 2024:
        return "DEVELOPMENT"
    return "VALIDATION"


def source_specs_for_month(year_month: str) -> tuple[SourceSpec, ...]:
    start, end = _month_bounds(year_month)
    role = role_for_month(year_month)
    return tuple(
        SourceSpec(
            year_month=year_month,
            interval_start=start,
            interval_end=end,
            research_role=role,
            target_release_id=ROLE_RELEASES[role],
            native_timeframe=timeframe,
            price_side=side,
        )
        for timeframe in ("M1", "H1")
        for side in ("BID", "ASK")
    )


def iter_population_months() -> Iterator[str]:
    for year in range(2021, 2026):
        for month in range(1, 13):
            yield f"{year:04d}-{month:02d}"


def build_population_plan() -> dict[str, object]:
    months = list(iter_population_months())
    objects = [spec for month in months for spec in source_specs_for_month(month)]
    return {
        "schema": "ovc-opt-a-provider-population-plan/v1",
        "programme_id": PROGRAMME_ID,
        "provider": PROVIDER,
        "instrument_id": INSTRUMENT,
        "interval_start": "2021-01-01T00:00:00Z",
        "interval_end": "2026-01-01T00:00:00Z",
        "month_count": len(months),
        "source_object_count": len(objects),
        "months": months,
        "required_families": ["M1_BID", "M1_ASK", "H1_BID", "H1_ASK"],
        "role_counts": {
            "DISCOVERY": 36 * 4,
            "DEVELOPMENT": 12 * 4,
            "VALIDATION": 12 * 4,
        },
        "authority": {
            "market": "NONE",
            "release_parent": "DENIED_UNTIL_FREEZE",
            "selector_input": "DENIED",
            "validation_consumption": "LOCKED_UNCONSUMED",
        },
    }


def _canonical_json_sha256(document: object) -> str:
    payload = json.dumps(document, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def schema_fingerprint() -> str:
    return _canonical_json_sha256(
        {
            "ordered_columns": ORDERED_COLUMNS,
            "logical_types": LOGICAL_TYPES,
            "timestamp_unit": "unix_ms",
            "timezone": "UTC",
            "decimal_authority": "base10_text",
            "volume_field": "volume",
            "volume_unit": "units",
            "missing_value": "empty",
            "parser_contract": "ovc-opt-a-provider-csv-parser/v1",
        }
    )


def request_parameters_sha256(spec: SourceSpec) -> str:
    return _canonical_json_sha256(
        {
            "provider": PROVIDER,
            "instrument": "gbpusd",
            "timeframe": spec.native_timeframe.lower(),
            "price_type": spec.price_side.lower(),
            "from": _utc_iso(spec.interval_start),
            "to": _utc_iso(spec.interval_end),
            "utc_offset": 0,
            "volumes": True,
            "volume_units": "units",
            "ignore_flats": True,
            "downloader_version": DOWNLOADER_VERSION,
        }
    )


def _decimal(value: str, *, row_number: int, field: str) -> Decimal:
    try:
        result = Decimal(value)
    except InvalidOperation as exc:
        raise PopulationIntakeError(
            f"row {row_number}: {field} is not an exact decimal: {value!r}"
        ) from exc
    if not result.is_finite():
        raise PopulationIntakeError(f"row {row_number}: {field} must be finite")
    return result


def audit_provider_csv(path: Path, spec: SourceSpec) -> dict[str, object]:
    if not path.is_file():
        raise PopulationIntakeError(f"provider CSV is missing: {path}")
    raw = path.read_bytes()
    if not raw:
        raise PopulationIntakeError(f"provider CSV is empty: {path}")

    row_count = 0
    first_timestamp: datetime | None = None
    last_timestamp: datetime | None = None
    previous_ms: int | None = None
    step_ms = 60_000 if spec.native_timeframe == "M1" else 3_600_000

    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != ORDERED_COLUMNS:
            raise PopulationIntakeError(
                f"unexpected ordered columns for {spec.source_object_id}: {reader.fieldnames!r}"
            )
        for row_number, row in enumerate(reader, start=2):
            row_count += 1
            try:
                timestamp_ms = int(row["timestamp"])
            except (TypeError, ValueError) as exc:
                raise PopulationIntakeError(
                    f"row {row_number}: timestamp is not Unix milliseconds"
                ) from exc
            if timestamp_ms % step_ms:
                raise PopulationIntakeError(
                    f"row {row_number}: timestamp is not aligned to {spec.native_timeframe}"
                )
            if previous_ms is not None and timestamp_ms <= previous_ms:
                raise PopulationIntakeError(
                    f"row {row_number}: timestamps are duplicate or non-monotonic"
                )
            observed = datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc)
            if not (spec.interval_start <= observed < spec.interval_end):
                raise PopulationIntakeError(
                    f"row {row_number}: timestamp outside monthly partition: {_utc_iso(observed)}"
                )
            open_price = _decimal(row["open"], row_number=row_number, field="open")
            high = _decimal(row["high"], row_number=row_number, field="high")
            low = _decimal(row["low"], row_number=row_number, field="low")
            close = _decimal(row["close"], row_number=row_number, field="close")
            volume = _decimal(row["volume"], row_number=row_number, field="volume")
            if min(open_price, high, low, close) <= 0:
                raise PopulationIntakeError(f"row {row_number}: prices must be positive")
            if high < max(open_price, low, close) or low > min(open_price, high, close):
                raise PopulationIntakeError(f"row {row_number}: invalid OHLC ordering")
            if volume < 0:
                raise PopulationIntakeError(f"row {row_number}: volume must be non-negative")
            first_timestamp = first_timestamp or observed
            last_timestamp = observed
            previous_ms = timestamp_ms

    if row_count == 0:
        raise PopulationIntakeError(f"provider CSV has no accepted rows: {path}")
    assert first_timestamp is not None and last_timestamp is not None
    return {
        "sha256": hashlib.sha256(raw).hexdigest(),
        "size_bytes": len(raw),
        "row_count": row_count,
        "first_timestamp": _utc_iso(first_timestamp),
        "last_timestamp": _utc_iso(last_timestamp),
        "ordered_columns": ORDERED_COLUMNS,
        "logical_types": LOGICAL_TYPES,
        "volume_unit": "units",
        "schema_fingerprint": schema_fingerprint(),
    }


def build_intake_record(spec: SourceSpec, audit: dict[str, object]) -> dict[str, object]:
    return {
        "schema": "ovc-opt-a-provider-intake-record/v2",
        "intake_id": spec.intake_id,
        "source_object_id": spec.source_object_id,
        "synthetic": False,
        "provider": PROVIDER,
        "instrument_id": INSTRUMENT,
        "native_timeframe": spec.native_timeframe,
        "price_side": spec.price_side,
        "research_role": spec.research_role,
        "target_release_id": spec.target_release_id,
        "partition": {
            "year_month": spec.year_month,
            "interval_start": _utc_iso(spec.interval_start),
            "interval_end": _utc_iso(spec.interval_end),
            "timezone": "UTC",
        },
        "request": {
            "provider_instrument": INSTRUMENT,
            "timeframe": spec.native_timeframe,
            "price_side": spec.price_side,
            "interval_start": _utc_iso(spec.interval_start),
            "interval_end": _utc_iso(spec.interval_end),
            "parameters_sha256": request_parameters_sha256(spec),
        },
        "response": {
            "status": 200,
            "content_type": "text/csv; charset=utf-8",
            "sha256": audit["sha256"],
            "size_bytes": audit["size_bytes"],
        },
        "parsed_object": {
            "row_count": audit["row_count"],
            "first_timestamp": audit["first_timestamp"],
            "last_timestamp": audit["last_timestamp"],
            "ordered_columns": audit["ordered_columns"],
            "logical_types": audit["logical_types"],
            "volume_unit": audit["volume_unit"],
        },
        "schema_fingerprint": audit["schema_fingerprint"],
        "downloader_version": DOWNLOADER_VERSION,
        "qa_state": "PASS",
        "availability_state": "LOCAL_ONLY",
        "disposition": "ACCEPTED_WORKSPACE_INPUT",
        "reason_codes": [],
        "authority": {
            "market": "NONE",
            "release_parent": "DENIED_UNTIL_FREEZE",
            "discovery_seed": "DENIED",
            "selector_input": "DENIED",
        },
    }


def build_source_identity(spec: SourceSpec, audit: dict[str, object]) -> dict[str, object]:
    return {
        "schema": "ovc-opt-a-source-object-identity/v2",
        "source_object_id": spec.source_object_id,
        "synthetic": False,
        "provider": PROVIDER,
        "instrument_id": INSTRUMENT,
        "native_timeframe": spec.native_timeframe,
        "price_side": spec.price_side,
        "research_role": spec.research_role,
        "target_release_id": spec.target_release_id,
        "partition_start": _utc_iso(spec.interval_start),
        "partition_end": _utc_iso(spec.interval_end),
        "timezone": "UTC",
        "intake_record_id": spec.intake_id,
        "response_sha256": audit["sha256"],
        "size_bytes": audit["size_bytes"],
        "row_count": audit["row_count"],
        "first_timestamp": audit["first_timestamp"],
        "last_timestamp": audit["last_timestamp"],
        "schema_fingerprint": audit["schema_fingerprint"],
        "identity_version": 1,
        "supersedes_source_object_id": None,
        "quality_state": "PASS",
        "authority": {
            "market": "NONE",
            "workspace_input": "ELIGIBLE",
            "release_parent": "DENIED_UNTIL_FREEZE",
            "selector_input": "DENIED",
        },
    }


def write_json(path: Path, document: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def audit_month_workspace(workspace_root: Path, year_month: str) -> dict[str, object]:
    records: list[dict[str, object]] = []
    identities: list[dict[str, object]] = []
    for spec in source_specs_for_month(year_month):
        csv_path = workspace_root / spec.relative_csv_path
        audit = audit_provider_csv(csv_path, spec)
        intake = build_intake_record(spec, audit)
        identity = build_source_identity(spec, audit)
        write_json(workspace_root / spec.relative_intake_record_path, intake)
        write_json(workspace_root / spec.relative_identity_path, identity)
        records.append(intake)
        identities.append(identity)

    summary = {
        "schema": "ovc-opt-a-provider-month-intake-summary/v1",
        "programme_id": PROGRAMME_ID,
        "year_month": year_month,
        "research_role": role_for_month(year_month),
        "source_object_count": len(identities),
        "row_count": sum(int(item["row_count"]) for item in identities),
        "size_bytes": sum(int(item["size_bytes"]) for item in identities),
        "source_objects": [item["source_object_id"] for item in identities],
        "qa_state": "PASS",
        "market_authority": "NONE",
        "release_parent": "DENIED_UNTIL_FREEZE",
        "selector_input": "DENIED",
        "validation_consumption": (
            "LOCKED_UNCONSUMED" if role_for_month(year_month) == "VALIDATION" else "NOT_APPLICABLE"
        ),
    }
    write_json(workspace_root / "summaries" / f"{year_month}.json", summary)
    return summary


def aggregate_month_summaries(paths: Iterable[Path]) -> dict[str, object]:
    summaries = [json.loads(path.read_text(encoding="utf-8")) for path in sorted(paths)]
    months = [item["year_month"] for item in summaries]
    expected = list(iter_population_months())
    if months != expected:
        raise PopulationIntakeError(
            f"population summary months do not match exact plan: expected {len(expected)}, got {len(months)}"
        )
    if any(item["qa_state"] != "PASS" for item in summaries):
        raise PopulationIntakeError("one or more monthly intake summaries are not PASS")
    return {
        "schema": "ovc-opt-a-provider-population-intake-summary/v1",
        "programme_id": PROGRAMME_ID,
        "provider": PROVIDER,
        "instrument_id": INSTRUMENT,
        "interval_start": "2021-01-01T00:00:00Z",
        "interval_end": "2026-01-01T00:00:00Z",
        "month_count": len(summaries),
        "source_object_count": sum(int(item["source_object_count"]) for item in summaries),
        "row_count": sum(int(item["row_count"]) for item in summaries),
        "size_bytes": sum(int(item["size_bytes"]) for item in summaries),
        "monthly_summaries": summaries,
        "qa_state": "PASS",
        "market_authority": "NONE",
        "release_parent": "DENIED_UNTIL_FREEZE",
        "selector_activation": "NONE",
        "r2_mutation": "NONE",
        "validation_consumption": "LOCKED_UNCONSUMED",
    }
