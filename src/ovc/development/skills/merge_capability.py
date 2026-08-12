from __future__ import annotations

import re
from typing import Any, Mapping, Sequence

from ovc.development.identity import canonical_sha256, normalize_relative_path

_SHA40 = re.compile(r"^[0-9a-f]{40}$")
_ALLOWED_CHECK_CONCLUSIONS = {"success"}
_ALLOWED_MERGE_METHODS = {"squash"}


def _valid_sha(value: str) -> bool:
    return bool(_SHA40.fullmatch(str(value)))


def _checks(value: Mapping[str, str]) -> dict[str, str]:
    return {str(name): str(conclusion).lower() for name, conclusion in sorted(value.items())}


def _paths(value: Sequence[str]) -> list[str]:
    return sorted({normalize_relative_path(path) for path in value})


def _reasons_for_assurance(
    *,
    base_branch: str,
    base_sha: str,
    head_sha: str,
    required_checks: Mapping[str, str],
    qa_status: str,
    changed_paths: Sequence[str],
    scope_id: str,
    authority_delta: str,
    auto_ratifiable: bool,
    operator_required: bool,
    prerequisites_satisfied: bool,
    blocking_warnings: Sequence[str],
    unresolved_reviews: Sequence[str],
) -> list[str]:
    reasons: list[str] = []
    if base_branch != "main":
        reasons.append("TARGET_NOT_MAIN")
    if not _valid_sha(base_sha):
        reasons.append("BASE_SHA_INVALID")
    if not _valid_sha(head_sha):
        reasons.append("HEAD_SHA_INVALID")
    checks = _checks(required_checks)
    if not checks:
        reasons.append("REQUIRED_CHECKS_MISSING")
    elif any(result not in _ALLOWED_CHECK_CONCLUSIONS for result in checks.values()):
        reasons.append("REQUIRED_CHECK_NOT_PASS")
    if str(qa_status).upper() != "PASS":
        reasons.append("QA_NOT_PASS")
    if not changed_paths:
        reasons.append("CHANGE_SCOPE_EMPTY")
    if not str(scope_id).strip():
        reasons.append("SCOPE_ID_MISSING")
    if str(authority_delta).upper() != "NONE":
        reasons.append("AUTHORITY_DELTA_NOT_AUTO_EXECUTABLE")
    if not auto_ratifiable:
        reasons.append("AUTO_RATIFICATION_NOT_ELIGIBLE")
    if operator_required:
        reasons.append("OPERATOR_RESERVED_AUTHORITY_PRESENT")
    if not prerequisites_satisfied:
        reasons.append("PREREQUISITE_NOT_SATISFIED")
    if blocking_warnings:
        reasons.append("BLOCKING_WARNING_PRESENT")
    if unresolved_reviews:
        reasons.append("UNRESOLVED_REVIEW_PRESENT")
    return reasons


def prepare_merge_candidate(
    *,
    pull_request_number: int,
    base_branch: str,
    base_sha: str,
    head_sha: str,
    required_checks: Mapping[str, str],
    qa_status: str,
    changed_paths: Sequence[str],
    scope_id: str,
    authority_delta: str,
    auto_ratifiable: bool,
    operator_required: bool,
    prerequisites_satisfied: bool = True,
    blocking_warnings: Sequence[str] = (),
    unresolved_reviews: Sequence[str] = (),
) -> dict[str, Any]:
    """Freeze a prospective squash-merge candidate without performing a side effect.

    A prepared candidate is only a deterministic assurance object. It carries no merge
    authority and deliberately refuses reserved authority deltas.
    """
    normalized_paths = _paths(changed_paths)
    normalized_checks = _checks(required_checks)
    reasons = _reasons_for_assurance(
        base_branch=base_branch,
        base_sha=base_sha,
        head_sha=head_sha,
        required_checks=normalized_checks,
        qa_status=qa_status,
        changed_paths=normalized_paths,
        scope_id=scope_id,
        authority_delta=authority_delta,
        auto_ratifiable=auto_ratifiable,
        operator_required=operator_required,
        prerequisites_satisfied=prerequisites_satisfied,
        blocking_warnings=blocking_warnings,
        unresolved_reviews=unresolved_reviews,
    )
    snapshot = {
        "pull_request_number": int(pull_request_number),
        "base_branch": str(base_branch),
        "base_sha": str(base_sha),
        "head_sha": str(head_sha),
        "required_checks": normalized_checks,
        "qa_status": str(qa_status).upper(),
        "changed_paths": normalized_paths,
        "scope_id": str(scope_id),
        "authority_delta": str(authority_delta).upper(),
        "auto_ratifiable": bool(auto_ratifiable),
        "operator_required": bool(operator_required),
        "prerequisites_satisfied": bool(prerequisites_satisfied),
        "blocking_warnings": sorted(str(item) for item in blocking_warnings),
        "unresolved_reviews": sorted(str(item) for item in unresolved_reviews),
        "merge_method": "squash",
    }
    return {
        "schema": "ovc-dsai-merge-preparation/v1",
        "status": "READY_FOR_REVALIDATION" if not reasons else "BLOCK",
        "reason_codes": reasons or ["PREPARED_NO_SIDE_EFFECT"],
        "merge_plan_id": canonical_sha256(snapshot, role="DSAI_MERGE_PREPARATION"),
        "snapshot": snapshot,
        "merge_authority": "NONE",
        "automatic_merge": False,
        "force_push": False,
        "history_rewrite": False,
        "side_effect_performed": False,
        "authority_effect": "NONE",
    }


