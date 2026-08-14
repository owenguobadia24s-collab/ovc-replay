"""GRT2-WP3B non-authoritative ownership and Genesis binding projection."""
from __future__ import annotations

from collections import defaultdict
from typing import Any, Mapping, Sequence

from .serialization import SERIALIZATION_ID, canonical_sha256

EVIDENCE_PRECEDENCE = {
    "EXPLICIT_REPOSITORY_DECISION": 0,
    "NATIVE_PROGRAMME_GENESIS": 1,
    "RATIFIED_CURRENT_PLAN": 2,
    "CURRENT_PROGRAMME_STATE": 3,
    "ACCEPTED_LINEAGE": 4,
    "REGISTERED_PACKAGE_RULE": 5,
    "CORROBORATED_HISTORICAL": 6,
    "CANDIDATE_INFERENCE": 7,
}
CURRENT_OWNER_EVIDENCE = frozenset({
    "EXPLICIT_REPOSITORY_DECISION", "NATIVE_PROGRAMME_GENESIS", "RATIFIED_CURRENT_PLAN",
    "CURRENT_PROGRAMME_STATE", "ACCEPTED_LINEAGE", "REGISTERED_PACKAGE_RULE",
})
NATIVE_GENESIS_EVIDENCE = frozenset({"NATIVE_PROGRAMME_GENESIS", "EXPLICIT_REPOSITORY_DECISION", "ACCEPTED_LINEAGE"})


class GovernanceBindingError(ValueError):
    pass


def _claim_key(claim: Mapping[str, Any]) -> tuple[int, str, str]:
    evidence_class = claim.get("evidence_class")
    if evidence_class not in EVIDENCE_PRECEDENCE:
        raise GovernanceBindingError("GRT_BINDING_EVIDENCE_CLASS_INVALID")
    source_id = claim.get("source_id")
    value = claim.get("value")
    if not isinstance(source_id, str) or not source_id or not isinstance(value, str) or not value:
        raise GovernanceBindingError("GRT_BINDING_CLAIM_INVALID")
    return EVIDENCE_PRECEDENCE[evidence_class], source_id, value


def resolve_claims(claims: Sequence[Mapping[str, Any]], *, binding_kind: str) -> dict[str, Any]:
    if binding_kind not in {"PROGRAMME_OWNER", "IMPLEMENTATION_OWNER", "MAINTENANCE_RESPONSIBILITY", "GENESIS_CROSSWALK"}:
        raise GovernanceBindingError("GRT_BINDING_KIND_INVALID")
    if not claims:
        return {"binding_kind": binding_kind, "status": "UNRESOLVED", "value": None, "reason_codes": ["NO_EVIDENCE"], "authority_effect": "NONE_GOVERNANCE_PROJECTION"}
    normalized = [dict(claim) for claim in claims]
    ranked = sorted(normalized, key=_claim_key)
    best_rank = EVIDENCE_PRECEDENCE[ranked[0]["evidence_class"]]
    best = [claim for claim in ranked if EVIDENCE_PRECEDENCE[claim["evidence_class"]] == best_rank]
    values = sorted({claim["value"] for claim in best})
    if len(values) > 1:
        return {
            "binding_kind": binding_kind, "status": "CONFLICTING", "value": None,
            "conflicting_values": values, "evidence": best,
            "reason_codes": ["SAME_PRECEDENCE_CONFLICT", "OPERATOR_REQUIRED"],
            "authority_effect": "NONE_GOVERNANCE_PROJECTION",
        }
    selected = values[0]
    selected_claim = next(claim for claim in best if claim["value"] == selected)
    if binding_kind == "GENESIS_CROSSWALK" and selected_claim["evidence_class"] not in NATIVE_GENESIS_EVIDENCE:
        return {
            "binding_kind": binding_kind, "status": "PGN_AUTHORITY_REQUIRED_CURRENT", "value": None,
            "candidate_value": selected, "evidence": best,
            "reason_codes": ["CANDIDATE_OR_PROVISIONAL_GENESIS_CANNOT_SATISFY_CURRENT"],
            "authority_effect": "NONE_GOVERNANCE_PROJECTION",
        }
    if binding_kind in {"PROGRAMME_OWNER", "IMPLEMENTATION_OWNER"} and selected_claim["evidence_class"] not in CURRENT_OWNER_EVIDENCE:
        return {
            "binding_kind": binding_kind, "status": "CANDIDATE_RELATION", "value": None,
            "candidate_value": selected, "evidence": best, "reason_codes": ["NON_AUTHORITATIVE_OWNER_EVIDENCE"],
            "authority_effect": "NONE_GOVERNANCE_PROJECTION",
        }
    return {
        "binding_kind": binding_kind, "status": "RESOLVED", "value": selected,
        "evidence": best, "reason_codes": [], "authority_effect": "NONE_GOVERNANCE_PROJECTION",
    }


