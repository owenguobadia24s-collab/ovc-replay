from __future__ import annotations

from typing import Any, Mapping, Sequence

from ovc.development.identity import canonical_sha256
from ovc.development.skills.orch345 import (
    PARALLEL_BUILD_CLASS,
    SERIAL_CLASS,
    SERIAL_INTEGRATION_POLICY,
    build_packet_train_plan,
    build_portfolio_schedule,
    classify_packet_pair,
)


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
    max_packets: int | None = None,
) -> dict[str, Any]:
    _require_active(authority_resolution)
    plan = build_packet_train_plan(
        programme_id=programme_id,
        packets=packets,
        completed_packet_ids=completed_packet_ids,
        max_packets=max_packets,
    )
    if plan.get("status") == "STOP_OPERATOR":
        raise PermissionError("ORCH-3 packet train reached an operator-required boundary")
    return _active_record(
        "ovc-dsai2-orch3-authorized-packet-train/v1",
        "DSAI2_ORCH3_AUTHORIZED_PACKET_TRAIN",
        {
            "programme_id": programme_id,
            "selected_packet_ids": list(plan.get("selected_packet_ids", [])),
            "waiting": list(plan.get("waiting", [])),
            "operator_boundaries": list(plan.get("operator_boundaries", [])),
            "execution_mode": "ACTIVE_BOUNDED",
            "integration_policy": SERIAL_INTEGRATION_POLICY,
            "parallel_merge": False,
            "source_plan_id": plan.get("record_id"),
        },
    )


def authorize_parallel_build_pair(
    *,
    authority_resolution: Mapping[str, Any],
    left: Mapping[str, Any],
    right: Mapping[str, Any],
) -> dict[str, Any]:
    _require_active(authority_resolution)
    pair = classify_packet_pair(left, right)
    admitted = pair.get("classification") == PARALLEL_BUILD_CLASS
    return _active_record(
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


def build_authorized_portfolio_schedule(
    *,
    authority_resolution: Mapping[str, Any],
    packets: Sequence[Mapping[str, Any]],
    completed_packet_ids: Sequence[str] = (),
    max_parallel: int = 2,
) -> dict[str, Any]:
    _require_active(authority_resolution)
    schedule = build_portfolio_schedule(
        packets=packets,
        completed_packet_ids=completed_packet_ids,
        max_parallel=max_parallel,
    )
    return _active_record(
        "ovc-dsai2-orch5-authorized-portfolio-schedule/v1",
        "DSAI2_ORCH5_AUTHORIZED_PORTFOLIO_SCHEDULE",
        {
            "selected_packet_ids": list(schedule.get("selected_packet_ids", [])),
            "selected_programme_ids": list(schedule.get("selected_programme_ids", [])),
            "waiting": list(schedule.get("waiting", [])),
            "blocked": list(schedule.get("blocked", [])),
            "operator_wait": list(schedule.get("operator_wait", [])),
            "execution_mode": "ACTIVE_BOUNDED",
            "dispatch_authority": "ALREADY_AUTHORIZED_LOW_RISK_PACKETS_ONLY",
            "integration_policy": SERIAL_INTEGRATION_POLICY,
            "parallel_merge": False,
            "source_schedule_id": schedule.get("record_id"),
        },
    )
