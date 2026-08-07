"""MG-WP9 deterministic read-only market-grammar review model.

The derived model makes MG-WP7/WP8 evidence inspectable. It has no mutation,
selector, promotion, canonicalisation, publication, C3, Validation or exposure authority.
"""
from __future__ import annotations

from hashlib import sha256
import json
from typing import Mapping, Sequence

from .topology_smoke import run_topology_smoke

SCHEMA = "ovc-mg-wp9-review-model/v1"
AUTHORITY = "INACTIVE_NONCANONICAL_SHADOW_EXPERIMENT_READ_ONLY_REVIEW"


def _canon(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _hash(value: object) -> str:
    return sha256(_canon(value).encode("utf-8")).hexdigest()


def _candidate_records(records: Sequence[Mapping[str, object]]) -> list[dict[str, object]]:
    values = [dict(item) for item in records]
    values.sort(key=lambda item: str(item.get("rule_candidate_id", "")))
    if len(values) != 14 or len({str(item.get("rule_candidate_id")) for item in values}) != 14:
        raise ValueError("WP9 requires exactly fourteen unique candidate migration records")
    for item in values:
        if item.get("migration_status") not in {"MAPPED", "SUPERSEDED", "QUARANTINED", "UNRESOLVED"}:
            raise ValueError("unsupported candidate migration status")
        evaluation = dict(item.get("evaluation", {}))
        if not evaluation.get("counterexample_set_sha256"):
            raise ValueError("candidate migration must retain counterexample identity")
    return values


def build_review_model(
    fixture: Mapping[str, object],
    sensitivity_registry: Mapping[str, object],
    migration_ledger: Mapping[str, object],
    candidate_records: Sequence[Mapping[str, object]],
) -> dict[str, object]:
    smoke = run_topology_smoke(fixture, sensitivity_registry, migration_ledger)
    candidates = _candidate_records(candidate_records)
    if smoke.get("canonical") is not False or smoke.get("published") is not False:
        raise ValueError("WP9 cannot review canonical or published smoke output")
    if smoke.get("read_only_projection", {}).get("mutation_controls") is not False:
        raise ValueError("WP9 source projection must remain read-only")
    if migration_ledger.get("canonical") is not False or migration_ledger.get("promotion_authority") != "NONE":
        raise ValueError("WP9 migration source may not carry promotion authority")

    sensitivity = dict(smoke["sensitivity_comparison"])
    hierarchy = dict(sensitivity.get("hierarchy", {}))
    variant_ledger = dict(sensitivity.get("episode_variant_ledger", {}))
    grammar = dict(smoke["grammar_release"])
    parse_result = dict(smoke["parse_result"])

    counterexamples = []
    for item in candidates:
        evaluation = dict(item["evaluation"])
        counterexamples.append({
            "counterexample_id": "MG.WP9.CEX." + _hash({"rule_candidate_id":item["rule_candidate_id"],"counterexample_set_sha256":evaluation["counterexample_set_sha256"]})[:24],
            "source": "CEAR_G10_CANDIDATE_MIGRATION",
            "rule_candidate_id": item["rule_candidate_id"],
            "migration_status": item["migration_status"],
            "counterexample_count": int(evaluation.get("counterexample_count", 0)),
            "counterexample_set_sha256": evaluation["counterexample_set_sha256"],
            "match_set_sha256": evaluation.get("match_set_sha256"),
            "read_only": True,
        })
    for item in variant_ledger.get("counterexamples", []):
        counterexamples.append({
            "counterexample_id": str(item.get("counterexample_id", item.get("record_id", ""))),
            "source": "C2G_FAMILY_VARIANT",
            "record_id": item.get("record_id"),
            "family_id": item.get("family_id"),
            "nearest_variant_id": item.get("nearest_variant_id"),
            "nearest_variant_distance": item.get("nearest_variant_distance"),
            "reason": item.get("reason"),
            "read_only": True,
        })
    counterexamples.sort(key=lambda item: (str(item.get("source")), str(item.get("rule_candidate_id", item.get("record_id", "")))))

    issues = [
        {
            "issue_id": "MG.WP9.ISSUE.REVISED_C2_SYNTHETIC_BOUNDARY",
            "severity": "WARNING",
            "blocking": False,
            "status": "OPEN_KNOWN_LIMITATION",
            "evidence": "REVISED_C2_ACCEPTED_RECORD_SURFACE",
            "authority_effect": "NONE",
        },
        {
            "issue_id": "MG.WP9.ISSUE.C2G_PROJECTION_ADAPTER",
            "severity": "WARNING",
            "blocking": False,
            "status": "OPEN_KNOWN_LIMITATION",
            "evidence": "C2_TO_C2G_STRUCTURAL_PROJECTION_ADAPTER",
            "authority_effect": "NONE",
        },
        {
            "issue_id": "MG.WP9.ISSUE.TYPED_EMPIRICAL_PARITY_NOT_EVALUATED",
            "severity": "WARNING",
            "blocking": False,
            "status": "DEFERRED_BY_WP7_CONTRACT",
            "evidence": migration_ledger.get("migration_policy", {}).get("exact_empirical_parity"),
            "authority_effect": "NONE",
        },
    ]
    for item in candidates:
        if item["migration_status"] != "MAPPED":
            issues.append({
                "issue_id": "MG.WP9.ISSUE.CANDIDATE." + str(item["rule_candidate_id"]).split(".")[-1],
                "severity": "WARNING",
                "blocking": False,
                "status": str(item["migration_status"]),
                "evidence": item["source_clause_inventory_sha256"],
                "authority_effect": "NONE",
            })
    issues.sort(key=lambda item: item["issue_id"])

    candidate_view = []
    for item in candidates:
        evaluation = dict(item["evaluation"])
        candidate_view.append({
            "rule_candidate_id": item["rule_candidate_id"],
            "functional_core_id": item["functional_core_id"],
            "family_id": item["family_id"],
            "migration_id": item["migration_id"],
            "migration_status": item["migration_status"],
            "source_rule_content_sha256": item["source_rule_content_sha256"],
            "source_clause_inventory_sha256": item["source_clause_inventory_sha256"],
            "typed_mapping_sha256": item["typed_mapping_sha256"],
            "domain_counts": item["domain_counts"],
            "typed_layer_counts": item["typed_layer_counts"],
            "matched_count": evaluation.get("matched_count"),
            "match_set_sha256": evaluation.get("match_set_sha256"),
            "counterexample_count": evaluation.get("counterexample_count"),
            "counterexample_set_sha256": evaluation.get("counterexample_set_sha256"),
            "promotion_authority": "NONE",
            "read_only": True,
        })

    model = {
        "schema": SCHEMA,
        "programme_id": "OVC-C2E-C2G-C2P-MARKET-GRAMMAR-REMEDIATION-v0.1",
        "packet_id": "MG-WP9",
        "authority": AUTHORITY,
        "canonical": False,
        "mutation_controls": False,
        "input_sha256": _hash({
            "smoke_result_sha256": smoke["result_sha256"],
            "migration_ledger_sha256": migration_ledger["ledger_sha256"],
            "candidate_record_hashes": [_hash(item) for item in candidates],
        }),
        "source_bindings": {
            "wp8_smoke_result_sha256": smoke["result_sha256"],
            "wp8_input_sha256": smoke["input_sha256"],
            "wp7_migration_ledger_sha256": migration_ledger["ledger_sha256"],
            "candidate_record_count": 14,
            "source_authority": "RAW_RECORDS_REMAIN_AUTHORITATIVE",
            "derived_index_replaceable": True,
        },
        "sensitivity_comparison": {
            "mode": "READ_ONLY",
            "pack_ids": sensitivity.get("pack_ids", []),
            "canonical_pack_id": sensitivity.get("canonical_pack_id"),
            "adjacent_metrics": hierarchy.get("adjacent_metrics", []),
            "split_events": hierarchy.get("split_events", []),
            "merge_events": hierarchy.get("merge_events", []),
        },
        "family_graph": {
            "mode": "READ_ONLY",
            "hierarchy_id": hierarchy.get("hierarchy_id"),
            "edges": hierarchy.get("edges", []),
            "split_events": hierarchy.get("split_events", []),
            "merge_events": hierarchy.get("merge_events", []),
            "canonical_family_id": None,
        },
        "medoid_variant_stability": {
            "mode": "READ_ONLY",
            "adjacent_metrics": hierarchy.get("adjacent_metrics", []),
            "variants": variant_ledger.get("variants", []),
            "canonical_variant_id": None,
        },
        "assignment_explanations": {
            "mode": "READ_ONLY",
            "variant_explanations": variant_ledger.get("explanations", []),
            "parser_nearest_family_id": parse_result.get("nearest_family_id"),
            "parser_nearest_variant_id": parse_result.get("nearest_variant_id"),
            "family_distance": parse_result.get("family_distance"),
            "variant_distance": parse_result.get("variant_distance"),
        },
        "grammar_review": {
            "mode": "READ_ONLY",
            "grammar_release_id": grammar.get("grammar_release_id"),
            "release_sha256": grammar.get("release_sha256"),
            "canonical": grammar.get("canonical"),
            "published": grammar.get("published"),
            "layers": grammar.get("layers"),
            "invalidating_conditions": grammar.get("invalidating_conditions"),
            "parse_status": parse_result.get("status"),
            "parse_id": parse_result.get("parse_id"),
            "current_phases": parse_result.get("current_phases"),
            "completed_phases": parse_result.get("completed_phases"),
            "lawful_next_phases": parse_result.get("lawful_next_phases"),
            "missing_evidence": parse_result.get("missing_evidence"),
            "conflicting_evidence": parse_result.get("conflicting_evidence"),
            "invalidation_reasons": parse_result.get("invalidation_reasons"),
            "upstream_lineage": parse_result.get("upstream_lineage"),
        },
        "context_review": {
            "mode": "READ_ONLY",
            "profile": {"evaluation_clock":"15M","context_clock":"2H_A_L","relationship":"PARENT_CONTEXT"},
            "status_counts": smoke.get("context_status_counts"),
            "explicit_missing_context": smoke.get("missing_context_resolution"),
            "missing_context_neutralised": False,
        },
        "candidate_migration": {
            "mode": "READ_ONLY",
            "candidate_count": 14,
            "migration_status_counts": migration_ledger["migration_status_counts"],
            "promotion_authority": "NONE",
            "candidates": candidate_view,
        },
        "counterexample_ledger": counterexamples,
        "issue_ledger": issues,
        "provenance_policy": {
            "structural_match_feature": False,
            "diagnostic_only": True,
            "structural_assignment_sha256": smoke["provenance_ablation"]["structural_assignment_sha256"],
            "provenance_inclusive_diagnostic_sha256": smoke["provenance_ablation"]["provenance_inclusive_diagnostic_sha256"],
        },
    }
    model["result_sha256"] = _hash(model)
    return model
