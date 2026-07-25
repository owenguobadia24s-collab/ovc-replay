from __future__ import annotations

import argparse
from collections import Counter, defaultdict
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
    REVIEW_VERSION,
    frozen_holdout_rules,
    mirror_story_key,
    response_contradiction_labels,
    review_disposition,
    story_antecedent,
    story_feature_key,
    story_response,
)
from run_complete_opt_b_replay import DeterministicJsonlGzipWriter, canonical_hash  # noqa: E402


CONTRACT_VERSION = REVIEW_VERSION


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


def make_review_ledger(
    archetypes: list[dict[str, object]],
    *,
    memberships_by_archetype: dict[str, list[dict[str, object]]],
    cases_by_archetype: dict[str, list[dict[str, object]]],
    counterexamples_by_archetype: dict[str, list[dict[str, object]]],
    counter_stories_by_archetype: dict[str, dict[str, object]],
    pack_by_contrast: dict[str, dict[str, object]],
) -> list[dict[str, object]]:
    records = []
    for archetype in archetypes:
        archetype_id = archetype["story_archetype_id"]
        memberships = memberships_by_archetype[archetype_id]
        cases = cases_by_archetype[archetype_id]
        counterexamples = counterexamples_by_archetype[archetype_id]
        contrast_ids = sorted({row["contrast_id"] for row in memberships})
        outcome_ids = sorted({row["neutral_outcome_record_id"] for row in memberships})
        signature_hashes = sorted({row["exact_semantic_signature_hash"] for row in memberships})
        endpoint_patterns = sorted({row["endpoint_b_state_pattern_hash"] for row in memberships})
        transition_patterns = sorted({row["transition_axes_pattern_hash"] for row in memberships})
        disposition, reason = review_disposition(archetype["repetition_status"])
        temporal_counts = Counter(
            pack_by_contrast[contrast_id]["parent_temporal_stability"]["temporal_delta_status"]
            for contrast_id in contrast_ids
        )
        counterexample_types = Counter(row["counterexample_type"] for row in counterexamples)
        counterexample_outcomes = sorted({row["neutral_outcome_record_id"] for row in counterexamples})
        core = {
            "story_archetype_id": archetype_id,
            "source_story_feature_key": story_feature_key(archetype),
            "source_repetition_status": archetype["repetition_status"],
            "review_disposition": disposition,
            "review_reason": reason,
            "antecedent": story_antecedent(archetype),
            "forward_response": story_response(archetype),
            "source_evidence": {
                "unique_outcome_records": archetype["unique_outcome_records"],
                "distinct_overlap_clusters": archetype["distinct_overlap_clusters"],
                "distinct_anchor_months": archetype["distinct_anchor_months"],
                "outcome_record_ids_hash": archetype["outcome_record_ids_hash"],
            },
            "review_context": {
                "contrast_memberships": len(memberships),
                "distinct_contrasts": len(contrast_ids),
                "contrast_ids_hash": hash_ids(contrast_ids),
                "unique_context_outcomes": len(outcome_ids),
                "context_outcome_ids_hash": hash_ids(outcome_ids),
                "temporal_status_counts": dict(sorted(temporal_counts.items())),
                "representative_cases": len(cases),
                "representative_case_role_counts": dict(sorted(Counter(
                    row["case_role"] for row in cases
                ).items())),
                "representative_case_ids_hash": hash_ids([row["story_case_id"] for row in cases]),
                "counterexample_memberships": len(counterexamples),
                "counterexample_type_counts": dict(sorted(counterexample_types.items())),
                "unique_counterexample_outcomes": len(counterexample_outcomes),
                "counterexample_outcome_ids_hash": hash_ids(counterexample_outcomes),
                "counter_story_review": counter_stories_by_archetype[archetype_id],
            },
            "lineage_review": {
                "exact_semantic_signature_variants": len(signature_hashes),
                "exact_semantic_signature_hashes_hash": hash_ids(signature_hashes),
                "endpoint_b_state_pattern_variants": len(endpoint_patterns),
                "endpoint_b_state_pattern_hashes_hash": hash_ids(endpoint_patterns),
                "transition_axes_pattern_variants": len(transition_patterns),
                "transition_axes_pattern_hashes_hash": hash_ids(transition_patterns),
                "parent_archetype_lineage_annotations": archetype["lineage_annotations"],
            },
            "review_contract_version": CONTRACT_VERSION,
            "operator_decision": "PENDING",
            "authority": "IN_SAMPLE_EXPLORATORY_REVIEW_ONLY",
        }
        records.append({**core, "story_review_record_id": f"opt-d-review:{canonical_hash(core)}"})
    return records


