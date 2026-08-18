from __future__ import annotations

"""Read-only aggregate reanalysis for C2P2 scientific discrimination.

This module consumes only the compact R5 court-record result. It does not read
real-source artifacts, rerun a candidate, select an ObjectPack, activate C2P,
or consume Validation. Runtime/storage metrics are retained as descriptive
capacity evidence only and cannot determine scientific selection.
"""

import json
from pathlib import Path
from typing import Any, Mapping

PROGRAMME_ID = "OVC-C2P2-SCIENTIFIC-DISCRIMINATION-v0.1"
R5_RESULT_STATUS = "COMPLETED_COMPARATIVE_SET_NO_WINNER"
EVIDENCE_CONTRACT_ID = "C2P2_RS0_NEGATIVE_COVERAGE_CERTIFICATE_v0_2"
RUNTIME_BINDING_ID = "C2P2_RS0_INDEXED_OUTCOME_EQUIVALENT_RUNTIME_BINDING_v0_3"
POPULATION_COUNT = 1_489_144
CANDIDATE_IDS = {
    "A": "C2P2-PS0-OP-A-STRICT-CONTINUITY-v3",
    "B": "C2P2-PS0-OP-B-RELATIONAL-CONTINUITY-v3",
    "C": "C2P2-PS0-OP-C-EPISODE-ENRICHED-CONTINUITY-v3",
}


class ScientificDiscriminationAggregateError(ValueError):
    pass


