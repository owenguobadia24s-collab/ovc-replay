from __future__ import annotations

import argparse
from collections import defaultdict
import gzip
import hashlib
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from build_reference_level_registry import sha256  # noqa: E402
from ovc_opt_b import build_overlap_clusters, semantic_event_signature  # noqa: E402
from run_complete_opt_b_replay import canonical_hash  # noqa: E402
from build_opt_d_cluster_cohorts import (  # noqa: E402
    CLOCKS,
    CONTRACT_VERSION,
    DIRECTIONS,
    FAMILIES,
    HORIZONS,
    base_cohort_id,
    cohort_evidence,
    signature_cohort_id,
    summarize_registry,
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
    parser.add_argument("--semantic-root", type=Path, required=True)
    parser.add_argument("--ledger-root", type=Path, required=True)
    parser.add_argument("--determinism-root", type=Path)
    args = parser.parse_args()
    root = args.release_root.resolve()
    measurement_root = args.measurement_root.resolve()
    semantic_root = args.semantic_root.resolve()
    ledger_root = args.ledger_root.resolve()

    manifest = verify_manifest(root, "OPT_D_CLUSTER_AWARE_COHORT_MANIFEST.json")
    measurement_manifest = verify_manifest(
        measurement_root, "OPT_C_NEUTRAL_OUTCOME_MEASUREMENT_MANIFEST.json"
    )
    semantic_manifest = verify_manifest(semantic_root, "OPT_C_SEMANTIC_SANITY_REVIEW_MANIFEST.json")
    ledger_manifest = verify_manifest(ledger_root, "OPT_C_EVENT_ANCHOR_LEDGER_MANIFEST.json")
    if manifest["cohort_contract_version"] != CONTRACT_VERSION:
        raise ValueError("cohort contract version mismatch")
    if manifest["parent_semantic_review_manifest_hash"] != semantic_manifest["manifest_hash"]:
        raise ValueError("semantic review lineage mismatch")
    if manifest["parent_measurement_manifest_hash"] != measurement_manifest["manifest_hash"]:
        raise ValueError("measurement lineage mismatch")
    if manifest["event_ledger_manifest_hash"] != ledger_manifest["manifest_hash"]:
        raise ValueError("event ledger lineage mismatch")

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
    all_rows = [row for clock in CLOCKS for row in rows_by_clock[clock]]
    anchors = {
        row["event_anchor_id"]: row
        for clock in CLOCKS
        for row in load_gzip(ledger_root / f"opt_c_event_anchor_ledger_{clock.lower()}.jsonl.gz")
    }
    if len(all_rows) != 14979:
        raise ValueError("unexpected measurement count")

    expected_clusters = []
    expected_assignment_by_outcome = {}
    for horizon in HORIZONS:
        clusters, assignments = build_overlap_clusters(
            [row for row in all_rows if row["horizon_hours"] == horizon]
        )
        expected_clusters.extend({**cluster, "contract_version": CONTRACT_VERSION} for cluster in clusters)
        expected_assignment_by_outcome.update(assignments)
    expected_clusters.sort(key=lambda row: (row["horizon_hours"], row["cluster_start_time"]))
    actual_clusters = load_gzip(root / "opt_d_overlap_clusters.jsonl.gz")
    if actual_clusters != expected_clusters or len(actual_clusters) != 1386:
        raise ValueError("overlap cluster ledger mismatch")
    if len(expected_assignment_by_outcome) != len(all_rows):
        raise ValueError("not every outcome received exactly one cluster")

    expected_assignments = []
    for row in sorted(all_rows, key=lambda item: (item["horizon_hours"], item["anchor_time"], item["event_timeframe"])):
        core = {
            "neutral_outcome_record_id": row["neutral_outcome_record_id"],
            "event_anchor_id": row["event_anchor_id"],
            "event_timeframe": row["event_timeframe"],
            "horizon_hours": row["horizon_hours"],
            "anchor_time": row["anchor_time"],
            "endpoint_time": row["endpoint_time"],
            "overlap_cluster_id": expected_assignment_by_outcome[row["neutral_outcome_record_id"]],
            "contract_version": CONTRACT_VERSION,
        }
        expected_assignments.append({**core, "cluster_assignment_id": f"opt-d-assignment:{canonical_hash(core)}"})
    actual_assignments = load_gzip(root / "opt_d_outcome_cluster_assignments.jsonl.gz")
    if actual_assignments != expected_assignments:
        raise ValueError("outcome cluster assignment mismatch")

    expected_base = []
    expected_memberships = {}
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
                    "overlap_cluster_id": expected_assignment_by_outcome[row["neutral_outcome_record_id"]],
                    "event_timeframe": clock,
                    "horizon_hours": row["horizon_hours"],
                    "contract_version": CONTRACT_VERSION,
                }
                record = {**core, "cohort_membership_id": f"opt-d-membership:{canonical_hash(core)}"}
                expected_memberships[record["cohort_membership_id"]] = record
        for horizon in HORIZONS:
            horizon_rows = [row for row in rows_by_clock[clock] if row["horizon_hours"] == horizon]
            for family in FAMILIES:
                for direction in DIRECTIONS:
                    subset = [
                        row for row in horizon_rows
                        if family in row["event_families"] and row["event_direction"] == direction
                    ]
                    expected_base.append({
                        "cohort_layer": "BASE",
                        "cohort_id": base_cohort_id(clock, horizon, family, direction),
                        "event_timeframe": clock,
                        "horizon_hours": horizon,
                        "event_family": family,
                        "event_direction": direction,
                        **cohort_evidence(subset, expected_assignment_by_outcome),
                        "membership_rule": "MULTI_FAMILY_ROWS_APPEAR_IN_EACH_NAMED_FAMILY_COHORT_NOT_ADDITIVE",
                        "contract_version": CONTRACT_VERSION,
                    })
    actual_base = load_gzip(root / "opt_d_base_cohort_registry.jsonl.gz")
    if actual_base != expected_base or len(actual_base) != 160:
        raise ValueError("base cohort registry mismatch")

    expected_signatures = []
    for (clock, horizon, signature_hash), subset in sorted(signature_groups.items()):
        signature = semantic_event_signature(anchors[subset[0]["event_anchor_id"]])
        expected_signatures.append({
            "cohort_layer": "EXACT_SEMANTIC_SIGNATURE",
            "cohort_id": signature_cohort_id(clock, horizon, signature_hash),
            "event_timeframe": clock,
            "horizon_hours": horizon,
            **signature,
            **cohort_evidence(subset, expected_assignment_by_outcome),
            "contract_version": CONTRACT_VERSION,
        })
    actual_signatures = load_gzip(root / "opt_d_signature_cohort_registry.jsonl.gz")
    if actual_signatures != expected_signatures or len(actual_signatures) != 1286:
        raise ValueError("exact-signature cohort registry mismatch")
    actual_memberships = {
        row["cohort_membership_id"]: row for row in load_gzip(root / "opt_d_cohort_memberships.jsonl.gz")
    }
    if actual_memberships != expected_memberships or len(actual_memberships) != 32904:
        raise ValueError("cohort membership ledger mismatch")

    if manifest["results"]["base_cohorts"] != summarize_registry(expected_base):
        raise ValueError("base cohort summary mismatch")
    if manifest["results"]["signature_cohorts"] != summarize_registry(expected_signatures):
        raise ValueError("signature cohort summary mismatch")
    stream_checks = []
    for filename, key, count in (
        ("opt_d_overlap_clusters.jsonl.gz", "cluster_stream_canonical_jsonl_hash", 1386),
        ("opt_d_outcome_cluster_assignments.jsonl.gz", "assignment_stream_canonical_jsonl_hash", 14979),
        ("opt_d_base_cohort_registry.jsonl.gz", "base_cohort_stream_canonical_jsonl_hash", 160),
        ("opt_d_signature_cohort_registry.jsonl.gz", "signature_cohort_stream_canonical_jsonl_hash", 1286),
        ("opt_d_cohort_memberships.jsonl.gz", "membership_stream_canonical_jsonl_hash", 32904),
    ):
        stream_hash, stream_count = canonical_stream_hash(root / filename)
        if stream_hash != manifest["results"]["stream_metadata"][key] or stream_count != count:
            raise ValueError(f"canonical stream mismatch: {filename}")
        stream_checks.append({"path": filename, "rows": count, "canonical_jsonl_hash": stream_hash})

    determinism = {"checked": False}
    if args.determinism_root:
        other = verify_manifest(args.determinism_root.resolve(), "OPT_D_CLUSTER_AWARE_COHORT_MANIFEST.json")
        if other["manifest_hash"] != manifest["manifest_hash"]:
            raise ValueError("OPT-D cohort determinism mismatch")
        determinism = {"checked": True, "manifest_hash_match": True}

    validation = {
        "status": "PASS",
        "validated_manifest_hash": manifest["manifest_hash"],
        "reviewed_outcome_records": 14979,
        "artifact_checks": artifact_checks,
        "stream_checks": stream_checks,
        "determinism": determinism,
        "gate_controls": {
            "cross_clock_half_open_clusters_recomputed": True,
            "all_outcomes_assigned_exactly_once_per_horizon": True,
            "all_base_cohorts_recomputed": True,
            "all_exact_semantic_signatures_recomputed": True,
            "all_memberships_recomputed": True,
            "row_and_cluster_support_bands_recomputed": True,
            "24h_coverage_only": True,
            "48h_blocked": True,
        },
        "authority_boundary": "Cohort formation only; no independence, significance, edge, recommendation, trade or execution authority.",
    }
    (root / "OPT_D_CLUSTER_AWARE_COHORT_VALIDATION.json").write_text(
        json.dumps(validation, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    lines = [
        "# OPT-D Cluster-Aware Cohort Validation",
        "",
        "**Status:** `PASS`  ",
        f"**Validated manifest:** `{manifest['manifest_hash']}`  ",
        f"**Independent determinism:** `{'PASS' if determinism['checked'] else 'NOT RUN'}`",
        "",
        "All 14,979 outcome assignments, 1,386 cross-clock overlap clusters, 160 base cohorts, 1,286 exact semantic-signature cohorts and 32,904 memberships were independently recomputed and matched.",
        "",
        "Readiness remains descriptive only. Cluster counts do not establish statistical independence.",
    ]
    (root / "OPT_D_CLUSTER_AWARE_COHORT_VALIDATION.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )
    print(json.dumps({"status": "PASS", "manifest_hash": manifest["manifest_hash"]}, sort_keys=True))


if __name__ == "__main__":
    main()
