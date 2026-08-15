from __future__ import annotations

import hashlib
from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Iterable, Mapping

from .core import RCCRValidationError, canonical_json_bytes, logical_identity, validate_canonical_object

DERIVATION_MODES = {
    "SOURCE_EXPLICIT",
    "SOURCE_CROSSWALK",
    "PROTOCOL_DERIVED",
    "THEORY_IMPLICATION_DERIVED",
    "OPERATOR_FORMALISED",
    "EXTERNAL_FINDING_CROSSWALK",
}

CANONICAL_DERIVATION_CLASS = {
    "SOURCE_EXPLICIT": "OWNER_EXPLICIT",
    "SOURCE_CROSSWALK": "SOURCE_FAITHFUL_DETERMINISTIC",
    "PROTOCOL_DERIVED": "PROTOCOL_EXPLICIT",
    "THEORY_IMPLICATION_DERIVED": "SOURCE_FAITHFUL_DETERMINISTIC",
    "OPERATOR_FORMALISED": "HUMAN_REVIEWED",
    "EXTERNAL_FINDING_CROSSWALK": "HUMAN_REVIEWED",
}


@dataclass(frozen=True)
class ResolvedSource:
    source_id: str
    source_owner: str
    object_type: str
    semantic_generation: str
    semantic_payload_hash: str
    artifact_byte_hash: str | None
    first_valid_time: str
    authority_state: str
    source_refs: tuple[str, ...]
    source_class: str
    owner_authority_effect: str
    exact_source_token: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id,
            "source_owner": self.source_owner,
            "object_type": self.object_type,
            "semantic_generation": self.semantic_generation,
            "semantic_payload_hash": self.semantic_payload_hash,
            "artifact_byte_hash": self.artifact_byte_hash,
            "first_valid_time": self.first_valid_time,
            "authority_state": self.authority_state,
            "source_refs": list(self.source_refs),
            "source_class": self.source_class,
            "owner_authority_effect": self.owner_authority_effect,
            "exact_source_token": self.exact_source_token,
            "authority_effect": "NONE",
        }


class SourceResolverService:
    """Read-only exact-identity RCCR source resolver.

    The catalog is supplied by an owning repository/external binding adapter. RCCR never scans
    protected payloads, resolves by title, or converts external evidence into owner authority.
    """

    def __init__(self, catalog: Iterable[Mapping[str, Any]]):
        self._catalog: dict[str, dict[str, Any]] = {}
        for raw in catalog:
            item = dict(raw)
            source_id = item.get("source_id")
            if not isinstance(source_id, str) or not source_id:
                raise RCCRValidationError("SOURCE_EXACT_ID_REQUIRED", "catalog item has no source_id")
            if source_id in self._catalog:
                raise RCCRValidationError("DUPLICATE_SOURCE_ID", source_id)
            self._catalog[source_id] = item

    def resolve(self, source_id: str) -> ResolvedSource:
        if not isinstance(source_id, str) or not source_id:
            raise RCCRValidationError("SOURCE_EXACT_ID_REQUIRED", str(source_id))
        if source_id not in self._catalog:
            raise RCCRValidationError("SOURCE_NOT_FOUND_EXACT_ID", source_id)
        item = deepcopy(self._catalog[source_id])
        if item.get("protected") is True or str(item.get("protection_class", "")).upper() == "VALIDATION":
            raise RCCRValidationError("PROTECTED_SOURCE_DENIED", source_id)
        owner = item.get("source_owner")
        authority_state = item.get("authority_state")
        if not isinstance(owner, str) or not owner or not isinstance(authority_state, str) or not authority_state:
            raise RCCRValidationError("MISSING_OWNER_AUTHORITY", source_id)
        source_class = str(item.get("source_class", "OWNER")).upper()
        owner_authority_effect = "NONE" if source_class == "EXTERNAL" else "PRESERVE_OWNER_STATE"
        required = {
            "object_type",
            "semantic_generation",
            "semantic_payload_hash",
            "first_valid_time",
            "source_refs",
        }
        missing = sorted(key for key in required if item.get(key) in (None, ""))
        if missing:
            raise RCCRValidationError("SOURCE_METADATA_INCOMPLETE", f"{source_id}:{','.join(missing)}")
        digest_material = {
            "source_id": source_id,
            "source_owner": owner,
            "object_type": item["object_type"],
            "semantic_generation": item["semantic_generation"],
            "semantic_payload_hash": item["semantic_payload_hash"],
            "artifact_byte_hash": item.get("artifact_byte_hash"),
            "first_valid_time": item["first_valid_time"],
            "authority_state": authority_state,
            "source_refs": list(item["source_refs"]),
            "source_class": source_class,
            "owner_authority_effect": owner_authority_effect,
        }
        token = hashlib.sha256(canonical_json_bytes(digest_material)).hexdigest()
        return ResolvedSource(
            source_id=source_id,
            source_owner=owner,
            object_type=str(item["object_type"]),
            semantic_generation=str(item["semantic_generation"]),
            semantic_payload_hash=str(item["semantic_payload_hash"]),
            artifact_byte_hash=item.get("artifact_byte_hash"),
            first_valid_time=str(item["first_valid_time"]),
            authority_state=authority_state,
            source_refs=tuple(str(ref) for ref in item["source_refs"]),
            source_class=source_class,
            owner_authority_effect=owner_authority_effect,
            exact_source_token=token,
        )

    def manifest(self, source_ids: Iterable[str]) -> dict[str, Any]:
        resolved = [self.resolve(source_id).as_dict() for source_id in source_ids]
        resolved.sort(key=lambda item: item["source_id"])
        payload = {
            "schema": "ovc-rccr-source-resolution-manifest/v1",
            "sources": resolved,
            "protected_payloads_opened": False,
            "authority_effect": "NONE",
        }
        payload["manifest_hash"] = hashlib.sha256(canonical_json_bytes(payload)).hexdigest()
        return payload


