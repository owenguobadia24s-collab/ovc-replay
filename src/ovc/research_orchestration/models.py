from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from .serialization import logical_sha256, stable_id

POPULATION_MODES = frozenset({"SYNTHETIC_FIXTURE", "SYNTHETIC_GENERATED", "SEALED_REAL_REPLAY", "TIME_GATED_REPLAY", "LIVE_PROSPECTIVE"})
CAPACITY_TIERS = frozenset({"MICRO", "SMALL", "MEDIUM", "LARGE", "LONG_HORIZON"})
DEPENDENCY_DISPOSITIONS = frozenset({"REQUIRED", "OPTIONAL", "FORBIDDEN"})
DETERMINISM_MODES = frozenset({"EXACT", "TOLERANCE_DECLARED", "NONDETERMINISTIC_FORBIDDEN"})
CHECKPOINT_CAPABILITIES = frozenset({"NONE", "STAGE", "OPAQUE_SUBSTAGE"})
EXECUTION_STATUSES = frozenset({"READY", "RUNNING", "REUSED", "COMPLETE", "CAPACITY_EXCEEDED", "FAILED", "QUARANTINED", "DEFERRED_BY_OPERATOR", "NOT_AUTHORISED"})
ARTIFACT_STATES = frozenset({"STAGING", "COMPLETE", "QUARANTINED", "SUPERSEDED"})
AUTHORITY_DECISIONS = frozenset({"ALLOW", "NOT_AUTHORISED", "DEFERRED_BY_OPERATOR"})
FAILURE_CLASSES = frozenset({"EXECUTION", "AUTHORITY", "DEPENDENCY"})


def _required(name: str, value: str) -> str:
    result = str(value).strip()
    if not result:
        raise ValueError(f"{name} required")
    return result


def _unique(values: tuple[str, ...], name: str) -> tuple[str, ...]:
    normalized = tuple(str(item).strip() for item in values)
    if any(not item for item in normalized) or len(normalized) != len(set(normalized)):
        raise ValueError(f"{name} must contain unique non-empty values")
    return normalized


@dataclass(frozen=True)
class PopulationSpec:
    population_id: str
    population_mode: str
    population_schema_version: str
    instrument: str
    price_side: str
    clock_lattice: str
    role: str
    source_adapter_id: str
    validation_access_state: str
    capacity_tier: str
    source_release_id: str | None = None
    source_manifest_hash: str | None = None
    start_time: str | None = None
    end_time: str | None = None
    admissible_cutoff: str | None = None
    expected_source_count: int | None = None
    synthetic_fixture_id: str | None = None
    generator_spec_id: str | None = None
    authority_binding_ids: tuple[str, ...] = ()
    external_artifact_root_alias: str | None = None

    def __post_init__(self) -> None:
        for name in ("population_id", "population_schema_version", "instrument", "price_side", "clock_lattice", "role", "source_adapter_id", "validation_access_state"):
            _required(name, getattr(self, name))
        if self.population_mode not in POPULATION_MODES:
            raise ValueError(f"invalid population_mode: {self.population_mode}")
        if self.capacity_tier not in CAPACITY_TIERS:
            raise ValueError(f"invalid capacity_tier: {self.capacity_tier}")
        _unique(self.authority_binding_ids, "authority_binding_ids")
        if self.expected_source_count is not None and self.expected_source_count < 0:
            raise ValueError("expected_source_count cannot be negative")
        if self.population_mode == "SYNTHETIC_FIXTURE" and not self.synthetic_fixture_id:
            raise ValueError("SYNTHETIC_FIXTURE requires synthetic_fixture_id")
        if self.population_mode == "SYNTHETIC_GENERATED" and not self.generator_spec_id:
            raise ValueError("SYNTHETIC_GENERATED requires generator_spec_id")
        if self.population_mode in {"SEALED_REAL_REPLAY", "TIME_GATED_REPLAY"} and (not self.source_release_id or not self.source_manifest_hash):
            raise ValueError("real replay modes require source_release_id and source_manifest_hash")

    def semantic_dict(self) -> dict[str, Any]:
        return {
            "population_id": self.population_id,
            "population_mode": self.population_mode,
            "population_schema_version": self.population_schema_version,
            "source_release_id": self.source_release_id,
            "source_manifest_hash": self.source_manifest_hash,
            "instrument": self.instrument,
            "price_side": self.price_side,
            "clock_lattice": self.clock_lattice,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "admissible_cutoff": self.admissible_cutoff,
            "role": self.role,
            "expected_source_count": self.expected_source_count,
            "source_adapter_id": self.source_adapter_id,
            "synthetic_fixture_id": self.synthetic_fixture_id,
            "generator_spec_id": self.generator_spec_id,
            "authority_binding_ids": list(self.authority_binding_ids),
            "validation_access_state": self.validation_access_state,
            "capacity_tier": self.capacity_tier,
        }

    @property
    def logical_hash(self) -> str:
        return logical_sha256(self.semantic_dict())

    def to_dict(self) -> dict[str, Any]:
        return {**self.semantic_dict(), "external_artifact_root_alias": self.external_artifact_root_alias, "logical_hash": self.logical_hash}


