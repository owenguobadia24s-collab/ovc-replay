from __future__ import annotations

from datetime import timedelta
from typing import Any, Mapping, Sequence

from ovc.opt_b.c2e_v2.models import validate_record

from .builder import OccurrenceContextError
from .chronology import parse_rfc3339
from .models import ContextDependencyRef, OccurrenceAnchorRef

_KIND_TO_ANCHOR = {
    "episode_genesis": ("C2E_EPISODE_GENESIS", "episode_id"),
    "episode_snapshot": ("C2E_EPISODE_SNAPSHOT", "snapshot_id"),
    "phase_segment": ("C2E_PHASE_SEGMENT", "phase_segment_id"),
}


def c2e_anchor(kind: str, record: Mapping[str, Any]) -> OccurrenceAnchorRef:
    if kind not in _KIND_TO_ANCHOR:
        raise OccurrenceContextError("OC_AVAIL_ANCHOR_MISSING", f"unsupported C2E anchor kind {kind}")
    validated = validate_record(kind, record)
    anchor_kind, id_field = _KIND_TO_ANCHOR[kind]
    return OccurrenceAnchorRef(
        anchor_kind=anchor_kind,
        anchor_id=str(validated[id_field]),
        anchor_schema_id=str(validated["schema"]),
        anchor_logical_hash=str(validated["logical_hash"]),
        anchor_first_valid_time=str(validated["first_valid_time"]),
        source_release_id=str(validated.get("source_release_id") or ""),
    )


def c2e_dependency(kind: str, record: Mapping[str, Any], *, role: str = "C2E_RELATIVE", required: bool = True) -> ContextDependencyRef:
    anchor = c2e_anchor(kind, record)
    return ContextDependencyRef(
        dependency_kind=kind.upper(),
        record_id=anchor.anchor_id,
        schema_id=anchor.anchor_schema_id,
        logical_hash=anchor.anchor_logical_hash,
        first_valid_time=anchor.anchor_first_valid_time,
        dependency_role=role,
        required=required,
        source_release_id=anchor.source_release_id,
    )


def _iso_duration(delta: timedelta) -> str:
    seconds = int(delta.total_seconds())
    if seconds < 0:
        raise OccurrenceContextError("OC_TIME_BACKDATE_DENIED")
    return f"PT{seconds}S"


def episode_relative_context(
    genesis: Mapping[str, Any],
    snapshot: Mapping[str, Any],
    phases: Sequence[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    genesis_valid = validate_record("episode_genesis", genesis)
    snapshot_valid = validate_record("episode_snapshot", snapshot)
    if snapshot_valid["episode_id"] != genesis_valid["episode_id"]:
        raise OccurrenceContextError("OC_ID_ANCHOR_MUTATION", "snapshot/genesis episode mismatch")
    birth = parse_rfc3339(str(genesis_valid["birth_effective_time"]))
    as_of = parse_rfc3339(str(snapshot_valid["as_of_time"]))
    phase_records = [validate_record("phase_segment", phase) for phase in phases]
    if any(phase["episode_id"] != genesis_valid["episode_id"] for phase in phase_records):
        raise OccurrenceContextError("OC_ID_ANCHOR_MUTATION", "phase/genesis episode mismatch")
    current_phase = None
    if phase_records:
        current_phase = max(phase_records, key=lambda item: (item["first_valid_time"], item["phase_segment_id"]))
    status = str(snapshot_valid["status"])
    censoring = None
    completion = None
    if status == "CENSORED":
        censoring = {"status": "CENSORED", "first_valid_time": snapshot_valid["first_valid_time"]}
    elif status in {"TERMINATED", "CONFLICTED"}:
        completion = {"status": status, "first_valid_time": snapshot_valid["first_valid_time"]}
    return {
        "episode_id": genesis_valid["episode_id"],
        "episode_genesis_ref": {
            "record_id": genesis_valid["episode_id"],
            "logical_hash": genesis_valid["logical_hash"],
            "first_valid_time": genesis_valid["first_valid_time"],
            "boundary_pack_id": genesis_valid["boundary_pack_id"],
        },
        "snapshot_ref": {
            "record_id": snapshot_valid["snapshot_id"],
            "logical_hash": snapshot_valid["logical_hash"],
            "first_valid_time": snapshot_valid["first_valid_time"],
        },
        "elapsed_duration": _iso_duration(as_of - birth),
        "elapsed_eligible_observation_count": len(snapshot_valid["member_ids"]),
        "current_phase_ref": None if current_phase is None else {
            "record_id": current_phase["phase_segment_id"],
            "logical_hash": current_phase["logical_hash"],
            "first_valid_time": current_phase["first_valid_time"],
        },
        "lifecycle_status": status,
        "censoring_context": censoring,
        "completion_context": completion,
        "as_of_time": snapshot_valid["as_of_time"],
    }
