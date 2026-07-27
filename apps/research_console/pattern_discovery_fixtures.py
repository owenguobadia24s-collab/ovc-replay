from __future__ import annotations

from ovc.research_operations.pattern_discovery.review import (
    build_candidate_detail,
    build_cluster_view,
    build_review_queue_item,
)


def pattern_discovery_fixture_bundle() -> dict:
    candidate = {
        "window_id": "PDW-UI-FIX-001",
        "status": "READY_FOR_REVIEW",
        "operation_mode": "LIVE_PROSPECTIVE",
        "instrument": "GBPUSD",
        "clock": "15M",
        "price_side": "BID",
        "scope_id": "GBPUSD-15M-LOCAL-v0.1",
        "window_start_utc": "2026-07-27T08:00:00Z",
        "trigger_first_valid_at": "2026-07-27T08:15:00Z",
        "window_end_utc": "2026-07-27T09:00:00Z",
        "represented_c2_time": "2026-07-27T09:00:00Z",
        "closure_reason": "STABLE_RESOLUTION",
        "primary_trigger_reason": "BOUNDARY_ZONE_ENTRY",
        "trigger_event_ids": ["PDTE-UI-001"],
        "trigger_snapshot_hash": "fixture-trigger-hash",
        "source_release_id": "OPT-B.C2.GBPUSD.DISCOVERY.2021_2023.v1",
        "source_manifest_id": "MANIFEST-C2-DISCOVERY-v1",
        "opt_a_release_id": "OPT-A.GBPUSD.DISCOVERY.2021_2023.v2",
        "source_c2_record_ids": ["C2S-UI-001", "C2S-UI-002", "C2S-UI-003"],
        "quality_state": "COMPLETE",
        "control_class": "NONE",
        "transition_summary": ["MID_REGION → UPPER_REGION", "APPROACHING → BREACH_ACTIVE"],
        "timeline": [
            {"time": "2026-07-27T08:00:00Z", "location": "MID_REGION", "motion": "UP_PROGRESS", "interaction": "APPROACHING"},
            {"time": "2026-07-27T08:15:00Z", "location": "UPPER_REGION", "motion": "UP_PROGRESS", "interaction": "BREACH_ACTIVE"},
            {"time": "2026-07-27T09:00:00Z", "location": "UPPER_REGION", "motion": "UP_STALL", "interaction": "RETURNED_INSIDE"},
        ],
    }
    fingerprint = {
        "record_type": "PatternFingerprint",
        "fingerprint_id": "PDFP-UI-001",
        "fingerprint_version": "PD.FINGERPRINT.v0.1",
        "candidate_window_id": candidate["window_id"],
        "source_release_id": candidate["source_release_id"],
        "transition_sequence": ["AXIS.LOCATION", "AXIS.INTERACTION", "AXIS.MOTION"],
        "partition": {
            "clock": "15M",
            "price_side": "BID",
            "primary_transition_grammar": "BOUNDARY_TEST",
            "boundary_interaction_class": "BREACH_RETURN",
            "parent_containment_class": "CONTAINED",
            "closure_class": "STABLE_RESOLUTION",
        },
    }
    cluster_version = {
        "record_type": "ClusterVersion",
        "cluster_version_id": "PDCV-UI-001",
        "build_status": "PASS",
        "partition": ["15M", "BID", "BOUNDARY_TEST", "BREACH_RETURN", "CONTAINED", "STABLE_RESOLUTION"],
        "input_count": 6,
        "selected_k": 1,
        "assignments": {fingerprint["fingerprint_id"]: fingerprint["fingerprint_id"]},
        "distances": {fingerprint["fingerprint_id"]: 0.0},
        "clusters": [{
            "cluster_id": "PDCL-UI-001",
            "status": "RECURRING",
            "member_count": 6,
            "medoid_id": fingerprint["fingerprint_id"],
            "member_ids": [fingerprint["fingerprint_id"]],
            "dispersion": 0.12,
            "outlier_ids": [],
        }],
    }
    price_strip = {
        "status": "AVAILABLE",
        "source_release_id": candidate["opt_a_release_id"],
        "clock": "15M",
        "bars": [
            {"bar_id": "A-1", "bar_end_utc": "2026-07-27T08:00:00Z", "close": 1.2840},
            {"bar_id": "A-2", "bar_end_utc": "2026-07-27T08:15:00Z", "close": 1.2850},
            {"bar_id": "A-3", "bar_end_utc": "2026-07-27T09:00:00Z", "close": 1.2844},
        ],
        "markers": {
            "window_start_utc": candidate["window_start_utc"],
            "trigger_first_valid_at": candidate["trigger_first_valid_at"],
            "window_end_utc": candidate["window_end_utc"],
            "closure_reason": candidate["closure_reason"],
        },
    }
    novelty = {
        "novelty_state": "BASELINE_FORMING",
        "badge": None,
        "queue_ranking_weight": 0.0,
    }
    queue_item = build_review_queue_item(candidate, fingerprint=fingerprint, cluster_version=cluster_version, novelty=novelty)
    detail = build_candidate_detail(candidate, fingerprint=fingerprint, cluster_version=cluster_version, price_strip=price_strip)
    return {
        "queue_items": [queue_item],
        "candidate_details": {candidate["window_id"]: detail},
        "cluster_view": build_cluster_view(cluster_version),
        "authority": "FIXTURE_ONLY_NO_WRITE",
    }
