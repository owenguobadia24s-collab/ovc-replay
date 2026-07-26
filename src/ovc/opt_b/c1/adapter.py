from __future__ import annotations

from datetime import datetime
from decimal import Decimal, InvalidOperation

from .models import SourceBar

ALLOWED_RELEASES = {
    "OPT-A.GBPUSD.DISCOVERY.2021_2023.v2",
    "OPT-A.GBPUSD.DEVELOPMENT.2024.v2",
    "OPT-A.GBPUSD.VALIDATION.2025.v2",
}
ALLOWED_CLOCKS = {"15M", "2H_A_L"}
ALLOWED_SIDES = {"BID", "ASK"}

class InputRejected(ValueError):
    pass


def _dt(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def adapt(payload: dict) -> SourceBar:
    required = (
        "release_id", "manifest_id", "research_role", "instrument_id", "clock_id", "price_side",
        "source_bar_id", "open_time", "close_time", "first_valid_time", "open", "high", "low", "close",
        "admissibility", "quality_state", "synthetic", "selector_state", "authority_state",
        "validation_consumption_state", "parent_source_object_ids", "parent_m1_bar_ids",
    )
    missing = [name for name in required if name not in payload]
    if missing:
        raise InputRejected(f"UPSTREAM_IDENTITY_UNRESOLVED:{','.join(missing)}")
    if payload["release_id"] not in ALLOWED_RELEASES:
        raise InputRejected("PROHIBITED_PARENT_RELEASE")
    if payload["instrument_id"] != "GBPUSD":
        raise InputRejected("INSTRUMENT_NOT_AUTHORISED")
    if payload["clock_id"] not in ALLOWED_CLOCKS:
        raise InputRejected("CONTROL_CLOCK_NOT_AUTHORISED")
    if payload["price_side"] not in ALLOWED_SIDES:
        raise InputRejected("PRICE_SIDE_NOT_AUTHORISED")
    if payload["admissibility"] != "HANDOFF_ELIGIBLE":
        raise InputRejected("SOURCE_BAR_INADMISSIBLE")
    if payload["research_role"] == "VALIDATION" and payload["validation_consumption_state"] == "LOCKED_UNCONSUMED":
        raise InputRejected("VALIDATION_LOCKED")
    if not payload["synthetic"] and (payload["selector_state"] != "ACTIVE" or not str(payload["authority_state"]).startswith("ACTIVE_")):
        raise InputRejected("UPSTREAM_SELECTOR_NOT_ACTIVE")
    try:
        o, h, l, c = (Decimal(str(payload[name])) for name in ("open", "high", "low", "close"))
        increment = payload.get("price_increment")
        pi = Decimal(str(increment)) if increment not in (None, "") else None
    except InvalidOperation as exc:
        raise InputRejected("INVALID_DECIMAL") from exc
    if h < max(o, c) or l > min(o, c) or h < l:
        raise InputRejected("INVALID_OHLC_ORDER")
    if pi is not None and pi <= 0:
        raise InputRejected("INVALID_PRICE_INCREMENT")
    if _dt(payload["close_time"]) <= _dt(payload["open_time"]):
        raise InputRejected("INVALID_INTERVAL")
    if _dt(payload["first_valid_time"]) > _dt(payload["close_time"]):
        raise InputRejected("FUTURE_FIRST_VALID_TIME")
    return SourceBar(
        release_id=payload["release_id"], manifest_id=payload["manifest_id"], research_role=payload["research_role"],
        instrument_id=payload["instrument_id"], clock_id=payload["clock_id"], price_side=payload["price_side"],
        source_bar_id=payload["source_bar_id"], open_time=payload["open_time"], close_time=payload["close_time"],
        first_valid_time=payload["first_valid_time"], open=o, high=h, low=l, close=c, price_increment=pi,
        admissibility=payload["admissibility"], quality_state=payload["quality_state"], synthetic=bool(payload["synthetic"]),
        selector_state=payload["selector_state"], authority_state=payload["authority_state"],
        validation_consumption_state=payload["validation_consumption_state"],
        parent_source_object_ids=tuple(payload["parent_source_object_ids"]), parent_m1_bar_ids=tuple(payload["parent_m1_bar_ids"]),
    )
