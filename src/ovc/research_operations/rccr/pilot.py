from __future__ import annotations

import hashlib
from copy import deepcopy
from datetime import datetime, timezone
from statistics import median
from typing import Any, Iterable, Mapping

from .core import canonical_json_bytes, logical_identity, validate_canonical_object

EC1_PILOT_QUESTIONS = tuple(f"EC1-Q{i:02d}" for i in range(1, 11))
ADVERSARIAL_CASES = tuple(f"AV{i:02d}" for i in range(1, 25))
GOLDEN_CASES = tuple(f"G{i:02d}" for i in range(1, 13))
GOLDEN_EXPECTED = {
    "G01": "CURRENT_STACK_SUFFICIENT",
    "G02": "METHOD_GAP",
    "G03": "DENOMINATOR_GAP",
    "G04": "DATA_GAP",
    "G05": "OWNER_SEMANTICS_GAP",
    "G06": "IMPLEMENTATION_GAP",
    "G07": "AUTHORITY_GAP",
    "G08": "PROTOCOL_EXCLUSION",
    "G09": "GENUINE_INFORMATION_GAP",
    "G10": "UNRESOLVED_GAP",
    "G11": "NEED_SUPPORTED",
    "G12": "NEED_CONTRADICTED",
}
AV_EXPECTED = {
    "AV01": "DISTINCT_SOURCE_GENERATION",
    "AV02": "SEMANTIC_EQUIVALENCE_PRESERVES_GENERATION_WITH_ARTIFACT_PROVENANCE",
    "AV03": "OWNER_FIT_UNRESOLVED_NO_CAPABILITY_NEED",
    "AV04": "METHOD_GAP",
    "AV05": "DENOMINATOR_GAP",
    "AV06": "ZERO_SUPPORTED_DEMAND",
    "AV07": "NO_NEED_STATUS_INCREASE",
    "AV08": "PROTOCOL_EXCLUSION_SELF_INDUCED",
    "AV09": "AUTHORITY_GAP",
    "AV10": "DATA_GAP",
    "AV11": "CAPABILITY_OVERBROAD_SMALLER_ROUTE_FIRST",
    "AV12": "INFORMATION_GAP_C2P_ASSESSMENT_ALLOWED",
    "AV13": "METHOD_DERIVATION_FIRST_NO_AUTOMATIC_C3_NEED",
    "AV14": "VISIBILITY_DENY_OR_CONTAMINATION",
    "AV15": "SUCCESSOR_PROTOCOL_OR_GENERATION_REQUIRED",
    "AV16": "COMMON_ANCESTRY_NOT_INDEPENDENT_CONFIRMATION",
    "AV17": "INDEPENDENCE_UNKNOWN",
    "AV18": "OLD_ASSESSMENT_HISTORICAL_VALID",
    "AV19": "EXPLICIT_CORRECTION_LINEAGE",
    "AV20": "QUARANTINE_PRESERVE_HISTORY_EXCLUDE_CURRENT",
    "AV21": "VIEW_SEPARATES_IMPLEMENTED_AND_ACTIVE",
    "AV22": "SCALAR_COVERAGE_SCORE_DENIED",
    "AV23": "NEGATIVE_EVIDENCE_PARITY_REQUIRED",
    "AV24": "CIRCULAR_SOURCE_DENIED",
}


class RCCRPilotError(ValueError):
    pass


