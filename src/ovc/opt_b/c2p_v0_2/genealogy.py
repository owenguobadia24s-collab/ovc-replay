from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
from typing import Any, Iterable, Mapping, Sequence

from .canonical import canonical_bytes
from .events import build_event, event_record_hash
from .projection import project_assertion_stream


LINEAGE_SCHEMA = "c2p-lineage-edge/v0.2"
CORE_EDGE_TYPES = frozenset({"SPLIT_FROM", "MERGED_FROM", "RECURRENCE_OF", "NESTED_IN"})


class GenealogyError(ValueError):
    pass


def _hash(payload: Any) -> str:
    return sha256(canonical_bytes(payload)).hexdigest()


def _ordered(events: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    materialized = [deepcopy(dict(event)) for event in events]
    if not materialized:
        raise GenealogyError("C2P_GENEALOGY_STREAM_REQUIRED")
    return sorted(materialized, key=lambda event: (event["sequence_no"], event["event_id"]))


def _assertion_id(events: Sequence[Mapping[str, Any]]) -> str:
    return project_assertion_stream(events)["object_assertion_id"]


def _assertion_pack(events: Sequence[Mapping[str, Any]]) -> str:
    packs = {event["object_pack_id"] for event in events}
    if len(packs) != 1:
        raise GenealogyError("C2P_GENEALOGY_MULTI_PACK_STREAM")
    return next(iter(packs))


def _lineage_edge(
    *,
    edge_type: str,
    object_pack_id: str,
    parent_assertion_ids: Iterable[str],
    child_assertion_ids: Iterable[str],
    market_effective_time: str,
    first_valid_time: str,
    evaluation_cutoff: str,
    source_event_ids: Iterable[str],
) -> dict[str, Any]:
    if edge_type not in CORE_EDGE_TYPES:
        raise GenealogyError(f"C2P_GENEALOGY_EDGE_TYPE_UNSUPPORTED:{edge_type}")
    parents = sorted(set(parent_assertion_ids))
    children = sorted(set(child_assertion_ids))
    sources = sorted(set(source_event_ids))
    if not parents or not children or not sources:
        raise GenealogyError("C2P_GENEALOGY_EDGE_INCOMPLETE")
    if set(parents) & set(children):
        raise GenealogyError("C2P_GENEALOGY_IDENTITY_COLLAPSE")
    body = {
        "schema": LINEAGE_SCHEMA,
        "edge_type": edge_type,
        "object_pack_id": object_pack_id,
        "parent_assertion_ids": parents,
        "child_assertion_ids": children,
        "market_effective_time": market_effective_time,
        "first_valid_time": first_valid_time,
        "evaluation_cutoff": evaluation_cutoff,
        "source_event_ids": sources,
    }
    return {"edge_id": _hash(body), **body}


def _append_genealogy_event(
    events: Sequence[Mapping[str, Any]],
    object_pack: Mapping[str, Any],
    *,
    event_type: str,
    market_effective_time: str,
    first_valid_time: str,
    evaluation_cutoff: str,
    decision_id: str,
    source_hashes: Iterable[str],
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    frontier = events[-1]
    if _assertion_pack(events) != object_pack.get("object_pack_id"):
        raise GenealogyError("C2P_GENEALOGY_OBJECT_PACK_MISMATCH")
    return build_event(
        stream_id=_assertion_id(events),
        sequence_no=frontier["sequence_no"] + 1,
        event_type=event_type,
        object_pack=object_pack,
        market_effective_start=market_effective_time,
        market_effective_end=None,
        first_valid_time=first_valid_time,
        evaluation_cutoff=evaluation_cutoff,
        decision_id=decision_id,
        parent_event_ids=[frontier["event_id"]],
        source_hashes=source_hashes,
        payload=payload,
        prior_event_hash=event_record_hash(frontier),
    )


def split(
    parent_events: Iterable[Mapping[str, Any]],
    child_assertions: Iterable[Mapping[str, Any]],
    object_pack: Mapping[str, Any],
    *,
    parent_disposition: str,
    market_effective_time: str,
    first_valid_time: str,
    evaluation_cutoff: str,
    decision_id: str,
    source_hashes: Iterable[str],
) -> tuple[dict[str, Any], dict[str, Any]]:
    events = _ordered(parent_events)
    parent_id = _assertion_id(events)
    children = [dict(child) for child in child_assertions]
    child_ids = sorted({child["object_assertion_id"] for child in children})
    if len(child_ids) < 2 or len(child_ids) != len(children):
        raise GenealogyError("C2P_SPLIT_REQUIRES_DISTINCT_CHILDREN")
    if parent_id in child_ids:
        raise GenealogyError("C2P_SPLIT_CHILD_REUSES_PARENT_ID")
    if any(child.get("object_pack_id") != object_pack.get("object_pack_id") for child in children):
        raise GenealogyError("C2P_SPLIT_CHILD_PACK_MISMATCH")
    if parent_disposition not in {"ACTIVE", "RETIRED", "SUPERSEDED"}:
        raise GenealogyError("C2P_SPLIT_PARENT_DISPOSITION_INVALID")
    event = _append_genealogy_event(
        events,
        object_pack,
        event_type="SPLIT",
        market_effective_time=market_effective_time,
        first_valid_time=first_valid_time,
        evaluation_cutoff=evaluation_cutoff,
        decision_id=decision_id,
        source_hashes=source_hashes,
        payload={
            "parent_assertion_id": parent_id,
            "child_assertion_ids": child_ids,
            "parent_disposition": parent_disposition,
        },
    )
    edge = _lineage_edge(
        edge_type="SPLIT_FROM",
        object_pack_id=object_pack["object_pack_id"],
        parent_assertion_ids=[parent_id],
        child_assertion_ids=child_ids,
        market_effective_time=market_effective_time,
        first_valid_time=first_valid_time,
        evaluation_cutoff=evaluation_cutoff,
        source_event_ids=[event["event_id"]],
    )
    return event, edge


def merge(
    merged_events: Iterable[Mapping[str, Any]],
    parent_assertions: Iterable[Mapping[str, Any]],
    object_pack: Mapping[str, Any],
    *,
    parent_dispositions: Mapping[str, str],
    market_effective_time: str,
    first_valid_time: str,
    evaluation_cutoff: str,
    decision_id: str,
    source_hashes: Iterable[str],
) -> tuple[dict[str, Any], dict[str, Any]]:
    events = _ordered(merged_events)
    merged_id = _assertion_id(events)
    parents = [dict(parent) for parent in parent_assertions]
    parent_ids = sorted({parent["object_assertion_id"] for parent in parents})
    if len(parent_ids) < 2 or len(parent_ids) != len(parents):
        raise GenealogyError("C2P_MERGE_REQUIRES_DISTINCT_PARENTS")
    if merged_id in parent_ids:
        raise GenealogyError("C2P_MERGE_REUSES_PARENT_ID")
    if any(parent.get("object_pack_id") != object_pack.get("object_pack_id") for parent in parents):
        raise GenealogyError("C2P_MERGE_PARENT_PACK_MISMATCH")
    if set(parent_dispositions) != set(parent_ids):
        raise GenealogyError("C2P_MERGE_PARENT_DISPOSITIONS_INCOMPLETE")
    if any(value not in {"ACTIVE", "RETIRED", "SUPERSEDED"} for value in parent_dispositions.values()):
        raise GenealogyError("C2P_MERGE_PARENT_DISPOSITION_INVALID")
    event = _append_genealogy_event(
        events,
        object_pack,
        event_type="MERGE",
        market_effective_time=market_effective_time,
        first_valid_time=first_valid_time,
        evaluation_cutoff=evaluation_cutoff,
        decision_id=decision_id,
        source_hashes=source_hashes,
        payload={
            "merged_assertion_id": merged_id,
            "parent_assertion_ids": parent_ids,
            "parent_dispositions": {key: parent_dispositions[key] for key in parent_ids},
        },
    )
    edge = _lineage_edge(
        edge_type="MERGED_FROM",
        object_pack_id=object_pack["object_pack_id"],
        parent_assertion_ids=parent_ids,
        child_assertion_ids=[merged_id],
        market_effective_time=market_effective_time,
        first_valid_time=first_valid_time,
        evaluation_cutoff=evaluation_cutoff,
        source_event_ids=[event["event_id"]],
    )
    return event, edge


def recurrence(
    predecessor_events: Iterable[Mapping[str, Any]],
    successor_events: Iterable[Mapping[str, Any]],
    object_pack: Mapping[str, Any],
    *,
    market_effective_time: str,
    first_valid_time: str,
    evaluation_cutoff: str,
    decision_id: str,
    source_hashes: Iterable[str],
) -> tuple[dict[str, Any], dict[str, Any]]:
    predecessor = _ordered(predecessor_events)
    successor = _ordered(successor_events)
    predecessor_snapshot = project_assertion_stream(predecessor)
    successor_snapshot = project_assertion_stream(successor)
    if predecessor_snapshot["lifecycle_state"] not in {"RETIRED", "SUPERSEDED"}:
        raise GenealogyError("C2P_RECURRENCE_PREDECESSOR_NOT_TERMINAL")
    if successor_snapshot["lifecycle_state"] != "ACTIVE":
        raise GenealogyError("C2P_RECURRENCE_SUCCESSOR_NOT_ACTIVE")
    predecessor_id = predecessor_snapshot["object_assertion_id"]
    successor_id = successor_snapshot["object_assertion_id"]
    if predecessor_id == successor_id:
        raise GenealogyError("C2P_RECURRENCE_REUSES_PREDECESSOR_ID")
    if _assertion_pack(predecessor) != object_pack.get("object_pack_id") or _assertion_pack(successor) != object_pack.get("object_pack_id"):
        raise GenealogyError("C2P_RECURRENCE_PACK_MISMATCH")
    event = _append_genealogy_event(
        successor,
        object_pack,
        event_type="RECURRENCE_LINKED",
        market_effective_time=market_effective_time,
        first_valid_time=first_valid_time,
        evaluation_cutoff=evaluation_cutoff,
        decision_id=decision_id,
        source_hashes=source_hashes,
        payload={
            "predecessor_assertion_id": predecessor_id,
            "successor_assertion_id": successor_id,
            "continuity_claim": False,
        },
    )
    edge = _lineage_edge(
        edge_type="RECURRENCE_OF",
        object_pack_id=object_pack["object_pack_id"],
        parent_assertion_ids=[predecessor_id],
        child_assertion_ids=[successor_id],
        market_effective_time=market_effective_time,
        first_valid_time=first_valid_time,
        evaluation_cutoff=evaluation_cutoff,
        source_event_ids=[event["event_id"]],
    )
    return event, edge


def nested_in(
    parent_events: Iterable[Mapping[str, Any]],
    child_events: Iterable[Mapping[str, Any]],
    *,
    market_effective_time: str,
    first_valid_time: str,
    evaluation_cutoff: str,
) -> dict[str, Any]:
    parent = _ordered(parent_events)
    child = _ordered(child_events)
    parent_id = _assertion_id(parent)
    child_id = _assertion_id(child)
    if parent_id == child_id:
        raise GenealogyError("C2P_NESTING_IDENTITY_COLLAPSE")
    parent_pack = _assertion_pack(parent)
    if parent_pack != _assertion_pack(child):
        raise GenealogyError("C2P_NESTING_PACK_MISMATCH")
    return _lineage_edge(
        edge_type="NESTED_IN",
        object_pack_id=parent_pack,
        parent_assertion_ids=[parent_id],
        child_assertion_ids=[child_id],
        market_effective_time=market_effective_time,
        first_valid_time=first_valid_time,
        evaluation_cutoff=evaluation_cutoff,
        source_event_ids=[parent[-1]["event_id"], child[-1]["event_id"]],
    )
