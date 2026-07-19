from __future__ import annotations

import argparse
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from build_reference_level_registry import sha256  # noqa: E402
from ovc_opt_b import evaluate_hypothesis, frozen_holdout_rules  # noqa: E402
from run_complete_opt_b_replay import canonical_hash  # noqa: E402
from run_opt_d_holdout_validation import (  # noqa: E402
    MANIFEST_NAME,
    coverage_summary,
    disposition,
    load_gzip,
    supplied_months,
    verify_manifest,
    verify_seal,
)


def canonical_stream_hash(path: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    count = 0
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            digest.update(
                (json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n").encode()
            )
            count += 1
    return digest.hexdigest(), count


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--release-root", type=Path, required=True)
    parser.add_argument("--determinism-root", type=Path)
    parser.add_argument("--ratification-root", type=Path, required=True)
    parser.add_argument("--review-root", type=Path, required=True)
    parser.add_argument("--holdout-seal-root", type=Path, required=True)
    parser.add_argument("--coverage-root", type=Path, required=True)
    parser.add_argument("--measurement-root", type=Path, required=True)
    parser.add_argument("--cohort-root", type=Path, required=True)
    args = parser.parse_args()
    root = args.release_root.resolve()
    manifest = verify_manifest(root, MANIFEST_NAME)
    ratification = verify_manifest(
        args.ratification_root.resolve(), "OPT_D_REVIEW_RATIFICATION_MANIFEST.json"
    )
    review = verify_manifest(
        args.review_root.resolve(), "OPT_D_EVIDENCE_REVIEW_MANIFEST.json"
    )
    holdout_seal = verify_seal(args.holdout_seal_root.resolve())
    coverage = verify_manifest(
        args.coverage_root.resolve(), "OPT_C_FORWARD_PATH_COVERAGE_MANIFEST.json"
    )
    measurement = verify_manifest(
        args.measurement_root.resolve(), "OPT_C_NEUTRAL_OUTCOME_MEASUREMENT_MANIFEST.json"
    )
    cohort = verify_manifest(
        args.cohort_root.resolve(), "OPT_D_CLUSTER_AWARE_COHORT_MANIFEST.json"
    )
    expected_lineage = {
        "ratification_manifest_hash": ratification["manifest_hash"],
        "parent_review_manifest_hash": review["manifest_hash"],
        "holdout_opt_a_seal_hash": holdout_seal["seal_hash"],
        "coverage_manifest_hash": coverage["manifest_hash"],
        "measurement_manifest_hash": measurement["manifest_hash"],
        "cohort_manifest_hash": cohort["manifest_hash"],
    }
    for key, value in expected_lineage.items():
        if manifest[key] != value:
            raise ValueError(f"validation lineage mismatch: {key}")

    artifact_checks = []
    for artifact in manifest["artifacts"]:
        path = root / artifact["path"]
        actual = sha256(path)
        if actual != artifact["sha256"]:
            raise ValueError(f"validation artifact mismatch: {path.name}")
        artifact_checks.append({"path": path.name, "sha256": actual, "status": "PASS"})

    rows = load_gzip(root / "opt_d_holdout_validation_ledger.jsonl.gz")
    hypotheses = load_gzip(
        args.review_root.resolve() / "opt_d_pending_hypothesis_register.jsonl.gz"
    )
    ratified_rows = load_gzip(
        args.ratification_root.resolve()
        / "opt_d_hypothesis_batch_ratification_ledger.jsonl.gz"
    )
    outcomes = load_gzip(
        args.measurement_root.resolve() / "opt_c_neutral_outcomes_15m.jsonl.gz"
    )
    assignments = load_gzip(
        args.cohort_root.resolve() / "opt_d_outcome_cluster_assignments.jsonl.gz"
    )
    cluster_by_outcome = {
        row["neutral_outcome_record_id"]: row["overlap_cluster_id"] for row in assignments
    }
    coverage_rows = load_gzip(
        args.coverage_root.resolve() / "opt_c_forward_path_coverage_15m.jsonl.gz"
    )
    months = supplied_months(str(holdout_seal["scope"]["interval"]))
    if len(rows) != 202 or len(hypotheses) != 202 or len(ratified_rows) != 202:
        raise ValueError("validation batch cardinality mismatch")
    ratified_by_id = {row["hypothesis_id"]: row for row in ratified_rows}
    if set(ratified_by_id) != {row["hypothesis_id"] for row in hypotheses}:
        raise ValueError("independent ratification-set mismatch")

    expected_rows = []
    for hypothesis in hypotheses:
        if hypothesis["untouched_validation_rules"] != frozen_holdout_rules():
            raise ValueError("holdout-rule drift during independent recomputation")
        result = evaluate_hypothesis(
            hypothesis,
            outcome_rows=outcomes,
            cluster_by_outcome=cluster_by_outcome,
            supplied_months=months,
        )
        audit = coverage_summary(hypothesis, rows=coverage_rows, months=months)
        failures = []
        if result["evaluable"] and not result["structural_story_reappeared"]:
            failures.append("STRUCTURAL_STORY_NOT_REAPPEARED_WHEN_EVALUABLE")
        if result["counter_story_alert"]:
            failures.append("COUNTER_STORY_ALERT")
        core = {
            **result,
            "validation_disposition": disposition(result),
            "coverage_audit": audit,
            "failure_conditions_observed": failures,
            "definition_drift_status": "NO_DRIFT_DETECTED",
            "ratification_manifest_hash": ratification["manifest_hash"],
            "holdout_opt_a_seal_hash": holdout_seal["seal_hash"],
            "opt_c_measurement_manifest_hash": measurement["manifest_hash"],
            "opt_d_cohort_manifest_hash": cohort["manifest_hash"],
        }
        expected_rows.append({
            **core,
            "validation_record_id": f"opt-d-validation:{canonical_hash(core)}",
        })
    if rows != expected_rows:
        raise ValueError("independently recomputed hypothesis ledger mismatch")

    stream_hash, stream_count = canonical_stream_hash(
        root / "opt_d_holdout_validation_ledger.jsonl.gz"
    )
    metadata = manifest["results"]["stream_metadata"]
    if stream_count != metadata["validation_records"] or stream_hash != metadata[
        "validation_stream_canonical_jsonl_hash"
    ]:
        raise ValueError("validation stream metadata mismatch")
    if Counter(row["validation_disposition"] for row in rows) != Counter(
        manifest["results"]["disposition_counts"]
    ):
        raise ValueError("validation disposition summary mismatch")
    if any(
        set(row["monthly_distinct_cluster_counts"]["antecedent"]) != set(months)
        or set(row["coverage_audit"]["coverage_records_by_month"]) != set(months)
        for row in rows
    ):
        raise ValueError("zero-support month reporting is incomplete")
    if any(row["definition_drift_status"] != "NO_DRIFT_DETECTED" for row in rows):
        raise ValueError("definition drift entered validation ledger")
    if any(row["execution_authority"] != "NONE" for row in rows):
        raise ValueError("execution authority escaped structural validation")

    determinism = {"checked": False}
    if args.determinism_root:
        other = verify_manifest(args.determinism_root.resolve(), MANIFEST_NAME)
        if other["manifest_hash"] != manifest["manifest_hash"]:
            raise ValueError("OPT-D validation deterministic reproduction mismatch")
        determinism = {"checked": True, "manifest_hash_match": True}

    validation = {
        "status": "PASS",
        "validated_manifest_hash": manifest["manifest_hash"],
        "artifact_checks": artifact_checks,
        "stream_check": {
            "rows": stream_count,
            "canonical_jsonl_hash": stream_hash,
        },
        "determinism": determinism,
        "counts": manifest["results"],
        "gate_controls": {
            "complete_202_hypothesis_batch_recomputed": True,
            "ratification_and_parent_review_bound": True,
            "untouched_opt_a_seal_bound": True,
            "discovery_holdout_non_overlap_manifest_bound": True,
            "exact_antecedent_match_recomputed": True,
            "exact_seven_field_response_match_recomputed": True,
            "distinct_overlap_cluster_counts_recomputed": True,
            "ten_cluster_four_month_gates_recomputed": True,
            "counter_story_alerts_recomputed": True,
            "strict_complete_path_only_policy_verified": True,
            "all_twelve_months_explicit": True,
            "definition_drift_detected": False,
            "no_probability_edge_trade_or_execution_authority": True,
        },
        "authority_boundary": "Independent verification of structural holdout recurrence only; no probability, edge, recommendation, trade or execution authority.",
    }
    (root / "OPT_D_UNTOUCHED_VALIDATION_VERIFICATION.json").write_text(
        json.dumps(validation, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    lines = [
        "# OPT-D Untouched Structural Validation Verification",
        "",
        "**Status:** `PASS`  ",
        f"**Validated manifest:** `{manifest['manifest_hash']}`  ",
        f"**Deterministic reproduction:** `{'PASS' if determinism['checked'] else 'NOT RUN'}`",
        "",
        "All 202 hypothesis decisions were independently recomputed from the frozen review register, strict complete OPT-C outcomes and cross-clock overlap-cluster assignments. Artifact hashes, canonical stream hash, lineage, thresholds, counter-story alerts and twelve-month zero reporting match.",
        "",
        "The verification grants no probability, predictive edge, trade or execution authority.",
    ]
    (root / "OPT_D_UNTOUCHED_VALIDATION_VERIFICATION.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )
    print(json.dumps({
        "status": "PASS",
        "manifest_hash": manifest["manifest_hash"],
        "records": stream_count,
        "determinism": determinism["checked"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