def build_counter_story_index(
    archetypes: list[dict[str, object]],
    *,
    memberships_by_archetype: dict[str, list[dict[str, object]]],
) -> dict[str, dict[str, object]]:
    groups = defaultdict(list)
    for archetype in archetypes:
        groups[(
            archetype["event_timeframe"],
            tuple(archetype["event_family_set"]),
            archetype["event_direction"],
            archetype["horizon_hours"],
        )].append(archetype)
    result = {}
    for group in groups.values():
        for target in group:
            counter_ids = []
            label_counts = Counter()
            outcome_ids = set()
            cluster_ids = set()
            for other in group:
                if other["story_archetype_id"] == target["story_archetype_id"]:
                    continue
                labels = response_contradiction_labels(target, other)
                if not labels:
                    continue
                counter_ids.append(other["story_archetype_id"])
                label_counts.update(labels)
                for membership in memberships_by_archetype[other["story_archetype_id"]]:
                    outcome_ids.add(membership["neutral_outcome_record_id"])
                    cluster_ids.add(membership["overlap_cluster_id"])
            result[target["story_archetype_id"]] = {
                "definition": "SAME_ANTECEDENT_AND_HORIZON_WITH_OPPOSITE_ENDPOINT_ALIGNMENT_OR_FRONTIER_POLARITY",
                "counter_story_archetypes": len(counter_ids),
                "counter_story_archetype_ids_hash": hash_ids(counter_ids),
                "contradiction_label_counts": dict(sorted(label_counts.items())),
                "unique_counter_story_outcomes": len(outcome_ids),
                "counter_story_outcome_ids_hash": hash_ids(list(outcome_ids)),
                "distinct_counter_story_overlap_clusters": len(cluster_ids),
                "counter_story_overlap_cluster_ids_hash": hash_ids(list(cluster_ids)),
            }
    return result


def make_hypothesis(review: dict[str, object]) -> dict[str, object]:
    core = {
        "source_story_archetype_id": review["story_archetype_id"],
        "source_story_review_record_id": review["story_review_record_id"],
        "classification": "IN_SAMPLE_EXPLORATORY_PENDING_OPERATOR_RATIFICATION",
        "antecedent": review["antecedent"],
        "expected_forward_response": review["forward_response"],
        "discovery_evidence": review["source_evidence"],
        "discovery_context": review["review_context"],
        "lineage_review": review["lineage_review"],
        "primary_validation_measure": "DISTINCT_OVERLAP_CLUSTERS_MATCHING_FROZEN_STORY",
        "supporting_validation_measures": [
            "DISTINCT_ANTECEDENT_OVERLAP_CLUSTERS",
            "MATCHING_STORY_CALENDAR_MONTHS",
            "ANTECEDENT_CALENDAR_MONTHS",
            "CONTRADICTORY_RESPONSE_OVERLAP_CLUSTERS",
            "MONTHLY_MATCHING_STORY_CLUSTER_COUNTS",
        ],
        "untouched_validation_rules": frozen_holdout_rules(),
        "failure_conditions": [
            "INVALID_DEFINITION_OR_LINEAGE_DRIFT",
            "STRUCTURAL_STORY_NOT_REAPPEARED_WHEN_EVALUABLE",
            "COUNTER_STORY_ALERT",
            "STRICT_FORWARD_PATH_COVERAGE_OR_CENSORING_FAILURE",
        ],
        "review_contract_version": CONTRACT_VERSION,
        "operator_decision": "PENDING_BATCH_RATIFICATION",
        "outcome_authority": "NONE",
        "execution_authority": "NONE",
    }
    return {**core, "hypothesis_id": f"opt-d-hypothesis:{canonical_hash(core)}"}


