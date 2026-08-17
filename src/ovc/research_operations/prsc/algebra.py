from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping, Sequence

from .contracts import CHALLENGE_DIMENSIONS, PRSCContractError, semantic_id

DECISION_STATES = frozenset({
    "NON_FATAL_SUPPORT", "SCOPE_RESTRICTION", "REVISION_REQUIRED",
    "FATAL_TO_CURRENT_CLAIM", "UNRESOLVED", "NOT_APPLICABLE",
})
ROLE_TO_OPERATOR = {
    "REQUIRED": "REQUIRE",
    "SCOPE_CONDITION": "RESTRICT",
    "ADVISORY": "ANNOTATE",
    "NOT_APPLICABLE": "ANNOTATE",
}
PRECEDENCE = (
    "INTEGRITY_INVALID",
    "REQUIRED_FATAL",
    "REQUIRED_UNRESOLVED",
    "REVISION_REQUIRED",
    "SCOPE_RESTRICTION",
    "DISCOVERY_FREEZE_ELIGIBLE",
    "DESCRIPTIVE_ONLY",
)

_TEMPLATE_ROLES = {
    "P1A": {
        "required": ("dependence", "reference", "representation", "temporal", "multiplicity"),
        "scope": ("context",),
        "advisory": ("replication",),
        "not_applicable": ("boundary",),
    },
    "P1B": {
        "required": ("dependence", "reference", "representation", "temporal", "multiplicity"),
        "scope": ("context",),
        "advisory": ("replication",),
        "not_applicable": ("boundary",),
    },
    "P1C": {
        "required": ("dependence", "reference", "representation", "temporal", "boundary", "multiplicity"),
        "scope": ("context",),
        "advisory": ("replication",),
        "not_applicable": (),
    },
}


def build_claim_dependency_manifest(*, candidate_ref: str, population_family: str, claim_class: str = "DISCOVERY_FREEZE_ELIGIBILITY") -> dict[str, Any]:
    if population_family not in _TEMPLATE_ROLES:
        raise PRSCContractError("PRSC_CLAIM_POPULATION_FAMILY_INVALID")
    if not candidate_ref:
        raise PRSCContractError("PRSC_CLAIM_CANDIDATE_REF_REQUIRED")
    roles = _TEMPLATE_ROLES[population_family]
    body = {
        "schema": "ovc-prsc-claim-dependency-manifest/v0.1",
        "candidate_ref": candidate_ref,
        "claim_class": claim_class,
        "population_family": population_family,
        "required_dimensions": list(roles["required"]),
        "scope_condition_dimensions": list(roles["scope"]),
        "advisory_dimensions": list(roles["advisory"]),
        "non_applicable_dimensions": list(roles["not_applicable"]),
        "fatal_failure_states": ["FATAL_TO_CURRENT_CLAIM"],
        "restriction_states": ["SCOPE_RESTRICTION"],
        "revision_states": ["REVISION_REQUIRED"],
        "unresolved_states": ["UNRESOLVED"],
        "aggregation": "NON_COMPENSATORY",
        "allowed_effects": ["REQUIRE", "RESTRICT", "ANNOTATE"],
        "authority_effect": "NONE",
    }
    body["claim_dependency_id"] = semantic_id(body)
    return body


def build_scientific_challenge_vector(*, candidate_ref: str, dimension_states: Mapping[str, str], evidence_refs: Mapping[str, Sequence[str]] | None = None, reason_codes: Mapping[str, Sequence[str]] | None = None, protocol_generation_ref: str | None = None) -> dict[str, Any]:
    unknown = set(dimension_states) - set(CHALLENGE_DIMENSIONS)
    if unknown:
        raise PRSCContractError(f"PRSC_UNKNOWN_CHALLENGE_DIMENSION:{','.join(sorted(unknown))}")
    evidence_refs = evidence_refs or {}
    reason_codes = reason_codes or {}
    dimensions: dict[str, Any] = {}
    for dimension in CHALLENGE_DIMENSIONS:
        state = dimension_states.get(dimension, "NOT_APPLICABLE")
        if state not in DECISION_STATES:
            raise PRSCContractError(f"PRSC_CHALLENGE_STATE_INVALID:{dimension}:{state}")
        dimensions[dimension] = {
            "state": state,
            "evidence_refs": list(evidence_refs.get(dimension, ())),
            "reason_codes": list(reason_codes.get(dimension, ())),
        }
    body = {
        "candidate_ref": candidate_ref,
        "protocol_generation_ref": protocol_generation_ref,
        "dimensions": dimensions,
        "authority_effect": "NONE",
    }
    body["scientific_challenge_vector_id"] = semantic_id(body)
    return body


def _role_map(manifest: Mapping[str, Any]) -> dict[str, str]:
    roles: dict[str, str] = {}
    for d in manifest.get("required_dimensions", []): roles[d] = "REQUIRED"
    for d in manifest.get("scope_condition_dimensions", []): roles[d] = "SCOPE_CONDITION"
    for d in manifest.get("advisory_dimensions", []): roles[d] = "ADVISORY"
    for d in manifest.get("non_applicable_dimensions", []): roles[d] = "NOT_APPLICABLE"
    return roles


