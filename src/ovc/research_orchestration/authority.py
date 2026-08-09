from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping

from .models import AuthorityBinding, PopulationSpec, StageSpec
from .planner import CanonicalPlan

REAL_POPULATION_MODES = frozenset({"SEALED_REAL_REPLAY", "TIME_GATED_REPLAY", "LIVE_PROSPECTIVE"})
DENIED_VALIDATION_PREFIXES = ("LOCKED", "DENIED", "NOT_AUTHORISED")


class AuthorityError(ValueError):
    def __init__(self, reason_code: str, detail: str) -> None:
        self.reason_code = reason_code
        self.detail = detail
        super().__init__(f"{reason_code}: {detail}")


@dataclass(frozen=True)
class AuthorityRequirementSpec:
    requirement_id: str
    owner_programme: str
    owner_gate: str
    authority_kind: str
    subject: str
    allowed_binding_statuses: tuple[str, ...] = ("APPROVED", "ACTIVE", "AVAILABLE")
    required_scope: Mapping[str, Any] = field(default_factory=dict)
    require_unconsumed_token: bool = False

    def __post_init__(self) -> None:
        for name in ("requirement_id", "owner_programme", "owner_gate", "authority_kind", "subject"):
            if not str(getattr(self, name)).strip():
                raise AuthorityError("IROF_AUTHORITY_REQUIREMENT_FIELD_REQUIRED", name)
        if not self.allowed_binding_statuses:
            raise AuthorityError("IROF_AUTHORITY_ALLOWED_STATUS_REQUIRED", self.requirement_id)


@dataclass(frozen=True)
class RequirementResolution:
    requirement_id: str
    owner_programme: str
    owner_gate: str
    decision: str
    reason_codes: tuple[str, ...]
    matched_binding_id: str | None = None
    token_state_observed: str | None = None
    token_consumption_performed: bool = False


@dataclass(frozen=True)
class StageAuthorityReceipt:
    stage_id: str
    decision: str
    reason_codes: tuple[str, ...]
    requirement_resolutions: tuple[RequirementResolution, ...] = ()

    @property
    def matched_binding_ids(self) -> tuple[str, ...]:
        return tuple(sorted(item.matched_binding_id for item in self.requirement_resolutions if item.matched_binding_id is not None))


@dataclass(frozen=True)
class PopulationResolutionReceipt:
    population_id: str
    population_mode: str
    role: str
    status: str
    reason_codes: tuple[str, ...]
    protected_resolution_performed: bool
    physical_location_resolved: bool
    source_release_id: str | None = None
    source_manifest_hash: str | None = None


@dataclass(frozen=True)
class OwnerAuthorityObservation:
    binding_id: str
    owner_programme: str
    owner_gate: str
    decision: str
    status: str
    token_state: str | None
    used_by_stage_ids: tuple[str, ...]


@dataclass(frozen=True)
class AuthorityPreflightReceipt:
    profile_id: str
    population: PopulationResolutionReceipt
    execution_status: str
    stage_receipts: tuple[StageAuthorityReceipt, ...]
    blocked_stage_ids: tuple[str, ...]
    blocked_descendant_ids: tuple[str, ...]
    reusable_ancestor_stage_ids: tuple[str, ...]
    owner_authority_observations: tuple[OwnerAuthorityObservation, ...]
    token_consumption_performed: bool = False
    profile_degraded: bool = False
    synthetic_substitution_applied: bool = False


class AuthorityRequirementRegistry:
    def __init__(self, specs: Iterable[AuthorityRequirementSpec]) -> None:
        values = tuple(specs)
        ids = tuple(item.requirement_id for item in values)
        if len(ids) != len(set(ids)):
            raise AuthorityError("IROF_DUPLICATE_AUTHORITY_REQUIREMENT_ID", "duplicate requirement identity")
        self._specs = {item.requirement_id: item for item in values}

    def require(self, requirement_id: str) -> AuthorityRequirementSpec:
        try:
            return self._specs[requirement_id]
        except KeyError as exc:
            raise AuthorityError("IROF_AUTHORITY_REQUIREMENT_UNKNOWN", requirement_id) from exc

    def ids(self) -> tuple[str, ...]:
        return tuple(sorted(self._specs))


def _scope_satisfies(required: Mapping[str, Any], observed: Mapping[str, Any]) -> bool:
    # One binding must independently satisfy the complete required scope. Scope fragments
    # from multiple bindings are never unioned.
    return all(key in observed and observed[key] == value for key, value in required.items())


