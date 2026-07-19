from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime
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
    STORY_VERSION,
    qualitative_story_features,
    select_representative_cases,
    semantic_event_signature,
)
from run_complete_opt_b_replay import DeterministicJsonlGzipWriter, canonical_hash  # noqa: E402


CONTRACT_VERSION = "OPT-D-STORY-0.1"
CLOCKS = ("15M", "2H")


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


def hash_ids(ids: list[str]) -> str | None:
    return canonical_hash(sorted(ids)) if ids else None


def story_lineage(row: dict[str, object], semantic_signature: dict[str, object]) -> dict[str, object]:
    endpoint = row["endpoint_b_state_snapshot"]
    endpoint_pattern = {
        key: endpoint[key]
        for key in (
            "acceptance_event_state",
            "displacement_state",
            "compression_state",
            "interaction_state",
            "quality_state",
        )
    }
    transition_axes = sorted(
        axis for axis, count in row["transition_lineage"]["counts_by_axis"].items()
        if int(count) > 0
    )
    return {
        "exact_semantic_signature_hash": semantic_signature["semantic_signature_hash"],
        "endpoint_b_state_pattern_hash": canonical_hash(endpoint_pattern),
        "transition_axes_pattern_hash": canonical_hash(transition_axes),
        "transition_axes_present": transition_axes,
    }


def repetition_status(distinct_clusters: int) -> str:
    if distinct_clusters == 1:
        return "SINGLETON_INVENTORY"
    if distinct_clusters == 2:
        return "REPEATED_MINIMAL_SUPPORT"
    if distinct_clusters < 10:
        return "REPEATED_LIMITED_SUPPORT"
    return "REPEATED_DESCRIPTIVE_SUPPORT"


def archetype_summary(
    outcome_ids: list[str],
    *,
    rows: dict[str, dict[str, object]],
    story_by_outcome: dict[str, dict[str, object]],
    cluster_by_outcome: dict[str, str],
) -> list[dict[str, object]]:
    grouped = defaultdict(list)
    for outcome_id in outcome_ids:
        grouped[story_by_outcome[outcome_id]["story_archetype_id"]].append(outcome_id)
    result = []
    for archetype_id, members in grouped.items():
        result.append({
            "story_archetype_id": archetype_id,
            "outcome_records": len(members),
            "distinct_overlap_clusters": len({cluster_by_outcome[item] for item in members}),
            "distinct_anchor_months": len({rows[item]["anchor_time"][:7] for item in members}),
            "outcome_record_ids_hash": hash_ids(members),
        })
    return sorted(
        result,
        key=lambda item: (
            -item["distinct_overlap_clusters"],
            -item["outcome_records"],
            item["story_archetype_id"],
        ),
    )


