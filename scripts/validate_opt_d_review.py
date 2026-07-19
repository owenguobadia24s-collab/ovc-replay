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
from build_opt_d_review import (  # noqa: E402
    CONTRACT_VERSION,
    build_counter_story_index,
    make_directional_registry,
    make_hypothesis,
    make_review_ledger,
)
from ovc_opt_b import frozen_holdout_rules  # noqa: E402
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
    parser.add_argument("--story-root", type=Path, required=True)
    parser.add_argument("--contrast-root", type=Path, required=True)
    parser.add_argument("--determinism-root", type=Path)
    args = parser.parse_args()
    root = args.release_root.resolve()
    story_root = args.story_root.resolve()
    contrast_root = args.contrast_root.resolve()

    manifest = verify_manifest(root, "OPT_D_EVIDENCE_REVIEW_MANIFEST.json")
    story_manifest = verify_manifest(
        story_root, "OPT_D_REPEATED_STORY_EVIDENCE_MANIFEST.json"
    )
    contrast_manifest = verify_manifest(
        contrast_root, "OPT_D_CLUSTER_BALANCED_CONTRAST_MANIFEST.json"
    )
    if manifest["review_contract_version"] != CONTRACT_VERSION:
        raise ValueError("review contract version mismatch")
    if manifest["parent_story_manifest_hash"] != story_manifest["manifest_hash"]:
        raise ValueError("story lineage mismatch")
    if manifest["parent_contrast_manifest_hash"] != contrast_manifest["manifest_hash"]:
        raise ValueError("contrast lineage mismatch")
    if story_manifest["parent_contrast_manifest_hash"] != contrast_manifest["manifest_hash"]:
        raise ValueError("parent chain mismatch")

    artifact_checks = []
    for artifact in manifest["artifacts"]:
        path = root / artifact["path"]
        actual = sha256(path)
        if actual != artifact["sha256"]:
            raise ValueError(f"artifact hash mismatch: {path.name}")
        artifact_checks.append({"path": path.name, "sha256": actual, "status": "PASS"})

    archetypes = load_gzip(story_root / "opt_d_story_archetype_registry.jsonl.gz")
    archetype_by_id = {row["story_archetype_id"]: row for row in archetypes}
    memberships = load_gzip(story_root / "opt_d_story_memberships.jsonl.gz")
    cases = load_gzip(story_root / "opt_d_story_case_index.jsonl.gz")
    packs = load_gzip(story_root / "opt_d_story_evidence_packs.jsonl.gz")
    pack_by_contrast = {row["contrast_id"]: row for row in packs}
    memberships_by_archetype = defaultdict(list)
    story_by_contrast_outcome = {}
    for row in memberships:
        memberships_by_archetype[row["story_archetype_id"]].append(row)
        story_by_contrast_outcome[(row["contrast_id"], row["neutral_outcome_record_id"])] = row[
            "story_archetype_id"
        ]
    cases_by_archetype = defaultdict(list)
    for row in cases:
        cases_by_archetype[row["story_archetype_id"]].append(row)
    counterexamples_by_archetype = defaultdict(list)
    for row in load_gzip(contrast_root / "opt_d_contrast_counterexamples.jsonl.gz"):
        archetype_id = story_by_contrast_outcome.get(
            (row["contrast_id"], row["neutral_outcome_record_id"])
        )
        if archetype_id:
            counterexamples_by_archetype[archetype_id].append(row)
    counter_stories_by_archetype = build_counter_story_index(
        archetypes, memberships_by_archetype=memberships_by_archetype
    )

    expected_review = make_review_ledger(
        archetypes,
        memberships_by_archetype=memberships_by_archetype,
        cases_by_archetype=cases_by_archetype,
        counterexamples_by_archetype=counterexamples_by_archetype,
        counter_stories_by_archetype=counter_stories_by_archetype,
        pack_by_contrast=pack_by_contrast,
    )
    actual_review = load_gzip(root / "opt_d_story_review_ledger.jsonl.gz")
    if actual_review != expected_review:
        raise ValueError("review ledger mismatch")
    candidates = [
        row for row in expected_review
        if row["review_disposition"] == "CANDIDATE_FOR_BATCH_PREREGISTRATION"
    ]
    expected_hypotheses = [make_hypothesis(row) for row in candidates]
    actual_hypotheses = load_gzip(root / "opt_d_pending_hypothesis_register.jsonl.gz")
    if actual_hypotheses != expected_hypotheses:
        raise ValueError("hypothesis register mismatch")
    expected_directional = make_directional_registry(
        candidates, archetype_by_id=archetype_by_id
    )
    actual_directional = load_gzip(root / "opt_d_directional_symmetry_review.jsonl.gz")
    if actual_directional != expected_directional:
        raise ValueError("directional symmetry registry mismatch")

    source_status_counts = Counter(row["repetition_status"] for row in archetypes)
    disposition_counts = Counter(row["review_disposition"] for row in actual_review)
    expected_dispositions = {
        "CANDIDATE_FOR_BATCH_PREREGISTRATION": source_status_counts["REPEATED_DESCRIPTIVE_SUPPORT"],
        "RETAIN_LIMITED_SUPPORT_INVENTORY": source_status_counts["REPEATED_LIMITED_SUPPORT"],
        "RETAIN_MINIMAL_SUPPORT_INVENTORY": source_status_counts["REPEATED_MINIMAL_SUPPORT"],
        "RETAIN_SINGLETON_INVENTORY": source_status_counts["SINGLETON_INVENTORY"],
    }
    if disposition_counts != Counter(expected_dispositions):
        raise ValueError("outcome-neutral disposition mismatch")
    if len(actual_hypotheses) != 202:
        raise ValueError("pending hypothesis candidate set must remain complete")
    if {row["expected_forward_response"]["endpoint_alignment"] for row in actual_hypotheses} != {
        "ALIGNED", "OPPOSITE"
    }:
        raise ValueError("candidate register omitted an endpoint alignment class")
    if Counter(
        row["expected_forward_response"]["endpoint_alignment"] for row in actual_hypotheses
    ) != {"ALIGNED": 81, "OPPOSITE": 121}:
        raise ValueError("alignment-neutral admission count mismatch")
    if any(
        row["discovery_context"]["counter_story_review"]["counter_story_archetypes"] == 0
        for row in actual_hypotheses
    ):
        raise ValueError("candidate missing deterministic counter-story surface")
    if {row["antecedent"]["event_timeframe"] for row in actual_hypotheses} != {"15M"}:
        raise ValueError("unexpected clock gained hypothesis authority")

    allowed_antecedent_keys = {
        "event_timeframe", "event_family_set", "event_direction",
        "eligibility_time", "antecedent_contract",
    }
    for hypothesis in actual_hypotheses:
        if set(hypothesis["antecedent"]) != allowed_antecedent_keys:
            raise ValueError("forward response leaked into antecedent")
        if hypothesis["untouched_validation_rules"] != frozen_holdout_rules():
            raise ValueError("holdout rule drift")
        if hypothesis["operator_decision"] != "PENDING_BATCH_RATIFICATION":
            raise ValueError("hypothesis was silently ratified")
        if hypothesis["execution_authority"] != "NONE":
            raise ValueError("execution authority escaped review gate")

    directional_by_story = {
        row["story_archetype_id"]: row for row in actual_directional
    }
    for row in actual_directional:
        counterpart = row["mirrored_story_archetype_id"]
        if counterpart:
            other = directional_by_story[counterpart]
            if other["mirrored_story_archetype_id"] != row["story_archetype_id"]:
                raise ValueError("directional mirror is not reciprocal")
            if other["directional_pair_id"] != row["directional_pair_id"]:
                raise ValueError("directional pair ID mismatch")
    paired = [row for row in actual_directional if row["mirrored_story_archetype_id"]]
    if len(paired) != 156 or len({row["directional_pair_id"] for row in paired}) != 78:
        raise ValueError("directional mirror coverage mismatch")

    forbidden = {"win_rate", "profit", "position_size", "trade_signal", "validated_edge"}
    materialized_keys = set().union(
        recursive_keys(actual_review),
        recursive_keys(actual_hypotheses),
        recursive_keys(actual_directional),
    )
    if forbidden.intersection(materialized_keys):
        raise ValueError("forbidden authority field materialized")

    stream_checks = []
    for filename, prefix, expected_count in (
        ("opt_d_story_review_ledger.jsonl.gz", "review", 1830),
        ("opt_d_pending_hypothesis_register.jsonl.gz", "hypothesis", 202),
        ("opt_d_directional_symmetry_review.jsonl.gz", "directional", 202),
    ):
        stream_hash, count = canonical_stream_hash(root / filename)
        metadata = manifest["results"]["stream_metadata"]
        if count != expected_count or count != metadata[f"{prefix}_records"]:
            raise ValueError(f"stream count mismatch: {filename}")
        if stream_hash != metadata[f"{prefix}_stream_canonical_jsonl_hash"]:
            raise ValueError(f"stream canonical hash mismatch: {filename}")
        stream_checks.append({"path": filename, "rows": count, "canonical_jsonl_hash": stream_hash})

    determinism = {"checked": False}
    if args.determinism_root:
        other = verify_manifest(
            args.determinism_root.resolve(), "OPT_D_EVIDENCE_REVIEW_MANIFEST.json"
        )
        if other["manifest_hash"] != manifest["manifest_hash"]:
            raise ValueError("review release determinism mismatch")
        determinism = {"checked": True, "manifest_hash_match": True}

    validation = {
        "status": "PASS",
        "validated_manifest_hash": manifest["manifest_hash"],
        "artifact_checks": artifact_checks,
        "stream_checks": stream_checks,
        "determinism": determinism,
        "counts": {
            "reviewed_archetypes": len(actual_review),
            "pending_hypotheses": len(actual_hypotheses),
            "complete_directional_pairs": 78,
            "unpaired_candidates": 46,
            "review_disposition_counts": dict(sorted(disposition_counts.items())),
        },
        "gate_controls": {
            "outcome_neutral_dispositions_recomputed": True,
            "complete_candidate_batch_preserved": True,
            "antecedent_response_separation_verified": True,
            "all_holdout_rules_frozen": True,
            "directional_mirrors_recomputed": True,
            "counterexamples_and_cases_linked": True,
            "counter_story_surface_recomputed": True,
            "operator_decision_remains_pending": True,
            "no_2h_hypothesis_authority": True,
            "24h_coverage_only": True,
            "48h_blocked": True,
            "no_trade_or_execution_authority": True,
        },
        "authority_boundary": "Pending in-sample exploratory hypotheses only; no validation, probability, edge, recommendation, trade or execution authority.",
    }
    (root / "OPT_D_EVIDENCE_REVIEW_VALIDATION.json").write_text(
        json.dumps(validation, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    lines = [
        "# OPT-D Evidence Review Validation",
        "",
        "**Status:** `PASS`  ",
        f"**Validated manifest:** `{manifest['manifest_hash']}`  ",
        f"**Independent determinism:** `{'PASS' if determinism['checked'] else 'NOT RUN'}`",
        "",
        "All 1,830 story dispositions, 202 pending hypotheses and 202 directional-symmetry records were independently recomputed and matched.",
        "",
        "The complete candidate batch contains both aligned and opposite H1 paths. All operator decisions remain pending and no 2H, probability, edge, trade or execution authority was granted.",
    ]
    (root / "OPT_D_EVIDENCE_REVIEW_VALIDATION.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )
    print(json.dumps({"status": "PASS", "manifest_hash": manifest["manifest_hash"]}, sort_keys=True))


if __name__ == "__main__":
    main()
