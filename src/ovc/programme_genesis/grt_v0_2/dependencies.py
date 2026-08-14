"""GRT2-WP3C typed dependency, companion, orphan and workflow resolvers."""
from __future__ import annotations

from typing import Any, Mapping, Sequence

from .serialization import canonical_sha256


class DependencyResolutionError(ValueError):
    pass


def resolve_dependency(contract: Mapping[str, Any], providers: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    requiredness = contract.get("requiredness")
    if requiredness not in {"REQUIRED", "OPTIONAL", "CONDITIONAL"}:
        raise DependencyResolutionError("GRT_DEPENDENCY_REQUIREDNESS_INVALID")
    cardinality = contract.get("cardinality", "EXACTLY_ONE")
    if cardinality not in {"EXACTLY_ONE", "ZERO_OR_ONE", "ONE_OR_MORE", "ZERO_OR_MORE"}:
        raise DependencyResolutionError("GRT_DEPENDENCY_CARDINALITY_INVALID")
    compatible = []
    rejected = []
    for provider in providers:
        reasons = []
        if contract.get("provider_artifact_type") and provider.get("artifact_type") != contract["provider_artifact_type"]:
            reasons.append("TYPE_INCOMPATIBLE")
        allowed_lifecycle = set(contract.get("allowed_lifecycle_classes", []))
        if allowed_lifecycle and provider.get("lifecycle_class") not in allowed_lifecycle:
            reasons.append("LIFECYCLE_INCOMPATIBLE")
        allowed_versions = set(contract.get("allowed_versions", []))
        if allowed_versions and provider.get("version") not in allowed_versions:
            reasons.append("VERSION_INCOMPATIBLE")
        if provider.get("authority_status") in {"CONFLICTING", "UNRESOLVED", "FORBIDDEN"}:
            reasons.append("AUTHORITY_INCOMPATIBLE")
        (rejected if reasons else compatible).append({"provider_id": provider.get("artifact_id"), "reason_codes": reasons})
    count = len(compatible)
    cardinality_ok = {
        "EXACTLY_ONE": count == 1,
        "ZERO_OR_ONE": count <= 1,
        "ONE_OR_MORE": count >= 1,
        "ZERO_OR_MORE": True,
    }[cardinality]
    if not cardinality_ok:
        status = "UNRESOLVED" if requiredness != "OPTIONAL" else "OPTIONAL_ABSENT"
        reasons = ["CARDINALITY_UNSATISFIED"]
    elif count == 0 and requiredness == "REQUIRED":
        status, reasons = "UNRESOLVED", ["REQUIRED_PROVIDER_MISSING"]
    elif count == 0:
        status, reasons = "OPTIONAL_ABSENT", []
    else:
        status, reasons = "RESOLVED", []
    body = {
        "schema": "grt-dependency-resolution/v0.2",
        "contract_id": contract.get("contract_id"),
        "consumer_artifact_id": contract.get("consumer_artifact_id"),
        "requiredness": requiredness,
        "status": status,
        "provider_ids": sorted(str(item["provider_id"]) for item in compatible if item["provider_id"]),
        "rejected_providers": sorted(rejected, key=lambda item: str(item["provider_id"])),
        "reason_codes": reasons,
        "authority_effect": "NONE_RESOLUTION_ONLY",
    }
    return {**body, "canonical_hash": canonical_sha256(body)}


def assess_companion(obligation: Mapping[str, Any], companions: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    if obligation.get("required") is not True:
        return {"obligation_id": obligation.get("obligation_id"), "status": "NOT_APPLICABLE", "reason_codes": [], "authority_effect": "NONE_RESOLUTION_ONLY"}
    valid = []
    invalid = []
    for companion in companions:
        reasons = []
        if companion.get("artifact_type") != obligation.get("companion_artifact_type"):
            reasons.append("WRONG_COMPANION_CLASS")
        if companion.get("placeholder") is True or companion.get("content_valid") is not True:
            reasons.append("PLACEHOLDER_OR_INVALID")
        if companion.get("owner_status") != "RESOLVED":
            reasons.append("OWNER_UNRESOLVED")
        if obligation.get("allowed_lifecycle_classes") and companion.get("lifecycle_class") not in obligation["allowed_lifecycle_classes"]:
            reasons.append("LIFECYCLE_INCOMPATIBLE")
        (invalid if reasons else valid).append({"artifact_id": companion.get("artifact_id"), "reason_codes": reasons})
    minimum = int(obligation.get("minimum", 1))
    status = "RESOLVED" if len(valid) >= minimum else "FAIL"
    return {
        "obligation_id": obligation.get("obligation_id"), "status": status,
        "satisfying_artifact_ids": sorted(str(x["artifact_id"]) for x in valid if x["artifact_id"]),
        "invalid_companions": sorted(invalid, key=lambda x: str(x["artifact_id"])),
        "reason_codes": [] if status == "RESOLVED" else ["REQUIRED_COMPANION_MISSING_OR_INVALID"],
        "authority_effect": "NONE_RESOLUTION_ONLY",
    }


def assess_orphan(artifact: Mapping[str, Any], relationships: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    lifecycle = artifact.get("lifecycle_class")
    current = lifecycle in {"CURRENT_AUTHORITATIVE", "CURRENT_IMPLEMENTATION", "CURRENT_SUPPORTING"}
    if not current:
        return {"artifact_id": artifact.get("artifact_id"), "status": "HISTORICAL_NON_ACTIONABLE", "actionable": False, "reason_codes": [], "authority_effect": "NONE_ASSESSMENT_ONLY"}
    useful = {"OWNED_BY", "GOVERNED_BY", "DOCUMENTS", "TESTS", "IMPLEMENTS", "DEPENDS_ON", "GENERATED_FROM", "REFERENCES"}
    lawful = [rel for rel in relationships if rel.get("relationship_type") in useful and rel.get("status", "RESOLVED") == "RESOLVED"]
    actionable = not lawful
    return {
        "artifact_id": artifact.get("artifact_id"),
        "status": "CURRENT_ACTIONABLE_ORPHAN" if actionable else "RESOLVED",
        "actionable": actionable,
        "reason_codes": ["NO_LAWFUL_PURPOSE_GOVERNANCE_OR_CONSUMER_RELATIONSHIP"] if actionable else [],
        "authority_effect": "NONE_ASSESSMENT_ONLY",
    }


def validate_workflow_governance(record: Mapping[str, Any]) -> dict[str, Any]:
    required = ("workflow_id", "owner", "purpose", "permissions", "commands", "lifecycle", "rollback")
    missing = [field for field in required if record.get(field) in (None, "", [], {})]
    if missing:
        return {"workflow_id": record.get("workflow_id"), "status": "FAIL", "reason_codes": ["MISSING_" + field.upper() for field in missing], "authority_effect": "NONE_ASSESSMENT_ONLY"}
    if record.get("lifecycle") not in {"CURRENT_SUPPORTING", "CURRENT_IMPLEMENTATION", "HISTORICAL_IMMUTABLE", "QUARANTINED"}:
        return {"workflow_id": record.get("workflow_id"), "status": "NOT_EVALUABLE", "reason_codes": ["WORKFLOW_LIFECYCLE_INVALID"], "authority_effect": "NONE_ASSESSMENT_ONLY"}
    return {"workflow_id": record["workflow_id"], "status": "PASS", "reason_codes": [], "authority_effect": "NONE_ASSESSMENT_ONLY"}
