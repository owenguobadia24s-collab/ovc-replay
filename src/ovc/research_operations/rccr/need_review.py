from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from statistics import median
from typing import Any

from .core import RCCRValidationError, logical_identity, validate_canonical_object

NEED_STATUSES = {
    "NOT_REQUIRED",
    "POSSIBLY_REQUIRED",
    "EVIDENCE_REQUIRED",
    "NEED_SUPPORTED",
    "NEED_CONTRADICTED",
    "UNRESOLVED",
}
REVIEW_ROLES = {
    "REQUIREMENT_REVIEWER",
    "OWNER_FIT_REVIEWER",
    "MINIMALITY_REVIEWER",
    "MODE_FIREWALL_REVIEWER",
    "PILOT_EXIT_REVIEWER",
}
VISIBILITY_CLASSES = {
    "PATH1_PRE_FREEZE",
    "PATH2_PRE_FREEZE",
    "CROSS_MODE_POST_FREEZE",
    "OPERATOR_RESTRICTED",
    "GENERAL_RESEARCH",
}
INDEPENDENCE_STATES = {
    "INDEPENDENT",
    "PARTIALLY_INDEPENDENT",
    "COMMON_ANCESTRY",
    "CONTAMINATED",
    "UNKNOWN",
}


class RCCRNeedReviewError(ValueError):
    pass


