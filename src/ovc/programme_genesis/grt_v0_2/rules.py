"""GRT2-WP3C deterministic rule evaluation over explicit semantic facts."""
from __future__ import annotations

from typing import Any, Mapping, Sequence

from .debt import classify_debt_transition, compare_debt_extent, make_finding
from .serialization import canonical_sha256


class RuleEvaluationError(ValueError):
    pass


def evaluate_rule(rule: Mapping[str, Any], subject: Mapping[str, Any], facts: Mapping[str, Any]) -> dict[str, Any]:
    """Evaluate registered rule labels against caller-supplied exact facts.

    Predicate names are registry identities, never executable expressions.  The
    caller must supply an explicit Boolean/NOT_EVALUABLE value for both the
    applicability and violation predicate when the rule is evaluated.
    """
    rule_id = rule.get("rule_id")
    applicability_key = rule.get("applicability_predicate")
    violation_key = rule.get("violation_predicate")
    if not all(isinstance(value, str) and value for value in (rule_id, applicability_key, violation_key)):
        raise RuleEvaluationError("GRT_RULE_IDENTITY_INVALID")
    applicability = facts.get(applicability_key, "NOT_EVALUABLE")
    if applicability not in {True, False, "NOT_EVALUABLE"}:
        raise RuleEvaluationError("GRT_RULE_APPLICABILITY_FACT_INVALID")
    if applicability == "NOT_EVALUABLE":
        status, result = "NOT_EVALUABLE", "NOT_EVALUABLE"
    elif applicability is False:
        status, result = "NOT_APPLICABLE", "PASS"
    else:
        violation = facts.get(violation_key, "NOT_EVALUABLE")
        if violation not in {True, False, "NOT_EVALUABLE"}:
            raise RuleEvaluationError("GRT_RULE_VIOLATION_FACT_INVALID")
        if violation == "NOT_EVALUABLE":
            status, result = "NOT_EVALUABLE", "NOT_EVALUABLE"
        elif violation is True:
            status, result = "VIOLATION", rule.get("candidate_admission_effect", "FAIL")
        else:
            status, result = "PASS", "PASS"
    body = {
        "schema": "grt-rule-evaluation/v0.2",
        "rule_id": rule_id,
        "subject_artifact_id": subject.get("artifact_id"),
        "applicability_status": status if status in {"NOT_EVALUABLE", "NOT_APPLICABLE"} else "APPLICABLE",
        "evaluation_status": status,
        "admission_result": result,
        "authority_class": rule.get("authority_class"),
        "debt_effect": rule.get("debt_effect"),
        "authority_effect": "NONE_EVALUATION_ONLY",
    }
    return {**body, "canonical_hash": canonical_sha256(body)}


def findings_from_evaluations(
    *,
    evaluations: Sequence[Mapping[str, Any]],
    rule_by_id: Mapping[str, Mapping[str, Any]],
    first_seen_tree: str,
) -> list[dict[str, Any]]:
    findings = []
    for evaluation in evaluations:
        if evaluation.get("evaluation_status") != "VIOLATION":
            continue
        rule_id = str(evaluation["rule_id"])
        rule = rule_by_id.get(rule_id)
        if rule is None:
            raise RuleEvaluationError("GRT_RULE_NOT_IN_BUNDLE")
        if rule.get("debt_effect") != "ACTIONABLE_DEBT":
            continue
        findings.append(
            make_finding(
                rule_id=rule_id,
                subject_artifact_id=str(evaluation["subject_artifact_id"]),
                relation_role=str(rule.get("rule_family", "RULE")),
                debt_extent={"violations": 1},
                first_seen_tree=first_seen_tree,
                applicability_evidence=[evaluation["canonical_hash"]],
                violation_evidence=[evaluation["canonical_hash"]],
            )
        )
    return sorted(findings, key=lambda item: item["finding_id"])


def reconcile_finding(
    *,
    predecessor_state: str,
    candidate_state: str,
    predecessor_extent: Mapping[str, int] | None = None,
    candidate_extent: Mapping[str, int] | None = None,
    related_identity: bool = True,
) -> dict[str, Any]:
    extent_result = None
    if predecessor_extent is not None and candidate_extent is not None:
        extent_result = compare_debt_extent(predecessor_extent, candidate_extent)
    classification, admission = classify_debt_transition(
        predecessor_state=predecessor_state,
        candidate_state=candidate_state,
        extent_result=extent_result,
        related_identity=related_identity,
    )
    return {
        "classification": classification,
        "admission": admission,
        "extent_result": extent_result,
        "authority_effect": "NONE_DEBT_RECONCILIATION_ONLY",
    }