def arm_pack(
    outcome_ids: list[str],
    *,
    contrast_id: str,
    arm: str,
    metric_field: str,
    rows: dict[str, dict[str, object]],
    story_by_outcome: dict[str, dict[str, object]],
    cluster_by_outcome: dict[str, str],
    counterexamples_by_contrast_arm: dict[tuple[str, str], list[dict[str, object]]],
) -> tuple[dict[str, object], list[dict[str, object]]]:
    arm_rows = [rows[outcome_id] for outcome_id in outcome_ids]
    archetypes = archetype_summary(
        outcome_ids,
        rows=rows,
        story_by_outcome=story_by_outcome,
        cluster_by_outcome=cluster_by_outcome,
    )
    selected = select_representative_cases(
        arm_rows,
        cluster_by_outcome=cluster_by_outcome,
        metric_field=metric_field,
    )
    case_records = []
    for case in selected:
        outcome_id = case["neutral_outcome_record_id"]
        row = rows[outcome_id]
        core = {
            "contrast_id": contrast_id,
            "arm": arm,
            **case,
            "story_archetype_id": story_by_outcome[outcome_id]["story_archetype_id"],
            "event_timeframe": row["event_timeframe"],
            "horizon_hours": row["horizon_hours"],
            "anchor_time": row["anchor_time"],
            "endpoint_time": row["endpoint_time"],
            "event_direction": row["event_direction"],
            "event_families": row["event_families"],
            "story_contract_version": CONTRACT_VERSION,
            "selection_authority": "FIXED_CLUSTER_BALANCED_CASE_ROLE_ONLY",
        }
        case_records.append({**core, "story_case_id": f"opt-d-story-case:{canonical_hash(core)}"})
    counterexamples = counterexamples_by_contrast_arm[(contrast_id, arm)]
    type_counts = Counter(item["counterexample_type"] for item in counterexamples)
    opposite = [
        item["neutral_outcome_record_id"] for item in counterexamples
        if item["counterexample_type"] == "OPPOSITE_DIRECTION_ENDPOINT"
    ]
    frontier = [
        item["neutral_outcome_record_id"] for item in counterexamples
        if item["counterexample_type"] == "PRIMARY_FRONTIER_LOSS_ON_CLOSE"
    ]
    absent_frontier = [
        outcome_id for outcome_id in outcome_ids
        if rows[outcome_id]["event_direction"] in ("UP", "DOWN")
        and rows[outcome_id]["measurements"]["primary_frontier_type"] is None
    ]
    pack = {
        "outcome_records": len(outcome_ids),
        "distinct_overlap_clusters": len({cluster_by_outcome[item] for item in outcome_ids}),
        "distinct_anchor_months": len({rows[item]["anchor_time"][:7] for item in outcome_ids}),
        "story_archetypes": len(archetypes),
        "top_story_archetypes_by_cluster_support": archetypes[:5],
        "full_archetype_distribution_hash": canonical_hash(archetypes),
        "representative_story_case_ids": [item["story_case_id"] for item in case_records],
        "representative_case_role_counts": dict(sorted(Counter(item["case_role"] for item in case_records).items())),
        "counterexample_records": len(counterexamples),
        "counterexample_type_counts": dict(sorted(type_counts.items())),
        "opposite_direction_endpoint_records": len(opposite),
        "opposite_direction_outcome_ids_hash": hash_ids(opposite),
        "primary_frontier_loss_on_close_records": len(frontier),
        "primary_frontier_loss_outcome_ids_hash": hash_ids(frontier),
        "directional_rows_without_primary_frontier": len(absent_frontier),
        "absent_primary_frontier_outcome_ids_hash": hash_ids(absent_frontier),
    }
    return pack, case_records


def build_archetype_registry(
    admitted_outcomes: set[str],
    *,
    rows: dict[str, dict[str, object]],
    story_by_outcome: dict[str, dict[str, object]],
    lineage_by_outcome: dict[str, dict[str, object]],
    cluster_by_outcome: dict[str, str],
) -> list[dict[str, object]]:
    grouped = defaultdict(list)
    for outcome_id in admitted_outcomes:
        grouped[story_by_outcome[outcome_id]["story_archetype_id"]].append(outcome_id)
    records = []
    for archetype_id, outcome_ids in sorted(grouped.items()):
        example = story_by_outcome[outcome_ids[0]]
        distinct_clusters = len({cluster_by_outcome[item] for item in outcome_ids})
        semantic_counts = Counter(
            lineage_by_outcome[item]["exact_semantic_signature_hash"] for item in outcome_ids
        )
        endpoint_counts = Counter(
            lineage_by_outcome[item]["endpoint_b_state_pattern_hash"] for item in outcome_ids
        )
        transition_counts = Counter(
            lineage_by_outcome[item]["transition_axes_pattern_hash"] for item in outcome_ids
        )
        core = {
            **example,
            "unique_outcome_records": len(outcome_ids),
            "distinct_overlap_clusters": distinct_clusters,
            "distinct_anchor_months": len({rows[item]["anchor_time"][:7] for item in outcome_ids}),
            "event_timeframe_counts": dict(sorted(Counter(rows[item]["event_timeframe"] for item in outcome_ids).items())),
            "horizon_counts": dict(sorted(Counter(str(rows[item]["horizon_hours"]) for item in outcome_ids).items())),
            "outcome_record_ids_hash": hash_ids(outcome_ids),
            "repetition_status": repetition_status(distinct_clusters),
            "lineage_annotations": {
                "exact_semantic_signature_variants": len(semantic_counts),
                "exact_semantic_signature_counts_hash": canonical_hash(dict(sorted(semantic_counts.items()))),
                "endpoint_b_state_pattern_variants": len(endpoint_counts),
                "endpoint_b_state_pattern_counts_hash": canonical_hash(dict(sorted(endpoint_counts.items()))),
                "transition_axes_pattern_variants": len(transition_counts),
                "transition_axes_pattern_counts_hash": canonical_hash(dict(sorted(transition_counts.items()))),
            },
            "authority": "QUALITATIVE_DESCRIPTIVE_ARCHETYPE_ONLY",
        }
        records.append(core)
    return records


