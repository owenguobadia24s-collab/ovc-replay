from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

from .core import SFFContractError, content_identity


@dataclass(frozen=True)
class ForecastSearchExposureManifest:
    manifest_id: str
    generation_id: str
    searched_targets: tuple[str, ...]
    multiplicity_policy_id: str
    calibration_partition_id: str

    @classmethod
    def freeze(cls, generation_id: str, searched_targets: Sequence[str], multiplicity_policy_id: str, calibration_partition_id: str):
        targets = tuple(searched_targets)
        if not all((generation_id, targets, multiplicity_policy_id, calibration_partition_id)):
            raise SFFContractError("search exposure must be complete")
        payload = {"generation_id": generation_id, "searched_targets": targets, "multiplicity_policy_id": multiplicity_policy_id, "calibration_partition_id": calibration_partition_id}
        return cls(content_identity("sff-search-exposure", payload), generation_id, targets, multiplicity_policy_id, calibration_partition_id)


@dataclass(frozen=True)
class ChallengerComparison:
    challenger_id: str
    credible_simpler: bool
    matched_support_result: str
    full_population_result: str


@dataclass(frozen=True)
class SFFFalsificationContract:
    contract_id: str
    blocking_dimensions: tuple[str, ...]
    non_compensation: bool = True


@dataclass(frozen=True)
class ClaimDecision:
    generation_id: str
    decision: str
    blocking_failures: tuple[str, ...]
    scientific_authority_effect: str = "NONE"


def decide_claim(
    *,
    generation_id: str,
    dimension_results: Mapping[str, str],
    falsification: SFFFalsificationContract,
    challengers: Sequence[ChallengerComparison],
) -> ClaimDecision:
    missing = [dimension for dimension in falsification.blocking_dimensions if dimension not in dimension_results]
    if missing:
        raise SFFContractError(f"CLAIM_DIMENSIONS_MISSING:{','.join(missing)}")
    if not challengers or any(not challenger.credible_simpler for challenger in challengers):
        raise SFFContractError("CREDIBLE_SIMPLER_CHALLENGER_MISSING")
    blockers = [dimension for dimension in falsification.blocking_dimensions if dimension_results[dimension] != "PASS"]
    if any(challenger.matched_support_result != "PASS" for challenger in challengers):
        blockers.append("CHALLENGER_MATCHED_SUPPORT")
    if any(challenger.full_population_result != "PASS" for challenger in challengers):
        blockers.append("CHALLENGER_FULL_POPULATION")
    blockers = tuple(sorted(blockers))
    return ClaimDecision(generation_id, "FAIL" if blockers else "MECHANICAL_ELIGIBLE", blockers)


@dataclass(frozen=True)
class FailureRecord:
    failure_id: str
    generation_id: str
    target_semantics_id: str
    reason: str
    disposition: str
    append_only: bool = True

    @classmethod
    def create(cls, generation_id: str, target_semantics_id: str, reason: str, disposition: str):
        if disposition not in {"FAILED_CONFIRMATORY", "QUARANTINED", "OUT_OF_SCOPE_PREDECLARED"}:
            raise SFFContractError("failure disposition is invalid")
        payload = {"generation_id": generation_id, "target_semantics_id": target_semantics_id, "reason": reason, "disposition": disposition}
        return cls(content_identity("sff-failure", payload), generation_id, target_semantics_id, reason, disposition)


def reentry_generation(failure: FailureRecord, *, proposed_generation_id: str, proposed_target_semantics_id: str) -> str:
    if proposed_generation_id == failure.generation_id:
        raise SFFContractError("SAME_GENERATION_RESCUE_PROHIBITED")
    if proposed_target_semantics_id != failure.target_semantics_id:
        return "SUCCESSOR_GENERATION_NEW_SEMANTICS_REQUIRED"
    return "SUCCESSOR_GENERATION_REENTRY_ELIGIBLE"
