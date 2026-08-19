from __future__ import annotations

from collections.abc import Mapping, Sequence
from copy import deepcopy
from typing import Any

from ovc.research_operations.canonical import canonical_sha256

REQUIRED_ENVELOPE_FIELDS = (
    "generation_id",
    "source_frontier_id",
    "currentness_state",
    "visibility_state",
    "completeness_state",
    "warnings",
)


class ProjectionValidationError(ValueError):
    pass


def _digest(value: str, field: str) -> str:
    if type(value) is not str or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
        raise ProjectionValidationError(f"{field} must be lowercase SHA-256")
    return value


def _require_envelope(record: Mapping[str, Any]) -> None:
    missing = [field for field in REQUIRED_ENVELOPE_FIELDS if field not in record]
    if missing:
        raise ProjectionValidationError(f"missing projection envelope fields: {missing}")
    if record.get("read_only") is not True:
        raise ProjectionValidationError("Research Console projection must be read-only")
    if record.get("authority_effect") != "NONE":
        raise ProjectionValidationError("Research Console projection may not grant authority")


def build_console_projection(
    *,
    query_family: str,
    query_result: Mapping[str, Any],
    evidence_passport_refs: Sequence[str],
    system_atlas_deep_link: str | None = None,
) -> dict[str, Any]:
    if type(query_family) is not str or not query_family:
        raise ProjectionValidationError("query_family is required")
    _require_envelope(query_result)
    refs = sorted(set(evidence_passport_refs))
    if any(type(ref) is not str or not ref for ref in refs):
        raise ProjectionValidationError("evidence_passport_refs must contain non-empty strings")
    if len(refs) != len(evidence_passport_refs):
        raise ProjectionValidationError("evidence_passport_refs must be unique")
    if system_atlas_deep_link is not None and (type(system_atlas_deep_link) is not str or not system_atlas_deep_link):
        raise ProjectionValidationError("system_atlas_deep_link must be a non-empty string when supplied")

    body = {
        "schema": "ovc-p2ctii-console-projection/v0.1",
        "source_id": "P2CTI",
        "query_family": query_family,
        "generation_id": query_result["generation_id"],
        "source_frontier_id": query_result["source_frontier_id"],
        "currentness_state": query_result["currentness_state"],
        "visibility_state": query_result["visibility_state"],
        "completeness_state": query_result["completeness_state"],
        "warnings": sorted(set(query_result.get("warnings", []))),
        "result": deepcopy(query_result.get("result")),
        "evidence_passport_refs": refs,
        "system_atlas_deep_link": system_atlas_deep_link,
        "read_only": True,
        "write_controls_present": False,
        "consumer_admission_granted": False,
        "operational_reliance": False,
        "authority_effect": "NONE",
    }
    return {**body, "content_sha256": canonical_sha256(body)}


def build_source_admission_packet(
    *,
    source_frontier_id: str,
    projection_evidence_sha256: str,
    producer_authority_refs: Sequence[str],
) -> dict[str, Any]:
    refs = sorted(set(producer_authority_refs))
    if not refs or any(type(ref) is not str or not ref for ref in refs):
        raise ProjectionValidationError("producer authority references are required")
    if type(source_frontier_id) is not str or not source_frontier_id.startswith("p2cti:frontier:"):
        raise ProjectionValidationError("source_frontier_id must be exact P2CTI frontier identity")
    _digest(source_frontier_id.rsplit(":", 1)[1], "source_frontier_id")
    _digest(projection_evidence_sha256, "projection_evidence_sha256")

    body = {
        "schema": "ovc-p2ctii-research-console-source-admission-packet/v0.1",
        "producer": "OVC-P2CTI-CONFORMANCE-v0.1",
        "source_id": "P2CTI",
        "source_frontier_id": source_frontier_id,
        "projection_evidence_sha256": projection_evidence_sha256,
        "producer_authority_refs": refs,
        "presentation_contract": "READ_ONLY_EVIDENCE_PRESERVING",
        "producer_recommendation": "READY_FOR_CONSUMER_OWNER_ADMISSION_REVIEW",
        "consumer_owner": "RESEARCH_CONSOLE",
        "consumer_admission": "NOT_GRANTED_BY_P2CTI",
        "source_presentation_authority": "NON_TRANSITIVE",
        "operational_reliance": False,
        "authority_effect": "NONE",
    }
    return {**body, "packet_sha256": canonical_sha256(body)}