class RequirementProfileCompiler:
    def compile(
        self,
        *,
        coverage_item_generation_id: str,
        resolved_source: ResolvedSource,
        derivation_mode: str,
        requirements: Mapping[str, Iterable[str]],
        derivation_refs: Iterable[str] = (),
        reviewer: str | None = None,
        reviewed_at: str | None = None,
        semantic_choice_required: bool = False,
        theory_implications_explicit: bool = True,
        theory_falsifiers_explicit: bool = True,
        supersedes_requirement_profile_id: str | None = None,
    ) -> dict[str, Any]:
        if derivation_mode not in DERIVATION_MODES:
            raise RCCRValidationError("UNKNOWN_DERIVATION_MODE", derivation_mode)
        human_required = derivation_mode in {"OPERATOR_FORMALISED", "EXTERNAL_FINDING_CROSSWALK"}
        human_required = human_required or semantic_choice_required
        if derivation_mode == "THEORY_IMPLICATION_DERIVED" and not (
            theory_implications_explicit and theory_falsifiers_explicit
        ):
            human_required = True
        if human_required and not reviewer:
            raise RCCRValidationError("HUMAN_REVIEW_REQUIRED", derivation_mode)
        canonical_class = CANONICAL_DERIVATION_CLASS[derivation_mode]
        if human_required:
            canonical_class = "HUMAN_REVIEWED"
        refs = sorted(set(str(ref) for ref in derivation_refs) | set(resolved_source.source_refs) | {resolved_source.source_id})
        if resolved_source.source_class == "EXTERNAL":
            refs.append("EXTERNAL_SOURCE_AUTHORITY_EFFECT_NONE")
        def values(name: str) -> list[str]:
            return sorted(str(value) for value in requirements.get(name, ()))
        record: dict[str, Any] = {
            "schema_version": "0.1",
            "requirement_profile_id": "PENDING",
            "coverage_item_generation_id": coverage_item_generation_id,
            "derivation_class": canonical_class,
            "derivation_refs": refs,
            "reviewer": reviewer,
            "reviewed_at": reviewed_at,
            "scientific_constructs": values("scientific_constructs"),
            "epistemic_requirements": values("epistemic_requirements"),
            "evidence_requirements": values("evidence_requirements"),
            "population_requirements": values("population_requirements"),
            "chronology_requirements": values("chronology_requirements"),
            "inferential_requirements": values("inferential_requirements"),
            "denominator_requirements": values("denominator_requirements"),
            "comparability_requirements": values("comparability_requirements"),
            "forbidden_dependencies": values("forbidden_dependencies"),
            "sufficiency_conditions": values("sufficiency_conditions"),
            "partial_sufficiency_conditions": values("partial_sufficiency_conditions"),
            "invalidating_conditions": values("invalidating_conditions"),
            "known_limitations": values("known_limitations"),
            "supersedes_requirement_profile_id": supersedes_requirement_profile_id,
            "first_valid_time": resolved_source.first_valid_time,
            "provenance_refs": sorted(set(refs) | {resolved_source.exact_source_token, f"DERIVATION_MODE:{derivation_mode}"}),
            "authority_effect": "NONE",
        }
        record["requirement_profile_id"] = logical_identity("ResearchRequirementProfile", record)
        validate_canonical_object("ResearchRequirementProfile", record)
        return record


class RequirementDependencyIndex:
    def __init__(self) -> None:
        self._items: dict[str, tuple[str, ...]] = {}

    def register(self, requirement_profile: Mapping[str, Any]) -> None:
        profile_id = str(requirement_profile["requirement_profile_id"])
        refs = tuple(sorted(set(str(ref) for ref in requirement_profile["derivation_refs"])))
        if profile_id in self._items and self._items[profile_id] != refs:
            raise RCCRValidationError("DEPENDENCY_INDEX_COLLISION", profile_id)
        self._items[profile_id] = refs

    def dependencies(self, profile_id: str) -> tuple[str, ...]:
        return self._items.get(profile_id, ())


def project_currentness(
    *,
    prior_source_token: str,
    current_source_token: str,
    prior_protocol_token: str,
    current_protocol_token: str,
) -> str:
    if prior_protocol_token != current_protocol_token:
        return "STALE_PROTOCOL"
    if prior_source_token != current_source_token:
        return "STALE_SOURCE"
    return "CURRENT"
