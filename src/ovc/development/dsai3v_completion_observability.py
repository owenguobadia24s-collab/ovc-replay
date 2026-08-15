"""Canonical DEVOBS receipt attached to DSAI3V packet completion.

The receipt is diagnostic-only. It joins already-observed DEVOBS latency context with
ORCH, VIT and SIQ provenance without granting authority or inferring unobserved time.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Mapping, Sequence

from ovc.development.identity import canonical_sha256

CANONICAL_COMPLETION_SCHEMA = "ovc-development-latency-canonical-dsai3v/v1"
ATTACHMENT_SCHEMA = "ovc-dsai3v-completion-observability-attachment/v1"


def _record_ref(value: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "schema": value.get("schema"),
        "record_id": value.get("record_id") or value.get("receipt_id"),
        "run_id": value.get("run_id"),
        "packet_id": value.get("packet_id"),
        "status": value.get("status") or value.get("outcome") or value.get("decision_state"),
    }


def _count_truthy(records: Sequence[Mapping[str, Any]], *keys: str) -> int:
    return sum(1 for row in records if any(row.get(key) is True for key in keys))


def _count_value(records: Sequence[Mapping[str, Any]], key: str, values: set[str]) -> int:
    return sum(1 for row in records if str(row.get(key, "")).upper() in values)


def build_canonical_completion_latency_receipt(
    *,
    programme_id: str,
    packet_id: str,
    completion_receipt_id: str,
    contextual_latency_receipt: Mapping[str, Any] | None = None,
    trace_summary: Mapping[str, Any] | None = None,
    orch_receipts: Sequence[Mapping[str, Any]] = (),
    vit_receipts: Sequence[Mapping[str, Any]] = (),
    siq_receipts: Sequence[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    """Build one content-addressed completion receipt from observed source receipts."""
    if not programme_id or not packet_id or not completion_receipt_id:
        raise ValueError("programme_id, packet_id and completion_receipt_id are required")

    context: dict[str, Any] = {
        "task_profile": None,
        "assistant_configuration": None,
        "comparison_keys": None,
        "context_status": "UNAVAILABLE",
    }
    if contextual_latency_receipt is not None:
        if contextual_latency_receipt.get("schema") != "ovc-development-latency-diagnostic-companion/v2":
            raise ValueError("contextual latency receipt must be DEVOBS v0.2 companion")
        context = {
            "task_profile": contextual_latency_receipt.get("task_profile"),
            "assistant_configuration": contextual_latency_receipt.get("assistant_configuration"),
            "comparison_keys": contextual_latency_receipt.get("comparison_keys"),
            "context_status": "OBSERVED",
            "context_receipt_id": contextual_latency_receipt.get("record_id"),
        }

    latency = {
        "status": "UNAVAILABLE",
        "total_wall_ms": None,
        "throughput": None,
        "latency_decomposition": None,
        "trace_summary_id": None,
    }
    if trace_summary is not None:
        if trace_summary.get("schema") != "ovc-development-observability-trace-summary/v1":
            raise ValueError("trace_summary schema mismatch")
        latency = {
            "status": "OBSERVED",
            "total_wall_ms": trace_summary.get("total_wall_ms"),
            "throughput": trace_summary.get("throughput"),
            "latency_decomposition": trace_summary.get("latency_decomposition"),
            "trace_summary_id": trace_summary.get("record_id"),
        }

    orch = tuple(dict(row) for row in orch_receipts)
    vit = tuple(dict(row) for row in vit_receipts)
    siq = tuple(dict(row) for row in siq_receipts)
    logical = {
        "programme_id": str(programme_id),
        "packet_id": str(packet_id),
        "completion_receipt_id": str(completion_receipt_id),
        "devobs_context": context,
        "latency": latency,
        "orch": {
            "receipt_count": len(orch),
            "decision_selected_count": _count_value(orch, "decision_state", {"DECISION_SELECTED"}),
            "execution_started_count": _count_value(orch, "execution_state", {"EXECUTION_STARTED", "EXECUTION_COMPLETED"}),
            "execution_completed_count": _count_value(orch, "execution_state", {"EXECUTION_COMPLETED"}),
            "receipts": [_record_ref(row) for row in orch],
        },
        "vit": {
            "receipt_count": len(vit),
            "exact_tree_equal_count": _count_truthy(vit, "exact_tree_equal", "equality"),
            "tree_mismatch_count": _count_value(vit, "outcome", {"POST_WRITE_TREE_MISMATCH"}),
            "supersession_or_rebuild_count": sum(int(row.get("supersession_or_rebuild_count", 0) or 0) for row in vit),
            "receipts": [_record_ref(row) for row in vit],
        },
        "siq": {
            "receipt_count": len(siq),
            "ready_pass_count": _count_value(siq, "status", {"READY", "PASS", "SIQ_READY"}),
            "base_moved_count": _count_value(siq, "reason", {"OVC_BASE_MOVED_BEFORE_READINESS", "PREDECESSOR_MOVED"}),
            "lease_wait_or_retry_count": sum(int(row.get("lease_wait_or_retry_count", 0) or 0) for row in siq),
            "receipts": [_record_ref(row) for row in siq],
        },
        "evidence_rule": "OBSERVED_FIELDS_ONLY_NO_UNOBSERVED_LATENCY_OR_EXECUTION_INFERENCE",
        "authority_effect": "NONE",
    }
    return {
        "schema": CANONICAL_COMPLETION_SCHEMA,
        **logical,
        "record_id": canonical_sha256(logical, role="OVC_DSAI3V_CANONICAL_DEVELOPMENT_LATENCY_RECEIPT"),
    }


@dataclass(frozen=True)
class CompletionObservabilityAttachment:
    programme_id: str
    packet_id: str
    completion_receipt_id: str
    development_latency_receipt_id: str
    authority_effect: str = "NONE"

    @property
    def attachment_id(self) -> str:
        return canonical_sha256(asdict(self), role="OVC_DSAI3V_COMPLETION_OBSERVABILITY_ATTACHMENT")

    def to_record(self) -> dict[str, Any]:
        return {"schema": ATTACHMENT_SCHEMA, **asdict(self), "attachment_id": self.attachment_id}


def validate_completion_attachment(
    *,
    programme_id: str,
    packet_id: str,
    completion_receipt_id: str,
    development_latency_receipt: Mapping[str, Any],
) -> CompletionObservabilityAttachment:
    if development_latency_receipt.get("schema") != CANONICAL_COMPLETION_SCHEMA:
        raise ValueError("canonical development latency receipt schema mismatch")
    if development_latency_receipt.get("programme_id") != programme_id:
        raise ValueError("programme_id mismatch")
    if development_latency_receipt.get("packet_id") != packet_id:
        raise ValueError("packet_id mismatch")
    if development_latency_receipt.get("completion_receipt_id") != completion_receipt_id:
        raise ValueError("completion receipt binding mismatch")
    if development_latency_receipt.get("authority_effect") != "NONE":
        raise ValueError("development latency receipt must be authority-inert")
    record_id = development_latency_receipt.get("record_id")
    if not isinstance(record_id, str) or not record_id:
        raise ValueError("development latency receipt record_id is required")
    return CompletionObservabilityAttachment(programme_id, packet_id, completion_receipt_id, record_id)
