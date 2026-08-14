"""Contextual classification for development latency diagnostic receipts.

This module extends the existing temporary diagnostic observability receipt with
comparison context. The added fields are descriptive only: they do not measure
model reasoning, grant authority, or alter the identity of the source execution
record or trace summary.
"""
from __future__ import annotations

from typing import Any, Mapping

from ovc.development.diagnostic_observability import (
    DIAGNOSTIC_RECEIPT_CLASS,
    build_companion_receipt,
)
from ovc.development.identity import canonical_sha256

DIFFICULTY_CLASSES = {
    "D1": "MECHANICAL",
    "D2": "BOUNDED_IMPLEMENTATION",
    "D3": "CROSS_COMPONENT",
    "D4": "ARCHITECTURAL",
    "D5": "NOVEL_BLOCKING",
}
WORK_PHASES = frozenset(
    {"DESIGN", "IMPLEMENTATION", "TEST_QA", "RECONCILIATION", "INTEGRATION", "OTHER"}
)
SPECIFICATION_MATURITY = frozenset(
    {"UNSPECIFIED", "DESIGN_ONLY", "IMPLEMENTATION_PLAN", "RATIFIED_IMPLEMENTATION_PLAN", "WORK_PACKET_EXACT"}
)
REASONING_PROFILES = frozenset({"MEDIUM", "HIGH", "EXTRA_HIGH", "PRO", "UNKNOWN"})
CONFIG_EVIDENCE_CLASSES = frozenset({"DECLARED", "PLATFORM_REPORTED", "UNAVAILABLE"})
SCOPE_METRICS = frozenset(
    {
        "changed_files_count",
        "components_touched_count",
        "tests_run_count",
        "pr_count",
        "workflow_run_count",
        "remediation_attempt_count",
    }
)


def _normalize_scope_metrics(value: Mapping[str, Any] | None) -> dict[str, int]:
    if value is None:
        return {}
    unknown = set(value) - SCOPE_METRICS
    if unknown:
        raise ValueError(f"unsupported scope metric(s): {sorted(unknown)}")
    normalized: dict[str, int] = {}
    for key, raw in value.items():
        if isinstance(raw, bool) or not isinstance(raw, int) or raw < 0:
            raise ValueError(f"scope metric {key} must be a non-negative integer")
        normalized[str(key)] = int(raw)
    return dict(sorted(normalized.items()))


