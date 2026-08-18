from __future__ import annotations

from collections.abc import Mapping

from ovc.research_operations.canonical import canonical_sha256
from .source_resolution import REQUIRED_CURRENTNESS_OWNERS


def _frontier_state(frontier: Mapping[str, object]) -> str:
    if frontier.get("record_type") != "SourceFrontierManifest":
        raise ValueError("SourceFrontierManifest is required")
    if not frontier.get("frontier_id") or not frontier.get("frontier_sha256"):
        raise ValueError("source frontier identity is incomplete")
    entries = frontier.get("owner_entries")
    if not isinstance(entries, list) or not entries:
        raise ValueError("source frontier owner_entries must be non-empty")
    if any(not isinstance(item, Mapping) for item in entries):
        raise ValueError("source frontier entries must be objects")
    required_owners = frontier.get("required_owners")
    missing = frontier.get("missing_required_owners")
    duplicates = frontier.get("duplicate_required_owners")
    reason_codes = frontier.get("reason_codes")
    completeness_state = frontier.get("completeness_state")
    if not all(isinstance(value, list) for value in (required_owners, missing, duplicates, reason_codes)):
        raise ValueError("source frontier completeness fields must be arrays")
    if required_owners != list(REQUIRED_CURRENTNESS_OWNERS):
        raise ValueError("source frontier required owner set is not exact")
    owners = [str(item.get("owner")) for item in entries]
    expected_missing = sorted(set(REQUIRED_CURRENTNESS_OWNERS) - set(owners))
    expected_duplicates = sorted(
        owner for owner in REQUIRED_CURRENTNESS_OWNERS if owners.count(owner) > 1
    )
    states = {str(item.get("resolution_state")) for item in entries}
    if states - {"RESOLVED", "UNRESOLVED", "CONFLICT", "UNAVAILABLE"}:
        raise ValueError(f"source frontier has invalid resolution states: {sorted(states)}")
    if expected_duplicates or "CONFLICT" in states:
        expected_state, expected_reasons = "CONFLICT", ["OWNER_SEMANTIC_CONFLICT"]
    elif expected_missing or states - {"RESOLVED"}:
        expected_state, expected_reasons = "UNRESOLVED", ["UNRESOLVED_CURRENTNESS"]
    else:
        expected_state, expected_reasons = "COMPLETE", []
    if (
        missing != expected_missing
        or duplicates != expected_duplicates
        or completeness_state != expected_state
        or reason_codes != expected_reasons
    ):
        raise ValueError("source frontier completeness does not bind owner_entries")
    identity = {
        "required_owners": required_owners,
        "owner_entries": entries,
        "missing_required_owners": missing,
        "duplicate_required_owners": duplicates,
        "completeness_state": completeness_state,
        "reason_codes": reason_codes,
    }
    if canonical_sha256(identity) != frontier["frontier_sha256"]:
        raise ValueError("source frontier hash does not bind owner_entries")
    return str(completeness_state)


def evaluate_two_point_currentness(
    *, generation_id: str, prebuild_frontier: Mapping[str, object], prepublish_frontier: Mapping[str, object]
) -> dict[str, object]:
    """Evaluate currentness while keeping WP2 output non-decision-bearing."""

    if not generation_id:
        raise ValueError("generation_id must be non-empty")
    pre_state = _frontier_state(prebuild_frontier)
    post_state = _frontier_state(prepublish_frontier)
    pre_ref = str(prebuild_frontier.get("frontier_id", ""))
    post_ref = str(prepublish_frontier.get("frontier_id", ""))
    equal = (
        bool(prebuild_frontier.get("frontier_sha256"))
        and prebuild_frontier.get("frontier_sha256") == prepublish_frontier.get("frontier_sha256")
    )
    if "CONFLICT" in {pre_state, post_state}:
        currentness, reasons = "CONFLICT", ["OWNER_SEMANTIC_CONFLICT"]
    elif "UNRESOLVED" in {pre_state, post_state}:
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
