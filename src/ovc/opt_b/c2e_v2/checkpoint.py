"""Replaceable checkpoint helpers for deterministic C2E v0.2 restart assurance."""
from __future__ import annotations

from typing import Any, Mapping, Sequence

from .models import build_record
from .persistence import semantic_prefix_hash


class CheckpointError(ValueError):
    pass


def create_checkpoint(
    manifest: Mapping[str, Any],
    *,
    completed_partitions: Sequence[str],
    logical_cursor: str,
    semantic_prefix_records: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    manifest_id = manifest.get("stream_manifest_id")
    if not isinstance(manifest_id, str):
        raise CheckpointError("STREAM_MANIFEST_ID_REQUIRED")
    return build_record(
        "checkpoint",
        {
            "stream_manifest_id": manifest_id,
            "completed_partitions": sorted({str(item) for item in completed_partitions}),
            "logical_cursor": str(logical_cursor),
            "semantic_prefix_hash": semantic_prefix_hash(semantic_prefix_records),
            "replaceable": True,
            "authority": "OPERATIONAL_NON_SEMANTIC",
        },
    )


def verify_resume(
    checkpoint: Mapping[str, Any],
    manifest: Mapping[str, Any],
    semantic_prefix_records: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    if checkpoint.get("stream_manifest_id") != manifest.get("stream_manifest_id"):
        raise CheckpointError("RESTART_BINDING_MISMATCH")
    observed = semantic_prefix_hash(semantic_prefix_records)
    if checkpoint.get("semantic_prefix_hash") != observed:
        raise CheckpointError("RESTART_LOGICAL_DIVERGENCE")
    return {
        "status": "PASS",
        "checkpoint_id": checkpoint.get("checkpoint_id"),
        "stream_manifest_id": manifest.get("stream_manifest_id"),
        "semantic_prefix_hash": observed,
        "authority_effect": "NONE",
    }
