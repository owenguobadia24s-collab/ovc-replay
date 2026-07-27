from __future__ import annotations

from copy import deepcopy
from decimal import Decimal, InvalidOperation
from typing import Any, Mapping


class HandoffError(ValueError):
    """Raised when a C1 parent is outside the frozen C2 input profile."""


_REQUIRED = {
    "c1_record_id",
    "c1_release_id",
    "c1_manifest_id",
    "opt_a_release_id",
    "opt_a_manifest_id",
    "opt_a_manifest_sha256",
    "role",
    "authority_state",
    "instrument",
    "clock",
    "side",
    "open_time",
    "close_time",
    "first_valid_time",
    "source_path",
    "source_bar_id",
    "measurements",
    "categorical",
    "null_reasons",
    "quality_state",
    "prices",
}
_ALLOWED_AUTHORITY = {
    "DISCOVERY": "ACTIVE_DISCOVERY",
    "DEVELOPMENT": "ACTIVE_DEVELOPMENT",
}
_ALLOWED_CLOCKS = {"15M", "2H_A_L"}
_ALLOWED_SIDES = {"BID", "ASK"}
_FORBIDDEN = {
    "future_outcome",
    "trade_label",
    "episode_id",
    "winning_state",
    "overall_state",
}
_MEASUREMENTS = {
    "range_abs",
    "range_ticks",
    "body_signed",
    "body_abs",
    "body_utilisation",
    "upper_wick_abs",
    "lower_wick_abs",
    "upper_wick_share",
    "lower_wick_share",
    "wick_balance",
    "open_location",
    "close_location",
    "signed_efficiency",
    "true_range_abs",
    "true_range_ticks",
    "close_change",
    "open_gap",
}
_PRICES = {"open", "high", "low", "close"}
_PROSPECTIVE_MODE = "TIME_GATED_REPLAY"
_PROSPECTIVE_AUTHORITY = "TIME_GATED_REPLAY_DERIVED"


def _decimalise(value: Any) -> str:
    try:
        return format(Decimal(str(value)), "f")
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise HandoffError("NON_DECIMAL_MEASUREMENT") from exc


def _common(record: Mapping[str, Any]) -> tuple[Mapping[str, Any], Mapping[str, Any]]:
    missing = sorted(_REQUIRED - set(record))
    if missing:
        raise HandoffError(f"MISSING_REQUIRED:{','.join(missing)}")
    leaked = sorted(_FORBIDDEN & set(record))
    if leaked:
        raise HandoffError(f"FORBIDDEN_FIELD:{','.join(leaked)}")
    if record["instrument"] != "GBPUSD":
        raise HandoffError("WRONG_INSTRUMENT")
    if record["clock"] not in _ALLOWED_CLOCKS:
        raise HandoffError("WRONG_CLOCK")
    if record["side"] not in _ALLOWED_SIDES:
        raise HandoffError("WRONG_SIDE")
    if not str(record["c1_record_id"]).startswith("c1:"):
        raise HandoffError("INVALID_C1_RECORD_ID")
    if record["first_valid_time"] < record["close_time"]:
        raise HandoffError("FIRST_VALID_BEFORE_CLOSE")
    measurements = record["measurements"]
    if not isinstance(measurements, Mapping) or set(measurements) != _MEASUREMENTS:
        raise HandoffError("MEASUREMENT_CARDINALITY")
    categorical = record["categorical"]
    if (
        not isinstance(categorical, Mapping)
        or categorical.get("direction") not in {"UP", "DOWN", "FLAT"}
    ):
        raise HandoffError("CATEGORICAL_CARDINALITY")
    prices = record["prices"]
    if not isinstance(prices, Mapping) or set(prices) != _PRICES:
        raise HandoffError("PRICE_PARENT_CARDINALITY")
    return measurements, prices


