"""Shared Systems v0.1 owner-neutral evidence/state/interface envelopes.

This is an inactive, standard-library-only reference implementation.  It transports
owner facts and typed degraded states; it never creates authority or domain meaning.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Iterable, Mapping


class SharedEnvelopeError(ValueError):
    """Fail-closed envelope validation error."""


PLANE_FAMILIES = frozenset({
    "LIFECYCLE", "AVAILABILITY", "OBSERVABILITY", "EVALUABILITY",
    "COMPARABILITY", "EXECUTION", "AUTHORITY", "MATURITY",
    "PROGRESSION", "ASSURANCE", "REPRODUCIBILITY",
})
LINEAGE_PLANES = frozenset({
    "DERIVATION", "GENEALOGY", "CORRESPONDENCE", "SUPERSESSION_VERSION",
    "RESEARCH_EVIDENCE", "REPOSITORY_GOVERNANCE", "DEPENDENCY_IMPACT",
})
COMPATIBILITY_CLASSES = frozenset({
    "IDENTICAL", "BACKWARD_COMPATIBLE", "FORWARD_COMPATIBLE",
    "BIDIRECTIONAL_COMPATIBLE", "ADAPTER_REQUIRED", "LOSSY_ADAPTER_ALLOWED",
    "HISTORICAL_REPLAY_ONLY", "INCOMPATIBLE", "UNKNOWN",
})


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise SharedEnvelopeError(f"{field.upper()}_INVALID")
    return value


def _strings(value: Any, field: str) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)) or any(not isinstance(v, str) or not v for v in value):
        raise SharedEnvelopeError(f"{field.upper()}_INVALID")
    result = tuple(value)
    if len(result) != len(set(result)):
        raise SharedEnvelopeError(f"{field.upper()}_DUPLICATE")
    return result


def _utc(value: str, field: str) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise SharedEnvelopeError(f"{field.upper()}_UTC_Z_REQUIRED")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise SharedEnvelopeError(f"{field.upper()}_INVALID") from exc
    if parsed.tzinfo != timezone.utc:
        raise SharedEnvelopeError(f"{field.upper()}_UTC_REQUIRED")
    return parsed


@dataclass(frozen=True)
class StatePlaneValue:
    plane_family: str
    owner_namespace: str
    owner_state: str
    owning_rule_ref: str | None = None
    authority_effect: str = "NONE"

    def __post_init__(self) -> None:
        if self.plane_family not in PLANE_FAMILIES:
            raise SharedEnvelopeError(f"STATE_PLANE_UNKNOWN:{self.plane_family}")
        _text(self.owner_namespace, "owner_namespace")
        _text(self.owner_state, "owner_state")
        if self.authority_effect != "NONE":
            raise SharedEnvelopeError("STATE_PLANE_AUTHORITY_EFFECT_FORBIDDEN")


@dataclass(frozen=True)
class StateVector:
    values: tuple[StatePlaneValue, ...]

    def __post_init__(self) -> None:
        keys = [(v.plane_family, v.owner_namespace) for v in self.values]
        if len(keys) != len(set(keys)):
            raise SharedEnvelopeError("STATE_VECTOR_PLANE_AMBIGUOUS")

    def value(self, plane_family: str, owner_namespace: str) -> StatePlaneValue | None:
        return next((v for v in self.values if v.plane_family == plane_family and v.owner_namespace == owner_namespace), None)

    def authority(self, owner_namespace: str) -> str:
        value = self.value("AUTHORITY", owner_namespace)
        return value.owner_state if value else "UNKNOWN"


def research_operations_legacy_state(*, lifecycle_state: str, authority_state: str, authority_decision_ref: str | None = None) -> StateVector:
    """Preserve RO FROZEN as record governance, never as authorization."""
    values = [StatePlaneValue("LIFECYCLE", "RESEARCH_OPERATIONS", lifecycle_state)]
    if authority_state == "FROZEN":
        values.append(StatePlaneValue("AUTHORITY", "RESEARCH_OPERATIONS", "UNKNOWN", authority_decision_ref))
    else:
        values.append(StatePlaneValue("AUTHORITY", "RESEARCH_OPERATIONS", authority_state, authority_decision_ref))
    return StateVector(tuple(values))


@dataclass(frozen=True)
class DependencyDescriptor:
    source_requirement: str
    requiredness: str
    consumption_policy: str
    purpose: str
    owner_role: str
    failure_disposition: str
    source_owner: str
    dependent_surfaces: tuple[str, ...]
    authority_requirement: str | None = None
    comparability_requirement: str | None = None

    def __post_init__(self) -> None:
        for field in ("source_requirement", "purpose", "owner_role", "failure_disposition", "source_owner"):
            _text(getattr(self, field), field)
        if self.requiredness not in {"REQUIRED", "OPTIONAL", "CONDITIONAL"}:
            raise SharedEnvelopeError("DEPENDENCY_REQUIREDNESS_UNKNOWN")
        if self.consumption_policy not in {"ALLOWED", "FORBIDDEN"}:
            raise SharedEnvelopeError("DEPENDENCY_CONSUMPTION_POLICY_UNKNOWN")
        if not self.dependent_surfaces:
            raise SharedEnvelopeError("DEPENDENCY_SURFACES_REQUIRED")
        _strings(self.dependent_surfaces, "dependent_surfaces")

    def missing_disposition(self) -> dict[str, Any]:
        if self.consumption_policy == "FORBIDDEN":
            return {"status": "FORBIDDEN", "affected_surfaces": self.dependent_surfaces, "reason_code": self.failure_disposition}
        status = "NOT_EVALUABLE" if self.requiredness == "REQUIRED" else "MISSING_OPTIONAL"
        return {"status": status, "affected_surfaces": self.dependent_surfaces, "reason_code": self.failure_disposition}


@dataclass(frozen=True)
class EvidenceEntry:
    evidence_id: str
    dependency_ref: str
    first_valid_time: str
    source_generation: str

    def __post_init__(self) -> None:
        for field in ("evidence_id", "dependency_ref", "source_generation"):
            _text(getattr(self, field), field)
        _utc(self.first_valid_time, "first_valid_time")


@dataclass(frozen=True)
class EvidenceFrontier:
    frontier_id: str
    schema_version: str
    owner_namespace: str
    evaluation_cutoff: str
    dependency_manifest_ref: str
    evidence_entries: tuple[EvidenceEntry, ...]
    missing_entries: tuple[str, ...]
    latest_required_first_valid_time: str | None
    source_generations: tuple[str, ...]
    reason_codes: tuple[str, ...] = ()
    comparability_domain_ref: str | None = None
    authority_snapshot_ref: str | None = None

    def __post_init__(self) -> None:
        for field in ("frontier_id", "schema_version", "owner_namespace", "dependency_manifest_ref"):
            _text(getattr(self, field), field)
        cutoff = _utc(self.evaluation_cutoff, "evaluation_cutoff")
        if any(_utc(e.first_valid_time, "first_valid_time") > cutoff for e in self.evidence_entries):
            raise SharedEnvelopeError("EVIDENCE_AFTER_CUTOFF")
        ids = [e.evidence_id for e in self.evidence_entries]
        if len(ids) != len(set(ids)) or set(ids) & set(self.missing_entries):
            raise SharedEnvelopeError("EVIDENCE_PRESENT_MISSING_CONFLICT")
        if self.latest_required_first_valid_time is not None:
            latest = _utc(self.latest_required_first_valid_time, "latest_required_first_valid_time")
            if latest > cutoff:
                raise SharedEnvelopeError("LATEST_REQUIRED_FVT_AFTER_CUTOFF")
            if not any(_utc(e.first_valid_time, "first_valid_time") == latest for e in self.evidence_entries):
                raise SharedEnvelopeError("LATEST_REQUIRED_FVT_UNBOUND")
        _strings(self.source_generations, "source_generations")
        _strings(self.missing_entries, "missing_entries")
        _strings(self.reason_codes, "reason_codes")


class OwnerExtensionRegistry:
    def __init__(self, entries: Iterable[Mapping[str, Any]]) -> None:
        self._entries: dict[tuple[str, str], frozenset[str]] = {}
        for entry in entries:
            extension_type = _text(entry.get("extension_type"), "extension_type")
            owner = _text(entry.get("owner_namespace"), "owner_namespace")
            predicates = frozenset(_strings(entry.get("allowed_predicates"), "allowed_predicates"))
            key = (extension_type, owner)
            if key in self._entries:
                raise SharedEnvelopeError("OWNER_EXTENSION_AMBIGUOUS")
            self._entries[key] = predicates

    def permits(self, extension_type: str, owner_namespace: str, predicate: str) -> bool:
        try:
            return predicate in self._entries[(extension_type, owner_namespace)]
        except KeyError as exc:
            raise SharedEnvelopeError(f"OWNER_EXTENSION_UNKNOWN:{extension_type}:{owner_namespace}") from exc


@dataclass(frozen=True)
class LineageEdgeEnvelope:
    edge_id: str
    lineage_plane: str
    predicate_owner: str
    predicate: str
    source_ref: str
    target_ref: str
    semantic_scope: str
    extension_type: str

    def validate(self, registry: OwnerExtensionRegistry) -> None:
        if self.lineage_plane not in LINEAGE_PLANES:
            raise SharedEnvelopeError("LINEAGE_PLANE_UNKNOWN")
        if self.predicate == "PARENT":
            raise SharedEnvelopeError("UNQUALIFIED_GLOBAL_PARENT_FORBIDDEN")
        for field in ("edge_id", "predicate_owner", "predicate", "source_ref", "target_ref", "semantic_scope", "extension_type"):
            _text(getattr(self, field), field)
        if self.source_ref == self.target_ref:
            raise SharedEnvelopeError("LINEAGE_SELF_EDGE_FORBIDDEN")
        if not registry.permits(self.extension_type, self.predicate_owner, self.predicate):
            raise SharedEnvelopeError("OWNER_PREDICATE_NOT_PERMITTED")


@dataclass(frozen=True)
class CompatibilityContract:
    compatibility_contract_id: str
    producer_contract_ref: str
    consumer_contract_ref: str
    compatibility_class: str
    semantic_scope: str
    constraints: tuple[str, ...]
    declared_loss_fields: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.compatibility_class not in COMPATIBILITY_CLASSES:
            raise SharedEnvelopeError("COMPATIBILITY_CLASS_UNKNOWN")
        for field in ("compatibility_contract_id", "producer_contract_ref", "consumer_contract_ref", "semantic_scope"):
            value = _text(getattr(self, field), field)
            if field.endswith("contract_ref") and "latest" in value.lower():
                raise SharedEnvelopeError("NORMATIVE_LATEST_REF_FORBIDDEN")
        _strings(self.constraints, "constraints")
        _strings(self.declared_loss_fields, "declared_loss_fields")
        if self.compatibility_class == "LOSSY_ADAPTER_ALLOWED" and not self.declared_loss_fields:
            raise SharedEnvelopeError("LOSSY_ADAPTER_LOSS_DECLARATION_REQUIRED")


@dataclass(frozen=True)
class AdapterDescriptor:
    adapter_id: str
    adapter_owner: str
    source_contract_ref: str
    target_contract_ref: str
    field_mapping: tuple[tuple[str, str], ...]
    declared_loss_fields: tuple[str, ...]
    semantic_inventions: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.semantic_inventions:
            raise SharedEnvelopeError("ADAPTER_SEMANTIC_FABRICATION_FORBIDDEN")
        for field in ("adapter_id", "adapter_owner", "source_contract_ref", "target_contract_ref"):
            value = _text(getattr(self, field), field)
            if field.endswith("contract_ref") and "latest" in value.lower():
                raise SharedEnvelopeError("NORMATIVE_LATEST_REF_FORBIDDEN")
        sources = [pair[0] for pair in self.field_mapping]
        targets = [pair[1] for pair in self.field_mapping]
        if any(len(pair) != 2 or not pair[0] or not pair[1] for pair in self.field_mapping):
            raise SharedEnvelopeError("ADAPTER_FIELD_MAPPING_INVALID")
        if len(targets) != len(set(targets)):
            raise SharedEnvelopeError("ADAPTER_TARGET_AMBIGUOUS")
        if set(sources) & set(self.declared_loss_fields):
            raise SharedEnvelopeError("ADAPTER_MAPPED_FIELD_DECLARED_LOST")

    def adapt(self, source: Mapping[str, Any]) -> dict[str, Any]:
        missing = sorted(src for src, _ in self.field_mapping if src not in source)
        if missing:
            raise SharedEnvelopeError(f"ADAPTER_SOURCE_FIELDS_MISSING:{missing}")
        undeclared_drops = sorted(set(source) - {src for src, _ in self.field_mapping} - set(self.declared_loss_fields))
        if undeclared_drops:
            raise SharedEnvelopeError(f"ADAPTER_UNDECLARED_LOSS:{undeclared_drops}")
        return {target: source[src] for src, target in self.field_mapping}


@dataclass(frozen=True)
class InterfaceBinding:
    interface_binding_id: str
    producer_owner: str
    consumer_owner: str
    producer_contract_ref: str
    consumer_contract_ref: str
    schema_refs: tuple[str, ...]
    serialization_profile_refs: tuple[str, ...]
    generation_constraints: tuple[str, ...]
    dependency_role: str
    compatibility_policy_ref: str
    adapter_ref: str | None = None
    qa_refs: tuple[str, ...] = ()
    decision_refs: tuple[str, ...] = ()
    authority_requirement: str | None = None

    def __post_init__(self) -> None:
        for field in ("interface_binding_id", "producer_owner", "consumer_owner", "producer_contract_ref", "consumer_contract_ref", "dependency_role", "compatibility_policy_ref"):
            value = _text(getattr(self, field), field)
            if field.endswith("ref") and "latest" in value.lower():
                raise SharedEnvelopeError("NORMATIVE_LATEST_REF_FORBIDDEN")
        for field in ("schema_refs", "serialization_profile_refs", "generation_constraints"):
            if not _strings(getattr(self, field), field):
                raise SharedEnvelopeError(f"{field.upper()}_REQUIRED")

    def validate(self, compatibility: CompatibilityContract, adapter: AdapterDescriptor | None = None) -> None:
        if self.compatibility_policy_ref != compatibility.compatibility_contract_id:
            raise SharedEnvelopeError("INTERFACE_COMPATIBILITY_REF_MISMATCH")
        requires_adapter = compatibility.compatibility_class in {"ADAPTER_REQUIRED", "LOSSY_ADAPTER_ALLOWED"}
        if requires_adapter != (self.adapter_ref is not None):
            raise SharedEnvelopeError("INTERFACE_ADAPTER_REQUIREMENT_MISMATCH")
        if self.adapter_ref is not None:
            if adapter is None or adapter.adapter_id != self.adapter_ref:
                raise SharedEnvelopeError("INTERFACE_ADAPTER_UNRESOLVED")
            if adapter.source_contract_ref != self.producer_contract_ref or adapter.target_contract_ref != self.consumer_contract_ref:
                raise SharedEnvelopeError("INTERFACE_ADAPTER_CONTRACT_MISMATCH")
            if tuple(sorted(adapter.declared_loss_fields)) != tuple(sorted(compatibility.declared_loss_fields)):
                raise SharedEnvelopeError("INTERFACE_ADAPTER_LOSS_MISMATCH")
