from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime
from decimal import Decimal
import gzip
import itertools
import json
from pathlib import Path
import shutil
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from build_reference_level_registry import sha256  # noqa: E402
from ovc_opt_b import (  # noqa: E402
    cluster_balanced_metric,
    contrast_readiness,
    exclusive_arms,
    median_decimal,
    temporal_delta_status,
)
from run_complete_opt_b_replay import DeterministicJsonlGzipWriter, canonical_hash  # noqa: E402


CONTRACT_VERSION = "OPT-D-CONTRAST-0.1"
CLOCKS = ("15M", "2H")
HORIZONS = (1, 2, 4, 8, 12)
MONTHS = ("2026-01", "2026-02", "2026-03", "2026-04", "2026-05", "2026-06")


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


def primary_metric(direction: str) -> str:
    return (
        "direction_normalized_endpoint_return_pips"
        if direction in ("UP", "DOWN", "DIRECTION_SYMMETRY")
        else "raw_return_pips"
    )


def hash_ids(ids: list[str]) -> str | None:
    return canonical_hash(sorted(ids)) if ids else None


def arm_summary(
    rows: list[dict[str, object]],
    *,
    metric_field: str,
    cluster_by_outcome: dict[str, str],
) -> tuple[dict[str, object], list[dict[str, object]]]:
    balanced = cluster_balanced_metric(
        rows, cluster_by_outcome=cluster_by_outcome, metric_field=metric_field
    )
    values = [
        Decimal(str(row["measurements"][metric_field]))
        for row in rows if row["measurements"][metric_field] is not None
    ]
    clusters = {cluster_by_outcome[row["neutral_outcome_record_id"]] for row in rows}
    months = {datetime.fromisoformat(row["anchor_time"]).strftime("%Y-%m") for row in rows}
    opposite = [
        row for row in rows
        if row["measurements"]["direction_normalized_endpoint_return_pips"] is not None
        and Decimal(str(row["measurements"]["direction_normalized_endpoint_return_pips"])) < 0
    ]
    frontier = [
        row for row in rows if row["measurements"]["primary_frontier_lost_on_close"] is True
    ]
    counterexamples = [
        {"counterexample_type": "OPPOSITE_DIRECTION_ENDPOINT", "row": row} for row in opposite
    ] + [
        {"counterexample_type": "PRIMARY_FRONTIER_LOSS_ON_CLOSE", "row": row} for row in frontier
    ]
    summary = {
        "outcome_records": len(rows),
        "unique_event_anchors": len({row["event_anchor_id"] for row in rows}),
        "distinct_overlap_clusters": len(clusters),
        "distinct_anchor_months": len(months),
        "primary_metric_field": metric_field,
        "row_median_pips": str(median_decimal(values)) if values else None,
        "cluster_balanced_median_pips": balanced["cluster_balanced_median"],
        "cluster_medians_hash": canonical_hash(balanced["cluster_medians"]),
        "opposite_direction_endpoint_records": len(opposite),
        "opposite_direction_endpoint_record_ids_hash": hash_ids(
            [row["neutral_outcome_record_id"] for row in opposite]
        ),
        "primary_frontier_loss_on_close_records": len(frontier),
        "primary_frontier_loss_record_ids_hash": hash_ids(
            [row["neutral_outcome_record_id"] for row in frontier]
        ),
    }
    return summary, counterexamples


def month_metric(
    rows: list[dict[str, object]],
    month: str,
    metric_field: str,
    cluster_by_outcome: dict[str, str],
) -> dict[str, object]:
    subset = [row for row in rows if row["anchor_time"].startswith(month)]
    balanced = cluster_balanced_metric(
        subset, cluster_by_outcome=cluster_by_outcome, metric_field=metric_field
    )
    return {
        "outcome_records": len(subset),
        "distinct_overlap_clusters": len({cluster_by_outcome[row["neutral_outcome_record_id"]] for row in subset}),
        "cluster_balanced_median_pips": balanced["cluster_balanced_median"],
    }


