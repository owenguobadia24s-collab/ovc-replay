from __future__ import annotations

from typing import Any, Mapping

from .models import OccurrenceAnchorRef


def anchor_from_mapping(value: Mapping[str, Any]) -> OccurrenceAnchorRef:
    required = ("anchor_kind", "anchor_id", "anchor_schema_id", "anchor_logical_hash", "anchor_first_valid_time")
    missing = [field for field in required if not value.get(field)]
    if missing:
        raise ValueError("OC_AVAIL_ANCHOR_MISSING:" + ",".join(missing))
    return OccurrenceAnchorRef(
        anchor_kind=str(value["anchor_kind"]),
        anchor_id=str(value["anchor_id"]),
        anchor_schema_id=str(value["anchor_schema_id"]),
        anchor_logical_hash=str(value["anchor_logical_hash"]),
        anchor_first_valid_time=str(value["anchor_first_valid_time"]),
        source_release_id=value.get("source_release_id"),
        structural_anchor_ref=value.get("structural_anchor_ref"),
    )
