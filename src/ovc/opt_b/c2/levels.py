from __future__ import annotations

from decimal import Decimal
from typing import Any, Iterable, Mapping, Sequence

from .adapter import accept_c1_record
from .identity import stable_id

PARAMETER_PACK_ID = "C2.PARAMS.GBPUSD.DISCOVERY.v0.1"
_PARAMS = {
    "15M": {"range": 32, "left": 4, "right": 4},
    "2H_A_L": {"range": 24, "left": 3, "right": 3},
}
_LEVEL_TYPES = ("SWING_HIGH", "SWING_LOW", "RANGE_HIGH", "RANGE_LOW", "MIDPOINT")


def _excluded(level_type: str, reason: str, parent: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "level_type": level_type,
        "status": "EXCLUDED",
        "reason_code": reason,
        "clock": parent["clock"],
        "side": parent["side"],
    }


def _active(
    *,
    level_type: str,
    value: Decimal,
    first_valid_time: str,
    parent: Mapping[str, Any],
    source_records: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    source_ids = [item["c1_record_id"] for item in source_records]
    identity = {
        "type_id": level_type,
        "clock": parent["clock"],
        "price_side": parent["side"],
        "source_record_ids": source_ids,
        "first_valid_time": first_valid_time,
        "parameter_pack_id": PARAMETER_PACK_ID,
        "value": value,
    }
    return {
        "c2_level_id": stable_id("c2-level", identity),
        "level_type": level_type,
        "value": format(value, "f"),
        "status": "ACTIVE",
        "first_valid_time": first_valid_time,
        "clock": parent["clock"],
        "side": parent["side"],
        "source_c1_record_ids": source_ids,
        "parent_c1_record_id": parent["c1_record_id"],
        "parameter_pack_id": PARAMETER_PACK_ID,
    }


def _latest_swing(
    history: Sequence[Mapping[str, Any]],
    *,
    kind: str,
    left: int,
    right: int,
    parent: Mapping[str, Any],
) -> dict[str, Any] | None:
    price_field = "high" if kind == "SWING_HIGH" else "low"
    for center in range(len(history) - right - 1, left - 1, -1):
        window = history[center - left : center + right + 1]
        values = [Decimal(str(item["prices"][price_field])) for item in window]
        candidate = values[left]
        other = values[:left] + values[left + 1 :]
        confirmed = candidate > max(other) if kind == "SWING_HIGH" else candidate < min(other)
        if confirmed:
            return _active(
                level_type=kind,
                value=candidate,
                first_valid_time=str(window[-1]["first_valid_time"]),
                parent=parent,
                source_records=window,
            )
    return None


def build_levels(
    record: Mapping[str, Any],
    history: Sequence[Mapping[str, Any]] | None = None,
    level_types: Iterable[str] | None = None,
) -> list[dict[str, Any]]:
    parent = accept_c1_record(record)
    accepted_history = [accept_c1_record(item) for item in (history or [parent])]
    if accepted_history[-1]["c1_record_id"] != parent["c1_record_id"]:
        raise ValueError("HISTORY_CURRENT_RECORD_MISMATCH")
    if any(
        (item["clock"], item["side"], item["c1_release_id"])
        != (parent["clock"], parent["side"], parent["c1_release_id"])
        for item in accepted_history
    ):
        raise ValueError("MIXED_LEVEL_HISTORY_SCOPE")

    params = _PARAMS[parent["clock"]]
    requested = tuple(level_types or _LEVEL_TYPES)
    unknown = sorted(set(requested) - set(_LEVEL_TYPES))
    if unknown:
        raise ValueError(f"UNKNOWN_LEVEL_TYPE:{','.join(unknown)}")

    built: dict[str, dict[str, Any]] = {}
    if len(accepted_history) >= params["range"]:
        window = accepted_history[-params["range"] :]
        high = max(Decimal(item["prices"]["high"]) for item in window)
        low = min(Decimal(item["prices"]["low"]) for item in window)
        built["RANGE_HIGH"] = _active(
            level_type="RANGE_HIGH",
            value=high,
            first_valid_time=parent["first_valid_time"],
            parent=parent,
            source_records=window,
        )
        built["RANGE_LOW"] = _active(
            level_type="RANGE_LOW",
            value=low,
            first_valid_time=parent["first_valid_time"],
            parent=parent,
            source_records=window,
        )
        built["MIDPOINT"] = _active(
            level_type="MIDPOINT",
            value=(high + low) / Decimal("2"),
            first_valid_time=parent["first_valid_time"],
            parent=parent,
            source_records=window,
        )
    else:
        for level_type in ("RANGE_HIGH", "RANGE_LOW", "MIDPOINT"):
            built[level_type] = _excluded(level_type, "WINDOW_NOT_COMPLETE", parent)

    for level_type in ("SWING_HIGH", "SWING_LOW"):
        swing = _latest_swing(
            accepted_history,
            kind=level_type,
            left=params["left"],
            right=params["right"],
            parent=parent,
        )
        built[level_type] = swing or _excluded(level_type, "NO_CONFIRMED_SWING", parent)

    return [built[level_type] for level_type in requested]
