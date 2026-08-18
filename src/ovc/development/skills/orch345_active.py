from __future__ import annotations

from typing import Any, Mapping, Sequence

from ovc.development.identity import canonical_sha256
from ovc.development.skills.orch345 import (
    LOW_RISK_PACKET_CLASS,
    OPERATOR_GATE_CLASSES,
    PARALLEL_BUILD_CLASS,
    SERIAL_CLASS,
    SERIAL_INTEGRATION_POLICY,
    build_packet_train_plan,
    build_portfolio_schedule,
    classify_packet_pair,
)
from ovc.development.skills.orch345_diagnostics import (
    build_orch3_decision_receipt,
    build_orch4_decision_receipt,
    build_orch5_decision_receipt,
)

DEFAULT_MAX_PARALLEL_BUILDS = 4
DEFAULT_MAX_TRAIN_PACKETS = 8
DEFAULT_MAX_REQUEUE_ATTEMPTS = 2
FRONTIER_RECOMPOSITION_REASON_CODES = {
    "PREDECESSOR_MOVED",
    "OVC_BASE_MOVED_BEFORE_READINESS",  # historical input alias
    "OVC_BASE_MOVED_DURING_READINESS",  # historical input alias
    "MAIN_ADVANCED_AFTER_ASSURANCE",
}
AUTO_REQUEUE_REASON_CODES = FRONTIER_RECOMPOSITION_REASON_CODES


def _require_active(authority_resolution: Mapping[str, Any]) -> None:
    if authority_resolution.get("status") != "ACTIVE_AUTHORIZED":
        raise PermissionError("DSAI2-G3 bounded ORCH-3/4/5 authority is not active")
    if authority_resolution.get("record_present_on_main") is not True:
        raise PermissionError("DSAI2-G3 authority record is not present on main")


def _active_record(schema: str, role: str, payload: Mapping[str, Any]) -> dict[str, Any]:
    logical = dict(payload)
    return {
        "schema": schema,
        **logical,
        "record_id": canonical_sha256(logical, role=role),
        "authority_effect": "BOUNDED_ORCH345_EXECUTION",
    }


def build_authorized_packet_train(
    *,
    authority_resolution: Mapping[str, Any],
    programme_id: str,
    packets: Sequence[Mapping[str, Any]],
    completed_packet_ids: Sequence[str] = (),
    max_packets: int | None = DEFAULT_MAX_TRAIN_PACKETS,
) -> dict[str, Any]:
    _require_active(authority_resolution)
    if max_packets is None:
        max_packets = DEFAULT_MAX_TRAIN_PACKETS
    if max_packets > DEFAULT_MAX_TRAIN_PACKETS:
        raise PermissionError(
            f"ORCH-3 train depth exceeds active operational cap {DEFAULT_MAX_TRAIN_PACKETS}"
        )
    plan = build_packet_train_plan(
        programme_id=programme_id,
        packets=packets,
        completed_packet_ids=completed_packet_ids,
        max_packets=max_packets,
    )
    if plan.get("status") == "STOP_OPERATOR":
        raise PermissionError("ORCH-3 packet train reached an operator-required boundary")
    active = _active_record(
        "ovc-dsai2-orch3-authorized-packet-train/v2",
        "DSAI2_ORCH3_AUTHORIZED_PACKET_TRAIN",
        {
            "programme_id": programme_id,
            "selected_packet_ids": list(plan.get("selected_packet_ids", [])),
            "waiting": list(plan.get("waiting", [])),
            "operator_boundaries": list(plan.get("operator_boundaries", [])),
            "max_train_packets": max_packets,
            "execution_mode": "ACTIVE_BOUNDED",
            "integration_policy": SERIAL_INTEGRATION_POLICY,
            "parallel_merge": False,
            "source_plan_id": plan.get("record_id"),
        },
    )
    active["diagnostic_receipt"] = build_orch3_decision_receipt(
        source_execution_record=active,
        source_plan=plan,
        candidate_packet_count=len(packets),
    )
    return active


def authorize_parallel_build_pair(
    *,
    authority_resolution: Mapping[str, Any],
    left: Mapping[str, Any],
    right: Mapping[str, Any],
) -> dict[str, Any]:
    _require_active(authority_resolution)
    pair = classify_packet_pair(left, right)
    admitted = pair.get("classification") == PARALLEL_BUILD_CLASS
    active = _active_record(
        "ovc-dsai2-orch4-parallel-build-admission/v1",
        "DSAI2_ORCH4_PARALLEL_BUILD_ADMISSION",
        {
            "left_packet_id": str(left.get("packet_id", "")),
            "right_packet_id": str(right.get("packet_id", "")),
            "classification": pair.get("classification", SERIAL_CLASS),
            "reason_codes": list(pair.get("reason_codes", [])),
            "admission": "PARALLEL_BUILD_ADMITTED_SERIAL_INTEGRATION_ONLY" if admitted else "SERIAL_REQUIRED",
            "integration_policy": SERIAL_INTEGRATION_POLICY,
            "parallel_merge": False,
            "source_classification_id": pair.get("record_id"),
        },
    )
    active["diagnostic_receipt"] = build_orch4_decision_receipt(
        source_execution_record=active,
        source_classification=pair,
    )
    return active


