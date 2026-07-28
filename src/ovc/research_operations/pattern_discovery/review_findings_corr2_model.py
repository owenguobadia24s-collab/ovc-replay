from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from . import pilot_discovery as pilot

PACKET_ID = "C1C-G5-CORR2"
RETURN_GATE = "C1C-G5-CORRECTIVE-PILOT-REVIEW"
EXPECTED_RUN_ID = "PD.PILOT.RUN.96c16f11717e787f971851ee"
EXPECTED_NAMESPACE = "PD.PILOT.GBPUSD.20260622_20260625.v2"
REVIEW_INPUT_SCHEMA = "ovc-c1c-g5-corr2-deferred-rereview-input/v1"
REVIEW_RECEIPT_SCHEMA = "ovc-c1c-g5-corr2-deferred-rereview-receipt/v1"
CLOSURE_LEDGER_SCHEMA = "ovc-c1c-g5-corr2-closure-ledger/v1"
INVENTORY_SCHEMA = "ovc-c1c-g5-corr2-evidence-inventory/v1"
RETURN_GATE_SCHEMA = "ovc-c1c-g5-corrective-pilot-review-return-gate-input/v1"
TEMPLATE_NAME = "pilot-deferred-rereview.corr2.template.json"
CONTEXT_NAME = "pilot-deferred-rereview.corr2.context.json"
FINAL_DIR = "operator-review-corr2"
DEFERRED_FINDINGS = {
    "PDPILOT-CANDIDATE-4f41e21b6cd075e0fdbc40e4": "PD-DEFER-REVIEW-EVIDENCE-INCOMPLETE-001",
    "PDPILOT-CANDIDATE-bab63b935155e4d9033aed81": "PD-DEFER-STRUCTURAL-COMPARISON-PENDING-002",
}
FINAL_DISPOSITIONS = {"WORKFLOW_ACCEPTED", "REJECT_PILOT_OBJECT"}
ALLOWED_REFERENCE_PATHS = {
    "review/queue-items.jsonl",
    "review/console-bundle.json",
    "derived/fingerprints.jsonl",
    "derived/cluster-versions.jsonl",
    "operator-review-v2/pilot-review-receipt-v2.json",
}

class Corr2Error(RuntimeError):
    pass

def _require_text(source: Mapping[str, Any], field: str, code: str) -> str:
    value = str(source.get(field) or "").strip()
    if not value or "REPLACE_WITH" in value:
        raise Corr2Error(f"{code}:{field}")
    return value


def _require_strings(source: Mapping[str, Any], field: str, code: str) -> list[str]:
    value = source.get(field)
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise Corr2Error(f"{code}:{field}")
    normalized = sorted({str(item).strip() for item in value if str(item).strip()})
    if not normalized or any("REPLACE_WITH" in item for item in normalized):
        raise Corr2Error(f"{code}:{field}")
    return normalized


def _reference(candidate_id: str, path: str, key: str = "candidate_window_id") -> str:
    if path not in ALLOWED_REFERENCE_PATHS:
        raise Corr2Error(f"UNAPPROVED_EVIDENCE_REFERENCE_PATH:{path}")
    return f"{path}#{key}={candidate_id}"


def parse_evidence_reference(reference: str) -> tuple[str, str, str]:
    if "#" not in reference:
        raise Corr2Error(f"INVALID_EVIDENCE_REFERENCE:{reference}")
    path, fragment = reference.split("#", 1)
    if path not in ALLOWED_REFERENCE_PATHS or path.startswith("/") or ".." in Path(path).parts:
        raise Corr2Error(f"UNAPPROVED_EVIDENCE_REFERENCE_PATH:{path}")
    if "=" not in fragment:
        raise Corr2Error(f"INVALID_EVIDENCE_REFERENCE_FRAGMENT:{reference}")
    key, value = fragment.split("=", 1)
    if key not in {"candidate_window_id", "cluster_id"} or not value.strip():
        raise Corr2Error(f"INVALID_EVIDENCE_REFERENCE_FRAGMENT:{reference}")
    return path, key, value.strip()


def _by_candidate(rows: Iterable[Mapping[str, Any]], candidate_id: str, code: str) -> dict[str, Any]:
    matches = [dict(item) for item in rows if str(item.get("candidate_window_id") or item.get("window_id") or "") == candidate_id]
    if len(matches) != 1:
        raise Corr2Error(f"{code}:{candidate_id}:{len(matches)}")
    return matches[0]


