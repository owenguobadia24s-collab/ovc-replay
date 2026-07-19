from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from decimal import Decimal
import gzip
import json
from pathlib import Path
import shutil
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from build_reference_level_registry import sha256  # noqa: E402
from ovc_opt_b import (  # noqa: E402
    descriptive_support_band,
    measurement_semantic_violations,
    nested_horizon_violations,
    overlap_stratum,
)
from run_complete_opt_b_replay import DeterministicJsonlGzipWriter, canonical_hash  # noqa: E402


REVIEW_VERSION = "OPT-C-SEMANTIC-REVIEW-0.1"
MEASUREMENT_VERSION = "OPT-C-MEASURE-0.1.1"
CLOCKS = ("15M", "2H")
HORIZONS = (1, 2, 4, 8, 12)
FAMILIES = ("ACCEPTANCE_FRONTIER", "DISPLACEMENT", "COMPRESSION", "INTERACTION")
DIRECTIONS = ("UP", "DOWN", "MIXED", "NONE")


def verify_manifest(root: Path, name: str) -> dict[str, object]:
    manifest = json.loads((root / name).read_text(encoding="utf-8"))
    core = {key: value for key, value in manifest.items() if key != "manifest_hash"}
    if canonical_hash(core) != manifest["manifest_hash"]:
        raise ValueError(f"manifest self-hash mismatch: {name}")
    for artifact in manifest["artifacts"]:
        path = root / artifact["path"]
        if sha256(path) != artifact["sha256"]:
            raise ValueError(f"artifact hash mismatch: {path.name}")
    return manifest


def load_gzip(path: Path) -> list[dict[str, object]]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle]


def percentile(values: list[Decimal], fraction: Decimal) -> str | None:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return str(ordered[0])
    position = fraction * Decimal(len(ordered) - 1)
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    weight = position - Decimal(lower)
    return str(ordered[lower] + (ordered[upper] - ordered[lower]) * weight)


def distribution(values: list[Decimal]) -> dict[str, object]:
    return {
        "count": len(values),
        "minimum": str(min(values)) if values else None,
        "p10": percentile(values, Decimal("0.10")),
        "median": percentile(values, Decimal("0.50")),
        "p90": percentile(values, Decimal("0.90")),
        "maximum": str(max(values)) if values else None,
    }


def rate(numerator: int, denominator: int) -> float | None:
    return round(numerator * 100 / denominator, 4) if denominator else None


def outcome_distribution(rows: list[dict[str, object]], field: str) -> dict[str, object]:
    return distribution(
        [Decimal(str(row["measurements"][field])) for row in rows if row["measurements"][field] is not None]
    )


def build_support_matrix(rows_by_clock: dict[str, list[dict[str, object]]], output: Path):
    path = output / "opt_c_semantic_cohort_support_matrix.jsonl.gz"
    writer = DeterministicJsonlGzipWriter(path)
    band_counts = Counter()
    matrix_rows = []
    for clock in CLOCKS:
        for horizon in HORIZONS:
            horizon_rows = [row for row in rows_by_clock[clock] if row["horizon_hours"] == horizon]
            for family in FAMILIES:
                for direction in DIRECTIONS:
                    subset = [
                        row for row in horizon_rows
                        if family in row["event_families"] and row["event_direction"] == direction
                    ]
                    band = descriptive_support_band(len(subset))
                    band_counts[band] += 1
                    core = {
                        "event_timeframe": clock,
                        "horizon_hours": horizon,
                        "event_family": family,
                        "event_direction": direction,
                        "outcome_records": len(subset),
                        "unique_event_anchors": len({row["event_anchor_id"] for row in subset}),
                        "support_band": band,
                        "raw_return_pips": outcome_distribution(subset, "raw_return_pips"),
                        "direction_normalized_endpoint_return_pips": outcome_distribution(
                            subset, "direction_normalized_endpoint_return_pips"
                        ),
                        "membership_rule": "MULTI_FAMILY_ROWS_APPEAR_IN_EACH_NAMED_FAMILY_CELLS_NOT_ADDITIVE",
                        "review_contract_version": REVIEW_VERSION,
                    }
                    record = {**core, "support_cell_id": f"opt-c-support:{canonical_hash(core)}"}
                    writer.write(record)
                    matrix_rows.append(record)
    writer.close()
    return (
        {
            "cells": writer.count,
            "support_band_counts": dict(sorted(band_counts.items())),
            "canonical_jsonl_hash": writer.canonical_jsonl_hash,
        },
        {"path": path.name, "sha256": sha256(path), "size_bytes": path.stat().st_size},
        matrix_rows,
    )


