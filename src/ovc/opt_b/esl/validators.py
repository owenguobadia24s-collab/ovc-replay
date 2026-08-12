from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable

from .model import (
    DependencyRef,
    DependencyRole,
    EvidenceFrontier,
    EvidenceState,
    OccurrencePack,
    StructuralOccurrenceRecord,
)


class ESLValidationError(ValueError):
    pass


_OWNER_RANK = {
    "OPT-A": 10,
    "C1": 20,
    "C2": 30,
    "C2P": 40,
    "C2E": 40,
    "OCCURRENCE_CONTEXT": 45,
    "ESL": 50,
    "SRI": 60,
    "SOI": 70,
    "CEI": 75,
    "C2.5": 80,
    "C3": 90,
    "RESEARCH_OPERATIONS": 100,
}

_ALLOWED_OCCURRENCE_OWNERS = {"OPT-A", "C1", "C2", "C2P", "C2E", "OCCURRENCE_CONTEXT", "ESL"}


def parse_utc(value: str, *, field: str) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ESLValidationError(f"ESL_TIME_NOT_UTC_Z:{field}")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise ESLValidationError(f"ESL_TIME_INVALID:{field}") from exc
    if parsed.tzinfo is None:
        raise ESLValidationError(f"ESL_TIME_NOT_UTC_Z:{field}")
    return parsed.astimezone(timezone.utc)


def validate_owner(ref: DependencyRef, *, consumer_owner: str = "ESL") -> None:
    if ref.owner not in _OWNER_RANK:
        raise ESLValidationError("ESL_OWNER_UNKNOWN:" + ref.owner)
    if consumer_owner not in _OWNER_RANK:
        raise ESLValidationError("ESL_OWNER_UNKNOWN:" + consumer_owner)
    if ref.owner not in _ALLOWED_OCCURRENCE_OWNERS:
        raise ESLValidationError("ESL_REVERSE_EDGE_FORBIDDEN:" + ref.owner)
    if _OWNER_RANK[ref.owner] > _OWNER_RANK[consumer_owner]:
        raise ESLValidationError("ESL_REVERSE_EDGE_FORBIDDEN:" + ref.owner)


def validate_dependencies(
    refs: Iterable[DependencyRef],
    *,
    conditional_required_active: Iterable[str] = (),
) -> None:
    active = set(conditional_required_active)
    seen: set[str] = set()
    for ref in refs:
        if ref.ref_id in seen:
            raise ESLValidationError("ESL_DUPLICATE_DEPENDENCY_REF:" + ref.ref_id)
        seen.add(ref.ref_id)
        validate_owner(ref)
        if ref.role is DependencyRole.FORBIDDEN:
            raise ESLValidationError("ESL_FORBIDDEN_DEPENDENCY_PRESENT:" + ref.ref_id)
        required = ref.role is DependencyRole.REQUIRED or (
            ref.role is DependencyRole.CONDITIONAL_REQUIRED and ref.ref_id in active
        )
        if required and ref.evidence_state is not EvidenceState.AVAILABLE:
            raise ESLValidationError("ESL_REQUIRED_DEPENDENCY_UNAVAILABLE:" + ref.ref_id)
        if ref.evidence_state is EvidenceState.AVAILABLE and not ref.first_valid_time:
            raise ESLValidationError("ESL_AVAILABLE_DEPENDENCY_FVT_MISSING:" + ref.ref_id)
        if ref.first_valid_time is not None:
            parse_utc(ref.first_valid_time, field=f"dependency:{ref.ref_id}:first_valid_time")


def validate_frontier(frontier: EvidenceFrontier, refs: Iterable[DependencyRef]) -> None:
    refs = tuple(refs)
    by_id = {ref.ref_id: ref for ref in refs}
    all_ids = set(by_id)
    frontier_ids = set(frontier.required_ref_ids) | set(frontier.optional_ref_ids) | set(frontier.missing_ref_ids)
    if not frontier_ids.issubset(all_ids):
        raise ESLValidationError("ESL_FRONTIER_UNKNOWN_REF")
    expected_missing = {ref.ref_id for ref in refs if ref.evidence_state is not EvidenceState.AVAILABLE}
    if set(frontier.missing_ref_ids) != expected_missing:
        raise ESLValidationError("ESL_FRONTIER_MISSING_SET_MISMATCH")
    if set(frontier.required_ref_ids) & set(frontier.optional_ref_ids):
        raise ESLValidationError("ESL_FRONTIER_ROLE_OVERLAP")
    if set(frontier.required_ref_ids) & set(frontier.missing_ref_ids):
        raise ESLValidationError("ESL_REQUIRED_REF_LISTED_MISSING")
    for ref_id, role in frontier.dependency_roles.items():
        if ref_id not in by_id:
            raise ESLValidationError("ESL_FRONTIER_UNKNOWN_ROLE_REF:" + ref_id)
        if DependencyRole(role) is not by_id[ref_id].role:
            raise ESLValidationError("ESL_FRONTIER_ROLE_MISMATCH:" + ref_id)
    cutoff = parse_utc(frontier.evaluation_cutoff, field="frontier:evaluation_cutoff")
    required_fvts = [
        parse_utc(by_id[ref_id].first_valid_time, field=f"dependency:{ref_id}:first_valid_time")
        for ref_id in frontier.required_ref_ids
        if by_id[ref_id].first_valid_time is not None
    ]
    if required_fvts:
        latest = max(required_fvts)
        if frontier.latest_required_fvt is None:
            raise ESLValidationError("ESL_FRONTIER_LATEST_REQUIRED_FVT_MISSING")
        declared = parse_utc(frontier.latest_required_fvt, field="frontier:latest_required_fvt")
        if declared != latest:
            raise ESLValidationError("ESL_FRONTIER_LATEST_REQUIRED_FVT_MISMATCH")
        if latest > cutoff:
            raise ESLValidationError("ESL_REQUIRED_FVT_AFTER_CUTOFF")
    elif frontier.latest_required_fvt is not None:
        raise ESLValidationError("ESL_FRONTIER_LATEST_REQUIRED_FVT_UNEXPECTED")
    actual_generations = tuple(sorted({ref.generation_id for ref in refs}))
    if tuple(sorted(frontier.source_generation_ids)) != actual_generations:
        raise ESLValidationError("ESL_FRONTIER_GENERATION_SET_MISMATCH")


