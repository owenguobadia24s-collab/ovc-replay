from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import gzip
import json
from pathlib import Path
import shutil
import statistics
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from build_reference_level_registry import sha256  # noqa: E402
from ovc_opt_b import (  # noqa: E402
    ROBUSTNESS_VERSION,
    antecedent_key,
    concentration_summary,
    directional_pair_context,
    evaluate_hypothesis,
    expected_response_vector,
    ratio,
    response_vector,
    robustness_disposition,
    summarize_leave_one_month_out,
)
from run_complete_opt_b_replay import (  # noqa: E402
    DeterministicJsonlGzipWriter,
    canonical_hash,
)
from run_opt_d_holdout_validation import (  # noqa: E402
    load_gzip,
    supplied_months,
    verify_manifest,
)


MANIFEST_NAME = "OPT_D_ROBUSTNESS_REVIEW_MANIFEST.json"


def month_of(row: dict[str, object]) -> str:
    return str(row["anchor_time"])[:7]


def relevant_key(row: dict[str, object]) -> tuple[int, tuple[str, tuple[str, ...], str]]:
    return int(row["horizon_hours"]), antecedent_key(row)


def coverage_robustness(
    rows: list[dict[str, object]], *, months: tuple[str, ...]
) -> dict[str, object]:
    monthly = {}
    rates = []
    for month in months:
        selected = [row for row in rows if month_of(row) == month]
        statuses = Counter(str(row["coverage_status"]) for row in selected)
        if set(statuses).difference({"COMPLETE", "CENSORED"}):
            raise ValueError("unexpected coverage status in robustness review")
        total = len(selected)
        complete = statuses["COMPLETE"]
        rate = round(complete * 100 / total, 4) if total else None
        if rate is not None:
            rates.append(rate)
        monthly[month] = {
            "coverage_records": total,
            "complete_records": complete,
            "censored_records": statuses["CENSORED"],
            "complete_rate_pct": rate,
        }
    total = len(rows)
    complete = sum(str(row["coverage_status"]) == "COMPLETE" for row in rows)
    minimum = min(rates) if rates else None
    maximum = max(rates) if rates else None
    return {
        "strict_path_rule": "COMPLETE_ONLY_NO_REPAIR",
        "coverage_records": total,
        "complete_records": complete,
        "censored_records": total - complete,
        "overall_complete_rate_pct": round(complete * 100 / total, 4) if total else None,
        "monthly": monthly,
        "minimum_monthly_complete_rate_pct": minimum,
        "maximum_monthly_complete_rate_pct": maximum,
        "monthly_complete_rate_range_pct_points": (
            round(maximum - minimum, 4) if minimum is not None and maximum is not None else None
        ),
    }


