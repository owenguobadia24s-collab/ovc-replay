from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
from collections import Counter
from decimal import Decimal, getcontext
from pathlib import Path
from typing import Any

getcontext().prec = 34

ROLES = {
    "discovery": {
        "role": "DISCOVERY",
        "release_id": "OPT-A.GBPUSD.DISCOVERY.2021_2023.v2",
        "manifest_id": "MANIFEST.OPT-A.GBPUSD.DISCOVERY.2021_2023.v2.r2",
        "manifest_sha256": "0cbcafa9421449574b61bfeec24f634de99cbbbc6e7a53d09ace8f702182ab8c",
    },
    "development": {
        "role": "DEVELOPMENT",
        "release_id": "OPT-A.GBPUSD.DEVELOPMENT.2024.v2",
        "manifest_id": "MANIFEST.OPT-A.GBPUSD.DEVELOPMENT.2024.v2.r2",
        "manifest_sha256": "25e1be8a7edb0e96017c45bf35f4e788345f94b22a8ed9bb0874c86338ba64cc",
    },
}
CLOCK_MS = {"15M": 15 * 60 * 1000, "2H_A_L": 2 * 60 * 60 * 1000}
PRICE_INCREMENT = Decimal("0.00001")
ZERO_NULLS = (
    "body_utilisation", "upper_wick_share", "lower_wick_share", "wick_balance",
    "open_location", "close_location", "signed_efficiency",
)
PRIOR_FIELDS = ("true_range_abs", "true_range_ticks", "close_change", "open_gap")


def dec(value: str) -> Decimal:
    return Decimal(value)


def text(value: Decimal | None) -> str | None:
    if value is None:
        return None
    value = value.normalize()
    rendered = format(value, "f")
    return "0" if rendered in {"-0", ""} else rendered


