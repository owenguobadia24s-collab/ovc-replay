"""Prospective source-bound DSAI3V canonical completion receipt v2.

V1 remains historical and unchanged. V2 is diagnostic-only, append-only and
authority-inert; it records only directly observed source-bound timestamps and
never manufactures chronology from another event.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import re
from typing import Any, Mapping, Sequence

from ovc.development.dsai3v_completion_observability import CANONICAL_COMPLETION_SCHEMA
from ovc.development.identity import canonical_sha256

CANONICAL_COMPLETION_SCHEMA_V1 = CANONICAL_COMPLETION_SCHEMA
CANONICAL_COMPLETION_SCHEMA_V2 = "ovc-development-latency-canonical-dsai3v/v2"
ATTACHMENT_SCHEMA_V2 = "ovc-dsai3v-completion-observability-attachment/v2"
V2_EVIDENCE_RULE = "OBSERVED_SOURCE_BOUND_TIMESTAMPS_ONLY_NO_CHRONOLOGY_INFERENCE"
TIMING_FIELDS = (
    "pr_opened_at_utc",
    "aa0_reuse_observed_at_utc",
    "profile_passed_at_utc",
    "siq_ready_at_utc",
    "merge_readiness_passed_at_utc",
    "physical_materialised_at_utc",
    "packet_completion_receipt_persisted_at_utc",
    "completion_proof_persisted_at_utc",
)
TIMING_STATUSES = frozenset({"OBSERVED_COMPLETE", "OBSERVED_PARTIAL", "UNAVAILABLE"})
SOURCE_TYPES = frozenset({
    "GITHUB_PR", "GITHUB_WORKFLOW_JOB", "GITHUB_CHECK_RUN",
    "INTEGRATION_ADMISSION_RECEIPT", "PHYSICAL_MATERIALISATION_RECEIPT",
    "PACKET_COMPLETION_RECEIPT", "DEVOBS_RECEIPT", "COMPLETION_PROOF",
    "OWNER_LOCAL_RECEIPT", "EXACT_LOG",
})
SOURCE_PRECEDENCE = {
    "PHYSICAL_MATERIALISATION_RECEIPT": 1,
    "PACKET_COMPLETION_RECEIPT": 1,
    "COMPLETION_PROOF": 1,
    "INTEGRATION_ADMISSION_RECEIPT": 1,
    "OWNER_LOCAL_RECEIPT": 1,
    "GITHUB_PR": 2,
    "GITHUB_WORKFLOW_JOB": 2,
    "GITHUB_CHECK_RUN": 2,
    "DEVOBS_RECEIPT": 3,
    "EXACT_LOG": 4,
}
MANDATORY_ORDERINGS = (
    ("pr_opened_at_utc", "aa0_reuse_observed_at_utc"),
    ("pr_opened_at_utc", "profile_passed_at_utc"),
    ("pr_opened_at_utc", "siq_ready_at_utc"),
    ("pr_opened_at_utc", "merge_readiness_passed_at_utc"),
    ("pr_opened_at_utc", "physical_materialised_at_utc"),
    ("aa0_reuse_observed_at_utc", "physical_materialised_at_utc"),
    ("profile_passed_at_utc", "physical_materialised_at_utc"),
    ("siq_ready_at_utc", "physical_materialised_at_utc"),
    ("merge_readiness_passed_at_utc", "physical_materialised_at_utc"),
    ("physical_materialised_at_utc", "packet_completion_receipt_persisted_at_utc"),
    ("packet_completion_receipt_persisted_at_utc", "completion_proof_persisted_at_utc"),
)
DERIVED_LATENCIES = {
    "pr_open_to_materialised_ms": ("pr_opened_at_utc", "physical_materialised_at_utc"),
    "pr_open_to_siq_ready_ms": ("pr_opened_at_utc", "siq_ready_at_utc"),
    "pr_open_to_merge_readiness_ms": ("pr_opened_at_utc", "merge_readiness_passed_at_utc"),
    "merge_readiness_to_materialised_ms": ("merge_readiness_passed_at_utc", "physical_materialised_at_utc"),
    "materialised_to_packet_completion_ms": ("physical_materialised_at_utc", "packet_completion_receipt_persisted_at_utc"),
    "materialised_to_completion_proof_ms": ("physical_materialised_at_utc", "completion_proof_persisted_at_utc"),
}
_RFC3339 = re.compile(r"^(?P<date>\d{4}-\d{2}-\d{2})T(?P<time>\d{2}:\d{2}:\d{2})(?:\.(?P<fraction>\d{1,6}))?(?P<zone>Z|[+-]\d{2}:\d{2})$")
_SHA40 = re.compile(r"^[0-9a-f]{40}$")
_SHA64 = re.compile(r"^[0-9a-f]{64}$")


def normalize_canonical_utc(value: str) -> str:
    text = str(value).strip()
    match = _RFC3339.fullmatch(text)
    if not match:
        raise ValueError("timestamp must be timezone-explicit RFC3339 with at most microsecond precision")
    candidate = text[:-1] + "+00:00" if text.endswith("Z") else text
    parsed = datetime.fromisoformat(candidate)
    if parsed.tzinfo is None:
        raise ValueError("timestamp timezone is required")
    utc = parsed.astimezone(timezone.utc)
    result = utc.strftime("%Y-%m-%dT%H:%M:%S")
    fraction = match.group("fraction")
    if fraction is not None:
        result += "." + f"{utc.microsecond:06d}"[: len(fraction)]
    return result + "Z"


def _parse_utc(value: str) -> datetime:
    normalized = normalize_canonical_utc(value)
    return datetime.fromisoformat(normalized[:-1] + "+00:00")


def _source_row(value: Mapping[str, Any]) -> dict[str, str]:
    field = str(value.get("field", ""))
    source_type = str(value.get("source_type", ""))
    source_id = str(value.get("source_id", ""))
    authority = str(value.get("authority", ""))
    if field not in TIMING_FIELDS:
        raise ValueError(f"unknown timing field: {field}")
    if source_type not in SOURCE_TYPES:
        raise ValueError(f"unknown timing source type: {source_type}")
    if not source_id:
        raise ValueError("timing source_id is required")
    if authority != "OBSERVATIONAL_ONLY":
        raise ValueError("timing source authority must be OBSERVATIONAL_ONLY")
    observed = value.get("observed_at_utc")
    if not isinstance(observed, str) or not observed:
        raise ValueError("timing source observed_at_utc is required")
    return {
        "field": field,
        "source_type": source_type,
        "source_id": source_id,
        "observed_at_utc": normalize_canonical_utc(observed),
        "authority": "OBSERVATIONAL_ONLY",
    }


def _timing_model(sources: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    normalized = sorted(
        (_source_row(row) for row in sources),
        key=lambda row: (
            row["field"],
            SOURCE_PRECEDENCE[row["source_type"]],
            row["source_type"],
            row["source_id"],
            row["observed_at_utc"],
        ),
    )
    selected: dict[str, str | None] = {field: None for field in TIMING_FIELDS}
    selected_sources: dict[str, dict[str, str]] = {}
    for field in TIMING_FIELDS:
        matches = [row for row in normalized if row["field"] == field]
        if matches:
            selected[field] = matches[0]["observed_at_utc"]
            selected_sources[field] = matches[0]

    warnings: list[dict[str, str]] = []
    invalid: set[tuple[str, str]] = set()
    for earlier, later in MANDATORY_ORDERINGS:
        first = selected[earlier]
        second = selected[later]
        if first is not None and second is not None and _parse_utc(first) > _parse_utc(second):
            invalid.add((earlier, later))
            warnings.append(
                {
                    "code": "SOURCE_TIMESTAMP_ORDER_INVALID",
                    "earlier_field": earlier,
                    "later_field": later,
                }
            )

    derived: dict[str, float | None] = {}
    for name, (earlier, later) in DERIVED_LATENCIES.items():
        first = selected[earlier]
        second = selected[later]
        if first is None or second is None or (earlier, later) in invalid:
            derived[name] = None
            continue
        milliseconds = (_parse_utc(second) - _parse_utc(first)).total_seconds() * 1000
        derived[name] = None if milliseconds < 0 else round(milliseconds, 3)

    observed_count = sum(value is not None for value in selected.values())
    if observed_count == 0:
        status = "UNAVAILABLE"
    elif observed_count == len(TIMING_FIELDS) and not warnings:
        status = "OBSERVED_COMPLETE"
    else:
        status = "OBSERVED_PARTIAL"
    return {
        "status": status,
        **selected,
        "sources": normalized,
        "selected_sources": selected_sources,
        "warnings": warnings,
        "derived_latency_ms": derived,
    }


def _nullable_id(value: Any, *, length: int | None = None) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    if length == 40 and not _SHA40.fullmatch(text):
        raise ValueError("expected lowercase 40-character SHA")
    if length == 64 and not _SHA64.fullmatch(text):
        raise ValueError("expected lowercase 64-character SHA")
    return text


def _aa0_model(value: Mapping[str, Any] | None) -> dict[str, Any]:
    row = dict(value or {})
    allowed = {
        "repository_assurance_disposition", "unittest_parity_disposition",
        "runner_parity_disposition", "canonical_shards_executed",
        "candidate_head_sha", "pr_head_sha", "pip_id", "qualification_id",
        "aa0_harness_id", "prewarm_run_id", "prewarm_completed_at_utc",
        "pr_assurance_run_id", "prospective_tree_sha", "physical_tree_sha",
    }
    unknown = sorted(set(row) - allowed)
    if unknown:
        raise ValueError(f"unknown AA0 observability fields: {unknown}")
    for key in (
        "repository_assurance_disposition",
        "unittest_parity_disposition",
        "runner_parity_disposition",
    ):
        if row.get(key) is not None and str(row[key]) not in {
            "RUN_AA0", "EXACT_GENERATION_REUSE", "PLACEMENT_ONLY_PIP_REUSE"
        }:
            raise ValueError(f"invalid {key}")
    shards = row.get("canonical_shards_executed")
    if shards is not None and not isinstance(shards, bool):
        raise ValueError("canonical_shards_executed must be bool or null")
    result = {
        "repository_assurance_disposition": row.get("repository_assurance_disposition"),
        "unittest_parity_disposition": row.get("unittest_parity_disposition"),
        "runner_parity_disposition": row.get("runner_parity_disposition"),
        "canonical_shards_executed": shards,
        "candidate_head_sha": _nullable_id(row.get("candidate_head_sha"), length=40),
        "pr_head_sha": _nullable_id(row.get("pr_head_sha"), length=40),
        "pip_id": _nullable_id(row.get("pip_id"), length=64),
        "qualification_id": _nullable_id(row.get("qualification_id"), length=64),
        "aa0_harness_id": _nullable_id(row.get("aa0_harness_id"), length=64),
        "prewarm_run_id": _nullable_id(row.get("prewarm_run_id")),
        "prewarm_completed_at_utc": (
            normalize_canonical_utc(str(row["prewarm_completed_at_utc"]))
            if row.get("prewarm_completed_at_utc") else None
        ),
        "pr_assurance_run_id": _nullable_id(row.get("pr_assurance_run_id")),
        "prospective_tree_sha": _nullable_id(row.get("prospective_tree_sha"), length=40),
        "physical_tree_sha": _nullable_id(row.get("physical_tree_sha"), length=40),
    }
    if (
        result["candidate_head_sha"]
        and result["pr_head_sha"]
        and result["candidate_head_sha"] != result["pr_head_sha"]
    ):
        raise ValueError("PR/head mismatch")
    if (
        result["prospective_tree_sha"]
        and result["physical_tree_sha"]
        and result["prospective_tree_sha"] != result["physical_tree_sha"]
    ):
        raise ValueError("materialisation tree mismatch")
    return result


def _validate_v1_identity(receipt: Mapping[str, Any]) -> None:
    if receipt.get("schema") != CANONICAL_COMPLETION_SCHEMA_V1:
        raise ValueError("v1 canonical receipt schema mismatch")
    record_id = receipt.get("record_id")
    if not isinstance(record_id, str) or not record_id:
        raise ValueError("v1 record_id is required")
    logical = {key: value for key, value in receipt.items() if key not in {"schema", "record_id"}}
    if canonical_sha256(
        logical, role="OVC_DSAI3V_CANONICAL_DEVELOPMENT_LATENCY_RECEIPT"
    ) != record_id:
        raise ValueError("v1 record identity mismatch")


def build_canonical_completion_latency_receipt_v2(
    *,
    v1_receipt: Mapping[str, Any],
    timing_sources: Sequence[Mapping[str, Any]] = (),
    aa0_observability: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    _validate_v1_identity(v1_receipt)
    logical = {
        "programme_id": str(v1_receipt["programme_id"]),
        "packet_id": str(v1_receipt["packet_id"]),
        "completion_receipt_id": str(v1_receipt["completion_receipt_id"]),
        "v1_receipt_id": str(v1_receipt["record_id"]),
        "devobs_context": v1_receipt["devobs_context"],
        "latency": v1_receipt["latency"],
        "async_assurance": v1_receipt.get("async_assurance"),
        "orch": v1_receipt["orch"],
        "vit": v1_receipt["vit"],
        "siq": v1_receipt["siq"],
        "timing": _timing_model(timing_sources),
        "aa0": _aa0_model(aa0_observability),
        "evidence_rule": V2_EVIDENCE_RULE,
        "authority_effect": "NONE",
    }
    return {
        "schema": CANONICAL_COMPLETION_SCHEMA_V2,
        **logical,
        "record_id": canonical_sha256(
            logical, role="OVC_DSAI3V_CANONICAL_DEVELOPMENT_LATENCY_RECEIPT_V2"
        ),
    }


def validate_canonical_completion_latency_receipt_v2(
    receipt: Mapping[str, Any],
    *,
    expected: Mapping[str, Any] | None = None,
) -> None:
    if receipt.get("schema") != CANONICAL_COMPLETION_SCHEMA_V2:
        raise ValueError("v2 canonical receipt schema mismatch")
    logical = {key: value for key, value in receipt.items() if key not in {"schema", "record_id"}}
    if canonical_sha256(
        logical, role="OVC_DSAI3V_CANONICAL_DEVELOPMENT_LATENCY_RECEIPT_V2"
    ) != receipt.get("record_id"):
        raise ValueError("v2 record identity mismatch")
    if receipt.get("authority_effect") != "NONE":
        raise ValueError("v2 receipt must be authority-inert")
    timing = receipt.get("timing")
    aa0 = receipt.get("aa0")
    if not isinstance(timing, Mapping) or timing.get("status") not in TIMING_STATUSES:
        raise ValueError("v2 timing invalid")
    if not isinstance(aa0, Mapping):
        raise ValueError("v2 AA0 invalid")
    expected = dict(expected or {})
    for key in ("programme_id", "packet_id", "completion_receipt_id"):
        if key in expected and receipt.get(key) != expected[key]:
            raise ValueError(f"{key} mismatch")
    for key in (
        "candidate_head_sha", "pr_head_sha", "pip_id", "qualification_id",
        "aa0_harness_id", "prospective_tree_sha", "physical_tree_sha",
    ):
        if key in expected and aa0.get(key) != expected[key]:
            raise ValueError(f"{key} mismatch")


def validate_compatible_canonical_completion_receipt(receipt: Mapping[str, Any]) -> str:
    """Validate a canonical completion receipt and return its exact schema version."""
    schema = str(receipt.get("schema", ""))
    if schema == CANONICAL_COMPLETION_SCHEMA_V1:
        _validate_v1_identity(receipt)
        return CANONICAL_COMPLETION_SCHEMA_V1
    if schema == CANONICAL_COMPLETION_SCHEMA_V2:
        validate_canonical_completion_latency_receipt_v2(receipt)
        return CANONICAL_COMPLETION_SCHEMA_V2
    raise ValueError("unsupported canonical completion receipt schema")


@dataclass(frozen=True)
class CompletionObservabilityAttachmentV2:
    programme_id: str
    packet_id: str
    completion_receipt_id: str
    development_latency_receipt_id: str
    authority_effect: str = "NONE"

    @property
    def attachment_id(self) -> str:
        return canonical_sha256(
            asdict(self), role="OVC_DSAI3V_COMPLETION_OBSERVABILITY_ATTACHMENT_V2"
        )

    def to_record(self) -> dict[str, Any]:
        return {
            "schema": ATTACHMENT_SCHEMA_V2,
            **asdict(self),
            "attachment_id": self.attachment_id,
        }


def build_completion_attachment_v2(
    *,
    programme_id: str,
    packet_id: str,
    completion_receipt_id: str,
    development_latency_receipt: Mapping[str, Any],
) -> CompletionObservabilityAttachmentV2:
    validate_canonical_completion_latency_receipt_v2(
        development_latency_receipt,
        expected={
            "programme_id": programme_id,
            "packet_id": packet_id,
            "completion_receipt_id": completion_receipt_id,
        },
    )
    return CompletionObservabilityAttachmentV2(
        programme_id,
        packet_id,
        completion_receipt_id,
        str(development_latency_receipt["record_id"]),
    )
