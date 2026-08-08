"""Read-only downstream producer views for C2E v0.2.

C2E owns stable stream identity/chronology only. Representation, normalization,
distance, family discovery, semantic interpretation and outcomes remain consumer-owned.
"""
from __future__ import annotations

from typing import Any, Mapping, Sequence

from .models import build_record


class DownstreamBoundaryError(ValueError):
    pass


def assert_base_episode_key(value: Any) -> str:
    if isinstance(value, Mapping):
        if value.get("schema") == "c2e_remap_record/v0_2" or value.get("comparison_only") is True:
            raise DownstreamBoundaryError("C2E_REMAP_IDENTITY_USE_DENIED")
        value = value.get("episode_id")
    text = str(value)
    if text.startswith("C2E.REMAP.") or not text.startswith("C2E.EPISODE."):
        raise DownstreamBoundaryError("C2E_REMAP_IDENTITY_USE_DENIED")
    return text


def build_sri_handoff(
    *,
    genesis: Mapping[str, Any],
    snapshot: Mapping[str, Any],
    records: Sequence[Mapping[str, Any]],
    first_valid_time: str,
) -> dict[str, Any]:
    episode_id = assert_base_episode_key(genesis)
    if snapshot.get("episode_id") != episode_id:
        raise DownstreamBoundaryError("SRI_SNAPSHOT_EPISODE_MISMATCH")
    phase_refs: list[str] = []
    boundary_refs: list[str] = []
    lineage_refs: list[str] = []
    membership_refs: list[str] = []
    for item in records:
        schema = item.get("schema")
        if schema == "c2e_phase_segment/v0_2" and item.get("episode_id") == episode_id:
            phase_refs.append(str(item["phase_segment_id"]))
        elif schema == "c2e_boundary_event/v0_2" and episode_id in item.get("episode_ids", []):
            boundary_refs.append(str(item["boundary_event_id"]))
        elif schema == "c2e_lineage_edge/v0_2" and episode_id in {item.get("parent_episode_id"), item.get("child_episode_id")}:
            lineage_refs.append(str(item["lineage_edge_id"]))
        elif schema == "c2e_membership_delta/v0_2" and item.get("episode_id") == episode_id:
            membership_refs.append(str(item["membership_delta_id"]))
    return build_record(
        "sri_handoff",
        {
            "episode_id": episode_id,
            "boundary_pack_id": genesis["boundary_pack_id"],
            "source_release_id": genesis["source_release_id"],
            "scope_id": genesis["scope_id"],
            "scale_id": genesis["scale_id"],
            "side": genesis["side"],
            "status": snapshot["status"],
            "genesis_ref": genesis["episode_id"],
            "snapshot_ref": snapshot["snapshot_id"],
            "phase_refs": sorted(phase_refs),
            "boundary_refs": sorted(boundary_refs),
            "lineage_refs": sorted(lineage_refs),
            "membership_refs": sorted(membership_refs),
            "availability": "AVAILABLE",
            "first_valid_time": first_valid_time,
            "authority": "READ_ONLY_PRODUCER_HANDOFF",
        },
    )
