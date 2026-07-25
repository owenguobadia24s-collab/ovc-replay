from __future__ import annotations

import argparse
import gzip
import hashlib
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from build_opt_a_validation_seal import (  # noqa: E402
    END,
    SEAL_VERSION,
    START,
    gap_ledger,
    rejected_record,
    volume_audit,
)
from build_reference_level_registry import read_canonical_bars, sha256  # noqa: E402
from ovc_opt_b import aggregate_bars, read_dukascopy_csv  # noqa: E402
from run_complete_opt_b_replay import canonical_hash  # noqa: E402


def load_gzip(path: Path) -> list[dict[str, object]]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle]


def canonical_stream_hash(path: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    count = 0
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            digest.update((json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n").encode())
            count += 1
    return digest.hexdigest(), count


def bar_signature(bar) -> tuple[object, ...]:
    return (
        bar.bar_id, bar.instrument_id, bar.timeframe, bar.open_time, bar.close_time,
        bar.open, bar.high, bar.low, bar.close, bar.price_side, bar.source_id, bar.source_release_id,
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seal-root", type=Path, required=True)
    parser.add_argument("--determinism-root", type=Path)
    args = parser.parse_args()
    root = args.seal_root.resolve()
    manifest = json.loads((root / "OPT_A_SEAL_MANIFEST.json").read_text(encoding="utf-8"))
    core = {key: value for key, value in manifest.items() if key != "seal_hash"}
    if canonical_hash(core) != manifest["seal_hash"]:
        raise ValueError("OPT-A validation seal self-hash mismatch")
    if manifest["seal_version"] != SEAL_VERSION:
        raise ValueError("OPT-A validation seal version mismatch")
    if manifest["scope"]["interval"] != "[2025-01-01T00:00:00Z, 2026-01-01T00:00:00Z)":
        raise ValueError("holdout interval mismatch")
    if manifest["scope"]["canonical_timeframes"] != ["15M"]:
        raise ValueError("unexpected canonical holdout clock")
    if manifest["authority"]["execution_authority"] != "NONE":
        raise ValueError("execution authority escaped seal")

    artifact_checks = []
    for artifact in manifest["artifacts"]:
        path = root / artifact["path"]
        actual = sha256(path)
        if actual != artifact["sha256"]:
            raise ValueError(f"artifact hash mismatch: {path.name}")
        artifact_checks.append({"path": artifact["path"], "sha256": actual, "status": "PASS"})

    raw_artifact = next(item for item in manifest["artifacts"] if item["role"] == "RAW_M1_PROVIDER_RELEASE")
    raw_path = root / raw_artifact["path"]
    source_release_id = f"dukascopy-gbpusd-bid-{raw_artifact['sha256'][:16]}"
    raw = read_dukascopy_csv(raw_path, source_release_id=source_release_id)
    volumes = volume_audit(raw_path)
    if volumes != {"rows": 371074, "zero_volume_rows": 0, "negative_volume_rows": 0}:
        raise ValueError("raw provider volume audit mismatch")
    if not (START <= raw[0].open_time < raw[-1].close_time <= END):
        raise ValueError("raw provider coverage escapes holdout")

    gaps = gap_ledger(raw)
    actual_gaps = load_gzip(root / "quality/minute_gap_ledger.jsonl.gz")
    if actual_gaps != gaps:
        raise ValueError("minute gap ledger mismatch")
    expected_minutes = int((END - START).total_seconds() // 60)
    if len(raw) + sum(item["missing_minutes"] for item in gaps) != expected_minutes:
        raise ValueError("minute coverage conservation mismatch")

    fifteen = aggregate_bars(raw, target_timeframe="15M")
    two_hour = aggregate_bars(fifteen.accepted, target_timeframe="2H")
    actual_15m = read_canonical_bars(root / "canonical/accepted_15m.csv")
    actual_2h = read_canonical_bars(root / "canonical/accepted_2h.csv")
    if [bar_signature(item) for item in actual_15m] != [bar_signature(item) for item in fifteen.accepted]:
        raise ValueError("canonical 15M holdout mismatch")
    if [bar_signature(item) for item in actual_2h] != [bar_signature(item) for item in two_hour.accepted]:
        raise ValueError("2H context mismatch")
    if load_gzip(root / "quality/rejected_15m_buckets.jsonl.gz") != [
        rejected_record(item) for item in fifteen.rejected
    ]:
        raise ValueError("15M rejection ledger mismatch")
    if load_gzip(root / "quality/rejected_2h_context_buckets.jsonl.gz") != [
        rejected_record(item) for item in two_hour.rejected
    ]:
        raise ValueError("2H context rejection ledger mismatch")

    retrieval = json.loads((root / "retrieval/DUKASCOPY_RETRIEVAL_MANIFEST.json").read_text(encoding="utf-8"))
    if retrieval["include_flats"] is not False:
        raise ValueError("retrieval unexpectedly included synthetic flats")
    if retrieval["date_from"] != "2025-01-01" or retrieval["date_to_exclusive"] != "2026-01-01":
        raise ValueError("retrieval interval mismatch")
    if retrieval["raw_sha256"] != raw_artifact["sha256"]:
        raise ValueError("retrieval/raw hash mismatch")
    if retrieval["retrieval_client_version"] != "1.49.0":
        raise ValueError("retrieval client version drift")

    metadata = manifest["counts"]["stream_metadata"]
    stream_checks = []
    for filename, prefix, expected_count in (
        ("quality/minute_gap_ledger.jsonl.gz", "gaps", len(gaps)),
        ("quality/rejected_15m_buckets.jsonl.gz", "rejected_15m", len(fifteen.rejected)),
        ("quality/rejected_2h_context_buckets.jsonl.gz", "rejected_2h", len(two_hour.rejected)),
    ):
        stream_hash, count = canonical_stream_hash(root / filename)
        if count != expected_count or count != metadata[f"{prefix}_records"]:
            raise ValueError(f"canonical stream count mismatch: {filename}")
        if stream_hash != metadata[f"{prefix}_canonical_jsonl_hash"]:
            raise ValueError(f"canonical stream hash mismatch: {filename}")
        stream_checks.append({"path": filename, "rows": count, "canonical_jsonl_hash": stream_hash})

    determinism = {"checked": False}
    if args.determinism_root:
        other = json.loads(
            (args.determinism_root.resolve() / "OPT_A_SEAL_MANIFEST.json").read_text(encoding="utf-8")
        )
        other_core = {key: value for key, value in other.items() if key != "seal_hash"}
        if canonical_hash(other_core) != other["seal_hash"] or other["seal_hash"] != manifest["seal_hash"]:
            raise ValueError("OPT-A validation seal determinism mismatch")
        determinism = {"checked": True, "seal_hash_match": True}

    validation = {
        "status": "PASS",
        "validated_seal_hash": manifest["seal_hash"],
        "artifact_checks": artifact_checks,
        "stream_checks": stream_checks,
        "determinism": determinism,
        "counts": {
            "raw_m1_rows": len(raw),
            "absent_minutes": expected_minutes - len(raw),
            "accepted_15m_bars": len(fifteen.accepted),
            "rejected_touched_15m_buckets": len(fifteen.rejected),
            "accepted_2h_context_bars": len(two_hour.accepted),
        },
        "gate_controls": {
            "provider_rows_strictly_monotonic": True,
            "minute_coverage_conserved": True,
            "zero_synthetic_flat_rows": True,
            "all_incomplete_15m_buckets_quarantined": True,
            "canonical_15m_recomputed": True,
            "2h_is_context_only": True,
            "no_execution_authority": True,
        },
    }
    (root / "OPT_A_VALIDATION_SEAL_VALIDATION.json").write_text(
        json.dumps(validation, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    lines = [
        "# OPT-A GBP/USD 2025 Validation Seal Verification",
        "",
        "**Status:** `PASS`  ",
        f"**Seal hash:** `{manifest['seal_hash']}`  ",
        f"**Independent determinism:** `{'PASS' if determinism['checked'] else 'NOT RUN'}`",
        "",
        f"All {len(raw):,} provider-returned minutes, {len(gaps):,} gap records, {len(fifteen.accepted):,} complete 15M bars and {len(fifteen.rejected):,} touched-but-incomplete 15M buckets were independently recomputed and matched.",
        "",
        "No zero-volume synthetic flats were present. The 2H series remains context-only and carries no OPT-D hypothesis authority.",
    ]
    (root / "OPT_A_VALIDATION_SEAL_VALIDATION.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )
    print(json.dumps({"status": "PASS", "seal_hash": manifest["seal_hash"]}, sort_keys=True))


if __name__ == "__main__":
    main()