def build_authorized_portfolio_schedule(
    *,
    authority_resolution: Mapping[str, Any],
    packets: Sequence[Mapping[str, Any]],
    completed_packet_ids: Sequence[str] = (),
    newly_completed_packet_ids: Sequence[str] = (),
    max_parallel: int = DEFAULT_MAX_PARALLEL_BUILDS,
) -> dict[str, Any]:
    _require_active(authority_resolution)
    if max_parallel > DEFAULT_MAX_PARALLEL_BUILDS:
        raise PermissionError(
            f"ORCH-5 parallel build slots exceed active operational cap {DEFAULT_MAX_PARALLEL_BUILDS}"
        )
    schedule = build_portfolio_schedule(
        packets=packets,
        completed_packet_ids=completed_packet_ids,
        max_parallel=max_parallel,
    )
    active = _active_record(
        "ovc-dsai2-orch5-authorized-portfolio-schedule/v2",
        "DSAI2_ORCH5_AUTHORIZED_PORTFOLIO_SCHEDULE",
        {
            "selected_packet_ids": list(schedule.get("selected_packet_ids", [])),
            "selected_programme_ids": list(schedule.get("selected_programme_ids", [])),
            "waiting": list(schedule.get("waiting", [])),
            "blocked": list(schedule.get("blocked", [])),
            "operator_wait": list(schedule.get("operator_wait", [])),
            "max_parallel_builds": max_parallel,
            "execution_mode": "ACTIVE_BOUNDED",
            "dispatch_authority": "ALREADY_AUTHORIZED_LOW_RISK_PACKETS_ONLY",
            "integration_policy": SERIAL_INTEGRATION_POLICY,
            "parallel_merge": False,
            "source_schedule_id": schedule.get("record_id"),
        },
    )
    active["diagnostic_receipt"] = build_orch5_decision_receipt(
        source_execution_record=active,
        source_schedule=schedule,
        packets=packets,
        completed_packet_ids=completed_packet_ids,
        newly_completed_packet_ids=newly_completed_packet_ids,
    )
    return active


def build_authorized_requeue_reconciliation(
    *,
    authority_resolution: Mapping[str, Any],
    packet: Mapping[str, Any],
    failure_reason: str,
    attempt: int,
    previous_base: str,
    current_main: str,
    write_set_changed: bool = False,
    semantic_owner_changed: bool = False,
    authority_surface_changed: bool = False,
    frozen_surface_changed: bool = False,
) -> dict[str, Any]:
    """Return a fail-closed same-PIP frontier recomposition decision.

    Physical-main movement is no longer a request to construct a fresh branch or
    replacement PR.  For an unchanged low-risk packet it keeps the source head and
    PIP, recomputes VIT placement on current main, reuses A0, and renews A1/A2.
    Semantic, authority, frozen-surface or write-set drift still stops serially.
    """
    _require_active(authority_resolution)
    packet_id = str(packet.get("packet_id", "")).strip()
    if not packet_id:
        raise ValueError("packet_id is required")
    if attempt < 1:
        raise ValueError("attempt must be positive")

    reason = str(failure_reason).upper().strip()
    gate_class = str(packet.get("gate_class", "AUTO_EXECUTABLE")).upper()
    authority_delta = str(packet.get("authority_delta", "NONE")).upper()
    packet_class = str(packet.get("packet_class", "")).upper()

    blockers: list[str] = []
    if reason not in FRONTIER_RECOMPOSITION_REASON_CODES:
        blockers.append("FAILURE_REASON_NOT_FRONTIER_RECOMPOSITION_ELIGIBLE")
    if packet_class != LOW_RISK_PACKET_CLASS:
        blockers.append("PACKET_CLASS_NOT_FRONTIER_RECOMPOSITION_ELIGIBLE")
    if gate_class in OPERATOR_GATE_CLASSES:
        blockers.append("OPERATOR_GATE_BOUNDARY")
    if authority_delta != "NONE":
        blockers.append("NON_NONE_AUTHORITY_DELTA")
    if not previous_base or not current_main:
        blockers.append("BASE_IDENTITY_MISSING")
    elif previous_base == current_main:
        blockers.append("MAIN_HAS_NOT_ADVANCED")
    if write_set_changed:
        blockers.append("WRITE_SET_DRIFT")
    if semantic_owner_changed:
        blockers.append("SEMANTIC_OWNER_DRIFT")
    if authority_surface_changed:
        blockers.append("AUTHORITY_SURFACE_DRIFT")
    if frozen_surface_changed:
        blockers.append("FROZEN_SURFACE_DRIFT")

    action = (
        "RECOMPOSE_SAME_PIP_CURRENT_FRONTIER"
        if not blockers
        else "STOP_SERIAL_REQUIRED"
    )
    return _active_record(
        "ovc-dsai2-orch345-frontier-recomposition/v2",
        "DSAI2_ORCH345_FRONTIER_RECOMPOSITION",
        {
            "packet_id": packet_id,
            "failure_reason": reason,
            "attempt": attempt,
            "max_auto_requeue_attempts": None,
            "previous_base": previous_base,
            "current_main": current_main,
            "action": action,
            "blockers": sorted(set(blockers)),
            "same_pr_required": action == "RECOMPOSE_SAME_PIP_CURRENT_FRONTIER",
            "same_source_head_required": action == "RECOMPOSE_SAME_PIP_CURRENT_FRONTIER",
            "same_pip_required": action == "RECOMPOSE_SAME_PIP_CURRENT_FRONTIER",
            "fresh_branch_required": False,
            "fresh_exact_head_assurance_required": False,
            "a0_reuse_required": action == "RECOMPOSE_SAME_PIP_CURRENT_FRONTIER",
            "a1_recomposition_required": action == "RECOMPOSE_SAME_PIP_CURRENT_FRONTIER",
            "a2_prospective_assurance_required": action == "RECOMPOSE_SAME_PIP_CURRENT_FRONTIER",
            "scope_identity_must_be_preserved": True,
            "write_set_identity_must_be_preserved": True,
            "semantic_owner_identity_must_be_preserved": True,
            "integration_policy": SERIAL_INTEGRATION_POLICY,
            "parallel_merge": False,
            "force_push": False,
            "history_rewrite": False,
        },
    )