def load_json(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def validate_r5_result(result: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    if result.get("status") != R5_RESULT_STATUS:
        raise ScientificDiscriminationAggregateError("SD_R5_STATUS_INVALID")
    if result.get("selection_state") != "COMPARATIVE_SET_ONLY_NO_WINNER":
        raise ScientificDiscriminationAggregateError("SD_R5_SELECTION_STATE_INVALID")
    if result.get("active_object_pack_id") is not None:
        raise ScientificDiscriminationAggregateError("SD_R5_ACTIVE_PACK_FORBIDDEN")
    if result.get("c2p_activation") != "NONE":
        raise ScientificDiscriminationAggregateError("SD_R5_ACTIVATION_FORBIDDEN")

    rows = result.get("candidate_results")
    if not isinstance(rows, list) or len(rows) != 3:
        raise ScientificDiscriminationAggregateError("SD_R5_CANDIDATE_CARDINALITY_INVALID")
    by_id = {str(row.get("candidate_id")): row for row in rows}
    if set(by_id) != set(CANDIDATE_IDS.values()):
        raise ScientificDiscriminationAggregateError("SD_R5_CANDIDATE_SET_INVALID")

    for candidate_id in CANDIDATE_IDS.values():
        row = by_id[candidate_id]
        if row.get("status") != "COMPLETED_SHADOW_UNSELECTED":
            raise ScientificDiscriminationAggregateError("SD_R5_CANDIDATE_NOT_COMPLETE")
        if row.get("selection_state") != "UNSELECTED_RESEARCH_CANDIDATE":
            raise ScientificDiscriminationAggregateError("SD_R5_CANDIDATE_SELECTION_DRIFT")
        if row.get("activation_state") != "NONE":
            raise ScientificDiscriminationAggregateError("SD_R5_CANDIDATE_ACTIVATION_DRIFT")
        if row.get("evidence_contract_id") != EVIDENCE_CONTRACT_ID:
            raise ScientificDiscriminationAggregateError("SD_R5_EVIDENCE_CONTRACT_DRIFT")
        if row.get("runtime_binding_id") != RUNTIME_BINDING_ID:
            raise ScientificDiscriminationAggregateError("SD_R5_RUNTIME_BINDING_DRIFT")
        counts = row.get("scientific_summary", {}).get("counts", {})
        if counts.get("candidates") != POPULATION_COUNT:
            raise ScientificDiscriminationAggregateError("SD_R5_POPULATION_COUNT_DRIFT")
        if counts.get("processed_source_record_ids") != POPULATION_COUNT:
            raise ScientificDiscriminationAggregateError("SD_R5_PROCESSED_COUNT_DRIFT")

    c_summary = by_id[CANDIDATE_IDS["C"]].get("scientific_summary", {})
    if c_summary.get("c2e_dependency_disposition_counts") != {
        "NOT_APPLICABLE_C2_ONLY": 1_489_120
    }:
        raise ScientificDiscriminationAggregateError("SD_C_C2E_FIREWALL_EVIDENCE_DRIFT")
    return by_id


def _metric(row: Mapping[str, Any]) -> dict[str, Any]:
    summary = row["scientific_summary"]
    counts = summary["counts"]
    decisions = summary["decision_terminal_counts"]
    return {
        "object_assertions": int(counts["object_assertions"]),
        "tracklets": int(counts["tracklets"]),
        "evaluated_pair_vectors": int(counts["evaluated_pair_vectors"]),
        "genesis": int(decisions.get("GENESIS", 0)),
        "new_tracklet": int(decisions.get("NEW_TRACKLET", 0)),
        "tracklet_update": int(decisions.get("TRACKLET_UPDATE", 0)),
        "update": int(decisions.get("UPDATE", 0)),
        "objects_per_100k_source_records": int(counts["object_assertions"]) / POPULATION_COUNT * 100_000,
        "update_fraction": int(decisions.get("UPDATE", 0)) / POPULATION_COUNT,
        "indexed_database_bytes": int(row["indexed_database_bytes"]),
        "peak_rss_bytes": int(row["peak_rss_bytes"]),
        "wall_seconds": float(row["wall_seconds"]),
    }


def aggregate_reanalysis(result: Mapping[str, Any]) -> dict[str, Any]:
    by_id = validate_r5_result(result)
    metrics = {letter: _metric(by_id[candidate_id]) for letter, candidate_id in CANDIDATE_IDS.items()}

    def comparison(left: str, right: str) -> dict[str, Any]:
        l = metrics[left]
        r = metrics[right]
        return {
            "left": left,
            "right": right,
            "object_assertion_delta": l["object_assertions"] - r["object_assertions"],
            "object_assertion_ratio": l["object_assertions"] / r["object_assertions"],
            "tracklet_delta": l["tracklets"] - r["tracklets"],
            "update_delta": l["update"] - r["update"],
            "scientific_disposition": "DESCRIPTIVE_CONTRADICTION_SIGNAL_ONLY_NOT_SELECTION_EVIDENCE",
        }

    return {
        "schema": "ovc-c2p2-scientific-discrimination-r5-aggregate-reanalysis/v1",
        "programme_id": PROGRAMME_ID,
        "packet_id": "C2P2-SD-WP2",
        "source": "R5_COMPACT_COURT_RECORD_ONLY_NO_REAL_SOURCE_READ",
        "population_count_per_candidate": POPULATION_COUNT,
        "candidate_metrics": metrics,
        "pairwise": [comparison("A", "B"), comparison("A", "C"), comparison("B", "C")],
        "stratum_plan": {
            "years": [2021, 2022, 2023],
            "sides": ["BID", "ASK"],
            "clocks": ["15M", "2H_A_L"],
            "dynamic_dimensions": ["structural_role_id", "geometry_kind_id"],
            "sampling": "FORBIDDEN",
            "current_status": "PLAN_ONLY_R5_COMPACT_RESULT_HAS_NO_FULL_STRATUM_LEDGER",
        },
        "c_episode_enrichment_firewall": {
            "episode_relative_role_count": 0,
            "r5_observed_disposition": "NOT_APPLICABLE_C2_ONLY",
            "scientific_value_claim": "NOT_EVALUATED",
            "selection_justification": "FORBIDDEN",
        },
        "selection": {
            "recommended_candidate": None,
            "reason": "AGGREGATE_OBJECT_COUNTS_AND_COMPRESSION_CANNOT_DISCRIMINATE_FALSE_FRAGMENTATION_FROM_FALSE_CONTINUITY",
            "next_required_evidence": "FULL_DISAGREEMENT_AND_HARD_BREAK_LEDGER_PLUS_BLINDED_ADJUDICATION",
        },
        "authority_effect": "NONE_READ_ONLY_REANALYSIS",
    }
