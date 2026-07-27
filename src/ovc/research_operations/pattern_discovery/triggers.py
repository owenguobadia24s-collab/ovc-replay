from __future__ import annotations

from typing import Any, Iterable, Mapping

from ovc.research_operations.canonical import canonical_sha256

from .models import OPERATION_MODES, PatternDiscoveryError, parse_utc


TRIGGER_VERSION = "PD.TRIGGERS.v0.1"
PRECEDENCE = (
    "QUALITY_OR_INCIDENT",
    "CROSS_SCALE_CONFLICT",
    "STRUCTURAL_TRANSITION",
    "PERSISTENCE_OR_INSTABILITY",
    "NOVELTY",
    "RECURRENCE",
    "CONTROL",
)
_PRECEDENCE_INDEX = {family: index for index, family in enumerate(PRECEDENCE)}


DEFAULT_TRIGGER_FAMILIES = {
    "TR-LOC-001": "STRUCTURAL_TRANSITION",
    "TR-INT-001": "STRUCTURAL_TRANSITION",
    "TR-INT-002": "STRUCTURAL_TRANSITION",
    "TR-ORG-001": "STRUCTURAL_TRANSITION",
    "TR-XSC-001": "CROSS_SCALE_CONFLICT",
    "TR-XSC-002": "CROSS_SCALE_CONFLICT",
    "TR-PER-001": "PERSISTENCE_OR_INSTABILITY",
    "TR-INS-001": "PERSISTENCE_OR_INSTABILITY",
    "TR-NOV-001": "NOVELTY",
    "TR-NOV-002": "NOVELTY",
    "TR-REC-001": "RECURRENCE",
    "TR-CTL-001": "CONTROL",
}


def build_trigger_event(
    *,
    trigger_id: str,
    reason_code: str,
    source_transitions: Iterable[Mapping[str, Any]],
    operation_mode: str,
    closure_profile_id: str,
    rate_limit_group: str,
    trigger_version: str = TRIGGER_VERSION,
    first_valid_at: str | None = None,
) -> dict[str, Any]:
    if operation_mode not in OPERATION_MODES:
        raise PatternDiscoveryError(f"unsupported operation mode: {operation_mode}")
    transitions = list(source_transitions)
    if not transitions:
        raise PatternDiscoveryError("TriggerEvent requires at least one TransitionRecord")
    transition_ids: list[str] = []
    times: list[str] = []
    for transition in transitions:
        transition_id = transition.get("transition_id")
        transition_time = transition.get("first_valid_at")
        if not isinstance(transition_id, str) or not transition_id:
            raise PatternDiscoveryError("source transition requires transition_id")
        if not isinstance(transition_time, str):
            raise PatternDiscoveryError("source transition requires first_valid_at")
        parse_utc(transition_time)
        transition_ids.append(transition_id)
        times.append(transition_time)
    if len(set(transition_ids)) != len(transition_ids):
        raise PatternDiscoveryError("source transition IDs must be unique")
    resolved_time = first_valid_at or max(times, key=parse_utc)
    parse_utc(resolved_time)
    if any(parse_utc(value) > parse_utc(resolved_time) for value in times):
        raise PatternDiscoveryError("TriggerEvent cannot predate a source transition")
    identity = {
        "trigger_id": trigger_id,
        "trigger_version": trigger_version,
        "first_valid_at": resolved_time,
        "reason_code": reason_code,
        "source_transition_ids": sorted(transition_ids),
        "operation_mode": operation_mode,
        "closure_profile_id": closure_profile_id,
        "rate_limit_group": rate_limit_group,
    }
    return {
        "record_type": "TriggerEvent",
        "trigger_event_id": f"PDTE-{canonical_sha256(identity)[:32]}",
        "trigger_id": trigger_id,
        "trigger_version": trigger_version,
        "first_valid_at": resolved_time,
        "reason_code": reason_code,
        "source_transition_ids": sorted(transition_ids),
        "operation_mode": operation_mode,
        "closure_profile_id": closure_profile_id,
        "rate_limit_group": rate_limit_group,
        "primary": False,
    }


def mark_display_primary(
    events: Iterable[Mapping[str, Any]],
    *,
    trigger_families: Mapping[str, str] | None = None,
) -> list[dict[str, Any]]:
    """Return all TriggerEvents with exactly one display-primary flag.

    Precedence changes presentation only. No event is removed or rewritten in the
    append-only event ledger.
    """

    family_map = dict(DEFAULT_TRIGGER_FAMILIES)
    if trigger_families:
        family_map.update(trigger_families)
    copied = [dict(item) for item in events]
    if not copied:
        return []

    def order(item: Mapping[str, Any]) -> tuple[int, str, str]:
        family = family_map.get(str(item.get("trigger_id")), "CONTROL")
        return (
            _PRECEDENCE_INDEX.get(family, len(PRECEDENCE)),
            str(item.get("first_valid_at")),
            str(item.get("trigger_event_id")),
        )

    primary_id = min(copied, key=order)["trigger_event_id"]
    for event in copied:
        event["primary"] = event["trigger_event_id"] == primary_id
    return sorted(copied, key=order)
