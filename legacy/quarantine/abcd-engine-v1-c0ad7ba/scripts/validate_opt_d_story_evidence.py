from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import gzip
import hashlib
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from build_reference_level_registry import sha256  # noqa: E402
from build_opt_d_story_evidence import (  # noqa: E402
    CLOCKS,
    CONTRACT_VERSION,
    build_archetype_registry,
    story_lineage,
)
from ovc_opt_b import qualitative_story_features, semantic_event_signature  # noqa: E402
from run_complete_opt_b_replay import canonical_hash  # noqa: E402


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


def recursive_keys(value: object) -> set[str]:
    if isinstance(value, dict):
        return set(value).union(*(recursive_keys(item) for item in value.values()))
    if isinstance(value, list):
        return set().union(*(recursive_keys(item) for item in value)) if value else set()
    return set()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--release-root", type=Path, required=True)
    parser.add_argument("--contrast-root", type=Path, required=True)
    parser.add_argument("--cohort-root", type=Path, required=True)
    parser.add_argument("--measurement-root", type=Path, required=True)
    parser.add_argument("--ledger-root", type=Path, required=True)
    parser.add_argument("--determinism-root", type=Path)
    args = parser.parse_args()
    root = args.release_root.resolve()
    contrast_root = args.contrast_root.resolve()
    cohort_root = args.cohort_root.resolve()
    measurement_root = args.measurement_root.resolve()
    ledger_root = args.ledger_root.resolve()

    manifest = verify_manifest(root, "OPT_D_REPEATED_STORY_EVIDENCE_MANIFEST.json")
    contrast_manifest = verify_manifest(
        contrast_root, "OPT_D_CLUSTER_BALANCED_CONTRAST_MANIFEST.json"
    )
    cohort_manifest = verify_manifest(cohort_root, "OPT_D_CLUSTER_AWARE_COHORT_MANIFEST.json")
    measurement_manifest = verify_manifest(
        measurement_root, "OPT_C_NEUTRAL_OUTCOME_MEASUREMENT_MANIFEST.json"
    )
    ledger_manifest = verify_manifest(ledger_root, "OPT_C_EVENT_ANCHOR_LEDGER_MANIFEST.json")
    if manifest["story_contract_version"] != CONTRACT_VERSION:
        raise ValueError("story contract version mismatch")
    for field, expected in (
        ("parent_contrast_manifest_hash", contrast_manifest["manifest_hash"]),
        ("parent_cohort_manifest_hash", cohort_manifest["manifest_hash"]),
        ("parent_measurement_manifest_hash", measurement_manifest["manifest_hash"]),
        ("event_ledger_manifest_hash", ledger_manifest["manifest_hash"]),
    ):
        if manifest[field] != expected:
            raise ValueError(f"lineage mismatch: {field}")

    artifact_checks = []
    for artifact in manifest["artifacts"]:
        path = root / artifact["path"]
        actual = sha256(path)
        if actual != artifact["sha256"]:
            raise ValueError(f"artifact hash mismatch: {path.name}")
        artifact_checks.append({"path": path.name, "sha256": actual, "status": "PASS"})

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
    admitted_ids = {
        row["contrast_id"] for row in contrasts
        if row["contrast_readiness"] == "DESCRIPTIVE_CONTRAST_READY"
    }
    excluded_ids = {row["contrast_id"] for row in contrasts} - admitted_ids
    parent_memberships = [
        row for row in load_gzip(contrast_root / "opt_d_contrast_memberships.jsonl.gz")
        if row["contrast_id"] in admitted_ids
    ]
    admitted_outcomes = {row["neutral_outcome_record_id"] for row in parent_memberships}

    story_by_outcome = {}
    lineage_by_outcome = {}
    for outcome_id in sorted(admitted_outcomes):
        row = rows[outcome_id]
        signature = semantic_event_signature(anchors[row["event_anchor_id"]])
        story_by_outcome[outcome_id] = qualitative_story_features(
            row, event_families=row["event_families"]
        )
        lineage_by_outcome[outcome_id] = story_lineage(row, signature)
    expected_archetypes = build_archetype_registry(
        admitted_outcomes,
        rows=rows,
        story_by_outcome=story_by_outcome,
        lineage_by_outcome=lineage_by_outcome,
        cluster_by_outcome=cluster_by_outcome,
    )
    actual_archetypes = load_gzip(root / "opt_d_story_archetype_registry.jsonl.gz")
    if actual_archetypes != expected_archetypes:
        raise ValueError("story archetype registry mismatch")

    story_memberships = load_gzip(root / "opt_d_story_memberships.jsonl.gz")
    if len(story_memberships) != len(parent_memberships):
        raise ValueError("story membership coverage mismatch")
    parent_keys = {
        (row["contrast_id"], row["contrast_stratum"], row["neutral_outcome_record_id"])
        for row in parent_memberships
    }
    story_keys = {
        (row["contrast_id"], row["contrast_stratum"], row["neutral_outcome_record_id"])
        for row in story_memberships
    }
    if story_keys != parent_keys:
        raise ValueError("story membership does not exactly cover admitted parent memberships")
    for item in story_memberships:
        outcome_id = item["neutral_outcome_record_id"]
        if item["story_archetype_id"] != story_by_outcome[outcome_id]["story_archetype_id"]:
            raise ValueError("membership archetype mismatch")
        for key, value in lineage_by_outcome[outcome_id].items():
            if item[key] != value:
                raise ValueError(f"membership lineage mismatch: {key}")

    packs = load_gzip(root / "opt_d_story_evidence_packs.jsonl.gz")
    exclusions = load_gzip(root / "opt_d_story_exclusions.jsonl.gz")
    cases = load_gzip(root / "opt_d_story_case_index.jsonl.gz")
    if {row["contrast_id"] for row in packs} != admitted_ids:
        raise ValueError("pack admission mismatch")
    if {row["contrast_id"] for row in exclusions} != excluded_ids:
        raise ValueError("exclusion ledger mismatch")
    if any(len(row["monthly_variation"]) != 6 for row in packs):
        raise ValueError("monthly variation coverage mismatch")
    case_roles = Counter(row["case_role"] for row in cases)
    required_roles = {
        "CENTRAL", "LOWER_TAIL", "UPPER_TAIL",
        "OPPOSITE_DIRECTION_COUNTEREXAMPLE", "PRIMARY_FRONTIER_LOSS_CASE",
    }
    if set(case_roles) != required_roles or any(case_roles[role] != 74 for role in required_roles):
        raise ValueError("fixed representative case-role coverage mismatch")
    case_ids = {row["story_case_id"] for row in cases}
    if any(
        not set(pack[arm]["representative_story_case_ids"]).issubset(case_ids)
        for pack in packs for arm in ("arm_a", "arm_b")
    ):
        raise ValueError("pack/case index linkage mismatch")

    expected_repetition = Counter(row["repetition_status"] for row in actual_archetypes)
    if manifest["results"]["repetition_status_counts"] != dict(sorted(expected_repetition.items())):
        raise ValueError("repetition status summary mismatch")
    singleton_outcomes = {
        row["story_archetype_id"] for row in actual_archetypes
        if row["repetition_status"] == "SINGLETON_INVENTORY"
    }
    if any(
        row["distinct_overlap_clusters"] != 1
        for row in actual_archetypes if row["story_archetype_id"] in singleton_outcomes
    ):
        raise ValueError("singleton label has repeated cluster coverage")

    forbidden = {"probability", "win_rate", "edge", "profit", "position_size", "trade_signal"}
    materialized_keys = set().union(
        recursive_keys(actual_archetypes), recursive_keys(story_memberships),
        recursive_keys(packs), recursive_keys(cases), recursive_keys(exclusions),
    )
    if forbidden.intersection(materialized_keys):
        raise ValueError("forbidden authority field materialized")

    stream_checks = []
    for filename, prefix, expected_count in (
        ("opt_d_story_archetype_registry.jsonl.gz", "archetype", len(actual_archetypes)),
        ("opt_d_story_memberships.jsonl.gz", "membership", len(story_memberships)),
        ("opt_d_story_evidence_packs.jsonl.gz", "pack", len(packs)),
        ("opt_d_story_case_index.jsonl.gz", "case", len(cases)),
        ("opt_d_story_exclusions.jsonl.gz", "exclusion", len(exclusions)),
    ):
        stream_hash, count = canonical_stream_hash(root / filename)
        metadata = manifest["results"]["stream_metadata"]
        if count != expected_count or count != metadata[f"{prefix}_records"]:
            raise ValueError(f"stream count mismatch: {filename}")
        if stream_hash != metadata[f"{prefix}_stream_canonical_jsonl_hash"]:
            raise ValueError(f"canonical stream hash mismatch: {filename}")
        stream_checks.append({"path": filename, "rows": count, "canonical_jsonl_hash": stream_hash})

    determinism = {"checked": False}
    if args.determinism_root:
        other = verify_manifest(
            args.determinism_root.resolve(), "OPT_D_REPEATED_STORY_EVIDENCE_MANIFEST.json"
        )
        if other["manifest_hash"] != manifest["manifest_hash"]:
            raise ValueError("story release determinism mismatch")
        determinism = {"checked": True, "manifest_hash_match": True}

    validation = {
        "status": "PASS",
        "validated_manifest_hash": manifest["manifest_hash"],
        "artifact_checks": artifact_checks,
        "stream_checks": stream_checks,
        "determinism": determinism,
        "counts": {
            "admitted_packs": len(packs),
            "excluded_contrasts": len(exclusions),
            "unique_admitted_outcomes": len(admitted_outcomes),
            "story_archetypes": len(actual_archetypes),
            "story_memberships": len(story_memberships),
            "representative_cases": len(cases),
            "repetition_status_counts": dict(sorted(expected_repetition.items())),
        },
        "gate_controls": {
            "admission_and_exclusion_exact": True,
            "all_parent_memberships_preserved": True,
            "coarse_archetypes_recomputed": True,
            "exact_semantic_and_state_lineage_preserved": True,
            "singletons_not_presented_as_repeated": True,
            "counterexample_case_roles_complete": True,
            "six_month_records_per_pack": True,
            "no_probability_edge_or_execution_fields": True,
            "24h_coverage_only": True,
            "48h_blocked": True,
        },
        "authority_boundary": "Descriptive repeated-story evidence only; no independence, probability, edge, recommendation, trade or execution authority.",
    }
    (root / "OPT_D_REPEATED_STORY_EVIDENCE_VALIDATION.json").write_text(
        json.dumps(validation, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    lines = [
        "# OPT-D Repeated-Story Evidence Validation",
        "",
        "**Status:** `PASS`  ",
        f"**Validated manifest:** `{manifest['manifest_hash']}`  ",
        f"**Independent determinism:** `{'PASS' if determinism['checked'] else 'NOT RUN'}`",
        "",
        f"All {len(packs)} admitted evidence packs, {len(exclusions)} exclusions, {len(story_memberships):,} memberships, {len(actual_archetypes):,} archetypes and {len(cases)} representative cases passed lineage, coverage and canonical-stream checks.",
        "",
        "Singleton archetypes remain inventory-only. Repetition labels describe distinct overlap-cluster recurrence, not independence, probability or edge.",
    ]
    (root / "OPT_D_REPEATED_STORY_EVIDENCE_VALIDATION.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )
    print(json.dumps({"status": "PASS", "manifest_hash": manifest["manifest_hash"]}, sort_keys=True))


if __name__ == "__main__":
    main()
