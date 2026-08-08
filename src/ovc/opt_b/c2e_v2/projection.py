"""Deterministic rebuildable episode projections."""
from __future__ import annotations

from typing import Any, Mapping, Sequence

from .models import build_record


class ProjectionError(ValueError):
    pass


def project_episode(episode_id: str, records: Sequence[Mapping[str, Any]], *, as_of_time: str, first_valid_time: str) -> dict[str, Any]:
    members: set[str] = set()
    phases: set[str] = set()
    boundaries: set[str] = set()
    status = "OPEN"
    for record in records:
        schema = record.get("schema")
        if schema == "c2e_membership_delta/v0_2" and record.get("episode_id") == episode_id:
            if record.get("operation") == "ADD":
                members.add(str(record["frame_id"]))
            elif record.get("operation") == "REMOVE_TOPOLOGY_EFFECT":
                members.discard(str(record["frame_id"]))
        elif schema == "c2e_phase_segment/v0_2" and record.get("episode_id") == episode_id:
            phases.add(str(record["phase_segment_id"]))
        elif schema == "c2e_boundary_event/v0_2" and episode_id in record.get("episode_ids", []):
            boundaries.add(str(record["boundary_event_id"]))
            action = record.get("lifecycle_action")
            if action in {"CENSOR_GAP","CENSOR_RELEASE_END"}:
                status = "CENSORED"
            elif action == "TERMINATE_CONFLICT":
                status = "CONFLICTED"
            elif action == "TERMINATE":
                status = "TERMINATED"
    return build_record("episode_snapshot", {
        "episode_id": episode_id,
        "as_of_time": as_of_time,
        "first_valid_time": first_valid_time,
        "status": status,
        "member_ids": sorted(members),
        "phase_segment_ids": sorted(phases),
        "boundary_event_ids": sorted(boundaries),
        "authority": "INACTIVE_NONCANONICAL_SHADOW",
    })
