"""SHSI-WP8 read-only Research Operations/DMRP shadow consumer.

The module consumes only owner-governed repository records.  It transports exact
identities and typed missing states; it cannot add a provider, source, research
role, artifact store, or authority.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Any, Iterable, Mapping

from .envelopes import (
    EvidenceEntry,
    EvidenceFrontier,
    StateVector,
    research_operations_legacy_state,
)
from .foundation import (
    DurableArtifactDescriptor,
    EvidenceReachabilityManifest,
    inspect_reachability,
)


class RODMRPShadowError(ValueError):
    """A fail-closed Research Operations/DMRP shadow contract violation."""


def _text(value: str, field: str) -> str:
    if not isinstance(value, str) or not value or "latest" in value.casefold():
        raise RODMRPShadowError(f"{field.upper()}_EXACT_REF_REQUIRED")
    return value


def _refs(values: tuple[str, ...], field: str) -> None:
    if not values or any(not isinstance(value, str) or not value for value in values):
        raise RODMRPShadowError(f"{field.upper()}_REQUIRED")
    if len(values) != len(set(values)):
        raise RODMRPShadowError(f"{field.upper()}_DUPLICATE")


def _canonical(value: object) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise RODMRPShadowError("NON_CANONICAL_RO_DMRP_VALUE") from exc


def _logical_id(value: object) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


@dataclass(frozen=True)
class RODMRPSharedSystemsConsumptionManifest:
    manifest_id: str
    consumer_programme_id: str
    consumer_generation: str
    shared_release_id: str
    current_state_ref: str
    current_state_blob_sha: str
    owner_provider_refs: tuple[str, ...]
    owner_source_refs: tuple[str, ...]
    owner_research_roles: tuple[str, ...]
    consumed_provider_refs: tuple[str, ...]
    consumed_source_refs: tuple[str, ...]
    consumed_research_roles: tuple[str, ...]
    access_mode: str = "READ_ONLY"
    status: str = "SHADOW_ONLY"
    current_binding_changed: bool = False
    writes_performed: tuple[str, ...] = ()
    artifact_store_created: bool = False
    authority_effect: str = "NONE"

    def __post_init__(self) -> None:
        for field in (
            "manifest_id",
            "consumer_programme_id",
            "consumer_generation",
            "shared_release_id",
            "current_state_ref",
        ):
            _text(getattr(self, field), field)
        if self.consumer_programme_id != "OVC-EC1-DMRP-CONFORMANCE-v0.1":
            raise RODMRPShadowError("NON_DMRP_CONSUMER_FORBIDDEN")
        if len(self.current_state_blob_sha) != 40:
            raise RODMRPShadowError("DMRP_CURRENT_STATE_BLOB_INVALID")
        for field in (
            "owner_provider_refs",
            "owner_source_refs",
            "owner_research_roles",
            "consumed_provider_refs",
            "consumed_source_refs",
            "consumed_research_roles",
        ):
            _refs(getattr(self, field), field)
        for consumed_field, owner_field, code in (
            ("consumed_provider_refs", "owner_provider_refs", "PROVIDER"),
            ("consumed_source_refs", "owner_source_refs", "SOURCE"),
            ("consumed_research_roles", "owner_research_roles", "RESEARCH_ROLE"),
        ):
            additions = set(getattr(self, consumed_field)) - set(getattr(self, owner_field))
            if additions:
                raise RODMRPShadowError(f"UNOWNED_{code}_ADDITION_FORBIDDEN")
        if (
            self.access_mode != "READ_ONLY"
            or self.status != "SHADOW_ONLY"
            or self.current_binding_changed
            or self.writes_performed
            or self.artifact_store_created
        ):
            raise RODMRPShadowError("RO_DMRP_WRITE_ACTIVATION_OR_STORE_FORBIDDEN")
        if self.authority_effect != "NONE":
            raise RODMRPShadowError("RO_DMRP_CONSUMPTION_AUTHORITY_EFFECT_FORBIDDEN")


@dataclass(frozen=True)
class RODMRPStatePlaneCrosswalk:
    crosswalk_id: str
    owner_lifecycle_state: str
    shared_lifecycle_state: str
    shared_authority_state: str
    authority_decision_ref: str | None
    authority_effect: str = "NONE"

    def __post_init__(self) -> None:
        _text(self.crosswalk_id, "crosswalk_id")
        if self.owner_lifecycle_state != self.shared_lifecycle_state:
            raise RODMRPShadowError("RO_LIFECYCLE_REWRITE_FORBIDDEN")
        if self.owner_lifecycle_state == "FROZEN" and self.shared_authority_state != "UNKNOWN":
            raise RODMRPShadowError("FROZEN_AS_AUTHORITY_FORBIDDEN")
        if self.shared_authority_state == "FROZEN":
            raise RODMRPShadowError("FROZEN_AS_AUTHORITY_FORBIDDEN")
        if self.shared_authority_state != "UNKNOWN" and not self.authority_decision_ref:
            raise RODMRPShadowError("AUTHORITY_DECISION_REF_REQUIRED")
        if self.authority_effect != "NONE":
            raise RODMRPShadowError("RO_STATE_CROSSWALK_AUTHORITY_EFFECT_FORBIDDEN")


def crosswalk_ro_state(
    crosswalk_id: str,
    *,
    lifecycle_state: str,
    authority_state: str = "UNKNOWN",
    authority_decision_ref: str | None = None,
) -> tuple[RODMRPStatePlaneCrosswalk, StateVector]:
    if lifecycle_state == "FROZEN":
        authority_state = "UNKNOWN"
    vector = research_operations_legacy_state(
        lifecycle_state=lifecycle_state,
        authority_state=authority_state,
        authority_decision_ref=authority_decision_ref,
    )
    crosswalk = RODMRPStatePlaneCrosswalk(
        crosswalk_id,
        lifecycle_state,
        vector.value("LIFECYCLE", "RESEARCH_OPERATIONS").owner_state,
        vector.authority("RESEARCH_OPERATIONS"),
        authority_decision_ref,
    )
    return crosswalk, vector


REQUIRED_RECORD_TYPES = (
    "DMRP_STUDY",
    "EVIDENCE_CYCLE_GENERATION",
    "RESEARCH_QUESTION_RECORD",
)


@dataclass(frozen=True)
class RODMRPEvidenceEvaluation:
    evaluation_id: str
    frontier: EvidenceFrontier
    record_identity_refs: tuple[tuple[str, str], ...]
    status: str
    reason_codes: tuple[str, ...]
    authority_effect: str = "NONE"

    def __post_init__(self) -> None:
        expected = "READY" if not self.frontier.missing_entries else "NOT_EVALUABLE"
        if self.status != expected:
            raise RODMRPShadowError("RO_EVIDENCE_EVALUATION_STATUS_INCONSISTENT")
        if expected == "NOT_EVALUABLE" and "REQUIRED_RECORD_MISSING" not in self.reason_codes:
            raise RODMRPShadowError("RO_EVIDENCE_MISSING_REASON_REQUIRED")
        if self.authority_effect != "NONE":
            raise RODMRPShadowError("RO_EVIDENCE_AUTHORITY_EFFECT_FORBIDDEN")


def build_ro_evidence_frontier(
    evaluation_id: str,
    fixture: Mapping[str, Any],
    *,
    source_generation: str,
    evaluation_cutoff: str,
    dependency_manifest_ref: str,
) -> RODMRPEvidenceEvaluation:
    if fixture.get("status") != "SYNTHETIC_NON_AUTHORITATIVE":
        raise RODMRPShadowError("NON_SYNTHETIC_FIXTURE_FORBIDDEN")
    if fixture.get("market_authority") != "NONE" or fixture.get("real_source_authority") != "NONE":
        raise RODMRPShadowError("FIXTURE_AUTHORITY_FORBIDDEN")
    rows = fixture.get("fixtures")
    if not isinstance(rows, list):
        raise RODMRPShadowError("FIXTURE_ROWS_REQUIRED")
    by_type: dict[str, Mapping[str, Any]] = {}
    for row in rows:
        if not isinstance(row, Mapping) or not isinstance(row.get("record_type"), str):
            raise RODMRPShadowError("FIXTURE_RECORD_INVALID")
        if row["record_type"] in by_type:
            raise RODMRPShadowError("FIXTURE_RECORD_TYPE_AMBIGUOUS")
        by_type[row["record_type"]] = row
    missing = tuple(record_type for record_type in REQUIRED_RECORD_TYPES if record_type not in by_type)
    identities = tuple(
        (record_type, _logical_id(by_type[record_type]))
        for record_type in REQUIRED_RECORD_TYPES
        if record_type in by_type
    )
    entries = tuple(
        EvidenceEntry(identity, record_type, evaluation_cutoff, source_generation)
        for record_type, identity in identities
    )
    reasons = ("REQUIRED_RECORD_MISSING",) if missing else ()
    frontier = EvidenceFrontier(
        f"{evaluation_id}.FRONTIER",
        "ovc-shsi-ro-dmrp-evidence-frontier/v0.1",
        "RESEARCH_OPERATIONS",
        evaluation_cutoff,
        dependency_manifest_ref,
        entries,
        missing,
        evaluation_cutoff if entries else None,
        (source_generation,),
        reasons,
    )
    return RODMRPEvidenceEvaluation(
        evaluation_id,
        frontier,
        identities,
        "NOT_EVALUABLE" if missing else "READY",
        reasons,
    )


@dataclass(frozen=True)
class RODMRPReadOnlyArtifactBinding:
    binding_id: str
    repository_path: str
    descriptor: DurableArtifactDescriptor
    external_artifact_fetch_performed: bool = False
    writes_performed: tuple[str, ...] = ()
    artifact_store_created: bool = False
    authority_effect: str = "NONE"

    def __post_init__(self) -> None:
        _text(self.binding_id, "binding_id")
        _text(self.repository_path, "repository_path")
        if self.descriptor.storage_class != "GIT_COMPACT_DURABLE":
            raise RODMRPShadowError("RO_ARTIFACT_REPOSITORY_STORAGE_REQUIRED")
        if self.external_artifact_fetch_performed or self.writes_performed or self.artifact_store_created:
            raise RODMRPShadowError("RO_ARTIFACT_FETCH_WRITE_OR_STORE_FORBIDDEN")
        if self.authority_effect != "NONE":
            raise RODMRPShadowError("RO_ARTIFACT_BINDING_AUTHORITY_EFFECT_FORBIDDEN")


def build_read_only_artifact_binding(
    binding_id: str,
    repository_path: str,
    raw: bytes,
    *,
    owner_programme_id: str = "OVC-EC1-DMRP-CONFORMANCE-v0.1",
) -> RODMRPReadOnlyArtifactBinding:
    digest = hashlib.sha256(raw).hexdigest()
    descriptor = DurableArtifactDescriptor(
        f"repo:{repository_path}",
        f"sha256:{digest}",
        digest,
        len(raw),
        "application/json",
        "GIT_COMPACT_DURABLE",
        owner_programme_id,
        "HISTORICAL_EVIDENCE",
    )
    return RODMRPReadOnlyArtifactBinding(binding_id, repository_path, descriptor)


def inspect_read_only_artifacts(
    manifest_id: str,
    bindings: Iterable[RODMRPReadOnlyArtifactBinding],
    available_bytes: Mapping[str, bytes],
) -> EvidenceReachabilityManifest:
    rows = tuple(bindings)
    if len({row.binding_id for row in rows}) != len(rows):
        raise RODMRPShadowError("RO_ARTIFACT_BINDING_AMBIGUOUS")
    return inspect_reachability(
        manifest_id,
        (row.descriptor for row in rows),
        available_bytes,
    )


@dataclass(frozen=True)
class RODMRPShadowAdapterBinding:
    binding_id: str
    source_schema: str
    target_contract_ref: str
    field_mapping: tuple[tuple[str, str], ...] = (("$", "source_record"),)
    semantic_inventions: tuple[str, ...] = ()
    active: bool = False
    status: str = "SHADOW_ONLY"
    authority_effect: str = "NONE"

    def __post_init__(self) -> None:
        for field in ("binding_id", "source_schema", "target_contract_ref"):
            _text(getattr(self, field), field)
        if self.field_mapping != (("$", "source_record"),):
            raise RODMRPShadowError("RO_ADAPTER_NON_IDENTITY_MAPPING_FORBIDDEN")
        if self.semantic_inventions:
            raise RODMRPShadowError("RO_ADAPTER_SEMANTIC_FABRICATION")
        if self.active or self.status != "SHADOW_ONLY":
            raise RODMRPShadowError("RO_ADAPTER_ACTIVATION_FORBIDDEN")
        if self.authority_effect != "NONE":
            raise RODMRPShadowError("RO_ADAPTER_AUTHORITY_EFFECT_FORBIDDEN")


def adapt_ro_record(
    binding: RODMRPShadowAdapterBinding, source_record: Mapping[str, Any]
) -> dict[str, Any]:
    if source_record.get("schema") != binding.source_schema:
        raise RODMRPShadowError("RO_ADAPTER_SOURCE_SCHEMA_MISMATCH")
    source = dict(source_record)
    payload = {
        "binding_id": binding.binding_id,
        "source_record": source,
        "source_logical_sha256": _logical_id(source),
        "status": "SHADOW_ONLY",
        "writes_performed": [],
        "authority_effect": "NONE",
    }
    return {"schema": "ovc-shsi-ro-dmrp-shadow/v0.1", **payload, "logical_id": _logical_id(payload)}


def unwrap_ro_record(
    binding: RODMRPShadowAdapterBinding, wrapped: Mapping[str, Any]
) -> dict[str, Any]:
    if wrapped.get("binding_id") != binding.binding_id or wrapped.get("status") != "SHADOW_ONLY":
        raise RODMRPShadowError("RO_SHADOW_WRAPPER_BINDING_MISMATCH")
    source = wrapped.get("source_record")
    if not isinstance(source, Mapping) or _logical_id(source) != wrapped.get("source_logical_sha256"):
        raise RODMRPShadowError("RO_SHADOW_SOURCE_IDENTITY_MISMATCH")
    return dict(source)


@dataclass(frozen=True)
class RODMRPDualRunComparison:
    comparison_id: str
    reference_logical_sha256: str
    shadow_logical_sha256: str
    status: str
    divergent: bool
    authority_effect: str = "NONE"

    def __post_init__(self) -> None:
        expected = "PASS" if not self.divergent else "BLOCK"
        if self.status != expected:
            raise RODMRPShadowError("RO_DUAL_RUN_STATUS_INCONSISTENT")
        if self.authority_effect != "NONE":
            raise RODMRPShadowError("RO_DUAL_RUN_AUTHORITY_EFFECT_FORBIDDEN")


def compare_ro_dual_run(
    comparison_id: str,
    reference: Mapping[str, Any],
    shadow: Mapping[str, Any],
) -> RODMRPDualRunComparison:
    reference_id = _logical_id(reference)
    shadow_id = _logical_id(shadow)
    divergent = reference_id != shadow_id
    return RODMRPDualRunComparison(
        comparison_id,
        reference_id,
        shadow_id,
        "BLOCK" if divergent else "PASS",
        divergent,
    )


@dataclass(frozen=True)
class RODMRPAdapterComplexityLedger:
    ledger_id: str
    binding_ref: str
    active_adapter_count: int
    adapter_code_surface_lines: int
    adapter_mapping_count: int
    artifact_byte_delta: int
    maintenance_time_seconds: int
    adapter_incident_contribution_count: int
    status: str
    exceeded_dimensions: tuple[str, ...]
    authority_effect: str = "NONE"

    def __post_init__(self) -> None:
        if self.status != ("PASS" if not self.exceeded_dimensions else "BLOCK"):
            raise RODMRPShadowError("RO_ADAPTER_BUDGET_STATUS_INCONSISTENT")
        if self.authority_effect != "NONE":
            raise RODMRPShadowError("RO_ADAPTER_LEDGER_AUTHORITY_EFFECT_FORBIDDEN")


def evaluate_ro_adapter_complexity(
    ledger_id: str,
    binding: RODMRPShadowAdapterBinding,
    *,
    budget: Mapping[str, Any],
    code_surface_lines: int,
    artifact_byte_delta: int,
    maintenance_time_seconds: int = 0,
    incident_contribution_count: int = 0,
) -> RODMRPAdapterComplexityLedger:
    caps = {row[0]: float(row[1]) for row in budget.get("numeric_caps", ())}
    observed = {
        "ACTIVE_ADAPTER_COUNT": int(binding.active),
        "ADAPTER_CODE_SURFACE_LINES": code_surface_lines,
        "ADAPTER_MAPPING_COUNT": len(binding.field_mapping),
        "ARTIFACT_BYTE_DELTA_BYTES": artifact_byte_delta,
        "MAINTENANCE_TIME_SECONDS": maintenance_time_seconds,
        "ADAPTER_INCIDENT_CONTRIBUTION_COUNT": incident_contribution_count,
    }
    missing = sorted(set(observed) - set(caps))
    if missing:
        raise RODMRPShadowError(f"PILOT_BUDGET_CAP_MISSING:{','.join(missing)}")
    exceeded = tuple(sorted(key for key, value in observed.items() if value > caps[key]))
    return RODMRPAdapterComplexityLedger(
        ledger_id,
        binding.binding_id,
        observed["ACTIVE_ADAPTER_COUNT"],
        code_surface_lines,
        observed["ADAPTER_MAPPING_COUNT"],
        artifact_byte_delta,
        maintenance_time_seconds,
        incident_contribution_count,
        "BLOCK" if exceeded else "PASS",
        exceeded,
    )
