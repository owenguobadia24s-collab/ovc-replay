"""Compact, fail-closed CEAR-G10 disposition-evidence builder.

The builder reads an already completed, content-addressed C2 vNext full replay
and emits only compact research evidence. It never mutates replay payloads and
cannot grant selector, semantic, outcome, publication, Validation, probability,
risk, exposure, trading, execution, or agent-write authority.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator, Mapping, Sequence

SCHEMA = "ovc-c2-vnext-cear-g10-disposition-evidence/v1"
AUTHORITY = "PROVISIONAL_DISCOVERY_RESEARCH_ONLY"
DENIED = {
    "active_selector": "DENIED",
    "release_publication": "DENIED",
    "r2_write": "DENIED",
    "validation_consumption": "DENIED",
    "semantic_promotion": "DENIED",
    "probability_risk_exposure_execution": "DENIED",
    "agent_write": "DENIED",
}
TERMINAL_RECEIPTS = (
    "orchestration-receipt.json",
    "determinism-receipt.json",
    "restart-receipt.json",
)
RUN_DIRS = ("run-001", "run-002", "restart-verification")
EVIDENCE_FILES = (
    "opportunity-population.jsonl",
    "motifs.json",
    "families.json",
    "functional-cores.json",
    "rule-candidates.jsonl",
    "rule-evaluations.jsonl",
    "matched-controls.jsonl",
)


class DispositionEvidenceError(RuntimeError):
    """Raised when compact evidence cannot be reproduced lawfully."""


def canonical(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"),
        ensure_ascii=False, allow_nan=False,
    ).encode("utf-8")


def sha_value(value: Any) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def sha_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise DispositionEvidenceError(f"INVALID_JSON:{path}") from exc
    if not isinstance(value, dict):
        raise DispositionEvidenceError(f"JSON_OBJECT_REQUIRED:{path}")
    return value


def iter_jsonl(path: Path) -> Iterator[dict[str, Any]]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            for line_number, raw in enumerate(handle, start=1):
                if not raw.strip():
                    continue
                value = json.loads(raw)
                if not isinstance(value, dict):
                    raise DispositionEvidenceError(
                        f"JSONL_OBJECT_REQUIRED:{path}:{line_number}"
                    )
                yield value
    except (OSError, json.JSONDecodeError) as exc:
        raise DispositionEvidenceError(f"INVALID_JSONL:{path}") from exc


def write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def _require(condition: bool, marker: str) -> None:
    if not condition:
        raise DispositionEvidenceError(marker)


def git_head(repository_root: Path) -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=repository_root, check=True,
            capture_output=True, text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        raise DispositionEvidenceError("ANALYSIS_GIT_HEAD_UNAVAILABLE") from exc


def _week_key(timestamp: str) -> str:
    try:
        parsed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    except ValueError as exc:
        raise DispositionEvidenceError(f"INVALID_FIRST_VALID_TIME:{timestamp}") from exc
    year, week, _ = parsed.isocalendar()
    return f"{year}-W{week:02d}"


def _half_key(timestamp: str) -> str:
    try:
        parsed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    except ValueError as exc:
        raise DispositionEvidenceError(f"INVALID_FIRST_VALID_TIME:{timestamp}") from exc
    return f"{parsed.year:04d}-{parsed.month:02d}-H{1 if parsed.day <= 15 else 2}"


def verify_replay_root(replay_root: Path) -> dict[str, Any]:
    replay_root = replay_root.resolve()
    receipts = {name: read_json(replay_root / name) for name in TERMINAL_RECEIPTS}
    for name, receipt in receipts.items():
        _require(receipt.get("result") == "PASS", f"TERMINAL_RECEIPT_NOT_PASS:{name}")
    determinism = receipts["determinism-receipt.json"]
    _require(determinism.get("discrepancies") == [], "DETERMINISM_DISCREPANCIES_PRESENT")
    for key in ("artifact_inventory_match", "count_reconciliation_match", "logical_hash_match", "restart_exercised"):
        _require(determinism.get(key) is True, f"DETERMINISM_ASSERTION_FAILED:{key}")
    restart = receipts["restart-receipt.json"]
    for key in ("checkpoint_loaded", "logical_hash_matches_clean_runs", "resumed_to_completion"):
        _require(restart.get(key) is True, f"RESTART_ASSERTION_FAILED:{key}")

    manifests = {name: read_json(replay_root / name / "output-manifest.json") for name in RUN_DIRS}
    baseline = manifests[RUN_DIRS[0]]
    stable = (
        "binding_id", "binding_sha256", "code_commit", "logical_population_sha256",
        "counts", "interval", "complete_accounting", "first_valid_chronology",
        "legacy_seed_count", "outcome_dependency_count", "validation_dependency_count",
        "active", "canonical", "authority",
    )
    for run_name, manifest in manifests.items():
        for key in stable:
            _require(manifest.get(key) == baseline.get(key), f"RUN_MANIFEST_MISMATCH:{run_name}:{key}")
        _require(manifest.get("complete_accounting") is True, f"INCOMPLETE_ACCOUNTING:{run_name}")
        _require(manifest.get("first_valid_chronology") is True, f"FIRST_VALID_FAILURE:{run_name}")
        _require(manifest.get("legacy_seed_count") == 0, f"LEGACY_SEED_PRESENT:{run_name}")
        _require(manifest.get("outcome_dependency_count") == 0, f"OUTCOME_DEPENDENCY_PRESENT:{run_name}")
        _require(manifest.get("validation_dependency_count") == 0, f"VALIDATION_DEPENDENCY_PRESENT:{run_name}")
        _require(manifest.get("active") is False and manifest.get("canonical") is False, f"REPLAY_AUTHORITY_DRIFT:{run_name}")
        for filename in EVIDENCE_FILES:
            _require((replay_root / run_name / "evidence" / filename).is_file(), f"EVIDENCE_FILE_MISSING:{run_name}:{filename}")
    orchestration = receipts["orchestration-receipt.json"]
    _require(orchestration.get("binding_sha256") == baseline.get("binding_sha256"), "ORCHESTRATION_BINDING_MISMATCH")
    _require(orchestration.get("logical_population_sha256") == baseline.get("logical_population_sha256"), "ORCHESTRATION_LOGICAL_HASH_MISMATCH")
    _require(orchestration.get("clean_run_count") == 2, "TWO_CLEAN_RUNS_REQUIRED")
    _require(orchestration.get("authority") == DENIED, "ORCHESTRATION_AUTHORITY_DRIFT")
    return {
        "replay_root": replay_root.as_posix(),
        "receipts": receipts,
        "manifests": manifests,
        "baseline_manifest": baseline,
    }


def _opportunity_index(population_path: Path) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    outcomes: Counter[str] = Counter()
    for row in iter_jsonl(population_path):
        opportunity_id = str(row.get("opportunity_id", ""))
        _require(bool(opportunity_id), "OPPORTUNITY_ID_REQUIRED")
        _require(opportunity_id not in index, f"DUPLICATE_OPPORTUNITY_ID:{opportunity_id}")
        ordered = row.get("ordered_development")
        _require(isinstance(ordered, list), f"ORDERED_DEVELOPMENT_REQUIRED:{opportunity_id}")
        timestamp = str(row.get("first_valid_time", ""))
        meta = {
            "clock_id": str(row.get("clock_id", "")),
            "side": str(row.get("side", "")),
            "frame_id": str(row.get("frame_id", "")),
            "object_family": str(row.get("object_family", "")),
            "sequence_length": len(ordered),
            "duration_observations": int(row.get("duration_observations", 0)),
            "first_valid_time": timestamp,
            "week": _week_key(timestamp),
            "month_half": _half_key(timestamp),
            "opportunity_outcome": str(row.get("opportunity_outcome", "")),
        }
        index[opportunity_id] = meta
        outcomes[meta["opportunity_outcome"]] += 1
    return index, {
        "record_count": len(index),
        "outcome_counts": dict(sorted(outcomes.items())),
        "population_index_sha256": sha_value(index),
    }


def _rates_by_dimension(
    results: Sequence[Mapping[str, Any]],
    opportunity_index: Mapping[str, Mapping[str, Any]],
    dimension: str,
) -> list[dict[str, Any]]:
    counts: dict[str, Counter[str]] = defaultdict(Counter)
    for result in results:
        opportunity_id = str(result["opportunity_id"])
        meta = opportunity_index.get(opportunity_id)
        _require(meta is not None, f"EVALUATION_OPPORTUNITY_MISSING:{opportunity_id}")
        counts[str(meta[dimension])][str(result["evaluation_outcome"])] += 1
    output = []
    for value in sorted(counts):
        counter = counts[value]
        computable = counter.get("MATCHED", 0) + counter.get("NOT_MATCHED", 0)
        output.append({
            "value": value,
            "result_count": sum(counter.values()),
            "outcome_counts": dict(sorted(counter.items())),
            "computable_count": computable,
            "matched_count": counter.get("MATCHED", 0),
            "match_rate_within_computable": None if computable == 0 else counter.get("MATCHED", 0) / computable,
        })
    return output


def _control_summaries(
    controls_path: Path,
    candidates: Sequence[Mapping[str, Any]],
) -> dict[str, dict[str, Any]]:
    controls = list(iter_jsonl(controls_path))
    _require(len(controls) == len(candidates), "CONTROL_SET_CANDIDATE_COUNT_MISMATCH")
    output: dict[str, dict[str, Any]] = {}
    for candidate, control in zip(candidates, controls):
        candidate_id = str(candidate["rule_candidate_id"])
        _require(control.get("member_count") == len(candidate.get("source_opportunity_ids", [])), f"CONTROL_MEMBER_COUNT_MISMATCH:{candidate_id}")
        _require(control.get("hidden_nearest_or_best_selection") is False, f"HIDDEN_CONTROL_SELECTION:{candidate_id}")
        output[candidate_id] = {
            "control_set_id": control.get("control_set_id"),
            "member_count": control.get("member_count"),
            "matched_count": control.get("matched_count"),
            "unmatched_count": control.get("unmatched_count"),
            "duration_bin_size": control.get("duration_bin_size"),
            "complete_control_coverage": control.get("unmatched_count") == 0 and control.get("matched_count") == control.get("member_count"),
            "unmatched_reason_counts": dict(sorted(Counter(str(item.get("reason_code")) for item in control.get("unmatched_requests", [])).items())),
            "content_sha256": control.get("content_sha256"),
        }
    return output


def _candidate_summaries(
    evaluation_path: Path,
    candidates: Sequence[Mapping[str, Any]],
    cores: Mapping[str, Any],
    families: Mapping[str, Any],
    controls: Mapping[str, Mapping[str, Any]],
    opportunity_index: Mapping[str, Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, set[str]]]:
    evaluations = list(iter_jsonl(evaluation_path))
    _require(len(evaluations) == len(candidates), "EVALUATION_CANDIDATE_COUNT_MISMATCH")
    core_by_id = {str(item["functional_core_id"]): item for item in cores.get("functional_cores", [])}
    family_by_id = {str(item["family_id"]): item for item in families.get("families", [])}
    output: list[dict[str, Any]] = []
    match_sets: dict[str, set[str]] = {}
    for candidate, evaluation in zip(candidates, evaluations):
        candidate_id = str(candidate["rule_candidate_id"])
        _require(evaluation.get("rule_candidate_id") == candidate_id, f"EVALUATION_ORDER_MISMATCH:{candidate_id}")
        results = evaluation.get("results")
        _require(isinstance(results, list), f"EVALUATION_RESULTS_REQUIRED:{candidate_id}")
        _require(evaluation.get("complete_accounting") is True, f"EVALUATION_ACCOUNTING_FAILURE:{candidate_id}")
        _require(len(results) == len(opportunity_index), f"EVALUATION_POPULATION_COUNT_MISMATCH:{candidate_id}")
        observed_counts = Counter(str(item.get("evaluation_outcome")) for item in results)
        _require(dict(sorted(observed_counts.items())) == evaluation.get("outcome_counts"), f"EVALUATION_OUTCOME_COUNT_MISMATCH:{candidate_id}")
        matched = {str(item["opportunity_id"]) for item in results if item.get("evaluation_outcome") == "MATCHED"}
        not_matched = {str(item["opportunity_id"]) for item in results if item.get("evaluation_outcome") == "NOT_MATCHED"}
        match_sets[candidate_id] = matched
        source_ids = {str(item) for item in candidate.get("source_opportunity_ids", [])}
        _require(source_ids.issubset(opportunity_index), f"CANDIDATE_SOURCE_OPPORTUNITY_MISSING:{candidate_id}")
        first_valid_weeks = sorted({opportunity_index[item]["week"] for item in source_ids})
        first_valid_halves = sorted({opportunity_index[item]["month_half"] for item in source_ids})
        core = core_by_id.get(str(candidate.get("functional_core_id")))
        family = family_by_id.get(str(candidate.get("family_id")))
        _require(core is not None and family is not None, f"CANDIDATE_LINEAGE_MISSING:{candidate_id}")
        output.append({
            "rule_candidate_id": candidate_id,
            "functional_core_id": candidate.get("functional_core_id"),
            "family_id": candidate.get("family_id"),
            "method_pack_id": candidate.get("method_pack_id"),
            "source_opportunity_count": len(source_ids),
            "source_fingerprint_count": len(candidate.get("source_fingerprint_ids", [])),
            "source_week_count": len(first_valid_weeks),
            "source_weeks": first_valid_weeks,
            "source_month_halves": first_valid_halves,
            "independent_recurrence_observed": len(first_valid_weeks) >= 2,
            "ast_operator": candidate.get("ast", {}).get("operator"),
            "ast_clause_count": len(candidate.get("ast", {}).get("clauses", [])),
            "evaluation_population_id": evaluation.get("evaluation_population_id"),
            "evaluation_result_count": len(results),
            "evaluation_outcome_counts": dict(sorted(observed_counts.items())),
            "matched_count": len(matched),
            "counterexample_count": len(not_matched),
            "counterexample_set_sha256": sha_value(sorted(not_matched)),
            "match_set_sha256": sha_value(sorted(matched)),
            "stability": {
                "clock": _rates_by_dimension(results, opportunity_index, "clock_id"),
                "side": _rates_by_dimension(results, opportunity_index, "side"),
                "sequence_length": _rates_by_dimension(results, opportunity_index, "sequence_length"),
                "week": _rates_by_dimension(results, opportunity_index, "week"),
                "month_half": _rates_by_dimension(results, opportunity_index, "month_half"),
            },
            "matched_controls": controls[candidate_id],
            "functional_core": {
                "member_count": core.get("member_count"),
                "classification_counts": core.get("classification_counts"),
                "semantic_name": core.get("semantic_name"),
                "provisional": core.get("provisional"),
            },
            "family": {
                "member_count": family.get("member_count"),
                "member_opportunity_count": len(family.get("member_opportunity_ids", [])),
                "distance_threshold": family.get("distance_threshold"),
                "provisional": family.get("provisional"),
                "semantic_authority": family.get("semantic_authority"),
            },
            "active": candidate.get("active"),
            "canonical": candidate.get("canonical"),
            "denied_authorities": {
                "selector": candidate.get("selector_authority"),
                "event": candidate.get("event_authority"),
                "episode": candidate.get("episode_authority"),
                "semantic": candidate.get("semantic_authority"),
                "outcome": candidate.get("outcome_authority"),
            },
            "operator_decision": None,
            "allowed_gate_decisions": ["PASS", "DEFER", "BLOCK", "QUARANTINE", "SUPERSEDE"],
        })
    return sorted(output, key=lambda item: item["rule_candidate_id"]), match_sets


def _jaccard(left: set[str], right: set[str]) -> float:
    union = left | right
    return 1.0 if not union else len(left & right) / len(union)


def _redundancy_surface(match_sets: Mapping[str, set[str]]) -> list[dict[str, Any]]:
    ids = sorted(match_sets)
    output = []
    for index, left_id in enumerate(ids):
        for right_id in ids[index + 1:]:
            left, right = match_sets[left_id], match_sets[right_id]
            output.append({
                "left_rule_candidate_id": left_id,
                "right_rule_candidate_id": right_id,
                "left_match_count": len(left),
                "right_match_count": len(right),
                "intersection_count": len(left & right),
                "union_count": len(left | right),
                "jaccard_similarity": _jaccard(left, right),
                "identical_match_population": left == right,
            })
    return output


def _cluster_motifs(motifs: Sequence[Mapping[str, Any]], threshold: float) -> list[list[str]]:
    remaining = {str(item["motif_id"]): item for item in motifs}
    families: list[list[str]] = []
    while remaining:
        medoid_id = sorted(remaining)[0]
        medoid = remaining.pop(medoid_id)
        medoid_tokens = set(str(item) for item in medoid.get("signature_tokens", []))
        members = [medoid_id]
        for motif_id in sorted(list(remaining)):
            tokens = set(str(item) for item in remaining[motif_id].get("signature_tokens", []))
            union = medoid_tokens | tokens
            distance = 0.0 if not union else 1.0 - len(medoid_tokens & tokens) / len(union)
            if distance <= threshold:
                members.append(motif_id)
                remaining.pop(motif_id)
        families.append(sorted(members))
    return families


def _parameter_surface(motifs: Mapping[str, Any], cores: Mapping[str, Any], method: Mapping[str, Any]) -> dict[str, Any]:
    retained = list(motifs.get("motifs", []))
    negatives = list(motifs.get("negative_candidates", []))
    all_candidates = retained + negatives
    baseline_support = int(method.get("minimum_motif_support", 2))
    support_values = sorted({baseline_support, 3, 5})
    support_surface = []
    for threshold in support_values:
        retained_here = [item for item in all_candidates if int(item.get("support_count", 0)) >= threshold]
        support_surface.append({
            "minimum_motif_support": threshold,
            "retained_motif_count": len(retained_here),
            "retained_member_count": sum(int(item.get("support_count", 0)) for item in retained_here),
            "excluded_candidate_count": len(all_candidates) - len(retained_here),
            "retained_ids_sha256": sha_value(sorted(str(item.get("motif_id") or item.get("motif_candidate_id")) for item in retained_here)),
            "baseline": threshold == baseline_support,
        })
    baseline_distance = float(method.get("family_distance_threshold", 0.35))
    distance_values = sorted({0.20, baseline_distance, 0.50})
    distance_surface = []
    for threshold in distance_values:
        families = _cluster_motifs(retained, threshold)
        distance_surface.append({
            "family_distance_threshold": threshold,
            "family_count": len(families),
            "family_member_count_distribution": sorted(len(item) for item in families),
            "assignment_sha256": sha_value(families),
            "baseline": threshold == baseline_distance,
        })

    def classification_counts(common: float, optional: float) -> tuple[Counter[str], list[dict[str, Any]]]:
        total: Counter[str] = Counter()
        clause_counts = []
        for core in cores.get("functional_cores", []):
            by_key: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
            for row in core.get("component_matrix", []):
                by_key[str(row["feature_key"])].append(row)
            core_counts: Counter[str] = Counter()
            for rows in by_key.values():
                max_frequency = max(float(row["frequency"]) for row in rows)
                distinct = len(rows)
                for row in rows:
                    frequency = float(row["frequency"])
                    count = int(row["count"])
                    member_count = int(core.get("member_count", 0))
                    if distinct == 1 and count == member_count:
                        label = "INVARIANT"
                    elif distinct > 1 and max_frequency < common:
                        label = "CONTRADICTORY"
                    elif frequency >= common:
                        label = "COMMON"
                    elif frequency >= optional:
                        label = "OPTIONAL"
                    else:
                        label = "RARE"
                    core_counts[label] += 1
                    total[label] += 1
            clause_counts.append({
                "functional_core_id": core.get("functional_core_id"),
                "compilable_clause_count": core_counts.get("INVARIANT", 0) + core_counts.get("COMMON", 0),
                "classification_counts": dict(sorted(core_counts.items())),
            })
        return total, clause_counts

    baseline_common = float(method.get("common_component_frequency", 0.75))
    baseline_optional = float(method.get("optional_component_frequency", 0.25))
    threshold_pairs = sorted({
        (baseline_common, baseline_optional),
        (0.60, min(baseline_optional, 0.25)),
        (0.90, min(baseline_optional, 0.25)),
        (baseline_common, 0.10),
        (baseline_common, min(0.40, baseline_common)),
    })
    component_surface = []
    for common, optional in threshold_pairs:
        totals, clauses = classification_counts(common, optional)
        component_surface.append({
            "common_component_frequency": common,
            "optional_component_frequency": optional,
            "aggregate_classification_counts": dict(sorted(totals.items())),
            "core_clause_counts": clauses,
            "surface_sha256": sha_value(clauses),
            "baseline": common == baseline_common and optional == baseline_optional,
        })
    return {
        "support_threshold_surface": support_surface,
        "family_distance_surface": distance_surface,
        "component_frequency_surface": component_surface,
        "selection_effect": "NONE",
        "candidate_promotion_effect": "NONE",
    }


def _legacy_surface(
    legacy_manifest: Path | None,
    match_sets: Mapping[str, set[str]],
) -> dict[str, Any]:
    allowed = ["REDISCOVERED", "SPLIT", "MERGED", "PARTIALLY_RECOVERED", "NOT_RECOVERED", "CONTRADICTED"]
    if legacy_manifest is None:
        return {
            "status": "DEFERRED_NO_LAWFUL_LEGACY_MATCH_POPULATION",
            "manifest": None,
            "mappings": [
                {
                    "benchmark_id": "LEGACY.C2.ACTIVE_DISCOVERY.RELEASE.v2",
                    "source_identity": "OPT-B.C2.GBPUSD.DISCOVERY.2021_2023.v2",
                    "comparison_status": "NOT_EVALUABLE_NO_VNEXT_OPPORTUNITY_ID_CROSSWALK",
                    "operator_decision": None,
                    "recommended_gate_decision": "DEFER",
                    "allowed_mapping_dispositions": allowed,
                },
                {
                    "benchmark_id": "LEGACY.PATTERN_DISCOVERY.CANDIDATE_WINDOW.v0.1",
                    "source_identity": "candidate_window_v0_1",
                    "comparison_status": "NOT_EVALUABLE_NO_VNEXT_OPPORTUNITY_ID_CROSSWALK",
                    "operator_decision": None,
                    "recommended_gate_decision": "DEFER",
                    "allowed_mapping_dispositions": allowed,
                },
            ],
            "legacy_seed_count": 0,
            "legacy_filter_count": 0,
            "legacy_score_count": 0,
            "legacy_stop_count": 0,
            "legacy_promotion_count": 0,
        }
    manifest = read_json(legacy_manifest)
    benchmarks = manifest.get("benchmarks")
    _require(isinstance(benchmarks, list), "LEGACY_BENCHMARKS_REQUIRED")
    mappings = []
    for benchmark in sorted(benchmarks, key=lambda item: str(item.get("legacy_rule_id"))):
        _require(benchmark.get("benchmark_only") is True, "LEGACY_BENCHMARK_ONLY_REQUIRED")
        legacy_set = {str(item) for item in benchmark.get("matched_opportunity_ids", [])}
        comparisons = []
        for candidate_id in sorted(match_sets):
            candidate_set = match_sets[candidate_id]
            comparisons.append({
                "rule_candidate_id": candidate_id,
                "legacy_match_count": len(legacy_set),
                "candidate_match_count": len(candidate_set),
                "intersection_count": len(legacy_set & candidate_set),
                "jaccard_similarity": _jaccard(legacy_set, candidate_set),
                "legacy_only_count": len(legacy_set - candidate_set),
                "candidate_only_count": len(candidate_set - legacy_set),
            })
        mappings.append({
            "benchmark_id": str(benchmark["legacy_rule_id"]),
            "comparison_status": "COMPUTABLE",
            "comparisons": comparisons,
            "operator_decision": None,
            "recommended_gate_decision": None,
            "allowed_mapping_dispositions": allowed,
        })
    return {
        "status": "COMPUTABLE",
        "manifest": legacy_manifest.as_posix(),
        "manifest_sha256": sha_file(legacy_manifest),
        "mappings": mappings,
        "legacy_seed_count": 0,
        "legacy_filter_count": 0,
        "legacy_score_count": 0,
        "legacy_stop_count": 0,
        "legacy_promotion_count": 0,
    }


def build_disposition_evidence(
    replay_root: Path,
    repository_root: Path,
    *,
    legacy_benchmark_manifest: Path | None = None,
) -> dict[str, Any]:
    verified = verify_replay_root(replay_root)
    baseline = verified["baseline_manifest"]
    repository_root = repository_root.resolve()
    registry_path = repository_root / "registries/opt_b/c2/vnext/C2_FUNCTIONAL_DISCOVERY_METHOD_CANDIDATE_v0_1.jsonc"
    registry = read_json(registry_path)
    method = registry.get("method_pack")
    _require(isinstance(method, dict), "METHOD_PACK_REQUIRED")
    _require(method.get("active") is False and method.get("canonical") is False, "METHOD_PACK_AUTHORITY_DRIFT")
    evidence_root = replay_root.resolve() / "run-001" / "evidence"
    population_index, population_summary = _opportunity_index(evidence_root / "opportunity-population.jsonl")
    _require(population_summary["record_count"] == baseline.get("counts", {}).get("records"), "POPULATION_MANIFEST_COUNT_MISMATCH")
    candidates = list(iter_jsonl(evidence_root / "rule-candidates.jsonl"))
    cores = read_json(evidence_root / "functional-cores.json")
    families = read_json(evidence_root / "families.json")
    motifs = read_json(evidence_root / "motifs.json")
    _require(len(candidates) == baseline.get("counts", {}).get("rule_candidates"), "CANDIDATE_MANIFEST_COUNT_MISMATCH")
    controls = _control_summaries(evidence_root / "matched-controls.jsonl", candidates)
    candidate_summaries, match_sets = _candidate_summaries(
        evidence_root / "rule-evaluations.jsonl", candidates, cores, families,
        controls, population_index,
    )
    redundancy = _redundancy_surface(match_sets)
    parameter = _parameter_surface(motifs, cores, method)
    legacy = _legacy_surface(legacy_benchmark_manifest, match_sets)
    warnings = []
    if legacy["status"] != "COMPUTABLE":
        warnings.append("LEGACY_BENCHMARK_COMPARISON_DEFERRED_NO_LAWFUL_OPPORTUNITY_CROSSWALK")
    result: dict[str, Any] = {
        "schema": SCHEMA,
        "programme_id": "OVC-C2-ANATOMY-REDESIGN-v0.2",
        "plan_id": "OVC-C2-ANATOMY-REDESIGN-IMPLEMENTATION",
        "plan_version": "0.3-REVISED",
        "packet_id": "C2AR-WP10-DISPOSITION-EVIDENCE",
        "gate_id": "CEAR-G10",
        "status": "GATE_READY_OPERATOR_DISPOSITIONS_REQUIRED",
        "analysis_code_commit": git_head(repository_root),
        "replay_binding": {
            "binding_id": baseline.get("binding_id"),
            "binding_sha256": baseline.get("binding_sha256"),
            "code_commit": baseline.get("code_commit"),
            "logical_population_sha256": baseline.get("logical_population_sha256"),
            "run_manifest_sha256": {
                name: sha_file(replay_root.resolve() / name / "output-manifest.json")
                for name in RUN_DIRS
            },
            "terminal_receipt_sha256": {
                name: sha_file(replay_root.resolve() / name)
                for name in TERMINAL_RECEIPTS
            },
        },
        "population": population_summary,
        "manifest_counts": baseline.get("counts"),
        "method_pack": {
            "method_pack_id": method.get("method_pack_id"),
            "version": method.get("version"),
            "registry_path": registry_path.relative_to(repository_root).as_posix(),
            "registry_sha256": sha_file(registry_path),
            "operator_decision": None,
            "allowed_gate_decisions": ["PASS", "DEFER", "BLOCK", "QUARANTINE", "SUPERSEDE"],
        },
        "rule_candidates": candidate_summaries,
        "functional_candidate_count": len(cores.get("functional_cores", [])),
        "rule_candidate_count": len(candidate_summaries),
        "redundancy_and_cooccurrence_surface": redundancy,
        "parameter_and_perturbation_surface": parameter,
        "legacy_benchmark_surface": legacy,
        "acceptance_conditions": {
            "complete_population_and_denominators": "PASS",
            "lineage_controls_counterexamples_stability": "PASS_EVIDENCE_SURFACE_READY_FOR_OPERATOR",
            "all_disposition_slots_present": "PASS_WITH_LEGACY_MAPPING_DEFER_RECOMMENDATION" if warnings else "PASS",
            "authority_separation": "PASS",
        },
        "qa_recommendation": "GATE_READY_OPERATOR_DECISION",
        "recommended_gate_decision": "DEFER_LEGACY_BENCHMARK_MAPPINGS_AND_DECIDE_METHOD_AND_RESEARCH_CANDIDATES_INDEPENDENTLY" if warnings else "OPERATOR_DECISION_REQUIRED",
        "warnings": warnings,
        "unresolved_issues": ["CEAR-G10-LEGACY-BENCHMARK-CROSSWALK-001"] if warnings else [],
        "authority": dict(DENIED),
        "active": False,
        "canonical": False,
        "created_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "rollback": "Delete or supersede this compact evidence record. Preserve all external replay bytes and keep PR 319 unmerged until operator disposition.",
    }
    result["content_sha256"] = sha_value({key: value for key, value in result.items() if key not in {"created_at_utc", "content_sha256"}})
    return result


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    root.add_argument("--replay-root", required=True, type=Path)
    root.add_argument("--repository-root", default=Path.cwd(), type=Path)
    root.add_argument("--output", required=True, type=Path)
    root.add_argument("--legacy-benchmark-manifest", type=Path)
    return root


def main(argv: Sequence[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        evidence = build_disposition_evidence(
            args.replay_root,
            args.repository_root,
            legacy_benchmark_manifest=args.legacy_benchmark_manifest,
        )
        write_json(args.output, evidence)
        print(json.dumps({
            "status": evidence["status"],
            "content_sha256": evidence["content_sha256"],
            "rule_candidate_count": evidence["rule_candidate_count"],
            "legacy_benchmark_status": evidence["legacy_benchmark_surface"]["status"],
            "output": args.output.resolve().as_posix(),
        }, sort_keys=True))
    except DispositionEvidenceError as exc:
        print(f"C2AR_WP10_DISPOSITION_EVIDENCE_FAILED:{exc}", file=__import__("sys").stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
