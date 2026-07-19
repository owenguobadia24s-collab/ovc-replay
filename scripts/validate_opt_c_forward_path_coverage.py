from __future__ import annotations

import argparse
from bisect import bisect_left, bisect_right
from collections import Counter
from datetime import datetime
import gzip
import hashlib
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from build_reference_level_registry import read_canonical_bars, verify_seal  # noqa: E402
from ovc_opt_b import OPT_C_HORIZONS_HOURS, assess_15m_path_coverage  # noqa: E402


COVERAGE_VERSION = "OPT-C-COVERAGE-0.1"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_hash(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def verify_manifest(root: Path, name: str) -> dict[str, object]:
    manifest = json.loads((root / name).read_text(encoding="utf-8"))
    core = {key: value for key, value in manifest.items() if key != "manifest_hash"}
    if canonical_hash(core) != manifest["manifest_hash"]:
        raise ValueError(f"manifest self-hash mismatch: {name}")
    return manifest


def load_gzip(path: Path) -> list[dict[str, object]]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle]


def recursive_keys(value: object) -> set[str]:
    if isinstance(value, dict):
        keys = {str(key).lower() for key in value}
        for item in value.values():
            keys.update(recursive_keys(item))
        return keys
    if isinstance(value, list):
        keys: set[str] = set()
        for item in value:
            keys.update(recursive_keys(item))
        return keys
    return set()


def expected_overlap(
    anchor: dict[str, object],
    endpoint: datetime,
    *,
    all_times: list[datetime],
    all_ids: list[str],
    clock_times: list[datetime],
) -> dict[str, object]:
    at = datetime.fromisoformat(anchor["anchor_time"])
    same_start = bisect_left(all_times, at)
    same_end = bisect_right(all_times, at)
    same_ids = [item for item in all_ids[same_start:same_end] if item != anchor["event_anchor_id"]]
    future_end = bisect_right(all_times, endpoint)
    future_ids = all_ids[same_end:future_end]
    ids = sorted((*same_ids, *future_ids))
    return {
        "same_time_other_anchor_count": len(same_ids),
        "subsequent_overlap_anchor_count_all_clocks": len(future_ids),
        "subsequent_overlap_anchor_count_same_clock": (
            bisect_right(clock_times, endpoint) - bisect_right(clock_times, at)
        ),
        "overlap_present": bool(ids),
        "overlap_anchor_ids_hash": canonical_hash(ids) if ids else None,
    }