def validate_partition_proposal(proposal: Mapping[str, Any]) -> dict[str, Any]:
    proposal_id = proposal.get("proposal_id")
    owner = proposal.get("proposed_owner")
    scope = proposal.get("scope")
    covered = proposal.get("covered_artifact_ids")
    exceptions = proposal.get("exceptions", [])
    impacted = proposal.get("impacted_owner_ids", [])
    objections = proposal.get("objections", [])
    if not all(isinstance(value, str) and value for value in (proposal_id, owner, scope)):
        raise GovernanceBindingError("GRT_PARTITION_PROPOSAL_IDENTITY_INVALID")
    if not isinstance(covered, list) or not covered or not all(isinstance(x, str) and x for x in covered):
        raise GovernanceBindingError("GRT_PARTITION_COVERAGE_INVALID")
    if len(set(covered)) != len(covered):
        raise GovernanceBindingError("GRT_PARTITION_COVERAGE_DUPLICATE")
    if not isinstance(exceptions, list) or not isinstance(impacted, list) or not isinstance(objections, list):
        raise GovernanceBindingError("GRT_PARTITION_REVIEW_SURFACE_INVALID")
    authoritative_claims = proposal.get("owner_evidence", [])
    resolution = resolve_claims(authoritative_claims, binding_kind="PROGRAMME_OWNER")
    reason_codes: list[str] = []
    status = "REVIEWABLE"
    if resolution["status"] != "RESOLVED" or resolution.get("value") != owner:
        status = "OPERATOR_REQUIRED" if resolution["status"] == "CONFLICTING" else "NOT_EVALUABLE"
        reason_codes.append("PROPOSED_OWNER_NOT_SOURCE_RESOLVED")
    if objections:
        status = "OPERATOR_REQUIRED"
        reason_codes.append("IMPACTED_OWNER_OBJECTION")
    overlaps = proposal.get("overlapping_authoritative_claims", [])
    if overlaps:
        status = "OPERATOR_REQUIRED"
        reason_codes.append("OVERLAPPING_AUTHORITATIVE_BOUNDARY")
    return {
        "proposal_id": proposal_id, "status": status, "proposed_owner": owner, "scope": scope,
        "coverage_count": len(covered), "exception_count": len(exceptions),
        "impacted_owner_ids": sorted(set(impacted)), "reason_codes": sorted(set(reason_codes)),
        "materialization_allowed": False,
        "authority_effect": "NONE_REVIEW_PROPOSAL_ONLY",
    }


def build_governance_binding_registry(entries: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
    allowed = {
        "programme_bindings", "inheritance_rules", "shared_service_bindings", "generated_artifact_rules",
        "maintenance_responsibilities", "genesis_crosswalks", "historical_associations", "conflicts",
    }
    for entry in entries:
        kind = entry.get("registry_section")
        if kind not in allowed:
            raise GovernanceBindingError("GRT_BINDING_REGISTRY_SECTION_INVALID")
        item = dict(entry)
        if item.get("authority_effect", "NONE_GOVERNANCE_PROJECTION") != "NONE_GOVERNANCE_PROJECTION":
            raise GovernanceBindingError("GRT_BINDING_REGISTRY_AUTHORITY_EFFECT_INVALID")
        item["authority_effect"] = "NONE_GOVERNANCE_PROJECTION"
        buckets[kind].append(item)
    body: dict[str, Any] = {
        "schema": "grt-governance-binding-registry/v0.2",
        "serialization_profile": SERIALIZATION_ID,
        "programme_bindings": [], "inheritance_rules": [], "shared_service_bindings": [],
        "generated_artifact_rules": [], "maintenance_responsibilities": [], "genesis_crosswalks": [],
        "historical_associations": [], "conflicts": [],
        "authority_effect": "NONE_GOVERNANCE_PROJECTION", "active_enforcement": "NONE",
    }
    for section in allowed:
        body[section] = sorted(buckets.get(section, []), key=canonical_sha256)
    return {**body, "canonical_hash": canonical_sha256(body)}
