from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import math
from typing import Mapping, Protocol, Sequence

from .core import SFFContractError, content_identity


class RiskStatus(str, Enum):
    RESOLVED = "RESOLVED"
    PREEMPTED = "PREEMPTED"
    EXPIRED = "EXPIRED"
    CENSORED = "CENSORED"
    NOT_EVALUABLE = "NOT_EVALUABLE"
    OUT_OF_SCOPE = "OUT_OF_SCOPE"
    ABSTAINED = "ABSTAINED"
    STILL_AT_RISK = "STILL_AT_RISK"


@dataclass(frozen=True)
class RiskSetEntry:
    target_id: str
    origin_id: str
    position: int
    status: RiskStatus
    dependence_group_id: str
    owner_dependency_state: str = "RESOLVED_CURRENT_AUTHORIZED"


@dataclass(frozen=True)
class ForecastRiskSetManifest:
    risk_set_id: str
    population_id: str
    entries: tuple[RiskSetEntry, ...]
    denominator: int
    repeated_snapshot_policy: str = "DEPENDENT_WITHIN_ORIGIN"

    @classmethod
    def build(cls, population_id: str, entries: Sequence[RiskSetEntry]) -> "ForecastRiskSetManifest":
        rows = tuple(entries)
        if not population_id or not rows:
            raise SFFContractError("risk-set population and entries are required")
        if len({(row.target_id, row.position) for row in rows}) != len(rows):
            raise SFFContractError("duplicate target-position risk-set entry")
        groups_by_origin: dict[str, set[str]] = {}
        for row in rows:
            groups_by_origin.setdefault(row.origin_id, set()).add(row.dependence_group_id)
        if any(len(groups) != 1 for groups in groups_by_origin.values()):
            raise SFFContractError("REPEATED_SNAPSHOT_PSEUDO_INDEPENDENCE")
        normalized = tuple(
            RiskSetEntry(
                target_id=row.target_id,
                origin_id=row.origin_id,
                position=row.position,
                status=(RiskStatus.NOT_EVALUABLE if row.owner_dependency_state != "RESOLVED_CURRENT_AUTHORIZED" else row.status),
                dependence_group_id=row.dependence_group_id,
                owner_dependency_state=row.owner_dependency_state,
            )
            for row in rows
        )
        payload = {"population_id": population_id, "entries": normalized, "denominator": len(normalized)}
        return cls(content_identity("sff-risk-set", payload), population_id, normalized, len(normalized))

    def counts(self) -> Mapping[str, int]:
        result = {status.value: 0 for status in RiskStatus}
        for row in self.entries:
            result[row.status.value] += 1
        if sum(result.values()) != self.denominator:
            raise SFFContractError("risk-set denominator reconciliation failed")
        return result


@dataclass(frozen=True)
class DistributionRecord:
    probabilities: Mapping[str, float]
    completeness: str
    support_state: str

    def __post_init__(self) -> None:
        if not self.probabilities:
            raise SFFContractError("probability distribution must not be empty")
        if any(not math.isfinite(value) for value in self.probabilities.values()):
            raise SFFContractError("probabilities must be finite")
        if any(value < 0 or value > 1 for value in self.probabilities.values()):
            raise SFFContractError("probabilities must be within [0,1]")
        total = sum(self.probabilities.values())
        if self.completeness == "COMPLETE" and abs(total - 1.0) > 1e-12:
            raise SFFContractError("complete distribution must sum to one")
        if self.completeness == "PARTIAL" and total >= 1.0:
            raise SFFContractError("partial distribution must preserve unallocated mass")
        if self.completeness not in {"COMPLETE", "PARTIAL"}:
            raise SFFContractError("distribution completeness must be explicit")
        if self.support_state not in {"KNOWN", "UNKNOWN"}:
            raise SFFContractError("support state must be explicit")

    def probability(self, outcome: str) -> float | None:
        if outcome in self.probabilities:
            return self.probabilities[outcome]
        if self.support_state == "UNKNOWN":
            return None
        return 0.0


class NeutralOptCAdapter(Protocol):
    def measure(self, target_id: str) -> Mapping[str, object] | None: ...


def evaluate_with_opt_c(adapter: NeutralOptCAdapter | None, target_id: str) -> Mapping[str, object]:
    if adapter is None:
        return {"target_id": target_id, "status": RiskStatus.ABSTAINED.value, "reason": "OPT_C_OWNER_DEPENDENCY_MISSING"}
    result = adapter.measure(target_id)
    if result is None:
        return {"target_id": target_id, "status": RiskStatus.NOT_EVALUABLE.value, "reason": "OPT_C_NO_LAWFUL_MEASUREMENT"}
    return {"target_id": target_id, "status": RiskStatus.RESOLVED.value, "measurement": dict(result)}