def revalidate_merge_candidate(
    prepared: Mapping[str, Any],
    *,
    current_base_sha: str,
    current_head_sha: str,
    required_checks: Mapping[str, str],
    qa_status: str,
    changed_paths: Sequence[str],
    scope_id: str,
    authority_delta: str,
    auto_ratifiable: bool,
    operator_required: bool,
    prerequisites_satisfied: bool = True,
    blocking_warnings: Sequence[str] = (),
    unresolved_reviews: Sequence[str] = (),
) -> dict[str, Any]:
    """Revalidate the exact frozen candidate immediately before merge execution."""
    if prepared.get("status") != "READY_FOR_REVALIDATION":
        return {
            "schema": "ovc-dsai-merge-revalidation/v1",
            "status": "BLOCK",
            "reason_codes": ["PREPARATION_NOT_READY"],
            "merge_plan_id": prepared.get("merge_plan_id"),
            "merge_authority": "NONE",
            "side_effect_performed": False,
            "authority_effect": "NONE",
        }

    snapshot = dict(prepared["snapshot"])
    reasons = _reasons_for_assurance(
        base_branch=str(snapshot["base_branch"]),
        base_sha=current_base_sha,
        head_sha=current_head_sha,
        required_checks=required_checks,
        qa_status=qa_status,
        changed_paths=changed_paths,
        scope_id=scope_id,
        authority_delta=authority_delta,
        auto_ratifiable=auto_ratifiable,
        operator_required=operator_required,
        prerequisites_satisfied=prerequisites_satisfied,
        blocking_warnings=blocking_warnings,
        unresolved_reviews=unresolved_reviews,
    )
    if str(current_base_sha) != snapshot["base_sha"]:
        reasons.append("BASE_SHA_DRIFT")
    if str(current_head_sha) != snapshot["head_sha"]:
        reasons.append("HEAD_SHA_DRIFT")
    if _checks(required_checks) != snapshot["required_checks"]:
        reasons.append("CHECK_SET_OR_RESULT_DRIFT")
    if str(qa_status).upper() != snapshot["qa_status"]:
        reasons.append("QA_STATUS_DRIFT")
    if _paths(changed_paths) != snapshot["changed_paths"]:
        reasons.append("SCOPE_PATH_DRIFT")
    if str(scope_id) != snapshot["scope_id"]:
        reasons.append("SCOPE_ID_DRIFT")
    if str(authority_delta).upper() != snapshot["authority_delta"]:
        reasons.append("AUTHORITY_DELTA_DRIFT")
    if bool(auto_ratifiable) != snapshot["auto_ratifiable"]:
        reasons.append("AUTO_RATIFIABLE_DRIFT")
    if bool(operator_required) != snapshot["operator_required"]:
        reasons.append("OPERATOR_AUTHORITY_DRIFT")
    if bool(prerequisites_satisfied) != snapshot["prerequisites_satisfied"]:
        reasons.append("PREREQUISITE_DRIFT")
    if sorted(str(item) for item in blocking_warnings) != snapshot["blocking_warnings"]:
        reasons.append("WARNING_SET_DRIFT")
    if sorted(str(item) for item in unresolved_reviews) != snapshot["unresolved_reviews"]:
        reasons.append("REVIEW_SET_DRIFT")

    unique = sorted(set(reasons))
    logical = {
        "merge_plan_id": prepared["merge_plan_id"],
        "current_base_sha": str(current_base_sha),
        "current_head_sha": str(current_head_sha),
        "checks": _checks(required_checks),
        "qa_status": str(qa_status).upper(),
        "changed_paths": _paths(changed_paths),
        "scope_id": str(scope_id),
        "authority_delta": str(authority_delta).upper(),
        "auto_ratifiable": bool(auto_ratifiable),
        "operator_required": bool(operator_required),
        "prerequisites_satisfied": bool(prerequisites_satisfied),
        "blocking_warnings": sorted(str(item) for item in blocking_warnings),
        "unresolved_reviews": sorted(str(item) for item in unresolved_reviews),
    }
    return {
        "schema": "ovc-dsai-merge-revalidation/v1",
        "status": "PASS_REVALIDATED" if not unique else "BLOCK",
        "reason_codes": unique or ["EXACT_CANDIDATE_REVALIDATED"],
        "merge_plan_id": prepared["merge_plan_id"],
        "revalidation_id": canonical_sha256(logical, role="DSAI_MERGE_REVALIDATION"),
        "snapshot": logical,
        "merge_authority": "NONE",
        "side_effect_performed": False,
        "authority_effect": "NONE",
    }


