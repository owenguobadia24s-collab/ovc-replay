from __future__ import annotations

from collections.abc import Mapping, Sequence
import re
from typing import Any

from ovc.research_operations.canonical import canonical_sha256


_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_SOURCE_POLICY = {
    "SOURCE_SCIENCE": ("ECX_DMRP_RESEARCH_OPERATIONS", "UNRESOLVED_SOURCE_GENERATION"),
    "P1_SCIENTIFIC_DISPOSITION": ("OWNING_PATH1_STUDY", "UNRESOLVED_SCIENTIFIC_DISPOSITION"),
    "CANDIDATE_PROPOSAL_FREEZE_C_ADMISSION": ("DMRP_CANDIDATE_SERVICE_AND_OPERATOR", "UNRESOLVED_CANDIDATE_STATE"),
    "GAP_AND_CAPABILITY_NEED": ("RCCR", "UNRESOLVED_RCCR_STATE"),
    "EXPOSURE_AND_INDEPENDENCE": ("DMRP_EXPOSURE_INFLUENCE_RECORDS", "INDEPENDENCE_UNKNOWN"),
    "VALIDATION_ACCESS": ("PROTECTED_RESOURCE_AUTHORITY", "ACCESS_UNRESOLVED"),
    "P1CDI_IDENTITY_ACTIVITY_CURRENTNESS_LINEAGE": ("P1CDI", "UNRESOLVED_CURRENTNESS"),
    "CONSOLE_SOURCE_ADMISSION": ("RESEARCH_CONSOLE", "NOT_ADMITTED"),
    "TOPOLOGY_DEEP_LINK": ("SYSTEM_ATLAS", "UNRESOLVED_REFERENCE"),
}
_STATES = frozenset({"RESOLVED", "UNRESOLVED", "CONFLICT", "UNAVAILABLE"})


def _normalized_evidence(evidence: Mapping[str, Any]) -> dict[str, Any]:
    required = {"predicate", "owner", "source_ref", "generation_ref", "source_sha256", "resolution_state"}
    if set(evidence) != required:
        raise ValueError("source evidence must use the exact closed field set")
    if evidence["resolution_state"] not in _STATES:
        raise ValueError(f"invalid resolution_state: {evidence['resolution_state']}")
    if not _SHA256.fullmatch(str(evidence["source_sha256"])):
        raise ValueError("source_sha256 must be lowercase SHA-256")
    return {name: evidence[name] for name in sorted(required)}


def resolve_owner_predicate(
    predicate: str, evidence: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    """Resolve one high-risk predicate without recency/path/title fallback."""

    if predicate not in _SOURCE_POLICY:
        raise ValueError(f"unknown owner predicate: {predicate}")
    expected_owner, missing_reason = _SOURCE_POLICY[predicate]
    rows = [_normalized_evidence(item) for item in evidence if item.get("predicate") == predicate]
    wrong_owner = [item for item in rows if item["owner"] != expected_owner]
    if wrong_owner:
        return _resolution(predicate, expected_owner, "CONFLICT", None, ["OWNER_SEMANTIC_CONFLICT"])
    if not rows:
        return _resolution(predicate, expected_owner, "UNRESOLVED", None, [missing_reason])
    if any(item["resolution_state"] == "CONFLICT" for item in rows):
        return _resolution(predicate, expected_owner, "CONFLICT", None, ["OWNER_SEMANTIC_CONFLICT"])
    resolved = [item for item in rows if item["resolution_state"] == "RESOLVED"]
    if not resolved:
        return _resolution(predicate, expected_owner, "UNRESOLVED", None, [missing_reason])
    identities = {
        (str(item["source_ref"]), str(item["generation_ref"]), str(item["source_sha256"]))
        for item in resolved
    }
    if len(identities) != 1 or len(resolved) != len(rows):
        return _resolution(predicate, expected_owner, "CONFLICT", None, ["OWNER_SEMANTIC_CONFLICT"])
    selected = sorted(resolved, key=lambda item: tuple(str(item[name]) for name in sorted(item)))[0]
    return _resolution(predicate, expected_owner, "RESOLVED", selected, [])


def _resolution(
    predicate: str,
    owner: str,
    state: str,
    source: Mapping[str, Any] | None,
    reasons: list[str],
) -> dict[str, Any]:
    return {
        "predicate": predicate,
        "controlling_owner": owner,
        "resolution_state": state,
        "resolved_source": dict(source) if source is not None else None,
        "reason_codes": reasons,
        "decision_bearing": False,
        "authority_effect": "NONE",
    }


def build_source_frontier(
    *, frontier_id: str, resolved_at: str, owner_entries: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    if not frontier_id or not resolved_at or not owner_entries:
        raise ValueError("frontier_id, resolved_at, and owner_entries are required")
    normalized: list[dict[str, Any]] = []
    for raw in owner_entries:
        required = {"owner", "source_ref", "generation_ref", "source_sha256", "resolution_state"}
        if set(raw) != required:
            raise ValueError("source frontier entries must use the exact closed field set")
        if raw["resolution_state"] not in _STATES:
            raise ValueError(f"invalid resolution_state: {raw['resolution_state']}")
        if not _SHA256.fullmatch(str(raw["source_sha256"])):
            raise ValueError("source_sha256 must be lowercase SHA-256")
        normalized.append({key: raw[key] for key in sorted(required)})
    normalized.sort(
        key=lambda item: (
            str(item["owner"]),
            str(item["source_ref"]),
            str(item["generation_ref"]),
            str(item["source_sha256"]),
            str(item["resolution_state"]),
        )
    )
    digest = canonical_sha256(normalized)
    return {
        "record_type": "SourceFrontierManifest",
        "schema_version": "0.1",
        "frontier_id": frontier_id,
        "resolved_at": resolved_at,
        "owner_entries": normalized,
        "frontier_sha256": digest,
        "authority_effect": "NONE",
    }
