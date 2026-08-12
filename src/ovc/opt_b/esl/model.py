from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping, Tuple


class DependencyRole(str, Enum):
    REQUIRED = "REQUIRED"
    OPTIONAL = "OPTIONAL"
    CONDITIONAL_REQUIRED = "CONDITIONAL_REQUIRED"
    STRATIFIER = "STRATIFIER"
    FILTER = "FILTER"
    DISPLAY_ONLY = "DISPLAY_ONLY"
    PROVENANCE_ONLY = "PROVENANCE_ONLY"
    FORBIDDEN = "FORBIDDEN"


class EvidenceState(str, Enum):
    AVAILABLE = "AVAILABLE"
    MISSING = "MISSING"
    NOT_EVALUABLE = "NOT_EVALUABLE"
    NOT_COMPARABLE = "NOT_COMPARABLE"
    CENSORED = "CENSORED"
    AMBIGUOUS = "AMBIGUOUS"
    CONFLICT = "CONFLICT"
    QUARANTINED = "QUARANTINED"
    UNRESOLVED = "UNRESOLVED"


class ExecutionProfile(str, Enum):
    BASE_STRUCTURAL = "BASE_STRUCTURAL"
    ORGANISATION_ENRICHED = "ORGANISATION_ENRICHED"
    CONSTRAINT_ENRICHED = "CONSTRAINT_ENRICHED"
    FULL_RESEARCH = "FULL_RESEARCH"


class StructuralDimension(str, Enum):
    LOCATION = "LOCATION"
    MOTION = "MOTION"
    ORGANISATION = "ORGANISATION"
    INTERACTION = "INTERACTION"


@dataclass(frozen=True)
class OccurrenceAnchor:
    anchor_kind: str
    anchor_id: str
    instrument: str
    side: str
    scale: str
    clock: str = "UTC"


@dataclass(frozen=True)
class DependencyRef:
    ref_id: str
    owner: str
    object_type: str
    role: DependencyRole
    evidence_state: EvidenceState
    first_valid_time: str | None
    generation_id: str
    comparability_domain_id: str | None = None
    identity_defining: bool = True


@dataclass(frozen=True)
class StructuralFacet:
    dimension: StructuralDimension
    evidence_state: EvidenceState
    source_ref_ids: Tuple[str, ...] = ()
    value: Mapping[str, Any] | None = None
    reason_codes: Tuple[str, ...] = ()


@dataclass(frozen=True)
class ComparabilityDomain:
    comparability_domain_id: str
    instrument: str
    side: str
    scale: str
    clock: str
    generation_scope: str


@dataclass(frozen=True)
class OccurrencePack:
    occurrence_pack_id: str
    anchor_kind: str
    required_dimensions: Tuple[StructuralDimension, ...]
    required_source_types: Tuple[str, ...] = ()
    optional_source_types: Tuple[str, ...] = ()
    comparability_domain_id: str | None = None
    identity_projection_fields: Tuple[str, ...] = (
        "occurrence_pack_id",
        "anchor",
        "evaluation_cutoff",
        "facets",
        "dependency_refs",
        "evidence_frontier",
        "source_generation_ids",
    )


@dataclass(frozen=True)
class EvidenceFrontier:
    evaluation_cutoff: str
    required_ref_ids: Tuple[str, ...]
    optional_ref_ids: Tuple[str, ...]
    missing_ref_ids: Tuple[str, ...]
    source_generation_ids: Tuple[str, ...]
    latest_required_fvt: str | None
    dependency_roles: Mapping[str, DependencyRole]
    comparability_domain_id: str | None


@dataclass(frozen=True)
class GenerationCorrespondence:
    source_generation_id: str
    target_generation_id: str
    relation: str
    source_ref_ids: Tuple[str, ...]
    target_ref_ids: Tuple[str, ...]
    reason_codes: Tuple[str, ...] = ()


@dataclass(frozen=True)
class StructuralOccurrenceRecord:
    occurrence_record_id: str | None
    occurrence_pack_id: str
    anchor: OccurrenceAnchor
    evaluation_cutoff: str
    first_valid_time: str
    effective_time: str
    facets: Tuple[StructuralFacet, ...]
    dependency_refs: Tuple[DependencyRef, ...]
    evidence_frontier: EvidenceFrontier
    source_generation_ids: Tuple[str, ...]
    comparability_domain_id: str | None
    authority_state: str = "INACTIVE_CONFORMANCE_ONLY"
    extensions: Mapping[str, Any] = field(default_factory=dict)
