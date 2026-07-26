from __future__ import annotations

from decimal import Decimal
from typing import Any, Iterable, Mapping

from .identity import stable_id


def build_relation_set(record: Mapping[str, Any], levels: Iterable[Mapping[str, Any]], containers: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    close = Decimal(str(record["measurements"]["close"]))
    relations: list[dict[str, Any]] = []
    exclusions: list[dict[str, Any]] = []
    for level in levels:
        if level.get("status") != "ACTIVE":
            exclusions.append({"subject": level.get("level_type"), "reason_code": level.get("reason_code", "INELIGIBLE_LEVEL")})
            continue
        value = Decimal(str(level["value"]))
        signed = close - value
        relation = "AT" if signed == 0 else ("ABOVE" if signed > 0 else "BELOW")
        relations.append({"level_id": level["c2_level_id"], "relation_type": relation, "signed_distance": format(signed, "f"), "side": record["side"]})
    for container in containers:
        if container.get("status") != "ACTIVE":
            exclusions.append({"subject": container.get("container_type"), "reason_code": container.get("reason_code", "INELIGIBLE_CONTAINER")})
            continue
        low, high = Decimal(str(container["low"])), Decimal(str(container["high"]))
        relation = "INSIDE" if low <= close <= high else ("ABOVE" if close > high else "BELOW")
        relations.append({"container_id": container["c2_container_id"], "relation_type": relation, "side": record["side"]})
    payload = {"c1_record_id": record["c1_record_id"], "scope": record["clock"], "relations": relations, "exclusions": exclusions}
    return {"c2_relation_set_id": stable_id("c2-relset", payload), **payload, "complete_inventory": True}
