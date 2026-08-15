from __future__ import annotations

from dataclasses import asdict, dataclass
from statistics import mean
from typing import Iterable

from ovc.development.identity import canonical_sha256
from ovc.development.skills.vit_core import VitContractError


@dataclass(frozen=True)
class LanePacketObservation:
    lane_id: str
    packet_id: str
    build_seconds: float
    rebuild_seconds: float
    vit_lag_seconds: float
    checkpoint_seconds: float
    peak_memory_bytes: int
    durable_storage_bytes: int
    invalidation_severity: str
    discarded_for_topology: bool = False
    operator_intervention_unexpected: bool = False
    qualified_materialisable_idle_seconds: float = 0.0
    false_authority_allow: bool = False
    reference_optimized_equal: bool = True
    safe_bypass_exercised: bool = False
    external_reanchor_exercised: bool = False
    restart_exercised: bool = False


@dataclass(frozen=True)
class VITOperationalBudget:
    lane_count: int
    min_packets_per_lane: int
    parallel_build_slots_observed: int
    build_ahead_packets_observed: int
    false_parallel_value_rate: float
    mean_vit_lag_seconds: float
    peak_vit_lag_seconds: float
    peak_memory_bytes: int
    peak_storage_bytes: int
    mean_checkpoint_seconds: float
    mean_rebuild_seconds: float
    unexpected_operator_interventions: int
    physical_integration_idle_seconds: float
    placement_recompute_count: int
    assurance_renewal_count: int
    payload_rebuild_count: int
    authority_review_count: int
    source: str = "MEASURED_Q4_OBSERVATIONS"

    @property
    def budget_id(self) -> str:
        return canonical_sha256(asdict(self))


@dataclass(frozen=True)
class Q4StressReport:
    budget: VITOperationalBudget
    no_lane_starvation: bool
    work_conserving: bool
    zero_false_authority_allows: bool
    reference_optimized_equivalence: bool
    safe_bypass_exercised: bool
    selective_invalidation_exercised: bool
    restart_exercised: bool
    external_reanchor_exercised: bool

    @property
    def report_id(self) -> str:
        return canonical_sha256(asdict(self))

    @property
    def passes(self) -> bool:
        return all((
            self.budget.lane_count >= 3,
            self.budget.min_packets_per_lane >= 2,
            self.no_lane_starvation,
            self.work_conserving,
            self.zero_false_authority_allows,
            self.reference_optimized_equivalence,
            self.safe_bypass_exercised,
            self.selective_invalidation_exercised,
            self.restart_exercised,
            self.external_reanchor_exercised,
        ))


def measure_q4(observations: Iterable[LanePacketObservation]) -> Q4StressReport:
    obs = tuple(observations)
    if not obs:
        raise VitContractError("Q4_MEASURED_OBSERVATIONS_REQUIRED")
    by_lane: dict[str, list[LanePacketObservation]] = {}
    for item in obs:
        if min(item.build_seconds, item.rebuild_seconds, item.vit_lag_seconds, item.checkpoint_seconds, item.qualified_materialisable_idle_seconds) < 0 or item.peak_memory_bytes < 0 or item.durable_storage_bytes < 0:
            raise VitContractError("INPUT_PRECONDITION_MISMATCH")
        by_lane.setdefault(item.lane_id, []).append(item)
    if len(by_lane) < 3 or min(map(len, by_lane.values())) < 2:
        raise VitContractError("Q4_LIVE_LANE_DEPTH_INSUFFICIENT")
    severities = {"PLACEMENT_RECOMPUTE_ONLY": 0, "ASSURANCE_RENEWAL_REQUIRED": 0, "PAYLOAD_REBUILD_REQUIRED": 0, "AUTHORITY_REVIEW_REQUIRED": 0}
    for item in obs:
        if item.invalidation_severity in severities:
            severities[item.invalidation_severity] += 1
    budget = VITOperationalBudget(
        len(by_lane),
        min(map(len, by_lane.values())),
        len(by_lane),
        len(obs),
        sum(i.discarded_for_topology for i in obs) / len(obs),
        mean(i.vit_lag_seconds for i in obs),
        max(i.vit_lag_seconds for i in obs),
        max(i.peak_memory_bytes for i in obs),
        max(i.durable_storage_bytes for i in obs),
        mean(i.checkpoint_seconds for i in obs),
        mean(i.rebuild_seconds for i in obs),
        sum(i.operator_intervention_unexpected for i in obs),
        sum(i.qualified_materialisable_idle_seconds for i in obs),
        severities["PLACEMENT_RECOMPUTE_ONLY"],
        severities["ASSURANCE_RENEWAL_REQUIRED"],
        severities["PAYLOAD_REBUILD_REQUIRED"],
        severities["AUTHORITY_REVIEW_REQUIRED"],
    )
    counts = [len(v) for v in by_lane.values()]
    return Q4StressReport(
        budget,
        min(counts) >= 2,
        not any(i.qualified_materialisable_idle_seconds > 0 and not i.operator_intervention_unexpected for i in obs),
        not any(i.false_authority_allow for i in obs),
        all(i.reference_optimized_equal for i in obs),
        any(i.safe_bypass_exercised for i in obs),
        sum(severities.values()) > 0,
        any(i.restart_exercised for i in obs),
        any(i.external_reanchor_exercised for i in obs),
    )
