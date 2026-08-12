from __future__ import annotations

from typing import Any, Mapping, Sequence

from ovc.development.identity import canonical_sha256

from .merge_capability import (
    build_merge_execution_intent,
    build_merge_recovery_record,
    prepare_merge_candidate,
    revalidate_merge_candidate,
    simulate_squash_merge,
)
from .orchestration import build_remediation_cycle_record

AUTO_GATE_CLASSES = {"AUTO_EXECUTABLE", "AUTO_RATIFIABLE"}
FORBIDDEN_REMEDIATION_ACTIONS = {"CONTRACT_WEAKEN", "AUTHORITY_EXPAND", "TEST_WEAKEN", "EVIDENCE_DELETE"}


def evaluate_delegated_gate(
    *,
    gate_class: str,
    authority_delta: str,
    acceptance_conditions_pass: bool,
    qa_status: str,
    prerequisites_satisfied: bool,
    blocking_warnings: Sequence[str] = (),
    unresolved_reviews: Sequence[str] = (),
) -> dict[str, Any]:
    """Evaluate whether a gate is wholly non-reserved and mechanically auto-ratifiable.

    This projection grants no authority. Any operator-reserved classification or non-NONE
    authority delta stops before merge.
    """
    reasons: list[str] = []
    gate = str(gate_class).upper()
    delta = str(authority_delta).upper()
    if gate not in AUTO_GATE_CLASSES:
        reasons.append("OPERATOR_RESERVED_GATE")
    if delta != "NONE":
        reasons.append("AUTHORITY_DELTA_NOT_AUTO_EXECUTABLE")
    if not acceptance_conditions_pass:
        reasons.append("ACCEPTANCE_CONDITIONS_NOT_PASS")
    if str(qa_status).upper() != "PASS":
        reasons.append("QA_NOT_PASS")
    if not prerequisites_satisfied:
        reasons.append("PREREQUISITE_NOT_SATISFIED")
    if blocking_warnings:
        reasons.append("BLOCKING_WARNING_PRESENT")
    if unresolved_reviews:
        reasons.append("UNRESOLVED_REVIEW_PRESENT")
    return {
        "schema": "ovc-dsai-orch2-delegated-gate-evaluation/v1",
        "status": "AUTO_RATIFIABLE" if not reasons else "STOP_BEFORE_MERGE",
        "reason_codes": sorted(set(reasons)) or ["WHOLLY_AUTO_EXECUTABLE"],
        "authority_delta": delta,
        "operator_required": gate not in AUTO_GATE_CLASSES,
        "delegated_decision_effective": False,
        "authority_effect": "NONE",
    }