def build_merge_execution_intent(
    revalidation: Mapping[str, Any],
    *,
    g9a_trusted: bool,
    g9b_orch2_authority: bool,
    packet_class_enabled: bool,
    merge_method: str = "squash",
) -> dict[str, Any]:
    """Project execution eligibility; never perform the repository merge itself."""
    reasons: list[str] = []
    if revalidation.get("status") != "PASS_REVALIDATED":
        reasons.append("REVALIDATION_REQUIRED")
    if not g9a_trusted:
        reasons.append("DSAI_G9A_TRUST_REQUIRED")
    if not g9b_orch2_authority:
        reasons.append("DSAI_G9B_ORCH2_AUTHORITY_REQUIRED")
    if not packet_class_enabled:
        reasons.append("PACKET_CLASS_NOT_ENABLED")
    if merge_method not in _ALLOWED_MERGE_METHODS:
        reasons.append("MERGE_METHOD_NOT_ALLOWED")
    logical = {
        "merge_plan_id": revalidation.get("merge_plan_id"),
        "revalidation_id": revalidation.get("revalidation_id"),
        "merge_method": str(merge_method),
        "g9a_trusted": bool(g9a_trusted),
        "g9b_orch2_authority": bool(g9b_orch2_authority),
        "packet_class_enabled": bool(packet_class_enabled),
    }
    return {
        "schema": "ovc-dsai-merge-execution-intent/v1",
        "status": "ELIGIBLE" if not reasons else "BLOCK",
        "reason_codes": reasons or ["EXTERNAL_MERGE_ADAPTER_MAY_EXECUTE"],
        "execution_intent_id": canonical_sha256(logical, role="DSAI_MERGE_EXECUTION_INTENT"),
        **logical,
        "side_effect_authorized": not reasons,
        "side_effect_performed": False,
        "execution_adapter": "EXTERNAL_TOOL_BROKER_ONLY",
        "force_push": False,
        "history_rewrite": False,
        "authority_effect": "NONE_DERIVED_FROM_COURT_RECORD_INPUTS",
    }


def simulate_squash_merge(
    intent: Mapping[str, Any],
    *,
    result_main_sha: str,
) -> dict[str, Any]:
    """Pure sandbox/reference merge outcome used for qualification evidence."""
    if intent.get("status") != "ELIGIBLE" or not intent.get("side_effect_authorized"):
        return {
            "schema": "ovc-dsai-simulated-merge-receipt/v1",
            "status": "BLOCK",
            "reason_codes": ["EXECUTION_INTENT_NOT_ELIGIBLE"],
            "simulation_only": True,
            "side_effect_performed": False,
            "authority_effect": "NONE",
        }
    if not _valid_sha(result_main_sha):
        return {
            "schema": "ovc-dsai-simulated-merge-receipt/v1",
            "status": "BLOCK",
            "reason_codes": ["RESULT_MAIN_SHA_INVALID"],
            "simulation_only": True,
            "side_effect_performed": False,
            "authority_effect": "NONE",
        }
    logical = {
        "execution_intent_id": intent["execution_intent_id"],
        "merge_plan_id": intent["merge_plan_id"],
        "revalidation_id": intent["revalidation_id"],
        "merge_method": intent["merge_method"],
        "result_main_sha": str(result_main_sha),
    }
    return {
        "schema": "ovc-dsai-simulated-merge-receipt/v1",
        "status": "PASS",
        "reason_codes": ["SANDBOX_REFERENCE_MERGE_PASS"],
        "receipt_id": canonical_sha256(logical, role="DSAI_SIMULATED_MERGE_RECEIPT"),
        **logical,
        "simulation_only": True,
        "side_effect_performed": False,
        "force_push": False,
        "history_rewrite": False,
        "authority_effect": "NONE",
    }


def build_merge_recovery_record(
    *,
    merge_plan_id: str,
    phase: str,
    side_effect_observed: bool,
) -> dict[str, Any]:
    """Fail closed after interruption; unknown post-side-effect state requires reconciliation."""
    phase_value = str(phase).upper()
    if phase_value not in {"PREPARE", "REVALIDATE", "EXECUTE", "RECEIPT"}:
        raise ValueError("unknown merge phase")
    status = "SAFE_TO_RETRY_FROM_PREPARE" if not side_effect_observed else "BLOCK_RECONCILIATION_REQUIRED"
    return {
        "schema": "ovc-dsai-merge-recovery/v1",
        "merge_plan_id": str(merge_plan_id),
        "phase": phase_value,
        "side_effect_observed": bool(side_effect_observed),
        "status": status,
        "automatic_retry": False,
        "force_push": False,
        "history_rewrite": False,
        "authority_effect": "NONE",
    }
