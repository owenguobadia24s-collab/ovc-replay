from __future__ import annotations

from typing import Any, Mapping, Sequence

from ovc.development.head_churn import classify_main_head_movement
from ovc.development.identity import canonical_sha256
from ovc.development.skills.orch345_active import build_authorized_requeue_reconciliation

MANDATORY_FINAL_ASSURANCE = (
    "CURRENT_MAIN_RECONCILIATION",
    "PDC_HEAD_MOVEMENT_CLASSIFICATION",
    "EXACT_TREE_MERGE_READINESS",
    "MANDATORY_FINAL_HEAD_ASSURANCE",
    "IMMEDIATE_PREMERGE_HEAD_AND_BASE_PIN",
)


def plan_selective_assurance(
    *,
    baseline_main_sha: str,
    current_main_sha: str,
    changed_main_paths: Sequence[str],
    dependency_footprint: Mapping[str, Any] | None,
    pdc_policy: Mapping[str, Any] | None,
    completed_assurance: Sequence[str],
    impacted_assurance: Sequence[str] = (),
) -> dict[str, Any]:
    movement = classify_main_head_movement(
        baseline_main_sha=baseline_main_sha,
        current_main_sha=current_main_sha,
        changed_main_paths=changed_main_paths,
        footprint=dependency_footprint,
        policy=pdc_policy,
    )
    classification = movement["classification"]
    completed = tuple(sorted({str(item).upper() for item in completed_assurance}))
    impacted = {str(item).upper() for item in impacted_assurance}
    mandatory = set(MANDATORY_FINAL_ASSURANCE)

    if classification == "IRRELEVANT":
        rerun = mandatory
        reuse = {item for item in completed if item not in rerun}
        status = "REQUEUE_ELIGIBLE"
    elif classification == "INTEGRATION_RELEVANT":
        rerun = mandatory | impacted
        reuse = {item for item in completed if item not in rerun}
        status = "REQUEUE_ELIGIBLE"
    elif classification == "SEMANTIC_AUTHORITY_RELEVANT":
        rerun = set(completed) | mandatory
        reuse = set()
        status = "BLOCK_FULL_REPREFLIGHT_REQUIRED"
    else:
        rerun = set()
        reuse = set()
        status = "BLOCK_DEPENDENCY_FOOTPRINT_REQUIRED"

    logical = {
        "movement_receipt_sha256": movement["receipt_sha256"],
        "classification": classification,
        "status": status,
        "assurance_reused": sorted(reuse),
        "assurance_rerun": sorted(rerun),
        "full_semantic_authority_repreflight_required": classification == "SEMANTIC_AUTHORITY_RELEVANT",
        "dependency_footprint_required": classification == "UNRESOLVED_REQUIRES_FOOTPRINT",
    }
    return {
        "schema": "ovc-siq-selective-assurance-plan/v1",
        **logical,
        "record_id": canonical_sha256(logical, role="SIQ_SELECTIVE_ASSURANCE_PLAN"),
        "pdc_movement_receipt": movement,
        "authority_effect": "NONE",
    }


def build_automatic_requeue(
    *,
    authority_resolution: Mapping[str, Any],
    packet: Mapping[str, Any],
    movement_plan: Mapping[str, Any],
    attempt: int,
    previous_base: str,
    current_main: str,
) -> dict[str, Any]:
    status = str(movement_plan.get("status", ""))
    if status != "REQUEUE_ELIGIBLE":
        return {
            "schema": "ovc-siq-automatic-requeue/v1",
            "packet_id": str(packet.get("packet_id", "")),
            "action": "STOP_FAIL_CLOSED",
            "reason_codes": [status or "MOVEMENT_PLAN_NOT_REQUEUE_ELIGIBLE"],
            "parallel_merge": False,
            "force_push": False,
            "history_rewrite": False,
            "authority_effect": "NONE",
        }
    orch = build_authorized_requeue_reconciliation(
        authority_resolution=authority_resolution,
        packet=packet,
        failure_reason="MAIN_ADVANCED_AFTER_ASSURANCE",
        attempt=attempt,
        previous_base=previous_base,
        current_main=current_main,
    )
    return {
        "schema": "ovc-siq-automatic-requeue/v1",
        "packet_id": str(packet.get("packet_id", "")),
        "action": orch["action"],
        "reason_codes": list(orch.get("blockers", [])),
        "orch345_reconciliation_record_id": orch["record_id"],
        "fresh_branch_required": bool(orch.get("fresh_branch_required")),
        "fresh_exact_head_assurance_required": bool(orch.get("fresh_exact_head_assurance_required")),
        "selective_assurance_plan_id": movement_plan.get("record_id"),
        "parallel_merge": False,
        "force_push": False,
        "history_rewrite": False,
        "authority_effect": "NONE",
    }
