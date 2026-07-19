from __future__ import annotations

import argparse
from collections import Counter
import csv
from datetime import datetime
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ovc_opt_b import Bar, build_level_registry, reference_level_to_dict  # noqa: E402


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def verify_seal(seal_root: Path) -> dict[str, object]:
    manifest_path = seal_root / "OPT_A_SEAL_MANIFEST.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    expected_seal_hash = manifest.pop("seal_hash")
    canonical = json.dumps(manifest, sort_keys=True, separators=(",", ":"))
    actual_seal_hash = hashlib.sha256(canonical.encode()).hexdigest()
    if actual_seal_hash != expected_seal_hash:
        raise ValueError("OPT-A seal manifest hash mismatch")
    for artifact in manifest["artifacts"]:
        path = seal_root / artifact["path"]
        if not path.is_file() or sha256(path) != artifact["sha256"]:
            raise ValueError(f"OPT-A sealed artifact mismatch: {artifact['path']}")
    manifest["seal_hash"] = expected_seal_hash
    return manifest


def read_canonical_bars(path: Path) -> tuple[Bar, ...]:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    bars = tuple(
        Bar(
            bar_id=row["bar_id"],
            instrument_id=row["instrument_id"],
            timeframe=row["timeframe"],
            open_time=datetime.fromisoformat(row["open_time_utc"]),
            close_time=datetime.fromisoformat(row["close_time_utc"]),
            open=Decimal(row["open"]),
            high=Decimal(row["high"]),
            low=Decimal(row["low"]),
            close=Decimal(row["close"]),
            source_id=row["source_id"],
            source_release_id=row["source_release_id"],
            price_side=row["price_side"],
            price_increment=Decimal("0.00001"),
        )
        for row in rows
    )
    return bars