def _parse_time(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise RCCRNeedReviewError(f"invalid ISO timestamp: {value}") from exc
    if parsed.tzinfo is None:
        raise RCCRNeedReviewError(f"timestamp must be timezone-aware: {value}")
    return parsed.astimezone(timezone.utc)


def _seconds(start: str, end: str) -> float:
    delta = (_parse_time(end) - _parse_time(start)).total_seconds()
    if delta < 0:
        raise RCCRNeedReviewError("review time precedes queue time")
    return delta


def _candidate(candidate: dict[str, Any]) -> dict[str, str]:
    if set(candidate) != {"capability_id", "owner", "owner_contract_ref"}:
        raise RCCRNeedReviewError("one exact candidate capability/owner/contract is required")
    out = {key: str(candidate[key]) for key in ("capability_id", "owner", "owner_contract_ref")}
    if not all(out.values()):
        raise RCCRNeedReviewError("candidate capability fields must be non-empty")
    return out


class CapabilityNeedEvaluator:
    """Deterministic non-authoritative capability-need evaluator.

    Demand frequency, implementation cost and existence never contribute need-status authority.
    NEED_SUPPORTED is reachable only from a real INFORMATION_GAP plus owner-fit, exhausted
    smaller routes, QA PASS, and semantic-owner and/or shadow-closure evidence.
    """

    def evaluate(
        self,
        *,
        coverage_assessment: dict[str, Any],
        candidate_capability: dict[str, Any],
        missing_information_claim: str,
        ownership_test: dict[str, Any],
        minimality_test: dict[str, Any],
        alternative_routes: list[str],
        supporting_condition: str,
        falsifying_condition: str,
        shadow_test_route: str,
        next_owner_route: str,
        current_support: list[str] | None = None,
        current_counterevidence: list[str] | None = None,
        evidence_refs: list[str] | None = None,
        first_valid_time: str,
        qa_state: str = "PASS",
        review_state: str = "RESOLVED",
        demand_frequency: int | None = None,
        implementation_cost: float | None = None,
    ) -> dict[str, Any]:
        del demand_frequency, implementation_cost  # explicitly non-authoritative inputs
        candidate = _candidate(candidate_capability)
        if not missing_information_claim or not supporting_condition or not falsifying_condition:
            raise RCCRNeedReviewError("need claim and falsifiable conditions are mandatory")
        if not shadow_test_route or not next_owner_route:
            raise RCCRNeedReviewError("shadow and next-owner routes are mandatory")
        if not isinstance(alternative_routes, list):
            raise RCCRNeedReviewError("alternative_routes must be explicit")

        owner_fit = ownership_test.get("owner_fit", "UNRESOLVED")
        if owner_fit not in {"MATCH", "MISMATCH", "UNRESOLVED"}:
            raise RCCRNeedReviewError(f"unknown owner_fit: {owner_fit}")
        smaller_route = minimality_test.get("smaller_route_status", "UNRESOLVED")
        if smaller_route not in {"EXHAUSTED", "SMALLER_ROUTE_AVAILABLE", "UNRESOLVED"}:
            raise RCCRNeedReviewError(f"unknown smaller_route_status: {smaller_route}")
        if review_state not in {"RESOLVED", "PENDING", "CONFLICT"}:
            raise RCCRNeedReviewError(f"unknown review_state: {review_state}")

        information_gaps = []
        for gap in coverage_assessment.get("gap_assessments", []):
            if gap.get("gap_class") == "INFORMATION_GAP":
                information_gaps.append(
                    str(gap.get("gap_id") or gap.get("requirement_id") or "INFORMATION_GAP")
                )
        counterevidence = sorted(set(current_counterevidence or []))
        support = sorted(set(current_support or []))
        semantic_evidence = sorted(set(ownership_test.get("semantic_ownership_evidence", [])))
        shadow_evidence = sorted(set(minimality_test.get("shadow_closure_evidence", [])))

        if counterevidence:
            status = "NEED_CONTRADICTED"
        elif review_state == "CONFLICT":
            status = "UNRESOLVED"
        elif not information_gaps:
            status = "NOT_REQUIRED"
        elif owner_fit == "MISMATCH" or smaller_route == "SMALLER_ROUTE_AVAILABLE":
            status = "NOT_REQUIRED"
        elif owner_fit == "UNRESOLVED":
            status = "POSSIBLY_REQUIRED"
        elif review_state == "PENDING" or smaller_route == "UNRESOLVED" or qa_state != "PASS":
            status = "EVIDENCE_REQUIRED"
        elif semantic_evidence or shadow_evidence:
            status = "NEED_SUPPORTED"
        else:
            status = "EVIDENCE_REQUIRED"

        record: dict[str, Any] = {
            "schema_version": "0.1",
            "capability_need_assessment_id": "",
            "source_coverage_assessment_id": str(coverage_assessment["coverage_assessment_id"]),
            "source_gap_ids": sorted(information_gaps),
            "candidate_capability": candidate,
            "missing_information_claim": missing_information_claim,
            "ownership_test": deepcopy(ownership_test),
            "minimality_test": deepcopy(minimality_test),
            "alternative_routes": sorted(set(str(item) for item in alternative_routes)),
            "need_status": status,
            "supporting_condition": supporting_condition,
            "falsifying_condition": falsifying_condition,
            "current_support": support,
            "current_counterevidence": counterevidence,
            "shadow_test_route": shadow_test_route,
            "next_owner_route": next_owner_route,
            "authority_requested": "NONE",
            "authority_effect": "NONE",
            "evidence_refs": sorted(set(evidence_refs or [])),
            "first_valid_time": first_valid_time,
        }
        record["capability_need_assessment_id"] = logical_identity("CapabilityNeedAssessment", record)
        validate_canonical_object("CapabilityNeedAssessment", record)
        return record


class ModeVisibilityFirewall:
    """RCCR projection of the DMRP visibility/exposure firewall.

    Absence of a contamination record never upgrades independence; UNKNOWN is the default.
    """

    def evaluate(
        self,
        *,
        consumer_visibility: str,
        source_visibility: str,
        candidate_defining: bool = True,
        exposure_recorded: bool = False,
        post_freeze: bool = False,
        operator: bool = False,
        decision_bearing: bool = False,
        influence_recorded: bool = False,
        declared_independence: str | None = None,
    ) -> dict[str, Any]:
        if consumer_visibility not in VISIBILITY_CLASSES or source_visibility not in VISIBILITY_CLASSES:
            raise RCCRNeedReviewError("unknown visibility class")
        independence = declared_independence or "UNKNOWN"
        if independence not in INDEPENDENCE_STATES:
            raise RCCRNeedReviewError("unknown independence state")

        disposition = "ALLOW"
        reason = "VISIBILITY_COMPATIBLE"
        inspection_allowed = True
        decision_use_allowed = True

        if consumer_visibility == "PATH1_PRE_FREEZE" and source_visibility == "PATH2_PRE_FREEZE" and candidate_defining:
            disposition, reason, decision_use_allowed = "DENY", "PATH2_TO_PATH1_PRE_FREEZE_LEAK", False
        elif consumer_visibility == "PATH2_PRE_FREEZE" and source_visibility == "PATH1_PRE_FREEZE" and candidate_defining and not exposure_recorded:
            disposition, reason, decision_use_allowed = "DENY", "PATH1_TO_PATH2_PRE_FREEZE_LEAK", False
        elif "CROSS_MODE_POST_FREEZE" in {consumer_visibility, source_visibility} and not (post_freeze and exposure_recorded):
            disposition, reason, decision_use_allowed = "DENY", "CROSS_MODE_FREEZE_OR_EXPOSURE_MISSING", False
        elif consumer_visibility == "OPERATOR_RESTRICTED":
            if not operator:
                disposition, reason, inspection_allowed, decision_use_allowed = "DENY", "OPERATOR_ROLE_REQUIRED", False, False
            elif decision_bearing and not influence_recorded:
                disposition, reason, decision_use_allowed = "INSPECT_ONLY", "MATERIAL_INFLUENCE_RECORD_REQUIRED", False
        elif source_visibility == "GENERAL_RESEARCH" and not candidate_defining:
            disposition, reason = "ALLOW", "GENERAL_NON_CANDIDATE_RESEARCH"

        return {
            "disposition": disposition,
            "reason": reason,
            "inspection_allowed": inspection_allowed,
            "decision_use_allowed": decision_use_allowed,
            "origin_convergence": independence,
            "authority_effect": "NONE",
        }


class HumanReviewLedger:
    """Append-only in-memory adapter used by the bounded RCCR review workflow."""

    def __init__(self) -> None:
        self._queue: dict[str, dict[str, Any]] = {}
        self._completed: dict[str, dict[str, Any]] = {}

    def enqueue(
        self,
        *,
        review_id: str,
        review_role: str,
        subject_id: str,
        reviewer_id: str,
        input_refs: list[str],
        queued_at: str,
        conflict_disclosure: str = "NONE",
        common_ancestry_disclosure: str = "UNKNOWN",
        reopen_of: str | None = None,
    ) -> dict[str, Any]:
        if review_role not in REVIEW_ROLES:
            raise RCCRNeedReviewError("unknown review role")
        if not review_id or review_id in self._queue or review_id in self._completed:
            raise RCCRNeedReviewError("review_id must be unique and non-empty")
        _parse_time(queued_at)
        record = {
            "review_id": review_id,
            "review_role": review_role,
            "subject_id": subject_id,
            "reviewer_id": reviewer_id,
            "input_refs": sorted(set(input_refs)),
            "queued_at": queued_at,
            "conflict_disclosure": conflict_disclosure,
            "common_ancestry_disclosure": common_ancestry_disclosure,
            "reopen_of": reopen_of,
            "authority_effect": "NONE",
        }
        self._queue[review_id] = record
        return deepcopy(record)

    def complete(
        self,
        *,
        review_id: str,
        decision: str,
        rationale: str,
        reviewed_at: str,
        resolution_authority: str,
        first_valid_time: str,
        counterevidence: list[str] | None = None,
        reopen_evidence: list[str] | None = None,
    ) -> dict[str, Any]:
        if review_id not in self._queue:
            raise RCCRNeedReviewError("review must be queued exactly once before completion")
        queued = self._queue.pop(review_id)
        latency = _seconds(queued["queued_at"], reviewed_at)
        _parse_time(first_valid_time)
        if not decision or not rationale or not resolution_authority:
            raise RCCRNeedReviewError("decision, rationale and resolution authority are mandatory")
        record = {
            **queued,
            "decision": decision,
            "rationale": rationale,
            "reviewed_at": reviewed_at,
            "resolution_authority": resolution_authority,
            "first_valid_time": first_valid_time,
            "counterevidence": sorted(set(counterevidence or [])),
            "reopen_evidence": sorted(set(reopen_evidence or [])),
            "review_latency_seconds": latency,
        }
        self._completed[review_id] = record
        return deepcopy(record)

    def subject_disposition(self, *, subject_id: str, review_role: str) -> dict[str, Any]:
        rows = [
            row for row in self._completed.values()
            if row["subject_id"] == subject_id and row["review_role"] == review_role
        ]
        decisions = sorted(set(row["decision"] for row in rows))
        if len(decisions) > 1:
            return {
                "status": "UNRESOLVED",
                "reason": "REVIEWER_CONFLICT_NO_MAJORITY_VOTE",
                "decisions": decisions,
                "escalation_required": True,
                "authority_effect": "NONE",
            }
        if not decisions:
            return {
                "status": "PENDING",
                "reason": "NO_COMPLETED_REVIEW",
                "decisions": [],
                "escalation_required": False,
                "authority_effect": "NONE",
            }
        return {
            "status": "RESOLVED",
            "reason": "ELIGIBLE_REVIEW_CONVERGED",
            "decisions": decisions,
            "escalation_required": False,
            "authority_effect": "NONE",
        }

    def telemetry(self, *, cutoff: str) -> dict[str, Any]:
        _parse_time(cutoff)
        completed = list(self._completed.values())
        pending = list(self._queue.values())
        latencies = [float(row["review_latency_seconds"]) for row in completed]
        pending_ages = [_seconds(row["queued_at"], cutoff) for row in pending]
        subjects = sorted(set((row["subject_id"], row["review_role"]) for row in completed))
        conflicts = sum(
            1 for subject_id, role in subjects
            if self.subject_disposition(subject_id=subject_id, review_role=role)["status"] == "UNRESOLVED"
        )
        reopen_count = sum(1 for row in completed + pending if row.get("reopen_of"))
        per_role: dict[str, Any] = {}
        for role in sorted(REVIEW_ROLES):
            role_rows = [row for row in completed if row["review_role"] == role]
            role_latencies = [float(row["review_latency_seconds"]) for row in role_rows]
            per_role[role] = {
                "completed_count": len(role_rows),
                "latency_denominator": len(role_latencies),
                "median_latency_seconds": median(role_latencies) if role_latencies else None,
                "tail_latency_seconds": max(role_latencies) if role_latencies else None,
            }
        denominator = len(completed) + len(pending)
        return {
            "review_route_count": denominator,
            "completed_count": len(completed),
            "pending_count": len(pending),
            "latency_denominator": len(latencies),
            "median_review_latency_seconds": median(latencies) if latencies else None,
            "tail_review_latency_seconds": max(latencies) if latencies else None,
            "pending_queue_age_denominator": len(pending_ages),
            "median_pending_queue_age_seconds": median(pending_ages) if pending_ages else None,
            "tail_pending_queue_age_seconds": max(pending_ages) if pending_ages else None,
            "reopen_count": reopen_count,
            "reopen_rate_denominator": denominator,
            "reopen_rate": (reopen_count / denominator) if denominator else None,
            "reviewer_conflict_count": conflicts,
            "unresolved_subject_count": conflicts,
            "operator_escalation_count": conflicts,
            "per_role": per_role,
            "metric_use": "DESCRIPTIVE_DIAGNOSTIC_ONLY",
            "authority_effect": "NONE",
        }


class OffRegisterWorkaroundDetector:
    """Detects read-only workflow pressure before any Console-facing binding."""

    def __init__(self) -> None:
        self._route_attempts = 0
        self._records: list[dict[str, Any]] = []

    def record_route_attempt(self) -> None:
        self._route_attempts += 1

    def record_workaround(
        self,
        *,
        workaround_id: str,
        attempted_route: str,
        blocked_cause: str,
        workaround_class: str,
        burden: str,
        resolution: str,
        escalation: str,
        first_valid_time: str,
        decision_bearing_external_rationale: bool = False,
        rationale_provenance_ref: str | None = None,
    ) -> dict[str, Any]:
        if not all([workaround_id, attempted_route, blocked_cause, workaround_class, burden, resolution, escalation]):
            raise RCCRNeedReviewError("workaround record fields are mandatory")
        if decision_bearing_external_rationale and not rationale_provenance_ref:
            raise RCCRNeedReviewError("decision-bearing external rationale requires provenance before use")
        _parse_time(first_valid_time)
        if any(row["workaround_id"] == workaround_id for row in self._records):
            raise RCCRNeedReviewError("workaround_id is append-only unique")
        record = {
            "workaround_id": workaround_id,
            "attempted_route": attempted_route,
            "blocked_cause": blocked_cause,
            "workaround_class": workaround_class,
            "burden": burden,
            "resolution": resolution,
            "escalation": escalation,
            "first_valid_time": first_valid_time,
            "decision_bearing_external_rationale": decision_bearing_external_rationale,
            "rationale_provenance_ref": rationale_provenance_ref,
            "authority_effect": "NONE",
        }
        self._records.append(record)
        return deepcopy(record)

    def summary(self) -> dict[str, Any]:
        by_class: dict[str, int] = {}
        for row in self._records:
            by_class[row["workaround_class"]] = by_class.get(row["workaround_class"], 0) + 1
        denominator = self._route_attempts
        return {
            "route_attempt_denominator": denominator,
            "workaround_count": len(self._records),
            "workaround_rate": (len(self._records) / denominator) if denominator else None,
            "workaround_class_counts": dict(sorted(by_class.items())),
            "detected": bool(self._records),
            "metric_use": "OPERATIONAL_DIAGNOSTIC_ONLY",
            "authority_effect": "NONE",
        }
