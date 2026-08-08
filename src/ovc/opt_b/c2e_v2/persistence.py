"""Deterministic compact persistence views for C2E v0.2 synthetic assurance.

This module never writes provider data or activates a boundary pack. It canonicalises
semantic record ordering so equivalent execution layouts and exact resharding reconcile.
"""
from __future__ import annotations

import copy
from collections import Counter
from types import MappingProxyType
from typing import Any, Mapping, Sequence

from .models import build_record
from .serialization import sha256_hex

_ID_FIELDS = {
    "c2e_episode_genesis/v0_2": "episode_id",
    "c2e_episode_snapshot/v0_2": "snapshot_id",
    "c2e_phase_segment/v0_2": "phase_segment_id",
    "c2e_boundary_event/v0_2": "boundary_event_id",
    "c2e_lineage_edge/v0_2": "lineage_edge_id",
    "c2e_membership_delta/v0_2": "membership_delta_id",
    "c2e_remap_record/v0_2": "remap_record_id",
}


class PersistenceError(ValueError):
    pass


def semantic_record_id(record: Mapping[str, Any]) -> str:
    schema = str(record.get("schema", ""))
    field = _ID_FIELDS.get(schema)
    if field is None or not isinstance(record.get(field), str):
        raise PersistenceError(f"SEMANTIC_RECORD_ID_NOT_FOUND:{schema}")
    return str(record[field])


def canonical_record_order(records: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    materialized = [copy.deepcopy(dict(item)) for item in records]
    for item in materialized:
        semantic_record_id(item)
        if not isinstance(item.get("logical_hash"), str):
            raise PersistenceError("LOGICAL_HASH_REQUIRED")
    return sorted(
        materialized,
        key=lambda item: (
            str(item.get("first_valid_time", "")),
            str(item.get("effective_time", item.get("birth_effective_time", item.get("as_of_time", "")))),
            str(item.get("schema", "")),
            semantic_record_id(item),
            str(item["logical_hash"]),
        ),
    )


def build_stream_manifest(
    records: Sequence[Mapping[str, Any]],
    *,
    source_binding: Mapping[str, Any],
    boundary_pack_id: str,
    schema_ids: Sequence[str],
    code_hashes: Sequence[str],
    missingness: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    ordered = canonical_record_order(records)
    counts = Counter(str(item["schema"]) for item in ordered)
    count_payload = {"attempted_records": len(ordered), "emitted_records": len(ordered)}
    count_payload.update({key: counts[key] for key in sorted(counts)})
    return build_record(
        "stream_manifest",
        {
            "source_binding": copy.deepcopy(dict(source_binding)),
            "boundary_pack_id": str(boundary_pack_id),
            "schema_ids": sorted({str(item) for item in schema_ids}),
            "code_hashes": sorted({str(item) for item in code_hashes}),
            "ordered_record_ids": [semantic_record_id(item) for item in ordered],
            "ordered_record_hashes": [str(item["logical_hash"]) for item in ordered],
            "counts": count_payload,
            "missingness": [copy.deepcopy(dict(item)) for item in (missingness or [])],
            "authority": "INACTIVE_NONCANONICAL_SHADOW",
        },
    )


def recombine_partitions(
    partitions: Mapping[str, Sequence[Mapping[str, Any]]],
    *,
    expected_partition_ids: Sequence[str],
    source_binding: Mapping[str, Any],
    boundary_pack_id: str,
    schema_ids: Sequence[str],
    code_hashes: Sequence[str],
) -> dict[str, Any]:
    """Recombine only an exact declared partition set (QA-23 synthetic primitive)."""
    expected = sorted({str(item) for item in expected_partition_ids})
    observed = sorted(str(item) for item in partitions)
    if observed != expected:
        raise PersistenceError("RECOVERY_PARTITION_SET_MISMATCH")
    flattened: list[Mapping[str, Any]] = []
    seen: set[str] = set()
    for partition_id in observed:
        for record in partitions[partition_id]:
            record_id = semantic_record_id(record)
            if record_id in seen:
                raise PersistenceError("RECOVERY_DUPLICATE_SEMANTIC_RECORD")
            seen.add(record_id)
            flattened.append(record)
    return build_stream_manifest(
        flattened,
        source_binding=source_binding,
        boundary_pack_id=boundary_pack_id,
        schema_ids=schema_ids,
        code_hashes=code_hashes,
    )


def semantic_prefix_hash(records: Sequence[Mapping[str, Any]]) -> str:
    ordered = canonical_record_order(records)
    return sha256_hex([str(item["logical_hash"]) for item in ordered])


def read_only_records(records: Sequence[Mapping[str, Any]]) -> tuple[Mapping[str, Any], ...]:
    """Expose detached immutable views; consumer mutation cannot touch source."""
    return tuple(MappingProxyType(copy.deepcopy(dict(item))) for item in canonical_record_order(records))
