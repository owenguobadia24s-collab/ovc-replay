"""Fresh synthetic source construction and OPT-A fixture adapter for FSR v0.1.

This module is deliberately noncanonical.  It creates deterministic provider-like
GBP/USD fixture bytes, validates them against the frozen OPT-A CSV contract,
derives complete clocks without repairing gaps, and emits synthetic handoff
records suitable for the existing C1 fixture path.
"""
from __future__ import annotations

import csv
import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from typing import Iterable

from .provider_population import SourceSpec, audit_provider_csv
from .role_workspace import Bar, _aggregate_exact

UTC = timezone.utc
PROGRAMME_ID = "OVC-FULL-STACK-SYNTHETIC-FRESH-DISCOVERY-REHEARSAL-v0.1"
FIXTURE_NAMESPACE = "FSR.FRESH.GBPUSD.20230605.v1"
START = datetime(2023, 6, 5, tzinfo=UTC)
END = datetime(2023, 6, 6, tzinfo=UTC)
TICK = Decimal("0.00001")
GAP_START_INDEX = 13 * 60 + 17
GAP_END_INDEX = 13 * 60 + 22
GENERATOR_SPEC_REL = Path("fixtures/full_stack_synthetic_fresh_discovery/v0_1/GENERATOR_SPEC.json")
HIDDEN_LEDGER_REL = Path("fixtures/full_stack_synthetic_fresh_discovery/v0_1/hidden/HIDDEN_CONSTRUCTION_LEDGER.json")
EXPECTED_SOURCE_SHA256 = {
    "GBPUSD_M1_BID_2023-06_FSR.csv": "7da5aa942df5c65f756c6ea159a31bea06847ded14ba809e113f18cb7837cbe7",
    "GBPUSD_M1_ASK_2023-06_FSR.csv": "32db88aa84e6853fc389976ccfe13c76223b7f1e90530151353f26f469fccdf4",
    "GBPUSD_H1_BID_2023-06_FSR.csv": "35cf6a6a8b6ad7780c69214180635dc2ba4c52c4c3b37035698f4a33eb756a14",
    "GBPUSD_H1_ASK_2023-06_FSR.csv": "f920f809e7dff7e268c80c929c9c0382e1bfb3e35e7ad36c0c9145a394c3fccd",
}


class FSRFixtureError(ValueError):
    pass


@dataclass(frozen=True)
class GeneratedSource:
    name: str
    native_timeframe: str
    price_side: str
    rows: tuple[Bar, ...]


def _delta_ticks(index: int) -> int:
    if index < 120:
        return (0, 1, 0, -1, 0, 0)[index % 6]
    if index < 240:
        if index < 180:
            return (1, 0, -1, 0)[index % 4]
        return (0, 0, 1, -1, 0, 0)[index % 6]
    if index < 360:
        return (1, 2, 1, 1, 2, 0)[index % 6]
    if index < 420:
        return (4, 5, 3, 4, 6, 3)[index % 6]
    if index < 540:
        return (-2, -2, -1, -3, -1, 0)[index % 6]
    if index < 660:
        return (2, 2, -2, -2, 1, -1)[index % 6]
    if index < 780:
        return (2, 1, -2, -1, 2, -2, 1, -1)[index % 8]
    if index < 900:
        return (-2, -2, -1, -3, -1, 1)[index % 6]
    if index < 1020:
        if index - 900 < 28:
            return (-2, -2, -1, -3, -1, 0)[index % 6]
        return (2, 3, 1, 2, 2, 1)[index % 6]
    if index < 1140:
        return (3, -3, 2, -2, 3, -3, 1, -1)[index % 8]
    if index < 1260:
        return (2, 3, 1, 2, 4, 0)[index % 6]
    if index < 1380:
        return (1, -1, 1, 0, -1, 0, 2, -2)[index % 8]
    return (-3, -2, -4, 1, -3, -1, 2, -4)[index % 8]


