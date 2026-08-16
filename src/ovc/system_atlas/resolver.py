from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping, Sequence

from ovc.development.skills.vit_current_state import resolve_current_vit_query

from .canonical import canonical_sha256, logical_id


class AtlasResolverError(ValueError):
    """Raised when resolver input would require guessing or scope widening."""


REFERENCE_RESOLVER_VERSION = "0.1"
HIGH_RISK_PREDICATE_ALIASES = {"OWNED_BY": "OWNS", "GOVERNED_BY": "GOVERNS"}
HIGH_RISK_EVIDENCE = {"SOURCE_EXPLICIT", "LINEAGE_EXPLICIT"}
AUTHORITY_INTERSECTION_FACTORS = (
    "programme_scope",
    "domain_scope",
    "runtime_permission",
    "security_policy",
    "prerequisite_state",
    "currentness",
)


def _require(condition: bool, code: str) -> None:
    if not condition:
        raise AtlasResolverError(code)


def relationship_resolution_state(
    *, declared: bool | None, observed: bool | None, forbidden: bool, authority_conflict: bool = False
) -> str:
    if authority_conflict:
        return "CONFLICTING"
    if forbidden and observed is True:
        return "FORBIDDEN_OBSERVED"
    if declared is True and observed is True:
        return "RECONCILED"
    if declared is True and observed is False:
        return "DECLARED_ONLY"
    if declared is False and observed is True:
        return "OBSERVED_ONLY"
    return "UNRESOLVED"


def _explicit_identity(value: str, bindings: Mapping[str, Mapping[str, Any]]) -> str:
    binding = bindings.get(value)
    if binding is None:
        return value
    _require(binding.get("continuity_status") == "EXPLICIT", "ATLAS_IDENTITY_BINDING_NOT_EXPLICIT")
    canonical_id = str(binding.get("canonical_id", ""))
    _require(bool(canonical_id), "ATLAS_IDENTITY_CANONICAL_ID_REQUIRED")
    return canonical_id


