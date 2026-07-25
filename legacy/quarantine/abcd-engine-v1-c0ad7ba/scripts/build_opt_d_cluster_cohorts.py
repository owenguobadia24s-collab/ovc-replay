from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime
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
    build_overlap_clusters,
    cohort_readiness,
    descriptive_band,
    semantic_event_signature,
)
from run_complete_opt_b_replay import DeterministicJsonlGzipWriter, canonical_hash  # noqa: E402


CONTRACT_VERSION = "OPT-D-COHORT-0.1"
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


def distribution(rows: list[dict[str, object]], field: str) -> dict[str, object]:
    values = [
        Decimal(str(row["measurements"][field]))
        for row in rows
        if row["measurements"][field] is not None
    ]
    return {
        "count": len(values),
        "p10": percentile(values, Decimal("0.10")),
        "median": percentile(values, Decimal("0.50")),
        "p90": percentile(values, Decimal("0.90")),
    }


def rate(numerator: int, denominator: int) -> float | None:
    return round(numerator * 100 / denominator, 4) if denominator else None


def cohort_evidence(rows: list[dict[str, object]], cluster_by_outcome: dict[str, str]) -> dict[str, object]:
    cluster_counts = Counter(cluster_by_outcome[row["neutral_outcome_record_id"]] for row in rows)
    months = Counter(datetime.fromisoformat(row["anchor_time"]).strftime("%Y-%m") for row in rows)
    directional = [row for row in rows if row["event_direction"] in ("UP", "DOWN")]
    frontier = [row for row in directional if row["measurements"]["primary_frontier_type"] is not None]
    row_count = len(rows)
    cluster_count = len(cluster_counts)
    return {
        "outcome_records": row_count,
        "unique_event_anchors": len({row["event_anchor_id"] for row in rows}),
        "distinct_overlap_clusters": cluster_count,
        "row_support_band": descriptive_band(row_count),
        "cluster_support_band": descriptive_band(cluster_count),
        "distinct_anchor_months": len(months),
        "anchor_counts_by_month": dict(sorted(months.items())),
        "cohort_readiness": cohort_readiness(row_count, cluster_count, len(months)),
        "largest_cluster_membership": max(cluster_counts.values(), default=0),
        "largest_cluster_share_pct": rate(max(cluster_counts.values(), default=0), row_count),
        "singleton_membership_clusters": sum(count == 1 for count in cluster_counts.values()),
        "raw_return_pips": distribution(rows, "raw_return_pips"),
        "direction_normalized_endpoint_return_pips": distribution(
            rows, "direction_normalized_endpoint_return_pips"
        ),
        "direction_normalized_favorable_excursion_pips": distribution(
            rows, "direction_normalized_favorable_excursion_pips"
        ),
        "direction_normalized_adverse_excursion_pips": distribution(
            rows, "direction_normalized_adverse_excursion_pips"
        ),
        "directional_records": len(directional),
        "primary_frontier_applicable_records": len(frontier),
        "primary_frontier_retested_records": sum(
            row["measurements"]["primary_frontier_retested"] is True for row in frontier
        ),
        "primary_frontier_lost_on_close_records": sum(
            row["measurements"]["primary_frontier_lost_on_close"] is True for row in frontier
        ),
    }


def base_cohort_id(clock: str, horizon: int, family: str, direction: str) -> str:
    core = {
        "cohort_layer": "BASE",
        "event_timeframe": clock,
        "horizon_hours": horizon,
        "event_family": family,
        "event_direction": direction,
        "contract_version": CONTRACT_VERSION,
    }
    return f"opt-d-base-cohort:{canonical_hash(core)}"


def signature_cohort_id(clock: str, horizon: int, signature_hash: str) -> str:
    core = {
        "cohort_layer": "EXACT_SEMANTIC_SIGNATURE",
        "event_timeframe": clock,
        "horizon_hours": horizon,
        "semantic_signature_hash": signature_hash,
        "contract_version": CONTRACT_VERSION,
    }
    return f"opt-d-signature-cohort:{canonical_hash(core)}"


