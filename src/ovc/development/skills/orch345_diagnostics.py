from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping, Sequence

from ovc.development.identity import canonical_sha256
from ovc.development.skills.orch345 import PARALLEL_BUILD_CLASS


DIAGNOSTIC_RECEIPT_CLASS = "TEMPORARY_DIAGNOSTIC_OBSERVABILITY"
DIAGNOSTIC_AUTHORITY_EFFECT = "NONE"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def _temporary_receipt(
    *,
    schema: str,
    role: str,
    orchestrator: str,
    observed_at_utc: str | None,
    logical: Mapping[str, Any],
) -> dict[str, Any]:
    payload = {
        "receipt_class": DIAGNOSTIC_RECEIPT_CLASS,
        "orchestrator": orchestrator,
        "observed_at_utc": observed_at_utc or _utc_now(),
        "observability_only": True,
        "temporary": True,
        "governance_expansion": False,
        "authority_effect": DIAGNOSTIC_AUTHORITY_EFFECT,
        "new_operator_gate": False,
        "merge_authority": "NONE",
        **dict(logical),
    }
    return {
        "schema": schema,
        **payload,
        "record_id": canonical_sha256(payload, role=role),
    }


def build_orch3_decision_receipt(
    *,
    source_execution_record: Mapping[str, Any],
    source_plan: Mapping[str, Any],
    candidate_packet_count: int,
    observed_at_utc: str | None = None,
) -> dict[str, Any]:
    selected_packet_ids = list(source_execution_record.get("selected_packet_ids", []))
    waiting = list(source_execution_record.get("waiting", []))
    operator_boundaries = list(source_execution_record.get("operator_boundaries", []))
    return _temporary_receipt(
        schema="ovc-dsai2-orch3-diagnostic-decision-receipt/v1",
        role="DSAI2_ORCH3_DIAGNOSTIC_DECISION_RECEIPT",
        orchestrator="ORCH-3",
        observed_at_utc=observed_at_utc,
        logical={
            "trigger_condition": "ACTIVE_ORCH3_HELPER_INVOKED",
            "decision": "TRAIN_AUTHORIZED" if selected_packet_ids else "NO_ELIGIBLE_TRAIN",
            "programme_id": str(source_execution_record.get("programme_id", "")),
            "candidate_packet_count": int(candidate_packet_count),
            "selected_packet_ids": selected_packet_ids,
            "selected_train_depth": len(selected_packet_ids),
            "waiting": waiting,
            "waiting_count": len(waiting),
            "operator_boundaries": operator_boundaries,
            "operator_boundary_count": len(operator_boundaries),
            "max_train_packets": int(source_execution_record.get("max_train_packets", 0)),
            "source_execution_record_id": source_execution_record.get("record_id"),
            "source_plan_id": source_plan.get("record_id"),
            "integration_policy": source_execution_record.get("integration_policy"),
            "parallel_merge": False,
        },
    )


def build_orch4_decision_receipt(
    *,
    source_execution_record: Mapping[str, Any],
    source_classification: Mapping[str, Any],
    observed_at_utc: str | None = None,
) -> dict[str, Any]:
    classification = str(source_execution_record.get("classification", ""))
    decision = "PARALLEL_ALLOW" if classification == PARALLEL_BUILD_CLASS else "SERIAL_FALLBACK"
    return _temporary_receipt(
        schema="ovc-dsai2-orch4-diagnostic-decision-receipt/v1",
        role="DSAI2_ORCH4_DIAGNOSTIC_DECISION_RECEIPT",
        orchestrator="ORCH-4",
        observed_at_utc=observed_at_utc,
        logical={
            "trigger_condition": "ACTIVE_ORCH4_PAIR_CLASSIFICATION_INVOKED",
            "decision": decision,
            "left_packet_id": str(source_execution_record.get("left_packet_id", "")),
            "right_packet_id": str(source_execution_record.get("right_packet_id", "")),
            "classification": classification,
            "reason_codes": list(source_execution_record.get("reason_codes", [])),
            "overlaps": dict(source_classification.get("overlaps", {})),
            "admission": source_execution_record.get("admission"),
            "source_execution_record_id": source_execution_record.get("record_id"),
            "source_classification_id": source_classification.get("record_id"),
            "ambiguity_policy": "SERIAL_REQUIRED",
            "integration_policy": source_execution_record.get("integration_policy"),
            "parallel_merge": False,
        },
    )


