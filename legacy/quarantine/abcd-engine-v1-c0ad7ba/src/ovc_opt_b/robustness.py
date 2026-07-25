from __future__ import annotations

from collections import Counter
from typing import Iterable, Mapping


ROBUSTNESS_VERSION = "OPT-D-ROBUSTNESS-0.1"
PAPER_PLAYBOOK_GATE_VERSION = "PAPER-PLAYBOOK-GATE-0.1"


def percentage(numerator: int, denominator: int) -> float | None:
    if denominator == 0:
        return None
    return round(numerator * 100 / denominator, 4)


def ratio(numerator: int, denominator: int) -> float | None:
    if denominator == 0:
        return None
    return round(numerator / denominator, 4)


def summarize_leave_one_month_out(
    rows: Iterable[Mapping[str, object]], *, expected_months: int
) -> dict[str, object]:
    values = list(rows)
    if len(values) != expected_months:
        raise ValueError("leave-one-month-out surface is incomplete")
    omitted = [str(row["omitted_month"]) for row in values]
    if len(set(omitted)) != expected_months:
        raise ValueError("leave-one-month-out months are not unique")
    return {
        "month_deletions_tested": expected_months,
        "evaluable_after_deletion_count": sum(bool(row["evaluable"]) for row in values),
        "reappeared_after_deletion_count": sum(
            bool(row["structural_story_reappeared"]) for row in values
        ),
        "counter_alert_after_deletion_count": sum(
            bool(row["counter_story_alert"]) for row in values
        ),
        "reappearance_stable_across_all_deletions": all(
            bool(row["structural_story_reappeared"]) for row in values
        ),
        "counter_alert_persistent_across_all_deletions": all(
            bool(row["counter_story_alert"]) for row in values
        ),
        "minimum_matching_clusters_after_deletion": min(
            int(row["distinct_matching_overlap_clusters"]) for row in values
        ),
        "maximum_matching_clusters_after_deletion": max(
            int(row["distinct_matching_overlap_clusters"]) for row in values
        ),
        "minimum_contradictory_clusters_after_deletion": min(
            int(row["distinct_contradictory_overlap_clusters"]) for row in values
        ),
        "maximum_contradictory_clusters_after_deletion": max(
            int(row["distinct_contradictory_overlap_clusters"]) for row in values
        ),
    }


def robustness_disposition(
    *,
    evaluable: bool,
    reappeared: bool,
    counter_story_alert: bool,
    lomo_reappearance_stable: bool,
) -> str:
    if not evaluable:
        return "DEFERRED_INSUFFICIENT_ANTECEDENT_COVERAGE"
    if not reappeared and counter_story_alert:
        return "BLOCKED_NON_REAPPEARANCE_AND_COUNTER_STORY_DOMINANCE"
    if counter_story_alert:
        return "BLOCKED_COUNTER_STORY_DOMINANCE"
    if not reappeared:
        return "BLOCKED_STRUCTURAL_NON_REAPPEARANCE"
    if not lomo_reappearance_stable:
        return "DEFERRED_MONTH_SENSITIVE_RECURRENCE"
    return "ROBUSTNESS_REVIEW_CLEAR"


def directional_pair_context(
    *,
    directional_review: Mapping[str, object],
    current_robustness: Mapping[str, object],
    mirror_robustness: Mapping[str, object] | None,
) -> dict[str, object]:
    status = str(directional_review["directional_pair_status"])
    if status == "MIRRORED_CANDIDATE_ABSENT":
        if mirror_robustness is not None:
            raise ValueError("absent directional mirror unexpectedly resolved")
        return {
            "directional_pair_status": status,
            "directional_pair_id": None,
            "mirrored_story_archetype_id": None,
            "mirrored_hypothesis_id": None,
            "baseline_reappearance_concordant": None,
            "baseline_counter_alert_concordant": None,
            "lomo_reappearance_stability_concordant": None,
            "directional_symmetry_assessment": "NOT_ASSESSED_MIRROR_ABSENT_IN_FROZEN_BATCH",
        }
    if status != "MIRRORED_CANDIDATE_PRESENT" or mirror_robustness is None:
        raise ValueError("present directional mirror is unresolved")
    current_baseline = current_robustness["baseline_validation"]
    current_lomo = current_robustness["leave_one_month_out_summary"]
    baseline = mirror_robustness["baseline_validation"]
    lomo = mirror_robustness["leave_one_month_out_summary"]
    return {
        "directional_pair_status": status,
        "directional_pair_id": directional_review["directional_pair_id"],
        "mirrored_story_archetype_id": directional_review["mirrored_story_archetype_id"],
        "mirrored_hypothesis_id": mirror_robustness["hypothesis_id"],
        "baseline_reappearance_concordant": bool(
            baseline["structural_story_reappeared"]
        )
        == bool(current_baseline["structural_story_reappeared"]),
        "baseline_counter_alert_concordant": bool(baseline["counter_story_alert"])
        == bool(current_baseline["counter_story_alert"]),
        "lomo_reappearance_stability_concordant": bool(
            lomo["reappearance_stable_across_all_deletions"]
        )
        == bool(current_lomo["reappearance_stable_across_all_deletions"]),
        "directional_symmetry_assessment": "MIRROR_CONTEXT_REPORTED_NOT_A_PROMOTION_REQUIREMENT",
    }


