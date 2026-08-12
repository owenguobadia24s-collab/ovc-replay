from __future__ import annotations

from typing import Any, Mapping


def resolve_orch2_authority(
    *,
    authority: Mapping[str, Any],
    packet_class: str,
    record_present_on_main: bool,
) -> dict[str, Any]:
    """Resolve, but never self-grant, the operator-approved bounded ORCH-2 authority.

    The authority record is effective only when the exact record is present on ``main``.
    Any malformed field, unsupported packet class or weakened integration control fails
    closed. The returned boolean can be supplied to the existing ORCH-2 qualification /
    execution-intent path as ``g9b_orch2_authority``.
    """

    reasons: list[str] = []
    if authority.get("schema") != "ovc-dsai-orch2-authority/v1":
        reasons.append("AUTHORITY_SCHEMA_MISMATCH")
    if authority.get("gate_id") != "DSAI-G9B":
        reasons.append("GATE_ID_MISMATCH")
    if authority.get("orchestrator_stage") != "ORCH-2":
        reasons.append("ORCHESTRATOR_STAGE_MISMATCH")
    if authority.get("approved") is not True or authority.get("effective") is not True:
        reasons.append("AUTHORITY_NOT_EFFECTIVE")
    if authority.get("repository_effectivity_condition") != "AUTHORITY_RECORD_PRESENT_ON_MAIN":
        reasons.append("REPOSITORY_EFFECTIVITY_CONDITION_MISMATCH")
    if not record_present_on_main:
        reasons.append("AUTHORITY_RECORD_NOT_PRESENT_ON_MAIN")
    if authority.get("packet_class_policy") != "EXACT_ALLOWLIST_ONLY":
        reasons.append("PACKET_CLASS_POLICY_MISMATCH")
    enabled = [str(value) for value in authority.get("enabled_packet_classes", [])]
    if str(packet_class) not in enabled:
        reasons.append("PACKET_CLASS_NOT_ENABLED")
    if enabled != ["LOW_RISK_IMPLEMENTATION"]:
        reasons.append("PACKET_CLASS_ALLOWLIST_DRIFT")
    if authority.get("concurrency") != "SERIAL_REQUIRED":
        reasons.append("CONCURRENCY_POLICY_MISMATCH")

    gate_policy = authority.get("gate_policy")
    if not isinstance(gate_policy, Mapping):
        reasons.append("GATE_POLICY_MISSING")
    else:
        allowed_gate_classes = sorted(str(value) for value in gate_policy.get("allowed_gate_classes", []))
        if allowed_gate_classes != ["AUTO_EXECUTABLE", "AUTO_RATIFIABLE"]:
            reasons.append("AUTO_GATE_ALLOWLIST_DRIFT")
        if gate_policy.get("required_authority_delta") != "NONE":
            reasons.append("AUTHORITY_DELTA_POLICY_DRIFT")
        if gate_policy.get("required_acceptance_conditions") != "PASS_ALL":
            reasons.append("ACCEPTANCE_POLICY_DRIFT")
        if gate_policy.get("required_qa") != "PASS":
            reasons.append("QA_POLICY_DRIFT")
        if gate_policy.get("required_prerequisites") is not True:
            reasons.append("PREREQUISITE_POLICY_DRIFT")
        if list(gate_policy.get("required_blocking_warnings", [])):
            reasons.append("WARNING_POLICY_DRIFT")
        if list(gate_policy.get("required_unresolved_reviews", [])):
            reasons.append("REVIEW_POLICY_DRIFT")

    integration = authority.get("integration_policy")
    if not isinstance(integration, Mapping):
        reasons.append("INTEGRATION_POLICY_MISSING")
    else:
        if integration.get("target_branch") != "main":
            reasons.append("MERGE_TARGET_DRIFT")
        if integration.get("merge_method") != "squash":
            reasons.append("MERGE_METHOD_DRIFT")
        if integration.get("exact_base_head_checks_scope_revalidation") is not True:
            reasons.append("EXACT_REVALIDATION_DISABLED")
        if integration.get("external_merge_adapter_required") is not True:
            reasons.append("EXTERNAL_MERGE_ADAPTER_DISABLED")
        if integration.get("direct_main_mutation") is not False:
            reasons.append("DIRECT_MAIN_MUTATION_ENABLED")
        if integration.get("force_push") is not False:
            reasons.append("FORCE_PUSH_ENABLED")
        if integration.get("history_rewrite") is not False:
            reasons.append("HISTORY_REWRITE_ENABLED")

    if authority.get("validation") != "DENIED":
        reasons.append("VALIDATION_BOUNDARY_DRIFT")
    if authority.get("scientific_selector_model_family_candidate_theory_semantic_publication_probability_risk_exposure_trading_execution") != "NONE":
        reasons.append("RESERVED_SCIENTIFIC_OR_EXECUTION_AUTHORITY_DRIFT")

    unique = sorted(set(reasons))
    return {
        "schema": "ovc-dsai-orch2-authority-resolution/v1",
        "status": "ACTIVE_AUTHORIZED" if not unique else "BLOCK",
        "reason_codes": unique or ["EXACT_G9B_ORCH2_AUTHORITY_ACTIVE"],
        "g9b_orch2_authority": not unique,
        "packet_class": str(packet_class),
        "orchestrator_stage": "ORCH-2",
        "record_present_on_main": bool(record_present_on_main),
        "authority_effect": "READ_ONLY_RESOLUTION",
    }