def validate_comparability(record: StructuralOccurrenceRecord) -> None:
    domain = record.comparability_domain_id
    for ref in record.dependency_refs:
        if ref.role in {DependencyRole.DISPLAY_ONLY, DependencyRole.PROVENANCE_ONLY}:
            continue
        if ref.evidence_state is EvidenceState.NOT_COMPARABLE:
            if ref.role is DependencyRole.REQUIRED:
                raise ESLValidationError("ESL_REQUIRED_DEPENDENCY_NOT_COMPARABLE:" + ref.ref_id)
            continue
        if domain and ref.comparability_domain_id and ref.comparability_domain_id != domain:
            raise ESLValidationError("ESL_COMPARABILITY_DOMAIN_MISMATCH:" + ref.ref_id)


def validate_generation(record: StructuralOccurrenceRecord) -> None:
    referenced = tuple(sorted({ref.generation_id for ref in record.dependency_refs}))
    declared = tuple(sorted(record.source_generation_ids))
    if declared != referenced:
        raise ESLValidationError("ESL_OCCURRENCE_GENERATION_SET_MISMATCH")
    if tuple(sorted(record.evidence_frontier.source_generation_ids)) != declared:
        raise ESLValidationError("ESL_FRONTIER_OCCURRENCE_GENERATION_MISMATCH")


def validate_chronology(record: StructuralOccurrenceRecord) -> None:
    effective = parse_utc(record.effective_time, field="effective_time")
    fvt = parse_utc(record.first_valid_time, field="first_valid_time")
    cutoff = parse_utc(record.evaluation_cutoff, field="evaluation_cutoff")
    frontier_cutoff = parse_utc(record.evidence_frontier.evaluation_cutoff, field="frontier:evaluation_cutoff")
    if frontier_cutoff != cutoff:
        raise ESLValidationError("ESL_FRONTIER_CUTOFF_MISMATCH")
    if effective > fvt:
        raise ESLValidationError("ESL_FVT_BEFORE_EFFECTIVE_TIME")
    if fvt > cutoff:
        raise ESLValidationError("ESL_FVT_AFTER_EVALUATION_CUTOFF")
    required_fvts = [
        parse_utc(ref.first_valid_time, field=f"dependency:{ref.ref_id}:first_valid_time")
        for ref in record.dependency_refs
        if ref.identity_defining
        and ref.role in {DependencyRole.REQUIRED, DependencyRole.CONDITIONAL_REQUIRED}
        and ref.evidence_state is EvidenceState.AVAILABLE
        and ref.first_valid_time is not None
    ]
    if required_fvts and fvt < max(required_fvts):
        raise ESLValidationError("ESL_FVT_BACKDATED")


def validate_facets(record: StructuralOccurrenceRecord, pack: OccurrencePack) -> None:
    by_dimension = {}
    for facet in record.facets:
        if facet.dimension in by_dimension:
            raise ESLValidationError("ESL_DUPLICATE_FACET:" + facet.dimension.value)
        by_dimension[facet.dimension] = facet
        if facet.evidence_state is EvidenceState.AVAILABLE and facet.value is None:
            raise ESLValidationError("ESL_AVAILABLE_FACET_VALUE_MISSING:" + facet.dimension.value)
        if facet.evidence_state is not EvidenceState.AVAILABLE and facet.value is not None:
            raise ESLValidationError("ESL_NONAVAILABLE_FACET_VALUE_PRESENT:" + facet.dimension.value)
    for dimension in pack.required_dimensions:
        if dimension not in by_dimension:
            raise ESLValidationError("ESL_REQUIRED_FACET_ABSENT:" + dimension.value)


def validate_occurrence(record: StructuralOccurrenceRecord, pack: OccurrencePack) -> None:
    if record.occurrence_pack_id != pack.occurrence_pack_id:
        raise ESLValidationError("ESL_OCCURRENCE_PACK_MISMATCH")
    if record.anchor.anchor_kind != pack.anchor_kind:
        raise ESLValidationError("ESL_ANCHOR_KIND_MISMATCH")
    if pack.comparability_domain_id and record.comparability_domain_id != pack.comparability_domain_id:
        raise ESLValidationError("ESL_PACK_COMPARABILITY_DOMAIN_MISMATCH")
    validate_dependencies(record.dependency_refs)
    present_required_types = {
        ref.object_type
        for ref in record.dependency_refs
        if ref.role is DependencyRole.REQUIRED and ref.evidence_state is EvidenceState.AVAILABLE
    }
    missing_types = set(pack.required_source_types) - present_required_types
    if missing_types:
        raise ESLValidationError("ESL_REQUIRED_SOURCE_TYPE_MISSING:" + ",".join(sorted(missing_types)))
    validate_frontier(record.evidence_frontier, record.dependency_refs)
    validate_generation(record)
    validate_chronology(record)
    validate_comparability(record)
    validate_facets(record, pack)
    if record.authority_state != "INACTIVE_CONFORMANCE_ONLY":
        raise ESLValidationError("ESL_AUTHORITY_STATE_NOT_INACTIVE")
