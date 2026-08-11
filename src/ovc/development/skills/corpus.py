from __future__ import annotations

from typing import Any, Iterable, Mapping, Sequence

from ovc.development.identity import canonical_sha256


MANDATORY_ADVERSARIAL_FAMILIES = (
    "AUTHORITY_CONFUSION",
    "SCOPE_EXPANSION",
    "MISSING_PREREQUISITE",
    "SOURCE_PRECEDENCE",
    "STALE_APPROVAL",
    "VALIDATION_LEAKAGE",
    "PERMISSION_ESCALATION",
)


def build_curation_record(
    *,
    fixture_family: str,
    governing_source: str,
    author_role: str,
    reviewer_role: str,
    curation_effort_minutes: int,
    fixture_ids: Sequence[str],
    independent_review_state: str = "PENDING_HUMAN_REVIEW",
    reuse_lineage: Sequence[str] = (),
) -> dict[str, Any]:
    logical = {
        "fixture_family": str(fixture_family),
        "governing_source": str(governing_source),
        "author_role": str(author_role),
        "reviewer_role": str(reviewer_role),
        "curation_effort_minutes": int(curation_effort_minutes),
        "fixture_ids": sorted(set(str(value) for value in fixture_ids)),
        "independent_review_state": str(independent_review_state),
        "reuse_lineage": sorted(set(str(value) for value in reuse_lineage)),
    }
    return {
        "schema": "ovc-dsai-adversarial-corpus-curation-record/v1",
        **logical,
        "curation_id": canonical_sha256(logical, role="DSAI_ADVERSARIAL_CORPUS_CURATION"),
        "authority_effect": "NONE",
    }


def evaluate_corpus_qualification_readiness(
    records: Iterable[Mapping[str, Any]],
    *,
    mandatory_families: Iterable[str] = MANDATORY_ADVERSARIAL_FAMILIES,
) -> dict[str, Any]:
    rows = [dict(row) for row in records]
    by_family: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        by_family.setdefault(str(row.get("fixture_family", "")), []).append(row)
    missing = []
    review_gaps = []
    independence_failures = []
    zero_effort = []
    for family in sorted(set(str(value) for value in mandatory_families)):
        candidates = by_family.get(family, [])
        if not candidates:
            missing.append(family)
            continue
        accepted = [row for row in candidates if row.get("independent_review_state") == "ACCEPTED"]
        if not accepted:
            review_gaps.append(family)
            continue
        if not any(row.get("author_role") != row.get("reviewer_role") for row in accepted):
            independence_failures.append(family)
        if not any(int(row.get("curation_effort_minutes", 0)) > 0 for row in accepted):
            zero_effort.append(family)
    reasons = []
    if missing:
        reasons.append("MANDATORY_FAMILY_MISSING")
    if review_gaps:
        reasons.append("INDEPENDENT_HUMAN_REVIEW_MISSING")
    if independence_failures:
        reasons.append("AUTHOR_REVIEWER_SEPARATION_FAILED")
    if zero_effort:
        reasons.append("CURATION_EFFORT_MISSING")
    status = "PASS" if not reasons else "BLOCK"
    accepted_ids = sorted(
        str(row.get("curation_id"))
        for row in rows
        if row.get("independent_review_state") == "ACCEPTED" and row.get("curation_id")
    )
    return {
        "schema": "ovc-dsai-corpus-readiness/v1",
        "status": status,
        "qualification_eligible": status == "PASS",
        "reason_codes": reasons,
        "missing_families": missing,
        "review_gaps": review_gaps,
        "independence_failures": independence_failures,
        "zero_effort_families": zero_effort,
        "accepted_curation_ids": accepted_ids,
        "authority_effect": "NONE",
    }


def reusable_fixture_ids(records: Iterable[Mapping[str, Any]]) -> list[str]:
    selected: set[str] = set()
    for row in records:
        if row.get("independent_review_state") != "ACCEPTED":
            continue
        selected.update(str(value) for value in row.get("fixture_ids", []))
    return sorted(selected)


def score_historical_replay_case(*, actual_interpretation: str, case: Mapping[str, Any]) -> dict[str, Any]:
    reference = str(case.get("reference_interpretation", ""))
    result = {
        "schema": "ovc-dsai-historical-replay-result/v1",
        "case_id": str(case.get("case_id", "")),
        "actual_interpretation": str(actual_interpretation),
        "reference_interpretation": reference,
        "operator_outcome_observed": case.get("operator_outcome"),
        "operator_outcome_used_for_scoring": False,
        "status": "PASS" if str(actual_interpretation) == reference else "FAIL",
        "authority_effect": "NONE",
    }
    result["result_id"] = canonical_sha256(result, role="DSAI_HISTORICAL_REPLAY_RESULT")
    return result


def build_programme_skill_bootstrap_template(
    *,
    programme_id: str,
    plan_id: str,
    initial_packet: str,
    requested_authority: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    if requested_authority:
        raise ValueError("warm-start template cannot create or grant programme authority")
    logical = {
        "programme_id": str(programme_id),
        "plan_id": str(plan_id),
        "initial_packet": str(initial_packet),
        "status": "PLANNED_PROPOSAL_ONLY",
    }
    return {
        "schema": "ovc-dsai-programme-skill-bootstrap-template/v1",
        **logical,
        "template_id": canonical_sha256(logical, role="DSAI_PROGRAMME_SKILL_BOOTSTRAP"),
        "may_create_programme_state": False,
        "may_grant_authority": False,
        "authority_effect": "NONE",
    }