def build_orch5_decision_receipt(
    *,
    source_execution_record: Mapping[str, Any],
    source_schedule: Mapping[str, Any],
    packets: Sequence[Mapping[str, Any]],
    completed_packet_ids: Sequence[str] = (),
    newly_completed_packet_ids: Sequence[str] = (),
    observed_at_utc: str | None = None,
) -> dict[str, Any]:
    selected_packet_ids = list(source_execution_record.get("selected_packet_ids", []))
    waiting = list(source_execution_record.get("waiting", []))
    blocked = list(source_execution_record.get("blocked", []))
    operator_wait = list(source_execution_record.get("operator_wait", []))
    max_parallel = int(source_execution_record.get("max_parallel_builds", 0))
    occupied_slots = len(selected_packet_ids)
    waiting_reasons: dict[str, int] = {}
    for item in waiting:
        reason = str(item.get("reason", "UNKNOWN"))
        waiting_reasons[reason] = waiting_reasons.get(reason, 0) + 1

    completed = {str(value) for value in completed_packet_ids}
    newly_completed = {str(value) for value in newly_completed_packet_ids}
    selected = set(selected_packet_ids)
    dependency_wakeups: list[dict[str, Any]] = []
    for packet in packets:
        packet_id = str(packet.get("packet_id", ""))
        if packet_id not in selected:
            continue
        dependencies = {
            str(value)
            for value in packet.get("cross_programme_dependencies", ())
            if str(value)
        }
        newly_satisfied_by = sorted(dependencies & newly_completed)
        if dependencies and dependencies.issubset(completed) and newly_satisfied_by:
            dependency_wakeups.append(
                {
                    "packet_id": packet_id,
                    "satisfied_dependencies": sorted(dependencies),
                    "newly_satisfied_by": newly_satisfied_by,
                }
            )

    return _temporary_receipt(
        schema="ovc-dsai2-orch5-diagnostic-decision-receipt/v1",
        role="DSAI2_ORCH5_DIAGNOSTIC_DECISION_RECEIPT",
        orchestrator="ORCH-5",
        observed_at_utc=observed_at_utc,
        logical={
            "trigger_condition": "ACTIVE_ORCH5_PORTFOLIO_SCHEDULER_INVOKED",
            "decision": "PORTFOLIO_DISPATCH" if selected_packet_ids else "NO_ELIGIBLE_DISPATCH",
            "candidate_packet_count": len(packets),
            "selected_packet_ids": selected_packet_ids,
            "selected_programme_ids": list(source_execution_record.get("selected_programme_ids", [])),
            "occupied_slots": occupied_slots,
            "available_slots": max(0, max_parallel - occupied_slots),
            "max_parallel_builds": max_parallel,
            "capacity_saturated": max_parallel > 0 and occupied_slots >= max_parallel,
            "waiting": waiting,
            "waiting_count": len(waiting),
            "waiting_reason_counts": waiting_reasons,
            "serial_fallback_count": waiting_reasons.get("SERIAL_FALLBACK", 0),
            "slot_limit_wait_count": waiting_reasons.get("PARALLEL_SLOT_LIMIT", 0),
            "blocked": blocked,
            "blocked_count": len(blocked),
            "operator_wait": operator_wait,
            "operator_wait_count": len(operator_wait),
            "cross_programme_dependency_wakeups": dependency_wakeups,
            "dependency_wakeup_count": len(dependency_wakeups),
            "dependency_wakeup_input_present": bool(newly_completed),
            "source_execution_record_id": source_execution_record.get("record_id"),
            "source_schedule_id": source_schedule.get("record_id"),
            "integration_policy": source_execution_record.get("integration_policy"),
            "parallel_merge": False,
        },
    )