def write_jsonl(path: Path, records: list[dict[str, object]]) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for record in records:
            handle.write(json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n")


def write_csv(path: Path, records: list[dict[str, object]]) -> None:
    fields = [
        "reference_level_id",
        "registry_version",
        "instrument_id",
        "timeframe",
        "level_type",
        "price",
        "price_side",
        "created_at",
        "first_valid_time",
        "construction_rule_id",
        "construction_rule_version",
        "source_release_id",
        "status",
        "retired_at",
        "source_bar_ids",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for record in records:
            writer.writerow({**record, "source_bar_ids": "|".join(record["source_bar_ids"])})


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seal-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    seal_root = args.seal_root.resolve()
    output = args.output.resolve()
    if output.exists():
        raise FileExistsError(f"registry output already exists: {output}")
    output.mkdir(parents=True)

    seal = verify_seal(seal_root)
    sources = {
        "15M": seal_root / "canonical/accepted_15m.csv",
        "2H": seal_root / "canonical/accepted_2h.csv",
    }
    registries = {}
    all_records: list[dict[str, object]] = []
    for timeframe, source in sources.items():
        bars = read_canonical_bars(source)
        registry = build_level_registry(bars)
        records = [reference_level_to_dict(level) for level in registry.levels]
        write_jsonl(output / f"reference_levels_{timeframe.lower()}.jsonl", records)
        write_csv(output / f"reference_levels_{timeframe.lower()}.csv", records)
        counts = Counter(record["level_type"] for record in records)
        registries[timeframe] = {
            "source_path": source.relative_to(seal_root).as_posix(),
            "source_sha256": sha256(source),
            "source_bar_count": len(bars),
            "source_release_id": registry.source_release_id,
            "registry_hash": registry.registry_hash,
            "level_count": len(records),
            "level_type_counts": dict(sorted(counts.items())),
            "first_valid_time_min": records[0]["first_valid_time"] if records else None,
            "first_valid_time_max": records[-1]["first_valid_time"] if records else None,
        }
        all_records.extend(records)

    combined = json.dumps(all_records, sort_keys=True, separators=(",", ":"))
    registry_artifacts = [
        {
            "path": name,
            "sha256": sha256(output / name),
            "size_bytes": (output / name).stat().st_size,
        }
        for name in (
            "reference_levels_15m.jsonl",
            "reference_levels_15m.csv",
            "reference_levels_2h.jsonl",
            "reference_levels_2h.csv",
        )
    ]
    manifest_core = {
        "registry_id": "OPT-B-REFERENCE-LEVELS",
        "registry_version": "B-REF-0.1",
        "status": "BUILT_FOR_REPLAY_VALIDATION_NOT_ACTIVE",
        "generated_date": "2026-07-19",
        "opt_a_seal_id": seal["seal_id"],
        "opt_a_seal_hash": seal["seal_hash"],
        "instrument_id": "GBPUSD",
        "price_side": "BID",
        "timeframes": registries,
        "construction_rules": {
            "B.LEVEL.CONFIRMED_SWING_2X2.v0.1": {
                "types": ["PRIOR_SWING_HIGH", "PRIOR_SWING_LOW"],
                "left_bars": 2,
                "right_bars": 2,
                "tie_policy": "STRICT_EXTREME_REQUIRED",
                "first_valid_time": "close of second right-confirmation bar",
            },
            "B.LEVEL.ROLLING_RANGE_8.v0.1": {
                "types": ["RANGE_HIGH", "RANGE_LOW"],
                "window_bars": 8,
                "emission": "new level only when boundary price changes within a contiguous segment",
                "first_valid_time": "close of eighth source bar",
            },
        },
        "eligibility": {
            "candidate_rule": "first_valid_time <= candidate.open_time",
            "identity_rule": "instrument, timeframe, source release and price side must match",
            "multiplicity_rule": "all eligible levels remain separate; no silent best-level selection",
            "gap_rule": "construction windows never cross non-contiguous source bars",
        },
        "deferred_level_types": {
            "PDH_PDL_PWH_PWL_PMH_PML": "Economic/session calendar contract not ratified",
            "IBH_IBL_VAH_VAL_POC": "Initial-balance and profile contracts not ratified",
            "EQUILIBRIUM_FVG_BOUNDARY": "Construction predicates not ratified",
            "CUSTOM_RESEARCH": "Prohibited from active operator surfaces",
        },
        "artifacts": registry_artifacts,
        "combined_registry_hash": hashlib.sha256(combined.encode()).hexdigest(),
    }
    canonical_manifest = json.dumps(manifest_core, sort_keys=True, separators=(",", ":"))
    manifest = {**manifest_core, "manifest_hash": hashlib.sha256(canonical_manifest.encode()).hexdigest()}
    (output / "REFERENCE_LEVEL_REGISTRY_MANIFEST.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    counts_15m = registries["15M"]["level_type_counts"]
    counts_2h = registries["2H"]["level_type_counts"]
    report = f"""# OVC OPT-B Deterministic Reference-Level Registry v0.1

**Registry:** `OPT-B-REFERENCE-LEVELS`  
**Version:** `B-REF-0.1`  
**Status:** `BUILT FOR REPLAY VALIDATION — NOT ACTIVE`  
**OPT-A authority:** `{seal['seal_id']}`  
**OPT-A seal hash:** `{seal['seal_hash']}`

## Result

| Timeframe | Source bars | Swing high | Swing low | Range high | Range low | Total levels |
|---|---:|---:|---:|---:|---:|---:|
| 15M | {registries['15M']['source_bar_count']:,} | {counts_15m.get('PRIOR_SWING_HIGH', 0):,} | {counts_15m.get('PRIOR_SWING_LOW', 0):,} | {counts_15m.get('RANGE_HIGH', 0):,} | {counts_15m.get('RANGE_LOW', 0):,} | {registries['15M']['level_count']:,} |
| 2H | {registries['2H']['source_bar_count']:,} | {counts_2h.get('PRIOR_SWING_HIGH', 0):,} | {counts_2h.get('PRIOR_SWING_LOW', 0):,} | {counts_2h.get('RANGE_HIGH', 0):,} | {counts_2h.get('RANGE_LOW', 0):,} | {registries['2H']['level_count']:,} |

## Frozen construction rules

### Confirmed swing 2×2

- A high must be strictly greater than the highs of two closed bars on each side.
- A low must be strictly lower than the lows of two closed bars on each side.
- Ties do not qualify.
- The level is created at the pivot close but cannot become valid until the second right-hand confirmation bar closes.
- A five-bar window may not cross a source gap.

### Rolling range 8

- Range high is the maximum high of eight contiguous closed bars.
- Range low is the minimum low of the same window.
- The levels become valid when the eighth bar closes.
- A new record is emitted only when that boundary price changes within a contiguous segment.

## Eligibility and no-lookahead boundary

A level may be supplied to a classifier only when it matches instrument, timeframe, source release and price side, and `first_valid_time <= candidate.open_time`. Multiple eligible levels remain separate records. No later bar may alter an existing level ID, price, source bars or first-valid timestamp.

## Deferred

Previous-day/week/month, initial-balance and profile levels remain excluded until their calendar and construction contracts are separately ratified. This registry does not activate the five level-dependent OPT-B terms; it supplies their deterministic inputs for the next replay stage.
"""
    (output / "OVC_OPT_B_REFERENCE_LEVEL_REGISTRY_v0_1.md").write_text(report, encoding="utf-8")
    print(json.dumps({"status": manifest["status"], "combined_registry_hash": manifest["combined_registry_hash"], "timeframes": registries}))


if __name__ == "__main__":
    main()
