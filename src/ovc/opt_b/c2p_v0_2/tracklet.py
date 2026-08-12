from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
from typing import Any, Mapping

from .canonical import canonical_bytes
from .chronology import validate_causal_times


class TrackletError(ValueError):
    pass


def _hash(value: Any) -> str:
    return sha256(canonical_bytes(value)).hexdigest()


def _frontier(member_ids: list[str], last_decision_id: str | None = None) -> dict[str, Any]:
    return {
        "last_candidate_id": member_ids[-1],
        "last_decision_id": last_decision_id,
        "evaluated_candidate_count": len(member_ids),
        "frontier_hash": _hash({"member_candidate_ids": member_ids, "last_decision_id": last_decision_id}),
    }


def open_tracklet(candidate: Mapping[str, Any], object_pack: Mapping[str, Any]) -> dict[str, Any]:
    if candidate["object_pack_id"] != object_pack["object_pack_id"]:
        raise TrackletError("C2P_OBJECT_PACK_MISMATCH")
    member_ids = [candidate["candidate_id"]]
    tracklet_id = _hash({
        "schema": "c2p-tracklet-identity/v0.2",
        "object_pack_id": object_pack["object_pack_id"],
        "opening_candidate_id": candidate["candidate_id"],
        "hard_scope": candidate["hard_scope"],
    })
    return {
        "schema": "c2p-tracklet/v0.2",
        "tracklet_id": tracklet_id,
        "hash_version": "sha256-canonical-json-v1",
        "object_pack_id": object_pack["object_pack_id"],
        "opening_candidate_id": candidate["candidate_id"],
        "structural_role_id": candidate["structural_role_id"],
        "geometry_kind_id": candidate["geometry_kind_id"],
        "hard_scope": deepcopy(candidate["hard_scope"]),
        "member_candidate_ids": member_ids,
        "decision_frontier": _frontier(member_ids),
        "state": "OPEN",
        "observability_state": "OBSERVED",
        "evaluation_state": "AVAILABLE",
        "market_effective_start": candidate["market_effective_start"],
        "market_effective_end": candidate["market_effective_end"],
        "first_valid_time": candidate["first_valid_time"],
        "evaluation_cutoff": candidate["evaluation_cutoff"],
        "reason_codes": [],
    }


def append_candidate(tracklet: Mapping[str, Any], candidate: Mapping[str, Any], object_pack: Mapping[str, Any], *, equally_lawful_competitor: bool = False, decision_id: str | None = None) -> dict[str, Any]:
    current = deepcopy(dict(tracklet))
    if current["state"] in {"EXPIRED", "CENSORED"}:
        raise TrackletError("C2P_TRACKLET_TERMINAL")
    if candidate["object_pack_id"] != current["object_pack_id"] or candidate["object_pack_id"] != object_pack["object_pack_id"]:
        raise TrackletError("C2P_OBJECT_PACK_MISMATCH")
    if candidate["hard_scope"] != current["hard_scope"]:
        raise TrackletError("C2P_HARD_SCOPE_MISMATCH")
    validate_causal_times(market_effective_start=candidate["market_effective_start"], market_effective_end=candidate["market_effective_end"], first_valid_time=candidate["first_valid_time"], evaluation_cutoff=candidate["evaluation_cutoff"])
    if candidate["candidate_id"] in current["member_candidate_ids"]:
        raise TrackletError("C2P_DUPLICATE_CANDIDATE")
    current["member_candidate_ids"].append(candidate["candidate_id"])
    current["decision_frontier"] = _frontier(current["member_candidate_ids"], decision_id)
    current["market_effective_end"] = candidate["market_effective_end"]
    current["evaluation_cutoff"] = candidate["evaluation_cutoff"]
    current["first_valid_time"] = max(current["first_valid_time"], candidate["first_valid_time"])
    required = int(object_pack["confirmation_contract"]["successive_member_candidates"])
    if equally_lawful_competitor:
        current["state"] = "AMBIGUOUS"
        current["evaluation_state"] = "AMBIGUOUS"
        current["reason_codes"] = ["C2P_EQUAL_LAWFUL_COMPETITOR"]
    elif len(current["member_candidate_ids"]) >= required:
        current["state"] = "CONFIRMED"
        current["evaluation_state"] = "AVAILABLE"
        current["reason_codes"] = []
    else:
        current["state"] = "OPEN"
        current["evaluation_state"] = "AVAILABLE"
        current["reason_codes"] = []
    return current


def censor_tracklet(tracklet: Mapping[str, Any], *, cutoff: str, reason: str = "C2P_SOURCE_CENSORED") -> dict[str, Any]:
    current = deepcopy(dict(tracklet))
    current["state"] = "CENSORED"
    current["observability_state"] = "CENSORED"
    current["evaluation_state"] = "NOT_EVALUABLE"
    current["evaluation_cutoff"] = cutoff
    current["reason_codes"] = [reason]
    return current


def expire_tracklet(tracklet: Mapping[str, Any], *, cutoff: str, explicit_signal: bool) -> dict[str, Any]:
    if not explicit_signal:
        raise TrackletError("C2P_EXPLICIT_EXPIRY_SIGNAL_REQUIRED")
    current = deepcopy(dict(tracklet))
    current["state"] = "EXPIRED"
    current["evaluation_cutoff"] = cutoff
    current["reason_codes"] = ["C2P_SYNTHETIC_EXPLICIT_EXPIRY"]
    return current
