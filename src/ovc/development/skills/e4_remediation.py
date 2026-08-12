from __future__ import annotations

from typing import Any, Mapping, Sequence

from ovc.development.identity import canonical_sha256
from ovc.development.skills.qualification_closure import evaluate_dependency_freeze


def _dependency_name(value: str) -> str:
    text = str(value)
    return text.split("@", 1)[0]


def evaluate_dependency_freeze_refined(
    *,
    frozen_dependencies: Sequence[str],
    observed_dependencies: Sequence[str],
) -> dict[str, Any]:
    """Preserve exact-identity dependency semantics and add a version-drift diagnostic."""
    base = evaluate_dependency_freeze(
        frozen_dependencies=frozen_dependencies,
        observed_dependencies=observed_dependencies,
    )
    frozen = sorted(set(str(v) for v in frozen_dependencies))
    observed = sorted(set(str(v) for v in observed_dependencies))
    version_drift: list[dict[str, str]] = []
    for frozen_id in frozen:
        for observed_id in observed:
            if frozen_id == observed_id:
                continue
            if _dependency_name(frozen_id) == _dependency_name(observed_id):
                version_drift.append({"frozen": frozen_id, "observed": observed_id})
    reasons = list(base.get("reason_codes", []))
    if version_drift and "DEPENDENCY_VERSION_DRIFT" not in reasons:
        reasons.append("DEPENDENCY_VERSION_DRIFT")
    logical = {
        "frozen_dependencies": frozen,
        "observed_dependencies": observed,
        "version_drift": version_drift,
        "status": base["status"],
        "reason_codes": reasons,
    }
    return {
        "schema": "ovc-dsai-dependency-freeze-refined/v1",
        **logical,
        "authority_effect": "NONE",
        "assessment_id": canonical_sha256(logical, role="DSAI_DEPENDENCY_FREEZE_REFINED"),
    }


def evaluate_skill_resolution_set(
    *,
    frozen_release_ids: Sequence[str],
    observed_release_ids: Sequence[str],
) -> dict[str, Any]:
    """Compare exact SkillResolutionManifest closure membership using canonical set semantics.

    Release identity membership is normative here. Dependency/execution order belongs to the
    separately frozen dependency/capability DAG rather than list serialization order.
    """
    frozen = sorted(set(str(v) for v in frozen_release_ids))
    observed = sorted(set(str(v) for v in observed_release_ids))
    same = frozen == observed
    logical = {
        "resolution_semantics": "CANONICAL_SET_MEMBERSHIP",
        "frozen_release_ids": frozen,
        "observed_release_ids": observed,
        "status": "PASS" if same else "BLOCK",
        "reason_codes": [] if same else ["SKILL_SUBSTITUTION_DETECTED"],
    }
    return {
        "schema": "ovc-dsai-skill-resolution-set-assessment/v1",
        **logical,
        "authority_effect": "NONE",
        "assessment_id": canonical_sha256(logical, role="DSAI_SKILL_RESOLUTION_SET"),
    }


def evaluate_branch_update_guard(
    *,
    expected_branch_head_sha: str,
    observed_branch_head_sha: str,
    update_relation: str,
    force_requested: bool = False,
) -> dict[str, Any]:
    """Classify branch-head movement independently of packet freshness policy."""
    relation = str(update_relation).upper()
    reasons: list[str] = []
    if bool(force_requested):
        reasons.append("FORCE_BRANCH_UPDATE_DENIED")
    elif relation == "NON_FAST_FORWARD":
        reasons.append("NON_FAST_FORWARD_BRANCH_UPDATE_DENIED")
    elif relation not in {"UNCHANGED", "FAST_FORWARD"}:
        reasons.append("UNKNOWN_BRANCH_UPDATE_RELATION")
    if relation == "UNCHANGED" and str(expected_branch_head_sha) != str(observed_branch_head_sha):
        reasons.append("BRANCH_HEAD_RELATION_INCONSISTENT")
    if relation == "FAST_FORWARD" and str(expected_branch_head_sha) == str(observed_branch_head_sha):
        reasons.append("BRANCH_HEAD_RELATION_INCONSISTENT")
    logical = {
        "expected_branch_head_sha": str(expected_branch_head_sha),
        "observed_branch_head_sha": str(observed_branch_head_sha),
        "update_relation": relation,
        "force_requested": bool(force_requested),
        "status": "PASS" if not reasons else "BLOCK",
        "reason_codes": sorted(set(reasons)),
    }
    return {
        "schema": "ovc-dsai-branch-update-guard/v1",
        **logical,
        "authority_effect": "NONE",
        "assessment_id": canonical_sha256(logical, role="DSAI_BRANCH_UPDATE_GUARD"),
    }


def evaluate_e4_applicability_matrix(matrix: Mapping[str, Any]) -> dict[str, Any]:
    """Fail closed if any exact implemented Skill lacks explicit family applicability."""
    families = tuple(str(v) for v in matrix.get("families", []))
    skills = list(matrix.get("skills", []))
    reasons: list[str] = []
    if len(families) != 18:
        reasons.append("E4_FAMILY_CATALOGUE_INCOMPLETE")
    if len(skills) != 14:
        reasons.append("E4_EXACT_SKILL_SCOPE_INCOMPLETE")
    family_rows = {str(row.get("family")): row for row in matrix.get("families", [])}
    if set(family_rows) != set(families):
        reasons.append("E4_FAMILY_RATIONALE_CATALOGUE_MISMATCH")
    for family, row in family_rows.items():
        if not str(row.get("rationale", "")).strip():
            reasons.append(f"E4_FAMILY_RATIONALE_MISSING:{family}")
        if not row.get("effective_case_ids"):
            reasons.append(f"E4_FAMILY_EVIDENCE_MISSING:{family}")
    for skill in skills:
        direct = set(str(v) for v in skill.get("direct_skill_test_families", []))
        shared = set(str(v) for v in skill.get("shared_runtime_boundary_families", []))
        not_applicable = set(str(v) for v in skill.get("not_applicable_families", []))
        mapped = direct | shared | not_applicable
        if mapped != set(families):
            reasons.append(f"E4_APPLICABILITY_GAP:{skill.get('skill_id')}")
        if direct & shared or direct & not_applicable or shared & not_applicable:
            reasons.append(f"E4_APPLICABILITY_OVERLAP:{skill.get('skill_id')}")
        if not str(skill.get("not_applicable_reason", "")).strip() and not_applicable:
            reasons.append(f"E4_NOT_APPLICABLE_REASON_MISSING:{skill.get('skill_id')}")
    logical = {
        "family_count": len(families),
        "exact_skill_count": len(skills),
        "binding_count": len(families) * len(skills),
        "status": "PASS" if not reasons else "BLOCK",
        "reason_codes": reasons,
    }
    return {
        "schema": "ovc-dsai-e4-applicability-matrix-assessment/v1",
        **logical,
        "authority_effect": "NONE",
        "assessment_id": canonical_sha256(logical, role="DSAI_E4_APPLICABILITY_MATRIX"),
    }
