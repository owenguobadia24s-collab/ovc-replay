from __future__ import annotations

from typing import Any, Iterable, Mapping

from .market_description_assurance import project_candidate_chronology
from .models import PatternDiscoveryError


EVIDENCE_CLASSES = {
    "STATE_FIDELITY_REVIEW",
    "BOUNDARY_CONFLICT_CASE",
    "ANOMALY",
    "INCIDENT",
    "BOUNDED_RESEARCH_QUESTION",
}


def _candidate_chronology(candidate: Mapping[str, Any]) -> dict[str, Any]:
    timeline = candidate.get("timeline", ())
    if timeline:
        return project_candidate_chronology(candidate)
    return {
        "timeline": [],
        "source_c2_record_ids": [str(item) for item in candidate.get("source_c2_record_ids", ())],
        "original_is_chronological": None,
        "ordering_rule": "FIRST_VALID_TIME_THEN_C2_STATE_ID_WHEN_TIMELINE_AVAILABLE",
        "mutation": "NONE_READ_ONLY_PROJECTION_ONLY",
    }


def build_review_queue_item(
    candidate: Mapping[str, Any],
    *,
    fingerprint: Mapping[str, Any] | None = None,
    cluster_version: Mapping[str, Any] | None = None,
    novelty: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    candidate_id = str(candidate.get("window_id") or candidate.get("candidate_id") or "")
    if not candidate_id:
        raise PatternDiscoveryError("review queue item requires candidate identity")
    if candidate.get("status") not in {"READY_FOR_REVIEW", "DISMISSED", "REVIEWED", "SUPPRESSED_QUEUE_CAP"}:
        raise PatternDiscoveryError("candidate is not reviewable")
    fingerprint_id = fingerprint.get("fingerprint_id") if fingerprint else None
    nearest_cluster = None
    distance = None
    if cluster_version and fingerprint_id:
        assigned = cluster_version.get("assignments", {}).get(fingerprint_id)
        if assigned:
            nearest_cluster = next(
                (item for item in cluster_version.get("clusters", ()) if item.get("medoid_id") == assigned),
                None,
            )
            distance = cluster_version.get("distances", {}).get(fingerprint_id)
    chronology = _candidate_chronology(candidate)
    return {
        "queue_item_id": f"PDQI-{candidate_id}",
        "candidate_window_id": candidate_id,
        "status": str(candidate.get("status")),
        "instrument": str(candidate.get("instrument") or "GBPUSD"),
        "clock": str(candidate.get("clock")),
        "price_side": str(candidate.get("price_side")),
        "window_start_utc": candidate.get("window_start_utc"),
        "window_end_utc": candidate.get("window_end_utc"),
        "trigger_first_valid_at": candidate.get("trigger_first_valid_at"),
        "primary_trigger_reason": candidate.get("primary_trigger_reason") or candidate.get("closure_reason"),
        "transition_summary": list(candidate.get("transition_summary", ())),
        "quality_state": candidate.get("quality_state"),
        "control_class": candidate.get("control_class", "NONE"),
        "fingerprint_id": fingerprint_id,
        "nearest_cluster_id": nearest_cluster.get("cluster_id") if nearest_cluster else None,
        "nearest_cluster_medoid_id": nearest_cluster.get("medoid_id") if nearest_cluster else None,
        "nearest_cluster_distance": distance,
        "novelty_state": novelty.get("novelty_state") if novelty else None,
        "novelty_badge": novelty.get("badge") if novelty else None,
        "source_release_id": candidate.get("source_release_id"),
        "source_manifest_id": candidate.get("source_manifest_id"),
        "source_c2_record_ids": chronology["source_c2_record_ids"],
        "chronology_projection": {
            "original_is_chronological": chronology["original_is_chronological"],
            "ordering_rule": chronology["ordering_rule"],
            "mutation": chronology["mutation"],
        },
        "authority": "READ_ONLY_CANDIDATE",
    }


def build_candidate_detail(
    candidate: Mapping[str, Any],
    *,
    fingerprint: Mapping[str, Any],
    neighbours: Iterable[Mapping[str, Any]] = (),
    cluster_version: Mapping[str, Any] | None = None,
    price_strip: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    chronology = _candidate_chronology(candidate)
    queue_item = build_review_queue_item(candidate, fingerprint=fingerprint, cluster_version=cluster_version)
    source_ids = chronology["source_c2_record_ids"]
    if not source_ids:
        raise PatternDiscoveryError("candidate detail requires immutable C2 source IDs")
    return {
        "summary": queue_item,
        "authority_banner": "PROVISIONAL RESEARCH CASE — NO SEMANTIC, OUTCOME OR EXPOSURE AUTHORITY",
        "trigger_explanation": {
            "first_valid_at": candidate.get("trigger_first_valid_at"),
            "trigger_event_ids": list(candidate.get("trigger_event_ids", ())),
            "trigger_snapshot_hash": candidate.get("trigger_snapshot_hash"),
            "closure_reason": candidate.get("closure_reason"),
        },
        "timeline": chronology["timeline"],
        "chronology_projection": {
            "original_is_chronological": chronology["original_is_chronological"],
            "ordering_rule": chronology["ordering_rule"],
            "mutation": chronology["mutation"],
        },
        "fingerprint": dict(fingerprint),
        "neighbours": [dict(item) for item in neighbours],
        "cluster": dict(cluster_version) if cluster_version else None,
        "price_strip": dict(price_strip) if price_strip else {"status": "NOT_AVAILABLE_SOURCE_UNRESOLVED"},
        "source_lineage": {
            "release_id": candidate.get("source_release_id"),
            "manifest_id": candidate.get("source_manifest_id"),
            "c2_record_ids": source_ids,
            "fingerprint_id": fingerprint.get("fingerprint_id"),
            "fingerprint_version": fingerprint.get("fingerprint_version"),
        },
        "permitted_review_classes": sorted(EVIDENCE_CLASSES),
    }


def build_cluster_view(cluster_version: Mapping[str, Any]) -> dict[str, Any]:
    if cluster_version.get("record_type") != "ClusterVersion":
        raise PatternDiscoveryError("cluster view requires ClusterVersion")
    return {
        "cluster_version_id": cluster_version.get("cluster_version_id"),
        "build_status": cluster_version.get("build_status"),
        "partition": list(cluster_version.get("partition", ())),
        "selected_k": cluster_version.get("selected_k"),
        "clusters": [dict(item) for item in cluster_version.get("clusters", ())],
        "input_count": cluster_version.get("input_count"),
        "authority_banner": "PROVISIONAL CLUSTERS — ARCHETYPE AND SEMANTIC PROMOTION PROHIBITED",
        "permitted_actions": ["FLAG_ASSIGNMENT", "PROPOSE_SPLIT", "PROPOSE_MERGE", "RESTRICT", "REJECT"],
        "prohibited_actions": ["PROMOTE_ARCHETYPE", "MUTATE_C2", "ACTIVATE_SELECTOR"],
    }