def build_base_record(
    hypothesis: dict[str, object],
    validation: dict[str, object],
    *,
    outcome_rows: list[dict[str, object]],
    coverage_rows: list[dict[str, object]],
    cluster_by_outcome: dict[str, str],
    months: tuple[str, ...],
) -> dict[str, object]:
    baseline = evaluate_hypothesis(
        hypothesis,
        outcome_rows=outcome_rows,
        cluster_by_outcome=cluster_by_outcome,
        supplied_months=months,
    )
    for key, value in baseline.items():
        if validation.get(key) != value:
            raise ValueError(f"sealed validation mismatch during robustness review: {key}")

    lomo_rows = []
    for omitted in months:
        remaining = [row for row in outcome_rows if month_of(row) != omitted]
        result = evaluate_hypothesis(
            hypothesis,
            outcome_rows=remaining,
            cluster_by_outcome=cluster_by_outcome,
            supplied_months=tuple(month for month in months if month != omitted),
        )
        lomo_rows.append({
            "omitted_month": omitted,
            "evaluable": result["evaluable"],
            "structural_story_reappeared": result["structural_story_reappeared"],
            "counter_story_alert": result["counter_story_alert"],
            "distinct_antecedent_overlap_clusters": result["counts"][
                "distinct_antecedent_overlap_clusters"
            ],
            "distinct_matching_overlap_clusters": result["counts"][
                "distinct_matching_overlap_clusters"
            ],
            "distinct_contradictory_overlap_clusters": result["counts"][
                "distinct_contradictory_overlap_clusters"
            ],
            "distinct_antecedent_months": result["counts"]["distinct_antecedent_months"],
            "distinct_matching_months": result["counts"]["distinct_matching_months"],
            "contradictory_to_matching_cluster_ratio": ratio(
                int(result["counts"]["distinct_contradictory_overlap_clusters"]),
                int(result["counts"]["distinct_matching_overlap_clusters"]),
            ),
        })
    lomo_summary = summarize_leave_one_month_out(lomo_rows, expected_months=len(months))

    target_response = expected_response_vector(hypothesis)
    matching_cluster_ids = [
        cluster_by_outcome[str(row["neutral_outcome_record_id"])]
        for row in outcome_rows
        if response_vector(row) == target_response
    ]
    concentration = concentration_summary(matching_cluster_ids=matching_cluster_ids)
    coverage = coverage_robustness(coverage_rows, months=months)
    if coverage["complete_records"] != validation["counts"]["antecedent_outcome_records"]:
        raise ValueError("coverage/outcome mismatch entered robustness review")

    rules = hypothesis["untouched_validation_rules"]
    counts = validation["counts"]
    discovery = hypothesis["discovery_evidence"]
    disposition = robustness_disposition(
        evaluable=bool(validation["evaluable"]),
        reappeared=bool(validation["structural_story_reappeared"]),
        counter_story_alert=bool(validation["counter_story_alert"]),
        lomo_reappearance_stable=bool(
            lomo_summary["reappearance_stable_across_all_deletions"]
        ),
    )
    return {
        "hypothesis_id": hypothesis["hypothesis_id"],
        "source_story_archetype_id": hypothesis["source_story_archetype_id"],
        "antecedent": hypothesis["antecedent"],
        "expected_forward_response": hypothesis["expected_forward_response"],
        "baseline_validation": {
            "validation_record_id": validation["validation_record_id"],
            "validation_disposition": validation["validation_disposition"],
            "evaluable": validation["evaluable"],
            "structural_story_reappeared": validation["structural_story_reappeared"],
            "counter_story_alert": validation["counter_story_alert"],
            "distinct_antecedent_overlap_clusters": counts[
                "distinct_antecedent_overlap_clusters"
            ],
            "distinct_matching_overlap_clusters": counts[
                "distinct_matching_overlap_clusters"
            ],
            "distinct_contradictory_overlap_clusters": counts[
                "distinct_contradictory_overlap_clusters"
            ],
            "distinct_matching_months": counts["distinct_matching_months"],
            "contradictory_to_matching_cluster_ratio": ratio(
                int(counts["distinct_contradictory_overlap_clusters"]),
                int(counts["distinct_matching_overlap_clusters"]),
            ),
        },
        "frozen_threshold_margins": {
            "evaluable_antecedent_cluster_margin": int(
                counts["distinct_antecedent_overlap_clusters"]
            )
            - int(rules["minimum_evaluable_antecedent_clusters"]),
            "evaluable_antecedent_month_margin": int(counts["distinct_antecedent_months"])
            - int(rules["minimum_evaluable_antecedent_months"]),
            "reappearance_matching_cluster_margin": int(
                counts["distinct_matching_overlap_clusters"]
            )
            - int(rules["minimum_reappearance_matching_clusters"]),
            "reappearance_matching_month_margin": int(counts["distinct_matching_months"])
            - int(rules["minimum_reappearance_matching_months"]),
        },
        "discovery_to_holdout_support": {
            "discovery_distinct_overlap_clusters": discovery["distinct_overlap_clusters"],
            "discovery_distinct_anchor_months": discovery["distinct_anchor_months"],
            "holdout_distinct_matching_overlap_clusters": counts[
                "distinct_matching_overlap_clusters"
            ],
            "holdout_distinct_matching_months": counts["distinct_matching_months"],
            "holdout_to_discovery_matching_cluster_ratio": ratio(
                int(counts["distinct_matching_overlap_clusters"]),
                int(discovery["distinct_overlap_clusters"]),
            ),
        },
        "matching_cluster_concentration": concentration,
        "coverage_robustness": coverage,
        "leave_one_month_out": lomo_rows,
        "leave_one_month_out_summary": lomo_summary,
        "robustness_disposition": disposition,
        "review_contract_version": ROBUSTNESS_VERSION,
        "threshold_optimization": "PROHIBITED",
        "probability_authority": "NONE",
        "edge_authority": "NONE",
        "paper_playbook_authority": "NONE",
        "execution_authority": "NONE",
    }