def make_directional_registry(
    candidates: list[dict[str, object]],
    *,
    archetype_by_id: dict[str, dict[str, object]],
) -> list[dict[str, object]]:
    feature_to_id = {
        story_feature_key(archetype_by_id[row["story_archetype_id"]]): row["story_archetype_id"]
        for row in candidates
    }
    records = []
    for review in candidates:
        archetype = archetype_by_id[review["story_archetype_id"]]
        counterpart = feature_to_id.get(mirror_story_key(archetype))
        if counterpart:
            pair_members = sorted([review["story_archetype_id"], counterpart])
            pair_id = f"opt-d-direction-pair:{canonical_hash(pair_members)}"
            status = "MIRRORED_CANDIDATE_PRESENT"
        else:
            pair_members = [review["story_archetype_id"]]
            pair_id = None
            status = "MIRRORED_CANDIDATE_ABSENT"
        core = {
            "story_archetype_id": review["story_archetype_id"],
            "event_direction": archetype["event_direction"],
            "mirrored_story_archetype_id": counterpart,
            "directional_pair_id": pair_id,
            "directional_pair_members": pair_members,
            "directional_pair_status": status,
            "mirror_rule": "INVERT_DIRECTION_FIRST_EXTREME_AND_RANGE_THIRD_KEEP_RELATIVE_RESPONSE_FIELDS",
            "review_contract_version": CONTRACT_VERSION,
        }
        records.append({
            **core,
            "directional_review_record_id": f"opt-d-direction-review:{canonical_hash(core)}",
        })
    return records


