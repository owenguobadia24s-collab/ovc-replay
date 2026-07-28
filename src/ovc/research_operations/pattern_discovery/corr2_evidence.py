from __future__ import annotations

from typing import Any, Mapping, Sequence


PACKET_ID = "C1C-G5-CORR2"
RETURN_GATE = "C1C-G5-CORRECTIVE-PILOT-REVIEW"
DEFERRED_OBJECTS: dict[str, str] = {
    "PDPILOT-CANDIDATE-4f41e21b6cd075e0fdbc40e4": "PD-DEFER-REVIEW-EVIDENCE-INCOMPLETE-001",
    "PDPILOT-CANDIDATE-bab63b935155e4d9033aed81": "PD-DEFER-STRUCTURAL-COMPARISON-PENDING-002",
}


class Corr2EvidenceError(ValueError):
    pass


def exact_evidence_references(candidate_window_id: str) -> tuple[str, ...]:
    candidate_id = str(candidate_window_id or "").strip()
    if not candidate_id.startswith("PDPILOT-CANDIDATE-"):
        raise Corr2EvidenceError(f"INVALID_CORR2_CANDIDATE_ID:{candidate_id}")
    return (
        f"review/queue-items.jsonl#candidate_window_id={candidate_id}",
        f"review/console-bundle.json#candidate_details.{candidate_id}",
        f"derived/fingerprints.jsonl#candidate_window_id={candidate_id}",
        f"review/console-bundle.json#candidate_details.{candidate_id}.source_lineage",
    )


def validate_exact_evidence_references(candidate_window_id: str, references: Sequence[object]) -> list[str]:
    normalized = sorted({str(item).strip() for item in references if str(item).strip()})
    required = set(exact_evidence_references(candidate_window_id))
    missing = sorted(required - set(normalized))
    if missing:
        raise Corr2EvidenceError(
            f"CORR2_EXACT_EVIDENCE_REFERENCES_MISSING:{candidate_window_id}:{','.join(missing)}"
        )
    for reference in normalized:
        if "#candidate_window_id=" in reference and not reference.endswith(str(candidate_window_id)):
            raise Corr2EvidenceError(
                f"CORR2_EVIDENCE_REFERENCE_CANDIDATE_MISMATCH:{candidate_window_id}:{reference}"
            )
        if "#candidate_details." in reference and str(candidate_window_id) not in reference:
            raise Corr2EvidenceError(
                f"CORR2_EVIDENCE_REFERENCE_CANDIDATE_MISMATCH:{candidate_window_id}:{reference}"
            )
    return normalized


def build_exact_evidence_context(
    detail: Mapping[str, Any],
    *,
    queue_item: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    summary = detail.get("summary")
    if not isinstance(summary, Mapping):
        raise Corr2EvidenceError("CORR2_CANDIDATE_DETAIL_SUMMARY_MISSING")
    candidate_id = str(summary.get("candidate_window_id") or "")
    if not candidate_id:
        raise Corr2EvidenceError("CORR2_CANDIDATE_ID_MISSING")
    if queue_item is not None and str(queue_item.get("candidate_window_id") or "") != candidate_id:
        raise Corr2EvidenceError("CORR2_QUEUE_DETAIL_IDENTITY_MISMATCH")

    fingerprint = detail.get("fingerprint")
    if not isinstance(fingerprint, Mapping):
        raise Corr2EvidenceError("CORR2_FINGERPRINT_CONTEXT_MISSING")
    lineage = detail.get("source_lineage")
    if not isinstance(lineage, Mapping):
        raise Corr2EvidenceError("CORR2_SOURCE_LINEAGE_CONTEXT_MISSING")

    fingerprint_candidate_id = str(fingerprint.get("candidate_window_id") or "")
    if fingerprint_candidate_id and fingerprint_candidate_id != candidate_id:
        raise Corr2EvidenceError("CORR2_FINGERPRINT_CANDIDATE_IDENTITY_MISMATCH")

    queue = dict(queue_item or summary)
    required_queue_fields = (
        "candidate_window_id",
        "clock",
        "price_side",
        "trigger_first_valid_at",
        "primary_trigger_reason",
        "fingerprint_id",
    )
    missing_queue = [field for field in required_queue_fields if queue.get(field) in (None, "")]
    if missing_queue:
        raise Corr2EvidenceError(f"CORR2_QUEUE_CONTEXT_INCOMPLETE:{','.join(missing_queue)}")

    queue_fingerprint_id = str(queue.get("fingerprint_id") or "")
    fingerprint_id = str(fingerprint.get("fingerprint_id") or "")
    lineage_fingerprint_id = str(lineage.get("fingerprint_id") or "")
    if not fingerprint_id or queue_fingerprint_id != fingerprint_id or lineage_fingerprint_id != fingerprint_id:
        raise Corr2EvidenceError("CORR2_FINGERPRINT_LINEAGE_IDENTITY_MISMATCH")
    if not lineage.get("release_id") or not lineage.get("manifest_id"):
        raise Corr2EvidenceError("CORR2_SOURCE_RELEASE_MANIFEST_IDENTITY_MISSING")
    if not lineage.get("c2_record_ids"):
        raise Corr2EvidenceError("CORR2_SOURCE_LINEAGE_RECORD_IDS_MISSING")

    return {
        "schema": "ovc-c1c-g5-corr2-exact-evidence-context/v1",
        "packet_id": PACKET_ID,
        "return_gate": RETURN_GATE,
        "candidate_window_id": candidate_id,
        "is_deferred_object": candidate_id in DEFERRED_OBJECTS,
        "prior_finding_code": DEFERRED_OBJECTS.get(candidate_id),
        "exact_evidence_references": list(exact_evidence_references(candidate_id)),
        "queue_context": {
            "queue_item_id": queue.get("queue_item_id"),
            "clock": queue.get("clock"),
            "price_side": queue.get("price_side"),
            "window_start_utc": queue.get("window_start_utc"),
            "window_end_utc": queue.get("window_end_utc"),
            "trigger_first_valid_at": queue.get("trigger_first_valid_at"),
            "primary_trigger_reason": queue.get("primary_trigger_reason"),
            "quality_state": queue.get("quality_state"),
            "fingerprint_id": queue_fingerprint_id,
            "nearest_cluster_id": queue.get("nearest_cluster_id"),
            "nearest_cluster_distance": queue.get("nearest_cluster_distance"),
        },
        "fingerprint_context": {
            "fingerprint_id": fingerprint_id,
            "fingerprint_version": fingerprint.get("fingerprint_version"),
            "state_path": fingerprint.get("state_path"),
            "transition_path": fingerprint.get("transition_path"),
            "interaction_events": fingerprint.get("interaction_events"),
            "cross_scale_context": fingerprint.get("cross_scale_context"),
        },
        "source_lineage_context": {
            "release_id": lineage.get("release_id"),
            "manifest_id": lineage.get("manifest_id"),
            "c2_record_ids": list(lineage.get("c2_record_ids", ())),
            "fingerprint_id": lineage_fingerprint_id,
            "fingerprint_version": lineage.get("fingerprint_version"),
        },
        "authority": {
            "surface": "READ_ONLY_REVIEW_CONTEXT",
            "canonical_append": "DENIED",
            "promotion_eligibility": "NON_PROMOTABLE",
            "selector_mutation": "DENIED",
            "release_mutation": "DENIED",
        },
    }
