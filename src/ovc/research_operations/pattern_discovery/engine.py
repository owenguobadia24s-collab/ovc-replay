from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable, Mapping

from .persistence import PatternDiscoveryEventLedger
from .transitions import extract_transitions
from .triggers import build_trigger_event
from .windows import CandidateWindowManager


class PatternDiscoveryEngine:
    """Bounded PD-WP1 service for fixture and read-only C2 processing."""

    def __init__(
        self,
        *,
        ledger_root: str | Path,
        max_open_per_family_scope: int = 1,
        max_open_per_instrument: int = 20,
    ) -> None:
        self.ledger = PatternDiscoveryEventLedger(ledger_root)
        self.windows = CandidateWindowManager(
            max_open_per_family_scope=max_open_per_family_scope,
            max_open_per_instrument=max_open_per_instrument,
        )

    def record_transition_pair(
        self,
        previous_record: Mapping[str, Any],
        current_record: Mapping[str, Any],
    ) -> list[dict[str, Any]]:
        transitions = extract_transitions(previous_record, current_record)
        self.ledger.transitions.append_many(transitions)
        return transitions

    def record_trigger(
        self,
        *,
        trigger_id: str,
        reason_code: str,
        source_transitions: Iterable[Mapping[str, Any]],
        operation_mode: str,
        closure_profile_id: str,
        rate_limit_group: str,
        first_valid_at: str | None = None,
    ) -> dict[str, Any]:
        event = build_trigger_event(
            trigger_id=trigger_id,
            reason_code=reason_code,
            source_transitions=source_transitions,
            operation_mode=operation_mode,
            closure_profile_id=closure_profile_id,
            rate_limit_group=rate_limit_group,
            first_valid_at=first_valid_at,
        )
        self.ledger.triggers.append(event)
        return event

    def open_candidate(
        self,
        snapshot_record: Mapping[str, Any],
        trigger_event: Mapping[str, Any],
        *,
        trigger_family: str,
        open_window_epoch: str | None = None,
        control_class: str = "NONE",
    ) -> dict[str, Any]:
        return self.windows.open_from_trigger(
            snapshot_record,
            trigger_event,
            trigger_family=trigger_family,
            open_window_epoch=open_window_epoch,
            control_class=control_class,
        )