def build_clusters(rows: list[dict[str, object]], output: Path):
    cluster_writer = DeterministicJsonlGzipWriter(output / "opt_d_overlap_clusters.jsonl.gz")
    assignment_writer = DeterministicJsonlGzipWriter(output / "opt_d_outcome_cluster_assignments.jsonl.gz")
    cluster_by_outcome: dict[str, str] = {}
    summaries = {}
    all_clusters = []
    for horizon in HORIZONS:
        horizon_rows = [row for row in rows if row["horizon_hours"] == horizon]
        clusters, assignments = build_overlap_clusters(horizon_rows)
        cluster_by_outcome.update(assignments)
        all_clusters.extend(clusters)
        sizes = sorted(cluster["outcome_records"] for cluster in clusters)
        summaries[str(horizon)] = {
            "outcome_records": len(horizon_rows),
            "overlap_clusters": len(clusters),
            "singleton_clusters": sum(size == 1 for size in sizes),
            "cross_clock_clusters": sum(len(cluster["event_timeframe_counts"]) > 1 for cluster in clusters),
            "median_cluster_size": percentile([Decimal(size) for size in sizes], Decimal("0.50")),
            "maximum_cluster_size": max(sizes, default=0),
        }
    for cluster in sorted(all_clusters, key=lambda row: (row["horizon_hours"], row["cluster_start_time"])):
        cluster_writer.write({**cluster, "contract_version": CONTRACT_VERSION})
    for row in sorted(rows, key=lambda item: (item["horizon_hours"], item["anchor_time"], item["event_timeframe"])):
        core = {
            "neutral_outcome_record_id": row["neutral_outcome_record_id"],
            "event_anchor_id": row["event_anchor_id"],
            "event_timeframe": row["event_timeframe"],
            "horizon_hours": row["horizon_hours"],
            "anchor_time": row["anchor_time"],
            "endpoint_time": row["endpoint_time"],
            "overlap_cluster_id": cluster_by_outcome[row["neutral_outcome_record_id"]],
            "contract_version": CONTRACT_VERSION,
        }
        assignment_writer.write({**core, "cluster_assignment_id": f"opt-d-assignment:{canonical_hash(core)}"})
    cluster_writer.close()
    assignment_writer.close()
    artifacts = [
        {"path": cluster_writer.path.name, "sha256": sha256(cluster_writer.path), "size_bytes": cluster_writer.path.stat().st_size},
        {"path": assignment_writer.path.name, "sha256": sha256(assignment_writer.path), "size_bytes": assignment_writer.path.stat().st_size},
    ]
    return summaries, cluster_by_outcome, artifacts, {
        "cluster_stream_canonical_jsonl_hash": cluster_writer.canonical_jsonl_hash,
        "assignment_stream_canonical_jsonl_hash": assignment_writer.canonical_jsonl_hash,
        "cluster_records": cluster_writer.count,
        "assignment_records": assignment_writer.count,
    }


