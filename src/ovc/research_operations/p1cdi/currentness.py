from __future__ import annotations

from collections.abc import Mapping

from ovc.research_operations.canonical import canonical_sha256


def _states(frontier: Mapping[str, object]) -> set[str]:
    if frontier.get("record_type") != "SourceFrontierManifest":
        raise ValueError("SourceFrontierManifest is required")
    if not frontier.get("frontier_id") or not frontier.get("frontier_sha256"):
        raise ValueError("source frontier identity is incomplete")
    entries = frontier.get("owner_entries")
    if not isinstance(entries, list) or not entries:
        raise ValueError("source frontier owner_entries must be non-empty")
    if any(not isinstance(item, Mapping) for item in entries):
        raise ValueError("source frontier entries must be objects")
    if canonical_sha256(entries) != frontier["frontier_sha256"]:
        raise ValueError("source frontier hash does not bind owner_entries")
    states = {str(item.get("resolution_state")) for item in entries}
    if states - {"RESOLVED", "UNRESOLVED", "CONFLICT", "UNAVAILABLE"}:
        raise ValueError(f"source frontier has invalid resolution states: {sorted(states)}")
    return states


def evaluate_two_point_currentness(
    *, generation_id: str, prebuild_frontier: Mapping[str, object], prepublish_frontier: Mapping[str, object]
) -> dict[str, object]:
    """Evaluate currentness while keeping WP2 output non-decision-bearing."""

    if not generation_id:
        raise ValueError("generation_id must be non-empty")
    pre_states = _states(prebuild_frontier)
    post_states = _states(prepublish_frontier)
    pre_ref = str(prebuild_frontier.get("frontier_id", ""))
    post_ref = str(prepublish_frontier.get("frontier_id", ""))
    equal = (
        bool(prebuild_frontier.get("frontier_sha256"))
        and prebuild_frontier.get("frontier_sha256") == prepublish_frontier.get("frontier_sha256")
    )
    if "CONFLICT" in pre_states | post_states:
        currentness, reasons = "CONFLICT", ["OWNER_SEMANTIC_CONFLICT"]
    elif (pre_states | post_states) - {"RESOLVED"}:
        currentness, reasons = "UNRESOLVED", ["UNRESOLVED_CURRENTNESS"]
    elif not equal:
        currentness, reasons = "STALE", ["SOURCE_FRONTIER_MOVED"]
    else:
        currentness, reasons = "CURRENT", []
    return {
        "record_type": "CurrentnessResolutionRecord",
        "schema_version": "0.1",
        "resolution_id": f"p1:currentness:{generation_id}",
        "generation_id": generation_id,
        "prebuild_frontier_ref": pre_ref,
        "prepublish_frontier_ref": post_ref,
        "frontiers_equal": equal,
        "currentness": currentness,
        "reason_codes": reasons,
        "decision_bearing": False,
        "authority_effect": "NONE",
    }


def require_g2_alg_for_pointer(*, g2_alg_status: str) -> None:
    if g2_alg_status != "PASS":
        raise PermissionError("P1CDII-G2-ALG PASS is required before any Generation-0 current pointer")
