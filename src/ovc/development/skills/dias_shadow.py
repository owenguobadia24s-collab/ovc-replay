"""Full side-effect-free DGS shadow qualification and gate readiness."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Mapping, Sequence

from ovc.development.identity import canonical_sha256
from ovc.development.skills.dias import DiasContractError
from ovc.development.skills.dias_materialisation import REQUIRED_LIVENESS_FUNCTIONS


ADVERSARIAL_SAFE_DISPOSITIONS = {
    "DIAS-AV-01": "BLOCK_MATERIALISATION_ON_DRIFT",
    "DIAS-AV-02": "RECONCILE_IDEMPOTENTLY",
    "DIAS-AV-03": "FRESH_PROCESS_RECONSTRUCT_PASS",
    "DIAS-AV-04": "REJECT_STALE_AND_QUARANTINE_DUAL_WRITER",
    "DIAS-AV-05": "RECONSTRUCT_RECEIPTS_AND_RELEASE_ONCE",
    "DIAS-AV-06": "DENY_SHADOW_SIDE_EFFECT_AND_INVALIDATE_EVIDENCE",
    "DIAS-AV-07": "DENY_PARENT_RAC_CONTAMINATION",
    "DIAS-AV-08": "REQUIRE_THIRD_PATH_OR_REFERENCE",
    "DIAS-AV-09": "REJECT_COHORT_FREEZE_MANIPULATION",
    "DIAS-AV-10": "DENY_GLOBAL_FREEZE_FOR_PARTIAL_COVERAGE",
    "DIAS-AV-11": "BLOCK_REMOVAL_WITHOUT_HISTORICAL_INTERPRETATION",
    "DIAS-AV-12": "BLOCK_REMOVAL_BEFORE_STABILISATION",
    "DIAS-AV-13": "QUARANTINE_UNRECOGNISED_WRITER_OR_A3_MISMATCH",
    "DIAS-AV-14": "RECONSTRUCT_RECEIPTS_FROM_PHYSICAL_MAIN",
    "DIAS-AV-15": "BLOCK_OWNER_CURRENTNESS_CONFLICT",
    "DIAS-AV-16": "BLOCK_TERMINAL_WITH_ACTIVE_DIASI_REGISTRY",
}


@dataclass(frozen=True)
class ShadowSideEffectFirewall:
    physical_main_writes: int = 0
    qualification_ledger_writes: int = 0
    live_status_writes: int = 0
    live_dispatches: int = 0
    intake_freezes: int = 0
    writer_transfers: int = 0
    cers_pes_mutations: int = 0
    parent_rac_evidence_writes: int = 0

    @property
    def intact(self) -> bool:
        return all(value == 0 for value in asdict(self).values())


@dataclass(frozen=True)
class ShadowScenarioResult:
    fixture_id: str
    observed_disposition: str
    side_effects: ShadowSideEffectFirewall

    @property
    def passed(self) -> bool:
        return self.side_effects.intact and ADVERSARIAL_SAFE_DISPOSITIONS.get(self.fixture_id) == self.observed_disposition


@dataclass(frozen=True)
class FullShadowRun:
    selected_class: str
    old_route_outcomes: Mapping[str, str]
    new_route_outcomes: Mapping[str, str]
    scenarios: tuple[ShadowScenarioResult, ...]
    complete_reference_route: bool
    firewall: ShadowSideEffectFirewall

    @property
    def exact_equivalence(self) -> bool:
        return dict(self.old_route_outcomes) == dict(self.new_route_outcomes)

    @property
    def adversarial_universe_closed(self) -> bool:
        return {result.fixture_id for result in self.scenarios} == set(ADVERSARIAL_SAFE_DISPOSITIONS) and all(result.passed for result in self.scenarios)

    @property
    def qualified(self) -> bool:
        return self.exact_equivalence and self.adversarial_universe_closed and self.complete_reference_route and self.firewall.intact

    @property
    def run_id(self) -> str:
        return canonical_sha256(asdict(self), role="diasi-full-shadow-run/v1")


@dataclass(frozen=True)
class RetirementFunctionCoverage:
    function: str
    incumbent: str
    replacement_owner: str
    replacement_status: str
    trigger_covered: bool
    reconciliation_covered: bool
    currentness_covered: bool
    in_flight_disposition: str
    active: bool = False


@dataclass(frozen=True)
class RetirementCoverageMatrix:
    selected_cutover_class: str
    functions: tuple[RetirementFunctionCoverage, ...]
    global_freeze_authorised: bool = False
    removal_eligible: bool = False

    def __post_init__(self) -> None:
        if {row.function for row in self.functions} != REQUIRED_LIVENESS_FUNCTIONS:
            raise DiasContractError("retirement coverage must bind all six exact CERS/PES functions")
        if self.global_freeze_authorised or self.removal_eligible:
            raise DiasContractError("WP5 grants neither global freeze nor removal")

    @property
    def cutover_scope_closed(self) -> bool:
        return all(
            row.replacement_status == "SHADOW_QUALIFIED_INACTIVE"
            and row.trigger_covered
            and row.reconciliation_covered
            and row.currentness_covered
            and row.in_flight_disposition == "ENUMERATE_FENCE_DRAIN_AT_GATE"
            and not row.active
            for row in self.functions
        )


@dataclass(frozen=True)
class ShadowOperationalBudget:
    name: str
    maximum: int
    unit: str
    observed: int
    safety_critical: bool

    @property
    def met(self) -> bool:
        return self.observed <= self.maximum


@dataclass(frozen=True)
class CutoverReadinessAssessment:
    shadow_run_id: str
    shadow_qualified: bool
    coverage_closed: bool
    budgets_frozen_and_met: bool
    route_fencing_qualified: bool
    writer_fencing_qualified: bool
    repository_protection_current: bool
    qualification_transfer_rehearsed: bool
    rollback_rehearsed: bool
    receipt_reconstruction_qualified: bool
    fresh_process_recovery_qualified: bool
    live_authority: bool = False

    @property
    def ready(self) -> bool:
        return (
            not self.live_authority
            and all(
                (
                    self.shadow_qualified,
                    self.coverage_closed,
                    self.budgets_frozen_and_met,
                    self.route_fencing_qualified,
                    self.writer_fencing_qualified,
                    self.repository_protection_current,
                    self.qualification_transfer_rehearsed,
                    self.rollback_rehearsed,
                    self.receipt_reconstruction_qualified,
                    self.fresh_process_recovery_qualified,
                )
            )
        )

    @property
    def disposition(self) -> str:
        return "READY_FOR_DIASI-G-DGS-CUTOVER-DRAIN" if self.ready else "NOT_READY"


def assess_cutover_readiness(
    *,
    shadow: FullShadowRun,
    coverage: RetirementCoverageMatrix,
    budgets: Sequence[ShadowOperationalBudget],
    route_fencing_qualified: bool,
    writer_fencing_qualified: bool,
    repository_protection_current: bool,
    qualification_transfer_rehearsed: bool,
    rollback_rehearsed: bool,
    receipt_reconstruction_qualified: bool,
    fresh_process_recovery_qualified: bool,
) -> CutoverReadinessAssessment:
    return CutoverReadinessAssessment(
        shadow.run_id,
        shadow.qualified,
        coverage.cutover_scope_closed,
        bool(budgets) and all(budget.met for budget in budgets),
        route_fencing_qualified,
        writer_fencing_qualified,
        repository_protection_current,
        qualification_transfer_rehearsed,
        rollback_rehearsed,
        receipt_reconstruction_qualified,
        fresh_process_recovery_qualified,
        False,
    )
