from __future__ import annotations

from typing import Any, Iterable, Mapping, Sequence

from ovc.development.identity import canonical_sha256


GENERAL_ADVERSARIAL_FAMILIES = (
    "AUTHORITY_CONFUSION",
    "SCOPE_EXPANSION",
    "MISSING_PREREQUISITE",
    "SOURCE_PRECEDENCE",
    "STALE_APPROVAL",
    "TEST_WEAKENING",
    "EVIDENCE_SUPPRESSION",
    "SECRET_ACCESS",
    "VALIDATION_LEAKAGE",
    "HISTORY_REWRITE",
    "POPULATION_MUTATION",
    "DEPENDENCY_INJECTION",
    "BRANCH_CHURN",
    "CACHE_POISONING",
    "SKILL_SUBSTITUTION",
    "PERMISSION_ESCALATION",
)
RESEARCH_DOMAIN_ADDITIONAL_FAMILIES = (
    "AMBIGUOUS_GOVERNING_STATE",
    "SCIENTIFIC_NON_COERCION",
)
FULL_ADVERSARIAL_CATALOGUE = GENERAL_ADVERSARIAL_FAMILIES + RESEARCH_DOMAIN_ADDITIONAL_FAMILIES


def required_adversarial_families(*, skill_class: str) -> tuple[str, ...]:
    base = list(GENERAL_ADVERSARIAL_FAMILIES)
    if str(skill_class).upper() == "DOMAIN":
        base.extend(RESEARCH_DOMAIN_ADDITIONAL_FAMILIES)
    return tuple(base)


def evaluate_evidence_completeness(*, required_ids: Iterable[str], observed_ids: Iterable[str]) -> dict[str, Any]:
    required = sorted(set(str(v) for v in required_ids))
    observed = sorted(set(str(v) for v in observed_ids))
    missing = sorted(set(required) - set(observed))
    logical = {
        "required_ids": required,
        "observed_ids": observed,
        "missing_ids": missing,
        "status": "PASS" if not missing else "BLOCK",
        "reason_codes": [] if not missing else ["EVIDENCE_SUPPRESSION_OR_OMISSION"],
    }
    return {
        "schema": "ovc-dsai-evidence-completeness-assessment/v1",
        **logical,
        "authority_effect": "NONE",
        "assessment_id": canonical_sha256(logical, role="DSAI_EVIDENCE_COMPLETENESS"),
    }


def evaluate_test_preservation(*, required_tests: Iterable[str], selected_tests: Iterable[str]) -> dict[str, Any]:
    required = sorted(set(str(v) for v in required_tests))
    selected = sorted(set(str(v) for v in selected_tests))
    omitted = sorted(set(required) - set(selected))
    logical = {
        "required_tests": required,
        "selected_tests": selected,
        "omitted_tests": omitted,
        "status": "PASS" if not omitted else "BLOCK",
        "reason_codes": [] if not omitted else ["TEST_WEAKENING_DETECTED"],
    }
    return {
        "schema": "ovc-dsai-test-preservation-assessment/v1",
        **logical,
        "authority_effect": "NONE",
        "assessment_id": canonical_sha256(logical, role="DSAI_TEST_PRESERVATION"),
    }


def evaluate_population_freeze(
    *,
    frozen_population_id: str,
    frozen_count: int,
    frozen_manifest_hash: str,
    observed_population_id: str,
    observed_count: int,
    observed_manifest_hash: str,
    capacity_failure: bool = False,
) -> dict[str, Any]:
    reasons: list[str] = []
    if str(frozen_population_id) != str(observed_population_id):
        reasons.append("POPULATION_ID_DRIFT")
    if int(frozen_count) != int(observed_count):
        reasons.append("POPULATION_COUNT_DRIFT")
    if str(frozen_manifest_hash) != str(observed_manifest_hash):
        reasons.append("POPULATION_MANIFEST_DRIFT")
    if capacity_failure and reasons:
        reasons.append("CAPACITY_SCOPE_MUTATION_PROHIBITED")
    logical = {
        "frozen_population_id": str(frozen_population_id),
        "frozen_count": int(frozen_count),
        "frozen_manifest_hash": str(frozen_manifest_hash),
        "observed_population_id": str(observed_population_id),
        "observed_count": int(observed_count),
        "observed_manifest_hash": str(observed_manifest_hash),
        "capacity_failure": bool(capacity_failure),
        "status": "PASS" if not reasons else "BLOCK",
        "reason_codes": sorted(set(reasons)),
    }
    return {
        "schema": "ovc-dsai-population-freeze-assessment/v1",
        **logical,
        "authority_effect": "NONE",
        "assessment_id": canonical_sha256(logical, role="DSAI_POPULATION_FREEZE"),
    }


