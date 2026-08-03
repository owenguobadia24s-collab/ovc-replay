from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from copy import deepcopy
from typing import Any, Iterable, Mapping

from .ledger import validate_event


class ProjectionError(ValueError):
    """Raised when deterministic portfolio projection invariants fail."""


def _canonical_digest(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def order_events(events: Iterable[Mapping[str, Any]], precedence: Mapping[str, int]) -> list[dict[str, Any]]:
    materialised: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw in events:
        validate_event(raw, set(precedence))
        event = deepcopy(dict(raw))
        event_id = event["event_id"]
        if event_id in seen:
            raise ProjectionError(f"duplicate event_id: {event_id}")
        seen.add(event_id)
        materialised.append(event)
    return sorted(
        materialised,
        key=lambda item: (item["first_valid_at"], precedence[item["event_type"]], item["event_id"]),
    )


def project_programme(
    programme_id: str,
    events: Iterable[Mapping[str, Any]],
    precedence: Mapping[str, int],
) -> dict[str, Any]:
    ordered = [event for event in order_events(events, precedence) if event["programme_id"] == programme_id]
    state: dict[str, Any] = {
        "programme_id": programme_id,
        "status": "PLANNED",
        "current_packet": None,
        "current_gate": None,
        "blockers": [],
        "last_event_id": None,
        "authority_events": [],
    }
    blockers: dict[str, dict[str, Any]] = {}
    for event in ordered:
        event_id = event["event_id"]
        payload = event["payload"]
        event_type = event["event_type"]
        if event_type == "GENESIS_ACCEPTED":
            state["status"] = payload.get("status", "READY")
        elif event_type == "PACKET_STARTED":
            state["status"] = "RUNNING"
            state["current_packet"] = payload.get("packet_id")
            state["current_gate"] = payload.get("gate_id")
        elif event_type == "PACKET_IMPLEMENTED":
            state["status"] = "IMPLEMENTED"
        elif event_type == "QA_REVIEWED":
            state["status"] = "QA_REVIEW"
        elif event_type == "GATE_READY":
            state["status"] = "GATE_READY"
            state["current_gate"] = payload.get("gate_id", state["current_gate"])
        elif event_type == "GATE_DECIDED":
            decision = payload.get("decision")
            if decision == "PASS":
                state["status"] = payload.get("status_after", "APPROVED")
            elif decision in {"BLOCK", "DEFER", "QUARANTINE", "SUPERSEDE"}:
                state["status"] = {
                    "BLOCK": "BLOCKED",
                    "DEFER": "BLOCKED",
                    "QUARANTINE": "QUARANTINED",
                    "SUPERSEDE": "SUPERSEDED",
                }[decision]
        elif event_type == "PR_MERGED":
            state["last_merge_commit"] = payload.get("merge_commit")
        elif event_type == "BLOCKER_OPENED":
            blocker_id = payload.get("blocker_id")
            if not blocker_id:
                raise ProjectionError("BLOCKER_OPENED requires blocker_id")
            blockers[blocker_id] = payload
            state["status"] = "BLOCKED"
        elif event_type == "BLOCKER_CLOSED":
            blocker_id = payload.get("blocker_id")
            blockers.pop(blocker_id, None)
        elif event_type == "PROGRAMME_COMPLETED":
            state["status"] = "COMPLETED"
            state["current_packet"] = None
            state["current_gate"] = None
        elif event_type == "PROGRAMME_SUPERSEDED":
            state["status"] = "SUPERSEDED"
        elif event_type in {"STATE_SOURCE_CONFLICT", "STALE_PROJECTION"}:
            state.setdefault("health_events", []).append(event_id)

        if event["authority_effect"] != "NONE":
            state["authority_events"].append(event_id)
        state["last_event_id"] = event_id

    state["blockers"] = [blockers[key] for key in sorted(blockers)]
    state["event_count"] = len(ordered)
    state["event_order"] = [event["event_id"] for event in ordered]
    state["projection_sha256"] = _canonical_digest({key: value for key, value in state.items() if key != "projection_sha256"})
    return state


def build_partitioned_projection(
    genesis_records: Iterable[Mapping[str, Any]],
    events: Iterable[Mapping[str, Any]],
    precedence: Mapping[str, int],
    class_partitions: Mapping[str, str],
) -> dict[str, Any]:
    records = [deepcopy(dict(record)) for record in genesis_records]
    identities = [record["programme_id"] for record in records]
    if len(identities) != len(set(identities)):
        raise ProjectionError("programme identity appears more than once across partitions")

    events_by_programme: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for event in events:
        events_by_programme[event["programme_id"]].append(event)
    unknown_events = sorted(set(events_by_programme).difference(identities))
    if unknown_events:
        raise ProjectionError(f"orphan programme events: {unknown_events}")

    partitions: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in sorted(records, key=lambda item: item["programme_id"]):
        class_id = record["programme_class"]
        if class_id not in class_partitions:
            raise ProjectionError(f"unregistered programme class: {class_id}")
        partition_id = class_partitions[class_id]
        projection = project_programme(record["programme_id"], events_by_programme[record["programme_id"]], precedence)
        projection["genesis_id"] = record["genesis_id"]
        projection["programme_class"] = class_id
        projection["partition_id"] = partition_id
        partitions[partition_id].append(projection)

    partition_rows = []
    for partition_id in sorted(partitions):
        rows = sorted(partitions[partition_id], key=lambda item: item["programme_id"])
        partition_rows.append(
            {
                "partition_id": partition_id,
                "programme_count": len(rows),
                "programmes": rows,
                "partition_sha256": _canonical_digest(rows),
            }
        )

    result = {
        "schema": "ovc-programme-portfolio-projection/v1",
        "partition_count": len(partition_rows),
        "programme_count": len(records),
        "partitions": partition_rows,
        "cross_partition_checks": {
            "unique_programme_identity": True,
            "no_orphan_events": True,
            "authority_effect_is_derived_only": True,
        },
    }
    result["portfolio_sha256"] = _canonical_digest(result)
    return result