def build_exact_evidence_context(
    *,
    queue_items: Sequence[Mapping[str, Any]],
    candidate_details: Mapping[str, Mapping[str, Any]],
    fingerprints: Sequence[Mapping[str, Any]],
    cluster_versions: Sequence[Mapping[str, Any]],
    candidate_id: str,
) -> dict[str, Any]:
    if candidate_id not in DEFERRED_FINDINGS:
        raise Corr2Error(f"CORR2_CANDIDATE_NOT_AUTHORISED:{candidate_id}")
    queue_item = _by_candidate(queue_items, candidate_id, "QUEUE_ITEM_RESOLUTION_FAILED")
    detail_source = candidate_details.get(candidate_id)
    if not isinstance(detail_source, Mapping):
        raise Corr2Error(f"CANDIDATE_DETAIL_RESOLUTION_FAILED:{candidate_id}")
    detail = dict(detail_source)
    fingerprint = _by_candidate(fingerprints, candidate_id, "FINGERPRINT_RESOLUTION_FAILED")
    detail_fingerprint = detail.get("fingerprint")
    if not isinstance(detail_fingerprint, Mapping):
        raise Corr2Error(f"DETAIL_FINGERPRINT_UNAVAILABLE:{candidate_id}")
    if str(detail_fingerprint.get("fingerprint_id")) != str(fingerprint.get("fingerprint_id")):
        raise Corr2Error(f"FINGERPRINT_IDENTITY_MISMATCH:{candidate_id}")

    nearest_cluster_id = str(queue_item.get("nearest_cluster_id") or "")
    cluster: dict[str, Any] | None = None
    if nearest_cluster_id:
        matches = [
            dict(item)
            for version in cluster_versions
            for item in version.get("clusters", ())
            if isinstance(item, Mapping) and str(item.get("cluster_id")) == nearest_cluster_id
        ]
        if len(matches) == 1:
            cluster = matches[0]
        elif len(matches) > 1:
            raise Corr2Error(f"DUPLICATE_CLUSTER_RESOLUTION:{nearest_cluster_id}")

    references = [
        _reference(candidate_id, "review/queue-items.jsonl"),
        _reference(candidate_id, "review/console-bundle.json"),
        _reference(candidate_id, "derived/fingerprints.jsonl"),
        _reference(candidate_id, "operator-review-v2/pilot-review-receipt-v2.json"),
    ]
    if nearest_cluster_id:
        references.append(_reference(nearest_cluster_id, "derived/cluster-versions.jsonl", "cluster_id"))

    neighbours = [dict(item) for item in detail.get("neighbours", ()) if isinstance(item, Mapping)]
    nearest_structural_comparison = neighbours[0] if neighbours else None
    structural_status = "AVAILABLE" if nearest_structural_comparison or cluster else "NOT_AVAILABLE_EXPLICIT"
    source_lineage = detail.get("source_lineage") if isinstance(detail.get("source_lineage"), Mapping) else {}

    return {
        "schema": "ovc-c1c-g5-corr2-exact-evidence-context/v1",
        "packet_id": PACKET_ID,
        "candidate_window_id": candidate_id,
        "source_finding_code": DEFERRED_FINDINGS[candidate_id],
        "evidence_references": sorted(references),
        "queue_context": {
            "queue_item_id": queue_item.get("queue_item_id"),
            "status": queue_item.get("status"),
            "quality_state": queue_item.get("quality_state"),
            "control_class": queue_item.get("control_class"),
            "window_start_utc": queue_item.get("window_start_utc"),
            "trigger_first_valid_at": queue_item.get("trigger_first_valid_at"),
            "window_end_utc": queue_item.get("window_end_utc"),
            "nearest_cluster_id": queue_item.get("nearest_cluster_id"),
            "nearest_cluster_distance": queue_item.get("nearest_cluster_distance"),
        },
        "candidate_detail_context": {
            "summary": dict(detail.get("summary", {})) if isinstance(detail.get("summary"), Mapping) else {},
            "trigger_explanation": dict(detail.get("trigger_explanation", {})) if isinstance(detail.get("trigger_explanation"), Mapping) else {},
            "source_lineage": dict(source_lineage),
        },
        "fingerprint_context": fingerprint,
        "nearest_structural_comparison": nearest_structural_comparison,
        "cluster_context": cluster,
        "structural_comparison_status": structural_status,
        "pilot_only": True,
        "promotion_eligibility": "NON_PROMOTABLE",
        "canonical_discovery_population": False,
        "canonical_append": "DENIED",
        "semantic_interpretation": "DENIED",
        "later_outcome_use": "DENIED",
    }


def build_corr2_console_rows(detail: Mapping[str, Any]) -> list[dict[str, Any]]:
    summary = detail.get("summary") if isinstance(detail.get("summary"), Mapping) else {}
    candidate_id = str(summary.get("candidate_window_id") or "")
    if not candidate_id:
        return []
    fingerprint = detail.get("fingerprint") if isinstance(detail.get("fingerprint"), Mapping) else {}
    lineage = detail.get("source_lineage") if isinstance(detail.get("source_lineage"), Mapping) else {}
    neighbours = [dict(item) for item in detail.get("neighbours", ()) if isinstance(item, Mapping)]
    rows = [
        {
            "evidence_surface": "QUEUE_ITEM",
            "reference": _reference(candidate_id, "review/queue-items.jsonl"),
            "identity": summary.get("queue_item_id"),
            "status": "RESOLVED_READ_ONLY",
        },
        {
            "evidence_surface": "CANDIDATE_DETAIL",
            "reference": _reference(candidate_id, "review/console-bundle.json"),
            "identity": candidate_id,
            "status": "RESOLVED_READ_ONLY",
        },
        {
            "evidence_surface": "FINGERPRINT",
            "reference": _reference(candidate_id, "derived/fingerprints.jsonl"),
            "identity": fingerprint.get("fingerprint_id"),
            "status": "RESOLVED_READ_ONLY" if fingerprint.get("fingerprint_id") else "NOT_AVAILABLE_EXPLICIT",
        },
        {
            "evidence_surface": "SOURCE_LINEAGE",
            "reference": _reference(candidate_id, "review/console-bundle.json"),
            "identity": lineage.get("release_id"),
            "status": "RESOLVED_READ_ONLY" if lineage.get("c2_record_ids") else "NOT_AVAILABLE_EXPLICIT",
        },
    ]
    if neighbours:
        rows.append({
            "evidence_surface": "NEAREST_STRUCTURAL_COMPARISON",
            "reference": _reference(candidate_id, "review/console-bundle.json"),
            "identity": neighbours[0].get("fingerprint_id") or neighbours[0].get("candidate_window_id"),
            "status": "RESOLVED_READ_ONLY",
        })
    else:
        rows.append({
            "evidence_surface": "NEAREST_STRUCTURAL_COMPARISON",
            "reference": _reference(candidate_id, "review/console-bundle.json"),
            "identity": None,
            "status": "NOT_AVAILABLE_EXPLICIT",
        })
    return rows