@dataclass(frozen=True)
class PipelineProfile:
    profile_id: str
    profile_version: str
    included_stage_ids: tuple[str, ...]
    required_terminal_outputs: tuple[str, ...] = ()
    allowed_optional_branches: tuple[str, ...] = ()
    prerequisites: tuple[str, ...] = ()
    authority_policy_ref: str = "IROF_EXISTING_AUTHORITY_ONLY"
    observability_requirements: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _required("profile_id", self.profile_id); _required("profile_version", self.profile_version)
        _unique(self.included_stage_ids, "included_stage_ids")
        _unique(self.required_terminal_outputs, "required_terminal_outputs")
        _unique(self.allowed_optional_branches, "allowed_optional_branches")
        if not self.included_stage_ids:
            raise ValueError("profile requires at least one stage")

    def semantic_dict(self) -> dict[str, Any]:
        return {"profile_id": self.profile_id, "profile_version": self.profile_version, "included_stage_ids": list(self.included_stage_ids), "required_terminal_outputs": list(self.required_terminal_outputs), "allowed_optional_branches": list(self.allowed_optional_branches), "prerequisites": list(self.prerequisites), "authority_policy_ref": self.authority_policy_ref, "observability_requirements": list(self.observability_requirements)}

    @property
    def logical_hash(self) -> str:
        return logical_sha256(self.semantic_dict())

    def to_dict(self) -> dict[str, Any]:
        return {**self.semantic_dict(), "logical_hash": self.logical_hash}


@dataclass(frozen=True)
class StageDependency:
    stage_id: str
    disposition: str
    expected_output_types: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _required("stage_id", self.stage_id)
        if self.disposition not in DEPENDENCY_DISPOSITIONS:
            raise ValueError(f"invalid dependency disposition: {self.disposition}")
        _unique(self.expected_output_types, "expected_output_types")

    def to_dict(self) -> dict[str, Any]:
        return {"stage_id": self.stage_id, "disposition": self.disposition, "expected_output_types": list(self.expected_output_types)}