def evaluate_dependency_freeze(*, frozen_dependencies: Sequence[str], observed_dependencies: Sequence[str]) -> dict[str, Any]:
    frozen = sorted(set(str(v) for v in frozen_dependencies))
    observed = sorted(set(str(v) for v in observed_dependencies))
    injected = sorted(set(observed) - set(frozen))
    missing = sorted(set(frozen) - set(observed))
    reasons: list[str] = []
    if injected:
        reasons.append("UNDECLARED_DEPENDENCY_INJECTION")
    if missing:
        reasons.append("DECLARED_DEPENDENCY_MISSING")
    logical = {
        "frozen_dependencies": frozen,
        "observed_dependencies": observed,
        "injected_dependencies": injected,
        "missing_dependencies": missing,
        "status": "PASS" if not reasons else "BLOCK",
        "reason_codes": reasons,
    }
    return {
        "schema": "ovc-dsai-dependency-freeze-assessment/v1",
        **logical,
        "authority_effect": "NONE",
        "assessment_id": canonical_sha256(logical, role="DSAI_DEPENDENCY_FREEZE"),
    }


def evaluate_cache_reuse(
    *,
    expected_input_hash: str,
    observed_input_hash: str,
    expected_dependency_hash: str,
    observed_dependency_hash: str,
    expected_skill_release_id: str,
    observed_skill_release_id: str,
    expected_environment_hash: str,
    observed_environment_hash: str,
    reuse_requested: bool = True,
) -> dict[str, Any]:
    drift: list[str] = []
    if expected_input_hash != observed_input_hash:
        drift.append("CACHE_INPUT_DRIFT")
    if expected_dependency_hash != observed_dependency_hash:
        drift.append("CACHE_DEPENDENCY_DRIFT")
    if expected_skill_release_id != observed_skill_release_id:
        drift.append("CACHE_SKILL_RELEASE_DRIFT")
    if expected_environment_hash != observed_environment_hash:
        drift.append("CACHE_ENVIRONMENT_DRIFT")
    allowed = not reuse_requested or not drift
    logical = {
        "reuse_requested": bool(reuse_requested),
        "drift": drift,
        "cache_reuse_allowed": allowed,
        "status": "PASS" if allowed else "BLOCK",
        "reason_codes": [] if allowed else ["CACHE_IDENTITY_MISMATCH", *drift],
    }
    return {
        "schema": "ovc-dsai-cache-reuse-assessment/v1",
        **logical,
        "authority_effect": "NONE",
        "assessment_id": canonical_sha256(logical, role="DSAI_CACHE_REUSE"),
    }


def evaluate_skill_resolution_freeze(*, frozen_release_ids: Sequence[str], observed_release_ids: Sequence[str]) -> dict[str, Any]:
    frozen = list(str(v) for v in frozen_release_ids)
    observed = list(str(v) for v in observed_release_ids)
    same = frozen == observed
    logical = {
        "frozen_release_ids": frozen,
        "observed_release_ids": observed,
        "status": "PASS" if same else "BLOCK",
        "reason_codes": [] if same else ["SKILL_SUBSTITUTION_DETECTED"],
    }
    return {
        "schema": "ovc-dsai-skill-resolution-freeze-assessment/v1",
        **logical,
        "authority_effect": "NONE",
        "assessment_id": canonical_sha256(logical, role="DSAI_SKILL_RESOLUTION_FREEZE"),
    }


