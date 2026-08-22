"""Inactive WP6 persistence, security, observability, and pilot-budget records."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
import hashlib
import json
import math
from typing import Any, Iterable, Mapping


class SharedFoundationError(ValueError):
    """A fail-closed Shared Systems WP6 contract violation."""


def _text(value: str, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise SharedFoundationError(f"{field.upper()}_REQUIRED")
    return value


def _refs(values: tuple[str, ...], field: str, *, allow_empty: bool = False) -> None:
    if not isinstance(values, tuple) or (not values and not allow_empty):
        raise SharedFoundationError(f"{field.upper()}_REQUIRED")
    if any(not isinstance(value, str) or not value for value in values):
        raise SharedFoundationError(f"{field.upper()}_INVALID")
    if len(values) != len(set(values)):
        raise SharedFoundationError(f"{field.upper()}_DUPLICATE")


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _logical_id(value: object) -> str:
    try:
        raw = json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise SharedFoundationError("NON_CANONICAL_FOUNDATION_VALUE") from exc
    return _sha256(raw)


def _timestamp(value: str, field: str) -> None:
    _text(value, field)
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise SharedFoundationError(f"{field.upper()}_INVALID") from exc
    if parsed.tzinfo is None:
        raise SharedFoundationError(f"{field.upper()}_TIMEZONE_REQUIRED")


@dataclass(frozen=True)
class DurableArtifactDescriptor:
    artifact_ref: str
    logical_identity_ref: str
    blob_sha256: str
    byte_count: int
    media_type: str
    storage_class: str
    owner_programme_id: str
    retention_class: str
    authority_effect: str = "NONE"

    def __post_init__(self) -> None:
        for field in (
            "artifact_ref",
            "logical_identity_ref",
            "media_type",
            "owner_programme_id",
        ):
            _text(getattr(self, field), field)
        if len(self.blob_sha256) != 64 or any(
            char not in "0123456789abcdef" for char in self.blob_sha256
        ):
            raise SharedFoundationError("ARTIFACT_BLOB_SHA256_INVALID")
        if not isinstance(self.byte_count, int) or self.byte_count < 0:
            raise SharedFoundationError("ARTIFACT_BYTE_COUNT_INVALID")
        if self.storage_class not in {
            "GIT_COMPACT_DURABLE",
            "EXTERNAL_CONTENT_ADDRESSED_DURABLE",
            "LOCAL_REBUILDABLE",
            "LOCAL_EPHEMERAL",
        }:
            raise SharedFoundationError("ARTIFACT_STORAGE_CLASS_UNKNOWN")
        if self.retention_class not in {
            "COURT_RECORD",
            "HISTORICAL_EVIDENCE",
            "REPRODUCIBILITY_REQUIRED",
            "BOUNDED_DURABLE",
            "TEMPORARY",
            "DISPOSABLE",
        }:
            raise SharedFoundationError("ARTIFACT_RETENTION_CLASS_UNKNOWN")
        if self.authority_effect != "NONE":
            raise SharedFoundationError("ARTIFACT_AUTHORITY_EFFECT_FORBIDDEN")


@dataclass(frozen=True)
class ExternalArtifactReceipt:
    receipt_id: str
    artifact_ref: str
    storage_provider_ref: str
    locator_ref: str
    blob_sha256: str
    byte_count: int
    verified_at: str
    status: str
    authority_effect: str = "NONE"

    def __post_init__(self) -> None:
        for field in (
            "receipt_id",
            "artifact_ref",
            "storage_provider_ref",
            "locator_ref",
        ):
            _text(getattr(self, field), field)
        if len(self.blob_sha256) != 64 or any(
            char not in "0123456789abcdef" for char in self.blob_sha256
        ):
            raise SharedFoundationError("ARTIFACT_RECEIPT_SHA256_INVALID")
        if not isinstance(self.byte_count, int) or self.byte_count < 0:
            raise SharedFoundationError("ARTIFACT_RECEIPT_BYTE_COUNT_INVALID")
        _timestamp(self.verified_at, "verified_at")
        if self.status not in {"VERIFIED", "MISSING", "HASH_MISMATCH", "QUARANTINED"}:
            raise SharedFoundationError("ARTIFACT_RECEIPT_STATUS_UNKNOWN")
        if self.authority_effect != "NONE":
            raise SharedFoundationError("ARTIFACT_RECEIPT_AUTHORITY_EFFECT_FORBIDDEN")


@dataclass(frozen=True)
class EvidenceCommitManifest:
    manifest_id: str
    expected_artifact_refs: tuple[str, ...]
    receipt_refs: tuple[str, ...]
    status: str
    missing_artifact_refs: tuple[str, ...]
    invalid_artifact_refs: tuple[str, ...]
    authority_effect: str = "NONE"

    def __post_init__(self) -> None:
        _text(self.manifest_id, "manifest_id")
        _refs(self.expected_artifact_refs, "expected_artifact_refs")
        _refs(self.receipt_refs, "receipt_refs", allow_empty=True)
        _refs(self.missing_artifact_refs, "missing_artifact_refs", allow_empty=True)
        _refs(self.invalid_artifact_refs, "invalid_artifact_refs", allow_empty=True)
        expected = (
            "INVALID"
            if self.invalid_artifact_refs
            else "INCOMPLETE"
            if self.missing_artifact_refs
            else "SEALED"
        )
        if self.status != expected:
            raise SharedFoundationError("EVIDENCE_COMMIT_STATUS_INCONSISTENT")
        if self.authority_effect != "NONE":
            raise SharedFoundationError("EVIDENCE_COMMIT_AUTHORITY_EFFECT_FORBIDDEN")


def build_evidence_commit_manifest(
    manifest_id: str,
    descriptors: Iterable[DurableArtifactDescriptor],
    receipts: Iterable[ExternalArtifactReceipt],
) -> EvidenceCommitManifest:
    descriptor_rows = tuple(descriptors)
    descriptors_by_ref = {item.artifact_ref: item for item in descriptor_rows}
    receipt_rows = tuple(receipts)
    if len(descriptors_by_ref) == 0:
        raise SharedFoundationError("EVIDENCE_COMMIT_EMPTY")
    if len(descriptors_by_ref) != len(descriptor_rows):
        raise SharedFoundationError("ARTIFACT_DESCRIPTOR_AMBIGUOUS")
    grouped: dict[str, list[ExternalArtifactReceipt]] = {}
    for receipt in receipt_rows:
        if receipt.artifact_ref not in descriptors_by_ref:
            raise SharedFoundationError("ARTIFACT_RECEIPT_UNKNOWN_ARTIFACT")
        grouped.setdefault(receipt.artifact_ref, []).append(receipt)
    if any(len(rows) != 1 for rows in grouped.values()):
        raise SharedFoundationError("ARTIFACT_RECEIPT_AMBIGUOUS")
    missing = []
    invalid = []
    used = []
    for artifact_ref, descriptor in sorted(descriptors_by_ref.items()):
        rows = grouped.get(artifact_ref, [])
        if not rows:
            missing.append(artifact_ref)
            continue
        receipt = rows[0]
        used.append(receipt.receipt_id)
        if (
            receipt.status != "VERIFIED"
            or receipt.blob_sha256 != descriptor.blob_sha256
            or receipt.byte_count != descriptor.byte_count
        ):
            invalid.append(artifact_ref)
    return EvidenceCommitManifest(
        manifest_id,
        tuple(sorted(descriptors_by_ref)),
        tuple(sorted(used)),
        "INVALID" if invalid else "INCOMPLETE" if missing else "SEALED",
        tuple(missing),
        tuple(invalid),
    )


@dataclass(frozen=True)
class ArtifactReachability:
    artifact_ref: str
    status: str
    reason_codes: tuple[str, ...]

    def __post_init__(self) -> None:
        _text(self.artifact_ref, "artifact_ref")
        if self.status not in {"PRESENT_VERIFIED", "MISSING", "HASH_MISMATCH", "PROTECTED_DENIED"}:
            raise SharedFoundationError("REACHABILITY_OBSERVATION_STATUS_UNKNOWN")
        if self.status == "PRESENT_VERIFIED" and self.reason_codes:
            raise SharedFoundationError("REACHABILITY_SUCCESS_REASON_FORBIDDEN")
        if self.status != "PRESENT_VERIFIED" and not self.reason_codes:
            raise SharedFoundationError("REACHABILITY_FAILURE_REASON_REQUIRED")
        _refs(
            self.reason_codes,
            "reason_codes",
            allow_empty=self.status == "PRESENT_VERIFIED",
        )


@dataclass(frozen=True)
class EvidenceReachabilityManifest:
    manifest_id: str
    observations: tuple[ArtifactReachability, ...]
    status: str
    authority_effect: str = "NONE"

    def __post_init__(self) -> None:
        _text(self.manifest_id, "manifest_id")
        refs = [item.artifact_ref for item in self.observations]
        if not refs or len(refs) != len(set(refs)):
            raise SharedFoundationError("REACHABILITY_OBSERVATION_AMBIGUOUS")
        expected = (
            "REACHABLE"
            if all(item.status == "PRESENT_VERIFIED" for item in self.observations)
            else "GAPPED"
        )
        if self.status != expected:
            raise SharedFoundationError("REACHABILITY_STATUS_INCONSISTENT")
        if self.authority_effect != "NONE":
            raise SharedFoundationError("REACHABILITY_AUTHORITY_EFFECT_FORBIDDEN")


def inspect_reachability(
    manifest_id: str,
    descriptors: Iterable[DurableArtifactDescriptor],
    available_bytes: Mapping[str, bytes],
) -> EvidenceReachabilityManifest:
    observations = []
    for descriptor in sorted(descriptors, key=lambda item: item.artifact_ref):
        raw = available_bytes.get(descriptor.artifact_ref)
        if raw is None:
            observations.append(
                ArtifactReachability(
                    descriptor.artifact_ref, "MISSING", ("OBJECT_MISSING",)
                )
            )
        elif len(raw) != descriptor.byte_count or _sha256(raw) != descriptor.blob_sha256:
            observations.append(
                ArtifactReachability(
                    descriptor.artifact_ref,
                    "HASH_MISMATCH",
                    ("CONTENT_IDENTITY_MISMATCH",),
                )
            )
        else:
            observations.append(
                ArtifactReachability(descriptor.artifact_ref, "PRESENT_VERIFIED", ())
            )
    status = (
        "REACHABLE"
        if observations and all(item.status == "PRESENT_VERIFIED" for item in observations)
        else "GAPPED"
    )
    return EvidenceReachabilityManifest(manifest_id, tuple(observations), status)


@dataclass(frozen=True)
class SecurityRequest:
    request_id: str
    principal_ref: str
    resource_ref: str
    capability_ref: str
    permission_ref: str
    authority_ref: str
    scope_ref: str
    runtime_policy_ref: str
    information_class: str

    def __post_init__(self) -> None:
        for field in (
            "request_id",
            "principal_ref",
            "resource_ref",
            "capability_ref",
            "permission_ref",
            "authority_ref",
            "scope_ref",
            "runtime_policy_ref",
            "information_class",
        ):
            _text(getattr(self, field), field)


SECURITY_FACTORS = (
    "capability_present",
    "resource_reachable",
    "permission_granted",
    "authority_permits",
    "scope_allows",
    "runtime_policy_allows",
)


@dataclass(frozen=True)
class SecurityDecisionRecord:
    decision_id: str
    request_id: str
    resource_ref: str
    status: str
    factor_results: tuple[tuple[str, bool], ...]
    reason_codes: tuple[str, ...]
    metadata_revealed: bool
    dsai_decision_ref: str
    authority_effect: str = "NONE"

    def __post_init__(self) -> None:
        for field in ("decision_id", "request_id", "resource_ref", "dsai_decision_ref"):
            _text(getattr(self, field), field)
        if tuple(name for name, _ in self.factor_results) != SECURITY_FACTORS:
            raise SharedFoundationError("SECURITY_FACTOR_SET_INVALID")
        expected = "ALLOW" if all(value for _, value in self.factor_results) else "DENY"
        if self.status != expected:
            raise SharedFoundationError("SECURITY_DECISION_INCONSISTENT")
        expected_reasons = tuple(name.upper() for name, value in self.factor_results if not value)
        if self.reason_codes != expected_reasons:
            raise SharedFoundationError("SECURITY_DECISION_REASONS_INCONSISTENT")
        if self.status == "DENY" and self.metadata_revealed:
            raise SharedFoundationError("PROTECTED_METADATA_LEAK_FORBIDDEN")
        if self.authority_effect != "NONE":
            raise SharedFoundationError("SECURITY_DECISION_AUTHORITY_EFFECT_FORBIDDEN")


def decide_security(
    decision_id: str,
    request: SecurityRequest,
    *,
    factor_results: Mapping[str, bool],
    dsai_decision_ref: str,
) -> SecurityDecisionRecord:
    if set(factor_results) != set(SECURITY_FACTORS):
        raise SharedFoundationError("SECURITY_FACTOR_SET_INVALID")
    rows = tuple((name, factor_results[name] is True) for name in SECURITY_FACTORS)
    denied = tuple(name.upper() for name, value in rows if not value)
    return SecurityDecisionRecord(
        decision_id,
        request.request_id,
        request.resource_ref,
        "DENY" if denied else "ALLOW",
        rows,
        denied,
        False,
        dsai_decision_ref,
    )


def reveal_protected_metadata(
    decision: SecurityDecisionRecord, metadata: Mapping[str, Any]
) -> dict[str, Any]:
    if decision.status != "ALLOW":
        raise SharedFoundationError("PROTECTED_METADATA_PRE_RESOLUTION_DENIAL")
    return dict(metadata)


@dataclass(frozen=True)
class InformationExposureRecord:
    exposure_id: str
    decision_ref: str
    principal_ref: str
    resource_ref: str
    information_class: str
    exposed_field_names: tuple[str, ...]
    validation_provenance_consumed: bool
    authority_effect: str = "NONE"

    def __post_init__(self) -> None:
        for field in (
            "exposure_id",
            "decision_ref",
            "principal_ref",
            "resource_ref",
            "information_class",
        ):
            _text(getattr(self, field), field)
        _refs(self.exposed_field_names, "exposed_field_names")
        if self.information_class == "VALIDATION" and not self.validation_provenance_consumed:
            raise SharedFoundationError("VALIDATION_EXPOSURE_PROVENANCE_REQUIRED")
        if self.authority_effect != "NONE":
            raise SharedFoundationError("EXPOSURE_AUTHORITY_EFFECT_FORBIDDEN")


@dataclass(frozen=True)
class DSAISecurityAdapterBinding:
    binding_id: str
    dsai_contract_refs: tuple[str, ...]
    factor_mapping: tuple[tuple[str, str], ...]
    credential_store_created: bool = False
    permission_store_created: bool = False
    authority_store_created: bool = False
    authority_effect: str = "NONE"

    def __post_init__(self) -> None:
        _text(self.binding_id, "binding_id")
        _refs(self.dsai_contract_refs, "dsai_contract_refs")
        if tuple(name for name, _ in self.factor_mapping) != SECURITY_FACTORS:
            raise SharedFoundationError("DSAI_SECURITY_FACTOR_MAPPING_INVALID")
        if any(
            (
                self.credential_store_created,
                self.permission_store_created,
                self.authority_store_created,
            )
        ):
            raise SharedFoundationError("PARALLEL_SECURITY_STORE_FORBIDDEN")
        if self.authority_effect != "NONE":
            raise SharedFoundationError("SECURITY_ADAPTER_AUTHORITY_EFFECT_FORBIDDEN")


HEALTH_DIMENSIONS = frozenset(
    {
        "AVAILABILITY",
        "CORRECTNESS",
        "FRESHNESS",
        "DEPENDENCY",
        "CAPACITY",
        "PERFORMANCE",
        "PERSISTENCE",
        "SECURITY",
        "QUALIFICATION",
        "QUEUE",
    }
)


@dataclass(frozen=True)
class TelemetryRecord:
    telemetry_id: str
    telemetry_class: str
    service_id: str
    release_id: str
    operation: str
    environment_ref: str
    observed_at: str
    information_class: str
    value: int | float | str | bool
    run_ref: str | None = None
    monotonic_elapsed_ms: int | None = None
    authority_effect: str = "NONE"

    def __post_init__(self) -> None:
        for field in (
            "telemetry_id",
            "service_id",
            "release_id",
            "operation",
            "environment_ref",
            "information_class",
        ):
            _text(getattr(self, field), field)
        if self.telemetry_class not in {"METRIC", "EVENT", "TRACE", "LOG", "QUEUE_OBSERVATION"}:
            raise SharedFoundationError("TELEMETRY_CLASS_UNKNOWN")
        _timestamp(self.observed_at, "observed_at")
        if self.monotonic_elapsed_ms is not None and self.monotonic_elapsed_ms < 0:
            raise SharedFoundationError("MONOTONIC_ELAPSED_INVALID")
        if self.authority_effect != "NONE":
            raise SharedFoundationError("TELEMETRY_AUTHORITY_EFFECT_FORBIDDEN")


@dataclass(frozen=True)
class HealthAssertion:
    dimension: str
    status: str
    evidence_refs: tuple[str, ...]
    reason_codes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.dimension not in HEALTH_DIMENSIONS:
            raise SharedFoundationError("HEALTH_DIMENSION_UNKNOWN")
        if self.status not in {"HEALTHY", "DEGRADED", "UNHEALTHY", "NOT_EVALUABLE", "UNKNOWN"}:
            raise SharedFoundationError("HEALTH_STATUS_UNKNOWN")
        _refs(self.evidence_refs, "evidence_refs", allow_empty=self.status in {"NOT_EVALUABLE", "UNKNOWN"})
        if self.status != "HEALTHY" and not self.reason_codes:
            raise SharedFoundationError("HEALTH_REASON_REQUIRED")
        _refs(self.reason_codes, "reason_codes", allow_empty=self.status == "HEALTHY")


@dataclass(frozen=True)
class ServiceHealthSnapshot:
    snapshot_id: str
    service_id: str
    release_id: str
    environment_ref: str
    assertions: tuple[HealthAssertion, ...]
    observed_at: str
    authority_effect: str = "NONE"

    def __post_init__(self) -> None:
        for field in ("snapshot_id", "service_id", "release_id", "environment_ref"):
            _text(getattr(self, field), field)
        dimensions = [item.dimension for item in self.assertions]
        if not dimensions or len(dimensions) != len(set(dimensions)):
            raise SharedFoundationError("HEALTH_DIMENSION_AMBIGUOUS")
        _timestamp(self.observed_at, "observed_at")
        if self.authority_effect != "NONE":
            raise SharedFoundationError("HEALTH_AUTHORITY_EFFECT_FORBIDDEN")


@dataclass(frozen=True)
class ServiceLevelObjective:
    slo_id: str
    service_id: str
    release_id: str
    operation: str
    environment_ref: str
    indicator_ref: str
    window_ref: str
    comparison: str
    target_value: float | None
    status: str
    derivation_ref: str | None
    authority_effect: str = "NONE"

    def __post_init__(self) -> None:
        for field in (
            "slo_id",
            "service_id",
            "release_id",
            "operation",
            "environment_ref",
            "indicator_ref",
            "window_ref",
            "comparison",
        ):
            _text(getattr(self, field), field)
        if self.status not in {"BOUND", "UNBOUND"}:
            raise SharedFoundationError("SLO_STATUS_UNKNOWN")
        if self.comparison not in {"LT", "LTE", "GT", "GTE", "EQ"}:
            raise SharedFoundationError("SLO_COMPARISON_UNKNOWN")
        if self.status == "BOUND" and (
            self.target_value is None or not self.derivation_ref
        ):
            raise SharedFoundationError("BOUND_SLO_DERIVATION_REQUIRED")
        if self.status == "UNBOUND" and self.target_value is not None:
            raise SharedFoundationError("UNBOUND_SLO_TARGET_FORBIDDEN")
        if self.authority_effect != "NONE":
            raise SharedFoundationError("SLO_AUTHORITY_EFFECT_FORBIDDEN")


@dataclass(frozen=True)
class PilotBaselineMeasurement:
    measurement_id: str
    dimension: str
    unit: str
    environment_ref: str
    procedure_ref: str
    sample_values: tuple[float, ...]
    evidence_refs: tuple[str, ...]
    authority_effect: str = "NONE"

    def __post_init__(self) -> None:
        for field in ("measurement_id", "dimension", "unit", "environment_ref", "procedure_ref"):
            _text(getattr(self, field), field)
        if not self.sample_values or any(
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
            or value < 0
            for value in self.sample_values
        ):
            raise SharedFoundationError("PILOT_BASELINE_SAMPLES_INVALID")
        expected_unit = PILOT_NUMERIC_CAP_DIMENSIONS.get(self.dimension)
        if expected_unit is None or self.unit != expected_unit:
            raise SharedFoundationError("PILOT_BASELINE_DIMENSION_OR_UNIT_INVALID")
        _refs(self.evidence_refs, "evidence_refs")
        if self.authority_effect != "NONE":
            raise SharedFoundationError("PILOT_BASELINE_AUTHORITY_EFFECT_FORBIDDEN")


PILOT_HARD_FLOOR_DIMENSIONS = frozenset(
    {
        "REFERENCE_OPTIMIZED_SEMANTIC_MISMATCHES",
        "AUTHORITY_SECURITY_FALSE_ALLOWS",
        "UNEXPLAINED_MANDATORY_DUAL_RUN_DIVERGENCES",
        "HISTORICAL_ID_HASH_REWRITES",
        "UNRESOLVED_SERVICE_OWNER_CONFLICTS",
        "MANDATORY_EVIDENCE_REACHABILITY_GAPS",
        "CAPACITY_DRIVEN_SEMANTIC_WEAKENING",
        "ADAPTER_SEMANTIC_FABRICATION",
        "BOOTSTRAP_CYCLES_OR_FORBIDDEN_BACK_EDGES",
    }
)


PILOT_NUMERIC_CAP_DIMENSIONS = {
    "RESOLVER_P50_LATENCY_US": "us",
    "RESOLVER_P95_LATENCY_US": "us",
    "CANONICALIZATION_P50_LATENCY_US": "us",
    "CANONICALIZATION_P95_LATENCY_US": "us",
    "PEAK_MEMORY_DELTA_BYTES": "bytes",
    "ARTIFACT_BYTE_DELTA_BYTES": "bytes",
    "CHECKPOINT_RESTART_OVERHEAD_US": "us",
    "EVIDENCE_REACHABILITY_LATENCY_US": "us",
    "CI_QUEUE_TIME_SECONDS": "seconds",
    "WASTED_ASSURANCE_TIME_SECONDS": "seconds",
    "OPERATOR_TIME_SECONDS": "seconds",
    "MAINTENANCE_TIME_SECONDS": "seconds",
    "ACTIVE_ADAPTER_COUNT": "count",
    "ADAPTER_CODE_SURFACE_LINES": "lines",
    "ADAPTER_MAPPING_COUNT": "count",
    "ADAPTER_INCIDENT_CONTRIBUTION_COUNT": "count",
    "DEPENDENCY_FAN_OUT_COUNT": "count",
    "INVALIDATION_VOLUME_COUNT": "count",
}


@dataclass(frozen=True)
class PilotAcceptanceBudget:
    budget_id: str
    baseline_measurement_refs: tuple[str, ...]
    numeric_caps: tuple[tuple[str, float, str], ...]
    zero_tolerance_floor: tuple[tuple[str, int], ...]
    derivation_procedure_ref: str
    frozen: bool
    relaxable_within_pilot: bool = False
    authority_effect: str = "NONE"

    @classmethod
    def freeze_from_baselines(
        cls,
        budget_id: str,
        baselines: Iterable[PilotBaselineMeasurement],
        *,
        derivation_procedure_ref: str,
    ) -> "PilotAcceptanceBudget":
        """Freeze no-slack caps from the exact maximum of every pinned baseline."""
        rows = tuple(baselines)
        by_dimension = {item.dimension: item for item in rows}
        if len(by_dimension) != len(rows):
            raise SharedFoundationError("PILOT_BASELINE_DIMENSION_AMBIGUOUS")
        if set(by_dimension) != set(PILOT_NUMERIC_CAP_DIMENSIONS):
            raise SharedFoundationError("PILOT_BASELINE_DIMENSION_SET_INCOMPLETE")
        caps = tuple(
            (
                dimension,
                max(by_dimension[dimension].sample_values),
                PILOT_NUMERIC_CAP_DIMENSIONS[dimension],
            )
            for dimension in sorted(PILOT_NUMERIC_CAP_DIMENSIONS)
        )
        return cls(
            budget_id,
            tuple(by_dimension[dimension].measurement_id for dimension in sorted(by_dimension)),
            caps,
            tuple((dimension, 0) for dimension in sorted(PILOT_HARD_FLOOR_DIMENSIONS)),
            derivation_procedure_ref,
            True,
        )

    def __post_init__(self) -> None:
        _text(self.budget_id, "budget_id")
        _text(self.derivation_procedure_ref, "derivation_procedure_ref")
        _refs(self.baseline_measurement_refs, "baseline_measurement_refs")
        if not self.numeric_caps:
            raise SharedFoundationError("PILOT_NUMERIC_CAPS_REQUIRED")
        if any(
            isinstance(cap, bool)
            or not isinstance(cap, (int, float))
            or not math.isfinite(cap)
            or cap < 0
            or not dimension
            or not unit
            for dimension, cap, unit in self.numeric_caps
        ):
            raise SharedFoundationError("PILOT_NUMERIC_CAP_INVALID")
        if len({dimension for dimension, _, _ in self.numeric_caps}) != len(self.numeric_caps):
            raise SharedFoundationError("PILOT_NUMERIC_CAP_DUPLICATE")
        cap_units = {dimension: unit for dimension, _, unit in self.numeric_caps}
        if cap_units != PILOT_NUMERIC_CAP_DIMENSIONS:
            raise SharedFoundationError("PILOT_NUMERIC_CAP_DIMENSION_SET_INCOMPLETE")
        if len(self.baseline_measurement_refs) != len(PILOT_NUMERIC_CAP_DIMENSIONS):
            raise SharedFoundationError("PILOT_BASELINE_REFERENCE_SET_INCOMPLETE")
        floor_dimensions = {dimension for dimension, _ in self.zero_tolerance_floor}
        if (
            floor_dimensions != PILOT_HARD_FLOOR_DIMENSIONS
            or len(floor_dimensions) != len(self.zero_tolerance_floor)
            or any(value != 0 for _, value in self.zero_tolerance_floor)
        ):
            raise SharedFoundationError("PILOT_HARD_FLOOR_MUST_BE_ZERO")
        if not self.frozen or self.relaxable_within_pilot:
            raise SharedFoundationError("PILOT_BUDGET_FREEZE_REQUIRED")
        if self.authority_effect != "NONE":
            raise SharedFoundationError("PILOT_BUDGET_AUTHORITY_EFFECT_FORBIDDEN")

    @property
    def logical_id(self) -> str:
        return _logical_id(asdict(self))
