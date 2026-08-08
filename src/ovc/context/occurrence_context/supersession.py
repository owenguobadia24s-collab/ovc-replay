from __future__ import annotations

from typing import Any, Mapping

from .chronology import parse_rfc3339
from .serialization import logical_hash, sha256_payload


def create_supersession(
    prior: Mapping[str, Any],
    successor: Mapping[str, Any],
    reason_code: str,
    changed_dependency_ids: list[str] | None = None,
    changed_registry_ids: list[str] | None = None,
) -> dict[str, Any]:
    if prior["occurrence_key"] != successor["occurrence_key"]:
        raise ValueError("OC_ID_ANCHOR_MUTATION")
    if prior["occurrence_context_id"] == successor["occurrence_context_id"]:
        raise ValueError("OC_ID_LOGICAL_HASH_MISMATCH")
    if parse_rfc3339(successor["first_valid_time"]) < parse_rfc3339(prior["first_valid_time"]):
        raise ValueError("OC_TIME_BACKDATE_DENIED")
    payload = {
        "occurrence_key": prior["occurrence_key"],
        "prior_occurrence_context_id": prior["occurrence_context_id"],
        "successor_occurrence_context_id": successor["occurrence_context_id"],
        "reason_code": reason_code,
        "changed_dependency_ids": sorted(set(changed_dependency_ids or [])),
        "changed_registry_ids": sorted(set(changed_registry_ids or [])),
        "first_valid_time": successor["first_valid_time"],
        "authority_effect": "NONE",
    }
    result = {"supersession_id": sha256_payload("OVC.OCCURRENCE_CONTEXT.SUPERSESSION", payload), **payload}
    result["logical_hash"] = logical_hash(result)
    return result
