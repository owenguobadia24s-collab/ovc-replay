from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from ovc.research_operations.canonical import canonical_sha256

PROJECTIONS = frozenset({"PATH1_SAFE", "PATH2_FULL", "CROSS_MODE_POST_FREEZE", "RCCR_SOURCE"})
PATH1_FORBIDDEN = frozenset({"PATH2_PREDICATE", "PATH2_EXAMPLE", "PATH2_FALSIFIER", "PATH2_PARAMETER_BOUNDARY", "PATH2_RESTRICTED_NEIGHBOURHOOD"})


class FirewallError(ValueError):
    pass


def _evidence_id(record: Mapping[str, Any]) -> str:
    value = record.get("evidence_id")
    if type(value) is not str or not value:
        raise FirewallError("exact evidence_id is required")
    return value


def project_record(record: Mapping[str, Any], *, projection: str) -> dict[str, Any]:
    if projection not in PROJECTIONS:
        raise FirewallError("unknown projection")
    if not isinstance(record, Mapping):
        raise FirewallError("record must be a mapping")
    evidence_id = _evidence_id(record)
    information_class = record.get("information_class")
    visibility = record.get("visibility", "RESTRICTED")
    if visibility not in {"PUBLIC_SAFE", "PATH1_SAFE", "PATH2_RESTRICTED", "CROSS_MODE_POST_FREEZE", "RCCR_SOURCE_ONLY"}:
        return _deny(evidence_id, projection, "VISIBILITY_UNRESOLVED")

    if projection == "PATH1_SAFE":
        if information_class in PATH1_FORBIDDEN or visibility in {"PATH2_RESTRICTED", "CROSS_MODE_POST_FREEZE"}:
            return _deny(evidence_id, projection, "PATH1_RESTRICTED_INFORMATION_DENIED")
    elif projection == "PATH2_FULL":
        if information_class == "PATH1_UNFROZEN_CANDIDATE" and not _exact_exposure(record):
            return _deny(evidence_id, projection, "PATH1_UNFROZEN_CANDIDATE_DENIED")
    elif projection == "CROSS_MODE_POST_FREEZE":
        if record.get("candidate_frozen") is not True:
            return _deny(evidence_id, projection, "CANDIDATE_NOT_FROZEN")
        if not _exact_exposure(record):
            return _deny(evidence_id, projection, "EXPOSURE_EVIDENCE_MISSING")
        if not _exact_correspondence(record):
            return _deny(evidence_id, projection, "FORMAL_CORRESPONDENCE_MISSING")
    elif projection == "RCCR_SOURCE":
        if record.get("owner_object_type") == "THEORY_SEED" and record.get("decision_bearing") is True:
            return _deny(evidence_id, projection, "RAW_SEED_NOT_DECISION_BEARING_RCCR_SOURCE")
        if record.get("owner_object_type") not in {"THEORY_RECORD", "RESEARCH_PROTOCOL", "EXPERIMENT_RECORD", "RCCR_NEED_RECORD"}:
            return _deny(evidence_id, projection, "RCCR_SOURCE_TYPE_NOT_ADMITTED")

    safe = {key: value for key, value in record.items() if key not in {"restricted_payload", "secret", "raw_path2_payload"}}
    safe["projection"] = projection
    safe["admitted"] = True
    safe["authority_effect"] = "NONE"
    safe["scientific_inference"] = "NONE"
    safe["warnings"] = sorted(set(record.get("warnings", [])))
    safe["projection_sha256"] = canonical_sha256({key: value for key, value in safe.items() if key != "projection_sha256"})
    return safe


def _exact_exposure(record: Mapping[str, Any]) -> bool:
    evidence = record.get("dmrp_exposure_evidence")
    return isinstance(evidence, Mapping) and type(evidence.get("record_id")) is str and bool(evidence.get("record_id")) and evidence.get("status") == "RECORDED"


def _exact_correspondence(record: Mapping[str, Any]) -> bool:
    evidence = record.get("dmrp_correspondence_evidence")
    return isinstance(evidence, Mapping) and type(evidence.get("record_id")) is str and bool(evidence.get("record_id")) and evidence.get("status") == "FORMAL"


def _deny(evidence_id: str, projection: str, reason: str) -> dict[str, Any]:
    body = {"evidence_id": evidence_id, "projection": projection, "admitted": False, "reason": reason, "authority_effect": "NONE", "scientific_inference": "NONE", "payload": None}
    return {**body, "projection_sha256": canonical_sha256(body)}


def project_population(records: Sequence[Mapping[str, Any]], *, projection: str) -> dict[str, Any]:
    rows = [project_record(record, projection=projection) for record in records]
    rows.sort(key=lambda row: row["evidence_id"])
    denied = [row["evidence_id"] for row in rows if not row["admitted"]]
    admitted = [row for row in rows if row["admitted"]]
    body = {"projection": projection, "rows": admitted, "denied_evidence_ids": denied, "complete": len(denied) == 0, "negative_reachability_proved": all(row.get("payload") is None for row in rows if not row["admitted"]), "authority_effect": "NONE", "operational_reliance": False}
    return {**body, "content_sha256": canonical_sha256(body)}
