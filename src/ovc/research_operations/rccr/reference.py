from __future__ import annotations

from copy import deepcopy
from typing import Any, Iterable, Mapping

from .core import RCCRValidationError, canonical_json_bytes, logical_identity, validate_canonical_object

REFERENCE_RULE_PACK_ID = "RCCR-REFERENCE-v0.1"
REQUIREMENT_FIELDS = (
    "epistemic_requirements",
    "evidence_requirements",
    "population_requirements",
    "chronology_requirements",
    "inferential_requirements",
    "denominator_requirements",
    "comparability_requirements",
)
RESULT_STATES = {
    "SATISFIED",
    "PARTIALLY_SATISFIED",
    "UNSATISFIED",
    "NOT_EVALUABLE",
    "EXCLUDED_BY_PROTOCOL",
    "OUT_OF_SCOPE",
}
GAP_CLASSES = {
    "NONE",
    "METHOD_GAP",
    "INFORMATION_GAP",
    "OWNER_SEMANTICS_GAP",
    "DATA_GAP",
    "DENOMINATOR_GAP",
    "IMPLEMENTATION_GAP",
    "AUTHORITY_GAP",
    "PROTOCOL_EXCLUSION",
    "CAPACITY_GAP",
    "REVIEW_GAP",
    "UNRESOLVED_GAP",
    "OUT_OF_SCOPE",
}

# Lower index wins. INFORMATION_GAP is intentionally last.
DIAGNOSTIC_PRECEDENCE = (
    "PROTOCOL_INVALID",
    "OUT_OF_SCOPE",
    "PROTOCOL_EXCLUSION",
    "METHOD_INFORMATION_ENTANGLED",
    "METHOD_GAP",
    "CAPACITY_GAP",
    "REVIEW_GAP",
    "DENOMINATOR_GAP",
    "OWNER_SEMANTICS_GAP",
    "IMPLEMENTATION_GAP",
    "AUTHORITY_GAP",
    "DATA_GAP",
    "INFORMATION_GAP",
)
FLAG_TO_GAP = {
    "PROTOCOL_INVALID": "PROTOCOL_EXCLUSION",
    "OUT_OF_SCOPE": "OUT_OF_SCOPE",
    "PROTOCOL_EXCLUSION": "PROTOCOL_EXCLUSION",
    "METHOD_INFORMATION_ENTANGLED": "UNRESOLVED_GAP",
    "METHOD_GAP": "METHOD_GAP",
    "CAPACITY_GAP": "CAPACITY_GAP",
    "REVIEW_GAP": "REVIEW_GAP",
    "DENOMINATOR_GAP": "DENOMINATOR_GAP",
    "OWNER_SEMANTICS_GAP": "OWNER_SEMANTICS_GAP",
    "IMPLEMENTATION_GAP": "IMPLEMENTATION_GAP",
    "AUTHORITY_GAP": "AUTHORITY_GAP",
    "DATA_GAP": "DATA_GAP",
    "INFORMATION_GAP": "INFORMATION_GAP",
}


def _required_items(profile: Mapping[str, Any]) -> list[str]:
    values: set[str] = set()
    for field in REQUIREMENT_FIELDS:
        for value in profile.get(field, ()):
            values.add(str(value))
    return sorted(values)


def _diagnose(flags: Iterable[str]) -> tuple[str, str, list[str]]:
    normalized = sorted(set(str(flag) for flag in flags))
    chosen = next((flag for flag in DIAGNOSTIC_PRECEDENCE if flag in normalized), None)
    if chosen is None:
        return "NONE", "NO_GAP_SIGNAL", normalized
    if chosen == "INFORMATION_GAP" and "COUNTERFACTUAL_EXHAUSTED" not in normalized:
        return "UNRESOLVED_GAP", "INFORMATION_GAP_COUNTERFACTUAL_NOT_EXHAUSTED", normalized
    if chosen == "METHOD_INFORMATION_ENTANGLED":
        return "UNRESOLVED_GAP", "METHOD_INFORMATION_ENTANGLED", normalized
    return FLAG_TO_GAP[chosen], chosen, normalized


