from __future__ import annotations

from decimal import Decimal
from typing import Any, Mapping

from .adapter import accept_c1_record
from .containers import build_containers
from .levels import build_levels
from .relations import build_relation_set
from .identity import stable_id

AXES = ("LOCATION", "MOTION", "ORGANISATION", "INTERACTION", "QUALITY")


def _axis(value: str, *, reason: str | None = None) -> dict[str, Any]:
    out = {"status": "EVALUATED", "value": value}
    if reason:
        out["reason_code"] = reason
    return out


def build_parallel_state(record: Mapping[str, Any]) -> dict[str, Any]:
    parent = accept_c1_record(record)
    levels = build_levels(parent)
    containers = build_containers(parent)
    relation_set = build_relation_set(parent, levels, containers)
    m = parent["measurements"]
    close = Decimal(m["close"])
    open_ = Decimal(m.get("open", m["close"]))
    high = Decimal(m.get("high", m["close"]))
    low = Decimal(m.get("low", m["close"]))
    active_containers = [c for c in containers if c.get("status") == "ACTIVE"]
    location = "UNCONTAINED"
    if active_containers:
        c = active_containers[0]
        cl, ch = Decimal(c["low"]), Decimal(c["high"])
        location = "INSIDE" if cl <= close <= ch else ("ABOVE" if close > ch else "BELOW")
    motion = "UP" if close > open_ else ("DOWN" if close < open_ else "FLAT")
    organisation = "EXPANDED" if high - low > Decimal(m.get("prior_range", "0")) else "NOT_EXPANDED"
    interaction = "AT_LEVEL" if any(r.get("relation_type") == "AT" for r in relation_set["relations"]) else "NO_EXACT_TOUCH"
    quality = "CONFLICT" if any(c.get("status") == "CONFLICT" for c in containers) else "VALID"
    axes = {
        "LOCATION": _axis(location),
        "MOTION": _axis(motion),
        "ORGANISATION": _axis(organisation),
        "INTERACTION": _axis(interaction),
        "QUALITY": _axis(quality),
    }
    identity = {
        "c1_record_id": parent["c1_record_id"],
        "first_valid_time": parent["first_valid_time"],
        "clock": parent["clock"],
        "side": parent["side"],
        "axes": axes,
    }
    return {
        "c2_state_id": stable_id("c2-state", identity),
        "parent_c1_record_id": parent["c1_record_id"],
        "first_valid_time": parent["first_valid_time"],
        "clock": parent["clock"],
        "side": parent["side"],
        "axes": axes,
        "level_ids": [x["c2_level_id"] for x in levels if x.get("status") == "ACTIVE"],
        "container_ids": [x["c2_container_id"] for x in containers if x.get("status") == "ACTIVE"],
        "relation_set_id": relation_set["c2_relation_set_id"],
    }