def _normalise(
    record: Mapping[str, Any],
    measurements: Mapping[str, Any],
    prices: Mapping[str, Any],
    *,
    status: str,
) -> dict[str, Any]:
    accepted = deepcopy(dict(record))
    accepted["measurements"] = {
        str(key): None if value is None else _decimalise(value)
        for key, value in sorted(measurements.items())
    }
    accepted["prices"] = {
        str(key): _decimalise(value)
        for key, value in sorted(prices.items())
    }
    accepted["handoff_status"] = status
    return accepted


def _accept_prospective(record: Mapping[str, Any]) -> dict[str, Any]:
    measurements, prices = _common(record)
    if record.get("operation_mode") != _PROSPECTIVE_MODE:
        raise HandoffError("PROSPECTIVE_OPERATION_MODE_REQUIRED")
    if record["role"] != "DISCOVERY":
        raise HandoffError("PROSPECTIVE_DISCOVERY_ROLE_REQUIRED")
    if record["authority_state"] != _PROSPECTIVE_AUTHORITY:
        raise HandoffError("PROSPECTIVE_AUTHORITY_MISMATCH")
    if not str(record["c1_release_id"]).startswith("RPS.C1SET."):
        raise HandoffError("PROSPECTIVE_C1_SET_ID_REQUIRED")
    if not str(record["c1_manifest_id"]).startswith("RPS.C1MANIFEST."):
        raise HandoffError("PROSPECTIVE_C1_MANIFEST_ID_REQUIRED")
    if not str(record["opt_a_release_id"]).startswith("RPS.PRICESET."):
        raise HandoffError("PROSPECTIVE_PRICE_SET_ID_REQUIRED")
    if not str(record["opt_a_manifest_id"]).startswith("RPS.SOURCE-MANIFEST."):
        raise HandoffError("PROSPECTIVE_SOURCE_MANIFEST_ID_REQUIRED")
    if not str(record["source_bar_id"]).startswith("rps-price:"):
        raise HandoffError("PROSPECTIVE_SOURCE_BAR_ID_REQUIRED")
    if record["first_valid_time"] != record["close_time"]:
        raise HandoffError("PROSPECTIVE_FIRST_VALID_MUST_EQUAL_CLOSE")
    if record["quality_state"] != "COMPLETE":
        raise HandoffError("PROSPECTIVE_INCOMPLETE_PARENT")
    if record.get("release_membership") is not False:
        raise HandoffError("PROSPECTIVE_RELEASE_MEMBERSHIP_DENIED")
    if record.get("selector_eligibility") != "NONE":
        raise HandoffError("PROSPECTIVE_SELECTOR_AUTHORITY_DENIED")
    if record.get("r2_publication") != "DENIED":
        raise HandoffError("PROSPECTIVE_R2_PUBLICATION_DENIED")
    if record.get("validation_consumption") != "DENIED":
        raise HandoffError("PROSPECTIVE_VALIDATION_CONSUMPTION_DENIED")
    if record.get("live_prospective_append") != "DENIED":
        raise HandoffError("PROSPECTIVE_LIVE_APPEND_DENIED")
    return _normalise(
        record,
        measurements,
        prices,
        status="ACCEPTED_RPS_TIME_GATED_REPLAY_WITH_EXACT_PRICE_PARENT",
    )


def accept_c1_record(record: Mapping[str, Any]) -> dict[str, Any]:
    if record.get("operation_mode") == _PROSPECTIVE_MODE:
        return _accept_prospective(record)
    measurements, prices = _common(record)
    role = str(record["role"])
    if role not in _ALLOWED_AUTHORITY:
        raise HandoffError("WRONG_ROLE")
    if record["authority_state"] != _ALLOWED_AUTHORITY[role]:
        raise HandoffError("WRONG_PARENT_AUTHORITY")
    if str(record["c1_release_id"]).startswith(("B-STATE", "OPT-A.")):
        raise HandoffError("LEGACY_PARENT")
    if not str(record["source_bar_id"]).startswith("opt-a:"):
        raise HandoffError("INVALID_OPT_A_SOURCE_BAR_ID")
    return _normalise(
        record,
        measurements,
        prices,
        status="ACCEPTED_ACTUAL_C1_WITH_EXACT_OPT_A_PRICE_PARENT",
    )
