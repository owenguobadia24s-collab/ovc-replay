from __future__ import annotations

from typing import Any, Mapping, Sequence

from ovc.development.identity import canonical_sha256
from ovc.development.skills.orch345 import LOW_RISK_PACKET_CLASS
from ovc.development.skills.siq_core import OPERATOR_REQUIRED, READY, WAIT, QueueCandidate, build_queue_state, queue_head

QUEUE_OWNER = "OVC.SIQ.RUNTIME.v0.1"
QUEUE_ID = "OVC.SIQ.v0.1"


def _selected_packet_ids(source_orch_execution_record: Mapping[str, Any]) -> list[str]:
    source_id = str(source_orch_execution_record.get("record_id", "")).strip()
    if not source_id:
        raise ValueError("source ORCH execution record_id is required")
    if source_orch_execution_record.get("parallel_merge") is not False:
        raise PermissionError("DSAI3 binding requires ORCH serial integration / parallel_merge=false")
    selected = [str(value).strip() for value in source_orch_execution_record.get("selected_packet_ids", ())]
    if not selected or any(not value for value in selected):
        raise ValueError("source ORCH execution record must select at least one packet")
    if len(selected) != len(set(selected)):
        raise ValueError("source ORCH selected packet ids must be unique")
    return selected


def _candidate(packet: Mapping[str, Any], *, ready_sequence: int) -> QueueCandidate:
    packet_id = str(packet.get("packet_id", "")).strip()
    if not packet_id:
        raise ValueError("packet_id is required")
    packet_class = str(packet.get("packet_class", "")).upper().strip()
    if packet_class != LOW_RISK_PACKET_CLASS:
        raise PermissionError(f"packet {packet_id} is outside active low-risk DSAI3 binding scope")
    return QueueCandidate.from_mapping(
        {
            "packet_id": packet_id,
            "plan_id": packet.get("plan_id", ""),
            "candidate_head_sha": packet.get("candidate_head_sha", ""),
            "baseline_main_sha": packet.get("baseline_main_sha", ""),
            "ready_sequence": ready_sequence,
            "queue_state": packet.get("queue_state", "BUILD"),
            "implementation_complete": packet.get("implementation_complete", False),
            "qa_status": packet.get("qa_status", "PENDING"),
            "authority_delta": packet.get("authority_delta", "NONE"),
            "gate_class": packet.get("gate_class", "AUTO_EXECUTABLE"),
            "operator_authority_satisfied": packet.get("operator_authority_satisfied", False),
            "merge_authority_resolved": packet.get("merge_authority_resolved", False),
            "preliminary_assurance_pass": packet.get("preliminary_assurance_pass", False),
            "rollback_defined": packet.get("rollback_defined", False),
            "dependency_footprint_pinned": packet.get("dependency_footprint_pinned", False),
            "blocking_reviews": packet.get("blocking_reviews", ()),
            "blocking_issues": packet.get("blocking_issues", ()),
            "blocking_warnings": packet.get("blocking_warnings", ()),
            "reason_codes": packet.get("reason_codes", ()),
        }
    )


def build_orch_to_siq_binding_plan(
    *,
    source_orch_execution_record: Mapping[str, Any],
    packets: Sequence[Mapping[str, Any]],
    generation: int = 0,
) -> dict[str, Any]:
    """Build a deterministic, side-effect-free ORCH-to-existing-SIQ binding plan.

    The routine creates no queue and performs no repository or merge side effect. It
    projects the ORCH-selected low-risk packets into the already-active SIQ admission
    model, assigning READY sequence from the deterministic ORCH selection order.
    """
    selected = _selected_packet_ids(source_orch_execution_record)
    packet_by_id: dict[str, Mapping[str, Any]] = {}
    for packet in packets:
        packet_id = str(packet.get("packet_id", "")).strip()
        if not packet_id:
            raise ValueError("all packet mappings require packet_id")
        if packet_id in packet_by_id:
            raise ValueError(f"duplicate packet mapping: {packet_id}")
        packet_by_id[packet_id] = packet

    missing = [packet_id for packet_id in selected if packet_id not in packet_by_id]
    if missing:
        raise ValueError(f"selected packet mappings missing: {', '.join(missing)}")

    candidates = [_candidate(packet_by_id[packet_id], ready_sequence=index) for index, packet_id in enumerate(selected, start=1)]
    state = build_queue_state(candidates, queue_id=QUEUE_ID, generation=generation)
    head = queue_head(state)
    head_id = head.packet_id if head else None

    bindings: list[dict[str, Any]] = []
    for row in state.candidates:
        logical = {
            "packet_id": row.packet_id,
            "source_orch_execution_record_id": str(source_orch_execution_record["record_id"]),
            "queue_owner": QUEUE_OWNER,
            "queue_id": QUEUE_ID,
            "ready_sequence": row.ready_sequence,
            "candidate_head_sha": row.candidate_head_sha,
            "baseline_main_sha": row.baseline_main_sha,
            "queue_state": row.queue_state,
            "queue_head_eligible": row.packet_id == head_id and row.queue_state == READY,
            "creates_new_queue": False,
            "authority_effect": "NONE_BINDING_ONLY",
            "parallel_merge": False,
        }
        bindings.append(
            {
                "schema": "ovc-dsai3-siq-binding-record/v1",
                **logical,
                "binding_id": canonical_sha256(logical, role="DSAI3_SIQ_BINDING_RECORD"),
            }
        )

    ready_ids = [row.packet_id for row in state.candidates if row.queue_state == READY]
    operator_ids = [row.packet_id for row in state.candidates if row.queue_state == OPERATOR_REQUIRED]
    waiting_ids = [row.packet_id for row in state.candidates if row.queue_state == WAIT]
    logical_plan = {
        "source_orch_execution_record_id": str(source_orch_execution_record["record_id"]),
        "selected_packet_ids": selected,
        "queue_owner": QUEUE_OWNER,
        "queue_id": QUEUE_ID,
        "queue_generation": state.generation,
        "queue_head_packet_id": head_id,
        "base_sensitive_final_assurance_eligible_packet_id": head_id,
        "waiting_base_sensitive_packet_ids": [packet_id for packet_id in ready_ids if packet_id != head_id],
        "operator_required_packet_ids": operator_ids,
        "not_ready_packet_ids": waiting_ids,
        "creates_new_queue": False,
        "side_effect_performed": False,
        "execution_mode": "SHADOW_ONLY_PRE_DSAI3_G7",
        "parallel_merge": False,
        "authority_effect": "NONE_BINDING_PLANNER_ONLY",
    }
    return {
        "schema": "ovc-dsai3-orch-to-siq-binding-plan/v1",
        **logical_plan,
        "record_id": canonical_sha256(logical_plan, role="DSAI3_ORCH_TO_SIQ_BINDING_PLAN"),
        "queue_state": state.as_dict(),
        "bindings": bindings,
    }