@dataclass(frozen=True)
class StageSpec:
    stage_id: str
    stage_version: str
    stage_kind: str
    implementation_identity: str
    contract_identity: str
    schema_identity: str
    input_types: tuple[str, ...]
    output_types: tuple[str, ...]
    dependencies: tuple[StageDependency, ...] = ()
    authority_requirements: tuple[str, ...] = ()
    pack_requirements: tuple[str, ...] = ()
    deterministic_mode: str = "EXACT"
    execution_backend: str = "PYTHON_IN_PROCESS"
    checkpoint_capability: str = "NONE"
    cache_capability: str = "NONE"
    cache_scope: str | None = None
    resource_estimator: str | None = None
    external_artifact_policy: str = "COMPACT_GIT_LARGE_EXTERNAL"
    qa_requirements: tuple[str, ...] = ()
    adapter_identity: str = "UNBOUND"
    wrapper_mutation_policy: str = "NO_SCIENTIFIC_MUTATION"

    def __post_init__(self) -> None:
        for name in ("stage_id", "stage_version", "stage_kind", "implementation_identity", "contract_identity", "schema_identity", "execution_backend", "adapter_identity"):
            _required(name, getattr(self, name))
        _unique(self.input_types, "input_types"); _unique(self.output_types, "output_types")
        _unique(self.authority_requirements, "authority_requirements"); _unique(self.pack_requirements, "pack_requirements"); _unique(self.qa_requirements, "qa_requirements")
        dep_ids = tuple(dep.stage_id for dep in self.dependencies)
        _unique(dep_ids, "dependencies")
        if self.deterministic_mode not in DETERMINISM_MODES:
            raise ValueError("invalid deterministic_mode")
        if self.checkpoint_capability not in CHECKPOINT_CAPABILITIES:
            raise ValueError("invalid checkpoint_capability")
        if self.wrapper_mutation_policy != "NO_SCIENTIFIC_MUTATION":
            raise ValueError("IROF v0.1 forbids scientific wrapper mutation")

    def semantic_dict(self) -> dict[str, Any]:
        return {"stage_id": self.stage_id, "stage_version": self.stage_version, "stage_kind": self.stage_kind, "implementation_identity": self.implementation_identity, "contract_identity": self.contract_identity, "schema_identity": self.schema_identity, "input_types": list(self.input_types), "output_types": list(self.output_types), "dependencies": [dep.to_dict() for dep in sorted(self.dependencies, key=lambda item: item.stage_id)], "authority_requirements": list(self.authority_requirements), "pack_requirements": list(self.pack_requirements), "deterministic_mode": self.deterministic_mode, "execution_backend": self.execution_backend, "checkpoint_capability": self.checkpoint_capability, "cache_capability": self.cache_capability, "cache_scope": self.cache_scope, "resource_estimator": self.resource_estimator, "external_artifact_policy": self.external_artifact_policy, "qa_requirements": list(self.qa_requirements), "adapter_identity": self.adapter_identity, "wrapper_mutation_policy": self.wrapper_mutation_policy}

    @property
    def logical_hash(self) -> str:
        return logical_sha256(self.semantic_dict())

    def to_dict(self) -> dict[str, Any]:
        return {**self.semantic_dict(), "logical_hash": self.logical_hash}


@dataclass(frozen=True)
class StageInvocation:
    stage_id: str
    stage_spec_hash: str
    parent_artifact_hashes: tuple[str, ...] = ()
    pack_bindings: Mapping[str, str] = field(default_factory=dict)
    configuration: Mapping[str, Any] = field(default_factory=dict)

    def semantic_dict(self) -> dict[str, Any]:
        return {"stage_id": self.stage_id, "stage_spec_hash": self.stage_spec_hash, "parent_artifact_hashes": sorted(self.parent_artifact_hashes), "pack_bindings": dict(self.pack_bindings), "configuration": dict(self.configuration)}

    @property
    def invocation_id(self) -> str:
        return stable_id("IROF.INVOCATION.", self.semantic_dict())

    def to_dict(self) -> dict[str, Any]:
        return {**self.semantic_dict(), "invocation_id": self.invocation_id}


@dataclass(frozen=True)
class AuthorityBinding:
    binding_id: str
    owner_programme: str
    owner_gate: str
    authority_kind: str
    subject: str
    exact_scope: Mapping[str, Any]
    decision: str
    status: str
    source_decision_artifact: str
    source_decision_hash: str | None = None
    token_state: str | None = None
    expires_at: str | None = None
    superseded_by: str | None = None

    def __post_init__(self) -> None:
        for name in ("binding_id", "owner_programme", "owner_gate", "authority_kind", "subject", "decision", "status", "source_decision_artifact"):
            _required(name, getattr(self, name))
        if self.decision not in AUTHORITY_DECISIONS:
            raise ValueError("AuthorityBinding records authority; it cannot invent an unrecognised decision")

    def to_dict(self) -> dict[str, Any]:
        return {"binding_id": self.binding_id, "owner_programme": self.owner_programme, "owner_gate": self.owner_gate, "authority_kind": self.authority_kind, "subject": self.subject, "exact_scope": dict(self.exact_scope), "decision": self.decision, "status": self.status, "source_decision_artifact": self.source_decision_artifact, "source_decision_hash": self.source_decision_hash, "token_state": self.token_state, "expires_at": self.expires_at, "superseded_by": self.superseded_by}


