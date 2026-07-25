from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Iterable, Iterator

from .provider_population import (
    ORDERED_COLUMNS,
    ROLE_RELEASES,
    SourceSpec,
    audit_provider_csv,
    role_for_month,
    source_specs_for_month,
)

PROGRAMME_ID = "OVC-OPT-A-V2-IMPLEMENTATION-PLAN-0.2"
WORK_PACKET_ID = "WP5"
GATE_ID = "A2-G2"
ROLE_YEARS = {
    "DISCOVERY": {2021, 2022, 2023},
    "DEVELOPMENT": {2024},
    "VALIDATION": {2025},
}
DERIVED_CLOCKS = {"15M": 15, "H1_M1_DERIVED": 60, "2H_A_L": 120}


class RoleWorkspaceError(ValueError):
    """Raised when accepted intake evidence cannot enter a lawful role workspace."""


@dataclass(frozen=True)
class Bar:
    timestamp_ms: int
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal

    def as_row(self) -> dict[str, str]:
        return {
            "timestamp": str(self.timestamp_ms),
            "open": format(self.open, "f"),
            "high": format(self.high, "f"),
            "low": format(self.low, "f"),
            "close": format(self.close, "f"),
            "volume": format(self.volume, "f"),
        }


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_json(document: object) -> str:
    return json.dumps(document, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _canonical_json_sha256(document: object) -> str:
    return hashlib.sha256(_canonical_json(document).encode("utf-8")).hexdigest()


def _load_json(path: Path) -> dict[str, object]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RoleWorkspaceError(f"invalid JSON evidence: {path}") from exc
    if not isinstance(value, dict):
        raise RoleWorkspaceError(f"JSON evidence must be an object: {path}")
    return value


def _read_bars(path: Path) -> Iterator[Bar]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != ORDERED_COLUMNS:
            raise RoleWorkspaceError(f"unexpected provider columns in {path}")
        for row in reader:
            yield Bar(
                timestamp_ms=int(row["timestamp"]),
                open=Decimal(row["open"]),
                high=Decimal(row["high"]),
                low=Decimal(row["low"]),
                close=Decimal(row["close"]),
                volume=Decimal(row["volume"]),
            )


def _aggregate_exact(
    bars: Iterable[Bar], *, minutes: int
) -> tuple[list[Bar], list[dict[str, object]]]:
    step_ms = minutes * 60_000
    expected = minutes
    groups: dict[int, list[Bar]] = defaultdict(list)
    for bar in bars:
        bucket = (bar.timestamp_ms // step_ms) * step_ms
        groups[bucket].append(bar)

    output: list[Bar] = []
    quarantined: list[dict[str, object]] = []
    for bucket in sorted(groups):
        members = groups[bucket]
        exact_timestamps = [bucket + offset * 60_000 for offset in range(expected)]
        observed_timestamps = [item.timestamp_ms for item in members]
        if observed_timestamps != exact_timestamps:
            exact_set = set(exact_timestamps)
            observed_set = set(observed_timestamps)
            missing_timestamps = sorted(exact_set - observed_set)
            unexpected_timestamps = sorted(observed_set - exact_set)
            quarantined.append(
                {
                    "bucket_start": bucket,
                    "clock_minutes": minutes,
                    "expected_count": expected,
                    "observed_count": len(members),
                    "missing_timestamp_count": len(missing_timestamps),
                    "missing_timestamps_ms": missing_timestamps,
                    "unexpected_timestamp_count": len(unexpected_timestamps),
                    "unexpected_timestamps_ms": unexpected_timestamps,
                    "reason": "INCOMPLETE_OR_NONCONTIGUOUS_M1_BUCKET",
                }
            )
            continue
        output.append(
            Bar(
                timestamp_ms=bucket,
                open=members[0].open,
                high=max(item.high for item in members),
                low=min(item.low for item in members),
                close=members[-1].close,
                volume=sum((item.volume for item in members), Decimal("0")),
            )
        )
    return output, quarantined


def _portable_relative_path(path: Path, *, relative_to: Path) -> str:
    try:
        return path.resolve().relative_to(relative_to.resolve()).as_posix()
    except ValueError as exc:
        raise RoleWorkspaceError(
            f"workspace artifact path escapes its root: {path} not under {relative_to}"
        ) from exc


def _write_bars(
    path: Path, bars: Iterable[Bar], *, relative_to: Path
) -> dict[str, object]:
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    first_timestamp: int | None = None
    last_timestamp: int | None = None
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=ORDERED_COLUMNS, lineterminator="\n")
        writer.writeheader()
        for bar in bars:
            writer.writerow(bar.as_row())
            count += 1
            first_timestamp = bar.timestamp_ms if first_timestamp is None else first_timestamp
            last_timestamp = bar.timestamp_ms
    return {
        "path": _portable_relative_path(path, relative_to=relative_to),
        "row_count": count,
        "size_bytes": path.stat().st_size,
        "sha256": _sha256(path),
        "first_timestamp_ms": first_timestamp,
        "last_timestamp_ms": last_timestamp,
    }


def _find_source_csv(evidence_roots: Iterable[Path], spec: SourceSpec) -> Path:
    matches: list[Path] = []
    relative = spec.relative_csv_path
    for root in evidence_roots:
        direct = root / relative
        if direct.is_file():
            matches.append(direct)
        matches.extend(path for path in root.rglob(relative.name) if path.is_file())
    unique = sorted({path.resolve() for path in matches})
    if len(unique) != 1:
        raise RoleWorkspaceError(
            f"expected exactly one source CSV for {spec.source_object_id}; found {len(unique)}"
        )
    return unique[0]


def _validate_role_lock(role: str, *, allow_validation: bool) -> None:
    if role == "VALIDATION" and not allow_validation:
        raise RoleWorkspaceError("validation workspace is LOCKED_UNCONSUMED")


def _coverage_summary(
    observation_records: list[dict[str, object]],
    quarantine: list[dict[str, object]],
) -> dict[str, dict[str, dict[str, int]]]:
    accepted: Counter[tuple[str, str]] = Counter()
    for record in observation_records:
        accepted[(str(record["clock"]), str(record["price_side"]))] += int(
            record["row_count"]
        )
    rejected: Counter[tuple[str, str]] = Counter(
        (str(record["clock"]), str(record["price_side"])) for record in quarantine
    )
    summary: dict[str, dict[str, dict[str, int]]] = {}
    for clock in ("M1", *DERIVED_CLOCKS.keys()):
        summary[clock] = {}
        for side in ("BID", "ASK"):
            accepted_count = accepted[(clock, side)]
            quarantined_count = rejected[(clock, side)]
            candidate_count = accepted_count + quarantined_count
            summary[clock][side] = {
                "accepted_bucket_count": accepted_count,
                "quarantined_bucket_count": quarantined_count,
                "candidate_bucket_count": candidate_count,
                "acceptance_rate_ppm": (
                    accepted_count * 1_000_000 // candidate_count
                    if candidate_count
                    else 0
                ),
            }
    return summary


def build_role_workspace(
    *,
    evidence_roots: Iterable[Path],
    output_root: Path,
    role: str,
    allow_validation: bool = False,
) -> dict[str, object]:
    role = role.upper()
    if role not in ROLE_YEARS:
        raise RoleWorkspaceError(f"unknown role: {role}")
    _validate_role_lock(role, allow_validation=allow_validation)

    roots = tuple(Path(root) for root in evidence_roots)
    workspace = output_root / role.lower()
    if workspace.exists() and any(workspace.iterdir()):
        raise RoleWorkspaceError(f"workspace already exists and is not empty: {workspace}")
    workspace.mkdir(parents=True, exist_ok=True)

    source_records: list[dict[str, object]] = []
    observation_records: list[dict[str, object]] = []
    quarantine: list[dict[str, object]] = []

    for year in sorted(ROLE_YEARS[role]):
        for month in range(1, 13):
            year_month = f"{year:04d}-{month:02d}"
            if role_for_month(year_month) != role:
                raise RoleWorkspaceError(f"role allocation mismatch for {year_month}")
            for spec in source_specs_for_month(year_month):
                source_path = _find_source_csv(roots, spec)
                audit = audit_provider_csv(source_path, spec)
                source_records.append(
                    {
                        "source_object_id": spec.source_object_id,
                        "research_role": role,
                        "target_release_id": ROLE_RELEASES[role],
                        "native_timeframe": spec.native_timeframe,
                        "price_side": spec.price_side,
                        "source_path": spec.relative_csv_path.as_posix(),
                        "source_path_scope": "WP4_YEARLY_ARTIFACT_ROOT",
                        "source_sha256": _sha256(source_path),
                        "audit": audit,
                    }
                )

                if spec.native_timeframe != "M1":
                    continue
                m1_bars = list(_read_bars(source_path))
                native_copy = (
                    workspace / "observations" / "M1" / spec.price_side / source_path.name
                )
                observation_records.append(
                    {
                        "clock": "M1",
                        "price_side": spec.price_side,
                        "year_month": year_month,
                        **_write_bars(native_copy, m1_bars, relative_to=workspace),
                    }
                )
                for clock, minutes in DERIVED_CLOCKS.items():
                    derived, rejected = _aggregate_exact(m1_bars, minutes=minutes)
                    quarantine.extend(
                        {
                            **item,
                            "bucket_id": (
                                f"QBUCKET.{spec.source_object_id}.{clock}."
                                f"{item['bucket_start']}"
                            ),
                            "year_month": year_month,
                            "price_side": spec.price_side,
                            "clock": clock,
                            "source_object_id": spec.source_object_id,
                        }
                        for item in rejected
                    )
                    derived_name = (
                        f"GBPUSD_{clock}_{spec.price_side}_{year_month}_UTC.csv"
                    )
                    derived_path = (
                        workspace / "observations" / clock / spec.price_side / derived_name
                    )
                    observation_records.append(
                        {
                            "clock": clock,
                            "price_side": spec.price_side,
                            "year_month": year_month,
                            "source_object_id": spec.source_object_id,
                            **_write_bars(
                                derived_path, derived, relative_to=workspace
                            ),
                        }
                    )

    expected_source_objects = len(ROLE_YEARS[role]) * 12 * 4
    if len(source_records) != expected_source_objects:
        raise RoleWorkspaceError(
            f"source-object cardinality mismatch: {len(source_records)} != {expected_source_objects}"
        )

    reason_counts = Counter(str(item["reason"]) for item in quarantine)
    manifest = {
        "schema": "ovc-opt-a-role-workspace-manifest/v2",
        "programme_id": PROGRAMME_ID,
        "work_packet_id": WORK_PACKET_ID,
        "gate_id": GATE_ID,
        "role": role,
        "target_release_id": ROLE_RELEASES[role],
        "authority_state": "MUTABLE_WORKSPACE",
        "qa_state": "PASS" if not quarantine else "WARN",
        "validation_consumption": (
            "LOCKED_UNCONSUMED" if role == "VALIDATION" else "NOT_APPLICABLE"
        ),
        "source_object_count": len(source_records),
        "observation_object_count": len(observation_records),
        "quarantined_bucket_count": len(quarantine),
        "quarantine_reason_counts": dict(sorted(reason_counts.items())),
        "coverage": _coverage_summary(observation_records, quarantine),
        "source_objects": source_records,
        "observations": observation_records,
        "quarantine": quarantine,
        "authority": {
            "release_freeze": "DENIED",
            "r2_publication": "DENIED",
            "selector_activation": "DENIED",
            "opt_b_handoff": "DENIED",
            "market": "NONE",
        },
    }
    manifest["manifest_sha256"] = _canonical_json_sha256(manifest)
    manifest_path = workspace / "workspace-manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return manifest


def build_all_role_workspaces(
    *, evidence_roots: Iterable[Path], output_root: Path
) -> dict[str, object]:
    results = {
        role: build_role_workspace(
            evidence_roots=evidence_roots,
            output_root=output_root,
            role=role,
            allow_validation=(role == "VALIDATION"),
        )
        for role in ("DISCOVERY", "DEVELOPMENT", "VALIDATION")
    }
    report = {
        "schema": "ovc-opt-a-wp5-observation-construction-report/v2",
        "programme_id": PROGRAMME_ID,
        "work_packet_id": WORK_PACKET_ID,
        "gate_id": GATE_ID,
        "result": (
            "PASS"
            if all(item["qa_state"] in {"PASS", "WARN"} for item in results.values())
            else "BLOCK"
        ),
        "roles": {
            role: {
                "target_release_id": item["target_release_id"],
                "source_object_count": item["source_object_count"],
                "observation_object_count": item["observation_object_count"],
                "quarantined_bucket_count": item["quarantined_bucket_count"],
                "quarantine_reason_counts": item["quarantine_reason_counts"],
                "coverage": item["coverage"],
                "qa_state": item["qa_state"],
            }
            for role, item in results.items()
        },
        "authority": {
            "observation_construction": "COMPLETE_MUTABLE_ONLY",
            "release_freeze": "DENIED_PENDING_A2_G3",
            "r2_publication": "DENIED",
            "selector_activation": "DENIED",
            "validation_consumption": "LOCKED_UNCONSUMED",
            "market": "NONE",
        },
    }
    (output_root / "WP5_OBSERVATION_CONSTRUCTION_REPORT.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return report
