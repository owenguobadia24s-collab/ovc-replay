from __future__ import annotations

from decimal import Decimal
from typing import Any, Iterable, Mapping

from .adapter import accept_c1_record
from .identity import stable_id

_LEVEL_SOURCES = {"RANGE_LOW": "range_low", "RANGE_HIGH": "range_high", "SWING_LOW": "swing_low", "SWING_HIGH": "swing_high"}


def build_levels(record: Mapping[str, Any], level_types: Iterable[str] | None = None) -> list[dict[str, Any]]:
    parent = accept_c1_record(record)
    requested = tuple(level_types or _LEVEL_SOURCES)
    results: list[dict[str, Any]] = []
    for level_type in requested:
        if level_type not in _LEVEL_SOURCES:
            raise ValueError(f"UNKNOWN_LEVEL_TYPE:{level_type}")
        source = _LEVEL_SOURCES[level_type]
        if source not in parent["measurements"]:
            results.append({"level_type": level_type, "status": "EXCLUDED", "reason_code": "MISSING_MEASUREMENT"})
            continue
        value = format(Decimal(parent["measurements"][source]), "f")
        identity = {"type": level_type, "value": value, "c1_record_id": parent["c1_record_id"], "first_valid_time": parent["first_valid_time"], "clock": parent["clock"], "side": parent["side"]}
        results.append({"c2_level_id": stable_id("c2-level", identity), "level_type": level_type, "value": value, "status": "ACTIVE", "first_valid_time": parent["first_valid_time"], "clock": parent["clock"], "side": parent["side"], "parent_c1_record_id": parent["c1_record_id"]})
    return results