@dataclass(frozen=True)
class ResearchRunSpec:
    population: PopulationSpec
    profile: PipelineProfile
    stage_specs: tuple[StageSpec, ...]
    authority_bindings: tuple[AuthorityBinding, ...] = ()
    pack_bindings: Mapping[str, str] = field(default_factory=dict)
    chronology_policy_id: str | None = None
    comparability_domain_id: str | None = None
    context_role_identity: str | None = None
    code_identity: str | None = None
    workers: int | None = None
    scheduling_policy: str | None = None
    physical_output_root: str | None = None

    def __post_init__(self) -> None:
        ids = tuple(item.stage_id for item in self.stage_specs)
        _unique(ids, "stage_specs")
        missing = set(self.profile.included_stage_ids) - set(ids)
        if missing:
            raise ValueError(f"profile stages missing StageSpec: {sorted(missing)}")
        if self.workers is not None and self.workers <= 0:
            raise ValueError("workers must be positive")

    def semantic_dict(self) -> dict[str, Any]:
        stages = {item.stage_id: item.logical_hash for item in self.stage_specs if item.stage_id in self.profile.included_stage_ids}
        return {"population_hash": self.population.logical_hash, "profile_hash": self.profile.logical_hash, "stage_spec_hashes": stages, "authority_binding_ids": sorted(item.binding_id for item in self.authority_bindings), "pack_bindings": dict(self.pack_bindings), "chronology_policy_id": self.chronology_policy_id, "comparability_domain_id": self.comparability_domain_id, "context_role_identity": self.context_role_identity, "code_identity": self.code_identity}

    @property
    def semantic_run_id(self) -> str:
        return stable_id("IROF.RUN.", self.semantic_dict())

    def to_dict(self) -> dict[str, Any]:
        return {**self.semantic_dict(), "semantic_run_id": self.semantic_run_id, "workers": self.workers, "scheduling_policy": self.scheduling_policy, "physical_output_root": self.physical_output_root}


@dataclass(frozen=True)
class IntegratedRunManifest:
    semantic_run_id: str
    population_hash: str
    profile_hash: str
    stage_invocations: tuple[StageInvocation, ...]
    authority_binding_ids: tuple[str, ...]
    manifest_version: str = "0.1"

    def semantic_dict(self) -> dict[str, Any]:
        return {"manifest_version": self.manifest_version, "semantic_run_id": self.semantic_run_id, "population_hash": self.population_hash, "profile_hash": self.profile_hash, "stage_invocations": [item.to_dict() for item in sorted(self.stage_invocations, key=lambda item: item.stage_id)], "authority_binding_ids": sorted(self.authority_binding_ids)}

    @property
    def logical_hash(self) -> str:
        return logical_sha256(self.semantic_dict())

    def to_dict(self) -> dict[str, Any]:
        return {**self.semantic_dict(), "logical_hash": self.logical_hash}


