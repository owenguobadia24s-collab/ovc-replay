from __future__ import annotations

from typing import Any, Mapping, Sequence

from ovc.development.head_churn import classify_main_head_movement
from ovc.development.identity import canonical_sha256
from ovc.development.skills.orch345_active import build_authorized_requeue_reconciliation

MANDATORY_FINAL_ASSURANCE = (
    "CURRENT_FRONTIER_RECOMPOSITION",
    "PDC_HEAD_MOVEMENT_CLASSIFICATION",
    "EXACT_PROSPECTIVE_TREE_READINESS",
    "AA2_MATERIALISATION_EDGE_ASSURANCE",
    "IMMEDIATE_PREWRITE_PREDECESSOR_AND_TREE_PIN",
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
    """Plan same-PIP frontier recomposition without converting main movement into stale PRs."""

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
        status = "RECOMPOSITION_ELIGIBLE"
    elif classification == "INTEGRATION_RELEVANT":
        rerun = mandatory | impacted
        reuse = {item for item in completed if item not in rerun}
        status = "RECOMPOSITION_ELIGIBLE"
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
        "same_pr_required": status == "RECOMPOSITION_ELIGIBLE",
        "same_pip_required": status == "RECOMPOSITION_ELIGIBLE",
        "a0_reuse_allowed": status == "RECOMPOSITION_ELIGIBLE",
        "assurance_reused": sorted(reuse),
        "assurance_rerun": sorted(rerun),
        "full_semantic_authority_repreflight_required": classification
        == "SEMANTIC_AUTHORITY_RELEVANT",
        "dependency_footprint_required": classification
        == "UNRESOLVED_REQUIRES_FOOTPRINT",
    }
    return {
        "schema": "ovc-siq-selective-assurance-plan/v2",
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
    """Compatibility API that now schedules same-PR, same-PIP frontier recomposition."""

    status = str(movement_plan.get("status", ""))
    if status != "RECOMPOSITION_ELIGIBLE":
        return {
            "schema": "ovc-siq-automatic-frontier-recomposition/v2",
            "packet_id": str(packet.get("packet_id", "")),
            "action": "STOP_FAIL_CLOSED",
            "reason_codes": [status or "MOVEMENT_PLAN_NOT_RECOMPOSITION_ELIGIBLE"],
            "same_pr": True,
            "same_pip": True,
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
        "schema": "ovc-siq-automatic-frontier-recomposition/v2",
        "packet_id": str(packet.get("packet_id", "")),
        "action": orch["action"],
        "reason_codes": list(orch.get("blockers", [])),
        "orch345_reconciliation_record_id": orch["record_id"],
        "same_pr": bool(orch.get("same_pr_required", False)),
        "same_pip": bool(orch.get("same_pip_required", False)),
        "source_head_preserved": bool(orch.get("same_source_head_required", False)),
        "a0_reuse_allowed": bool(orch.get("a0_reuse_required", False)),
        "a1_renewal_required": bool(orch.get("a1_recomposition_required", False)),
        "a2_renewal_required": bool(orch.get("a2_prospective_assurance_required", False)),
        "fresh_branch_required": False,
        "fresh_exact_head_assurance_required": False,
        "selective_assurance_plan_id": movement_plan.get("record_id"),
        "parallel_merge": False,
        "force_push": False,
        "history_rewrite": False,
        "authority_effect": "NONE",
    }
