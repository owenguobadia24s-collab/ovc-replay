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
    VALIDATION_VERSION,
    antecedent_key,
    evaluate_hypothesis,
    frozen_holdout_rules,
)
from run_complete_opt_b_replay import (  # noqa: E402
    DeterministicJsonlGzipWriter,
    canonical_hash,
)


CLOCKS = ("15M", "2H")
HYPOTHESIS_CLOCK = "15M"
MANIFEST_NAME = "OPT_D_UNTOUCHED_VALIDATION_MANIFEST.json"


def verify_manifest(root: Path, name: str) -> dict[str, object]:
    manifest = json.loads((root / name).read_text(encoding="utf-8"))
    core = {key: value for key, value in manifest.items() if key != "manifest_hash"}
    if canonical_hash(core) != manifest["manifest_hash"]:
        raise ValueError(f"manifest self-hash mismatch: {name}")
    for artifact in manifest.get("artifacts", []):
        path = root / artifact["path"]
        if sha256(path) != artifact["sha256"]:
            raise ValueError(f"artifact hash mismatch: {path}")
    return manifest


def verify_seal(root: Path) -> dict[str, object]:
    manifest = json.loads((root / "OPT_A_SEAL_MANIFEST.json").read_text(encoding="utf-8"))
    core = {key: value for key, value in manifest.items() if key != "seal_hash"}
    if canonical_hash(core) != manifest["seal_hash"]:
        raise ValueError("OPT-A seal self-hash mismatch")
    for artifact in manifest["artifacts"]:
        path = root / artifact["path"]
        if sha256(path) != artifact["sha256"]:
            raise ValueError(f"OPT-A seal artifact mismatch: {path}")
    return manifest


def load_gzip(path: Path) -> list[dict[str, object]]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle]


def parse_interval(text: str) -> tuple[datetime, datetime]:
    if not (text.startswith("[") and text.endswith(")") and "," in text):
        raise ValueError(f"invalid half-open interval: {text}")
    start_text, end_text = text[1:-1].split(",", 1)
    return (
        datetime.fromisoformat(start_text.strip().replace("Z", "+00:00")),
        datetime.fromisoformat(end_text.strip().replace("Z", "+00:00")),
    )


def supplied_months(interval: str) -> tuple[str, ...]:
    start, end = parse_interval(interval)
    cursor = start.replace(day=1)
    result = []
    while cursor < end:
        result.append(cursor.strftime("%Y-%m"))
        if cursor.month == 12:
            cursor = cursor.replace(year=cursor.year + 1, month=1)
        else:
            cursor = cursor.replace(month=cursor.month + 1)
    return tuple(result)


def coverage_summary(
    hypothesis: dict[str, object],
    *,
    rows: list[dict[str, object]],
    months: tuple[str, ...],
) -> dict[str, object]:
    target = antecedent_key(hypothesis["antecedent"])
    horizon = int(hypothesis["expected_forward_response"]["horizon_hours"])
    matched = [
        row for row in rows
        if int(row["horizon_hours"]) == horizon and antecedent_key(row) == target
    ]
    statuses = Counter(str(row["coverage_status"]) for row in matched)
    if set(statuses).difference({"COMPLETE", "CENSORED"}):
        raise ValueError("unexpected OPT-C coverage status")
    reasons = Counter(
        str(reason)
        for row in matched
        for reason in row["censor_reasons"]
    )
    month_counts = Counter(str(row["anchor_time"])[:7] for row in matched)
    complete = statuses["COMPLETE"]
    total = len(matched)
    return {
        "coverage_records": total,
        "complete_records": complete,
        "censored_records": statuses["CENSORED"],
        "complete_rate_pct": round(complete * 100 / total, 4) if total else None,
        "censor_reason_counts": dict(sorted(reasons.items())),
        "coverage_records_by_month": {
            month: month_counts.get(month, 0) for month in months
        },
        "strict_path_rule": "COMPLETE_ONLY_NO_REPAIR",
    }


def disposition(row: dict[str, object]) -> str:
    if not row["evaluable"]:
        return "NOT_EVALUABLE"
    if row["structural_story_reappeared"]:
        return (
            "REAPPEARED_WITH_COUNTER_STORY_ALERT"
            if row["counter_story_alert"]
            else "REAPPEARED_WITHOUT_COUNTER_STORY_ALERT"
        )
    return (
        "NOT_REAPPEARED_WITH_COUNTER_STORY_ALERT"
        if row["counter_story_alert"]
        else "NOT_REAPPEARED_WITHOUT_COUNTER_STORY_ALERT"
    )