def build_records(
    *,
    hypotheses: list[dict[str, object]],
    validation_rows: list[dict[str, object]],
    directional_rows: list[dict[str, object]],
    outcomes: list[dict[str, object]],
    coverage_rows: list[dict[str, object]],
    assignments: list[dict[str, object]],
    months: tuple[str, ...],
) -> list[dict[str, object]]:
    validation_by_id = {row["hypothesis_id"]: row for row in validation_rows}
    if len(validation_by_id) != len(hypotheses):
        raise ValueError("robustness hypothesis/validation cardinality mismatch")
    cluster_by_outcome = {
        str(row["neutral_outcome_record_id"]): str(row["overlap_cluster_id"])
        for row in assignments
    }
    outcome_index: dict[
        tuple[int, tuple[str, tuple[str, ...], str]], list[dict[str, object]]
    ] = defaultdict(list)
    for row in outcomes:
        outcome_index[relevant_key(row)].append(row)
    coverage_index: dict[
        tuple[int, tuple[str, tuple[str, ...], str]], list[dict[str, object]]
    ] = defaultdict(list)
    for row in coverage_rows:
        coverage_index[relevant_key(row)].append(row)

    base_records = []
    for hypothesis in hypotheses:
        key = (
            int(hypothesis["expected_forward_response"]["horizon_hours"]),
            antecedent_key(hypothesis["antecedent"]),
        )
        base_records.append(build_base_record(
            hypothesis,
            validation_by_id[hypothesis["hypothesis_id"]],
            outcome_rows=outcome_index[key],
            coverage_rows=coverage_index[key],
            cluster_by_outcome=cluster_by_outcome,
            months=months,
        ))

    base_by_story = {row["source_story_archetype_id"]: row for row in base_records}
    directional_by_story = {row["story_archetype_id"]: row for row in directional_rows}
    if set(base_by_story) != set(directional_by_story):
        raise ValueError("directional review does not cover the frozen hypothesis batch")
    records = []
    for base in base_records:
        direction = directional_by_story[base["source_story_archetype_id"]]
        mirror_story = direction["mirrored_story_archetype_id"]
        mirror = base_by_story.get(mirror_story) if mirror_story else None
        core = {
            **base,
            "directional_pair_context": directional_pair_context(
                directional_review=direction,
                current_robustness=base,
                mirror_robustness=mirror,
            ),
        }
        records.append({
            **core,
            "robustness_record_id": f"opt-d-robustness:{canonical_hash(core)}",
        })
    return records


def numeric_summary(values: list[float]) -> dict[str, float | None]:
    if not values:
        return {"minimum": None, "median": None, "maximum": None}
    return {
        "minimum": round(min(values), 4),
        "median": round(statistics.median(values), 4),
        "maximum": round(max(values), 4),
    }