def make_contrast(
    *,
    template: str,
    event_timeframe: str,
    horizon_hours: int,
    arm_a_cohort_id: str,
    arm_b_cohort_id: str,
    arm_a_rows: list[dict[str, object]],
    arm_b_rows: list[dict[str, object]],
    shared_outcome_ids: list[str],
    direction_context: str,
    cluster_by_outcome: dict[str, str],
) -> tuple[dict[str, object], list[dict[str, object]], list[dict[str, object]], list[dict[str, object]]]:
    metric = primary_metric(direction_context)
    arm_a, counter_a = arm_summary(arm_a_rows, metric_field=metric, cluster_by_outcome=cluster_by_outcome)
    arm_b, counter_b = arm_summary(arm_b_rows, metric_field=metric, cluster_by_outcome=cluster_by_outcome)
    readiness = contrast_readiness(
        arm_a["outcome_records"], arm_a["distinct_overlap_clusters"], arm_a["distinct_anchor_months"],
        arm_b["outcome_records"], arm_b["distinct_overlap_clusters"], arm_b["distinct_anchor_months"],
    )
    a_clusters = {cluster_by_outcome[row["neutral_outcome_record_id"]] for row in arm_a_rows}
    b_clusters = {cluster_by_outcome[row["neutral_outcome_record_id"]] for row in arm_b_rows}
    monthly_records = []
    eligible_deltas = []
    for month in MONTHS:
        a_month = month_metric(arm_a_rows, month, metric, cluster_by_outcome)
        b_month = month_metric(arm_b_rows, month, metric, cluster_by_outcome)
        delta = None
        eligible = (
            a_month["distinct_overlap_clusters"] >= 5
            and b_month["distinct_overlap_clusters"] >= 5
            and a_month["cluster_balanced_median_pips"] is not None
            and b_month["cluster_balanced_median_pips"] is not None
        )
        if eligible:
            delta_value = Decimal(a_month["cluster_balanced_median_pips"]) - Decimal(
                b_month["cluster_balanced_median_pips"]
            )
            delta = str(delta_value)
            eligible_deltas.append(delta_value)
        monthly_records.append({
            "month": month,
            "arm_a": a_month,
            "arm_b": b_month,
            "eligible_for_temporal_delta": eligible,
            "arm_a_minus_arm_b_cluster_balanced_median_pips": delta,
        })
    temporal = temporal_delta_status(eligible_deltas)
    a_median = arm_a["cluster_balanced_median_pips"]
    b_median = arm_b["cluster_balanced_median_pips"]
    delta = str(Decimal(a_median) - Decimal(b_median)) if a_median is not None and b_median is not None else None
    identity_core = {
        "contrast_template": template,
        "event_timeframe": event_timeframe,
        "horizon_hours": horizon_hours,
        "arm_a_cohort_id": arm_a_cohort_id,
        "arm_b_cohort_id": arm_b_cohort_id,
        "contract_version": CONTRACT_VERSION,
    }
    contrast_id = f"opt-d-contrast:{canonical_hash(identity_core)}"
    core = {
        **identity_core,
        "contrast_id": contrast_id,
        "direction_context": direction_context,
        "primary_metric_field": metric,
        "arm_a": arm_a,
        "arm_b": arm_b,
        "shared_outcome_records_excluded": len(shared_outcome_ids),
        "shared_outcome_record_ids_hash": hash_ids(shared_outcome_ids),
        "shared_overlap_clusters_between_exclusive_arms": len(a_clusters.intersection(b_clusters)),
        "shared_overlap_cluster_ids_hash": hash_ids(list(a_clusters.intersection(b_clusters))),
        "arm_a_minus_arm_b_cluster_balanced_median_pips": delta,
        "contrast_readiness": readiness,
        "temporal_stability": temporal,
        "authority": "DESCRIPTIVE_CONTRAST_ONLY",
    }
    counterexamples = []
    for arm_label, items in (("A", counter_a), ("B", counter_b)):
        for item in items:
            row = item["row"]
            counter_core = {
                "contrast_id": contrast_id,
                "arm": arm_label,
                "counterexample_type": item["counterexample_type"],
                "neutral_outcome_record_id": row["neutral_outcome_record_id"],
                "event_anchor_id": row["event_anchor_id"],
                "overlap_cluster_id": cluster_by_outcome[row["neutral_outcome_record_id"]],
                "horizon_hours": horizon_hours,
                "contract_version": CONTRACT_VERSION,
            }
            counterexamples.append({
                **counter_core,
                "contrast_counterexample_id": f"opt-d-counterexample:{canonical_hash(counter_core)}",
            })
    memberships = []
    for arm_label, rows in (("A", arm_a_rows), ("B", arm_b_rows)):
        for row in rows:
            membership_core = {
                "contrast_id": contrast_id,
                "contrast_stratum": f"ARM_{arm_label}",
                "neutral_outcome_record_id": row["neutral_outcome_record_id"],
                "overlap_cluster_id": cluster_by_outcome[row["neutral_outcome_record_id"]],
                "contract_version": CONTRACT_VERSION,
            }
            memberships.append({
                **membership_core,
                "contrast_membership_id": f"opt-d-contrast-membership:{canonical_hash(membership_core)}",
            })
    for outcome_id in shared_outcome_ids:
        membership_core = {
            "contrast_id": contrast_id,
            "contrast_stratum": "SHARED_EXCLUDED",
            "neutral_outcome_record_id": outcome_id,
            "overlap_cluster_id": cluster_by_outcome[outcome_id],
            "contract_version": CONTRACT_VERSION,
        }
        memberships.append({
            **membership_core,
            "contrast_membership_id": f"opt-d-contrast-membership:{canonical_hash(membership_core)}",
        })
    monthly = []
    for record in monthly_records:
        monthly_core = {"contrast_id": contrast_id, **record, "contract_version": CONTRACT_VERSION}
        monthly.append({
            **monthly_core,
            "monthly_contrast_record_id": f"opt-d-monthly-contrast:{canonical_hash(monthly_core)}",
        })
    return core, memberships, counterexamples, monthly