class RCCRReferenceEngine:
    """Deterministic requirement-level coverage/gap evaluator.

    It does not assign scalar coverage, infer owner semantics, promote a capability, or treat
    implementation/availability as authority. Information absence is a last-resort diagnostic.
    """

    def assess(
        self,
        *,
        coverage_item_generation_id: str,
        requirement_profile: Mapping[str, Any],
        capability_frontier: Mapping[str, Any],
        requirement_evidence: Mapping[str, Mapping[str, Any]],
        evaluation_cutoff: str,
        protocol_state: str = "VALID",
        lawful_next_route: str = "RESEARCH_OPERATIONS_REVIEW",
        earliest_lawful_research_stage: str = "PRE_EVIDENTIARY",
        first_valid_time: str | None = None,
        supersedes_assessment_id: str | None = None,
    ) -> dict[str, Any]:
        if protocol_state not in {"VALID", "INVALID", "OUT_OF_SCOPE", "EXCLUDED"}:
            raise RCCRValidationError("UNKNOWN_PROTOCOL_STATE", protocol_state)
        required = _required_items(requirement_profile)
        rows: list[dict[str, Any]] = []
        gaps: list[dict[str, Any]] = []
        evidence_refs: set[str] = {
            str(requirement_profile["requirement_profile_id"]),
            str(capability_frontier["capability_frontier_id"]),
        }
        blocking: set[str] = set()
        for requirement_id in required:
            item = deepcopy(dict(requirement_evidence.get(requirement_id, {})))
            result = item.get("result", "NOT_EVALUABLE")
            if result not in RESULT_STATES:
                raise RCCRValidationError("UNKNOWN_REQUIREMENT_RESULT", f"{requirement_id}:{result}")
            flags = set(str(flag) for flag in item.get("flags", ()))
            if not item:
                flags.add("MISSING_REQUIREMENT_EVIDENCE")
            if protocol_state == "INVALID":
                flags.add("PROTOCOL_INVALID")
                result = "EXCLUDED_BY_PROTOCOL"
            elif protocol_state == "OUT_OF_SCOPE":
                flags.add("OUT_OF_SCOPE")
                result = "OUT_OF_SCOPE"
            elif protocol_state == "EXCLUDED":
                flags.add("PROTOCOL_EXCLUSION")
                result = "EXCLUDED_BY_PROTOCOL"
            if "MISSING_REQUIREMENT_EVIDENCE" in flags and not any(flag in DIAGNOSTIC_PRECEDENCE for flag in flags):
                gap_class, reason, normalized_flags = "UNRESOLVED_GAP", "MISSING_REQUIREMENT_EVIDENCE", sorted(flags)
            elif result == "SATISFIED" and not any(flag in DIAGNOSTIC_PRECEDENCE for flag in flags):
                gap_class, reason, normalized_flags = "NONE", "NO_GAP_SIGNAL", sorted(flags)
            else:
                gap_class, reason, normalized_flags = _diagnose(flags)
                if gap_class == "NONE" and result != "SATISFIED":
                    gap_class, reason = "UNRESOLVED_GAP", "RESULT_WITHOUT_DIAGNOSTIC"
            refs = sorted(set(str(ref) for ref in item.get("evidence_refs", ())))
            evidence_refs.update(refs)
            trace = [
                {"step": "RESULT", "value": result},
                {"step": "FLAGS", "value": normalized_flags},
                {"step": "DIAGNOSTIC_PRECEDENCE", "value": list(DIAGNOSTIC_PRECEDENCE)},
                {"step": "SELECTED_GAP", "value": gap_class},
                {"step": "REASON", "value": reason},
            ]
            rows.append(
                {
                    "requirement_id": requirement_id,
                    "result": result,
                    "gap_class": gap_class,
                    "reason": reason,
                    "evidence_refs": refs,
                    "decision_trace": trace,
                    "authority_effect": "NONE",
                }
            )
            if gap_class != "NONE":
                gap_id = f"gap:{requirement_id}:{gap_class}:{reason}"
                gaps.append(
                    {
                        "gap_id": gap_id,
                        "requirement_id": requirement_id,
                        "gap_class": gap_class,
                        "reason": reason,
                        "flags": normalized_flags,
                        "authority_effect": "NONE",
                    }
                )
                if gap_class in {"UNRESOLVED_GAP", "REVIEW_GAP"}:
                    blocking.add(reason)
        results = [row["result"] for row in rows]
        gap_classes = [row["gap_class"] for row in rows]
        if protocol_state == "OUT_OF_SCOPE":
            answerability, coverage = "OUT_OF_SCOPE_CURRENT_PROTOCOL", "NOT_APPLICABLE"
        elif protocol_state == "INVALID":
            answerability, coverage = "INVALID_QUESTION_CURRENT_PROTOCOL", "NOT_APPLICABLE"
        elif protocol_state == "EXCLUDED":
            answerability, coverage = "NOT_ANSWERABLE_CURRENT_FRONTIER", "NONE"
        elif rows and all(value == "SATISFIED" for value in results):
            answerability, coverage = "FULLY_ANSWERABLE", "FULL"
        elif any(value in {"SATISFIED", "PARTIALLY_SATISFIED"} for value in results):
            answerability, coverage = "PARTIALLY_ANSWERABLE", "PARTIAL"
        elif any(gap == "UNRESOLVED_GAP" for gap in gap_classes) or not rows:
            answerability, coverage = "UNRESOLVED", "UNRESOLVED"
        else:
            answerability, coverage = "NOT_ANSWERABLE_CURRENT_FRONTIER", "NONE"
        info_gaps = [gap for gap in gaps if gap["gap_class"] == "INFORMATION_GAP"]
        counterfactual = {
            "information_gap_count": len(info_gaps),
            "all_information_gaps_counterfactual_exhausted": all(
                "COUNTERFACTUAL_EXHAUSTED" in gap["flags"] for gap in info_gaps
            ),
            "smaller_explanation_classes_checked": [
                "METHOD_GAP",
                "CAPACITY_GAP",
                "REVIEW_GAP",
                "DENOMINATOR_GAP",
                "OWNER_SEMANTICS_GAP",
                "IMPLEMENTATION_GAP",
                "AUTHORITY_GAP",
                "DATA_GAP",
            ],
            "information_absence_is_last_resort": True,
            "authority_effect": "NONE",
        }
        record: dict[str, Any] = {
            "schema_version": "0.1",
            "coverage_assessment_id": "PENDING",
            "coverage_item_generation_id": coverage_item_generation_id,
            "requirement_profile_id": str(requirement_profile["requirement_profile_id"]),
            "capability_frontier_id": str(capability_frontier["capability_frontier_id"]),
            "assessment_rule_pack_id": REFERENCE_RULE_PACK_ID,
            "evaluation_cutoff": evaluation_cutoff,
            "answerability_state": answerability,
            "coverage_status": coverage,
            "requirement_results": rows,
            "gap_assessments": gaps,
            "counterfactual_sufficiency_review": counterfactual,
            "lawful_next_route": lawful_next_route,
            "earliest_lawful_research_stage": earliest_lawful_research_stage,
            "blocking_conditions": sorted(blocking),
            "evidence_refs": sorted(evidence_refs),
            "QA_state": "WARN" if blocking else "PASS",
            "first_valid_time": first_valid_time or evaluation_cutoff,
            "supersedes_assessment_id": supersedes_assessment_id,
            "authority_effect": "NONE",
        }
        record["coverage_assessment_id"] = logical_identity("ResearchCoverageAssessment", record)
        validate_canonical_object("ResearchCoverageAssessment", record)
        return record

    def capability_need(
        self,
        *,
        coverage_assessment: Mapping[str, Any],
        candidate_capability: Mapping[str, str],
        missing_information_claim: str,
        alternative_routes: Iterable[str],
        supporting_condition: str,
        falsifying_condition: str,
        shadow_test_route: str,
        next_owner_route: str,
        current_support: Iterable[str] = (),
        current_counterevidence: Iterable[str] = (),
        first_valid_time: str,
        supersedes_capability_need_assessment_id: str | None = None,
    ) -> dict[str, Any]:
        info_gaps = [
            gap for gap in coverage_assessment.get("gap_assessments", ()) if gap.get("gap_class") == "INFORMATION_GAP"
        ]
        source_gap_ids = sorted(str(gap["gap_id"]) for gap in info_gaps)
        counterfactual_ok = bool(info_gaps) and bool(
            coverage_assessment.get("counterfactual_sufficiency_review", {}).get(
                "all_information_gaps_counterfactual_exhausted"
            )
        )
        support = sorted(set(str(ref) for ref in current_support))
        counter = sorted(set(str(ref) for ref in current_counterevidence))
        if not counterfactual_ok:
            need_status = "UNRESOLVED" if info_gaps else "NOT_REQUIRED"
        elif counter:
            need_status = "NEED_CONTRADICTED"
        else:
            # WP4 is pre-evidentiary/non-authoritative. It may identify evidence required, not promote NEED_SUPPORTED.
            need_status = "EVIDENCE_REQUIRED"
        candidate = {
            "capability_id": str(candidate_capability["capability_id"]),
            "owner": str(candidate_capability["owner"]),
            "owner_contract_ref": str(candidate_capability["owner_contract_ref"]),
        }
        record: dict[str, Any] = {
            "schema_version": "0.1",
            "capability_need_assessment_id": "PENDING",
            "source_coverage_assessment_id": str(coverage_assessment["coverage_assessment_id"]),
            "source_gap_ids": source_gap_ids,
            "candidate_capability": candidate,
            "missing_information_claim": missing_information_claim,
            "ownership_test": {
                "candidate_owner_declared": True,
                "does_not_reassign_owner": True,
                "authority_effect": "NONE",
            },
            "minimality_test": {
                "counterfactual_exhausted": counterfactual_ok,
                "alternative_route_count": len(set(str(route) for route in alternative_routes)),
                "authority_effect": "NONE",
            },
            "alternative_routes": sorted(set(str(route) for route in alternative_routes)),
            "need_status": need_status,
            "supporting_condition": supporting_condition,
            "falsifying_condition": falsifying_condition,
            "current_support": support,
            "current_counterevidence": counter,
            "shadow_test_route": shadow_test_route,
            "next_owner_route": next_owner_route,
            "authority_requested": "NONE",
            "authority_effect": "NONE",
            "evidence_refs": sorted(set(source_gap_ids + support + counter)),
            "first_valid_time": first_valid_time,
            "supersedes_capability_need_assessment_id": supersedes_capability_need_assessment_id,
        }
        record["capability_need_assessment_id"] = logical_identity("CapabilityNeedAssessment", record)
        validate_canonical_object("CapabilityNeedAssessment", record)
        return record


def reference_replay_digest(assessments: Iterable[Mapping[str, Any]]) -> bytes:
    """Order-invariant reference digest input; deliberately no sampling/top-N path."""
    rows = [deepcopy(dict(item)) for item in assessments]
    rows.sort(key=canonical_json_bytes)
    return canonical_json_bytes(rows)
