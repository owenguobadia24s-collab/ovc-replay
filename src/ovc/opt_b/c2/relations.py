from __future__ import annotations

from decimal import Decimal
from typing import Any, Iterable, Mapping

from .adapter import accept_c1_record
from .identity import stable_id
from .levels import PARAMETER_PACK_ID

_PROXIMITY = {"15M": Decimal("0.10"), "2H_A_L": Decimal("0.08")}
_CROSSING_EPSILON = {"15M": Decimal("0.02"), "2H_A_L": Decimal("0.015")}


def build_relation_set(
    record: Mapping[str, Any],
    levels: Iterable[Mapping[str, Any]],
    containers: Iterable[Mapping[str, Any]],
    previous_record: Mapping[str, Any] | None = None,
    *,
    evaluation_scope_id: str | None = None,
) -> dict[str, Any]:
    parent = accept_c1_record(record)
    previous = accept_c1_record(previous_record) if previous_record is not None else None
    close = Decimal(parent["prices"]["close"])
    prior_close = Decimal(previous["prices"]["close"]) if previous is not None else None
    level_items = list(levels)
    container_items = list(containers)
    local = next(
        (
            item
            for item in container_items
            if item.get("container_type") == "LOCAL_RANGE" and item.get("status") == "ACTIVE"
        ),
        None,
    )
    local_scale = (
        Decimal(str(local["high"])) - Decimal(str(local["low"]))
        if local is not None
        else Decimal(parent["measurements"]["range_abs"])
    )
    proximity = local_scale * _PROXIMITY[parent["clock"]]
    epsilon = local_scale * _CROSSING_EPSILON[parent["clock"]]

    relations: list[dict[str, Any]] = []
    exclusions: list[dict[str, Any]] = []
    for level in level_items:
        if level.get("status") != "ACTIVE":
            exclusions.append(
                {
                    "subject_type": "LEVEL",
                    "subject": level.get("level_type"),
                    "reason_code": level.get("reason_code", "RELATION_EXCLUDED"),
                }
            )
            continue
        value = Decimal(str(level["value"]))
        signed = close - value
        normalized = signed / local_scale if local_scale else Decimal("0")
        relation_type = "AT_LEVEL" if abs(signed) <= proximity else ("ABOVE_LEVEL" if signed > 0 else "BELOW_LEVEL")
        if prior_close is not None:
            previous_signed = prior_close - value
            if previous_signed < -epsilon and signed > epsilon:
                relation_type = "CROSSED_UP"
            elif previous_signed > epsilon and signed < -epsilon:
                relation_type = "CROSSED_DOWN"
        relations.append(
            {
                "level_id": level["c2_level_id"],
                "level_type": level["level_type"],
                "relation_type": relation_type,
                "signed_distance": format(signed, "f"),
                "normalized_proximity": format(normalized, "f"),
                "proximity_threshold": format(proximity, "f"),
                "side": parent["side"],
                "first_valid_time": parent["first_valid_time"],
            }
        )
    for container in container_items:
        if container.get("status") != "ACTIVE":
            exclusions.append(
                {
                    "subject_type": "CONTAINER",
                    "subject": container.get("container_type"),
                    "reason_code": container.get("reason_code", "RELATION_EXCLUDED"),
                }
            )
            continue
        low = Decimal(str(container["low"]))
        high = Decimal(str(container["high"]))
        inside = low <= close <= high
        relations.append(
            {
                "container_id": container["c2_container_id"],
                "container_type": container["container_type"],
                "relation_type": "INSIDE_CONTAINER" if inside else "OUTSIDE_CONTAINER",
                "side": parent["side"],
                "first_valid_time": parent["first_valid_time"],
            }
        )
    payload = {
        "c1_record_id": parent["c1_record_id"],
        "scope": evaluation_scope_id or parent["clock"],
        "relations": relations,
        "exclusions": exclusions,
        "parameter_pack_id": PARAMETER_PACK_ID,
    }
    return {
        "c2_relation_set_id": stable_id("c2-relset", payload),
        **payload,
        "complete_inventory": True,
    }
