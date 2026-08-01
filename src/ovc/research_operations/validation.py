from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .availability import derive_reproducibility_state

RECORD_TYPES = {
    "DATA_RELEASE_REF", "RESEARCH_SESSION", "OBSERVATION_SNAPSHOT", "CLAIM_RECORD",
    "REALIZATION_SNAPSHOT", "EVIDENCE_ITEM", "CASE_BUNDLE", "INCIDENT_RECORD",
    "DECISION_RECORD", "AUDIT_EVENT",
    "RO4_SEQUENCE_BOUNDARY_ANNOTATION.v0.1", "RO4_C2E_FRICTION_RECORD.v0.1",
    "RO4_PROSPECTIVE_SEQUENCE_REVIEW.v0.1", "RO4_SIGNATURE_CONCENTRATION_ACKNOWLEDGEMENT.v0.1",
}
PAYLOAD_REQUIRED = {
    "DATA_RELEASE_REF": {"release_id", "manifest_id", "manifest_sha256", "role", "instrument", "coverage_start", "coverage_end", "clocks", "sides", "qa_state", "validation_access_state"},
    "RESEARCH_SESSION": {"objective", "instrument", "research_role", "session_state", "objects_reviewed"},
    "OBSERVATION_SNAPSHOT": {"session_id", "visible_facts", "unknowns", "source_record_refs"},
    "CLAIM_RECORD": {"observation_id", "eligibility", "discriminator", "falsifier", "horizons"},
    "REALIZATION_SNAPSHOT": {"observation_id", "reference_time", "horizon", "coverage", "path", "censoring_state"},
    "EVIDENCE_ITEM": {"observation_id", "claim_id", "realization_id", "evidence_role", "admissibility"},
    "CASE_BUNDLE": {"title", "record_refs", "artifact_refs", "review_state"},
    "INCIDENT_RECORD": {"incident_code", "severity", "target_id", "description", "blocking_effect"},
    "DECISION_RECORD": {"decision_scope", "disposition", "reason", "authority_delta", "rollback"},
    "AUDIT_EVENT": {"actor", "action", "object_id", "result", "trace_ref"},
    "RO4_SEQUENCE_BOUNDARY_ANNOTATION.v0.1": {
        "source_sequence_id", "source_release_id", "manifest_sha256", "clock", "side", "member_ids",
        "member_first_valid_times", "operation_mode", "annotation", "rationale", "record_authority",
        "c2_mutation", "pd_population_write", "semantic_authority",
    },
    "RO4_C2E_FRICTION_RECORD.v0.1": {
        "source_sequence_id", "source_release_id", "source_first_valid_times", "operation_mode", "reason_code",
        "evidence_refs", "counterexample_refs", "remediation_ref", "rationale", "record_authority",
        "c2_mutation", "c2e_opening", "pd_population_write", "semantic_authority",
    },
    "RO4_PROSPECTIVE_SEQUENCE_REVIEW.v0.1": {
        "source_sequence_id", "source_release_and_manifest", "operation_mode", "admissible", "post_cutoff_review",
        "logical_hash", "source_first_valid_times", "record_authority", "replay_to_prospective_translation",
        "validation_consumption",
    },
    "RO4_SIGNATURE_CONCENTRATION_ACKNOWLEDGEMENT.v0.1": {
        "population_id", "diversity_audit_logical_hash", "warning_status", "acknowledgement",
        "record_authority", "promotion_authority",
    },
}
COMMON_REQUIRED = {
    "record_type", "schema_version", "lifecycle_state", "created_at", "frozen_at",
    "operator_id", "admissible_cutoff", "source_release_refs", "artifact_refs",
    "missingness", "lineage", "authority_state", "reproducibility_state",
    "payload", "content_sha256",
}


class RecordValidationError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(f"{code}: {message}")
        self.code = code


def _dt(value: str) -> datetime:
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        raise RecordValidationError("INVALID_TIME", "timestamps must be timezone-aware")
    return parsed.astimezone(timezone.utc)


def validate_record(record: dict[str, Any]) -> None:
    missing = COMMON_REQUIRED - set(record)
    if missing:
        raise RecordValidationError("MISSING_ENVELOPE_FIELD", ",".join(sorted(missing)))
    record_type = record["record_type"]
    if record_type not in RECORD_TYPES:
        raise RecordValidationError("UNKNOWN_RECORD_TYPE", str(record_type))
    if record["schema_version"] != "0.1":
        raise RecordValidationError("SCHEMA_VERSION_MISMATCH", str(record["schema_version"]))
    if set(record["lineage"]) != {"parent", "derived_from", "supersedes", "adjudicates"}:
        raise RecordValidationError("INVALID_LINEAGE", "lineage keys must be exact")
    payload_missing = PAYLOAD_REQUIRED[record_type] - set(record["payload"])
    if payload_missing:
        raise RecordValidationError("MISSING_PAYLOAD_FIELD", ",".join(sorted(payload_missing)))

    cutoff = _dt(record["admissible_cutoff"])
    for group in ("source_release_refs", "artifact_refs", "model_refs"):
        for ref in record.get(group, []) or []:
            for key in ("first_valid_time", "available_at"):
                if ref.get(key) and _dt(ref[key]) > cutoff:
                    raise RecordValidationError("POST_CUTOFF_REFERENCE", f"{group}.{key}={ref[key]}")

    for ref in record.get("source_release_refs", []):
        if ref.get("release_id") == "OPT-A.GBPUSD.VALIDATION.2025.v2":
            forbidden = any(key in ref for key in ("payload_ref", "bar_id", "object_path"))
            if ref.get("validation_access_state") != "LOCKED_UNCONSUMED" or ref.get("payload_access") not in (None, "DENIED") or forbidden:
                raise RecordValidationError("VALIDATION_PAYLOAD_ACCESS_DENIED", "Validation metadata only")

    expected = derive_reproducibility_state(record.get("artifact_refs", []))
    if record["lifecycle_state"] != "DRAFT" and record["reproducibility_state"] != expected:
        raise RecordValidationError("REPRODUCIBILITY_STATE_MISMATCH", f"expected {expected}")