def _wiggle_ticks(index: int) -> int:
    return (2, 2, 1, 2, 1, 1, 2, 1)[index % 8]


def _spread_ticks(index: int) -> int:
    return (12, 12, 13, 13, 14, 13, 12, 13)[index % 8]


def _volume(index: int) -> Decimal:
    value = (10, 12, 14, 16, 15, 13, 11, 17)[index % 8]
    if 360 <= index < 420:
        value += 20
    if 1140 <= index < 1260:
        value += 10
    return Decimal(value)


def _full_bid_path() -> tuple[Bar, ...]:
    price = Decimal("1.26800")
    rows: list[Bar] = []
    for index in range(24 * 60):
        open_price = price
        close = open_price + TICK * _delta_ticks(index)
        wiggle = TICK * _wiggle_ticks(index)
        timestamp_ms = int((START + timedelta(minutes=index)).timestamp() * 1000)
        rows.append(
            Bar(
                timestamp_ms=timestamp_ms,
                open=open_price,
                high=max(open_price, close) + wiggle,
                low=min(open_price, close) - wiggle,
                close=close,
                volume=_volume(index),
            )
        )
        price = close
    return tuple(rows)


def _ask_from_bid(row: Bar, index: int) -> Bar:
    spread = TICK * _spread_ticks(index)
    return Bar(
        timestamp_ms=row.timestamp_ms,
        open=row.open + spread,
        high=row.high + spread,
        low=row.low + spread,
        close=row.close + spread,
        volume=row.volume,
    )


def generate_sources() -> tuple[GeneratedSource, ...]:
    full_bid = _full_bid_path()
    full_ask = tuple(_ask_from_bid(row, index) for index, row in enumerate(full_bid))
    m1_bid = tuple(row for index, row in enumerate(full_bid) if not GAP_START_INDEX <= index < GAP_END_INDEX)
    m1_ask = tuple(row for index, row in enumerate(full_ask) if not GAP_START_INDEX <= index < GAP_END_INDEX)
    native_h1_bid = tuple(_aggregate_complete(full_bid, 60))
    native_h1_ask = tuple(_aggregate_complete(full_ask, 60))
    return (
        GeneratedSource("GBPUSD_M1_BID_2023-06_FSR.csv", "M1", "BID", m1_bid),
        GeneratedSource("GBPUSD_M1_ASK_2023-06_FSR.csv", "M1", "ASK", m1_ask),
        GeneratedSource("GBPUSD_H1_BID_2023-06_FSR.csv", "H1", "BID", native_h1_bid),
        GeneratedSource("GBPUSD_H1_ASK_2023-06_FSR.csv", "H1", "ASK", native_h1_ask),
    )


def _aggregate_complete(rows: Iterable[Bar], minutes: int) -> list[Bar]:
    source = list(rows)
    output: list[Bar] = []
    for offset in range(0, len(source), minutes):
        members = source[offset : offset + minutes]
        if len(members) != minutes:
            continue
        output.append(
            Bar(
                timestamp_ms=members[0].timestamp_ms,
                open=members[0].open,
                high=max(item.high for item in members),
                low=min(item.low for item in members),
                close=members[-1].close,
                volume=sum((item.volume for item in members), Decimal("0")),
            )
        )
    return output


def _csv_bytes(rows: Iterable[Bar]) -> bytes:
    import io

    handle = io.StringIO(newline="")
    writer = csv.DictWriter(
        handle,
        fieldnames=["timestamp", "open", "high", "low", "close", "volume"],
        lineterminator="\n",
    )
    writer.writeheader()
    for row in rows:
        writer.writerow(row.as_row())
    return handle.getvalue().encode("utf-8")


