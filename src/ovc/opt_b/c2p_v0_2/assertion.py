from __future__ import annotations

from hashlib import sha256
from typing import Any, Iterable, Mapping

from .canonical import canonical_bytes


class AssertionGenesisError(ValueError):
    pass


def _hash(payload: Any) -> str:
    return sha256(canonical_bytes(payload)).hexdigest()


def create_object_assertion(
    tracklet: Mapping[str, Any],
    match_decision: Mapping[str, Any],
    object_pack: Mapping[str, Any],
    *,
    existing_assertion_ids: Iterable[str] = (),
) -> dict[str, Any]:
    if object_pack.get("status") != "SYNTHETIC_ONLY_NONEMPIRICAL" or object_pack.get("real_source_forbidden") is not True:
        raise AssertionGenesisError("C2P_WP3_SYNTHETIC_PACK_REQUIRED")
    if tracklet.get("object_pack_id") != object_pack.get("object_pack_id") or match_decision.get("object_pack_id") != object_pack.get("object_pack_id"):
        raise AssertionGenesisError("C2P_OBJECT_PACK_MISMATCH")
    if tracklet.get("state") != "CONFIRMED":
        raise AssertionGenesisError("C2P_TRACKLET_NOT_CONFIRMED")
    if match_decision.get("terminal_decision") != "NEW":
        raise AssertionGenesisError("C2P_GENESIS_REQUIRES_NEW_MATCH_DECISION")
    member_ids = list(tracklet.get("member_candidate_ids", ()))
    if not member_ids:
        raise AssertionGenesisError("C2P_GENESIS_EVIDENCE_REQUIRED")
    if len(member_ids) != len(set(member_ids)):
        raise AssertionGenesisError("C2P_DUPLICATE_GENESIS_EVIDENCE")
    if match_decision.get("candidate_id") != member_ids[-1]:
        raise AssertionGenesisError("C2P_GENESIS_DECISION_CANDIDATE_MISMATCH")

    first_valid_identity_time = max(str(tracklet["first_valid_time"]), str(match_decision["first_valid_time"]))
    evaluation_cutoff = min(str(tracklet["evaluation_cutoff"]), str(match_decision["evaluation_cutoff"]))
    if first_valid_identity_time > evaluation_cutoff:
        raise AssertionGenesisError("C2P_GENESIS_FVT_AFTER_CUTOFF")

    identity_payload = {
        "hash_version": "sha256-canonical-json-v1",
        "object_pack_id": object_pack["object_pack_id"],
        "structural_role_id": tracklet["structural_role_id"],
        "geometry_kind_id": tracklet["geometry_kind_id"],
        "hard_scope": tracklet["hard_scope"],
        "immutable_genesis_evidence_ids": member_ids,
        "genesis_match_decision_id": match_decision["decision_id"],
        "first_valid_identity_time": first_valid_identity_time,
    }
    object_assertion_id = _hash(identity_payload)
    if object_assertion_id in set(existing_assertion_ids):
        raise AssertionGenesisError("C2P_DUPLICATE_ASSERTION_GENESIS")

    genesis_event_id = _hash({
        "schema": "c2p-assertion-genesis-event-reference/v0.2",
        "object_assertion_id": object_assertion_id,
        "object_pack_id": object_pack["object_pack_id"],
        "genesis_match_decision_id": match_decision["decision_id"],
        "first_valid_identity_time": first_valid_identity_time,
    })
    return {
        "schema": "c2p-object-assertion/v0.2",
        "object_assertion_id": object_assertion_id,
        "hash_version": "sha256-canonical-json-v1",
        "object_pack_id": object_pack["object_pack_id"],
        "structural_role_id": tracklet["structural_role_id"],
        "geometry_kind_id": tracklet["geometry_kind_id"],
        "hard_scope": dict(tracklet["hard_scope"]),
        "immutable_genesis_evidence_ids": member_ids,
        "genesis_match_decision_id": match_decision["decision_id"],
        "genesis_event_id": genesis_event_id,
        "first_valid_identity_time": first_valid_identity_time,
        "lifecycle_state": "ACTIVE",
    }