def write_report(output: Path, summary: dict[str, object]) -> Path:
    lines = [
        "# OVC OPT-D Evidence Review and Pending Hypothesis Register v0.1",
        "",
        "**Status:** `BUILT FOR OPERATOR RATIFICATION — NOT PREREGISTERED`  ",
        f"**Contract:** `{CONTRACT_VERSION}`  ",
        "**Probability / edge / trade / execution authority:** `NONE`",
        "",
        "## Outcome-neutral dispositions",
        "",
        "| Disposition | Archetypes |",
        "|---|---:|",
    ]
    for status, count in summary["review_disposition_counts"].items():
        lines.append(f"| `{status}` | {count:,} |")
    lines.extend([
        "",
        f"Pending batch hypotheses: **{summary['pending_hypotheses']:,}**. All are labelled in-sample exploratory. Admission used only the parent cluster-repetition label; endpoint alignment and H1 path direction were not selection inputs.",
        "",
        "## Candidate composition",
        "",
        "| Dimension | Counts |",
        "|---|---|",
        f"| Clock | {', '.join(f'`{key}` {value}' for key, value in summary['candidate_clock_counts'].items())} |",
        f"| Horizon | {', '.join(f'`{key}h` {value}' for key, value in summary['candidate_horizon_counts'].items())} |",
        f"| Direction | {', '.join(f'`{key}` {value}' for key, value in summary['candidate_direction_counts'].items())} |",
        f"| Endpoint alignment | {', '.join(f'`{key}` {value}' for key, value in summary['candidate_alignment_counts'].items())} |",
        f"| Discovery months | {', '.join(f'`{key}` {value}' for key, value in summary['candidate_month_counts'].items())} |",
        "",
        "The register contains adverse and aligned paths together: selection is deliberately not a favourable-story filter.",
        "",
        "## Directional symmetry review",
        "",
        f"- Candidates with an exact mirrored counterpart: **{summary['candidates_with_mirror']:,}**",
        f"- Complete directional pairs: **{summary['complete_directional_pairs']:,}**",
        f"- Candidates without an exact mirrored counterpart: **{summary['candidates_without_mirror']:,}**",
        "",
        "Mirror absence is retained as review evidence. It is not repaired by weakening the story definition.",
        "",
        "## Counter-story surface",
        "",
        f"- Candidates with a deterministic competing response: **{summary['candidates_with_counter_story']:,}**",
        f"- Candidates without a qualifying competing response: **{summary['candidates_without_counter_story']:,}**",
        f"- Per-candidate distinct counter-story cluster links, summed across records: **{summary['candidate_counter_story_cluster_links']:,}**",
        "",
        "A counter-story shares the event antecedent and horizon but reverses endpoint alignment and/or held-versus-lost frontier polarity.",
        "",
        "## Clock boundary",
        "",
        "All pending hypotheses are 15M. No 2H parent contrast reached the admitted OPT-D story surface, so this release grants no 2H story hypothesis authority.",
        "",
        "## Frozen untouched-validation gate",
        "",
        "A new non-overlapping sealed OPT-A release is required. A hypothesis is evaluable only with at least 10 antecedent clusters across four months, and structurally reappears only with at least 10 exact story matches across four months. Definition changes after opening holdout data invalidate the run.",
        "",
        "## Operator decision",
        "",
        "The contract and the complete candidate set remain pending batch ratification. No individual hypothesis may be selected because its H1 path appears favourable. After ratification, the next build is `OPT-D-VALIDATE-0.1` on untouched data.",
    ])
    path = output / "OVC_OPT_D_EVIDENCE_REVIEW_REPORT_v0_1.md"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--story-root", type=Path, required=True)
    parser.add_argument("--contrast-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    story_root = args.story_root.resolve()
    contrast_root = args.contrast_root.resolve()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    manifest_path = output / "OPT_D_EVIDENCE_REVIEW_MANIFEST.json"
    if manifest_path.exists():
        raise FileExistsError("OPT-D review release already finalized")

    story_manifest = verify_manifest(
        story_root, "OPT_D_REPEATED_STORY_EVIDENCE_MANIFEST.json"
    )
    contrast_manifest = verify_manifest(
        contrast_root, "OPT_D_CLUSTER_BALANCED_CONTRAST_MANIFEST.json"
    )
    if story_manifest["parent_contrast_manifest_hash"] != contrast_manifest["manifest_hash"]:
        raise ValueError("story/contrast lineage mismatch")
    if story_manifest["story_contract_version"] != "OPT-D-STORY-0.1":
        raise ValueError("unsupported story contract")

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

    review_records = make_review_ledger(
        archetypes,
        memberships_by_archetype=memberships_by_archetype,
        cases_by_archetype=cases_by_archetype,
        counterexamples_by_archetype=counterexamples_by_archetype,
        counter_stories_by_archetype=counter_stories_by_archetype,
        pack_by_contrast=pack_by_contrast,
    )
    candidates = [
        row for row in review_records
        if row["review_disposition"] == "CANDIDATE_FOR_BATCH_PREREGISTRATION"
    ]
    hypotheses = [make_hypothesis(row) for row in candidates]
    directional_records = make_directional_registry(
        candidates, archetype_by_id=archetype_by_id
    )

    paired_candidates = [
        row for row in directional_records
        if row["directional_pair_status"] == "MIRRORED_CANDIDATE_PRESENT"
    ]
    pair_ids = {row["directional_pair_id"] for row in paired_candidates}
    summary = {
        "reviewed_archetypes": len(review_records),
        "review_disposition_counts": dict(sorted(Counter(
            row["review_disposition"] for row in review_records
        ).items())),
        "pending_hypotheses": len(hypotheses),
        "candidate_clock_counts": dict(sorted(Counter(
            row["antecedent"]["event_timeframe"] for row in candidates
        ).items())),
        "candidate_horizon_counts": dict(sorted(Counter(
            str(row["forward_response"]["horizon_hours"]) for row in candidates
        ).items(), key=lambda item: int(item[0]))),
        "candidate_direction_counts": dict(sorted(Counter(
            row["antecedent"]["event_direction"] for row in candidates
        ).items())),
        "candidate_alignment_counts": dict(sorted(Counter(
            row["forward_response"]["endpoint_alignment"] for row in candidates
        ).items())),
        "candidate_month_counts": dict(sorted(Counter(
            str(row["source_evidence"]["distinct_anchor_months"]) for row in candidates
        ).items(), key=lambda item: int(item[0]))),
        "candidate_family_counts": dict(sorted(Counter(
            "+".join(row["antecedent"]["event_family_set"]) for row in candidates
        ).items())),
        "candidates_with_mirror": len(paired_candidates),
        "complete_directional_pairs": len(pair_ids),
        "candidates_without_mirror": len(directional_records) - len(paired_candidates),
        "candidate_counterexample_memberships": sum(
            row["review_context"]["counterexample_memberships"] for row in candidates
        ),
        "candidate_representative_cases": sum(
            row["review_context"]["representative_cases"] for row in candidates
        ),
        "candidates_with_counter_story": sum(
            row["review_context"]["counter_story_review"]["counter_story_archetypes"] > 0
            for row in candidates
        ),
        "candidates_without_counter_story": sum(
            row["review_context"]["counter_story_review"]["counter_story_archetypes"] == 0
            for row in candidates
        ),
        "candidate_counter_story_cluster_links": sum(
            row["review_context"]["counter_story_review"]["distinct_counter_story_overlap_clusters"]
            for row in candidates
        ),
        "holdout_rules": frozen_holdout_rules(),
        "operator_decision": "PENDING_BATCH_RATIFICATION",
    }

    writers = {
        "review": DeterministicJsonlGzipWriter(output / "opt_d_story_review_ledger.jsonl.gz"),
        "hypothesis": DeterministicJsonlGzipWriter(output / "opt_d_pending_hypothesis_register.jsonl.gz"),
        "directional": DeterministicJsonlGzipWriter(output / "opt_d_directional_symmetry_review.jsonl.gz"),
    }
    for row in review_records:
        writers["review"].write(row)
    for row in hypotheses:
        writers["hypothesis"].write(row)
    for row in directional_records:
        writers["directional"].write(row)
    artifacts = []
    stream_metadata = {}
    for name, writer in writers.items():
        writer.close()
        artifacts.append({
            "path": writer.path.name,
            "sha256": sha256(writer.path),
            "size_bytes": writer.path.stat().st_size,
        })
        stream_metadata[f"{name}_records"] = writer.count
        stream_metadata[f"{name}_stream_canonical_jsonl_hash"] = writer.canonical_jsonl_hash
    summary["stream_metadata"] = stream_metadata

    summary_path = output / "opt_d_evidence_review_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    artifacts.append({
        "path": summary_path.name,
        "sha256": sha256(summary_path),
        "size_bytes": summary_path.stat().st_size,
    })
    report = write_report(output, summary)
    artifacts.append({"path": report.name, "sha256": sha256(report), "size_bytes": report.stat().st_size})
    for source in (
        ROOT / "contracts/OVC_OPT_D_EVIDENCE_REVIEW_HYPOTHESIS_CONTRACT_v0_1.md",
        ROOT / "contracts/OPT_D_REVIEW_OPERATOR_RATIFICATION_CHECKLIST_v0_1.md",
        ROOT / "contracts/OVC_OPT_D_REPEATED_STORY_EVIDENCE_CONTRACT_v0_1.md",
    ):
        destination = output / source.name
        shutil.copy2(source, destination)
        artifacts.append({
            "path": destination.name,
            "sha256": sha256(destination),
            "size_bytes": destination.stat().st_size,
        })

    manifest_core = {
        "release_id": "OPT-D-EVIDENCE-REVIEW-GBPUSD-2026H1-v0.1",
        "status": "BUILT_FOR_OPERATOR_RATIFICATION_NOT_PREREGISTERED",
        "generated_date": "2026-07-19",
        "review_contract_version": CONTRACT_VERSION,
        "parent_story_manifest_hash": story_manifest["manifest_hash"],
        "parent_contrast_manifest_hash": contrast_manifest["manifest_hash"],
        "coverage_only_horizons_hours": [24],
        "blocked_horizons_hours": [48],
        "results": summary,
        "artifacts": artifacts,
        "implementation_hashes": {
            "__init__.py": sha256(ROOT / "src/ovc_opt_b/__init__.py"),
            "review.py": sha256(ROOT / "src/ovc_opt_b/review.py"),
            "build_opt_d_review.py": sha256(Path(__file__).resolve()),
            "test_opt_d_review.py": sha256(ROOT / "tests/test_opt_d_review.py"),
        },
        "authority_boundary": "In-sample exploratory review and pending hypothesis definitions only. No validation, independence, probability, edge, recommendation, trade or execution authority.",
    }
    manifest = {**manifest_core, "manifest_hash": canonical_hash(manifest_core)}
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": manifest["status"],
        "manifest_hash": manifest["manifest_hash"],
        "reviewed_archetypes": len(review_records),
        "pending_hypotheses": len(hypotheses),
    }, sort_keys=True))


if __name__ == "__main__":
    main()