def write_exact_source_observations(output_root: Path) -> dict[str, object]:
    source_root = output_root / "source"
    inventory: list[dict[str, object]] = []
    for source in generate_sources():
        path = source_root / source.native_timeframe / source.price_side / source.name
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = _csv_bytes(source.rows)
        path.write_bytes(payload)
        observed_sha = hashlib.sha256(payload).hexdigest()
        expected_sha = EXPECTED_SOURCE_SHA256[source.name]
        if observed_sha != expected_sha:
            raise FSRFixtureError(f"NONDETERMINISTIC_SOURCE:{source.name}:{observed_sha}:{expected_sha}")
        inventory.append(
            {
                "name": source.name,
                "path": path.relative_to(output_root).as_posix(),
                "native_timeframe": source.native_timeframe,
                "price_side": source.price_side,
                "row_count": len(source.rows),
                "size_bytes": len(payload),
                "sha256": observed_sha,
                "synthetic": True,
                "market_authority": "NONE",
            }
        )
    return {"objects": inventory, "source_root": source_root.as_posix()}


def _source_spec(timeframe: str, side: str) -> SourceSpec:
    return SourceSpec(
        year_month="2023-06",
        interval_start=datetime(2023, 6, 1, tzinfo=UTC),
        interval_end=datetime(2023, 7, 1, tzinfo=UTC),
        research_role="DISCOVERY",
        target_release_id="OPT-A.GBPUSD.DISCOVERY.2021_2023.v2",
        native_timeframe=timeframe,
        price_side=side,
    )


