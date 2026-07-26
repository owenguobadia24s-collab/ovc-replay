from __future__ import annotations

from decimal import Decimal
from typing import Any, Iterable, Mapping

from .adapter import accept_c1_record
from .identity import stable_id
from .levels import PARAMETER_PACK_ID


def _by_type(levels: Iterable[Mapping[str, Any]]) -> dict[str, Mapping[str, Any]]:
    return {
        str(item["level_type"]): item
        for item in levels
        if item.get("status") == "ACTIVE"
    }


def _container(
    *,
    parent: Mapping[str, Any],
    container_type: str,
    scale: str,
    low: Mapping[str, Any] | None,
    high: Mapping[str, Any] | None,
) -> dict[str, Any]:
    if low is None or high is None:
        return {
            "container_type": container_type,
            "status": "EXCLUDED",
            "reason_code": "MISSING_FIRST_VALID_BOUNDARY",
            "scale": scale,
        }
    low_value = Decimal(str(low["value"]))
    high_value = Decimal(str(high["value"]))
    if low_value > high_value:
        return {
            "container_type": container_type,
            "status": "CONFLICT",
            "reason_code": "INVERTED_BOUNDARY",
            "scale": scale,
        }
    first_valid_time = max(str(low["first_valid_time"]), str(high["first_valid_time"]))
    boundary_ids = [str(low["c2_level_id"]), str(high["c2_level_id"])]
    identity = {
        "type": container_type,
        "low": low_value,
        "high": high_value,
        "scale": scale,
        "boundary_ids": boundary_ids,
        "first_valid_time": first_valid_time,
        "parameter_pack_id": PARAMETER_PACK_ID,
    }
    return {
        "c2_container_id": stable_id("c2-container", identity),
        "container_type": container_type,
        "scale": scale,
        "low": format(low_value, "f"),
        "high": format(high_value, "f"),
        "status": "ACTIVE",
        "first_valid_time": first_valid_time,
        "boundary_level_ids": boundary_ids,
        "parent_c1_record_id": parent["c1_record_id"],
        "parameter_pack_id": PARAMETER_PACK_ID,
    }


def build_containers(
    record: Mapping[str, Any],
    levels: Iterable[Mapping[str, Any]],
    parent_levels: Iterable[Mapping[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    parent = accept_c1_record(record)
    local = _by_type(levels)
    upper = _by_type(parent_levels or ())
    return [
        _container(
            parent=parent,
            container_type="LOCAL_RANGE",
            scale="LOCAL_CLOCK",
            low=local.get("RANGE_LOW"),
            high=local.get("RANGE_HIGH"),
        ),
        _container(
            parent=parent,
            container_type="PARENT_RANGE",
            scale="PARENT_CLOCK",
            low=upper.get("RANGE_LOW"),
            high=upper.get("RANGE_HIGH"),
        ),
        _container(
            parent=parent,
            container_type="SWING_ENVELOPE",
            scale="DECLARED_SCOPE",
            low=local.get("SWING_LOW"),
            high=local.get("SWING_HIGH"),
        ),
    ]
