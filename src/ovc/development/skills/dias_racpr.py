"""Embedded, reference-only RACPR CORE proof-resolution primitives."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Mapping, Sequence

from ovc.development.identity import canonical_sha256
from ovc.development.skills.dias import DiasContractError


CURRENTNESS_DIMENSIONS = frozenset(
    {"CLAIM", "METHOD", "DEPENDENCY", "HARNESS", "ENVIRONMENT", "POLICY", "PLACEMENT", "OWNER", "SOURCE_ARTIFACT"}
)
PROFILE_ATOMS = frozenset({"SELECTION", "SELECTED_EXECUTION", "ORCHESTRATION_VALIDATION", "BOUNDARY_PRESERVATION"})
REFERENCE_ONLY = "REFERENCE_ONLY"


def _require_exact(values: Sequence[str], label: str) -> tuple[str, ...]:
    result = tuple(values)
    if not result or any(not value for value in result) or len(set(result)) != len(result):
        raise DiasContractError(f"{label} must be non-empty, exact, and duplicate-free")
    return tuple(sorted(result))


@dataclass(frozen=True)
class AssuranceProofRequirement:
    claim_id: str
    rac_plan_id: str
    candidate_id: str
    required_assurance_members: tuple[str, ...]
    independence_requirements: tuple[str, ...]
    completeness_requirement: str
    currentness_requirements: tuple[str, ...]
    reference_method_id: str
    authority_mode: str = REFERENCE_ONLY

    def __post_init__(self) -> None:
        for field in ("claim_id", "rac_plan_id", "candidate_id", "reference_method_id"):
            if not getattr(self, field):
                raise DiasContractError(f"{field} is required")
        object.__setattr__(self, "required_assurance_members", _require_exact(self.required_assurance_members, "required members"))
        object.__setattr__(self, "independence_requirements", _require_exact(self.independence_requirements, "independence requirements"))
        object.__setattr__(self, "currentness_requirements", _require_exact(self.currentness_requirements, "currentness requirements"))
        if self.completeness_requirement not in {"EXACT_CLOSED_UNIVERSE", "EXACT_DECLARED_SUBSET", "BOUNDED_COMPLETE"}:
            raise DiasContractError("open or unknown completeness cannot support a proof requirement")
        if self.authority_mode != REFERENCE_ONLY:
            raise DiasContractError("WP4B requirements must remain reference-only")

    @property
    def requirement_id(self) -> str:
        return canonical_sha256(asdict(self), role="assurance-proof-requirement/v1")


@dataclass(frozen=True)
class ProofDependencyManifest:
    proof_attempt_id: str
    artifacts: tuple[str, ...]
    producers: tuple[str, ...]
    harnesses: tuple[str, ...]
    environments: tuple[str, ...]
    provenance: tuple[str, ...]
    dependency_tokens: tuple[str, ...]

    def __post_init__(self) -> None:
        for field in ("artifacts", "producers", "harnesses", "environments", "provenance", "dependency_tokens"):
            object.__setattr__(self, field, _require_exact(getattr(self, field), field))

    @property
    def manifest_id(self) -> str:
        return canonical_sha256(asdict(self), role="proof-dependency-manifest/v1")


@dataclass(frozen=True)
class ProofFrontierCompletenessManifest:
    dependency_manifest_id: str
    declared_universe: tuple[str, ...]
    observed_dependencies: tuple[str, ...]
    completeness: str
    unmapped_sentinel: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "declared_universe", _require_exact(self.declared_universe, "declared dependency universe"))
        object.__setattr__(self, "observed_dependencies", _require_exact(self.observed_dependencies, "observed dependencies"))

    @property
    def closed(self) -> bool:
        return (
            not self.unmapped_sentinel
            and self.completeness in {"EXACT_CLOSED_UNIVERSE", "EXACT_DECLARED_SUBSET", "BOUNDED_COMPLETE"}
            and set(self.declared_universe) == set(self.observed_dependencies)
        )


@dataclass(frozen=True)
class ProofCurrentnessAssessment:
    proof_id: str
    dimension_status: Mapping[str, str]
    frontier_complete: bool
    authority_mode: str = REFERENCE_ONLY

    @property
    def current(self) -> bool:
        return (
            self.authority_mode == REFERENCE_ONLY
            and self.frontier_complete
            and set(self.dimension_status) == CURRENTNESS_DIMENSIONS
            and all(value == "CURRENT" for value in self.dimension_status.values())
        )

    @property
    def disposition(self) -> str:
        return "REFERENCE_ONLY_CURRENT" if self.current else "REFERENCE_RERUN_REQUIRED"


@dataclass(frozen=True)
class ProofAdmissibilityPolicy:
    policy_id: str
    allowed_methods: Mapping[str, tuple[str, ...]]
    closed_rule_families: tuple[str, ...]
    performance_can_create_sufficiency: bool = False
    authority_mode: str = REFERENCE_ONLY

    def __post_init__(self) -> None:
        if self.performance_can_create_sufficiency or self.authority_mode != REFERENCE_ONLY:
            raise DiasContractError("performance cannot create sufficiency and WP4B is reference-only")

    def assess(
        self,
        *,
        claim_id: str,
        method_id: str,
        semantic_applicability: bool,
        exact_identity: bool,
        completeness: bool,
        independence: bool,
        currentness: bool,
        deterministic_rule_pass: bool,
    ) -> str:
        valid = all((semantic_applicability, exact_identity, completeness, independence, currentness, deterministic_rule_pass))
        if method_id not in self.allowed_methods.get(claim_id, ()) or not valid:
            return "REFERENCE_EXECUTION"
        return "REFERENCE_ONLY_PROOF_AVAILABLE"


@dataclass(frozen=True)
class AssuranceMemberSatisfactionBinding:
    requirement_id: str
    required_member: str
    claim_id: str
    method_id: str
    proof_id: str
    independence_constraints: tuple[str, ...]
    completeness_constraint: str
    currentness_constraints: tuple[str, ...]
    decision_bearing: bool = False

    def __post_init__(self) -> None:
        if self.decision_bearing:
            raise DiasContractError("WP4B cannot create a decision-bearing satisfaction binding")

    @property
    def binding_id(self) -> str:
        return canonical_sha256(asdict(self), role="assurance-member-satisfaction-binding/v1")


@dataclass(frozen=True)
class ReferenceReconciliationSchedule:
    method_class: str
    mandatory_triggers: tuple[str, ...]
    maximum_unreconciled_candidates: int
    maximum_elapsed_seconds: int
    unreconciled_candidates: int
    elapsed_seconds: int

    @property
    def debt_exceeded(self) -> bool:
        return self.unreconciled_candidates > self.maximum_unreconciled_candidates or self.elapsed_seconds > self.maximum_elapsed_seconds

    @property
    def route(self) -> str:
        return "REFERENCE_EXECUTION" if self.debt_exceeded else REFERENCE_ONLY


@dataclass(frozen=True)
class CommonModeDependency:
    primitive: str
    shared_by_optimised_and_reference: bool
    critical: bool
    false_agreement_possible: bool
    mutation_fixture: str | None
    independent_third_path: str | None


@dataclass(frozen=True)
class CommonModeDependencyRegistry:
    dependencies: tuple[CommonModeDependency, ...]

    def __post_init__(self) -> None:
        if not self.dependencies:
            raise DiasContractError("common-mode registry cannot be empty")
        for dependency in self.dependencies:
            if dependency.shared_by_optimised_and_reference and dependency.critical and not dependency.mutation_fixture:
                raise DiasContractError("critical shared primitive requires a mutation fixture")
            if dependency.shared_by_optimised_and_reference and dependency.false_agreement_possible and not dependency.independent_third_path:
                raise DiasContractError("false-agreement risk requires an independent third path")


@dataclass(frozen=True)
class AssuranceProofExposure:
    proof_id: str
    rac_certificate_id: str
    materialised_commit: str
    materialised_tree: str
    successor_repository_assurance_generation: str
    decision_bearing: bool


@dataclass(frozen=True)
class AssuranceProofExposureLedger:
    entries: tuple[AssuranceProofExposure, ...]
    authority_mode: str = REFERENCE_ONLY

    def __post_init__(self) -> None:
        if self.authority_mode != REFERENCE_ONLY or any(entry.decision_bearing for entry in self.entries):
            raise DiasContractError("WP4B exposure ledger cannot record decision-bearing substitutions")

    def affected_generations(self, proof_id: str) -> tuple[str, ...]:
        return tuple(sorted({entry.successor_repository_assurance_generation for entry in self.entries if entry.proof_id == proof_id}))


@dataclass(frozen=True)
class ParentRACInterlockManifest:
    parent_state: str
    parent_general_pass: bool
    narrower_owner_interlock: str | None
    shadow_only: bool
    contamination_permitted: bool = False

    @property
    def decision_bearing_allowed(self) -> bool:
        return self.parent_general_pass or bool(self.narrower_owner_interlock)

    def __post_init__(self) -> None:
        if not self.shadow_only or self.contamination_permitted or self.decision_bearing_allowed:
            raise DiasContractError("current parent RAC state permits separately labelled shadow work only")


@dataclass(frozen=True)
class CollectionParityProof:
    expected: tuple[str, ...]
    observed: tuple[str, ...]
    loader_errors: tuple[str, ...]
    result: str
    authority_mode: str = REFERENCE_ONLY


def derive_collection_parity(expected: Sequence[str], observed: Sequence[str], loader_errors: Sequence[str] = ()) -> CollectionParityProof:
    expected_tuple, observed_tuple = tuple(expected), tuple(observed)
    exact = (
        not loader_errors
        and len(expected_tuple) == len(set(expected_tuple))
        and len(observed_tuple) == len(set(observed_tuple))
        and set(expected_tuple) == set(observed_tuple)
    )
    return CollectionParityProof(tuple(sorted(expected_tuple)), tuple(sorted(observed_tuple)), tuple(loader_errors), "PASS" if exact else "NOT_PROVABLE")


def runtime_compatibility_route(*, environment_equivalent: bool, dependency_frontier_closed: bool, residual_dependency_complete: bool) -> str:
    if environment_equivalent and dependency_frontier_closed:
        return "DERIVED_PROOF_REFERENCE_ONLY"
    if residual_dependency_complete and dependency_frontier_closed:
        return "RESIDUAL_EXECUTION_REFERENCE_ONLY"
    return "REFERENCE_EXECUTION"


def profile_assurance_decomposition(atom_results: Mapping[str, str]) -> str:
    if set(atom_results) != PROFILE_ATOMS or any(value != "PASS" for value in atom_results.values()):
        return "REFERENCE_EXECUTION"
    return "DECOMPOSED_PROOF_REFERENCE_ONLY"


@dataclass(frozen=True)
class FastPathCohort:
    candidate_ids: tuple[str, ...]
    exclusions: Mapping[str, str]
    frozen_before_observation: bool
    target_p90_seconds: int = 60

    def __post_init__(self) -> None:
        if not self.frozen_before_observation or self.target_p90_seconds != 60:
            raise DiasContractError("fast-path cohort and sub-60 objective must be preregistered")
        if set(self.candidate_ids) & set(self.exclusions) or any(not reason for reason in self.exclusions.values()):
            raise DiasContractError("cohort exclusions must be disjoint and reason-coded")