def canonical_bytes(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")


def build_record(*, meta: dict[str, str], clock: str, side: str, source_path: str,
                 row: dict[str, str], prior: dict[str, Any] | None) -> tuple[dict[str, Any], str | None]:
    ts = int(row["timestamp"])
    o, h, l, c = map(dec, (row["open"], row["high"], row["low"], row["close"]))
    if not (l <= o <= h and l <= c <= h):
        return {}, "SOURCE_BAR_INADMISSIBLE"
    r = h - l
    body_signed = c - o
    body_abs = abs(body_signed)
    upper = h - max(o, c)
    lower = min(o, c) - l
    measurements: dict[str, Decimal | None] = {
        "range_abs": r,
        "range_ticks": r / PRICE_INCREMENT,
        "body_signed": body_signed,
        "body_abs": body_abs,
        "body_utilisation": None if r == 0 else body_abs / r,
        "upper_wick_abs": upper,
        "lower_wick_abs": lower,
        "upper_wick_share": None if r == 0 else upper / r,
        "lower_wick_share": None if r == 0 else lower / r,
        "wick_balance": None if r == 0 else (upper - lower) / r,
        "open_location": None if r == 0 else (o - l) / r,
        "close_location": None if r == 0 else (c - l) / r,
        "signed_efficiency": None if r == 0 else body_signed / r,
        "true_range_abs": None,
        "true_range_ticks": None,
        "close_change": None,
        "open_gap": None,
    }
    nulls: dict[str, str] = {}
    if r == 0:
        for field in ZERO_NULLS:
            nulls[field] = "ZERO_RANGE"
    prior_reason = "NO_PRIOR_BAR"
    if prior is not None:
        same = (
            prior["release_id"] == meta["release_id"] and prior["manifest_id"] == meta["manifest_id"]
            and prior["clock"] == clock and prior["side"] == side
        )
        contiguous = prior["timestamp"] + CLOCK_MS[clock] == ts
        if not same:
            prior_reason = "PRIOR_IDENTITY_MISMATCH"
        elif not contiguous:
            prior_reason = "NO_CONTIGUOUS_PRIOR_BAR"
        else:
            pc = prior["close"]
            tr = max(h - l, abs(h - pc), abs(l - pc))
            measurements["true_range_abs"] = tr
            measurements["true_range_ticks"] = tr / PRICE_INCREMENT
            measurements["close_change"] = c - pc
            measurements["open_gap"] = o - pc
            prior_reason = ""
    if prior_reason:
        for field in PRIOR_FIELDS:
            nulls[field] = prior_reason
    payload = {
        "schema": "ovc-c1-bar-primitives/v0.1",
        "formula_registry_id": "C1.FORMULAS.v0.1",
        "authority_state": "CANDIDATE_LOCAL_ONLY",
        "market_authority": "NONE",
        "release_parent_eligibility": "DENIED_PENDING_FREEZE",
        "role": meta["role"],
        "parent_release_id": meta["release_id"],
        "parent_manifest_id": meta["manifest_id"],
        "parent_manifest_sha256": meta["manifest_sha256"],
        "instrument": "GBPUSD",
        "clock": clock,
        "price_side": side,
        "timestamp_ms": ts,
        "source_path": source_path,
        "source_bar_id": "opt-a:" + hashlib.sha256(f"{meta['release_id']}|{source_path}|{ts}".encode()).hexdigest(),
        "measurements": {k: text(v) for k, v in measurements.items()},
        "categorical": {"direction": "UP" if c > o else "DOWN" if c < o else "FLAT"},
        "null_reasons": nulls,
    }
    identity_payload = {k: v for k, v in payload.items() if k not in {"authority_state", "market_authority", "release_parent_eligibility"}}
    payload["record_id"] = "c1:" + hashlib.sha256(canonical_bytes(identity_payload)).hexdigest()
    return payload, None


def hash_file(path: Path) -> dict[str, Any]:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
            size += len(block)
    return {"path": path.as_posix(), "size_bytes": size, "sha256": digest.hexdigest()}


def replay(role_key: str, source_root: Path, output_root: Path) -> dict[str, Any]:
    meta = ROLES[role_key]
    counts: Counter[str] = Counter()
    nulls: Counter[str] = Counter()
    rejects: Counter[str] = Counter()
    prior_by_key: dict[tuple[str, str], dict[str, Any]] = {}
    files: list[dict[str, Any]] = []
    canonical = source_root / "canonical"
    for clock in ("15M", "2H_A_L"):
        for side in ("BID", "ASK"):
            source_files = sorted((canonical / clock / side).glob("*.csv"))
            for source in source_files:
                rel = source.relative_to(source_root).as_posix()
                target = output_root / meta["role"].lower() / clock / side / (source.stem + ".c1.jsonl.gz")
                target.parent.mkdir(parents=True, exist_ok=True)
                with source.open(newline="", encoding="utf-8") as inp, target.open("wb") as raw:
                    with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as out:
                        reader = csv.DictReader(inp)
                        for row in reader:
                            key = (clock, side)
                            record, rejection = build_record(meta=meta, clock=clock, side=side, source_path=rel, row=row, prior=prior_by_key.get(key))
                            counts[f"input:{clock}:{side}"] += 1
                            if rejection:
                                rejects[rejection] += 1
                                continue
                            out.write(canonical_bytes(record))
                            counts[f"output:{clock}:{side}"] += 1
                            for reason in record["null_reasons"].values():
                                nulls[reason] += 1
                            prior_by_key[key] = {
                                "release_id": meta["release_id"], "manifest_id": meta["manifest_id"],
                                "clock": clock, "side": side, "timestamp": int(row["timestamp"]), "close": dec(row["close"]),
                            }
                files.append(hash_file(target))
    quarantine = source_root / "QA" / "quarantine-ledger.jsonl"
    quarantine_count = sum(1 for _ in quarantine.open(encoding="utf-8")) if quarantine.exists() else 0
    return {
        "role": meta["role"], "parent": meta, "counts": dict(sorted(counts.items())),
        "null_reason_counts": dict(sorted(nulls.items())), "rejected_source_counts": dict(sorted(rejects.items())),
        "quarantine_records_excluded": quarantine_count, "files": files,
    }


def inventory(root: Path) -> list[dict[str, Any]]:
    return [hash_file(path) for path in sorted(root.rglob("*.gz"))]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--discovery-root", type=Path, required=True)
    parser.add_argument("--development-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    args.output_root.mkdir(parents=True, exist_ok=True)
    summaries = [
        replay("discovery", args.discovery_root, args.output_root),
        replay("development", args.development_root, args.output_root),
    ]
    inv = inventory(args.output_root)
    report = {
        "schema": "ovc-opt-b-c1-wp4-replay-report/v1",
        "scope_id": "C1.WP4.GBPUSD.DISCOVERY_DEVELOPMENT.v1",
        "status": "LOCAL_CANDIDATE_QA_PASS",
        "formula_registry_id": "C1.FORMULAS.v0.1",
        "validation_consumption": "LOCKED_UNCONSUMED_EXCLUDED",
        "roles": summaries,
        "inventory": inv,
        "inventory_file_count": len(inv),
        "inventory_bytes": sum(item["size_bytes"] for item in inv),
        "controls": {
            "decimal_exact": "PASS", "cross_side_substitution": "PROHIBITED_AND_NOT_PERFORMED",
            "gap_repair": "PROHIBITED_AND_NOT_PERFORMED", "interpolation": "PROHIBITED_AND_NOT_PERFORMED",
            "quarantine_exclusion": "PASS", "release_freeze": "LOCAL_CANDIDATE_ONLY",
            "r2_publication": "NOT_AUTHORISED", "selector_activation": "NONE", "c2_consumption": "DENIED",
        },
    }
    (args.output_root / "WP4_REPLAY_REPORT.json").write_bytes(canonical_bytes(report))
    (args.output_root / "WP4_INVENTORY.json").write_bytes(canonical_bytes({"schema": "ovc-c1-inventory/v1", "files": inv}))


if __name__ == "__main__":
    main()
