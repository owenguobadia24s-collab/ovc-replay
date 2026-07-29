from __future__ import annotations

from typing import Any, Mapping, Sequence

from ovc.research_operations.canonical import canonical_sha256

from .distance import DOMAIN_WEIGHTS, DistancePack, build_scale_pack, composite_distance
from .fingerprints import partition_key
from .models import parse_utc


PACKET_ID = "C1C-G5-CORR3"
RETURN_GATE = "C1C-G5-CORRECTIVE-PILOT-REVIEW"
TARGET_CANDIDATE_ID = "PDPILOT-CANDIDATE-bab63b935155e4d9033aed81"
TARGET_FINDING_CODE = "PD-DEFER-CORR2-STRUCTURAL-COMPARISON-INCOMPLETE-001"
PERSISTENCE_TRIGGER_ID = "TR-PER-001"
PERSISTENCE_REASON_CODE = "LONG_PERSISTENCE"
PERSISTENCE_THRESHOLD_RECORDS = 4


class Corr3EvidenceError(ValueError):
    pass


def _candidate_id(value: Mapping[str, Any]) -> str:
    return str(value.get("window_id") or value.get("candidate_id") or value.get("candidate_window_id") or "")


def _unique_map(values: Sequence[Mapping[str, Any]], key_name: str, *, code: str) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for source in values:
        key = str(source.get(key_name) or "")
        if not key:
            raise Corr3EvidenceError(f"{code}_IDENTITY_MISSING")
        if key in result:
            raise Corr3EvidenceError(f"{code}_DUPLICATE:{key}")
        result[key] = dict(source)
    return result


def exact_corr3_references(candidate_window_id: str = TARGET_CANDIDATE_ID) -> tuple[str, ...]:
    if candidate_window_id != TARGET_CANDIDATE_ID:
        raise Corr3EvidenceError(f"CORR3_UNAUTHORISED_CANDIDATE:{candidate_window_id}")
    return (
        f"derived/candidates.jsonl#window_id={candidate_window_id}",
        f"derived/fingerprints.jsonl#candidate_window_id={candidate_window_id}",
        "derived/cluster-versions.jsonl#exact_assigned_medoid_and_distance",
        "derived/fingerprints.jsonl#exact_assigned_medoid_fingerprint_id",
        "derived/trigger-events.jsonl#trigger_id=TR-PER-001",
        "src/ovc/research_operations/pattern_discovery/evaluation.py#evaluate_persistence_trigger",
        "src/ovc/research_operations/pattern_discovery/distance.py#composite_distance",
    )


def validate_exact_corr3_references(references: Sequence[object]) -> list[str]:
    normalized = sorted({str(item).strip() for item in references if str(item).strip()})
    required = set(exact_corr3_references())
    missing = sorted(required - set(normalized))
    if missing:
        raise Corr3EvidenceError(f"CORR3_EXACT_REFERENCES_MISSING:{','.join(missing)}")
    return normalized


def _interval_overlap(left: Mapping[str, Any], right: Mapping[str, Any]) -> bool:
    left_start = parse_utc(str(left.get("window_start_utc")))
    left_end = parse_utc(str(left.get("window_end_utc")))
    right_start = parse_utc(str(right.get("window_start_utc")))
    right_end = parse_utc(str(right.get("window_end_utc")))
    return left_start < right_end and right_start < left_end


def _same_review_scope(left: Mapping[str, Any], right: Mapping[str, Any]) -> bool:
    fields = ("instrument", "price_side", "clock", "scope_id")
    return all(str(left.get(field) or "") == str(right.get(field) or "") for field in fields)