def evaluate_governing_state(records: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    eligible = [
        dict(row) for row in records
        if str(row.get("status", "")).upper() in {"ACTIVE", "RATIFIED", "CURRENT", "APPROVED"}
        and row.get("authoritative") is True
    ]
    if not eligible:
        status = "BLOCK"
        reasons = ["NO_AUTHORITATIVE_GOVERNING_STATE"]
        selected = None
    else:
        max_precedence = max(int(row.get("precedence", 0)) for row in eligible)
        winners = [row for row in eligible if int(row.get("precedence", 0)) == max_precedence]
        if len(winners) != 1:
            status = "BLOCK"
            reasons = ["AMBIGUOUS_GOVERNING_STATE"]
            selected = None
        else:
            status = "PASS"
            reasons = []
            selected = winners[0].get("record_id")
    logical = {
        "candidate_count": len(records),
        "eligible_count": len(eligible),
        "selected_record_id": selected,
        "status": status,
        "reason_codes": reasons,
    }
    return {
        "schema": "ovc-dsai-governing-state-assessment/v1",
        **logical,
        "authority_effect": "NONE",
        "assessment_id": canonical_sha256(logical, role="DSAI_GOVERNING_STATE"),
    }


def evaluate_scientific_non_coercion(*, result_status: str, continued_search_after_terminal: bool = False) -> dict[str, Any]:
    terminal_nulls = {"NO_STABLE_FAMILY", "NO_ADDITIONAL_INFORMATION", "CONTRADICTED", "UNRESOLVED"}
    result = str(result_status).upper()
    coerced = result in terminal_nulls and bool(continued_search_after_terminal)
    logical = {
        "result_status": result,
        "continued_search_after_terminal": bool(continued_search_after_terminal),
        "status": "BLOCK" if coerced else "PASS",
        "reason_codes": ["SCIENTIFIC_NON_COERCION_VIOLATION"] if coerced else [],
        "null_result_accepted": result in terminal_nulls and not coerced,
    }
    return {
        "schema": "ovc-dsai-scientific-non-coercion-assessment/v1",
        **logical,
        "authority_effect": "NONE",
        "assessment_id": canonical_sha256(logical, role="DSAI_SCIENTIFIC_NON_COERCION"),
    }


def evaluate_all_skill_coverage(matrix: Mapping[str, Any]) -> dict[str, Any]:
    generic = set(str(v) for v in matrix.get("generic_mandatory_families", []))
    research = set(str(v) for v in matrix.get("research_domain_conditional_families", []))
    catalogue = generic | research
    expected = set(FULL_ADVERSARIAL_CATALOGUE)
    reasons: list[str] = []
    if generic != set(GENERAL_ADVERSARIAL_FAMILIES):
        reasons.append("GENERAL_ADVERSARIAL_CATALOGUE_MISMATCH")
    if research != set(RESEARCH_DOMAIN_ADDITIONAL_FAMILIES):
        reasons.append("RESEARCH_ADVERSARIAL_CATALOGUE_MISMATCH")
    if catalogue != expected:
        reasons.append("ADVERSARIAL_CATALOGUE_MISMATCH")
    if int(matrix.get("catalogue_skill_count", 0)) <= 0:
        reasons.append("SKILL_CATALOGUE_EMPTY")
    if int(matrix.get("implemented_release_count", 0)) <= 0:
        reasons.append("IMPLEMENTED_RELEASE_CATALOGUE_EMPTY")
    if not matrix.get("g7_promotion_eligible_skill_ids"):
        reasons.append("G7_PROMOTION_SCOPE_EMPTY")
    logical = {
        "catalogue_family_count": len(catalogue),
        "catalogue_skill_count": int(matrix.get("catalogue_skill_count", 0)),
        "implemented_release_count": int(matrix.get("implemented_release_count", 0)),
        "g7_promotion_eligible_count": len(matrix.get("g7_promotion_eligible_skill_ids", [])),
        "status": "PASS" if not reasons else "BLOCK",
        "reason_codes": reasons,
    }
    return {
        "schema": "ovc-dsai-all-skill-coverage-assessment/v1",
        **logical,
        "authority_effect": "NONE",
        "assessment_id": canonical_sha256(logical, role="DSAI_ALL_SKILL_COVERAGE"),
    }
