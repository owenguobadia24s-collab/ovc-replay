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

from build_reference_level_registry import sha256  # noqa: E402
from run_opt_d_holdout_validation import load_gzip, verify_manifest  # noqa: E402
from run_opt_d_robustness_review import (  # noqa: E402
    MANIFEST_NAME,
    build_records,
    summarize,
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
    parser.add_argument("--validation-root", type=Path, required=True)
    parser.add_argument("--review-root", type=Path, required=True)
    parser.add_argument("--ratification-root", type=Path, required=True)
    parser.add_argument("--coverage-root", type=Path, required=True)
    parser.add_argument("--measurement-root", type=Path, required=True)
    parser.add_argument("--cohort-root", type=Path, required=True)
    args = parser.parse_args()
    root = args.release_root.resolve()
    manifest = verify_manifest(root, MANIFEST_NAME)
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
    expected_lineage = {
        "validation_manifest_hash": validation_manifest["manifest_hash"],
        "parent_review_manifest_hash": review_manifest["manifest_hash"],
        "ratification_manifest_hash": ratification_manifest["manifest_hash"],
        "coverage_manifest_hash": coverage_manifest["manifest_hash"],
        "measurement_manifest_hash": measurement_manifest["manifest_hash"],
        "cohort_manifest_hash": cohort_manifest["manifest_hash"],
    }
    for key, value in expected_lineage.items():
        if manifest[key] != value:
            raise ValueError(f"robustness lineage mismatch: {key}")

    artifact_checks = []
    for artifact in manifest["artifacts"]:
        path = root / artifact["path"]
        actual = sha256(path)
        if actual != artifact["sha256"]:
            raise ValueError(f"robustness artifact mismatch: {path.name}")
        artifact_checks.append({"path": path.name, "sha256": actual, "status": "PASS"})

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
    expected_records = build_records(
        hypotheses=hypotheses,
        validation_rows=validation_rows,
        directional_rows=directional_rows,
        outcomes=outcomes,
        coverage_rows=coverage_rows,
        assignments=assignments,
        months=months,
    )
    actual_records = load_gzip(root / "opt_d_robustness_review_ledger.jsonl.gz")
    if actual_records != expected_records:
        raise ValueError("independent robustness recomputation mismatch")
    if len(actual_records) != 202:
        raise ValueError("robustness batch cardinality mismatch")

    stream_hash, stream_count = canonical_stream_hash(
        root / "opt_d_robustness_review_ledger.jsonl.gz"
    )
    expected_summary = summarize(expected_records, months=months)
    expected_summary["stream_metadata"] = {
        "records": stream_count,
        "canonical_jsonl_hash": stream_hash,
    }
    if manifest["results"] != expected_summary:
        raise ValueError("robustness summary mismatch")
    if any(len(row["leave_one_month_out"]) != 12 for row in actual_records):
        raise ValueError("incomplete leave-one-month-out surface")
    if any(
        set(item["omitted_month"] for item in row["leave_one_month_out"]) != set(months)
        for row in actual_records
    ):
        raise ValueError("leave-one-month-out month coverage mismatch")
    if any(row["threshold_optimization"] != "PROHIBITED" for row in actual_records):
        raise ValueError("threshold optimization entered robustness release")
    if any(
        row["paper_playbook_authority"] != "NONE"
        or row["execution_authority"] != "NONE"
        for row in actual_records
    ):
        raise ValueError("authority escaped robustness review")

    determinism = {"checked": False}
    if args.determinism_root:
        other = verify_manifest(args.determinism_root.resolve(), MANIFEST_NAME)
        if other["manifest_hash"] != manifest["manifest_hash"]:
            raise ValueError("robustness deterministic reproduction mismatch")
        determinism = {"checked": True, "manifest_hash_match": True}

    result = {
        "status": "PASS",
        "validated_manifest_hash": manifest["manifest_hash"],
        "artifact_checks": artifact_checks,
        "stream_check": {"rows": stream_count, "canonical_jsonl_hash": stream_hash},
        "determinism": determinism,
        "controls": {
            "all_202_hypotheses_recomputed": True,
            "all_2424_month_deletions_recomputed": True,
            "month_spanning_clusters_preserved": True,
            "directional_mirror_context_recomputed": True,
            "strict_coverage_month_profiles_recomputed": True,
            "frozen_thresholds_unchanged": True,
            "counter_story_rule_unchanged": True,
            "no_probability_edge_playbook_trade_or_execution_authority": True,
        },
        "authority_boundary": "Independent verification of descriptive structural robustness only.",
    }
    (root / "OPT_D_ROBUSTNESS_REVIEW_VERIFICATION.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (root / "OPT_D_ROBUSTNESS_REVIEW_VERIFICATION.md").write_text(
        "\n".join([
            "# OPT-D Robustness Review Verification",
            "",
            "**Status:** `PASS`  ",
            f"**Validated manifest:** `{manifest['manifest_hash']}`  ",
            f"**Deterministic reproduction:** `{'PASS' if determinism['checked'] else 'NOT RUN'}`",
            "",
            "All 202 records and 2,424 exact month-deletion decisions were independently recomputed. Lineage, artifact hashes, stream hash, directional context, strict coverage profiles, frozen thresholds and authority boundaries match.",
            "",
            "No probability, edge, paper-playbook, trade or execution authority is granted.",
        ]) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "status": "PASS",
        "manifest_hash": manifest["manifest_hash"],
        "records": stream_count,
        "month_deletions": stream_count * len(months),
        "determinism": determinism["checked"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
