"""SHSI-WP10 non-cutover three-consumer pilot and terminal records."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping

from .foundation import PILOT_HARD_FLOOR_DIMENSIONS, PILOT_NUMERIC_CAP_DIMENSIONS
from .resolution import ResolutionManifest, SharedExecutionContext


class SharedTerminalError(ValueError):
    """A fail-closed terminal shadow-conformance contract violation."""


CONSUMERS = frozenset({
    "OVC-DSAI-v0.1",
    "OVC-EC1-DMRP-CONFORMANCE-v0.1",
    "OVC-OPTB-ESL-CONFORMANCE-v0.1",
})
TERMINAL_STATE = "SHARED_SYSTEMS_V0_1_IMPLEMENTED_THREE_CONSUMER_SHADOW_CONFORMANT"


def _text(value: str, field: str) -> str:
    if not isinstance(value, str) or not value or "latest" in value.casefold():
        raise SharedTerminalError(f"{field.upper()}_EXACT_REF_REQUIRED")
    return value


@dataclass(frozen=True)
class PilotConsumerBinding:
    consumer_programme_id: str
    resolution_manifest: ResolutionManifest
    execution_context: SharedExecutionContext
    shadow_packet_ref: str
    status: str = "SHADOW_ONLY"
    current_execution_binding_changed: bool = False
    authority_effect: str = "NONE"

    def __post_init__(self) -> None:
        if self.consumer_programme_id not in CONSUMERS:
            raise SharedTerminalError("PILOT_CONSUMER_UNKNOWN")
        _text(self.shadow_packet_ref, "shadow_packet_ref")
        if self.resolution_manifest.status != "RESOLVED":
            raise SharedTerminalError("PILOT_RESOLUTION_FAILED")
        if self.execution_context.resolution_manifest_id != self.resolution_manifest.logical_id:
            raise SharedTerminalError("PILOT_CONTEXT_RESOLUTION_MISMATCH")
        if (
            self.status != "SHADOW_ONLY" or self.current_execution_binding_changed
            or self.authority_effect != "NONE"
        ):
            raise SharedTerminalError("PILOT_CUTOVER_OR_AUTHORITY_FORBIDDEN")


@dataclass(frozen=True)
class IntegratedPilotMatrix:
    matrix_id: str
    bindings: tuple[PilotConsumerBinding, ...]
    status: str
    authority_effect: str = "NONE"

    def __post_init__(self) -> None:
        _text(self.matrix_id, "matrix_id")
        ids = [row.consumer_programme_id for row in self.bindings]
        valid = set(ids) == CONSUMERS and len(ids) == len(set(ids)) == 3
        expected = "PASS" if valid else "BLOCK"
        if self.status != expected:
            raise SharedTerminalError("PILOT_MATRIX_STATUS_INCONSISTENT")
        if any(row.current_execution_binding_changed for row in self.bindings):
            raise SharedTerminalError("PILOT_CURRENT_BINDING_CHANGE_FORBIDDEN")
        if self.authority_effect != "NONE":
            raise SharedTerminalError("PILOT_MATRIX_AUTHORITY_EFFECT_FORBIDDEN")


def build_integrated_pilot_matrix(
    matrix_id: str, bindings: Iterable[PilotConsumerBinding]
) -> IntegratedPilotMatrix:
    rows = tuple(bindings)
    valid = set(row.consumer_programme_id for row in rows) == CONSUMERS and len(rows) == 3
    return IntegratedPilotMatrix(matrix_id, rows, "PASS" if valid else "BLOCK")


@dataclass(frozen=True)
class GovernedCorpusEquivalence:
    equivalence_id: str
    consumer_programme_id: str
    corpus_ref: str
    corpus_class: str
    run_specification_ref: str
    reference_logical_sha256: str
    optimized_logical_sha256: str
    status: str
    cutover_authority_effect: str = "NONE"

    def __post_init__(self) -> None:
        for field in ("equivalence_id", "corpus_ref", "run_specification_ref"):
            _text(getattr(self, field), field)
        if self.consumer_programme_id not in CONSUMERS:
            raise SharedTerminalError("EQUIVALENCE_CONSUMER_UNKNOWN")
        if self.corpus_class not in {
            "ALREADY_LAWFUL_REAL_SOURCE", "GOVERNED_HISTORICAL", "SYNTHETIC_ONLY"
        }:
            raise SharedTerminalError("EQUIVALENCE_CORPUS_CLASS_UNKNOWN")
        expected = (
            "PASS" if self.reference_logical_sha256 == self.optimized_logical_sha256
            else "BLOCK"
        )
        if self.status != expected:
            raise SharedTerminalError("EQUIVALENCE_STATUS_INCONSISTENT")
        if self.cutover_authority_effect != "NONE":
            raise SharedTerminalError("EQUIVALENCE_CUTOVER_AUTHORITY_FORBIDDEN")


@dataclass(frozen=True)
class IntegratedReplayRecord:
    replay_id: str
    reference_logical_sha256: str
    optimized_logical_sha256: str
    restart_logical_sha256: str
    reshard_logical_sha256: str
    cold_resolution_logical_sha256: str
    status: str
    authority_effect: str = "NONE"

    def __post_init__(self) -> None:
        values = {
            self.reference_logical_sha256, self.optimized_logical_sha256,
            self.restart_logical_sha256, self.reshard_logical_sha256,
            self.cold_resolution_logical_sha256,
        }
        expected = "PASS" if len(values) == 1 else "BLOCK"
        if self.status != expected:
            raise SharedTerminalError("INTEGRATED_REPLAY_STATUS_INCONSISTENT")
        if self.authority_effect != "NONE":
            raise SharedTerminalError("INTEGRATED_REPLAY_AUTHORITY_EFFECT_FORBIDDEN")


@dataclass(frozen=True)
class PilotAcceptanceResult:
    result_id: str
    budget_ref: str
    observed_dimensions: tuple[tuple[str, float], ...]
    hard_floor_observations: tuple[tuple[str, int], ...]
    exceeded_dimensions: tuple[str, ...]
    violated_hard_floors: tuple[str, ...]
    disposition: str
    authority_effect: str = "NONE"

    def __post_init__(self) -> None:
        _text(self.result_id, "result_id")
        _text(self.budget_ref, "budget_ref")
        if {key for key, _ in self.observed_dimensions} != set(PILOT_NUMERIC_CAP_DIMENSIONS):
            raise SharedTerminalError("TERMINAL_NUMERIC_DIMENSION_SET_INCOMPLETE")
        if {key for key, _ in self.hard_floor_observations} != PILOT_HARD_FLOOR_DIMENSIONS:
            raise SharedTerminalError("TERMINAL_HARD_FLOOR_SET_INCOMPLETE")
        passed = not self.exceeded_dimensions and not self.violated_hard_floors
        expected = "PASS" if passed else "DEFER_OR_DO_NOT_MIGRATE"
        if self.disposition != expected:
            raise SharedTerminalError("TERMINAL_BUDGET_DISPOSITION_INCONSISTENT")
        if self.authority_effect != "NONE":
            raise SharedTerminalError("TERMINAL_BUDGET_AUTHORITY_EFFECT_FORBIDDEN")


def evaluate_terminal_budget(
    result_id: str, budget_ref: str, *, budget: Mapping[str, object],
    observed_dimensions: Mapping[str, float], hard_floor_observations: Mapping[str, int],
) -> PilotAcceptanceResult:
    caps = {str(row[0]): float(row[1]) for row in budget.get("numeric_caps", ())}  # type: ignore[arg-type]
    if set(caps) != set(PILOT_NUMERIC_CAP_DIMENSIONS):
        raise SharedTerminalError("TERMINAL_BUDGET_CAP_SET_INCOMPLETE")
    if set(observed_dimensions) != set(caps):
        raise SharedTerminalError("TERMINAL_NUMERIC_DIMENSION_SET_INCOMPLETE")
    if set(hard_floor_observations) != PILOT_HARD_FLOOR_DIMENSIONS:
        raise SharedTerminalError("TERMINAL_HARD_FLOOR_SET_INCOMPLETE")
    exceeded = tuple(sorted(key for key, value in observed_dimensions.items() if value > caps[key]))
    violated = tuple(sorted(key for key, value in hard_floor_observations.items() if value != 0))
    passed = not exceeded and not violated
    return PilotAcceptanceResult(
        result_id, budget_ref, tuple(sorted(observed_dimensions.items())),
        tuple(sorted(hard_floor_observations.items())), exceeded, violated,
        "PASS" if passed else "DEFER_OR_DO_NOT_MIGRATE",
    )


@dataclass(frozen=True)
class OperationalBurdenEntry:
    consumer_programme_id: str
    adapter_count: int
    adapter_code_surface_lines: int
    operator_time_seconds: float
    maintenance_time_seconds: float
    incident_contribution_count: int

    def __post_init__(self) -> None:
        if self.consumer_programme_id not in CONSUMERS:
            raise SharedTerminalError("BURDEN_CONSUMER_UNKNOWN")
        values = (
            self.adapter_count, self.adapter_code_surface_lines,
            self.operator_time_seconds, self.maintenance_time_seconds,
            self.incident_contribution_count,
        )
        if any(isinstance(value, bool) or value < 0 for value in values):
            raise SharedTerminalError("BURDEN_VALUE_INVALID")


@dataclass(frozen=True)
class ConsumerAdoptionDecision:
    decision_id: str
    consumer_programme_id: str
    disposition: str
    evidence_refs: tuple[str, ...]
    rollback_ref: str
    operator_review_required: bool = True
    current_execution_binding_changed: bool = False
    authority_effect: str = "NONE"

    def __post_init__(self) -> None:
        if self.consumer_programme_id not in CONSUMERS:
            raise SharedTerminalError("ADOPTION_CONSUMER_UNKNOWN")
        for field in ("decision_id", "rollback_ref"):
            _text(getattr(self, field), field)
        if self.disposition not in {
            "EVIDENCE_ONLY_READY_FOR_OPERATOR_REVIEW", "DEFER", "DO_NOT_MIGRATE"
        }:
            raise SharedTerminalError("ADOPTION_DISPOSITION_FORBIDDEN")
        if not self.evidence_refs:
            raise SharedTerminalError("ADOPTION_EVIDENCE_REQUIRED")
        if (
            not self.operator_review_required or self.current_execution_binding_changed
            or self.authority_effect != "NONE"
        ):
            raise SharedTerminalError("ADOPTION_CUTOVER_AUTHORITY_FORBIDDEN")


def build_adoption_decision(
    decision_id: str, consumer_programme_id: str, *,
    equivalence: GovernedCorpusEquivalence, evidence_refs: tuple[str, ...],
    rollback_ref: str,
) -> ConsumerAdoptionDecision:
    ready = equivalence.status == "PASS" and equivalence.corpus_class in {
        "ALREADY_LAWFUL_REAL_SOURCE", "GOVERNED_HISTORICAL"
    }
    return ConsumerAdoptionDecision(
        decision_id, consumer_programme_id,
        "EVIDENCE_ONLY_READY_FOR_OPERATOR_REVIEW" if ready else "DEFER",
        evidence_refs, rollback_ref,
    )


@dataclass(frozen=True)
class TerminalProgrammeRecord:
    record_id: str
    matrix_ref: str
    budget_result_ref: str
    adoption_decision_refs: tuple[str, ...]
    unresolved_incidents: tuple[str, ...]
    unresolved_owner_conflicts: tuple[str, ...]
    mandatory_reachability_gaps: tuple[str, ...]
    reproducibility_failures: tuple[str, ...]
    current_consumer_bindings_changed: bool
    terminal_state: str
    status: str
    authority_effect: str = "NONE"

    def __post_init__(self) -> None:
        for field in ("record_id", "matrix_ref", "budget_result_ref"):
            _text(getattr(self, field), field)
        if len(self.adoption_decision_refs) != 3:
            raise SharedTerminalError("TERMINAL_ADOPTION_DECISION_SET_INCOMPLETE")
        blockers = (
            self.unresolved_incidents or self.unresolved_owner_conflicts
            or self.mandatory_reachability_gaps or self.reproducibility_failures
            or self.current_consumer_bindings_changed
        )
        expected_status = "COMPLETED" if not blockers else "BLOCKED"
        expected_terminal = TERMINAL_STATE if not blockers else "NOT_REACHED"
        if self.status != expected_status or self.terminal_state != expected_terminal:
            raise SharedTerminalError("TERMINAL_STATE_INCONSISTENT")
        if self.authority_effect != "NONE":
            raise SharedTerminalError("TERMINAL_RECORD_AUTHORITY_EFFECT_FORBIDDEN")


def build_terminal_read_model(record: TerminalProgrammeRecord) -> dict[str, object]:
    if record.status != "COMPLETED":
        raise SharedTerminalError("BLOCKED_TERMINAL_READ_MODEL_FORBIDDEN")
    return {
        "schema": "ovc-shsi-terminal-read-model/v0.1",
        "source_record_ref": record.record_id,
        "terminal_state": record.terminal_state,
        "console_authority": "READ_ONLY",
        "mutation_routes": [],
        "frontend_scientific_calculation": "FORBIDDEN",
        "adoption_authority": "OPERATOR_REQUIRED_SEPARATE_GATE",
        "authority_effect": "NONE",
    }