def build_structural_comparison_context(
    *,
    candidates: Sequence[Mapping[str, Any]],
    fingerprints: Sequence[Mapping[str, Any]],
    cluster_versions: Sequence[Mapping[str, Any]],
    trigger_events: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    candidate_rows: dict[str, dict[str, Any]] = {}
    for source in candidates:
        candidate_id = _candidate_id(source)
        if not candidate_id:
            raise Corr3EvidenceError("CORR3_CANDIDATE_IDENTITY_MISSING")
        if candidate_id in candidate_rows:
            raise Corr3EvidenceError(f"CORR3_DUPLICATE_CANDIDATE_ID:{candidate_id}")
        candidate_rows[candidate_id] = dict(source)
    candidate = candidate_rows.get(TARGET_CANDIDATE_ID)
    if candidate is None:
        raise Corr3EvidenceError("CORR3_TARGET_CANDIDATE_MISSING")

    fingerprint_by_id = _unique_map(fingerprints, "fingerprint_id", code="CORR3_FINGERPRINT")
    fingerprint_by_candidate: dict[str, dict[str, Any]] = {}
    for item in fingerprint_by_id.values():
        candidate_id = str(item.get("candidate_window_id") or "")
        if not candidate_id:
            raise Corr3EvidenceError("CORR3_FINGERPRINT_CANDIDATE_ID_MISSING")
        if candidate_id in fingerprint_by_candidate:
            raise Corr3EvidenceError(f"CORR3_DUPLICATE_CANDIDATE_FINGERPRINT:{candidate_id}")
        fingerprint_by_candidate[candidate_id] = item
    fingerprint = fingerprint_by_candidate.get(TARGET_CANDIDATE_ID)
    if fingerprint is None:
        raise Corr3EvidenceError("CORR3_TARGET_FINGERPRINT_MISSING")
    fingerprint_id = str(fingerprint["fingerprint_id"])
    target_partition = partition_key(fingerprint)

    matching_versions = [
        dict(item)
        for item in cluster_versions
        if tuple(str(value) for value in item.get("partition", ())) == target_partition
        and fingerprint_id in item.get("assignments", {})
    ]
    if len(matching_versions) != 1:
        raise Corr3EvidenceError(f"CORR3_EXACT_CLUSTER_VERSION_COUNT:{len(matching_versions)}")
    cluster_version = matching_versions[0]
    if cluster_version.get("build_status") != "PASS":
        raise Corr3EvidenceError("CORR3_CLUSTER_VERSION_NOT_PASS")

    partition_population = [item for item in fingerprint_by_id.values() if partition_key(item) == target_partition]
    expected_set_hash = canonical_sha256(sorted(str(item["fingerprint_id"]) for item in partition_population))
    if cluster_version.get("input_candidate_set_hash") != expected_set_hash:
        raise Corr3EvidenceError("CORR3_CLUSTER_INPUT_SET_HASH_MISMATCH")
    if int(cluster_version.get("input_count") or -1) != len(partition_population):
        raise Corr3EvidenceError("CORR3_CLUSTER_INPUT_COUNT_MISMATCH")

    assigned_medoid_id = str(cluster_version.get("assignments", {}).get(fingerprint_id) or "")
    if not assigned_medoid_id:
        raise Corr3EvidenceError("CORR3_ASSIGNED_MEDOID_MISSING")
    medoid = fingerprint_by_id.get(assigned_medoid_id)
    if medoid is None:
        raise Corr3EvidenceError("CORR3_MEDOID_FINGERPRINT_MISSING")
    if partition_key(medoid) != target_partition:
        raise Corr3EvidenceError("CORR3_MEDOID_PARTITION_MISMATCH")

    cluster_rows = [
        dict(item)
        for item in cluster_version.get("clusters", ())
        if str(item.get("medoid_id") or "") == assigned_medoid_id
    ]
    if len(cluster_rows) != 1:
        raise Corr3EvidenceError(f"CORR3_ASSIGNED_CLUSTER_COUNT:{len(cluster_rows)}")
    cluster = cluster_rows[0]
    if fingerprint_id not in set(str(item) for item in cluster.get("member_ids", ())):
        raise Corr3EvidenceError("CORR3_TARGET_NOT_IN_ASSIGNED_CLUSTER")

    distance_pack = DistancePack()
    scale_pack = build_scale_pack(partition_population)
    if cluster_version.get("distance_pack_id") != distance_pack.pack_id:
        raise Corr3EvidenceError("CORR3_DISTANCE_PACK_ID_MISMATCH")
    if cluster_version.get("scale_pack_id") != scale_pack.scale_id:
        raise Corr3EvidenceError("CORR3_SCALE_PACK_ID_MISMATCH")
    comparison = composite_distance(
        fingerprint,
        medoid,
        scale_pack=scale_pack,
        distance_pack=distance_pack,
    )
    recorded_distance = float(cluster_version.get("distances", {}).get(fingerprint_id))
    if abs(float(comparison["distance"]) - recorded_distance) > 1e-12:
        raise Corr3EvidenceError("CORR3_RECOMPUTED_DISTANCE_MISMATCH")

    components = {
        domain: {
            "raw_distance": value,
            "weight": DOMAIN_WEIGHTS[domain],
            "weighted_contribution": round(DOMAIN_WEIGHTS[domain] * value, 12),
        }
        for domain, value in sorted(comparison["domains"].items())
    }
    contribution_total = round(sum(item["weighted_contribution"] for item in components.values()), 12)
    if abs(contribution_total - recorded_distance) > 1e-12:
        raise Corr3EvidenceError("CORR3_DISTANCE_COMPONENT_SUM_MISMATCH")

    threshold = float(cluster.get("outlier_threshold_p90") or 0.0)
    listed_outlier = fingerprint_id in set(str(item) for item in cluster.get("outlier_ids", ()))
    computed_outlier = recorded_distance > threshold
    if listed_outlier != computed_outlier:
        raise Corr3EvidenceError("CORR3_OUTLIER_CLASSIFICATION_MISMATCH")

    dedup_key = str(candidate.get("candidate_dedup_key") or "")
    same_dedup = sorted(
        candidate_id
        for candidate_id, item in candidate_rows.items()
        if candidate_id != TARGET_CANDIDATE_ID
        and dedup_key
        and str(item.get("candidate_dedup_key") or "") == dedup_key
    )
    exact_window_fields = (
        "instrument",
        "price_side",
        "clock",
        "scope_id",
        "window_start_utc",
        "window_end_utc",
    )
    exact_window_peers = sorted(
        candidate_id
        for candidate_id, item in candidate_rows.items()
        if candidate_id != TARGET_CANDIDATE_ID
        and all(str(item.get(field) or "") == str(candidate.get(field) or "") for field in exact_window_fields)
    )
    overlap_peers = sorted(
        candidate_id
        for candidate_id, item in candidate_rows.items()
        if candidate_id != TARGET_CANDIDATE_ID
        and _same_review_scope(candidate, item)
        and _interval_overlap(candidate, item)
    )

    event_by_id = _unique_map(trigger_events, "trigger_event_id", code="CORR3_TRIGGER_EVENT")
    linked_event_ids = sorted(str(item) for item in candidate.get("trigger_event_ids", ()))
    unresolved_event_ids = sorted(set(linked_event_ids) - set(event_by_id))
    if unresolved_event_ids:
        raise Corr3EvidenceError(f"CORR3_TRIGGER_EVENT_UNRESOLVED:{','.join(unresolved_event_ids)}")
    persistence_events = [
        event_by_id[event_id]
        for event_id in linked_event_ids
        if event_by_id[event_id].get("trigger_id") == PERSISTENCE_TRIGGER_ID
        or event_by_id[event_id].get("reason_code") == PERSISTENCE_REASON_CODE
    ]
    if len(persistence_events) != 1:
        raise Corr3EvidenceError(f"CORR3_LONG_PERSISTENCE_EVENT_COUNT:{len(persistence_events)}")
    persistence_event = persistence_events[0]
    if persistence_event.get("trigger_id") != PERSISTENCE_TRIGGER_ID or persistence_event.get("reason_code") != PERSISTENCE_REASON_CODE:
        raise Corr3EvidenceError("CORR3_LONG_PERSISTENCE_EVENT_MISMATCH")

    duration = fingerprint.get("duration_persistence", {})
    return {
        "schema": "ovc-c1c-g5-corr3-structural-comparison-context/v1",
        "packet_id": PACKET_ID,
        "return_gate": RETURN_GATE,
        "candidate_window_id": TARGET_CANDIDATE_ID,
        "prior_finding_code": TARGET_FINDING_CODE,
        "exact_evidence_references": list(exact_corr3_references()),
        "candidate_identity": {
            "candidate_record_count": 1,
            "fingerprint_record_count": 1,
            "candidate_dedup_key": dedup_key or None,
            "same_dedup_key_candidate_ids": same_dedup,
            "dedup_status": "UNIQUE_DEDUP_KEY" if not same_dedup else "SHARED_DEDUP_KEY",
            "exact_window_peer_ids": exact_window_peers,
            "exact_window_status": "UNIQUE_EXACT_WINDOW" if not exact_window_peers else "DUPLICATE_EXACT_WINDOW",
        },
        "overlap_status": {
            "comparison_scope": ["instrument", "price_side", "clock", "scope_id"],
            "overlapping_candidate_ids": overlap_peers,
            "status": "NO_OVERLAP" if not overlap_peers else "OVERLAP_PRESENT",
        },
        "comparison_availability": {
            "status": "EXACT_ASSIGNED_MEDOID_AVAILABLE",
            "cluster_version_id": cluster_version.get("cluster_version_id"),
            "cluster_id": cluster.get("cluster_id"),
            "target_fingerprint_id": fingerprint_id,
            "assigned_medoid_fingerprint_id": assigned_medoid_id,
            "partition": list(target_partition),
            "partition_input_count": len(partition_population),
            "distance_pack_id": comparison["distance_pack_id"],
            "scale_pack_id": comparison["scale_pack_id"],
        },
        "distance_comparison": {
            "recorded_distance": recorded_distance,
            "recomputed_distance": comparison["distance"],
            "components": components,
            "weighted_component_total": contribution_total,
            "outlier_threshold_p90": threshold,
            "listed_as_outlier": listed_outlier,
            "computed_as_outlier": computed_outlier,
            "outlier_status": "OUTLIER" if computed_outlier else "WITHIN_CLUSTER_P90",
        },
        "target_fingerprint": dict(fingerprint),
        "assigned_medoid_fingerprint": dict(medoid),
        "long_persistence_derivation": {
            "trigger_event_id": persistence_event.get("trigger_event_id"),
            "trigger_id": persistence_event.get("trigger_id"),
            "reason_code": persistence_event.get("reason_code"),
            "first_valid_at": persistence_event.get("first_valid_at"),
            "source_transition_ids": list(persistence_event.get("source_transition_ids", ())),
            "evaluator_rule": "evaluate_persistence_trigger fires on the first closed record where the trailing equal-state run reaches the frozen threshold.",
            "frozen_threshold_records": PERSISTENCE_THRESHOLD_RECORDS,
            "trigger_history_scope": "PRE_WINDOW_C2_HISTORY_THROUGH_TRIGGER_FIRST_VALID_AT",
            "candidate_window_scope": "POST_TRIGGER_WINDOW_BEGINNING_AT_TRIGGER_FIRST_VALID_AT",
            "candidate_fingerprint_duration_records": duration.get("duration_records"),
            "candidate_fingerprint_max_persistence": duration.get("max_persistence"),
            "reconciliation": "Trigger persistence is evaluated from pre-window C2 history; fingerprint duration describes the candidate window after it opens. The two counts are different scopes and are not required to match.",
            "trigger_rule_changed": False,
        },
        "authority": {
            "surface": "READ_ONLY_STRUCTURAL_COMPARISON",
            "machine_replay": "DENIED_NOT_REQUIRED",
            "distance_pack_change": "NONE",
            "clustering_change": "NONE",
            "threshold_or_model_change": "NONE",
            "canonical_append": "DENIED",
            "promotion_eligibility": "NON_PROMOTABLE",
            "selector_mutation": "DENIED",
            "release_mutation": "DENIED",
        },
    }