def evaluate_scientific_disposition(*, challenge_vector: Mapping[str, Any], claim_dependency_manifest: Mapping[str, Any], integrity_state: str = "PASS") -> dict[str, Any]:
    if integrity_state not in {"PASS", "BLOCK", "QUARANTINE"}:
        raise PRSCContractError("PRSC_INTEGRITY_STATE_INVALID")
    roles = _role_map(claim_dependency_manifest)
    dimensions = challenge_vector.get("dimensions", {})
    effects = []
    for dimension in CHALLENGE_DIMENSIONS:
        role = roles.get(dimension, "ADVISORY")
        state = dimensions.get(dimension, {}).get("state", "NOT_APPLICABLE")
        effects.append({"dimension": dimension, "effect": ROLE_TO_OPERATOR[role], "state": state})

    required_states = [dimensions[d]["state"] for d in claim_dependency_manifest.get("required_dimensions", [])]
    all_states = [dimensions[d]["state"] for d in CHALLENGE_DIMENSIONS]
    scope_states = [dimensions[d]["state"] for d in claim_dependency_manifest.get("scope_condition_dimensions", [])]

    if integrity_state == "QUARANTINE":
        precedence_hit, disposition = "INTEGRITY_INVALID", "QUARANTINE_INTEGRITY"
    elif integrity_state == "BLOCK":
        precedence_hit, disposition = "INTEGRITY_INVALID", "REJECT_CURRENT_CLAIM"
    elif "FATAL_TO_CURRENT_CLAIM" in required_states:
        precedence_hit, disposition = "REQUIRED_FATAL", "REJECT_CURRENT_CLAIM"
    elif "UNRESOLVED" in required_states:
        precedence_hit, disposition = "REQUIRED_UNRESOLVED", "NOT_EVALUABLE"
    elif "REVISION_REQUIRED" in all_states:
        precedence_hit, disposition = "REVISION_REQUIRED", "REFINE_WITHIN_DISCOVERY"
    elif "SCOPE_RESTRICTION" in required_states or "SCOPE_RESTRICTION" in scope_states:
        precedence_hit, disposition = "SCOPE_RESTRICTION", "FREEZE_WITH_SCOPE_RESTRICTION"
    elif required_states and all(s == "NON_FATAL_SUPPORT" for s in required_states):
        precedence_hit, disposition = "DISCOVERY_FREEZE_ELIGIBLE", "FREEZE_CANDIDATE_RECOMMENDED"
    else:
        precedence_hit, disposition = "DESCRIPTIVE_ONLY", "DESCRIPTIVE_INVENTORY_ONLY"

    body = {
        "candidate_ref": challenge_vector.get("candidate_ref"),
        "claim_dependency_ref": claim_dependency_manifest.get("claim_dependency_id"),
        "decision_effects": effects,
        "disposition": disposition,
        "precedence_hit": precedence_hit,
        "precedence": list(PRECEDENCE),
        "candidate_freeze_effect": "NONE",
        "authority_effect": "NONE",
        "aggregation": "NON_COMPENSATORY",
        "score": None,
        "majority_vote": None,
    }
    body["scientific_disposition_id"] = semantic_id(body)
    return body


def build_counterevidence_completeness_record(*, candidate_ref: str, required_categories: Sequence[str], evidence_by_category: Mapping[str, Sequence[str]]) -> dict[str, Any]:
    required = list(dict.fromkeys(str(v) for v in required_categories))
    missing = [c for c in required if not list(evidence_by_category.get(c, ()))]
    body = {
        "schema": "ovc-prsc-counterevidence-completeness-record/v0.1",
        "candidate_ref": candidate_ref,
        "required_categories": required,
        "evidence_by_category": {c: list(evidence_by_category.get(c, ())) for c in required},
        "missing_categories": missing,
        "complete": not missing,
        "authority_effect": "NONE",
    }
    body["counterevidence_completeness_id"] = semantic_id(body)
    return body


def build_candidate_freeze_recommendation(*, candidate_ref: str, scientific_disposition_ref: str, rationale_refs: Sequence[str]) -> dict[str, Any]:
    body = {
        "schema": "ovc-prsc-candidate-freeze-recommendation/v0.1",
        "candidate_ref": candidate_ref,
        "scientific_disposition_ref": scientific_disposition_ref,
        "rationale_refs": list(rationale_refs),
        "recommendation": "PREPARE_EC1_GSCI_CANDIDATE_FREEZE_REVIEW",
        "owner_gate": "EC1-GSCI",
        "candidate_freeze_effect": "NONE",
        "authority_effect": "NONE",
    }
    body["candidate_freeze_recommendation_id"] = semantic_id(body)
    return body