def build_opt_a_fixture(output_root: Path, *, repo_root: Path) -> dict[str, object]:
    generated = write_exact_source_observations(output_root)
    observations: list[dict[str, object]] = []
    quarantine: list[dict[str, object]] = []
    source_objects: list[dict[str, object]] = []
    source_root = output_root / "source"
    for source in generate_sources():
        path = source_root / source.native_timeframe / source.price_side / source.name
        audit = audit_provider_csv(path, _source_spec(source.native_timeframe, source.price_side))
        source_id = f"FSR.SOURCE.{source.native_timeframe}.{source.price_side}.{audit['sha256'][:20]}"
        source_objects.append(
            {
                "source_object_id": source_id,
                "native_timeframe": source.native_timeframe,
                "price_side": source.price_side,
                "synthetic": True,
                "market_authority": "NONE",
                "audit": audit,
            }
        )
        if source.native_timeframe == "H1":
            for row in source.rows:
                observations.append(_observation_record(row, "H1_PROVIDER_NATIVE", source.price_side, source_id, 60))
            continue
        m1_rows = list(source.rows)
        for row in m1_rows:
            observations.append(_observation_record(row, "M1", source.price_side, source_id, 1))
        for clock, minutes in (("15M", 15), ("H1_M1_DERIVED", 60), ("2H_A_L", 120)):
            derived, rejected = _aggregate_exact(m1_rows, minutes=minutes)
            for row in derived:
                observations.append(_observation_record(row, clock, source.price_side, source_id, minutes))
            for item in rejected:
                quarantine.append(
                    {
                        **item,
                        "clock": clock,
                        "price_side": source.price_side,
                        "source_object_id": source_id,
                        "authority": "NONE",
                        "repair": "DENIED",
                    }
                )
    generator_bytes = (repo_root / GENERATOR_SPEC_REL).read_bytes()
    hidden_bytes = (repo_root / HIDDEN_LEDGER_REL).read_bytes()
    fixture_identity_body = {
        "generator_spec_sha256": hashlib.sha256(generator_bytes).hexdigest(),
        "hidden_construction_ledger_sha256": hashlib.sha256(hidden_bytes).hexdigest(),
        "source_sha256": {item["name"]: item["sha256"] for item in generated["objects"]},
    }
    fixture_id = "FSR.FIXTURE." + hashlib.sha256(
        json.dumps(fixture_identity_body, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()[:24]
    manifest_id = "FSR.SOURCE-MANIFEST." + fixture_id.rsplit(".", 1)[-1]
    for record in observations:
        record["fixture_id"] = fixture_id
        record["manifest_id"] = manifest_id
    body = {
        "schema": "ovc-fsr-opt-a-fixture-manifest/v1",
        "programme_id": PROGRAMME_ID,
        "fixture_id": fixture_id,
        "manifest_id": manifest_id,
        "instrument_id": "GBPUSD",
        "interval_start": "2023-06-05T00:00:00Z",
        "interval_end": "2023-06-06T00:00:00Z",
        "source_inventory": generated["objects"],
        "source_objects": source_objects,
        "observations": observations,
        "quarantine": quarantine,
        "gap": {"start": "2023-06-05T13:17:00Z", "end": "2023-06-05T13:22:00Z", "minutes": 5},
        "hidden_construction_ledger_sha256": fixture_identity_body["hidden_construction_ledger_sha256"],
        "generator_spec_sha256": fixture_identity_body["generator_spec_sha256"],
        "MARKET_EVIDENCE": False,
        "CANONICAL": False,
        "PROMOTABLE": False,
        "SYNTHETIC": True,
        "authority": {
            "provider_intake": "NONE",
            "release": "NONE",
            "selector": "NONE",
            "publication": "NONE",
            "validation": "LOCKED_UNCONSUMED",
            "probability_risk_exposure_execution": "NONE",
        },
    }
    body["manifest_sha256"] = hashlib.sha256(
        json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return body


def _observation_record(row: Bar, clock: str, side: str, source_id: str, minutes: int) -> dict[str, object]:
    open_time = datetime.fromtimestamp(row.timestamp_ms / 1000, tz=UTC)
    close_time = open_time + timedelta(minutes=minutes)
    bar_identity = {
        "fixture_namespace": FIXTURE_NAMESPACE,
        "clock": clock,
        "side": side,
        "open_time": open_time.isoformat().replace("+00:00", "Z"),
        "source_object_id": source_id,
    }
    source_bar_id = "FSR.BAR." + hashlib.sha256(
        json.dumps(bar_identity, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()[:24]
    return {
        "source_bar_id": source_bar_id,
        "source_object_id": source_id,
        "clock_id": clock,
        "price_side": side,
        "open_time": open_time.isoformat().replace("+00:00", "Z"),
        "close_time": close_time.isoformat().replace("+00:00", "Z"),
        "first_valid_time": close_time.isoformat().replace("+00:00", "Z"),
        "open": format(row.open, "f"),
        "high": format(row.high, "f"),
        "low": format(row.low, "f"),
        "close": format(row.close, "f"),
        "volume": format(row.volume, "f"),
        "quality_state": "COMPLETE",
        "synthetic": True,
        "authority": "FIXTURE_ONLY",
    }


def c1_handoff_records(opt_a_manifest: dict[str, object]) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    for item in opt_a_manifest["observations"]:
        if item["clock_id"] not in {"15M", "2H_A_L"}:
            continue
        records.append(
            {
                "release_id": "OPT-A.GBPUSD.DISCOVERY.2021_2023.v2",
                "manifest_id": opt_a_manifest["manifest_id"],
                "research_role": "DISCOVERY",
                "instrument_id": "GBPUSD",
                "clock_id": item["clock_id"],
                "price_side": item["price_side"],
                "source_bar_id": item["source_bar_id"],
                "open_time": item["open_time"],
                "close_time": item["close_time"],
                "first_valid_time": item["first_valid_time"],
                "open": item["open"],
                "high": item["high"],
                "low": item["low"],
                "close": item["close"],
                "price_increment": "0.00001",
                "admissibility": "HANDOFF_ELIGIBLE",
                "quality_state": "COMPLETE",
                "synthetic": True,
                "selector_state": "NONE",
                "authority_state": "FIXTURE_ONLY",
                "validation_consumption_state": "DENIED",
                "parent_source_object_ids": [item["source_object_id"]],
                "parent_m1_bar_ids": [],
            }
        )
    return records
