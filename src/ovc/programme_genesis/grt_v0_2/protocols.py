from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping

from .bootstrap import BootstrapValidationError, validate_instance


def _parse_utc(text: str, *, field: str) -> datetime:
    if not isinstance(text, str) or not text.endswith("Z"):
        raise BootstrapValidationError(f"GRT_PROTOCOL_TIME_NOT_UTC:{field}")
    try:
        value = datetime.fromisoformat(text[:-1] + "+00:00")
    except ValueError as exc:
        raise BootstrapValidationError(f"GRT_PROTOCOL_TIME_INVALID:{field}") from exc
    if value.tzinfo != timezone.utc:
        raise BootstrapValidationError(f"GRT_PROTOCOL_TIME_NOT_UTC:{field}")
    return value


def validate_amendment_record(
    record: Mapping[str, Any],
    schema: Mapping[str, Any],
) -> None:
    validate_instance(record, schema)
    status = record["status"]
    if record["source_constitution_hash"] == record["candidate_constitution_hash"]:
        raise BootstrapValidationError("GRT_AMENDMENT_NO_SEMANTIC_GENERATION_CHANGE")
    if status in {"SHADOW_EVALUATION", "GATE_READY", "APPROVED"} and not record["shadow_evidence_refs"]:
        raise BootstrapValidationError("GRT_AMENDMENT_SHADOW_EVIDENCE_REQUIRED")
    if status in {"GATE_READY", "APPROVED"}:
        if not record["finding_migration_ref"]:
            raise BootstrapValidationError("GRT_AMENDMENT_FINDING_MIGRATION_REQUIRED")
        if not record["debt_floor_migration_ref"]:
            raise BootstrapValidationError("GRT_AMENDMENT_DEBT_FLOOR_MIGRATION_REQUIRED")
    if status == "APPROVED" and not record["operator_decision_ref"]:
        raise BootstrapValidationError("GRT_AMENDMENT_OPERATOR_DECISION_REQUIRED")
    if record["activation_gate"] != "OPERATOR_REQUIRED":
        raise BootstrapValidationError("GRT_AMENDMENT_OPERATOR_GATE_REQUIRED")


def validate_override_record(
    record: Mapping[str, Any],
    schema: Mapping[str, Any],
) -> None:
    validate_instance(record, schema)
    issued_at = _parse_utc(record["issued_at"], field="issued_at")
    expires_at = _parse_utc(record["expires_at"], field="expires_at")
    remediation_due = _parse_utc(record["remediation_due"], field="remediation_due")
    if expires_at <= issued_at:
        raise BootstrapValidationError("GRT_OVERRIDE_EXPIRY_NOT_AFTER_ISSUE")
    if remediation_due < issued_at:
        raise BootstrapValidationError("GRT_OVERRIDE_REMEDIATION_PRECEDES_ISSUE")
    if record["max_uses"] != 1:
        raise BootstrapValidationError("GRT_OVERRIDE_MAX_USES_NOT_ONE")
    if record["uses"] > record["max_uses"]:
        raise BootstrapValidationError("GRT_OVERRIDE_ALREADY_OVERUSED")
    if record["base_commit"] == record["candidate_commit"]:
        raise BootstrapValidationError("GRT_OVERRIDE_CANDIDATE_EQUALS_BASE")
    if record["underlying_finding_status"] != "TEMPORARILY_ADMITTED_ACTIONABLE":
        raise BootstrapValidationError("GRT_OVERRIDE_FINDING_STATUS_WEAKENED")


def validate_historical_disposition_record(
    record: Mapping[str, Any],
    schema: Mapping[str, Any],
) -> None:
    validate_instance(record, schema)
    open_count = record["batch_open_b0_count"]
    member_count = record["batch_member_count"]
    if open_count == 0 and member_count > 0:
        raise BootstrapValidationError("GRT_DISPOSITION_OPEN_DENOMINATOR_ZERO")
    enhanced_required = member_count * 20 > open_count
    if enhanced_required and not record["enhanced_independent_qa_required"]:
        raise BootstrapValidationError("GRT_DISPOSITION_ENHANCED_QA_REQUIRED")
    if enhanced_required and len(record["qa_refs"]) < 2:
        raise BootstrapValidationError("GRT_DISPOSITION_INDEPENDENT_QA_EVIDENCE_REQUIRED")


__all__ = [
    "validate_amendment_record",
    "validate_override_record",
    "validate_historical_disposition_record",
]