def summarize(records: list[dict[str, object]], *, months: tuple[str, ...]) -> dict[str, object]:
    dispositions = Counter(str(row["robustness_disposition"]) for row in records)
    by_horizon: dict[int, list[dict[str, object]]] = defaultdict(list)
    for row in records:
        by_horizon[int(row["expected_forward_response"]["horizon_hours"])].append(row)
    pair_rows = [
        row for row in records
        if row["directional_pair_context"]["directional_pair_status"]
        == "MIRRORED_CANDIDATE_PRESENT"
    ]
    pair_ids = {row["directional_pair_context"]["directional_pair_id"] for row in pair_rows}
    ratios = [
        float(row["baseline_validation"]["contradictory_to_matching_cluster_ratio"])
        for row in records
        if row["baseline_validation"]["contradictory_to_matching_cluster_ratio"] is not None
    ]
    coverage_rates = [
        float(row["coverage_robustness"]["overall_complete_rate_pct"])
        for row in records
        if row["coverage_robustness"]["overall_complete_rate_pct"] is not None
    ]
    return {
        "release_status": "ROBUSTNESS_REVIEW_COMPLETE_NO_PROMOTION_AUTHORITY",
        "hypotheses_reviewed": len(records),
        "supplied_months": list(months),
        "leave_one_month_out_deletions_per_hypothesis": len(months),
        "baseline_structural_reappearances": sum(
            bool(row["baseline_validation"]["structural_story_reappeared"])
            for row in records
        ),
        "lomo_stable_structural_reappearances": sum(
            bool(row["leave_one_month_out_summary"][
                "reappearance_stable_across_all_deletions"
            ])
            for row in records
        ),
        "baseline_counter_story_alerts": sum(
            bool(row["baseline_validation"]["counter_story_alert"]) for row in records
        ),
        "lomo_persistent_counter_story_alerts": sum(
            bool(row["leave_one_month_out_summary"][
                "counter_alert_persistent_across_all_deletions"
            ])
            for row in records
        ),
        "robustness_disposition_counts": dict(sorted(dispositions.items())),
        "contradictory_to_matching_cluster_ratio": numeric_summary(ratios),
        "strict_path_complete_rate_pct": numeric_summary(coverage_rates),
        "directional_context": {
            "complete_directional_pairs": len(pair_ids),
            "hypotheses_with_mirror": len(pair_rows),
            "hypotheses_without_mirror": len(records) - len(pair_rows),
            "paired_rows_reappearance_concordant": sum(
                bool(row["directional_pair_context"]["baseline_reappearance_concordant"])
                for row in pair_rows
            ),
            "paired_rows_counter_alert_concordant": sum(
                bool(row["directional_pair_context"]["baseline_counter_alert_concordant"])
                for row in pair_rows
            ),
            "paired_rows_lomo_stability_concordant": sum(
                bool(row["directional_pair_context"][
                    "lomo_reappearance_stability_concordant"
                ])
                for row in pair_rows
            ),
        },
        "horizon_results": {
            str(horizon): {
                "total": len(rows),
                "baseline_reappeared": sum(
                    bool(row["baseline_validation"]["structural_story_reappeared"])
                    for row in rows
                ),
                "lomo_stable_reappeared": sum(
                    bool(row["leave_one_month_out_summary"][
                        "reappearance_stable_across_all_deletions"
                    ])
                    for row in rows
                ),
                "baseline_counter_alerts": sum(
                    bool(row["baseline_validation"]["counter_story_alert"])
                    for row in rows
                ),
                "lomo_persistent_counter_alerts": sum(
                    bool(row["leave_one_month_out_summary"][
                        "counter_alert_persistent_across_all_deletions"
                    ])
                    for row in rows
                ),
            }
            for horizon, rows in sorted(by_horizon.items())
        },
        "interpretation": "Robustness diagnostics are one-way conservative and do not create probability, edge, playbook, trade or execution authority.",
    }


