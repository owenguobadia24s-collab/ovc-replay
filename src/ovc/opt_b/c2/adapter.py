from __future__ import annotations

from copy import deepcopy
from decimal import Decimal, InvalidOperation
from typing import Any, Mapping


class HandoffError(ValueError):
    """Raised when a C1 parent is outside the frozen C2 input profile."""


_REQUIRED = {
    "c1_record_id", "c1_release_id", "c1_manifest_id", "opt_a_release_id",
    "opt_a_manifest_id", "role", "authority_state", "instrument", "clock",
    "side", "close_time", "first_valid_time", "measurements", "quality_state",
}
_ALLOWED_AUTHORITY = {"DISCOVERY": "ACTIVE_DISCOVERY", "DEVELOPMENT": "ACTIVE_DEVELOPMENT"}
_ALLOWED_CLOCKS = {"15M", "2H_A_L"}
_ALLOWED_SIDES = {"BID", "ASK"}
_FORBIDDEN = {"future_outcome", "trade_label", "episode_id", "winning_state", "overall_state"}


def _decimalise(value: Any) -> str:
    try:
        return format(Decimal(str(value)), "f")
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise HandoffError("NON_DECIMAL_MEASUREMENT") from exc


def accept_c1_record(record: Mapping[str, Any]) -> dict[str, Any]:
    missing = sorted(_REQUIRED - set(record))
    if missing:
        raise HandoffError(f"MISSING_REQUIRED:{','.join(missing)}")
    leaked = sorted(_FORBIDDEN & set(record))
    if leaked:
        raise HandoffError(f"FORBIDDEN_FIELD:{','.join(leaked)}")
    role = str(record["role"])
    if role not in _ALLOWED_AUTHORITY:
        raise HandoffError("WRONG_ROLE")
    if record["authority_state"] != _ALLOWED_AUTHORITY[role]:
        raise HandoffError("WRONG_PARENT_AUTHORITY")
    if record["instrument"] != "GBPUSD":
        raise HandoffError("WRONG_INSTRUMENT")
    if record["clock"] not in _ALLOWED_CLOCKS:
        raise HandoffError("WRONG_CLOCK")
    if record["side"] not in _ALLOWED_SIDES:
        raise HandoffError("WRONG_SIDE")
    if str(record["c1_release_id"]).startswith(("B-STATE", "OPT-A.")):
        raise HandoffError("LEGACY_PARENT")
    if record["first_valid_time"] < record["close_time"]:
        raise HandoffError("FIRST_VALID_BEFORE_CLOSE")
    measurements = record["measurements"]
    if not isinstance(measurements, Mapping) or len(measurements) != 18:
        raise HandoffError("MEASUREMENT_CARDINALITY")
    accepted = deepcopy(dict(record))
    accepted["measurements"] = {str(k): _decimalise(v) for k, v in sorted(measurements.items())}
    accepted["handoff_status"] = "ACCEPTED_C1_V2"
    return accepted
