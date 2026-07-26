from __future__ import annotations

from decimal import Decimal
from typing import Any, Mapping

from .adapter import accept_c1_record
from .identity import stable_id


def build_containers(record: Mapping[str, Any]) -> list[dict[str, Any]]:
    parent = accept_c1_record(record)
    m = parent["measurements"]
    specs = [
        ("LOCAL_RANGE", "range_low", "range_high", "LOCAL_CLOCK"),
        ("SWING_ENVELOPE", "swing_low", "swing_high", "DECLARED_SCOPE"),
    ]
    containers: list[dict[str, Any]] = []
    for kind, low_key, high_key, scale in specs:
        if low_key not in m or high_key not in m:
            containers.append({"container_type": kind, "status": "EXCLUDED", "reason_code": "MISSING_BOUNDARY"})
            continue
        low, high = Decimal(m[low_key]), Decimal(m[high_key])
        if low > high:
            containers.append({"container_type": kind, "status": "CONFLICT", "reason_code": "INVERTED_BOUNDARY"})
            continue
        ident = {"type": kind, "low": low, "high": high, "scope": scale, "c1_record_id": parent["c1_record_id"], "first_valid_time": parent["first_valid_time"]}
        containers.append({"c2_container_id": stable_id("c2-container", ident), "container_type": kind, "scale": scale, "low": format(low,"f"), "high": format(high,"f"), "status": "ACTIVE", "first_valid_time": parent["first_valid_time"], "parent_c1_record_id": parent["c1_record_id"]})
    return containers