@dataclass(frozen=True)
class ArtifactRef:
    artifact_id: str
    logical_hash: str
    artifact_type: str
    owner_stage_id: str
    owner_run_id: str
    lifecycle_state: str
    content_sha256: str | None = None
    parent_artifact_ids: tuple[str, ...] = ()
    semantic_cache_key: str | None = None
    authority_classification: str = "DERIVED_ONLY"
    media_type: str | None = None
    schema_identity: str | None = None
    size_bytes: int | None = None
    locations: tuple[Mapping[str, str], ...] = ()
    created_attempt_id: str | None = None
    verification_status: str = "NOT_EVALUATED"

    def __post_init__(self) -> None:
        if self.lifecycle_state not in ARTIFACT_STATES:
            raise ValueError("invalid artifact lifecycle_state")

    def semantic_dict(self) -> dict[str, Any]:
        return {"artifact_id": self.artifact_id, "logical_hash": self.logical_hash, "content_sha256": self.content_sha256, "artifact_type": self.artifact_type, "owner_stage_id": self.owner_stage_id, "owner_run_id": self.owner_run_id, "parent_artifact_ids": list(self.parent_artifact_ids), "semantic_cache_key": self.semantic_cache_key, "authority_classification": self.authority_classification, "lifecycle_state": self.lifecycle_state, "media_type": self.media_type, "schema_identity": self.schema_identity, "size_bytes": self.size_bytes}

    def to_dict(self) -> dict[str, Any]:
        return {**self.semantic_dict(), "locations": [dict(item) for item in self.locations], "created_attempt_id": self.created_attempt_id, "verification_status": self.verification_status}


@dataclass(frozen=True)
class SemanticCacheKey:
    stage_id: str
    stage_version: str
    parent_semantic_hashes: tuple[str, ...]
    contract_identity: str
    schema_identity: str
    implementation_identity: str
    pack_bindings: Mapping[str, str] = field(default_factory=dict)
    population_hash: str | None = None
    chronology_identity: str | None = None
    comparability_identity: str | None = None
    context_role_identity: str | None = None
    code_identity: str | None = None

    def material(self) -> dict[str, Any]:
        return {"stage_id": self.stage_id, "stage_version": self.stage_version, "parent_semantic_hashes": sorted(self.parent_semantic_hashes), "contract_identity": self.contract_identity, "schema_identity": self.schema_identity, "implementation_identity": self.implementation_identity, "pack_bindings": dict(self.pack_bindings), "population_hash": self.population_hash, "chronology_identity": self.chronology_identity, "comparability_identity": self.comparability_identity, "context_role_identity": self.context_role_identity, "code_identity": self.code_identity}

    @property
    def key(self) -> str:
        return stable_id("IROF.CACHE.", self.material())

    def to_dict(self) -> dict[str, Any]:
        return {**self.material(), "key": self.key}


@dataclass(frozen=True)
class CheckpointRecord:
    checkpoint_id: str
    semantic_run_id: str
    stage_id: str
    level: str
    content_hash: str
    status: str
    owner_checkpoint_schema: str | None = None
    opaque_ref: str | None = None
    attempt_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return self.__dict__.copy()


@dataclass(frozen=True)
class RestartLedger:
    semantic_run_id: str
    attempt_ids: tuple[str, ...]
    checkpoint_ids: tuple[str, ...]
    restart_count: int
    recovered_work_units: int = 0
    repeated_work_units: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {"semantic_run_id": self.semantic_run_id, "attempt_ids": list(self.attempt_ids), "checkpoint_ids": list(self.checkpoint_ids), "restart_count": self.restart_count, "recovered_work_units": self.recovered_work_units, "repeated_work_units": self.repeated_work_units}


@dataclass(frozen=True)
class CapacityBudget:
    tier_id: str
    max_wall_seconds: float | None = None
    max_peak_rss_bytes: int | None = None
    max_external_bytes: int | None = None
    max_workers: int | None = None

    def __post_init__(self) -> None:
        _required("tier_id", self.tier_id)
        for value in (self.max_wall_seconds, self.max_peak_rss_bytes, self.max_external_bytes, self.max_workers):
            if value is not None and value <= 0:
                raise ValueError("capacity limits must be positive")

    def to_dict(self) -> dict[str, Any]:
        return self.__dict__.copy()


@dataclass(frozen=True)
class CapacityReceipt:
    run_id: str
    stage_id: str
    status: str
    estimated: Mapping[str, Any] = field(default_factory=dict)
    observed: Mapping[str, Any] = field(default_factory=dict)
    reason_codes: tuple[str, ...] = ()
    scientific_effect: str = "NONE"

    def __post_init__(self) -> None:
        if self.status not in EXECUTION_STATUSES:
            raise ValueError("invalid capacity status")
        if self.scientific_effect != "NONE":
            raise ValueError("capacity receipt cannot claim scientific effect")

    def to_dict(self) -> dict[str, Any]:
        return {"run_id": self.run_id, "stage_id": self.stage_id, "status": self.status, "estimated": dict(self.estimated), "observed": dict(self.observed), "reason_codes": list(self.reason_codes), "scientific_effect": self.scientific_effect}