def _rules_by_predicate(registry: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    _require(registry.get("schema") == "ovc-system-atlas-predicate-authority-registry/v1", "ATLAS_PREDICATE_REGISTRY_INVALID")
    rules = registry.get("predicates")
    _require(isinstance(rules, Sequence) and not isinstance(rules, (str, bytes)), "ATLAS_PREDICATE_RULES_INVALID")
    result: dict[str, Mapping[str, Any]] = {}
    for rule in rules:
        _require(isinstance(rule, Mapping) and bool(rule.get("predicate")), "ATLAS_PREDICATE_RULE_INVALID")
        predicate = str(rule["predicate"])
        _require(predicate not in result, "ATLAS_PREDICATE_RULE_DUPLICATE")
        result[predicate] = rule
    return result


def _candidate(candidate: Mapping[str, Any], identity_bindings: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    subject = _explicit_identity(str(candidate.get("subject_id", "")), identity_bindings)
    predicate = HIGH_RISK_PREDICATE_ALIASES.get(str(candidate.get("predicate", "")), str(candidate.get("predicate", "")))
    value = deepcopy(candidate.get("value"))
    if isinstance(value, str):
        value = _explicit_identity(value, identity_bindings)
    scope = candidate.get("scope")
    _require(bool(subject) and bool(predicate), "ATLAS_RESOLVER_CANDIDATE_IDENTITY_REQUIRED")
    _require(isinstance(scope, Mapping) and isinstance(scope.get("dimensions"), Mapping), "ATLAS_RESOLVER_SCOPE_REQUIRED")
    body = {
        "subject_id": subject,
        "predicate": predicate,
        "value": value,
        "source_class": str(candidate.get("source_class", "")),
        "evidence_class": str(candidate.get("evidence_class", "")),
        "source_currentness": str(candidate.get("source_currentness", "")),
        "scope": deepcopy(dict(scope)),
        "authority_factors": deepcopy(candidate.get("authority_factors")),
        "source_ref": deepcopy(candidate.get("source_ref")),
    }
    candidate_id = str(candidate.get("candidate_id", "")) or logical_id("resolver-candidate", body)
    return {"candidate_id": candidate_id, **body}


def _admissibility(candidate: Mapping[str, Any], rule: Mapping[str, Any]) -> list[str]:
    reasons = []
    if candidate["source_class"] not in set(rule.get("permitted_source_classes", [])):
        reasons.append("SOURCE_CLASS_NOT_ADMITTED")
    if candidate["evidence_class"] not in HIGH_RISK_EVIDENCE:
        reasons.append("EVIDENCE_CLASS_NOT_HIGH_RISK_ELIGIBLE")
    if candidate["source_currentness"] != "CURRENT":
        reasons.append("SOURCE_NOT_CURRENT")
    dimensions = candidate["scope"]["dimensions"]
    missing = [name for name in rule.get("required_dimensions", []) if name not in dimensions]
    if missing:
        reasons.append("REQUIRED_SCOPE_DIMENSION_MISSING:" + ",".join(sorted(missing)))
    return reasons


def _authority_outcome(candidates: Sequence[Mapping[str, Any]]) -> tuple[str, Any, list[str]]:
    effects = {str(row.get("value", {}).get("effect", "UNKNOWN")) for row in candidates if isinstance(row.get("value"), Mapping)}
    if "DENIED" in effects:
        return "DENIED", False, ["EXPLICIT_DENIAL_CONTROLS"]
    if "RESERVED" in effects:
        return "RESERVED", False, ["EXPLICIT_RESERVATION_CONTROLS"]
    grants = [row for row in candidates if isinstance(row.get("value"), Mapping) and row["value"].get("effect") == "GRANTED"]
    if not grants:
        return "UNRESOLVED", False, ["NO_EXACT_GRANT"]
    failed: set[str] = set()
    for grant in grants:
        factors = grant.get("authority_factors")
        if not isinstance(factors, Mapping):
            failed.update(AUTHORITY_INTERSECTION_FACTORS)
            continue
        failed.update(name for name in AUTHORITY_INTERSECTION_FACTORS if factors.get(name) != "ALLOW")
    if failed:
        return "UNRESOLVED", False, ["AUTHORITY_INTERSECTION_NOT_PROVEN:" + ",".join(sorted(failed))]
    return "RECONCILED", True, ["EXACT_AUTHORITY_INTERSECTION_PASS"]


def resolve_reference_candidates(
    candidates: Sequence[Mapping[str, Any]],
    *,
    predicate_registry: Mapping[str, Any],
    identity_bindings: Mapping[str, Mapping[str, Any]] | None = None,
    algorithm_gate_status: str = "PENDING",
) -> dict[str, Any]:
    """Resolve high-risk candidates without activating or publishing the results."""
    _require(algorithm_gate_status in {"PENDING", "PASS"}, "ATLAS_G4_ALG_STATUS_INVALID")
    rules = _rules_by_predicate(predicate_registry)
    bindings = identity_bindings or {}
    normalized = [_candidate(row, bindings) for row in candidates]
    normalized.sort(key=lambda row: row["candidate_id"])
    groups: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
    for row in normalized:
        scope_hash = canonical_sha256(row["scope"])
        groups.setdefault((row["subject_id"], row["predicate"], scope_hash), []).append(row)

    resolutions = []
    conflicts = []
    for (subject, predicate, scope_hash), rows in sorted(groups.items()):
        rule = rules.get(predicate)
        reasons_by_candidate: dict[str, list[str]] = {}
        if rule is None:
            admitted: list[dict[str, Any]] = []
            for row in rows:
                reasons_by_candidate[row["candidate_id"]] = ["PREDICATE_POLICY_MISSING"]
        else:
            for row in rows:
                reasons_by_candidate[row["candidate_id"]] = _admissibility(row, rule)
            admitted = [row for row in rows if not reasons_by_candidate[row["candidate_id"]]]

        resolution_status = "UNRESOLVED"
        value: Any = None
        reasons: list[str] = []
        conflict_id = None
        if not admitted:
            reasons = sorted({reason for values in reasons_by_candidate.values() for reason in values}) or ["NO_ADMISSIBLE_CANDIDATE"]
        elif predicate in {"OWNS", "GOVERNS"}:
            distinct = {canonical_sha256(row["value"]) for row in admitted}
            if len(distinct) > 1:
                resolution_status = "CONFLICTING"
                reasons = [str(rule.get("conflict_class", "OWNER_CONFLICT"))]
                conflict_body = {
                    "subject_id": subject,
                    "predicate": predicate,
                    "scope_hash": scope_hash,
                    "competing_candidate_ids": sorted(row["candidate_id"] for row in admitted),
                    "conflict_class": str(rule.get("conflict_class", "OWNER_CONFLICT")),
                }
                conflict_id = logical_id("resolver-conflict", conflict_body)
                conflicts.append({"conflict_id": conflict_id, **conflict_body, "status": "OPEN", "authority_effect": "NONE"})
            else:
                resolution_status = "RECONCILED"
                value = admitted[0]["value"]
                reasons = ["EXACTLY_ONE_OWNER_VALUE"]
        elif predicate == "AUTHORISED":
            resolution_status, value, reasons = _authority_outcome(admitted)
        else:
            precedence = list(rule.get("precedence", []))
            ranks = {source: index for index, source in enumerate(precedence)}
            best_rank = min(ranks.get(row["source_class"], len(ranks)) for row in admitted)
            controlling = [row for row in admitted if ranks.get(row["source_class"], len(ranks)) == best_rank]
            distinct = {canonical_sha256(row["value"]) for row in controlling}
            if len(distinct) > 1:
                resolution_status = "CONFLICTING"
                reasons = [str(rule.get("conflict_class", "PREDICATE_CONFLICT"))]
                conflict_body = {
                    "subject_id": subject,
                    "predicate": predicate,
                    "scope_hash": scope_hash,
                    "competing_candidate_ids": sorted(row["candidate_id"] for row in controlling),
                    "conflict_class": str(rule.get("conflict_class", "PREDICATE_CONFLICT")),
                }
                conflict_id = logical_id("resolver-conflict", conflict_body)
                conflicts.append({"conflict_id": conflict_id, **conflict_body, "status": "OPEN", "authority_effect": "NONE"})
            else:
                resolution_status = "RECONCILED"
                value = controlling[0]["value"]
                reasons = ["PREDICATE_PRECEDENCE_EXACT"]

        result_body = {
            "subject_id": subject,
            "predicate": predicate,
            "scope": deepcopy(rows[0]["scope"]),
            "scope_hash": scope_hash,
            "resolution_status": resolution_status,
            "value": value,
            "candidate_ids": [row["candidate_id"] for row in rows],
            "admitted_candidate_ids": [row["candidate_id"] for row in admitted],
            "candidate_reasons": reasons_by_candidate,
            "reasons": reasons,
            "conflict_id": conflict_id,
        }
        resolutions.append(
            {
                "resolution_id": logical_id("predicate-resolution", result_body),
                **result_body,
                "canonical_eligibility": "ELIGIBLE" if algorithm_gate_status == "PASS" and resolution_status == "RECONCILED" else "DENIED_PENDING_ATLAS_G4_ALG" if resolution_status == "RECONCILED" else "INELIGIBLE",
                "authority_effect": "NONE_REFERENCE_RESOLUTION_ONLY",
            }
        )

    resolutions.sort(key=lambda row: row["resolution_id"])
    conflicts.sort(key=lambda row: row["conflict_id"])
    body = {
        "schema": "ovc-atlas-reference-resolution-set/v1",
        "resolver_version": REFERENCE_RESOLVER_VERSION,
        "algorithm_gate_status": algorithm_gate_status,
        "normalized_candidates": normalized,
        "resolutions": resolutions,
        "conflicts": conflicts,
        "canonical_assertions": [],
        "authority_effect": "NONE_REFERENCE_RESOLVER_NOT_AUTHORITY",
    }
    return {**body, "resolution_set_hash": canonical_sha256(body)}


def resolve_current_vit_projection(repository_root: Path | str) -> dict[str, Any]:
    """Consume the accepted VIT current-state resolver without historical fallback."""
    current = resolve_current_vit_query(Path(repository_root))
    _require(current.get("resolution_status") == "RESOLVED_CURRENT", "ATLAS_VIT_CURRENT_STATUS_UNRESOLVED")
    _require(current.get("historical_source_fallback_allowed") is False, "ATLAS_VIT_HISTORICAL_FALLBACK_FORBIDDEN")
    active = (
        current.get("general_authority_status") == "ACTIVE"
        and current.get("default_execution_substrate_status") == "ACTIVE"
        and str(current.get("vit_live_physical_main_control", "")).startswith("ACTIVE_")
    )
    predicates = [
        {
            "subject_id": "ovc:programme:dsai-vit-v0.3",
            "predicate": "CURRENT",
            "value": True,
            "exact_source_chain": deepcopy(current["current_sources"]),
            "canonical_eligibility": "DENIED_PENDING_ATLAS_G4_ALG",
        },
        {
            "subject_id": "ovc:programme:dsai-vit-v0.3",
            "predicate": "ACTIVE",
            "value": active,
            "exact_source_chain": deepcopy(current["current_sources"]),
            "canonical_eligibility": "DENIED_PENDING_ATLAS_G4_ALG",
        },
        {
            "subject_id": "ovc:programme:dsai-vit-v0.3",
            "predicate": "AUTHORISED",
            "value": current.get("general_authority_status") == "ACTIVE",
            "exact_source_chain": deepcopy(current["current_sources"]),
            "canonical_eligibility": "DENIED_PENDING_ATLAS_G4_ALG",
        },
    ]
    body = {
        "schema": "ovc-atlas-vit-current-projection/v1",
        "source_resolver": "ovc.development.skills.vit_current_state.resolve_current_vit_query",
        "source_resolution": current,
        "predicates": predicates,
        "canonical_assertions": [],
        "historical_source_fallback_allowed": False,
        "authority_effect": "NONE_CURRENT_STATE_PROJECTION_ONLY",
    }
    return {**body, "projection_hash": canonical_sha256(body)}
