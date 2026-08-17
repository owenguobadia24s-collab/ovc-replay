from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping, Sequence

from ovc.research_operations.canonical import canonical_sha256

CHALLENGE_DIMENSIONS = (
    "dependence",
    "reference",
    "representation",
    "temporal",
    "context",
    "boundary",
    "multiplicity",
    "replication",
)
FORBIDDEN_PROTOCOL_NAMESPACES = frozenset({
    "OPT_C", "OPT_D", "VALIDATION", "DEVELOPMENT_OUTCOMES",
    "PROBABILITY", "RISK", "EXPOSURE", "EXECUTION",
})
ALLOWED_DECISION_EFFECTS = frozenset({"REQUIRE", "RESTRICT", "ANNOTATE"})


class PRSCContractError(ValueError):
    """Raised when a PRSC object would violate the ratified bounded constitution."""


def semantic_id(value: Mapping[str, Any]) -> str:
    """Content-address one semantic PRSC payload using Research Operations canonical JSON."""
    return canonical_sha256(dict(value))


def build_protocol_generation(
    *,
    protocol_series_id: str,
    generation: int,
    scientific_generation: str,
    method_pack_refs: Sequence[str],
    hypothesis_family_registry_ref: str,
    claim_template_refs: Sequence[str],
    reviewer_constitution_ref: str,
    preregistration_state: str = "DRAFT",
    source_namespaces: Sequence[str] = ("EC1_G1",),
) -> dict[str, Any]:
    if not protocol_series_id or not scientific_generation or generation < 1:
        raise PRSCContractError("PRSC_PROTOCOL_IDENTITY_INVALID")
    namespaces = tuple(str(v).upper() for v in source_namespaces)
    forbidden = sorted(set(namespaces) & FORBIDDEN_PROTOCOL_NAMESPACES)
    if forbidden:
        raise PRSCContractError(f"PRSC_OUTCOME_FIREWALL:{','.join(forbidden)}")
    if preregistration_state not in {"DRAFT", "READY_FOR_OPERATOR_FREEZE", "FROZEN"}:
        raise PRSCContractError("PRSC_PREREGISTRATION_STATE_INVALID")
    body = {
        "schema": "ovc-prsc-protocol-generation/v0.1",
        "protocol_series_id": protocol_series_id,
        "generation": int(generation),
        "scientific_generation": scientific_generation,
        "research_role": "DISCOVERY_POST_RECURRENCE_CHALLENGE",
        "outcome_blind": True,
        "source_namespaces": list(namespaces),
        "method_pack_refs": list(method_pack_refs),
        "hypothesis_family_registry_ref": hypothesis_family_registry_ref,
        "claim_template_refs": list(claim_template_refs),
        "reviewer_constitution_ref": reviewer_constitution_ref,
        "preregistration_state": preregistration_state,
        "authority_effect": "NONE",
    }
    body["protocol_generation_id"] = semantic_id(body)
    return body


def adapt_ec1_record(record: Mapping[str, Any], *, prsc_refs: Sequence[str]) -> dict[str, Any]:
    """Add PRSC references without changing the supplied EC1 record or its owner-defined fields."""
    result = deepcopy(dict(record))
    if "prsc_refs" in result and not isinstance(result["prsc_refs"], list):
        raise PRSCContractError("PRSC_ADAPTER_EXISTING_REF_INVALID")
    existing = list(result.get("prsc_refs", []))
    for ref in prsc_refs:
        value = str(ref).strip()
        if value and value not in existing:
            existing.append(value)
    result["prsc_refs"] = existing
    return result


def validate_claim_dependency_manifest(manifest: Mapping[str, Any]) -> None:
    required = set(manifest.get("required_dimensions", []))
    optional = set(manifest.get("optional_dimensions", []))
    unknown = (required | optional) - set(CHALLENGE_DIMENSIONS)
    if unknown:
        raise PRSCContractError(f"PRSC_UNKNOWN_CHALLENGE_DIMENSION:{','.join(sorted(unknown))}")
    if required & optional:
        raise PRSCContractError("PRSC_DIMENSION_ROLE_COLLISION")
    effects = set(manifest.get("allowed_effects", []))
    if not effects or not effects <= ALLOWED_DECISION_EFFECTS:
        raise PRSCContractError("PRSC_DECISION_EFFECT_INVALID")
    if manifest.get("aggregation") not in {"NON_COMPENSATORY", None}:
        raise PRSCContractError("PRSC_COMPENSATORY_AGGREGATION_FORBIDDEN")