def normalize_development_context(
    *,
    implementation_difficulty: str,
    work_phase: str,
    specification_maturity: str = "UNSPECIFIED",
    classification_basis: str | None = None,
    assistant_model: str | None = None,
    reasoning_profile: str = "UNKNOWN",
    subscription_plan: str | None = None,
    assistant_configuration_evidence: str = "UNAVAILABLE",
    scope_metrics: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Validate and normalize context used for apples-to-apples latency analysis."""
    difficulty = str(implementation_difficulty).upper()
    phase = str(work_phase).upper()
    maturity = str(specification_maturity).upper()
    profile = str(reasoning_profile).upper()
    config_evidence = str(assistant_configuration_evidence).upper()

    if difficulty not in DIFFICULTY_CLASSES:
        raise ValueError("implementation_difficulty must be one of D1, D2, D3, D4, D5")
    if phase not in WORK_PHASES:
        raise ValueError(f"unsupported work_phase {phase}")
    if maturity not in SPECIFICATION_MATURITY:
        raise ValueError(f"unsupported specification_maturity {maturity}")
    if profile not in REASONING_PROFILES:
        raise ValueError(f"unsupported reasoning_profile {profile}")
    if config_evidence not in CONFIG_EVIDENCE_CLASSES:
        raise ValueError(f"unsupported assistant configuration evidence {config_evidence}")
    if profile == "UNKNOWN" and config_evidence != "UNAVAILABLE":
        raise ValueError("UNKNOWN reasoning_profile must use UNAVAILABLE configuration evidence")
    if profile != "UNKNOWN" and config_evidence == "UNAVAILABLE":
        raise ValueError("known reasoning_profile requires DECLARED or PLATFORM_REPORTED evidence")

    basis = str(classification_basis).strip() if classification_basis is not None else None
    model = str(assistant_model).strip() if assistant_model is not None else None
    plan = str(subscription_plan).strip() if subscription_plan is not None else None
    if basis == "":
        basis = None
    if model == "":
        model = None
    if plan == "":
        plan = None

    return {
        "task_profile": {
            "implementation_difficulty": difficulty,
            "difficulty_label": DIFFICULTY_CLASSES[difficulty],
            "work_phase": phase,
            "specification_maturity": maturity,
            "classification_basis": basis,
            "scope_metrics": _normalize_scope_metrics(scope_metrics),
        },
        "assistant_configuration": {
            "assistant_model": model,
            "reasoning_profile": profile,
            "subscription_plan": plan,
            "evidence_class": config_evidence,
        },
        "comparison_keys": {
            "implementation_difficulty": difficulty,
            "work_phase": phase,
            "specification_maturity": maturity,
        },
    }


def build_contextual_companion_receipt(
    *,
    source_execution_record: Mapping[str, Any],
    trace_summary: Mapping[str, Any],
    implementation_difficulty: str,
    work_phase: str,
    specification_maturity: str = "UNSPECIFIED",
    classification_basis: str | None = None,
    assistant_model: str | None = None,
    reasoning_profile: str = "UNKNOWN",
    subscription_plan: str | None = None,
    assistant_configuration_evidence: str = "UNAVAILABLE",
    scope_metrics: Mapping[str, Any] | None = None,
    observed_at_utc: str | None = None,
) -> dict[str, Any]:
    """Build a v2 latency companion with task/configuration comparison context."""
    base = build_companion_receipt(
        source_execution_record=source_execution_record,
        trace_summary=trace_summary,
        observed_at_utc=observed_at_utc,
    )
    context = normalize_development_context(
        implementation_difficulty=implementation_difficulty,
        work_phase=work_phase,
        specification_maturity=specification_maturity,
        classification_basis=classification_basis,
        assistant_model=assistant_model,
        reasoning_profile=reasoning_profile,
        subscription_plan=subscription_plan,
        assistant_configuration_evidence=assistant_configuration_evidence,
        scope_metrics=scope_metrics,
    )
    payload = {key: value for key, value in base.items() if key not in {"schema", "record_id"}}
    payload["receipt_version"] = "DEVOBS-v0.2"
    payload.update(context)
    payload["comparison_context_only"] = True
    payload["source_execution_identity_unchanged"] = True
    payload["trace_summary_identity_unchanged"] = True
    return {
        "schema": "ovc-development-latency-diagnostic-companion/v2",
        **payload,
        "record_id": canonical_sha256(
            payload,
            role="OVC_DEVELOPMENT_LATENCY_DIAGNOSTIC_COMPANION_V2",
        ),
    }


def validate_contextual_companion_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    """Validate the comparison-specific invariants of a v2 diagnostic receipt."""
    if value.get("schema") != "ovc-development-latency-diagnostic-companion/v2":
        raise ValueError("development latency companion v2 schema mismatch")
    if value.get("receipt_class") != DIAGNOSTIC_RECEIPT_CLASS:
        raise ValueError("development latency companion receipt class mismatch")
    if value.get("authority_effect") != "NONE" or value.get("comparison_context_only") is not True:
        raise ValueError("development latency comparison context must be authority-inert")
    if value.get("source_execution_identity_unchanged") is not True:
        raise ValueError("source execution identity invariant is required")
    if value.get("trace_summary_identity_unchanged") is not True:
        raise ValueError("trace summary identity invariant is required")

    profile = value.get("task_profile")
    config = value.get("assistant_configuration")
    if not isinstance(profile, Mapping) or not isinstance(config, Mapping):
        raise ValueError("task_profile and assistant_configuration are required")
    normalized = normalize_development_context(
        implementation_difficulty=str(profile.get("implementation_difficulty", "")),
        work_phase=str(profile.get("work_phase", "")),
        specification_maturity=str(profile.get("specification_maturity", "")),
        classification_basis=profile.get("classification_basis"),
        assistant_model=config.get("assistant_model"),
        reasoning_profile=str(config.get("reasoning_profile", "")),
        subscription_plan=config.get("subscription_plan"),
        assistant_configuration_evidence=str(config.get("evidence_class", "")),
        scope_metrics=profile.get("scope_metrics") if isinstance(profile.get("scope_metrics"), Mapping) else None,
    )
    for key in ("task_profile", "assistant_configuration", "comparison_keys"):
        if value.get(key) != normalized[key]:
            raise ValueError(f"development latency context drift in {key}")

    payload = {key: item for key, item in value.items() if key not in {"schema", "record_id"}}
    expected = canonical_sha256(payload, role="OVC_DEVELOPMENT_LATENCY_DIAGNOSTIC_COMPANION_V2")
    if value.get("record_id") != expected:
        raise ValueError("development latency companion v2 logical identity mismatch")
    return dict(value)
