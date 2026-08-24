from __future__ import annotations

from collections.abc import Mapping, Sequence
from copy import deepcopy
from typing import Any

from ovc.research_operations.canonical import canonical_sha256

from .query import QUERY_FAMILIES

REQUIRED_QUERY_ENVELOPE_FIELDS = (
    "source_frontier_id",
    "assessment_profile_generation",
    "currentness_state",
    "visibility_state",
    "completeness_state",
    "warnings",
    "reason_trace",
)


class P1CDIProjectionError(ValueError):
    """A P1CDI consumer projection cannot preserve the producer query contract."""


def _exact_string(value: Any, name: str) -> str:
    if type(value) is not str or not value:
        raise P1CDIProjectionError(f"{name} must be a non-empty string")
    return value


def _refs(value: Sequence[str], name: str, *, allow_empty: bool = True) -> list[str]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise P1CDIProjectionError(f"{name} must be a sequence")
    rows = sorted(_exact_string(item, name) for item in value)
    if not allow_empty and not rows:
        raise P1CDIProjectionError(f"{name} must be non-empty")
    if len(rows) != len(set(rows)):
        raise P1CDIProjectionError(f"{name} must not contain duplicates")
    return rows


def _ordered_refs(value: Sequence[str], name: str) -> list[str]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise P1CDIProjectionError(f"{name} must be a sequence")
    rows = [_exact_string(item, name) for item in value]
    if len(rows) != len(set(rows)):
        raise P1CDIProjectionError(f"{name} must not contain duplicates")
    return rows


def _require_query_envelope(query_result: Mapping[str, Any]) -> None:
    if not isinstance(query_result, Mapping):
        raise P1CDIProjectionError("query_result must be an object")
    missing = [field for field in REQUIRED_QUERY_ENVELOPE_FIELDS if field not in query_result]
    if missing:
        raise P1CDIProjectionError(f"missing projection envelope fields: {missing}")
    if query_result.get("read_only") is not True:
        raise P1CDIProjectionError("P1CDI consumer projection must be read-only")
    if query_result.get("write_controls_present") is not False:
        raise P1CDIProjectionError("P1CDI query envelope contains write controls")
    if query_result.get("silent_truncation") != "FORBIDDEN":
        raise P1CDIProjectionError("silent truncation must remain forbidden")
    if query_result.get("operational_reliance") is not False:
        raise P1CDIProjectionError("WP9 cannot grant operational reliance")
    if query_result.get("authority_effect") != "NONE":
        raise P1CDIProjectionError("P1CDI consumer projection may not grant authority")


def build_console_projection(
    *,
    query_result: Mapping[str, Any],
    evidence_refs: Sequence[str] = (),
    system_atlas_refs: Sequence[str] = (),
) -> dict[str, Any]:
    _require_query_envelope(query_result)
    evidence = _refs(evidence_refs, "evidence_refs")
    atlas = _refs(system_atlas_refs, "system_atlas_refs")
    body = {
        "schema": "ovc-p1cdii-console-projection/v0.1",
        "source_id": "P1CDI",
        "query_family": _exact_string(query_result.get("query_family"), "query_family"),
        "source_frontier_id": _exact_string(query_result.get("source_frontier_id"), "source_frontier_id"),
        "assessment_profile_generation": _exact_string(
            query_result.get("assessment_profile_generation"), "assessment_profile_generation"
        ),
        "currentness_state": _exact_string(query_result.get("currentness_state"), "currentness_state"),
        "visibility_state": _exact_string(query_result.get("visibility_state"), "visibility_state"),
        "completeness_state": _exact_string(query_result.get("completeness_state"), "completeness_state"),
        "warnings": _refs(query_result.get("warnings", ()), "warnings"),
        "reason_trace": _ordered_refs(query_result.get("reason_trace", ()), "reason_trace"),
        "result": deepcopy(query_result.get("result")),
        "evidence_refs": evidence,
        "system_atlas_refs": atlas,
        "read_only": True,
        "write_controls_present": False,
        "consumer_admission_granted": False,
        "system_atlas_mutation": "DENIED",
        "operational_reliance": False,
        "authority_effect": "NONE",
    }
    return {**body, "content_sha256": canonical_sha256(body)}


def build_source_admission_packet(
    *,
    source_frontier_id: str,
    assessment_profile_generation: str,
    projection_evidence_sha256: str,
    producer_authority_refs: Sequence[str],
    query_families: Sequence[str],
    system_atlas_refs: Sequence[str] = (),
) -> dict[str, Any]:
    authority = _refs(producer_authority_refs, "producer_authority_refs", allow_empty=False)
    families = _refs(query_families, "query_families", allow_empty=False)
    unknown = sorted(set(families).difference(QUERY_FAMILIES))
    if unknown:
        raise P1CDIProjectionError(f"query_families contain unknown WP9 families: {unknown}")
    atlas = _refs(system_atlas_refs, "system_atlas_refs")
    digest = _exact_string(projection_evidence_sha256, "projection_evidence_sha256")
    if len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest):
        raise P1CDIProjectionError("projection_evidence_sha256 must be lowercase SHA-256")
    body = {
        "schema": "ovc-p1cdii-research-console-source-admission-packet/v0.1",
        "producer": "OVC-P1CDI-CONFORMANCE-v0.1",
        "source_id": "P1CDI",
        "source_frontier_id": _exact_string(source_frontier_id, "source_frontier_id"),
        "assessment_profile_generation": _exact_string(
            assessment_profile_generation, "assessment_profile_generation"
        ),
        "projection_evidence_sha256": digest,
        "producer_authority_refs": authority,
        "query_families": families,
        "system_atlas_refs": atlas,
        "presentation_contract": "READ_ONLY_EVIDENCE_PRESERVING",
        "visibility_contract": "CLASSIFY_BEFORE_INDEX_AND_PROJECTION",
        "silent_truncation": "FORBIDDEN",
        "negative_evidence_parity": "REQUIRED",
        "producer_recommendation": "READY_FOR_CONSUMER_OWNER_ADMISSION_REVIEW",
        "consumer_owner": "RESEARCH_CONSOLE",
        "consumer_admission": "NOT_GRANTED_BY_P1CDI",
        "source_presentation_authority": "NON_TRANSITIVE",
        "system_atlas_role": "REFERENCE_ONLY_DEEP_LINK_OWNER",
        "write_controls": "ABSENT",
        "operational_reliance": False,
        "authority_effect": "NONE",
    }
    return {**body, "packet_sha256": canonical_sha256(body)}