def distribution_integrity(rows_by_clock: dict[str, list[dict[str, object]]]) -> dict[str, object]:
    result = {}
    for clock in CLOCKS:
        by_anchor = defaultdict(list)
        violations = Counter()
        for row in rows_by_clock[clock]:
            violations.update(measurement_semantic_violations(row))
            by_anchor[row["event_anchor_id"]].append(row)
        nested_violations = Counter()
        horizon_count_distribution = Counter()
        for anchor_rows in by_anchor.values():
            horizon_count_distribution[str(len(anchor_rows))] += 1
            nested_violations.update(nested_horizon_violations(anchor_rows))
        horizons = {}
        for horizon in HORIZONS:
            subset = [row for row in rows_by_clock[clock] if row["horizon_hours"] == horizon]
            horizons[str(horizon)] = {
                "records": len(subset),
                "raw_return_pips": outcome_distribution(subset, "raw_return_pips"),
                "maximum_upward_excursion_pips": outcome_distribution(
                    subset, "maximum_upward_excursion_pips"
                ),
                "maximum_downward_excursion_pips": outcome_distribution(
                    subset, "maximum_downward_excursion_pips"
                ),
                "direction_normalized_endpoint_return_pips": outcome_distribution(
                    subset, "direction_normalized_endpoint_return_pips"
                ),
                "endpoint_close_position": outcome_distribution(
                    subset, "endpoint_close_position_in_forward_range"
                ),
            }
        result[clock] = {
            "outcome_records": len(rows_by_clock[clock]),
            "unique_event_anchors": len(by_anchor),
            "measurement_semantic_violation_counts": dict(sorted(violations.items())),
            "nested_horizon_violation_counts": dict(sorted(nested_violations.items())),
            "anchors_by_complete_horizon_count": dict(
                sorted(horizon_count_distribution.items(), key=lambda item: int(item[0]))
            ),
            "horizons": horizons,
        }
    return result


def overlap_review(rows_by_clock: dict[str, list[dict[str, object]]]) -> dict[str, object]:
    result = {}
    for clock in CLOCKS:
        horizons = {}
        for horizon in HORIZONS:
            subset = [row for row in rows_by_clock[clock] if row["horizon_hours"] == horizon]
            strata = {}
            for label in (
                "NO_OVERLAP", "SAME_TIME_ONLY", "SUBSEQUENT_CROSS_CLOCK_ONLY", "SUBSEQUENT_SAME_CLOCK"
            ):
                items = [row for row in subset if overlap_stratum(row["overlap"]) == label]
                strata[label] = {
                    "records": len(items),
                    "raw_return_pips": outcome_distribution(items, "raw_return_pips"),
                    "direction_normalized_endpoint_return_pips": outcome_distribution(
                        items, "direction_normalized_endpoint_return_pips"
                    ),
                }
            overlap_records = sum(row["overlap"]["overlap_present"] is True for row in subset)
            subsequent_counts = [
                int(row["overlap"]["subsequent_overlap_anchor_count_all_clocks"]) for row in subset
            ]
            horizons[str(horizon)] = {
                "records": len(subset),
                "overlap_records": overlap_records,
                "overlap_rate_pct": rate(overlap_records, len(subset)),
                "maximum_subsequent_overlap_anchors": max(subsequent_counts) if subsequent_counts else 0,
                "strata": strata,
            }
        result[clock] = {"horizons": horizons}
    return result


def frontier_review(rows_by_clock: dict[str, list[dict[str, object]]]) -> dict[str, object]:
    result = {}
    for clock in CLOCKS:
        horizons = {}
        for horizon in HORIZONS:
            subset = [row for row in rows_by_clock[clock] if row["horizon_hours"] == horizon]
            directional = [row for row in subset if row["event_direction"] in ("UP", "DOWN")]
            applicable = [
                row for row in directional if row["measurements"]["primary_frontier_type"] is not None
            ]
            retested = sum(row["measurements"]["primary_frontier_retested"] is True for row in applicable)
            lost = sum(row["measurements"]["primary_frontier_lost_on_close"] is True for row in applicable)
            held = sum(row["measurements"]["primary_frontier_held_at_endpoint"] is True for row in applicable)
            frontier_type_counts = Counter(
                item["frontier_type"] for row in subset for item in row["measurements"]["frontier_tests"]
            )
            horizons[str(horizon)] = {
                "records": len(subset),
                "directional_records": len(directional),
                "primary_frontier_applicable_records": len(applicable),
                "primary_frontier_applicability_rate_pct": rate(len(applicable), len(directional)),
                "primary_frontier_retested_records": retested,
                "primary_frontier_retest_rate_pct": rate(retested, len(applicable)),
                "primary_frontier_lost_on_close_records": lost,
                "primary_frontier_loss_rate_pct": rate(lost, len(applicable)),
                "primary_frontier_held_at_endpoint_records": held,
                "primary_frontier_endpoint_hold_rate_pct": rate(held, len(applicable)),
                "frontier_test_counts": dict(sorted(frontier_type_counts.items())),
            }
        result[clock] = {"horizons": horizons}
    return result