def _binding_identity_matches(requirement: AuthorityRequirementSpec, binding: AuthorityBinding) -> bool:
    return (
        binding.owner_programme == requirement.owner_programme
        and binding.owner_gate == requirement.owner_gate
        and binding.authority_kind == requirement.authority_kind
        and binding.subject == requirement.subject
    )


def resolve_requirement(requirement: AuthorityRequirementSpec, bindings: Iterable[AuthorityBinding]) -> RequirementResolution:
    candidates = tuple(binding for binding in bindings if _binding_identity_matches(requirement, binding))
    if not candidates:
        return RequirementResolution(
            requirement_id=requirement.requirement_id,
            owner_programme=requirement.owner_programme,
            owner_gate=requirement.owner_gate,
            decision="NOT_AUTHORISED",
            reason_codes=("IROF_OWNER_AUTHORITY_BINDING_MISSING",),
        )

    positives: list[AuthorityBinding] = []
    negative_reasons: set[str] = set()
    for binding in candidates:
        if binding.decision != "ALLOW":
            negative_reasons.add("IROF_OWNER_DECISION_NOT_ALLOW")
            continue
        if binding.status not in requirement.allowed_binding_statuses:
            negative_reasons.add("IROF_OWNER_BINDING_STATUS_NOT_ALLOWED")
            continue
        if not _scope_satisfies(requirement.required_scope, binding.exact_scope):
            negative_reasons.add("IROF_OWNER_SCOPE_MISMATCH")
            continue
        if requirement.require_unconsumed_token and binding.token_state not in {"UNCONSUMED", "AVAILABLE"}:
            negative_reasons.add("IROF_OWNER_TOKEN_NOT_UNCONSUMED")
            continue
        positives.append(binding)

    if len(positives) > 1:
        return RequirementResolution(
            requirement_id=requirement.requirement_id,
            owner_programme=requirement.owner_programme,
            owner_gate=requirement.owner_gate,
            decision="NOT_AUTHORISED",
            reason_codes=("IROF_AMBIGUOUS_MULTIPLE_OWNER_BINDINGS",),
        )
    if positives:
        binding = positives[0]
        return RequirementResolution(
            requirement_id=requirement.requirement_id,
            owner_programme=requirement.owner_programme,
            owner_gate=requirement.owner_gate,
            decision="ALLOW",
            reason_codes=(),
            matched_binding_id=binding.binding_id,
            token_state_observed=binding.token_state,
            token_consumption_performed=False,
        )

    representative = sorted(candidates, key=lambda item: item.binding_id)[0]
    return RequirementResolution(
        requirement_id=requirement.requirement_id,
        owner_programme=requirement.owner_programme,
        owner_gate=requirement.owner_gate,
        decision="NOT_AUTHORISED",
        reason_codes=tuple(sorted(negative_reasons or {"IROF_OWNER_AUTHORITY_NOT_EFFECTIVE"})),
        matched_binding_id=representative.binding_id,
        token_state_observed=representative.token_state,
        token_consumption_performed=False,
    )


def validation_is_protected(population: PopulationSpec) -> bool:
    state = population.validation_access_state.upper()
    role = population.role.upper()
    is_validation_role = role == "VALIDATION" or role.startswith("VALIDATION_")
    return population.population_mode in REAL_POPULATION_MODES and is_validation_role and state.startswith(DENIED_VALIDATION_PREFIXES)


def preflight_population_resolution(population: PopulationSpec) -> PopulationResolutionReceipt:
    if validation_is_protected(population):
        return PopulationResolutionReceipt(
            population_id=population.population_id,
            population_mode=population.population_mode,
            role=population.role,
            status="NOT_AUTHORISED",
            reason_codes=("IROF_VALIDATION_DENIED_BEFORE_PROTECTED_RESOLUTION",),
            protected_resolution_performed=False,
            physical_location_resolved=False,
        )
    return PopulationResolutionReceipt(
        population_id=population.population_id,
        population_mode=population.population_mode,
        role=population.role,
        status="METADATA_PREFLIGHT_READY",
        reason_codes=(),
        protected_resolution_performed=False,
        physical_location_resolved=False,
        source_release_id=population.source_release_id,
        source_manifest_hash=population.source_manifest_hash,
    )


def _is_source_stage(stage: StageSpec) -> bool:
    return "SOURCE" in stage.stage_kind.upper()