def write_report(output: Path, summary: dict[str, object]) -> Path:
    lines = [
        "# OVC OPT-D Untouched Structural Validation Report v0.1",
        "",
        f"**Status:** `{summary['release_status']}`  ",
        f"**Contract:** `{VALIDATION_VERSION}`  ",
        "**Probability / edge / trade / execution authority:** `NONE`",
        "",
        "## Holdout boundary",
        "",
        f"- Holdout OPT-A seal: `{summary['holdout_seal_id']}`",
        f"- Holdout interval: `{summary['holdout_interval']}`",
        f"- Discovery interval: `{summary['discovery_interval']}`",
        "- Temporal overlap: **none**",
        "- Ratified hypotheses evaluated: **202**",
        "",
        "## Frozen validation results",
        "",
        "| Disposition | Hypotheses |",
        "|---|---:|",
    ]
    for status, count in summary["disposition_counts"].items():
        lines.append(f"| `{status}` | {count:,} |")
    lines.extend([
        "",
        f"Evaluable hypotheses: **{summary['evaluable_hypotheses']:,}**. "
        f"Structurally reappeared: **{summary['reappeared_hypotheses']:,}**. "
        f"Counter-story alerts: **{summary['counter_story_alerts']:,}**.",
        "",
        "## By horizon",
        "",
        "| Horizon | Total | Evaluable | Reappeared | Counter alerts |",
        "|---:|---:|---:|---:|---:|",
    ])
    for horizon, item in summary["horizon_results"].items():
        lines.append(
            f"| {horizon}h | {item['total']:,} | {item['evaluable']:,} | "
            f"{item['reappeared']:,} | {item['counter_story_alerts']:,} |"
        )
    lines.extend([
        "",
        "## Interpretation boundary",
        "",
        "A structural reappearance means only that the exact frozen qualitative story met the preregistered cluster/month threshold in the untouched year. A non-reappearance or counter-story alert is retained without threshold changes. None of these labels establishes independence, probability, predictive edge or a trading rule.",
        "",
        "All contract-compliant censored paths remain in the OPT-C coverage audit and receive no outcome row. No missing path was repaired, and all twelve holdout months—including zero-support months—are represented in every hypothesis record.",
    ])
    path = output / "OVC_OPT_D_UNTOUCHED_VALIDATION_REPORT_v0_1.md"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ratification-root", type=Path, required=True)
    parser.add_argument("--review-root", type=Path, required=True)
    parser.add_argument("--holdout-seal-root", type=Path, required=True)
    parser.add_argument("--discovery-seal-root", type=Path, required=True)
    parser.add_argument("--ledger-root", type=Path, required=True)
    parser.add_argument("--coverage-root", type=Path, required=True)
    parser.add_argument("--measurement-root", type=Path, required=True)
    parser.add_argument("--cohort-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    roots = {
        key: value.resolve()
        for key, value in vars(args).items()
        if key != "output"
    }
    output = args.output.resolve()
    if output.exists():
        raise FileExistsError("OPT-D validation target exists")
    output.mkdir(parents=True)

    ratification = verify_manifest(
        roots["ratification_root"], "OPT_D_REVIEW_RATIFICATION_MANIFEST.json"
    )
    review = verify_manifest(roots["review_root"], "OPT_D_EVIDENCE_REVIEW_MANIFEST.json")
    holdout_seal = verify_seal(roots["holdout_seal_root"])
    discovery_seal = verify_seal(roots["discovery_seal_root"])
    ledger = verify_manifest(roots["ledger_root"], "OPT_C_EVENT_ANCHOR_LEDGER_MANIFEST.json")
    coverage = verify_manifest(roots["coverage_root"], "OPT_C_FORWARD_PATH_COVERAGE_MANIFEST.json")
    measurement = verify_manifest(
        roots["measurement_root"], "OPT_C_NEUTRAL_OUTCOME_MEASUREMENT_MANIFEST.json"
    )
    cohort = verify_manifest(roots["cohort_root"], "OPT_D_CLUSTER_AWARE_COHORT_MANIFEST.json")

    if ratification["parent_review_manifest_hash"] != review["manifest_hash"]:
        raise ValueError("ratification/review lineage mismatch")
    if ratification["status"] != "RATIFIED_FOR_UNTOUCHED_STRUCTURAL_VALIDATION":
        raise ValueError("hypothesis batch is not ratified for holdout validation")
    if ledger["opt_a_seal_hash"] != holdout_seal["seal_hash"]:
        raise ValueError("event ledger does not bind the holdout seal")
    if coverage["opt_a_seal_hash"] != holdout_seal["seal_hash"]:
        raise ValueError("coverage audit does not bind the holdout seal")
    if measurement["opt_a_seal_hash"] != holdout_seal["seal_hash"]:
        raise ValueError("measurement does not bind the holdout seal")
    if coverage["event_ledger_manifest_hash"] != ledger["manifest_hash"]:
        raise ValueError("coverage/event-ledger lineage mismatch")
    if measurement["event_ledger_manifest_hash"] != ledger["manifest_hash"]:
        raise ValueError("measurement/event-ledger lineage mismatch")
    if measurement["coverage_manifest_hash"] != coverage["manifest_hash"]:
        raise ValueError("measurement/coverage lineage mismatch")
    if cohort["event_ledger_manifest_hash"] != ledger["manifest_hash"]:
        raise ValueError("cohort/event-ledger lineage mismatch")
    if cohort["parent_measurement_manifest_hash"] != measurement["manifest_hash"]:
        raise ValueError("cohort/measurement lineage mismatch")

    holdout_interval = str(holdout_seal["scope"]["interval"])
    discovery_interval = str(discovery_seal["scope"]["interval"])
    holdout_start, holdout_end = parse_interval(holdout_interval)
    discovery_start, discovery_end = parse_interval(discovery_interval)
    if not (holdout_end <= discovery_start or discovery_end <= holdout_start):
        raise ValueError("holdout and discovery OPT-A intervals overlap")
    if holdout_seal["scope"]["instrument_id"] != discovery_seal["scope"]["instrument_id"]:
        raise ValueError("holdout/discovery instrument mismatch")
    if holdout_seal["scope"]["price_side"] != discovery_seal["scope"]["price_side"]:
        raise ValueError("holdout/discovery price-side mismatch")
    if holdout_seal["scope"]["canonical_timeframes"] != [HYPOTHESIS_CLOCK]:
        raise ValueError("holdout story authority must remain 15M only")
    months = supplied_months(holdout_interval)
    if len(months) != 12:
        raise ValueError("OPT-D-VALIDATE-0.1 requires the approved full-year holdout")

    hypotheses = load_gzip(
        roots["review_root"] / "opt_d_pending_hypothesis_register.jsonl.gz"
    )
    ratified = load_gzip(
        roots["ratification_root"] / "opt_d_hypothesis_batch_ratification_ledger.jsonl.gz"
    )
    ratified_by_id = {row["hypothesis_id"]: row for row in ratified}
    ratified_ids = set(ratified_by_id)
    if len(hypotheses) != 202 or len(ratified) != 202:
        raise ValueError("validation requires the complete 202-hypothesis batch")
    if ratified_ids != {row["hypothesis_id"] for row in hypotheses}:
        raise ValueError("ratified hypothesis set differs from review hypothesis set")
    if any(
        ratified_by_id[row["hypothesis_id"]]["source_story_archetype_id"]
        != row["source_story_archetype_id"]
        or ratified_by_id[row["hypothesis_id"]]["decision"]
        != "RATIFIED_FOR_UNTOUCHED_STRUCTURAL_VALIDATION"
        for row in hypotheses
    ):
        raise ValueError("ratified hypothesis lineage or decision drift")
    if any(row["untouched_validation_rules"] != frozen_holdout_rules() for row in hypotheses):
        raise ValueError("frozen holdout-rule drift")
    if any(row["antecedent"]["event_timeframe"] != HYPOTHESIS_CLOCK for row in hypotheses):
        raise ValueError("unexpected clock gained hypothesis authority")
    if any(
        row["expected_forward_response"]["matching_rule"]
        != "ALL_QUALITATIVE_RESPONSE_FIELDS_EXACT"
        for row in hypotheses
    ):
        raise ValueError("qualitative response matching rule drift")

    outcomes_by_clock = {
        clock: load_gzip(
            roots["measurement_root"]
            / f"opt_c_neutral_outcomes_{clock.lower()}.jsonl.gz"
        )
        for clock in CLOCKS
    }
    if any(
        row["outcome_status"] != "MEASURED_COMPLETE_PATH"
        for rows in outcomes_by_clock.values()
        for row in rows
    ):
        raise ValueError("non-complete path entered neutral measurement")
    measured_horizons = {int(value) for value in measurement["measured_horizons_hours"]}
    if any(
        int(row["expected_forward_response"]["horizon_hours"]) not in measured_horizons
        for row in hypotheses
    ):
        raise ValueError("ratified hypothesis horizon lacks measurement authority")
    if measurement["coverage_only_horizons_hours"] != [24] or measurement["blocked_horizons_hours"] != [48]:
        raise ValueError("OPT-C horizon authority drift")

    assignments = load_gzip(
        roots["cohort_root"] / "opt_d_outcome_cluster_assignments.jsonl.gz"
    )
    cluster_by_outcome = {
        row["neutral_outcome_record_id"]: row["overlap_cluster_id"]
        for row in assignments
    }
    outcome_ids = {
        row["neutral_outcome_record_id"]
        for rows in outcomes_by_clock.values()
        for row in rows
    }
    if set(cluster_by_outcome) != outcome_ids:
        raise ValueError("overlap-cluster assignments do not cover the measured outcome surface")

    coverage_rows = load_gzip(
        roots["coverage_root"] / "opt_c_forward_path_coverage_15m.jsonl.gz"
    )
    evaluated = []
    for hypothesis in hypotheses:
        result = evaluate_hypothesis(
            hypothesis,
            outcome_rows=outcomes_by_clock[HYPOTHESIS_CLOCK],
            cluster_by_outcome=cluster_by_outcome,
            supplied_months=months,
        )
        audit = coverage_summary(hypothesis, rows=coverage_rows, months=months)
        if audit["complete_records"] != result["counts"]["antecedent_outcome_records"]:
            raise ValueError("complete coverage/outcome count mismatch for frozen antecedent")
        failure_conditions = []
        if result["evaluable"] and not result["structural_story_reappeared"]:
            failure_conditions.append("STRUCTURAL_STORY_NOT_REAPPEARED_WHEN_EVALUABLE")
        if result["counter_story_alert"]:
            failure_conditions.append("COUNTER_STORY_ALERT")
        core = {
            **result,
            "validation_disposition": disposition(result),
            "coverage_audit": audit,
            "failure_conditions_observed": failure_conditions,
            "definition_drift_status": "NO_DRIFT_DETECTED",
            "ratification_manifest_hash": ratification["manifest_hash"],
            "holdout_opt_a_seal_hash": holdout_seal["seal_hash"],
            "opt_c_measurement_manifest_hash": measurement["manifest_hash"],
            "opt_d_cohort_manifest_hash": cohort["manifest_hash"],
        }
        evaluated.append({
            **core,
            "validation_record_id": f"opt-d-validation:{canonical_hash(core)}",
        })

    writer = DeterministicJsonlGzipWriter(output / "opt_d_holdout_validation_ledger.jsonl.gz")
    for row in evaluated:
        writer.write(row)
    writer.close()

    by_horizon: dict[int, list[dict[str, object]]] = defaultdict(list)
    for row in evaluated:
        by_horizon[int(row["expected_forward_response"]["horizon_hours"])].append(row)
    status_counts = Counter(row["validation_disposition"] for row in evaluated)
    summary = {
        "release_status": "UNTOUCHED_STRUCTURAL_VALIDATION_COMPLETE",
        "hypotheses_evaluated": len(evaluated),
        "evaluable_hypotheses": sum(row["evaluable"] for row in evaluated),
        "not_evaluable_hypotheses": sum(not row["evaluable"] for row in evaluated),
        "reappeared_hypotheses": sum(row["structural_story_reappeared"] for row in evaluated),
        "not_reappeared_evaluable_hypotheses": sum(
            row["evaluable"] and not row["structural_story_reappeared"] for row in evaluated
        ),
        "counter_story_alerts": sum(row["counter_story_alert"] for row in evaluated),
        "disposition_counts": dict(sorted(status_counts.items())),
        "expected_alignment_results": {
            alignment: {
                "total": len(rows),
                "evaluable": sum(row["evaluable"] for row in rows),
                "reappeared": sum(row["structural_story_reappeared"] for row in rows),
                "counter_story_alerts": sum(row["counter_story_alert"] for row in rows),
            }
            for alignment, rows in sorted(defaultdict(list, {
                value: [
                    row for row in evaluated
                    if row["expected_forward_response"]["endpoint_alignment"] == value
                ]
                for value in ("ALIGNED", "OPPOSITE")
            }).items())
        },
        "horizon_results": {
            str(horizon): {
                "total": len(rows),
                "evaluable": sum(row["evaluable"] for row in rows),
                "reappeared": sum(row["structural_story_reappeared"] for row in rows),
                "counter_story_alerts": sum(row["counter_story_alert"] for row in rows),
            }
            for horizon, rows in sorted(by_horizon.items())
        },
        "supplied_months": list(months),
        "holdout_seal_id": holdout_seal["seal_id"],
        "holdout_interval": holdout_interval,
        "discovery_seal_id": discovery_seal["seal_id"],
        "discovery_interval": discovery_interval,
        "temporal_overlap": False,
        "hypothesis_clock_authority": [HYPOTHESIS_CLOCK],
        "context_only_clocks": ["2H"],
        "coverage_only_horizons_hours": [24],
        "blocked_horizons_hours": [48],
        "stream_metadata": {
            "validation_records": writer.count,
            "validation_stream_canonical_jsonl_hash": writer.canonical_jsonl_hash,
        },
    }
    summary_path = output / "opt_d_holdout_validation_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report_path = write_report(output, summary)
    contract_source = ROOT / "contracts/OVC_OPT_D_UNTOUCHED_VALIDATION_CONTRACT_v0_1.md"
    contract_path = output / contract_source.name
    shutil.copy2(contract_source, contract_path)

    artifacts = []
    for path, role in (
        (writer.path, "HYPOTHESIS_VALIDATION_LEDGER"),
        (summary_path, "VALIDATION_SUMMARY"),
        (report_path, "HUMAN_READABLE_REPORT"),
        (contract_path, "FROZEN_VALIDATION_CONTRACT"),
    ):
        artifacts.append({
            "path": path.name,
            "role": role,
            "sha256": sha256(path),
            "size_bytes": path.stat().st_size,
        })
    manifest_core = {
        "release_id": "OPT-D-VALIDATE-GBPUSD-2025-v0.1",
        "status": summary["release_status"],
        "generated_date": "2026-07-19",
        "validation_contract_version": VALIDATION_VERSION,
        "ratification_manifest_hash": ratification["manifest_hash"],
        "parent_review_manifest_hash": review["manifest_hash"],
        "holdout_opt_a_seal_hash": holdout_seal["seal_hash"],
        "discovery_opt_a_seal_hash": discovery_seal["seal_hash"],
        "event_ledger_manifest_hash": ledger["manifest_hash"],
        "coverage_manifest_hash": coverage["manifest_hash"],
        "measurement_manifest_hash": measurement["manifest_hash"],
        "cohort_manifest_hash": cohort["manifest_hash"],
        "results": summary,
        "artifacts": artifacts,
        "implementation_hashes": {
            "holdout_validation.py": sha256(ROOT / "src/ovc_opt_b/holdout_validation.py"),
            "run_opt_d_holdout_validation.py": sha256(Path(__file__).resolve()),
            "validate_opt_d_holdout_validation.py": sha256(
                ROOT / "scripts/validate_opt_d_holdout_validation.py"
            ),
            "test_opt_d_holdout_validation.py": sha256(
                ROOT / "tests/test_opt_d_holdout_validation.py"
            ),
        },
        "definition_drift_status": "NO_DRIFT_DETECTED",
        "authority_boundary": "Structural untouched-validation recurrence evidence only. No probability, independence, predictive edge, recommendation, risk, trade or execution authority.",
    }
    manifest = {**manifest_core, "manifest_hash": canonical_hash(manifest_core)}
    (output / MANIFEST_NAME).write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps({
        "status": manifest["status"],
        "manifest_hash": manifest["manifest_hash"],
        "hypotheses": len(evaluated),
        "evaluable": summary["evaluable_hypotheses"],
        "reappeared": summary["reappeared_hypotheses"],
        "counter_story_alerts": summary["counter_story_alerts"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