def write_report(output: Path, summary: dict[str, object]) -> Path:
    lines = [
        "# OVC OPT-D Robustness Review v0.1",
        "",
        f"**Status:** `{summary['release_status']}`  ",
        f"**Contract:** `{ROBUSTNESS_VERSION}`  ",
        "**Probability / edge / paper-playbook / execution authority:** `NONE`",
        "",
        "## Result",
        "",
        f"All **{summary['hypotheses_reviewed']:,}** frozen hypotheses were recomputed under twelve exact leave-one-month-out deletions. "
        f"Baseline recurrence survived every month deletion for **{summary['lomo_stable_structural_reappearances']:,}** hypotheses. "
        f"The preregistered counter-story alert survived every month deletion for **{summary['lomo_persistent_counter_story_alerts']:,}** hypotheses.",
        "",
        "| Horizon | Total | Baseline reappeared | LOMO-stable | Counter alert | Counter alert LOMO-persistent |",
        "|---:|---:|---:|---:|---:|---:|",
    ]
    for horizon, row in summary["horizon_results"].items():
        lines.append(
            f"| {horizon}h | {row['total']:,} | {row['baseline_reappeared']:,} | "
            f"{row['lomo_stable_reappeared']:,} | {row['baseline_counter_alerts']:,} | "
            f"{row['lomo_persistent_counter_alerts']:,} |"
        )
    lines.extend([
        "",
        "## Directional context",
        "",
        f"The frozen batch contains **{summary['directional_context']['complete_directional_pairs']:,}** complete UP/DOWN mirror pairs and **{summary['directional_context']['hypotheses_without_mirror']:,}** unpaired hypotheses. Directional agreement is reported only as context; mirror absence is not used to invent or discard a hypothesis.",
        "",
        "## Interpretation boundary",
        "",
        "The review confirms whether the structural result depends on any single holdout month. It does not estimate probability or edge. Counter-story persistence means distinct overlap clusters repeatedly express a response that satisfies the preregistered contradiction rule for the same antecedent and horizon. A robustness diagnostic can add a blocker or deferral but cannot rescue a frozen validation failure.",
    ])
    path = output / "OVC_OPT_D_ROBUSTNESS_REVIEW_REPORT_v0_1.md"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--validation-root", type=Path, required=True)
    parser.add_argument("--review-root", type=Path, required=True)
    parser.add_argument("--ratification-root", type=Path, required=True)
    parser.add_argument("--coverage-root", type=Path, required=True)
    parser.add_argument("--measurement-root", type=Path, required=True)
    parser.add_argument("--cohort-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    if output.exists():
        raise FileExistsError("OPT-D robustness target exists")
    output.mkdir(parents=True)

    validation_manifest = verify_manifest(
        args.validation_root.resolve(), "OPT_D_UNTOUCHED_VALIDATION_MANIFEST.json"
    )
    review_manifest = verify_manifest(
        args.review_root.resolve(), "OPT_D_EVIDENCE_REVIEW_MANIFEST.json"
    )
    ratification_manifest = verify_manifest(
        args.ratification_root.resolve(), "OPT_D_REVIEW_RATIFICATION_MANIFEST.json"
    )
    coverage_manifest = verify_manifest(
        args.coverage_root.resolve(), "OPT_C_FORWARD_PATH_COVERAGE_MANIFEST.json"
    )
    measurement_manifest = verify_manifest(
        args.measurement_root.resolve(), "OPT_C_NEUTRAL_OUTCOME_MEASUREMENT_MANIFEST.json"
    )
    cohort_manifest = verify_manifest(
        args.cohort_root.resolve(), "OPT_D_CLUSTER_AWARE_COHORT_MANIFEST.json"
    )
    if validation_manifest["parent_review_manifest_hash"] != review_manifest["manifest_hash"]:
        raise ValueError("robustness review/validation lineage mismatch")
    if validation_manifest["ratification_manifest_hash"] != ratification_manifest["manifest_hash"]:
        raise ValueError("robustness ratification/validation lineage mismatch")
    if validation_manifest["coverage_manifest_hash"] != coverage_manifest["manifest_hash"]:
        raise ValueError("robustness coverage/validation lineage mismatch")
    if validation_manifest["measurement_manifest_hash"] != measurement_manifest["manifest_hash"]:
        raise ValueError("robustness measurement/validation lineage mismatch")
    if validation_manifest["cohort_manifest_hash"] != cohort_manifest["manifest_hash"]:
        raise ValueError("robustness cohort/validation lineage mismatch")

    hypotheses = load_gzip(
        args.review_root.resolve() / "opt_d_pending_hypothesis_register.jsonl.gz"
    )
    validation_rows = load_gzip(
        args.validation_root.resolve() / "opt_d_holdout_validation_ledger.jsonl.gz"
    )
    directional_rows = load_gzip(
        args.review_root.resolve() / "opt_d_directional_symmetry_review.jsonl.gz"
    )
    outcomes = load_gzip(
        args.measurement_root.resolve() / "opt_c_neutral_outcomes_15m.jsonl.gz"
    )
    coverage_rows = load_gzip(
        args.coverage_root.resolve() / "opt_c_forward_path_coverage_15m.jsonl.gz"
    )
    assignments = load_gzip(
        args.cohort_root.resolve() / "opt_d_outcome_cluster_assignments.jsonl.gz"
    )
    months = tuple(validation_manifest["results"]["supplied_months"])
    records = build_records(
        hypotheses=hypotheses,
        validation_rows=validation_rows,
        directional_rows=directional_rows,
        outcomes=outcomes,
        coverage_rows=coverage_rows,
        assignments=assignments,
        months=months,
    )
    writer = DeterministicJsonlGzipWriter(output / "opt_d_robustness_review_ledger.jsonl.gz")
    for row in records:
        writer.write(row)
    writer.close()
    summary = summarize(records, months=months)
    summary["stream_metadata"] = {
        "records": writer.count,
        "canonical_jsonl_hash": writer.canonical_jsonl_hash,
    }
    summary_path = output / "opt_d_robustness_review_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report_path = write_report(output, summary)
    contract_source = ROOT / "contracts/OVC_OPT_D_ROBUSTNESS_REVIEW_CONTRACT_v0_1.md"
    contract_path = output / contract_source.name
    shutil.copy2(contract_source, contract_path)

    artifacts = []
    for path, role in (
        (writer.path, "HYPOTHESIS_ROBUSTNESS_LEDGER"),
        (summary_path, "ROBUSTNESS_SUMMARY"),
        (report_path, "HUMAN_READABLE_REPORT"),
        (contract_path, "FROZEN_ROBUSTNESS_CONTRACT"),
    ):
        artifacts.append({
            "path": path.name,
            "role": role,
            "sha256": sha256(path),
            "size_bytes": path.stat().st_size,
        })
    core = {
        "release_id": "OPT-D-ROBUSTNESS-GBPUSD-2025-v0.1",
        "status": summary["release_status"],
        "generated_date": "2026-07-19",
        "robustness_contract_version": ROBUSTNESS_VERSION,
        "validation_manifest_hash": validation_manifest["manifest_hash"],
        "parent_review_manifest_hash": review_manifest["manifest_hash"],
        "ratification_manifest_hash": ratification_manifest["manifest_hash"],
        "coverage_manifest_hash": coverage_manifest["manifest_hash"],
        "measurement_manifest_hash": measurement_manifest["manifest_hash"],
        "cohort_manifest_hash": cohort_manifest["manifest_hash"],
        "results": summary,
        "artifacts": artifacts,
        "implementation_hashes": {
            "robustness.py": sha256(ROOT / "src/ovc_opt_b/robustness.py"),
            "run_opt_d_robustness_review.py": sha256(Path(__file__).resolve()),
            "validate_opt_d_robustness_review.py": sha256(
                ROOT / "scripts/validate_opt_d_robustness_review.py"
            ),
            "test_opt_d_robustness.py": sha256(ROOT / "tests/test_opt_d_robustness.py"),
        },
        "authority_boundary": "Descriptive one-way robustness review only; no probability, edge, playbook, trade or execution authority.",
    }
    manifest = {**core, "manifest_hash": canonical_hash(core)}
    (output / MANIFEST_NAME).write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps({
        "status": manifest["status"],
        "manifest_hash": manifest["manifest_hash"],
        "records": len(records),
        "lomo_stable_reappearances": summary["lomo_stable_structural_reappearances"],
        "persistent_counter_alerts": summary["lomo_persistent_counter_story_alerts"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