def write_report(output: Path, results: dict[str, object]) -> Path:
    integrity = results["distribution_integrity"]
    overlap = results["overlap_review"]
    frontier = results["frontier_review"]
    support = results["cohort_support"]
    lines = [
        "# OVC OPT-C Semantic Sanity Review v0.1",
        "",
        "**Status:** `PASS WITH OVERLAP AND SPARSE-COHORT CONTROLS`  ",
        f"**Review contract:** `{REVIEW_VERSION}`  ",
        "**Edge / trade / execution authority:** `NONE`",
        "",
        "## Measurement and nested-horizon integrity",
        "",
        "| Clock | Outcome rows | Unique anchors | Arithmetic/semantic violations | Nested-horizon violations |",
        "|---|---:|---:|---:|---:|",
    ]
    for clock in CLOCKS:
        item = integrity[clock]
        lines.append(
            f"| {clock} | {item['outcome_records']:,} | {item['unique_event_anchors']:,} | "
            f"{sum(item['measurement_semantic_violation_counts'].values()):,} | "
            f"{sum(item['nested_horizon_violation_counts'].values()):,} |"
        )
    lines.extend([
        "",
        "All return identities, excursion bounds, direction normalization, extreme timing, frontier relations and increasing-horizon invariants passed.",
        "",
        "## Overlap concentration",
        "",
        "| Clock | Horizon | Rows | Overlapping | Overlap rate |",
        "|---|---:|---:|---:|---:|",
    ])
    for clock in CLOCKS:
        for horizon in HORIZONS:
            item = overlap[clock]["horizons"][str(horizon)]
            lines.append(
                f"| {clock} | {horizon}h | {item['records']:,} | {item['overlap_records']:,} | "
                f"{(item['overlap_rate_pct'] or 0.0):.2f}% |"
            )
    lines.extend([
        "",
        "Overlap is a dominant property of this event ledger, especially at longer horizons. Pooled rows therefore cannot be treated as independent observations. Downstream cohorts must preserve overlap strata and use time-separated or cluster-aware comparison units.",
        "",
        "## Frontier applicability",
        "",
        "| Clock | Horizon | Directional | Primary frontier | Applicable | Retested | Lost on close |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ])
    for clock in CLOCKS:
        for horizon in HORIZONS:
            item = frontier[clock]["horizons"][str(horizon)]
            lines.append(
                f"| {clock} | {horizon}h | {item['directional_records']:,} | "
                f"{item['primary_frontier_applicable_records']:,} | "
                f"{(item['primary_frontier_applicability_rate_pct'] or 0.0):.2f}% | "
                f"{(item['primary_frontier_retest_rate_pct'] or 0.0):.2f}% | "
                f"{(item['primary_frontier_loss_rate_pct'] or 0.0):.2f}% |"
            )
    band_counts = support["support_band_counts"]
    lines.extend([
        "",
        "## Cohort support gate",
        "",
        f"The frozen 160-cell clock × horizon × family × direction matrix contains **{band_counts.get('ADEQUATE_DESCRIPTIVE_SUPPORT', 0)}** adequate descriptive cells, **{band_counts.get('LIMITED_DESCRIPTIVE_SUPPORT', 0)}** limited cells, **{band_counts.get('SPARSE_NO_COMPARISON', 0)}** sparse cells and **{band_counts.get('EMPTY', 0)}** empty cells.",
        "",
        "Sparse cells remain inventory-only. Multi-family cells overlap by construction and are not additive.",
        "",
        "## Gate decision",
        "",
        "The neutral OPT-C measurement semantics pass. The release may advance to an OPT-D cohort-contract draft only if that contract preserves overlap strata, support bands, family membership and the 1–12h complete-path boundary. No pooled independence, threshold optimization, significance, edge or execution claim is authorized.",
    ])
    path = output / "OVC_OPT_C_SEMANTIC_SANITY_REVIEW_REPORT_v0_1.md"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--measurement-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    measurement_root = args.measurement_root.resolve()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    manifest_path = output / "OPT_C_SEMANTIC_SANITY_REVIEW_MANIFEST.json"
    if manifest_path.exists():
        raise FileExistsError("OPT-C semantic review already finalized")

    measurement_manifest = verify_manifest(
        measurement_root, "OPT_C_NEUTRAL_OUTCOME_MEASUREMENT_MANIFEST.json"
    )
    if measurement_manifest["measurement_contract_version"] != MEASUREMENT_VERSION:
        raise ValueError("semantic review requires OPT-C-MEASURE-0.1")
    rows_by_clock = {
        clock: load_gzip(measurement_root / f"opt_c_neutral_outcomes_{clock.lower()}.jsonl.gz")
        for clock in CLOCKS
    }
    if sum(len(rows) for rows in rows_by_clock.values()) != measurement_manifest["total_outcome_records"]:
        raise ValueError("measurement row count does not match parent manifest")

    integrity = distribution_integrity(rows_by_clock)
    if any(
        integrity[clock][key]
        for clock in CLOCKS
        for key in ("measurement_semantic_violation_counts", "nested_horizon_violation_counts")
    ):
        raise ValueError("semantic integrity violation blocks review release")
    overlap = overlap_review(rows_by_clock)
    frontier = frontier_review(rows_by_clock)
    support_summary, support_artifact, _ = build_support_matrix(rows_by_clock, output)
    results = {
        "distribution_integrity": integrity,
        "overlap_review": overlap,
        "frontier_review": frontier,
        "cohort_support": support_summary,
        "gate_decision": "PASS_WITH_OVERLAP_AND_SPARSE_COHORT_CONTROLS",
    }

    artifacts = [support_artifact]
    for filename, content in (
        ("opt_c_semantic_distribution_integrity.json", integrity),
        ("opt_c_semantic_overlap_review.json", overlap),
        ("opt_c_semantic_frontier_review.json", frontier),
        ("opt_c_semantic_review_summary.json", results),
    ):
        path = output / filename
        path.write_text(json.dumps(content, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        artifacts.append({"path": path.name, "sha256": sha256(path), "size_bytes": path.stat().st_size})
    report = write_report(output, results)
    artifacts.append({"path": report.name, "sha256": sha256(report), "size_bytes": report.stat().st_size})
    for source in (
        ROOT / "contracts/OVC_OPT_C_SEMANTIC_SANITY_REVIEW_CONTRACT_v0_1.md",
        ROOT / "contracts/OVC_OPT_C_NEUTRAL_MEASUREMENT_IMPLEMENTATION_CONTRACT_v0_1_1.md",
    ):
        destination = output / source.name
        shutil.copy2(source, destination)
        artifacts.append({"path": destination.name, "sha256": sha256(destination), "size_bytes": destination.stat().st_size})

    manifest_core = {
        "release_id": "OPT-C-SEMANTIC-SANITY-GBPUSD-2026H1-v0.1",
        "status": "PASS_WITH_OVERLAP_AND_SPARSE_COHORT_CONTROLS",
        "generated_date": "2026-07-19",
        "review_contract_version": REVIEW_VERSION,
        "parent_measurement_contract_version": MEASUREMENT_VERSION,
        "parent_measurement_manifest_hash": measurement_manifest["manifest_hash"],
        "reviewed_outcome_records": sum(len(rows) for rows in rows_by_clock.values()),
        "reviewed_horizons_hours": list(HORIZONS),
        "coverage_only_horizons_hours": [24],
        "blocked_horizons_hours": [48],
        "support_bands": {
            "EMPTY": [0, 0],
            "SPARSE_NO_COMPARISON": [1, 29],
            "LIMITED_DESCRIPTIVE_SUPPORT": [30, 99],
            "ADEQUATE_DESCRIPTIVE_SUPPORT": [100, None],
        },
        "results": results,
        "artifacts": artifacts,
        "implementation_hashes": {
            "semantic_review.py": sha256(ROOT / "src/ovc_opt_b/semantic_review.py"),
            "review_opt_c_semantic_sanity.py": sha256(Path(__file__).resolve()),
            "test_opt_c_semantic_review.py": sha256(ROOT / "tests/test_opt_c_semantic_review.py"),
        },
        "authority_boundary": "Semantic coherence and descriptive cohort support only. No statistical independence, hypothesis, edge, recommendation, risk, trade or execution authority.",
    }
    manifest = {**manifest_core, "manifest_hash": canonical_hash(manifest_core)}
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": manifest["status"],
        "manifest_hash": manifest["manifest_hash"],
        "reviewed_rows": manifest["reviewed_outcome_records"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