def write_report(output: Path, summary: dict[str, object]) -> Path:
    lines = [
        "# OVC OPT-D Repeated-Story Evidence Report v0.1",
        "",
        "**Status:** `STORY EVIDENCE PACKS COMPLETE — DESCRIPTIVE ONLY`  ",
        f"**Contract:** `{CONTRACT_VERSION}`  ",
        "**Probability / edge / execution authority:** `NONE`",
        "",
        "## Admission",
        "",
        f"- Admitted descriptive-ready contrasts: **{summary['admitted_contrasts']:,}**",
        f"- Explicitly excluded non-ready contrasts: **{summary['excluded_contrasts']:,}**",
        f"- Unique admitted outcomes: **{summary['unique_admitted_outcomes']:,}**",
        "",
        "Temporal delta sign was not an admission rule. Both mixed and sign-consistent parent contrasts are present.",
        "",
        "## Story evidence",
        "",
        "| Artifact | Records |",
        "|---|---:|",
        f"| Qualitative story archetypes | {summary['story_archetypes']:,} |",
        f"| Contrast-arm story memberships | {summary['story_memberships']:,} |",
        f"| Evidence packs | {summary['story_evidence_packs']:,} |",
        f"| Representative cases | {summary['story_cases']:,} |",
        "",
        "## Repetition classification",
        "",
        "| Classification | Archetypes |",
        "|---|---:|",
    ]
    for status, count in summary["repetition_status_counts"].items():
        lines.append(f"| `{status}` | {count:,} |")
    lines.extend([
        "",
        "Exact semantic signatures, endpoint B-state patterns and transition-axis patterns are retained as lineage annotations; they do not fragment the qualitative archetype.",
        "",
        "## Highest cluster-coverage archetypes",
        "",
        "| Family | Clock | Horizon | Direction | Endpoint | Frontier | Clusters | Outcomes | Months |",
        "|---|---|---:|---|---|---|---:|---:|---:|",
    ])
    for item in summary["top_story_archetypes_by_cluster_support"]:
        lines.append(
            "| {families} | {clock} | {horizon}h | {direction} | {alignment} | {frontier} | {clusters:,} | {outcomes:,} | {months:,} |".format(
                families=" + ".join(item["event_family_set"]),
                clock=item["event_timeframe"],
                horizon=item["horizon_hours"],
                direction=item["event_direction"],
                alignment=item["endpoint_alignment"],
                frontier=item["frontier_outcome"],
                clusters=item["distinct_overlap_clusters"],
                outcomes=item["unique_outcome_records"],
                months=item["distinct_anchor_months"],
            )
        )
    lines.extend([
        "",
        "This table is ordered only by overlap-cluster coverage. It includes aligned and contrary paths and is not a favourable-outcome ranking.",
        "",
        "## Parent temporal states retained",
        "",
        "| State | Packs |",
        "|---|---:|",
    ])
    for status, count in summary["temporal_status_counts"].items():
        lines.append(f"| `{status}` | {count:,} |")
    lines.extend([
        "",
        f"Parent counterexample memberships linked into admitted packs: **{summary['linked_parent_counterexamples']:,}**. Representative case roles are fixed central, lower-tail, upper-tail, central opposite-direction counterexample and central frontier-loss case when available.",
        "",
        "## Gate decision",
        "",
        "Repeated-story evidence packs are complete. They may proceed to an operator-facing evidence review only as descriptive cases with full counterexamples and monthly variation. Archetype frequency, case selection and monthly sign consistency cannot be converted into conditional probability, edge, recommendation or execution authority.",
    ])
    path = output / "OVC_OPT_D_REPEATED_STORY_EVIDENCE_REPORT_v0_1.md"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contrast-root", type=Path, required=True)
    parser.add_argument("--cohort-root", type=Path, required=True)
    parser.add_argument("--measurement-root", type=Path, required=True)
    parser.add_argument("--ledger-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    contrast_root = args.contrast_root.resolve()
    cohort_root = args.cohort_root.resolve()
    measurement_root = args.measurement_root.resolve()
    ledger_root = args.ledger_root.resolve()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    manifest_path = output / "OPT_D_REPEATED_STORY_EVIDENCE_MANIFEST.json"
    if manifest_path.exists():
        raise FileExistsError("OPT-D story release already finalized")

    contrast_manifest = verify_manifest(
        contrast_root, "OPT_D_CLUSTER_BALANCED_CONTRAST_MANIFEST.json"
    )
    cohort_manifest = verify_manifest(cohort_root, "OPT_D_CLUSTER_AWARE_COHORT_MANIFEST.json")
    measurement_manifest = verify_manifest(
        measurement_root, "OPT_C_NEUTRAL_OUTCOME_MEASUREMENT_MANIFEST.json"
    )
    ledger_manifest = verify_manifest(ledger_root, "OPT_C_EVENT_ANCHOR_LEDGER_MANIFEST.json")
    if contrast_manifest["parent_cohort_manifest_hash"] != cohort_manifest["manifest_hash"]:
        raise ValueError("contrast/cohort lineage mismatch")
    if contrast_manifest["parent_measurement_manifest_hash"] != measurement_manifest["manifest_hash"]:
        raise ValueError("contrast/measurement lineage mismatch")
    if contrast_manifest["event_ledger_manifest_hash"] != ledger_manifest["manifest_hash"]:
        raise ValueError("contrast/event-ledger lineage mismatch")

    rows = {
        row["neutral_outcome_record_id"]: row
        for clock in CLOCKS
        for row in load_gzip(measurement_root / f"opt_c_neutral_outcomes_{clock.lower()}.jsonl.gz")
    }
    anchors = {
        row["event_anchor_id"]: row
        for clock in CLOCKS
        for row in load_gzip(ledger_root / f"opt_c_event_anchor_ledger_{clock.lower()}.jsonl.gz")
    }
    cluster_by_outcome = {
        row["neutral_outcome_record_id"]: row["overlap_cluster_id"]
        for row in load_gzip(cohort_root / "opt_d_outcome_cluster_assignments.jsonl.gz")
    }
    contrasts = load_gzip(contrast_root / "opt_d_contrast_registry.jsonl.gz")
    admitted = [row for row in contrasts if row["contrast_readiness"] == "DESCRIPTIVE_CONTRAST_READY"]
    excluded = [row for row in contrasts if row["contrast_readiness"] != "DESCRIPTIVE_CONTRAST_READY"]
    if len(admitted) != 37 or len(excluded) != 5:
        raise ValueError("story admission must preserve the full contrast readiness gate")
    admitted_ids = {row["contrast_id"] for row in admitted}
    memberships = [
        row for row in load_gzip(contrast_root / "opt_d_contrast_memberships.jsonl.gz")
        if row["contrast_id"] in admitted_ids
    ]
    memberships_by_contrast_stratum = defaultdict(list)
    for membership in memberships:
        memberships_by_contrast_stratum[(membership["contrast_id"], membership["contrast_stratum"])].append(
            membership["neutral_outcome_record_id"]
        )
    parent_counterexamples = [
        row for row in load_gzip(contrast_root / "opt_d_contrast_counterexamples.jsonl.gz")
        if row["contrast_id"] in admitted_ids
    ]
    counterexamples_by_contrast_arm = defaultdict(list)
    for item in parent_counterexamples:
        counterexamples_by_contrast_arm[(item["contrast_id"], item["arm"])].append(item)
    monthly_by_contrast = defaultdict(list)
    for item in load_gzip(contrast_root / "opt_d_monthly_contrast_stability.jsonl.gz"):
        if item["contrast_id"] in admitted_ids:
            monthly_by_contrast[item["contrast_id"]].append(item)

    admitted_outcomes = {
        membership["neutral_outcome_record_id"] for membership in memberships
    }
    story_by_outcome = {}
    lineage_by_outcome = {}
    for outcome_id in sorted(admitted_outcomes):
        row = rows[outcome_id]
        signature = semantic_event_signature(anchors[row["event_anchor_id"]])
        story_by_outcome[outcome_id] = qualitative_story_features(
            row, event_families=row["event_families"]
        )
        lineage_by_outcome[outcome_id] = story_lineage(row, signature)
    archetype_records = build_archetype_registry(
        admitted_outcomes,
        rows=rows,
        story_by_outcome=story_by_outcome,
        lineage_by_outcome=lineage_by_outcome,
        cluster_by_outcome=cluster_by_outcome,
    )

    story_memberships = []
    for membership in memberships:
        outcome_id = membership["neutral_outcome_record_id"]
        core = {
            "contrast_id": membership["contrast_id"],
            "contrast_stratum": membership["contrast_stratum"],
            "neutral_outcome_record_id": outcome_id,
            "event_anchor_id": rows[outcome_id]["event_anchor_id"],
            "overlap_cluster_id": membership["overlap_cluster_id"],
            "story_archetype_id": story_by_outcome[outcome_id]["story_archetype_id"],
            **lineage_by_outcome[outcome_id],
            "story_contract_version": CONTRACT_VERSION,
        }
        story_memberships.append({
            **core, "story_membership_id": f"opt-d-story-membership:{canonical_hash(core)}"
        })

    evidence_packs = []
    case_records = []
    for contrast in admitted:
        contrast_id = contrast["contrast_id"]
        arm_a_ids = memberships_by_contrast_stratum[(contrast_id, "ARM_A")]
        arm_b_ids = memberships_by_contrast_stratum[(contrast_id, "ARM_B")]
        shared_ids = memberships_by_contrast_stratum[(contrast_id, "SHARED_EXCLUDED")]
        arm_a, cases_a = arm_pack(
            arm_a_ids,
            contrast_id=contrast_id,
            arm="A",
            metric_field=contrast["primary_metric_field"],
            rows=rows,
            story_by_outcome=story_by_outcome,
            cluster_by_outcome=cluster_by_outcome,
            counterexamples_by_contrast_arm=counterexamples_by_contrast_arm,
        )
        arm_b, cases_b = arm_pack(
            arm_b_ids,
            contrast_id=contrast_id,
            arm="B",
            metric_field=contrast["primary_metric_field"],
            rows=rows,
            story_by_outcome=story_by_outcome,
            cluster_by_outcome=cluster_by_outcome,
            counterexamples_by_contrast_arm=counterexamples_by_contrast_arm,
        )
        case_records.extend(cases_a)
        case_records.extend(cases_b)
        monthly = monthly_by_contrast[contrast_id]
        if len(monthly) != 6:
            raise ValueError("every story pack must retain all six parent monthly records")
        temporal_status = contrast["temporal_stability"]["temporal_delta_status"]
        if temporal_status == "DELTA_SIGN_CONSISTENT_80PCT":
            evidence_state = "TEMPORAL_DELTA_SIGN_CONSISTENT_DESCRIPTIVE_ONLY"
        elif temporal_status == "DELTA_SIGN_MIXED":
            evidence_state = "TEMPORAL_DELTA_SIGN_MIXED"
        else:
            evidence_state = "TEMPORAL_SUPPORT_INSUFFICIENT"
        pack_core = {
            "contrast_id": contrast_id,
            "contrast_template": contrast["contrast_template"],
            "event_timeframe": contrast["event_timeframe"],
            "horizon_hours": contrast["horizon_hours"],
            "primary_metric_field": contrast["primary_metric_field"],
            "arm_a": arm_a,
            "arm_b": arm_b,
            "shared_excluded_outcome_records": len(shared_ids),
            "shared_excluded_distinct_clusters": len({cluster_by_outcome[item] for item in shared_ids}),
            "shared_excluded_outcome_ids_hash": hash_ids(shared_ids),
            "parent_cluster_balanced_delta_pips": contrast[
                "arm_a_minus_arm_b_cluster_balanced_median_pips"
            ],
            "parent_temporal_stability": contrast["temporal_stability"],
            "parent_monthly_record_ids_hash": hash_ids(
                [item["monthly_contrast_record_id"] for item in monthly]
            ),
            "monthly_variation": monthly,
            "evidence_state": evidence_state,
            "failure_conditions": {
                "opposite_direction_endpoints_present": (
                    arm_a["opposite_direction_endpoint_records"]
                    + arm_b["opposite_direction_endpoint_records"] > 0
                ),
                "primary_frontier_losses_present": (
                    arm_a["primary_frontier_loss_on_close_records"]
                    + arm_b["primary_frontier_loss_on_close_records"] > 0
                ),
                "directional_rows_without_primary_frontier_present": (
                    arm_a["directional_rows_without_primary_frontier"]
                    + arm_b["directional_rows_without_primary_frontier"] > 0
                ),
                "monthly_delta_sign_mixed": temporal_status == "DELTA_SIGN_MIXED",
                "monthly_support_insufficient": temporal_status == "INSUFFICIENT_MONTHLY_SUPPORT",
                "shared_overlap_clusters_between_arms": contrast[
                    "shared_overlap_clusters_between_exclusive_arms"
                ],
            },
            "story_contract_version": CONTRACT_VERSION,
            "authority": "DESCRIPTIVE_STORY_EVIDENCE_ONLY",
        }
        evidence_packs.append({
            **pack_core, "story_evidence_pack_id": f"opt-d-story-pack:{canonical_hash(pack_core)}"
        })

    exclusion_records = []
    for contrast in excluded:
        core = {
            "contrast_id": contrast["contrast_id"],
            "contrast_template": contrast["contrast_template"],
            "event_timeframe": contrast["event_timeframe"],
            "horizon_hours": contrast["horizon_hours"],
            "exclusion_reason": contrast["contrast_readiness"],
            "temporal_delta_status": contrast["temporal_stability"]["temporal_delta_status"],
            "story_contract_version": CONTRACT_VERSION,
            "reentry_rule": "REQUIRES_NEW_PARENT_CONTRAST_RELEASE_WITH_DESCRIPTIVE_CONTRAST_READY_STATUS",
        }
        exclusion_records.append({
            **core, "story_exclusion_id": f"opt-d-story-exclusion:{canonical_hash(core)}"
        })

    writers = {
        "archetype": DeterministicJsonlGzipWriter(output / "opt_d_story_archetype_registry.jsonl.gz"),
        "membership": DeterministicJsonlGzipWriter(output / "opt_d_story_memberships.jsonl.gz"),
        "pack": DeterministicJsonlGzipWriter(output / "opt_d_story_evidence_packs.jsonl.gz"),
        "case": DeterministicJsonlGzipWriter(output / "opt_d_story_case_index.jsonl.gz"),
        "exclusion": DeterministicJsonlGzipWriter(output / "opt_d_story_exclusions.jsonl.gz"),
    }
    for record in archetype_records:
        writers["archetype"].write(record)
    for record in sorted(story_memberships, key=lambda row: row["story_membership_id"]):
        writers["membership"].write(record)
    for record in evidence_packs:
        writers["pack"].write(record)
    for record in sorted(case_records, key=lambda row: row["story_case_id"]):
        writers["case"].write(record)
    for record in exclusion_records:
        writers["exclusion"].write(record)
    artifacts = []
    stream_metadata = {}
    for name, writer in writers.items():
        writer.close()
        artifacts.append({"path": writer.path.name, "sha256": sha256(writer.path), "size_bytes": writer.path.stat().st_size})
        stream_metadata[f"{name}_records"] = writer.count
        stream_metadata[f"{name}_stream_canonical_jsonl_hash"] = writer.canonical_jsonl_hash

    summary = {
        "admitted_contrasts": len(admitted),
        "excluded_contrasts": len(excluded),
        "unique_admitted_outcomes": len(admitted_outcomes),
        "story_archetypes": len(archetype_records),
        "repetition_status_counts": dict(sorted(Counter(
            item["repetition_status"] for item in archetype_records
        ).items())),
        "top_story_archetypes_by_cluster_support": [
            {
                key: item[key]
                for key in (
                    "story_archetype_id",
                    "event_family_set",
                    "event_timeframe",
                    "horizon_hours",
                    "event_direction",
                    "endpoint_alignment",
                    "excursion_dominance",
                    "first_extreme",
                    "continuation_state",
                    "frontier_outcome",
                    "endpoint_range_location",
                    "distinct_overlap_clusters",
                    "unique_outcome_records",
                    "distinct_anchor_months",
                    "repetition_status",
                )
            }
            for item in sorted(
                archetype_records,
                key=lambda item: (
                    -item["distinct_overlap_clusters"],
                    -item["unique_outcome_records"],
                    item["story_archetype_id"],
                ),
            )[:10]
        ],
        "story_memberships": len(story_memberships),
        "story_evidence_packs": len(evidence_packs),
        "story_cases": len(case_records),
        "case_role_counts": dict(sorted(Counter(item["case_role"] for item in case_records).items())),
        "temporal_status_counts": dict(sorted(Counter(
            item["parent_temporal_stability"]["temporal_delta_status"] for item in evidence_packs
        ).items())),
        "linked_parent_counterexamples": len(parent_counterexamples),
        "linked_parent_counterexample_type_counts": dict(sorted(Counter(
            item["counterexample_type"] for item in parent_counterexamples
        ).items())),
        "failure_condition_pack_counts": {
            key: sum(bool(pack["failure_conditions"][key]) for pack in evidence_packs)
            for key in (
                "opposite_direction_endpoints_present",
                "primary_frontier_losses_present",
                "directional_rows_without_primary_frontier_present",
                "monthly_delta_sign_mixed",
                "monthly_support_insufficient",
            )
        },
        "stream_metadata": stream_metadata,
    }
    summary_path = output / "opt_d_repeated_story_evidence_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    artifacts.append({"path": summary_path.name, "sha256": sha256(summary_path), "size_bytes": summary_path.stat().st_size})
    report = write_report(output, summary)
    artifacts.append({"path": report.name, "sha256": sha256(report), "size_bytes": report.stat().st_size})
    for source in (
        ROOT / "contracts/OVC_OPT_D_REPEATED_STORY_EVIDENCE_CONTRACT_v0_1.md",
        ROOT / "contracts/OVC_OPT_D_CLUSTER_BALANCED_CONTRAST_CONTRACT_v0_1.md",
    ):
        destination = output / source.name
        shutil.copy2(source, destination)
        artifacts.append({"path": destination.name, "sha256": sha256(destination), "size_bytes": destination.stat().st_size})

    manifest_core = {
        "release_id": "OPT-D-REPEATED-STORIES-GBPUSD-2026H1-v0.1",
        "status": "STORY_EVIDENCE_PACKS_COMPLETE_DESCRIPTIVE_ONLY",
        "generated_date": "2026-07-19",
        "story_contract_version": CONTRACT_VERSION,
        "parent_contrast_manifest_hash": contrast_manifest["manifest_hash"],
        "parent_cohort_manifest_hash": cohort_manifest["manifest_hash"],
        "parent_measurement_manifest_hash": measurement_manifest["manifest_hash"],
        "event_ledger_manifest_hash": ledger_manifest["manifest_hash"],
        "coverage_only_horizons_hours": [24],
        "blocked_horizons_hours": [48],
        "results": summary,
        "artifacts": artifacts,
        "implementation_hashes": {
            "stories.py": sha256(ROOT / "src/ovc_opt_b/stories.py"),
            "build_opt_d_story_evidence.py": sha256(Path(__file__).resolve()),
            "test_opt_d_stories.py": sha256(ROOT / "tests/test_opt_d_stories.py"),
        },
        "authority_boundary": "Descriptive repeated-story evidence only. No independence, probability, edge, recommendation, risk, trade or execution authority.",
    }
    manifest = {**manifest_core, "manifest_hash": canonical_hash(manifest_core)}
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": manifest["status"],
        "manifest_hash": manifest["manifest_hash"],
        "packs": len(evidence_packs),
        "archetypes": len(archetype_records),
    }, sort_keys=True))


if __name__ == "__main__":
    main()