def paper_playbook_gate(
    *, validation: Mapping[str, object], robustness: Mapping[str, object]
) -> dict[str, object]:
    coverage = validation["coverage_audit"]
    counts = validation["counts"]
    lineage_pass = (
        validation["definition_drift_status"] == "NO_DRIFT_DETECTED"
        and validation["edge_authority"] == "NONE"
        and validation["execution_authority"] == "NONE"
    )
    strict_censoring_pass = (
        coverage["strict_path_rule"] == "COMPLETE_ONLY_NO_REPAIR"
        and int(coverage["coverage_records"])
        == int(coverage["complete_records"]) + int(coverage["censored_records"])
        and int(coverage["complete_records"])
        == int(counts["antecedent_outcome_records"])
    )
    evaluable = bool(validation["evaluable"])
    reappeared = bool(validation["structural_story_reappeared"])
    counter_clear = not bool(validation["counter_story_alert"])
    lomo_stable = bool(
        robustness["leave_one_month_out_summary"][
            "reappearance_stable_across_all_deletions"
        ]
    )

    blockers: list[str] = []
    deferrals: list[str] = []
    if not lineage_pass:
        blockers.append("INVALID_DEFINITION_OR_LINEAGE_DRIFT")
    if not strict_censoring_pass:
        blockers.append("STRICT_FORWARD_PATH_COVERAGE_OR_CENSORING_FAILURE")
    if evaluable and not reappeared:
        blockers.append("STRUCTURAL_STORY_NOT_REAPPEARED_WHEN_EVALUABLE")
    if not counter_clear:
        blockers.append("COUNTER_STORY_ALERT")
    if not evaluable:
        deferrals.append("NOT_EVALUABLE_INSUFFICIENT_ANTECEDENT_COVERAGE")
    if evaluable and reappeared and counter_clear and not lomo_stable:
        deferrals.append("MONTH_SENSITIVE_RECURRENCE")

    if blockers:
        decision = "BLOCK"
    elif deferrals:
        decision = "DEFER"
    else:
        decision = "PASS"
    return {
        "gate_decision": decision,
        "gate_checks": {
            "definition_and_lineage_integrity": "PASS" if lineage_pass else "FAIL",
            "strict_complete_path_censoring_handling": (
                "PASS" if strict_censoring_pass else "FAIL"
            ),
            "evaluable_antecedent_coverage": "PASS" if evaluable else "DEFER",
            "frozen_structural_reappearance": "PASS" if reappeared else "FAIL",
            "counter_story_clear": "PASS" if counter_clear else "FAIL",
            "leave_one_month_out_recurrence": "PASS" if lomo_stable else "DEFER",
        },
        "blocking_reasons": blockers,
        "deferral_reasons": deferrals,
        "paper_playbook_authorized": decision == "PASS",
        "paper_execution_authority": "NONE",
        "live_execution_authority": "NONE",
    }


def concentration_summary(
    *, matching_cluster_ids: Iterable[str]
) -> dict[str, object]:
    counts = Counter(str(value) for value in matching_cluster_ids)
    total = sum(counts.values())
    largest = max(counts.values(), default=0)
    return {
        "matching_outcome_records": total,
        "distinct_matching_overlap_clusters": len(counts),
        "largest_matching_cluster_record_count": largest,
        "largest_matching_cluster_record_share_pct": percentage(largest, total),
    }