def write_report(output: Path, summary: dict[str, object]) -> Path:
    lines = [
        "# OVC OPT-D Cluster-Balanced Contrast Report v0.1",
        "",
        "**Status:** `CONTRAST CONSTRUCTION COMPLETE — DESCRIPTIVE ONLY`  ",
        f"**Contract:** `{CONTRACT_VERSION}`  ",
        "**Significance / edge / execution authority:** `NONE`",
        "",
        "## Exhaustive contrast inventory",
        "",
        "| Template | Contrasts |",
        "|---|---:|",
    ]
    for template, count in summary["template_counts"].items():
        lines.append(f"| `{template}` | {count:,} |")
    lines.extend([
        "",
        "## Post-exclusivity readiness",
        "",
        "| Status | Contrasts |",
        "|---|---:|",
    ])
    for status, count in summary["readiness_counts"].items():
        lines.append(f"| `{status}` | {count:,} |")
    lines.extend([
        "",
        "## Monthly delta stability",
        "",
        "| Status | Contrasts |",
        "|---|---:|",
    ])
    for status, count in summary["temporal_status_counts"].items():
        lines.append(f"| `{status}` | {count:,} |")
    lines.extend([
        "",
        f"Materialized counterexample memberships: **{summary['counterexample_records']:,}**. These are retained observations and may repeat across predeclared contrasts; they are not trade losses.",
        "",
        "Every family comparison excludes shared multi-family outcomes from both arms and preserves them in `SHARED_EXCLUDED`. Every arm summary gives equal descriptive mass to each represented overlap cluster. Monthly deltas require at least five clusters in both arms.",
        "",
        "## Gate decision",
        "",
        "Contrast construction is complete. Only `DESCRIPTIVE_CONTRAST_READY` records with adequate monthly coverage may proceed to repeated-story evidence packs. Sign consistency is descriptive and cannot be converted into probability, edge, recommendation or execution authority.",
    ])
    path = output / "OVC_OPT_D_CLUSTER_BALANCED_CONTRAST_REPORT_v0_1.md"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cohort-root", type=Path, required=True)
    parser.add_argument("--measurement-root", type=Path, required=True)
    parser.add_argument("--ledger-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    cohort_root = args.cohort_root.resolve()
    measurement_root = args.measurement_root.resolve()
    ledger_root = args.ledger_root.resolve()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    manifest_path = output / "OPT_D_CLUSTER_BALANCED_CONTRAST_MANIFEST.json"
    if manifest_path.exists():
        raise FileExistsError("OPT-D contrast release already finalized")

    cohort_manifest = verify_manifest(cohort_root, "OPT_D_CLUSTER_AWARE_COHORT_MANIFEST.json")
    measurement_manifest = verify_manifest(
        measurement_root, "OPT_C_NEUTRAL_OUTCOME_MEASUREMENT_MANIFEST.json"
    )
    ledger_manifest = verify_manifest(ledger_root, "OPT_C_EVENT_ANCHOR_LEDGER_MANIFEST.json")
    if cohort_manifest["parent_measurement_manifest_hash"] != measurement_manifest["manifest_hash"]:
        raise ValueError("cohort/measurement lineage mismatch")
    if cohort_manifest["event_ledger_manifest_hash"] != ledger_manifest["manifest_hash"]:
        raise ValueError("cohort/event-ledger lineage mismatch")

    rows = {
        row["neutral_outcome_record_id"]: row
        for clock in CLOCKS
        for row in load_gzip(measurement_root / f"opt_c_neutral_outcomes_{clock.lower()}.jsonl.gz")
    }
    assignments = load_gzip(cohort_root / "opt_d_outcome_cluster_assignments.jsonl.gz")
    cluster_by_outcome = {row["neutral_outcome_record_id"]: row["overlap_cluster_id"] for row in assignments}
    memberships = load_gzip(cohort_root / "opt_d_cohort_memberships.jsonl.gz")
    outcomes_by_cohort = defaultdict(list)
    for membership in memberships:
        outcomes_by_cohort[membership["cohort_id"]].append(membership["neutral_outcome_record_id"])
    base = load_gzip(cohort_root / "opt_d_base_cohort_registry.jsonl.gz")
    signatures = load_gzip(cohort_root / "opt_d_signature_cohort_registry.jsonl.gz")
    ready_base = [row for row in base if row["cohort_readiness"] == "DESCRIPTIVE_COHORT_READY"]
    ready_signatures = [row for row in signatures if row["cohort_readiness"] == "DESCRIPTIVE_COHORT_READY"]

    candidates = []
    base_index = {
        (row["event_timeframe"], row["horizon_hours"], row["event_family"], row["event_direction"]): row
        for row in ready_base
    }
    for clock in CLOCKS:
        for horizon in HORIZONS:
            for family in sorted({row["event_family"] for row in ready_base}):
                up = base_index.get((clock, horizon, family, "UP"))
                down = base_index.get((clock, horizon, family, "DOWN"))
                if up and down:
                    candidates.append(("BASE_DIRECTION_SYMMETRY", clock, horizon, up, down, "DIRECTION_SYMMETRY"))
    for clock in CLOCKS:
        for horizon in HORIZONS:
            for direction in ("UP", "DOWN", "MIXED", "NONE"):
                group = sorted(
                    [
                        row for row in ready_base
                        if (row["event_timeframe"], row["horizon_hours"], row["event_direction"])
                        == (clock, horizon, direction)
                    ],
                    key=lambda row: row["event_family"],
                )
                for arm_a, arm_b in itertools.combinations(group, 2):
                    candidates.append(("BASE_FAMILY_CONTEXT", clock, horizon, arm_a, arm_b, direction))
    signature_direction = {}
    for record in ready_signatures:
        directions = {rows[outcome_id]["event_direction"] for outcome_id in outcomes_by_cohort[record["cohort_id"]]}
        if len(directions) != 1:
            raise ValueError("exact semantic signature spans multiple event directions")
        signature_direction[record["cohort_id"]] = next(iter(directions))
    for clock in CLOCKS:
        for horizon in HORIZONS:
            for direction in ("UP", "DOWN", "MIXED", "NONE"):
                group = sorted(
                    [
                        row for row in ready_signatures
                        if (row["event_timeframe"], row["horizon_hours"], signature_direction[row["cohort_id"]])
                        == (clock, horizon, direction)
                    ],
                    key=lambda row: row["semantic_signature_hash"],
                )
                for arm_a, arm_b in itertools.combinations(group, 2):
                    candidates.append(("EXACT_SIGNATURE_CONTEXT", clock, horizon, arm_a, arm_b, direction))

    contrast_records = []
    membership_records = []
    counterexample_records = []
    monthly_records = []
    for template, clock, horizon, arm_a, arm_b, direction in candidates:
        a_rows = [rows[outcome_id] for outcome_id in outcomes_by_cohort[arm_a["cohort_id"]]]
        b_rows = [rows[outcome_id] for outcome_id in outcomes_by_cohort[arm_b["cohort_id"]]]
        if template == "BASE_FAMILY_CONTEXT":
            a_rows, b_rows, shared = exclusive_arms(a_rows, b_rows)
        else:
            shared = []
            if set(row["neutral_outcome_record_id"] for row in a_rows).intersection(
                row["neutral_outcome_record_id"] for row in b_rows
            ):
                raise ValueError("non-family contrast arms must be outcome-exclusive")
        contrast, contrast_memberships, counterexamples, monthly = make_contrast(
            template=template,
            event_timeframe=clock,
            horizon_hours=horizon,
            arm_a_cohort_id=arm_a["cohort_id"],
            arm_b_cohort_id=arm_b["cohort_id"],
            arm_a_rows=list(a_rows),
            arm_b_rows=list(b_rows),
            shared_outcome_ids=shared,
            direction_context=direction,
            cluster_by_outcome=cluster_by_outcome,
        )
        contrast_records.append(contrast)
        membership_records.extend(contrast_memberships)
        counterexample_records.extend(counterexamples)
        monthly_records.extend(monthly)

    writers = {
        "contrast": DeterministicJsonlGzipWriter(output / "opt_d_contrast_registry.jsonl.gz"),
        "membership": DeterministicJsonlGzipWriter(output / "opt_d_contrast_memberships.jsonl.gz"),
        "counterexample": DeterministicJsonlGzipWriter(output / "opt_d_contrast_counterexamples.jsonl.gz"),
        "monthly": DeterministicJsonlGzipWriter(output / "opt_d_monthly_contrast_stability.jsonl.gz"),
    }
    for record in contrast_records:
        writers["contrast"].write(record)
    for record in sorted(membership_records, key=lambda row: row["contrast_membership_id"]):
        writers["membership"].write(record)
    for record in sorted(counterexample_records, key=lambda row: row["contrast_counterexample_id"]):
        writers["counterexample"].write(record)
    for record in monthly_records:
        writers["monthly"].write(record)
    artifacts = []
    stream_metadata = {}
    for name, writer in writers.items():
        writer.close()
        artifacts.append({"path": writer.path.name, "sha256": sha256(writer.path), "size_bytes": writer.path.stat().st_size})
        stream_metadata[f"{name}_records"] = writer.count
        stream_metadata[f"{name}_stream_canonical_jsonl_hash"] = writer.canonical_jsonl_hash

    summary = {
        "contrasts": len(contrast_records),
        "template_counts": dict(sorted(Counter(row["contrast_template"] for row in contrast_records).items())),
        "readiness_counts": dict(sorted(Counter(row["contrast_readiness"] for row in contrast_records).items())),
        "temporal_status_counts": dict(sorted(Counter(
            row["temporal_stability"]["temporal_delta_status"] for row in contrast_records
        ).items())),
        "counterexample_records": len(counterexample_records),
        "counterexample_type_counts": dict(sorted(Counter(
            row["counterexample_type"] for row in counterexample_records
        ).items())),
        "shared_excluded_memberships": sum(
            row["contrast_stratum"] == "SHARED_EXCLUDED" for row in membership_records
        ),
        "stream_metadata": stream_metadata,
    }
    summary_path = output / "opt_d_cluster_balanced_contrast_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    artifacts.append({"path": summary_path.name, "sha256": sha256(summary_path), "size_bytes": summary_path.stat().st_size})
    report = write_report(output, summary)
    artifacts.append({"path": report.name, "sha256": sha256(report), "size_bytes": report.stat().st_size})
    for source in (
        ROOT / "contracts/OVC_OPT_D_CLUSTER_BALANCED_CONTRAST_CONTRACT_v0_1.md",
        ROOT / "contracts/OVC_OPT_D_CLUSTER_AWARE_COHORT_CONTRACT_v0_1.md",
    ):
        destination = output / source.name
        shutil.copy2(source, destination)
        artifacts.append({"path": destination.name, "sha256": sha256(destination), "size_bytes": destination.stat().st_size})

    manifest_core = {
        "release_id": "OPT-D-CLUSTER-CONTRASTS-GBPUSD-2026H1-v0.1",
        "status": "CONTRAST_CONSTRUCTION_COMPLETE_DESCRIPTIVE_ONLY",
        "generated_date": "2026-07-19",
        "contrast_contract_version": CONTRACT_VERSION,
        "parent_cohort_manifest_hash": cohort_manifest["manifest_hash"],
        "parent_measurement_manifest_hash": measurement_manifest["manifest_hash"],
        "event_ledger_manifest_hash": ledger_manifest["manifest_hash"],
        "horizons_hours": list(HORIZONS),
        "coverage_only_horizons_hours": [24],
        "blocked_horizons_hours": [48],
        "contrast_templates": [
            "BASE_DIRECTION_SYMMETRY", "BASE_FAMILY_CONTEXT", "EXACT_SIGNATURE_CONTEXT"
        ],
        "results": summary,
        "artifacts": artifacts,
        "implementation_hashes": {
            "contrasts.py": sha256(ROOT / "src/ovc_opt_b/contrasts.py"),
            "build_opt_d_cluster_contrasts.py": sha256(Path(__file__).resolve()),
            "test_opt_d_contrasts.py": sha256(ROOT / "tests/test_opt_d_contrasts.py"),
        },
        "authority_boundary": "Exhaustive cluster-balanced descriptive contrasts only. No independence, significance, probability, edge, recommendation, risk, trade or execution authority.",
    }
    manifest = {**manifest_core, "manifest_hash": canonical_hash(manifest_core)}
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": manifest["status"],
        "manifest_hash": manifest["manifest_hash"],
        "contrasts": len(contrast_records),
    }, sort_keys=True))


if __name__ == "__main__":
    main()
