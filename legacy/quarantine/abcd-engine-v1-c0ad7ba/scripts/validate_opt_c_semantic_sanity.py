from __future__ import annotations

import argparse
import gzip
import hashlib
import json
from pathlib import Path
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from build_reference_level_registry import sha256  # noqa: E402
from run_complete_opt_b_replay import canonical_hash  # noqa: E402
from review_opt_c_semantic_sanity import (  # noqa: E402
    CLOCKS,
    HORIZONS,
    REVIEW_VERSION,
    build_support_matrix,
    distribution_integrity,
    frontier_review,
    overlap_review,
)


def verify_manifest(root: Path, name: str) -> dict[str, object]:
    manifest = json.loads((root / name).read_text(encoding="utf-8"))
    core = {key: value for key, value in manifest.items() if key != "manifest_hash"}
    if canonical_hash(core) != manifest["manifest_hash"]:
        raise ValueError(f"manifest self-hash mismatch: {name}")
    return manifest


def load_gzip(path: Path) -> list[dict[str, object]]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle]


def canonical_stream_hash(path: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    count = 0
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            digest.update((json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n").encode())
            count += 1
    return digest.hexdigest(), count


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--release-root", type=Path, required=True)
    parser.add_argument("--measurement-root", type=Path, required=True)
    parser.add_argument("--determinism-root", type=Path)
    args = parser.parse_args()
    root = args.release_root.resolve()
    measurement_root = args.measurement_root.resolve()
    manifest = verify_manifest(root, "OPT_C_SEMANTIC_SANITY_REVIEW_MANIFEST.json")
    parent = verify_manifest(measurement_root, "OPT_C_NEUTRAL_OUTCOME_MEASUREMENT_MANIFEST.json")
    if manifest["review_contract_version"] != REVIEW_VERSION:
        raise ValueError("review contract version mismatch")
    if manifest["parent_measurement_manifest_hash"] != parent["manifest_hash"]:
        raise ValueError("measurement lineage mismatch")
    if manifest["status"] != "PASS_WITH_OVERLAP_AND_SPARSE_COHORT_CONTROLS":
        raise ValueError("semantic review did not reach the controlled pass state")

    artifact_checks = []
    for artifact in manifest["artifacts"]:
        path = root / artifact["path"]
        actual = sha256(path)
        if actual != artifact["sha256"]:
            raise ValueError(f"artifact hash mismatch: {path.name}")
        artifact_checks.append({"path": path.name, "sha256": actual, "status": "PASS"})

    rows_by_clock = {
        clock: load_gzip(measurement_root / f"opt_c_neutral_outcomes_{clock.lower()}.jsonl.gz")
        for clock in CLOCKS
    }
    if sum(len(rows) for rows in rows_by_clock.values()) != 14979:
        raise ValueError("review parent row count mismatch")
    expected_integrity = distribution_integrity(rows_by_clock)
    expected_overlap = overlap_review(rows_by_clock)
    expected_frontier = frontier_review(rows_by_clock)
    for clock in CLOCKS:
        if expected_integrity[clock]["measurement_semantic_violation_counts"]:
            raise ValueError(f"measurement semantic violation in {clock}")
        if expected_integrity[clock]["nested_horizon_violation_counts"]:
            raise ValueError(f"nested horizon violation in {clock}")
    if manifest["results"]["distribution_integrity"] != expected_integrity:
        raise ValueError("distribution-integrity review mismatch")
    if manifest["results"]["overlap_review"] != expected_overlap:
        raise ValueError("overlap review mismatch")
    if manifest["results"]["frontier_review"] != expected_frontier:
        raise ValueError("frontier review mismatch")

    matrix_path = root / "opt_c_semantic_cohort_support_matrix.jsonl.gz"
    actual_matrix = load_gzip(matrix_path)
    actual_hash, actual_count = canonical_stream_hash(matrix_path)
    with tempfile.TemporaryDirectory(prefix="opt-c-semantic-validate-") as temporary:
        expected_support, _, expected_matrix = build_support_matrix(rows_by_clock, Path(temporary))
    if actual_matrix != expected_matrix or actual_count != 160:
        raise ValueError("cohort support matrix mismatch")
    if actual_hash != expected_support["canonical_jsonl_hash"]:
        raise ValueError("cohort support canonical hash mismatch")
    if manifest["results"]["cohort_support"] != expected_support:
        raise ValueError("cohort support summary mismatch")
    if sum(expected_support["support_band_counts"].values()) != 160:
        raise ValueError("support bands do not cover all cohort cells")

    determinism = {"checked": False}
    if args.determinism_root:
        other = verify_manifest(
            args.determinism_root.resolve(), "OPT_C_SEMANTIC_SANITY_REVIEW_MANIFEST.json"
        )
        if other["manifest_hash"] != manifest["manifest_hash"]:
            raise ValueError("semantic review determinism mismatch")
        determinism = {"checked": True, "manifest_hash_match": True}

    validation = {
        "status": "PASS",
        "validated_manifest_hash": manifest["manifest_hash"],
        "reviewed_outcome_records": 14979,
        "artifact_checks": artifact_checks,
        "determinism": determinism,
        "gate_controls": {
            "all_measurement_identities_recomputed": True,
            "all_nested_horizon_invariants_recomputed": True,
            "all_overlap_strata_recomputed": True,
            "all_frontier_applicability_fields_recomputed": True,
            "all_160_support_cells_recomputed": True,
            "sparse_cells_labelled_no_comparison": True,
            "24h_coverage_only": True,
            "48h_blocked": True,
        },
        "authority_boundary": "Semantic coherence and descriptive support only; no edge, recommendation, risk, trade or execution authority.",
    }
    (root / "OPT_C_SEMANTIC_SANITY_REVIEW_VALIDATION.json").write_text(
        json.dumps(validation, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    lines = [
        "# OPT-C Semantic Sanity Review Validation",
        "",
        "**Status:** `PASS`  ",
        f"**Validated manifest:** `{manifest['manifest_hash']}`  ",
        f"**Independent determinism:** `{'PASS' if determinism['checked'] else 'NOT RUN'}`",
        "",
        "All 14,979 measurement rows, nested-horizon invariants, overlap strata, frontier-applicability summaries and 160 cohort-support cells were independently recomputed and matched the release.",
        "",
        "The controlled pass authorizes only an OPT-D cohort-contract draft. It does not establish independence, significance, edge or execution authority.",
    ]
    (root / "OPT_C_SEMANTIC_SANITY_REVIEW_VALIDATION.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )
    print(json.dumps({"status": "PASS", "manifest_hash": manifest["manifest_hash"]}, sort_keys=True))


if __name__ == "__main__":
    main()
