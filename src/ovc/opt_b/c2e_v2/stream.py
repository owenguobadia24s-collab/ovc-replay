"""Append-only semantic stream primitives for C2E v0.2."""
from __future__ import annotations

import copy
from typing import Any, Mapping

from .serialization import logical_stream_hash


class StreamError(ValueError):
    pass


_ID_BY_SCHEMA = {
    "c2e_episode_genesis/v0_2":"episode_id",
    "c2e_episode_snapshot/v0_2":"snapshot_id",
    "c2e_phase_segment/v0_2":"phase_segment_id",
    "c2e_boundary_event/v0_2":"boundary_event_id",
    "c2e_lineage_edge/v0_2":"lineage_edge_id",
    "c2e_membership_delta/v0_2":"membership_delta_id",
    "c2e_remap_record/v0_2":"remap_record_id",
    "c2e_stream_manifest/v0_2":"stream_manifest_id",
    "c2e_checkpoint/v0_2":"checkpoint_id",
    "c2e_sri_handoff/v0_1":"handoff_id",
}


class AppendOnlyStream:
    def __init__(self) -> None:
        self._records: list[dict[str, Any]] = []
        self._ids: set[str] = set()

    @staticmethod
    def _record_id(record: Mapping[str, Any]) -> str:
        field = _ID_BY_SCHEMA.get(str(record.get("schema", "")))
        if field is None or not isinstance(record.get(field), str):
            raise StreamError("SEMANTIC_RECORD_ID_NOT_FOUND")
        return str(record[field])

    def append(self, record: Mapping[str, Any]) -> None:
        item = copy.deepcopy(dict(record))
        record_id = self._record_id(item)
        if record_id in self._ids:
            raise StreamError("APPEND_ONLY_DUPLICATE_OR_UPDATE_DENIED")
        if item.get("authority") not in {"INACTIVE_NONCANONICAL_SHADOW","COMPARISON_ONLY"}:
            raise StreamError("STREAM_AUTHORITY_DENIED")
        self._records.append(item)
        self._ids.add(record_id)

    @property
    def records(self) -> list[dict[str, Any]]:
        return copy.deepcopy(self._records)

    @property
    def logical_hash(self) -> str:
        return logical_stream_hash(self._records)

    def update(self, *_args: Any, **_kwargs: Any) -> None:
        raise StreamError("APPEND_ONLY_UPDATE_DENIED")

    def delete(self, *_args: Any, **_kwargs: Any) -> None:
        raise StreamError("APPEND_ONLY_DELETE_DENIED")