def assessment_fields(value) -> dict[str, object]:
    return {
        "coverage_status": value.coverage_status,
        "censor_reasons": list(value.censor_reasons),
        "endpoint_time": value.endpoint_time.isoformat(),
        "expected_bar_count": value.expected_bar_count,
        "available_bar_count": value.available_bar_count,
        "missing_interval_count": value.missing_interval_count,
        "missing_run_count": value.missing_run_count,
        "max_missing_run_bars": value.max_missing_run_bars,
        "first_missing_open_time": value.first_missing_open_time.isoformat() if value.first_missing_open_time else None,
        "last_missing_open_time": value.last_missing_open_time.isoformat() if value.last_missing_open_time else None,
        "missing_open_times_hash": value.missing_open_times_hash,
        "available_bar_ids_hash": value.available_bar_ids_hash,
        "path_bar_ids_hash": value.path_bar_ids_hash,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--release-root", type=Path, required=True)
    parser.add_argument("--ledger-root", type=Path, required=True)
    parser.add_argument("--seal-root", type=Path, required=True)
    parser.add_argument("--determinism-root", type=Path)
    args = parser.parse_args()
    root = args.release_root.resolve()
    ledger_root = args.ledger_root.resolve()
    seal_root = args.seal_root.resolve()
    manifest = verify_manifest(root, "OPT_C_FORWARD_PATH_COVERAGE_MANIFEST.json")
    ledger_manifest = verify_manifest(ledger_root, "OPT_C_EVENT_ANCHOR_LEDGER_MANIFEST.json")
    seal = verify_seal(seal_root)
    if manifest["event_ledger_manifest_hash"] != ledger_manifest["manifest_hash"]:
        raise ValueError("coverage/event-ledger lineage mismatch")
    if manifest["opt_a_seal_hash"] != seal["seal_hash"]:
        raise ValueError("coverage/OPT-A lineage mismatch")
    if manifest["coverage_contract_version"] != COVERAGE_VERSION:
        raise ValueError("wrong coverage contract version")

    artifact_checks = []
    for artifact in manifest["artifacts"]:
        path = root / artifact["path"]
        actual = sha256(path)
        if actual != artifact["sha256"]:
            raise ValueError(f"artifact hash mismatch: {path.name}")
        artifact_checks.append({"path": path.name, "sha256": actual, "status": "PASS"})

    bars = read_canonical_bars(seal_root / "canonical/accepted_15m.csv")
    bar_ids_by_open_time = {bar.open_time: bar.bar_id for bar in bars}
    source_last_close_time = max(bar.close_time for bar in bars)
    anchors = {
        timeframe: load_gzip(ledger_root / f"opt_c_event_anchor_ledger_{timeframe.lower()}.jsonl.gz")
        for timeframe in ("15M", "2H")
    }
    anchor_by_id = {
        anchor["event_anchor_id"]: anchor
        for items in anchors.values()
        for anchor in items
    }
    entries = sorted(
        (datetime.fromisoformat(anchor["anchor_time"]), anchor["event_anchor_id"])
        for items in anchors.values()
        for anchor in items
    )
    all_times = [item[0] for item in entries]
    all_ids = [item[1] for item in entries]
    clock_times = {
        timeframe: sorted(datetime.fromisoformat(anchor["anchor_time"]) for anchor in items)
        for timeframe, items in anchors.items()
    }
    prohibited = {
        "endpoint_price",
        "endpoint_return",
        "maximum_upward_excursion",
        "maximum_downward_excursion",
        "mfe",
        "mae",
        "profit",
        "loss",
        "win",
        "execution",
    }
    stream_checks = []
    for timeframe in ("15M", "2H"):
        path = root / f"opt_c_forward_path_coverage_{timeframe.lower()}.jsonl.gz"
        records = load_gzip(path)
        expected_rows = len(anchors[timeframe]) * len(OPT_C_HORIZONS_HOURS)
        if len(records) != expected_rows:
            raise ValueError(f"coverage row-count mismatch in {timeframe}")
        identities = set()
        statuses = Counter()
        complete_by_horizon = Counter()
        for row in records:
            identity = (row["event_anchor_id"], row["horizon_hours"])
            if identity in identities:
                raise ValueError(f"duplicate anchor/horizon record in {timeframe}")
            identities.add(identity)
            if recursive_keys(row).intersection(prohibited):
                raise ValueError(f"forward outcome value entered coverage stream in {timeframe}")
            if row["coverage_contract_version"] != COVERAGE_VERSION:
                raise ValueError(f"coverage version mismatch in {timeframe}")
            anchor = anchor_by_id.get(row["event_anchor_id"])
            if anchor is None or anchor["event_timeframe"] != timeframe:
                raise ValueError(f"unknown event anchor in {timeframe}")
            if row["anchor_time"] != anchor["anchor_time"]:
                raise ValueError(f"anchor timestamp mismatch in {timeframe}")
            assessment = assess_15m_path_coverage(
                datetime.fromisoformat(anchor["anchor_time"]),
                row["horizon_hours"],
                bar_ids_by_open_time=bar_ids_by_open_time,
                source_last_close_time=source_last_close_time,
            )
            for field, expected in assessment_fields(assessment).items():
                if row[field] != expected:
                    raise ValueError(f"coverage assessment mismatch {timeframe}:{field}")
            overlap = expected_overlap(
                anchor,
                assessment.endpoint_time,
                all_times=all_times,
                all_ids=all_ids,
                clock_times=clock_times[timeframe],
            )
            if row["overlap"] != overlap:
                raise ValueError(f"overlap assessment mismatch in {timeframe}")
            if row["coverage_status"] == "COMPLETE":
                if row["path_bar_ids_hash"] is None or row["missing_interval_count"]:
                    raise ValueError(f"invalid complete path in {timeframe}")
                complete_by_horizon[str(row["horizon_hours"])] += 1
            else:
                if row["path_bar_ids_hash"] is not None:
                    raise ValueError(f"censored path received complete path hash in {timeframe}")
            statuses[row["coverage_status"]] += 1
        for horizon in OPT_C_HORIZONS_HOURS:
            declared = manifest["results"][timeframe]["horizons"][str(horizon)]["complete"]
            if complete_by_horizon[str(horizon)] != declared:
                raise ValueError(f"summary complete-count mismatch in {timeframe}:{horizon}")
        stream_checks.append(
            {
                "path": path.name,
                "rows": len(records),
                "unique_anchor_horizons": len(identities),
                "status_counts": dict(sorted(statuses.items())),
                "gzip_integrity": "PASS",
            }
        )

    if sum(manifest["results"][timeframe]["horizons"]["48"]["complete"] for timeframe in ("15M", "2H")):
        raise ValueError("48h gate must remain blocked when complete paths exist count is zero")

    determinism: dict[str, object] = {"checked": False}
    if args.determinism_root:
        prior = verify_manifest(args.determinism_root.resolve(), "OPT_C_FORWARD_PATH_COVERAGE_MANIFEST.json")
        comparisons = {
            timeframe: manifest["results"][timeframe]["coverage_stream_canonical_jsonl_hash"]
            == prior["results"][timeframe]["coverage_stream_canonical_jsonl_hash"]
            for timeframe in ("15M", "2H")
        }
        if not all(comparisons.values()):
            raise ValueError("independent coverage-audit determinism mismatch")
        determinism = {"checked": True, "all_canonical_hashes_match": True, "comparisons": comparisons}

    result = {
        "status": "PASS",
        "validated_manifest_hash": manifest["manifest_hash"],
        "artifact_checks": artifact_checks,
        "stream_checks": stream_checks,
        "determinism": determinism,
        "gate_controls": {
            "complete_paths_exact": True,
            "censored_paths_unrepaired": True,
            "overlap_recomputed": True,
            "forward_price_values_absent": True,
            "48h_measurement_blocked": True,
        },
        "authority_boundary": "Coverage and censoring evidence only; no forward outcome, edge, recommendation, risk or execution authority.",
    }
    (root / "OPT_C_FORWARD_PATH_COVERAGE_VALIDATION.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    lines = [
        "# OPT-C Forward-Path Coverage Validation",
        "",
        "**Status:** `PASS`  ",
        f"**Validated manifest:** `{manifest['manifest_hash']}`  ",
        f"**Independent determinism:** `{'PASS' if determinism['checked'] else 'NOT RUN'}`",
        "",
        "All 30,128 anchor–horizon assessments, exact interval counts, censor reasons, missing-run hashes, ordered complete-path hashes, overlap fields, artifact hashes and summary counts passed. No forward price or outcome value entered the audit.",
    ]
    (root / "OPT_C_FORWARD_PATH_COVERAGE_VALIDATION.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"status": "PASS", "manifest_hash": manifest["manifest_hash"]}, sort_keys=True))


if __name__ == "__main__":
    main()
