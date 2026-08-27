from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from .core import SFFContractError, content_identity
from .risk import DistributionRecord


@dataclass(frozen=True)
class ForecastModelGeneration:
    generation_id: str
    method_binding_id: str
    parameter_identity: str
    calibration_partition_id: str
    mode: str = "STATIC"
    adaptive_state: str = "DEFERRED_NON_EXECUTABLE"

    @classmethod
    def freeze(cls, method_binding_id: str, parameters: Mapping[str, float], calibration_partition_id: str):
        if not method_binding_id or not calibration_partition_id or not parameters:
            raise SFFContractError("model generation inputs must be explicit")
        parameter_identity = content_identity("sff-parameters", parameters)
        payload = {
            "method_binding_id": method_binding_id,
            "parameter_identity": parameter_identity,
            "calibration_partition_id": calibration_partition_id,
            "mode": "STATIC",
            "adaptive_state": "DEFERRED_NON_EXECUTABLE",
        }
        return cls(content_identity("sff-model-generation", payload), method_binding_id, parameter_identity, calibration_partition_id)

    def update_from_outcomes(self, *_args, **_kwargs):
        raise SFFContractError("SAME_GENERATION_OUTCOME_UPDATE_PROHIBITED")


@dataclass(frozen=True)
class StructuralFutureUncertaintyConstitution:
    constitution_id: str
    required_planes: tuple[str, ...] = ("EPISTEMIC", "ALEATORIC", "SUPPORT")


@dataclass(frozen=True)
class UncertaintyRecord:
    epistemic: str
    aleatoric: str
    support: str
    evidence_identity: str

    def earned(self) -> bool:
        return all(value not in {"", "UNKNOWN"} for value in (self.epistemic, self.aleatoric, self.support, self.evidence_identity))


@dataclass(frozen=True)
class ForecastSnapshot:
    snapshot_id: str
    target_id: str
    generation_id: str
    distribution: DistributionRecord | None
    uncertainty: UncertaintyRecord
    status: str
    reason: str | None
    research_effect: str = "SYNTHETIC_REFERENCE_ONLY"


def build_forecast_snapshot(
    *,
    target_id: str,
    generation: ForecastModelGeneration,
    distribution: DistributionRecord,
    uncertainty: UncertaintyRecord,
    support_currentness: str,
) -> ForecastSnapshot:
    if support_currentness != "CURRENT_SUPPORTED":
        status, reason, emitted = "ABSTAINED", "SUPPORT_NOT_CURRENT", None
    elif not uncertainty.earned():
        status, reason, emitted = "ABSTAINED", "UNCERTAINTY_NOT_EARNED", None
    else:
        status, reason, emitted = ("PARTIAL" if distribution.completeness == "PARTIAL" else "ISSUED"), None, distribution
    payload = {
        "target_id": target_id,
        "generation_id": generation.generation_id,
        "distribution": emitted,
        "uncertainty": uncertainty,
        "status": status,
        "reason": reason,
        "research_effect": "SYNTHETIC_REFERENCE_ONLY",
    }
    return ForecastSnapshot(content_identity("sff-forecast-snapshot", payload), target_id, generation.generation_id, emitted, uncertainty, status, reason)
