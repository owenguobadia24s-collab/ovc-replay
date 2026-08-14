from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Iterable

from ovc.development.identity import canonical_sha256


@dataclass(frozen=True)
class HistoricalReplayEvent:
    event_id: str
    source_ref: str
    programme_id: str
    packet_id: str
    event_class: str
    discarded_assurance_cycles: int = 0
    reconciliation_attempts: int = 0
    operator_interventions: int = 0
    payload_rebuild_required: bool = False
    placement_only_recomputable: bool = False
    authority_source_explicit: bool = True


@dataclass(frozen=True)
class HistoricalReplayReport:
    source_count: int
    event_count: int
    discarded_assurance_cycles: int
    projected_placement_only_recomputations: int
    projected_payload_rebuilds: int
    historical_operator_interventions: int
    projected_operator_interventions: int
    authority_inference_count: int
    source_classes: tuple[str, ...]

    @property
    def report_id(self) -> str:
        return canonical_sha256(asdict(self))


def replay_historical_events(events: Iterable[HistoricalReplayEvent]) -> HistoricalReplayReport:
    ordered = tuple(sorted(events, key=lambda e: e.event_id))
    source_refs = {e.source_ref for e in ordered}
    source_classes = tuple(sorted({e.event_class for e in ordered}))
    placement_only = sum(1 for e in ordered if e.placement_only_recomputable)
    payload_rebuilds = sum(1 for e in ordered if e.payload_rebuild_required)
    historical_ops = sum(e.operator_interventions for e in ordered)
    authority_inference = sum(1 for e in ordered if not e.authority_source_explicit)
    projected_ops = sum(1 for e in ordered if e.event_class == "OPERATOR_AUTHORITY_BOUNDARY")
    return HistoricalReplayReport(
        source_count=len(source_refs),
        event_count=len(ordered),
        discarded_assurance_cycles=sum(e.discarded_assurance_cycles for e in ordered),
        projected_placement_only_recomputations=placement_only,
        projected_payload_rebuilds=payload_rebuilds,
        historical_operator_interventions=historical_ops,
        projected_operator_interventions=projected_ops,
        authority_inference_count=authority_inference,
        source_classes=source_classes,
    )


def require_q2_source_completeness(report: HistoricalReplayReport, required_classes: Iterable[str]) -> bool:
    required = set(required_classes)
    return report.authority_inference_count == 0 and required.issubset(set(report.source_classes)) and report.source_count >= len(required)
