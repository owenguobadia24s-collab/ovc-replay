from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from .catalogue import ArtifactCatalogue
from .storage import DraftStore, FrozenRecordStore


def _dt(value: str) -> datetime:
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        raise ValueError("timestamps must be timezone-aware")
    return parsed.astimezone(timezone.utc)


class ResearchQueueService:
    def __init__(self, *, records: FrozenRecordStore, catalogue: ArtifactCatalogue | None = None, drafts: DraftStore | None = None):
        self.records = records
        self.catalogue = catalogue
        self.drafts = drafts

    def show(self, queue_type: str, *, as_of: str, stale_after_hours: int = 24) -> list[dict[str, Any]]:
        handlers = {
            "realization-due": self._realization_due,
            "open-incidents": self._open_incidents,
            "incomplete-sessions": self._incomplete_sessions,
            "stale-catalogues": lambda _: self._stale_catalogues(as_of, stale_after_hours),
            "missing-artifacts": lambda _: self._missing_artifacts(),
        }
        try:
            return handlers[queue_type](as_of)
        except KeyError as exc:
            raise ValueError(f"unknown queue type: {queue_type}") from exc

    def _realization_due(self, as_of: str) -> list[dict[str, Any]]:
        now = _dt(as_of)
        realized_claims = {
            record["payload"].get("claim_id")
            for record in self.records.iter_records("REALIZATION_SNAPSHOT")
            if record["payload"].get("claim_id")
        }
        due: list[dict[str, Any]] = []
        for claim in self.records.iter_records("CLAIM_RECORD"):
            if claim["record_id"] in realized_claims:
                continue
            for horizon in claim["payload"].get("horizons", []):
                if isinstance(horizon, dict) and horizon.get("due_at") and _dt(horizon["due_at"]) <= now:
                    due.append({"claim_id": claim["record_id"], "observation_id": claim["payload"]["observation_id"], "due_at": horizon["due_at"], "horizon": horizon.get("name")})
        return sorted(due, key=lambda item: (item["due_at"], item["claim_id"]))

    def _open_incidents(self, _: str) -> list[dict[str, Any]]:
        return [
            {"record_id": record["record_id"], **record["payload"]}
            for record in self.records.iter_records("INCIDENT_RECORD")
            if record["payload"].get("resolution_state", "OPEN") != "CLOSED"
        ]

    def _incomplete_sessions(self, _: str) -> list[dict[str, Any]]:
        items = [
            {"record_id": record["record_id"], "objective": record["payload"]["objective"], "session_state": record["payload"]["session_state"]}
            for record in self.records.iter_records("RESEARCH_SESSION")
            if record["payload"].get("session_state") != "CLOSED"
        ]
        if self.drafts is not None:
            for draft_id, record in self.drafts.iter_drafts():
                if record.get("record_type") == "RESEARCH_SESSION" and record["payload"].get("session_state") != "CLOSED":
                    items.append({"draft_id": draft_id, "objective": record["payload"]["objective"], "session_state": record["payload"]["session_state"]})
        return sorted(items, key=lambda item: item.get("record_id", item.get("draft_id", "")))

    def _stale_catalogues(self, as_of: str, stale_after_hours: int) -> list[dict[str, Any]]:
        if self.catalogue is None:
            return [{"state": "MISSING", "detail": "no catalogue loaded"}]
        age = _dt(as_of) - _dt(self.catalogue.generated_at)
        if age > timedelta(hours=stale_after_hours):
            return [{"state": "STALE", "generated_at": self.catalogue.generated_at, "age_seconds": int(age.total_seconds())}]
        return []

    def _missing_artifacts(self) -> list[dict[str, Any]]:
        if self.catalogue is None:
            return [{"state": "MISSING", "detail": "no catalogue loaded"}]
        blocked = {"MISSING", "EXPIRED", "PARTIALLY_AVAILABLE"}
        return [
            {"artifact_id": node.artifact_id, "availability": node.availability, "locations": list(node.locations)}
            for node in self.catalogue.nodes
            if node.availability in blocked
        ]
