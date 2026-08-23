from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime
import json
from pathlib import Path
from typing import Any

from ovc.research_operations.canonical import canonical_sha256


_REGISTRY_PATH = (
    Path(__file__).resolve().parents[4]
    / "registries/research_operations/p1cdi/lifecycle_registry.json"
)
_EVENT_FIELDS = frozenset(
    {
        "record_type",
        "schema_version",
        "event_id",
        "generation_id",
        "activity_state",
        "effective_time",
        "source_scientific_disposition_ref",
        "authority_effect",
    }
)


def _load_registry() -> dict[str, Any]:
    value = json.loads(_REGISTRY_PATH.read_text(encoding="utf-8"))
    if value.get("schema") != "p1cdi-lifecycle-registry/v0.1" or value.get("status") != "CLOSED":
        raise RuntimeError("P1CDI lifecycle registry is not the frozen closed v0.1 registry")
    activity = value.get("inventory_activity")
    demand = value.get("demand")
    if type(activity) is not list or not activity or len(activity) != len(set(activity)):
        raise RuntimeError("P1CDI inventory activity registry is invalid")
    if type(demand) is not list or not demand or len(demand) != len(set(demand)):
        raise RuntimeError("P1CDI demand-state registry is invalid")
    if value.get("scientific_disposition_ownership") != "SOURCE_OWNER_REFERENCE_ONLY":
        raise RuntimeError("P1CDI scientific disposition ownership must remain source-owner reference only")
    return value


_LIFECYCLE_REGISTRY = _load_registry()
INVENTORY_ACTIVITY_STATES = tuple(_LIFECYCLE_REGISTRY["inventory_activity"])
DEMAND_STATES = tuple(_LIFECYCLE_REGISTRY["demand"])


def _exact_string(value: Any, name: str) -> str:
    if type(value) is not str or not value:
        raise ValueError(f"{name} must be a non-empty string")
    return value


def _timestamp(value: Any) -> str:
    text = _exact_string(value, "effective_time")
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("effective_time must be an ISO-8601 date-time") from exc
    if parsed.tzinfo is None:
        raise ValueError("effective_time must include a timezone")
    return text


def _event_identity_body(
    *,
    generation_id: str,
    activity_state: str,
    effective_time: str,
    source_scientific_disposition_ref: str | None,
) -> dict[str, Any]:
    return {
        "generation_id": generation_id,
        "activity_state": activity_state,
        "effective_time": effective_time,
        "source_scientific_disposition_ref": source_scientific_disposition_ref,
    }


def build_lifecycle_event(
    *,
    generation_id: str,
    activity_state: str,
    effective_time: str,
    source_scientific_disposition_ref: str | None = None,
) -> dict[str, Any]:
    """Build one append-only inventory-activity event without owning scientific disposition."""

    generation = _exact_string(generation_id, "generation_id")
    state = _exact_string(activity_state, "activity_state")
    if state not in INVENTORY_ACTIVITY_STATES:
        raise ValueError(f"unknown P1CDI inventory activity state: {state}")
    timestamp = _timestamp(effective_time)
    if source_scientific_disposition_ref is not None:
        source_scientific_disposition_ref = _exact_string(
            source_scientific_disposition_ref, "source_scientific_disposition_ref"
        )
    body = _event_identity_body(
        generation_id=generation,
        activity_state=state,
        effective_time=timestamp,
        source_scientific_disposition_ref=source_scientific_disposition_ref,
    )
    return {
        "record_type": "P1DistinctionLifecycleEvent",
        "schema_version": "0.1",
        "event_id": f"p1:lifecycle:{canonical_sha256(body)}",
        **body,
        "authority_effect": "NONE",
    }


def validate_lifecycle_event(event: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(event, Mapping) or set(event) != _EVENT_FIELDS:
        raise ValueError("P1DistinctionLifecycleEvent must use the exact frozen field set")
    if event.get("record_type") != "P1DistinctionLifecycleEvent" or event.get("schema_version") != "0.1":
        raise ValueError("P1DistinctionLifecycleEvent schema identity mismatch")
    if event.get("authority_effect") != "NONE":
        raise ValueError("P1DistinctionLifecycleEvent authority_effect must be NONE")
    expected = build_lifecycle_event(
        generation_id=event.get("generation_id"),
        activity_state=event.get("activity_state"),
        effective_time=event.get("effective_time"),
        source_scientific_disposition_ref=event.get("source_scientific_disposition_ref"),
    )
    if dict(event) != expected:
        raise ValueError("P1DistinctionLifecycleEvent identity/content mismatch")
    return expected


def project_inventory_activity(
    *, generation_id: str, lifecycle_events: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    """Project current inventory activity only; never infer scientific strength or disposition."""

    generation = _exact_string(generation_id, "generation_id")
    if not isinstance(lifecycle_events, Sequence) or isinstance(lifecycle_events, (str, bytes)):
        raise ValueError("lifecycle_events must be a sequence")
    validated = [validate_lifecycle_event(event) for event in lifecycle_events]
    matching = [event for event in validated if event["generation_id"] == generation]
    if not matching:
        raise ValueError("at least one lifecycle event for generation_id is required")
    matching.sort(key=lambda event: (event["effective_time"], event["event_id"]))
    latest = matching[-1]
    return {
        "record_type": "P1InventoryActivityProjection",
        "schema_version": "0.1",
        "generation_id": generation,
        "activity_state": latest["activity_state"],
        "source_scientific_disposition_ref": latest["source_scientific_disposition_ref"],
        "source_event_refs": [event["event_id"] for event in matching],
        "scientific_strength_inference": "DENIED",
        "decision_bearing": False,
        "authority_effect": "NONE",
    }