def preflight_plan_authority(
    *,
    plan: CanonicalPlan,
    stage_specs: Iterable[StageSpec],
    population: PopulationSpec,
    requirement_registry: AuthorityRequirementRegistry,
    bindings: Iterable[AuthorityBinding],
    reusable_stage_ids: Iterable[str] = (),
) -> AuthorityPreflightReceipt:
    stage_by_id = {item.stage_id: item for item in stage_specs}
    binding_values = tuple(bindings)
    population_receipt = preflight_population_resolution(population)

    if population_receipt.status == "NOT_AUTHORISED":
        root = plan.ordered_stage_ids[0] if plan.ordered_stage_ids else None
        blocked = (root,) if root else ()
        descendants = plan.blocked_descendants(blocked) if blocked else ()
        receipt = StageAuthorityReceipt(
            stage_id=root or "POPULATION_RESOLUTION",
            decision="NOT_AUTHORISED",
            reason_codes=population_receipt.reason_codes,
        )
        observations = _authority_observations(binding_values, (receipt,))
        return AuthorityPreflightReceipt(
            profile_id=plan.profile_id,
            population=population_receipt,
            execution_status="NOT_AUTHORISED",
            stage_receipts=(receipt,),
            blocked_stage_ids=blocked,
            blocked_descendant_ids=descendants,
            reusable_ancestor_stage_ids=(),
            owner_authority_observations=observations,
        )

    stage_receipts: list[StageAuthorityReceipt] = []
    blocked: list[str] = []
    for stage_id in plan.ordered_stage_ids:
        stage = stage_by_id[stage_id]
        reasons: set[str] = set()
        resolutions: list[RequirementResolution] = []

        if population.population_mode in REAL_POPULATION_MODES and _is_source_stage(stage) and not stage.authority_requirements:
            reasons.add("IROF_REAL_SOURCE_AUTHORITY_REQUIREMENT_MISSING")

        for requirement_id in stage.authority_requirements:
            try:
                requirement = requirement_registry.require(requirement_id)
            except AuthorityError:
                reasons.add("IROF_AUTHORITY_REQUIREMENT_UNKNOWN")
                continue
            resolution = resolve_requirement(requirement, binding_values)
            resolutions.append(resolution)
            if resolution.decision != "ALLOW":
                reasons.update(resolution.reason_codes)

        decision = "ALLOW" if not reasons else "NOT_AUTHORISED"
        if decision != "ALLOW":
            blocked.append(stage_id)
        stage_receipts.append(StageAuthorityReceipt(stage_id, decision, tuple(sorted(reasons)), tuple(resolutions)))

    blocked_ids = tuple(sorted(set(blocked)))
    descendants = plan.blocked_descendants(blocked_ids) if blocked_ids else ()
    effective_blocked = set(blocked_ids) | set(descendants)
    requested_reusable = set(reusable_stage_ids)
    reusable = tuple(stage_id for stage_id in plan.ordered_stage_ids if stage_id in requested_reusable and stage_id not in effective_blocked)
    observations = _authority_observations(binding_values, tuple(stage_receipts))
    return AuthorityPreflightReceipt(
        profile_id=plan.profile_id,
        population=population_receipt,
        execution_status="READY" if not blocked_ids else "NOT_AUTHORISED",
        stage_receipts=tuple(stage_receipts),
        blocked_stage_ids=blocked_ids,
        blocked_descendant_ids=descendants,
        reusable_ancestor_stage_ids=reusable,
        owner_authority_observations=observations,
        token_consumption_performed=False,
        profile_degraded=False,
        synthetic_substitution_applied=False,
    )


def _authority_observations(bindings: tuple[AuthorityBinding, ...], stage_receipts: tuple[StageAuthorityReceipt, ...]) -> tuple[OwnerAuthorityObservation, ...]:
    used: dict[str, set[str]] = {binding.binding_id: set() for binding in bindings}
    for receipt in stage_receipts:
        for requirement in receipt.requirement_resolutions:
            if requirement.matched_binding_id in used:
                used[requirement.matched_binding_id].add(receipt.stage_id)
    return tuple(
        OwnerAuthorityObservation(
            binding_id=binding.binding_id,
            owner_programme=binding.owner_programme,
            owner_gate=binding.owner_gate,
            decision=binding.decision,
            status=binding.status,
            token_state=binding.token_state,
            used_by_stage_ids=tuple(sorted(used[binding.binding_id])),
        )
        for binding in sorted(bindings, key=lambda item: item.binding_id)
    )