def build_cohorts(
    rows_by_clock: dict[str, list[dict[str, object]]],
    anchors: dict[str, dict[str, object]],
    cluster_by_outcome: dict[str, str],
    output: Path,
):
    base_writer = DeterministicJsonlGzipWriter(output / "opt_d_base_cohort_registry.jsonl.gz")
    signature_writer = DeterministicJsonlGzipWriter(output / "opt_d_signature_cohort_registry.jsonl.gz")
    membership_writer = DeterministicJsonlGzipWriter(output / "opt_d_cohort_memberships.jsonl.gz")
    base_records = []
    signature_records = []
    signature_groups = defaultdict(list)

    for clock in CLOCKS:
        for row in rows_by_clock[clock]:
            signature = semantic_event_signature(anchors[row["event_anchor_id"]])
            signature_groups[(clock, row["horizon_hours"], signature["semantic_signature_hash"])].append(row)
            cohort_ids = [
                ("BASE", base_cohort_id(clock, row["horizon_hours"], family, row["event_direction"]))
                for family in row["event_families"]
            ]
            cohort_ids.append((
                "EXACT_SEMANTIC_SIGNATURE",
                signature_cohort_id(clock, row["horizon_hours"], signature["semantic_signature_hash"]),
            ))
            for layer, cohort_id in cohort_ids:
                core = {
                    "cohort_layer": layer,
                    "cohort_id": cohort_id,
                    "neutral_outcome_record_id": row["neutral_outcome_record_id"],
                    "event_anchor_id": row["event_anchor_id"],
                    "overlap_cluster_id": cluster_by_outcome[row["neutral_outcome_record_id"]],
                    "event_timeframe": clock,
                    "horizon_hours": row["horizon_hours"],
                    "contract_version": CONTRACT_VERSION,
                }
                membership_writer.write({**core, "cohort_membership_id": f"opt-d-membership:{canonical_hash(core)}"})

    for clock in CLOCKS:
        for horizon in HORIZONS:
            horizon_rows = [row for row in rows_by_clock[clock] if row["horizon_hours"] == horizon]
            for family in FAMILIES:
                for direction in DIRECTIONS:
                    subset = [
                        row for row in horizon_rows
                        if family in row["event_families"] and row["event_direction"] == direction
                    ]
                    core = {
                        "cohort_layer": "BASE",
                        "cohort_id": base_cohort_id(clock, horizon, family, direction),
                        "event_timeframe": clock,
                        "horizon_hours": horizon,
                        "event_family": family,
                        "event_direction": direction,
                        **cohort_evidence(subset, cluster_by_outcome),
                        "membership_rule": "MULTI_FAMILY_ROWS_APPEAR_IN_EACH_NAMED_FAMILY_COHORT_NOT_ADDITIVE",
                        "contract_version": CONTRACT_VERSION,
                    }
                    base_writer.write(core)
                    base_records.append(core)

    for (clock, horizon, signature_hash), subset in sorted(signature_groups.items()):
        signature = semantic_event_signature(anchors[subset[0]["event_anchor_id"]])
        core = {
            "cohort_layer": "EXACT_SEMANTIC_SIGNATURE",
            "cohort_id": signature_cohort_id(clock, horizon, signature_hash),
            "event_timeframe": clock,
            "horizon_hours": horizon,
            **signature,
            **cohort_evidence(subset, cluster_by_outcome),
            "contract_version": CONTRACT_VERSION,
        }
        signature_writer.write(core)
        signature_records.append(core)
    base_writer.close()
    signature_writer.close()
    membership_writer.close()
    artifacts = [
        {"path": base_writer.path.name, "sha256": sha256(base_writer.path), "size_bytes": base_writer.path.stat().st_size},
        {"path": signature_writer.path.name, "sha256": sha256(signature_writer.path), "size_bytes": signature_writer.path.stat().st_size},
        {"path": membership_writer.path.name, "sha256": sha256(membership_writer.path), "size_bytes": membership_writer.path.stat().st_size},
    ]
    metadata = {
        "base_cohort_records": base_writer.count,
        "signature_cohort_records": signature_writer.count,
        "membership_records": membership_writer.count,
        "base_cohort_stream_canonical_jsonl_hash": base_writer.canonical_jsonl_hash,
        "signature_cohort_stream_canonical_jsonl_hash": signature_writer.canonical_jsonl_hash,
        "membership_stream_canonical_jsonl_hash": membership_writer.canonical_jsonl_hash,
    }
    return base_records, signature_records, artifacts, metadata


def summarize_registry(records: list[dict[str, object]]) -> dict[str, object]:
    readiness = Counter(row["cohort_readiness"] for row in records)
    row_bands = Counter(row["row_support_band"] for row in records)
    cluster_bands = Counter(row["cluster_support_band"] for row in records)
    by_family = defaultdict(Counter)
    for row in records:
        if row["cohort_layer"] == "BASE":
            by_family[row["event_family"]][row["cohort_readiness"]] += 1
    return {
        "cohorts": len(records),
        "readiness_counts": dict(sorted(readiness.items())),
        "row_support_band_counts": dict(sorted(row_bands.items())),
        "cluster_support_band_counts": dict(sorted(cluster_bands.items())),
        "readiness_counts_by_family": {
            family: dict(sorted(counts.items())) for family, counts in sorted(by_family.items())
        },
    }