@dataclass(frozen=True)
class StageExecutionReceipt:
    run_id: str
    attempt_id: str
    stage_id: str
    stage_version: str
    status: str
    input_hashes: tuple[str, ...]
    output_artifact_ids: tuple[str, ...]
    metrics: Mapping[str, Any] = field(default_factory=dict)
    warnings: tuple[str, ...] = ()
    reason_codes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.status not in EXECUTION_STATUSES:
            raise ValueError("invalid execution status")

    def logical_dict(self) -> dict[str, Any]:
        return {"run_id": self.run_id, "stage_id": self.stage_id, "stage_version": self.stage_version, "status": self.status, "input_hashes": list(self.input_hashes), "output_artifact_ids": list(self.output_artifact_ids), "reason_codes": list(self.reason_codes)}

    def to_dict(self) -> dict[str, Any]:
        return {**self.logical_dict(), "attempt_id": self.attempt_id, "metrics": dict(self.metrics), "warnings": list(self.warnings)}


@dataclass(frozen=True)
class IntegratedRunReceipt:
    run_id: str
    attempt_id: str
    status: str
    stage_receipts: tuple[StageExecutionReceipt, ...]
    artifact_ids: tuple[str, ...] = ()
    qa_manifest_id: str | None = None
    aggregate_metrics: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.status not in EXECUTION_STATUSES:
            raise ValueError("invalid run status")

    def logical_dict(self) -> dict[str, Any]:
        return {"run_id": self.run_id, "status": self.status, "stage_receipts": [item.logical_dict() for item in sorted(self.stage_receipts, key=lambda item: item.stage_id)], "artifact_ids": list(self.artifact_ids), "qa_manifest_id": self.qa_manifest_id}

    @property
    def logical_hash(self) -> str:
        return logical_sha256(self.logical_dict())

    def to_dict(self) -> dict[str, Any]:
        return {**self.logical_dict(), "attempt_id": self.attempt_id, "aggregate_metrics": dict(self.aggregate_metrics), "logical_hash": self.logical_hash}


@dataclass(frozen=True)
class RunFailure:
    run_id: str
    failure_class: str
    reason_code: str
    blocked_stage_id: str | None = None
    blocked_descendants: tuple[str, ...] = ()
    reusable_ancestor_artifact_ids: tuple[str, ...] = ()
    required_authority: str | None = None
    current_authority: str | None = None
    owner_programme: str | None = None
    owner_gate: str | None = None
    detail: str | None = None

    def __post_init__(self) -> None:
        if self.failure_class not in FAILURE_CLASSES:
            raise ValueError("invalid failure_class")

    def to_dict(self) -> dict[str, Any]:
        return {"run_id": self.run_id, "failure_class": self.failure_class, "reason_code": self.reason_code, "blocked_stage_id": self.blocked_stage_id, "blocked_descendants": list(self.blocked_descendants), "reusable_ancestor_artifact_ids": list(self.reusable_ancestor_artifact_ids), "required_authority": self.required_authority, "current_authority": self.current_authority, "owner_programme": self.owner_programme, "owner_gate": self.owner_gate, "detail": self.detail}


@dataclass(frozen=True)
class RunComparisonRecord:
    left_run_id: str
    right_run_id: str
    comparison_kind: str
    left_logical_hash: str
    right_logical_hash: str
    equivalent: bool
    tolerance_identity: str | None = None
    differences: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {"left_run_id": self.left_run_id, "right_run_id": self.right_run_id, "comparison_kind": self.comparison_kind, "left_logical_hash": self.left_logical_hash, "right_logical_hash": self.right_logical_hash, "equivalent": self.equivalent, "tolerance_identity": self.tolerance_identity, "differences": list(self.differences)}