def _parse_time(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise RCCRPilotError(f"invalid ISO timestamp: {value}") from exc
    if parsed.tzinfo is None:
        raise RCCRPilotError(f"timestamp must be timezone-aware: {value}")
    return parsed.astimezone(timezone.utc)


def _sha(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def bind_ec1_pilot_questions(
    *,
    question_registry: Mapping[str, Any],
    evidence_registry: Mapping[str, Any],
    question_registry_ref: str,
    question_registry_blob_sha: str,
    evidence_registry_ref: str,
    evidence_registry_blob_sha: str,
    source_first_valid_time: str,
    capability_frontier_id: str,
    qa_receipt: str,
) -> dict[str, Any]:
    """Bind exact Q01-Q10 definitions for RCCR mechanism qualification only.

    The result deliberately does not consume E1/R1 evidence and does not answer EC1 science.
    """

    _parse_time(source_first_valid_time)
    if question_registry.get("authority_effect") != "NONE":
        raise RCCRPilotError("question registry authority must be NONE")
    if evidence_registry.get("authority_effect") != "NONE":
        raise RCCRPilotError("evidence-requirement registry authority must be NONE")
    if question_registry.get("cycle_id") != evidence_registry.get("cycle_id"):
        raise RCCRPilotError("EC1 cycle mismatch")
    questions = {row["question_id"]: dict(row) for row in question_registry.get("questions", [])}
    evidence = {row["question_id"]: dict(row) for row in evidence_registry.get("questions", [])}
    if tuple(sorted(questions)) != EC1_PILOT_QUESTIONS or tuple(sorted(evidence)) != EC1_PILOT_QUESTIONS:
        raise RCCRPilotError("pilot requires exact EC1-Q01..Q10 population")

    records: list[dict[str, Any]] = []
    for question_id in EC1_PILOT_QUESTIONS:
        q = questions[question_id]
        e = evidence[question_id]
        if q.get("text") != e.get("canonical_question"):
            raise RCCRPilotError(f"canonical question mismatch: {question_id}")
        source_identity = {
            "question_id": question_id,
            "cycle_id": question_registry["cycle_id"],
            "question_registry_ref": question_registry_ref,
            "question_registry_blob_sha": question_registry_blob_sha,
            "evidence_registry_ref": evidence_registry_ref,
            "evidence_registry_blob_sha": evidence_registry_blob_sha,
            "question": q,
            "requirements": e,
        }
        binding_id = f"rccr-pilot:{question_id}:{_sha(source_identity)}"
        records.append(
            {
                "question_id": question_id,
                "binding_id": binding_id,
                "source_identity": source_identity,
                "requirement_record": {
                    "canonical_question": e["canonical_question"],
                    "population": e["population"],
                    "evidence_families": sorted(e["evidence_families"]),
                    "information_dimension_roles": dict(sorted(e["information_dimension_roles"].items())),
                    "derivation": "SOURCE_EXPLICIT_NO_SEMANTIC_INVENTION",
                },
                "frontier_record": {
                    "capability_frontier_id": capability_frontier_id,
                    "real_source_ec1_authority": "NONE",
                    "use": "CURRENT_OWNER_STATE_FOR_MECHANISM_QUALIFICATION_ONLY",
                },
                "assessment_record": {
                    "assessment_class": "PRE_EVIDENTIARY_RCCR_MECHANISM_QUALIFICATION",
                    "ec1_scientific_answer": "NOT_PRODUCED",
                    "real_source_evidence_consumed": False,
                    "unsupported_information_gap_promoted": False,
                    "blocking_condition": "DMRPI-GREAL-EC1_AUTHORITY_NONE",
                    "lawful_next_route": "WAIT_FOR_SEPARATE_EC1_REAL_SOURCE_AUTHORITY_AND_E1_R1",
                },
                "authority_effect": "NONE",
            }
        )

    resolution_manifest = {
        "schema": "ovc-rccri-ec1-pilot-source-resolution/v1",
        "cycle_id": question_registry["cycle_id"],
        "question_count": len(records),
        "question_bindings": [row["binding_id"] for row in records],
        "protected_payloads_opened": False,
        "real_source_ec1_evidence_consumed": False,
        "authority_effect": "NONE",
    }
    resolution_manifest["manifest_hash"] = _sha(resolution_manifest)
    semantic_hash = _sha(
        {
            "question_bindings": records,
            "capability_frontier_id": capability_frontier_id,
            "mode": "PATH1_PRE_FREEZE_RCCR_MECHANISM_ONLY",
        }
    )
    bootstrap: dict[str, Any] = {
        "schema_version": "0.1",
        "bootstrap_id": "PENDING",
        "evaluation_cutoff": source_first_valid_time,
        "source_resolution_manifest": resolution_manifest["manifest_hash"],
        "admitted_source_classes": ["EC1_QUESTION", "EC1_PRE_EVIDENTIARY_REQUIREMENT"],
        "included_item_refs": [row["binding_id"] for row in records],
        "excluded_item_refs": ["REAL_SOURCE_EC1_E1_R1_OUTPUTS", "VALIDATION_PROTECTED_CONTENT"],
        "exclusion_reasons": ["REAL_SOURCE_EC1_AUTHORITY_NONE", "VALIDATION_LOCKED_UNCONSUMED"],
        "capability_frontier_id": capability_frontier_id,
        "mode_visibility_bindings": [
            {
                "research_mode": "PATH1",
                "visibility_class": "PATH1_PRE_FREEZE",
                "decision_bearing_scope": "RCCR_MECHANISM_QUALIFICATION_ONLY",
            }
        ],
        "QA_receipt": qa_receipt,
        "semantic_hash": semantic_hash,
        "first_valid_time": source_first_valid_time,
        "authority_effect": "NONE",
    }
    bootstrap["bootstrap_id"] = logical_identity("RCCRBootstrapManifest", bootstrap)
    validate_canonical_object("RCCRBootstrapManifest", bootstrap)
    return {
        "bootstrap_manifest": bootstrap,
        "source_resolution_manifest": resolution_manifest,
        "question_records": records,
        "authority_effect": "NONE",
    }


def validate_fixture_currentness(
    *,
    fixtures: Iterable[Mapping[str, Any]],
    current_dependencies: Mapping[str, str],
    checked_at: str,
) -> dict[str, Any]:
    _parse_time(checked_at)
    rows: list[dict[str, Any]] = []
    for raw in fixtures:
        fixture = dict(raw)
        fixture_id = str(fixture.get("fixture_id") or fixture.get("case_id") or "")
        if not fixture_id:
            raise RCCRPilotError("fixture identity required")
        bound = dict(fixture.get("dependency_digests", {}))
        stale = sorted(
            key for key, digest in bound.items()
            if current_dependencies.get(key) != digest
        )
        rows.append(
            {
                "fixture_id": fixture_id,
                "currentness": "STALE" if stale else "CURRENT",
                "stale_dependencies": stale,
                "action": "SUCCESSOR_GENERATION_REQUIRED" if stale else "NONE",
                "authority_effect": "NONE",
            }
        )
    status = "PASS" if all(row["currentness"] == "CURRENT" for row in rows) else "BLOCK"
    return {
        "schema": "ovc-rccri-fixture-currentness-manifest/v1",
        "checked_at": checked_at,
        "fixtures": rows,
        "status": status,
        "stale_fixture_rewrite_forbidden": True,
        "authority_effect": "NONE",
    }


def validate_historical_counterfactual(
    *,
    case_id: str,
    decision_cutoff: str,
    artifact_refs: Iterable[Mapping[str, Any]],
    expected_limiting_class: str,
    source_time_complete: bool,
    hindsight_refs: Iterable[str] = (),
) -> dict[str, Any]:
    cutoff = _parse_time(decision_cutoff)
    artifacts = [dict(row) for row in artifact_refs]
    unavailable_reasons: list[str] = []
    for row in artifacts:
        ref = str(row.get("ref", ""))
        available_at = row.get("available_at")
        if not ref or not available_at:
            unavailable_reasons.append("MISSING_SOURCE_TIME_METADATA")
            continue
        if _parse_time(str(available_at)) > cutoff:
            unavailable_reasons.append(f"POST_CUTOFF_ARTIFACT:{ref}")
    hindsight = sorted(set(str(ref) for ref in hindsight_refs))
    if hindsight:
        unavailable_reasons.append("HINDSIGHT_INPUT_PRESENT")
    if not source_time_complete:
        unavailable_reasons.append("SOURCE_TIME_INCOMPLETE")
    status = "NOT_AVAILABLE" if unavailable_reasons else "SOURCE_TIME_BOUND"
    return {
        "case_id": case_id,
        "decision_cutoff": decision_cutoff,
        "artifact_refs": artifacts,
        "expected_limiting_class": expected_limiting_class,
        "source_time_complete": source_time_complete,
        "hindsight_refs": hindsight,
        "status": status,
        "unavailable_reasons": sorted(set(unavailable_reasons)),
        "hindsight_excluded": not hindsight,
        "authority_effect": "NONE",
    }


class PilotAssuranceRunner:
    """Checks complete AV01-AV24 and G01-G12 execution receipts without silent sampling."""

    def evaluate(self, receipts: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
        by_case: dict[str, dict[str, Any]] = {}
        for raw in receipts:
            row = dict(raw)
            case_id = str(row.get("case_id", ""))
            if case_id in by_case:
                raise RCCRPilotError(f"duplicate assurance case: {case_id}")
            by_case[case_id] = row
        expected_ids = set(ADVERSARIAL_CASES) | set(GOLDEN_CASES)
        actual_ids = set(by_case)
        if actual_ids != expected_ids:
            missing = sorted(expected_ids - actual_ids)
            extra = sorted(actual_ids - expected_ids)
            raise RCCRPilotError(f"full assurance population required; missing={missing}; extra={extra}")

        failures: list[str] = []
        unsupported_information_gap = 0
        for case_id in ADVERSARIAL_CASES:
            row = by_case[case_id]
            if row.get("actual") != AV_EXPECTED[case_id] or row.get("authority_effect") != "NONE":
                failures.append(case_id)
            unsupported_information_gap += int(bool(row.get("unsupported_information_gap_promoted", False)))
        for case_id in GOLDEN_CASES:
            row = by_case[case_id]
            if row.get("actual") != GOLDEN_EXPECTED[case_id] or row.get("authority_effect") != "NONE":
                failures.append(case_id)
            unsupported_information_gap += int(bool(row.get("unsupported_information_gap_promoted", False)))
        if unsupported_information_gap:
            failures.append("UNSUPPORTED_INFORMATION_GAP_PROMOTION")
        return {
            "schema": "ovc-rccri-pilot-assurance-result/v1",
            "adversarial_denominator": len(ADVERSARIAL_CASES),
            "golden_denominator": len(GOLDEN_CASES),
            "executed_count": len(by_case),
            "failures": sorted(set(failures)),
            "unsupported_information_gap_promotions": unsupported_information_gap,
            "status": "PASS" if not failures else "QUARANTINE",
            "silent_sampling": False,
            "authority_effect": "NONE",
        }


def pilot_review_load_summary(*, admitted_assessment_count: int, human_review_rows: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    if admitted_assessment_count < 0:
        raise RCCRPilotError("admitted assessment denominator cannot be negative")
    rows = [dict(row) for row in human_review_rows]
    human_count = len(rows)
    share = (human_count / admitted_assessment_count) if admitted_assessment_count else None
    latencies = [float(row["review_latency_seconds"]) for row in rows if row.get("review_latency_seconds") is not None]
    conflicts = sum(1 for row in rows if row.get("conflict") is True)
    reopens = sum(1 for row in rows if row.get("reopened") is True)
    operator_escalations = sum(1 for row in rows if row.get("operator_escalation") is True)
    trigger = bool(share is not None and share > 0.30)
    return {
        "schema": "ovc-rccri-pilot-review-load-ledger/v1",
        "admitted_assessment_denominator": admitted_assessment_count,
        "human_review_required_count": human_count,
        "human_review_required_share": share,
        "latency_denominator": len(latencies),
        "median_latency_seconds": median(latencies) if latencies else None,
        "tail_latency_seconds": max(latencies) if latencies else None,
        "reviewer_conflict_count": conflicts,
        "reopen_count": reopens,
        "operator_escalation_count": operator_escalations,
        "review_trigger_over_30_percent": trigger,
        "default_scaleout_recommendation": "DEFER" if trigger else "NO_TRIGGER",
        "threshold_use": "OPERATIONAL_PILOT_TRIGGER_ONLY_NOT_SCIENTIFIC",
        "authority_effect": "NONE",
    }


def fixture_authorship_actuals(*, planning_estimate_ref: str, automated_execution_receipts: Iterable[str]) -> dict[str, Any]:
    """Never invent human person-day actuals when telemetry is unavailable."""
    return {
        "schema": "ovc-rccri-fixture-authorship-actuals/v1",
        "planning_estimate_ref": planning_estimate_ref,
        "automated_execution_receipts": sorted(set(str(ref) for ref in automated_execution_receipts)),
        "human_person_day_actuals": None,
        "human_actuals_status": "UNAVAILABLE_NOT_INSTRUMENTED",
        "independent_reviewer_effort": None,
        "independent_reviewer_effort_status": "PENDING_OPERATOR_REVIEW",
        "estimate_is_not_schedule_slo": True,
        "authority_effect": "NONE",
    }