def qualify_orch2_single_packet_cycle(
    *,
    packet_id: str,
    packet_class: str,
    enabled_packet_classes: Sequence[str],
    serial_slot_available: bool,
    baseline_main_sha: str,
    current_main_sha: str,
    head_sha: str,
    revalidation_base_sha: str | None = None,
    revalidation_head_sha: str | None = None,
    required_checks: Mapping[str, str],
    qa_status: str,
    changed_paths: Sequence[str],
    scope_id: str,
    gate_class: str,
    authority_delta: str,
    acceptance_conditions_pass: bool,
    prerequisites_satisfied: bool,
    g9a_trusted: bool,
    g9b_orch2_authority: bool,
    blocking_warnings: Sequence[str] = (),
    unresolved_reviews: Sequence[str] = (),
    remediation_actions: Sequence[str] = (),
    simulated_result_main_sha: str | None = None,
) -> dict[str, Any]:
    """Pure sandbox model of one ORCH-2 packet cycle.

    The routine intentionally performs no repository side effect. It can prove the
    post-G9B execution path by supplying synthetic ``g9b_orch2_authority=True`` while
    still returning a simulation-only receipt. Pre-G9B production use remains blocked.
    """
    packet = str(packet_class)
    enabled = {str(value) for value in enabled_packet_classes}
    reasons: list[str] = []
    if packet not in enabled:
        reasons.append("PACKET_CLASS_NOT_ENABLED")
    if not serial_slot_available:
        reasons.append("SERIAL_SLOT_NOT_AVAILABLE")
    if baseline_main_sha != current_main_sha:
        reasons.append("MAIN_HEAD_CHURN")
    if not g9a_trusted:
        reasons.append("DSAI_G9A_TRUST_REQUIRED")
    if not g9b_orch2_authority:
        reasons.append("DSAI_G9B_ORCH2_AUTHORITY_REQUIRED")
    forbidden = sorted({str(action).upper() for action in remediation_actions} & FORBIDDEN_REMEDIATION_ACTIONS)
    if forbidden:
        reasons.append("FORBIDDEN_REMEDIATION_ACTION")

    gate = evaluate_delegated_gate(
        gate_class=gate_class,
        authority_delta=authority_delta,
        acceptance_conditions_pass=acceptance_conditions_pass,
        qa_status=qa_status,
        prerequisites_satisfied=prerequisites_satisfied,
        blocking_warnings=blocking_warnings,
        unresolved_reviews=unresolved_reviews,
    )
    if gate["status"] != "AUTO_RATIFIABLE":
        reasons.append("GATE_NOT_AUTO_RATIFIABLE")

    remediation_records: list[dict[str, Any]] = []
    if not forbidden:
        for index, action in enumerate(remediation_actions, start=1):
            remediation_records.append(
                build_remediation_cycle_record(
                    run_id=f"ORCH2-{packet_id}",
                    cycle=index,
                    failure_class="BOUNDED_CORRECTABLE_DEFECT",
                    action=str(action),
                    status="PASS",
                )
            )

    base_revalidate = str(revalidation_base_sha or current_main_sha)
    head_revalidate = str(revalidation_head_sha or head_sha)
    prepared = prepare_merge_candidate(
        pull_request_number=1,
        base_branch="main",
        base_sha=str(current_main_sha),
        head_sha=str(head_sha),
        required_checks=required_checks,
        qa_status=qa_status,
        changed_paths=changed_paths,
        scope_id=scope_id,
        authority_delta=authority_delta,
        auto_ratifiable=gate["status"] == "AUTO_RATIFIABLE",
        operator_required=gate["operator_required"],
        prerequisites_satisfied=prerequisites_satisfied,
        blocking_warnings=blocking_warnings,
        unresolved_reviews=unresolved_reviews,
    )
    revalidated = revalidate_merge_candidate(
        prepared,
        current_base_sha=base_revalidate,
        current_head_sha=head_revalidate,
        required_checks=required_checks,
        qa_status=qa_status,
        changed_paths=changed_paths,
        scope_id=scope_id,
        authority_delta=authority_delta,
        auto_ratifiable=gate["status"] == "AUTO_RATIFIABLE",
        operator_required=gate["operator_required"],
        prerequisites_satisfied=prerequisites_satisfied,
        blocking_warnings=blocking_warnings,
        unresolved_reviews=unresolved_reviews,
    )
    if prepared["status"] != "READY_FOR_REVALIDATION":
        reasons.append("MERGE_PREPARATION_BLOCKED")
    if revalidated["status"] != "PASS_REVALIDATED":
        reasons.append("MERGE_REVALIDATION_BLOCKED")

    intent = build_merge_execution_intent(
        revalidated,
        g9a_trusted=g9a_trusted,
        g9b_orch2_authority=g9b_orch2_authority,
        packet_class_enabled=packet in enabled,
    )
    if intent["status"] != "ELIGIBLE":
        reasons.append("MERGE_EXECUTION_INTENT_BLOCKED")

    receipt: dict[str, Any] | None = None
    if not reasons and simulated_result_main_sha:
        receipt = simulate_squash_merge(intent, result_main_sha=simulated_result_main_sha)
        if receipt.get("status") != "PASS":
            reasons.append("SANDBOX_MERGE_RECEIPT_BLOCKED")

    logical = {
        "packet_id": str(packet_id),
        "packet_class": packet,
        "baseline_main_sha": str(baseline_main_sha),
        "current_main_sha": str(current_main_sha),
        "head_sha": str(head_sha),
        "scope_id": str(scope_id),
        "gate_status": gate["status"],
        "merge_plan_id": prepared.get("merge_plan_id"),
        "revalidation_id": revalidated.get("revalidation_id"),
        "execution_intent_id": intent.get("execution_intent_id"),
    }
    unique = sorted(set(reasons))
    return {
        "schema": "ovc-dsai-orch2-single-packet-sandbox/v1",
        "status": "SANDBOX_PASS" if not unique and receipt else "BLOCK",
        "reason_codes": unique or ["SERIAL_SINGLE_PACKET_SANDBOX_PASS"],
        "run_id": canonical_sha256(logical, role="DSAI_ORCH2_SINGLE_PACKET_SANDBOX"),
        "orchestrator_stage": "ORCH-2-CANDIDATE",
        "execution_mode": "SANDBOX_ONLY_PRE_G9B",
        "concurrency": "SERIAL_REQUIRED",
        "packet_class_policy": "EXACT_ALLOWLIST_ONLY",
        "gate_evaluation": gate,
        "remediation_records": remediation_records,
        "merge_preparation": prepared,
        "merge_revalidation": revalidated,
        "merge_execution_intent": intent,
        "sandbox_merge_receipt": receipt,
        "automatic_merge_performed": False,
        "repository_side_effect_performed": False,
        "force_push": False,
        "history_rewrite": False,
        "authority_effect": "NONE",
    }


def build_orch2_interruption_reconciliation(*, merge_plan_id: str, side_effect_observed: bool) -> dict[str, Any]:
    recovery = build_merge_recovery_record(
        merge_plan_id=merge_plan_id,
        phase="EXECUTE",
        side_effect_observed=side_effect_observed,
    )
    return {
        "schema": "ovc-dsai-orch2-interruption-reconciliation/v1",
        "status": recovery["status"],
        "recovery": recovery,
        "automatic_retry": False,
        "force_push": False,
        "history_rewrite": False,
        "authority_effect": "NONE",
    }
