from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from ovc.research_operations.canonical import canonical_sha256

from .models import C2Snapshot, ChronologyError, PatternDiscoveryError, SourceBindingError, parse_utc


_OPEN_STATUSES = {"OPEN", "OPEN_PENDING_INPUT", "ACCUMULATING"}
_TERMINAL_STATUSES = {"READY_FOR_REVIEW", "REVIEWED", "DISMISSED", "INVALID", "SUPPRESSED_DUPLICATE", "SUPPRESSED_QUEUE_CAP"}
_CONTROL_CLASSES = {"NONE", "MATCHED_CONTROL", "POPULATION_CONTROL"}


@dataclass
class _RuntimeWindow:
    public: dict[str, Any]
    trigger_family: str
    closure_profile_id: str
    last_snapshot: C2Snapshot
    parent_container_id: str


def _public_copy(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = dict(value)
    copied["trigger_event_ids"] = list(value.get("trigger_event_ids", ()))
    copied["source_c2_record_ids"] = list(value.get("source_c2_record_ids", ()))
    return copied


class CandidateWindowManager:
    """Deterministic, in-memory CandidateWindow lifecycle manager.

    It creates only derived candidate objects. It performs no C2, selector, release,
    evidence-ledger, repository or R2 mutation.
    """

    def __init__(
        self,
        *,
        max_open_per_family_scope: int = 1,
        max_open_per_instrument: int = 20,
    ) -> None:
        if max_open_per_family_scope < 1 or max_open_per_instrument < 1:
            raise ValueError("candidate caps must be positive")
        self.max_open_per_family_scope = max_open_per_family_scope
        self.max_open_per_instrument = max_open_per_instrument
        self._windows: dict[str, _RuntimeWindow] = {}
        self.source_binding_active = True

    @staticmethod
    def candidate_dedup_key(
        snapshot: C2Snapshot,
        *,
        trigger_family: str,
        open_window_epoch: str,
    ) -> str:
        return "|".join(
            [
                "GBPUSD",
                snapshot.side,
                snapshot.clock,
                snapshot.evaluation_scope_id,
                trigger_family,
                snapshot.parent_container_id,
                snapshot.boundary_or_relation_id,
                open_window_epoch,
            ]
        )

    def _open_windows(self) -> list[_RuntimeWindow]:
        return [item for item in self._windows.values() if item.public["status"] in _OPEN_STATUSES]

    def _suppressed_window(
        self,
        *,
        snapshot: C2Snapshot,
        trigger_event: Mapping[str, Any],
        trigger_family: str,
        dedup_key: str,
        suppression_reason: str,
        control_class: str,
    ) -> dict[str, Any]:
        trigger_id = str(trigger_event["trigger_event_id"])
        identity = {
            "dedup_key": dedup_key,
            "trigger_event_id": trigger_id,
            "closure_profile_id": trigger_event["closure_profile_id"],
            "suppression_reason": suppression_reason,
        }
        public = {
            "window_id": f"PDW-{canonical_sha256(identity)[:32]}",
            "status": "SUPPRESSED_QUEUE_CAP",
            "operation_mode": trigger_event["operation_mode"],
            "instrument": "GBPUSD",
            "price_side": snapshot.side,
            "clock": snapshot.clock,
            "scope_id": snapshot.evaluation_scope_id,
            "window_start_utc": snapshot.first_valid_time,
            "trigger_first_valid_at": trigger_event["first_valid_at"],
            "window_end_utc": snapshot.first_valid_time,
            "closure_reason": None,
            "trigger_event_ids": [trigger_id],
            "trigger_snapshot_hash": self._trigger_snapshot_hash(snapshot, trigger_event, trigger_family),
            "completed_fingerprint_hash": None,
            "source_release_id": snapshot.c2_release_id,
            "source_manifest_id": snapshot.c2_manifest_id,
            "source_c2_record_ids": [snapshot.c2_state_id],
            "closure_profile_id": trigger_event["closure_profile_id"],
            "candidate_dedup_key": dedup_key,
            "control_class": control_class,
            "quality_state": snapshot.quality_state,
            "suppression_reason": suppression_reason,
        }
        self._windows[public["window_id"]] = _RuntimeWindow(
            public=public,
            trigger_family=trigger_family,
            closure_profile_id=str(trigger_event["closure_profile_id"]),
            last_snapshot=snapshot,
            parent_container_id=snapshot.parent_container_id,
        )
        return _public_copy(public)

    @staticmethod
    def _trigger_snapshot_hash(
        snapshot: C2Snapshot,
        trigger_event: Mapping[str, Any],
        trigger_family: str,
    ) -> str:
        trigger_time_view = {
            "c2_state_id": snapshot.c2_state_id,
            "release_id": snapshot.c2_release_id,
            "manifest_id": snapshot.c2_manifest_id,
            "first_valid_time": snapshot.first_valid_time,
            "clock": snapshot.clock,
            "side": snapshot.side,
            "scope_id": snapshot.evaluation_scope_id,
            "parameter_pack_id": snapshot.parameter_pack_id,
            "selector_id": snapshot.selector_id,
            "axes": snapshot.axes,
            "relation_set_id": snapshot.relation_set_id,
            "level_ids": snapshot.level_ids,
            "container_ids": snapshot.container_ids,
            "parent_container_id": snapshot.parent_container_id,
            "boundary_or_relation_id": snapshot.boundary_or_relation_id,
            "trigger_event": dict(trigger_event),
            "trigger_family": trigger_family,
        }
        return canonical_sha256(trigger_time_view)

    def open_from_trigger(
        self,
        snapshot_record: Mapping[str, Any] | C2Snapshot,
        trigger_event: Mapping[str, Any],
        *,
        trigger_family: str,
        open_window_epoch: str | None = None,
        control_class: str = "NONE",
    ) -> dict[str, Any]:
        if not self.source_binding_active:
            raise SourceBindingError("Pattern Discovery source binding is stopped and requires a new operator rebind")
        snapshot = snapshot_record if isinstance(snapshot_record, C2Snapshot) else C2Snapshot.from_mapping(snapshot_record)
        if control_class not in _CONTROL_CLASSES:
            raise PatternDiscoveryError(f"unsupported control class: {control_class}")
        trigger_time = str(trigger_event.get("first_valid_at"))
        parse_utc(trigger_time)
        if trigger_time != snapshot.first_valid_time:
            raise ChronologyError("candidate trigger must bind the exact first-valid C2 snapshot")
        closure_profile = str(trigger_event.get("closure_profile_id") or "")
        if not closure_profile:
            raise PatternDiscoveryError("TriggerEvent requires closure_profile_id")
        trigger_event_id = str(trigger_event.get("trigger_event_id") or "")
        if not trigger_event_id:
            raise PatternDiscoveryError("TriggerEvent requires trigger_event_id")
        epoch = open_window_epoch or trigger_time
        parse_utc(epoch)
        base_dedup_key = self.candidate_dedup_key(snapshot, trigger_family=trigger_family, open_window_epoch=epoch)

        for runtime in self._open_windows():
            if runtime.public["candidate_dedup_key"] != base_dedup_key:
                continue
            if runtime.closure_profile_id == closure_profile:
                event_ids = sorted(set(runtime.public["trigger_event_ids"] + [trigger_event_id]))
                source_ids = sorted(set(runtime.public["source_c2_record_ids"] + [snapshot.c2_state_id]))
                runtime.public["trigger_event_ids"] = event_ids
                runtime.public["source_c2_record_ids"] = source_ids
                runtime.public["status"] = "ACCUMULATING"
                runtime.public["quality_state"] = snapshot.quality_state
                return _public_copy(runtime.public)

        dedup_key = base_dedup_key
        if any(
            runtime.public["candidate_dedup_key"] == base_dedup_key
            and runtime.closure_profile_id != closure_profile
            for runtime in self._open_windows()
        ):
            dedup_key = f"{base_dedup_key}|{closure_profile}"

        family_scope_count = sum(
            1
            for runtime in self._open_windows()
            if runtime.trigger_family == trigger_family
            and runtime.public["instrument"] == "GBPUSD"
            and runtime.public["clock"] == snapshot.clock
            and runtime.public["price_side"] == snapshot.side
            and runtime.public["scope_id"] == snapshot.evaluation_scope_id
        )
        if family_scope_count >= self.max_open_per_family_scope:
            return self._suppressed_window(
                snapshot=snapshot,
                trigger_event=trigger_event,
                trigger_family=trigger_family,
                dedup_key=dedup_key,
                suppression_reason="PER_FAMILY_SCOPE_OPEN_CAP",
                control_class=control_class,
            )
        instrument_count = sum(
            1 for runtime in self._open_windows() if runtime.public["instrument"] == "GBPUSD"
        )
        if instrument_count >= self.max_open_per_instrument:
            return self._suppressed_window(
                snapshot=snapshot,
                trigger_event=trigger_event,
                trigger_family=trigger_family,
                dedup_key=dedup_key,
                suppression_reason="INSTRUMENT_OPEN_WINDOW_CAP",
                control_class=control_class,
            )

        identity = {
            "candidate_dedup_key": dedup_key,
            "trigger_event_id": trigger_event_id,
            "closure_profile_id": closure_profile,
            "trigger_snapshot_hash": self._trigger_snapshot_hash(snapshot, trigger_event, trigger_family),
        }
        public = {
            "window_id": f"PDW-{canonical_sha256(identity)[:32]}",
            "status": "OPEN",
            "operation_mode": trigger_event["operation_mode"],
            "instrument": "GBPUSD",
            "price_side": snapshot.side,
            "clock": snapshot.clock,
            "scope_id": snapshot.evaluation_scope_id,
            "window_start_utc": snapshot.first_valid_time,
            "trigger_first_valid_at": trigger_time,
            "window_end_utc": None,
            "closure_reason": None,
            "trigger_event_ids": [trigger_event_id],
            "trigger_snapshot_hash": identity["trigger_snapshot_hash"],
            "completed_fingerprint_hash": None,
            "source_release_id": snapshot.c2_release_id,
            "source_manifest_id": snapshot.c2_manifest_id,
            "source_c2_record_ids": [snapshot.c2_state_id],
            "closure_profile_id": closure_profile,
            "candidate_dedup_key": dedup_key,
            "control_class": control_class,
            "quality_state": snapshot.quality_state,
            "suppression_reason": None,
        }
        self._windows[public["window_id"]] = _RuntimeWindow(
            public=public,
            trigger_family=trigger_family,
            closure_profile_id=closure_profile,
            last_snapshot=snapshot,
            parent_container_id=snapshot.parent_container_id,
        )
        return _public_copy(public)

    def accumulate(
        self,
        window_id: str,
        snapshot_record: Mapping[str, Any] | C2Snapshot,
    ) -> dict[str, Any]:
        runtime = self._require(window_id)
        if runtime.public["status"] not in _OPEN_STATUSES:
            raise PatternDiscoveryError(f"candidate {window_id} is not open")
        snapshot = snapshot_record if isinstance(snapshot_record, C2Snapshot) else C2Snapshot.from_mapping(snapshot_record)
        if snapshot.binding_key != runtime.last_snapshot.binding_key:
            raise SourceBindingError("candidate accumulation cannot cross source binding")
        if parse_utc(snapshot.first_valid_time) <= parse_utc(runtime.last_snapshot.first_valid_time):
            raise ChronologyError("candidate accumulation must be strictly chronological")

        if snapshot.gap_before:
            return self.close(window_id, snapshot.first_valid_time, "CENSORED_GAP")
        if snapshot.authority_state == "QUARANTINED" or snapshot.quality_state == "QUARANTINED":
            return self.invalidate(window_id, snapshot.first_valid_time, "INVALID_SOURCE_QUARANTINED")
        if snapshot.parent_container_id != runtime.parent_container_id:
            return self.close(window_id, snapshot.first_valid_time, "CENSORED_CONTEXT_CHANGE")

        runtime.public["source_c2_record_ids"] = sorted(
            set(runtime.public["source_c2_record_ids"] + [snapshot.c2_state_id])
        )
        runtime.public["status"] = "ACCUMULATING"
        runtime.public["quality_state"] = snapshot.quality_state
        runtime.last_snapshot = snapshot
        return _public_copy(runtime.public)

    def mark_pending_input(self, window_id: str) -> dict[str, Any]:
        runtime = self._require(window_id)
        if runtime.public["status"] not in {"OPEN", "ACCUMULATING"}:
            raise PatternDiscoveryError("only open candidates may wait for input")
        runtime.public["status"] = "OPEN_PENDING_INPUT"
        return _public_copy(runtime.public)

    def resume_after_validated_input(self, window_id: str) -> dict[str, Any]:
        runtime = self._require(window_id)
        if runtime.public["status"] != "OPEN_PENDING_INPUT":
            raise PatternDiscoveryError("candidate is not pending input")
        runtime.public["status"] = "ACCUMULATING"
        return _public_copy(runtime.public)

    def close(self, window_id: str, end_utc: str, closure_reason: str) -> dict[str, Any]:
        runtime = self._require(window_id)
        if runtime.public["status"] not in _OPEN_STATUSES:
            raise PatternDiscoveryError("only open candidates may close")
        if parse_utc(end_utc) < parse_utc(runtime.public["window_start_utc"]):
            raise ChronologyError("candidate end cannot predate start")
        runtime.public["status"] = "READY_FOR_REVIEW"
        runtime.public["window_end_utc"] = end_utc
        runtime.public["closure_reason"] = closure_reason
        return _public_copy(runtime.public)

    def invalidate(self, window_id: str, end_utc: str, reason: str) -> dict[str, Any]:
        runtime = self._require(window_id)
        if runtime.public["status"] in _TERMINAL_STATUSES:
            raise PatternDiscoveryError("terminal candidate cannot be rewritten")
        parse_utc(end_utc)
        runtime.public["status"] = "INVALID"
        runtime.public["window_end_utc"] = end_utc
        runtime.public["closure_reason"] = reason
        return _public_copy(runtime.public)

    def stop_for_selector_change(self, end_utc: str) -> list[dict[str, Any]]:
        parse_utc(end_utc)
        self.source_binding_active = False
        stopped: list[dict[str, Any]] = []
        for runtime in list(self._open_windows()):
            runtime.public["status"] = "INVALID"
            runtime.public["window_end_utc"] = end_utc
            runtime.public["closure_reason"] = "SOURCE_SELECTOR_CHANGED"
            stopped.append(_public_copy(runtime.public))
        return sorted(stopped, key=lambda item: item["window_id"])

    def get(self, window_id: str) -> dict[str, Any]:
        return _public_copy(self._require(window_id).public)

    def all_windows(self) -> list[dict[str, Any]]:
        return sorted(
            (_public_copy(runtime.public) for runtime in self._windows.values()),
            key=lambda item: (item["trigger_first_valid_at"], item["window_id"]),
        )

    def _require(self, window_id: str) -> _RuntimeWindow:
        try:
            return self._windows[window_id]
        except KeyError as exc:
            raise PatternDiscoveryError(f"unknown candidate window: {window_id}") from exc