def write_report(output: Path, results: dict[str, object]) -> Path:
    lines = [
        "# OVC OPT-D Cluster-Aware Cohort Release v0.1",
        "",
        "**Status:** `COHORT FORMATION COMPLETE — DESCRIPTIVE ONLY`  ",
        f"**Contract:** `{CONTRACT_VERSION}`  ",
        "**Edge / trade / execution authority:** `NONE`",
        "",
        "## Cross-clock overlap clusters",
        "",
        "| Horizon | Outcome rows | Clusters | Median size | Maximum size | Cross-clock clusters |",
        "|---:|---:|---:|---:|---:|---:|",
    ]
    for horizon in HORIZONS:
        item = results["cluster_summary"][str(horizon)]
        lines.append(
            f"| {horizon}h | {item['outcome_records']:,} | {item['overlap_clusters']:,} | "
            f"{item['median_cluster_size']} | {item['maximum_cluster_size']:,} | {item['cross_clock_clusters']:,} |"
        )
    lines.extend([
        "",
        "Clusters are connected components of half-open forward windows across both event clocks. They prevent overlapping 15M and 2H anchors from being presented as separate support. Cluster count is still not an independence claim.",
        "",
        "## Base-cohort readiness",
        "",
        "| Readiness | Cohorts |",
        "|---|---:|",
    ])
    for status, count in results["base_cohorts"]["readiness_counts"].items():
        lines.append(f"| `{status}` | {count:,} |")
    lines.extend([
        "",
        "## Exact-signature readiness",
        "",
        "| Readiness | Cohorts |",
        "|---|---:|",
    ])
    for status, count in results["signature_cohorts"]["readiness_counts"].items():
        lines.append(f"| `{status}` | {count:,} |")
    lines.extend([
        "",
        "Exact semantic signatures use the set of family/subtype/direction components. Level IDs do not fragment the vocabulary; multi-family base memberships remain explicit and non-additive.",
        "",
        "## Gate decision",
        "",
        "The cohort formation layer is complete. Only cohorts labelled `DESCRIPTIVE_COHORT_READY` may enter the first repeated-story comparison design; limited cohorts remain labelled, and all inventory-only cohorts are prohibited from comparison. The next gate must freeze contrast construction, counterexample retention and temporal validation without treating clusters as statistically independent.",
    ])
    path = output / "OVC_OPT_D_CLUSTER_AWARE_COHORT_REPORT_v0_1.md"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--measurement-root", type=Path, required=True)
    parser.add_argument("--semantic-root", type=Path, required=True)
    parser.add_argument("--ledger-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    measurement_root = args.measurement_root.resolve()
    semantic_root = args.semantic_root.resolve()
    ledger_root = args.ledger_root.resolve()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    manifest_path = output / "OPT_D_CLUSTER_AWARE_COHORT_MANIFEST.json"
    if manifest_path.exists():
        raise FileExistsError("OPT-D cohort release already finalized")

    measurement_manifest = verify_manifest(
        measurement_root, "OPT_C_NEUTRAL_OUTCOME_MEASUREMENT_MANIFEST.json"
    )
    semantic_manifest = verify_manifest(semantic_root, "OPT_C_SEMANTIC_SANITY_REVIEW_MANIFEST.json")
    ledger_manifest = verify_manifest(ledger_root, "OPT_C_EVENT_ANCHOR_LEDGER_MANIFEST.json")
    if semantic_manifest["parent_measurement_manifest_hash"] != measurement_manifest["manifest_hash"]:
        raise ValueError("semantic review/measurement lineage mismatch")
    if measurement_manifest["event_ledger_manifest_hash"] != ledger_manifest["manifest_hash"]:
        raise ValueError("measurement/event-ledger lineage mismatch")
    if semantic_manifest["status"] != "PASS_WITH_OVERLAP_AND_SPARSE_COHORT_CONTROLS":
        raise ValueError("OPT-C semantic gate has not passed")

    rows_by_clock = {
        clock: load_gzip(measurement_root / f"opt_c_neutral_outcomes_{clock.lower()}.jsonl.gz")
        for clock in CLOCKS
    }
    all_rows = [row for clock in CLOCKS for row in rows_by_clock[clock]]
    anchors = {
        row["event_anchor_id"]: row
        for clock in CLOCKS
        for row in load_gzip(ledger_root / f"opt_c_event_anchor_ledger_{clock.lower()}.jsonl.gz")
    }
    if len(all_rows) != int(measurement_manifest["total_outcome_records"]):
        raise ValueError("OPT-C measurement manifest/cardinality mismatch")

    cluster_summary, cluster_by_outcome, artifacts, cluster_metadata = build_clusters(all_rows, output)
    base_records, signature_records, cohort_artifacts, cohort_metadata = build_cohorts(
        rows_by_clock, anchors, cluster_by_outcome, output
    )
    artifacts.extend(cohort_artifacts)

    semantic_matrix = {
        (row["event_timeframe"], row["horizon_hours"], row["event_family"], row["event_direction"]): row
        for row in load_gzip(semantic_root / "opt_c_semantic_cohort_support_matrix.jsonl.gz")
    }
    for row in base_records:
        key = (row["event_timeframe"], row["horizon_hours"], row["event_family"], row["event_direction"])
        if row["outcome_records"] != semantic_matrix[key]["outcome_records"]:
            raise ValueError("OPT-D base cohort does not preserve OPT-C support count")

    results = {
        "cluster_summary": cluster_summary,
        "base_cohorts": summarize_registry(base_records),
        "signature_cohorts": summarize_registry(signature_records),
        "stream_metadata": {**cluster_metadata, **cohort_metadata},
    }
    summary_path = output / "opt_d_cluster_aware_cohort_summary.json"
    summary_path.write_text(json.dumps(results, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    artifacts.append({"path": summary_path.name, "sha256": sha256(summary_path), "size_bytes": summary_path.stat().st_size})
    report = write_report(output, results)
    artifacts.append({"path": report.name, "sha256": sha256(report), "size_bytes": report.stat().st_size})
    for source in (
        ROOT / "contracts/OVC_OPT_D_CLUSTER_AWARE_COHORT_CONTRACT_v0_1.md",
        ROOT / "contracts/OVC_OPT_C_SEMANTIC_SANITY_REVIEW_CONTRACT_v0_1.md",
    ):
        destination = output / source.name
        shutil.copy2(source, destination)
        artifacts.append({"path": destination.name, "sha256": sha256(destination), "size_bytes": destination.stat().st_size})

    manifest_core = {
        "release_id": "OPT-D-CLUSTER-COHORTS-GBPUSD-2026H1-v0.1",
        "status": "COHORT_FORMATION_COMPLETE_DESCRIPTIVE_ONLY",
        "generated_date": "2026-07-19",
        "cohort_contract_version": CONTRACT_VERSION,
        "parent_semantic_review_manifest_hash": semantic_manifest["manifest_hash"],
        "parent_measurement_manifest_hash": measurement_manifest["manifest_hash"],
        "event_ledger_manifest_hash": ledger_manifest["manifest_hash"],
        "reviewed_outcome_records": len(all_rows),
        "horizons_hours": list(HORIZONS),
        "coverage_only_horizons_hours": [24],
        "blocked_horizons_hours": [48],
        "overlap_interval_semantics": "HALF_OPEN_TRANSITIVE_CONNECTED_COMPONENTS_CROSS_CLOCK_PER_HORIZON",
        "results": results,
        "artifacts": artifacts,
        "implementation_hashes": {
            "cohorts.py": sha256(ROOT / "src/ovc_opt_b/cohorts.py"),
            "build_opt_d_cluster_cohorts.py": sha256(Path(__file__).resolve()),
            "test_opt_d_cohorts.py": sha256(ROOT / "tests/test_opt_d_cohorts.py"),
        },
        "authority_boundary": "Deterministic cohort formation and descriptive support only. No independence, significance, threshold, edge, recommendation, risk, trade or execution authority.",
    }
    manifest = {**manifest_core, "manifest_hash": canonical_hash(manifest_core)}
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": manifest["status"],
        "manifest_hash": manifest["manifest_hash"],
        "base_cohorts": len(base_records),
        "signature_cohorts": len(signature_records),
    }, sort_keys=True))


if __name__ == "__main__":
    main()
