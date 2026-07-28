from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any, Iterable, Mapping

ALLOWED_ROLES = {"DISCOVERY", "DEVELOPMENT"}
ALLOWED_CLOCKS = {"15M", "2H_A_L"}
ALLOWED_SIDES = {"BID", "ASK"}
ALLOWED_NULL_REASONS = {
    "ZERO_RANGE",
    "NO_PRIOR_BAR",
    "NO_CONTIGUOUS_PRIOR_BAR",
    "PRIOR_IDENTITY_MISMATCH",
    "PRIOR_NOT_FIRST_VALID",
    "PRICE_INCREMENT_UNAVAILABLE",
    "SOURCE_BAR_INADMISSIBLE",
    "CONTROL_CLOCK_NOT_AUTHORISED",
    "VALIDATION_LOCKED",
    "UPSTREAM_IDENTITY_UNRESOLVED",
}
ZERO_RANGE_NULL_FIELDS = {
    "body_utilisation",
    "upper_wick_share",
    "lower_wick_share",
    "wick_balance",
    "open_location",
    "close_location",
    "signed_efficiency",
}
ZERO_RANGE_ABSOLUTE_FIELDS = {
    "range_abs",
    "body_signed",
    "body_abs",
    "upper_wick_abs",
    "lower_wick_abs",
}
PRIOR_FIELDS = {"true_range_abs", "true_range_ticks", "close_change", "open_gap"}
_INVALID_NUMERIC_STRINGS = {
    "", "nan", "+nan", "-nan", "infinity", "+infinity", "-infinity",
    "inf", "+inf", "-inf", "null", "none", "-999", "999999",
}


class ComputabilityContractError(ValueError):
    """Raised when C1 computability evidence violates the frozen contract."""


class ComputabilityAccessDenied(ComputabilityContractError):
    """Raised before Validation or other forbidden content can be resolved."""


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _parse_time(value: Any, field: str) -> datetime:
    if not isinstance(value, str) or not value:
        raise ComputabilityContractError(f"{field} must be a non-empty UTC timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ComputabilityContractError(f"invalid {field}: {value}") from exc
    if parsed.tzinfo is None:
        raise ComputabilityContractError(f"{field} must include timezone")
    return parsed.astimezone(timezone.utc)


def _decimal(value: Any, field: str) -> Decimal:
    if isinstance(value, bool) or value is None:
        raise ComputabilityContractError(f"{field} is not a Decimal value")
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ComputabilityContractError(f"invalid Decimal for {field}") from exc
    if not result.is_finite():
        raise ComputabilityContractError(f"non-finite Decimal for {field}")
    return result


def _validate_measurement_value(field: str, value: Any) -> None:
    if value is None:
        return
    if not isinstance(value, str):
        raise ComputabilityContractError(f"measurement {field} must be canonical Decimal string or null")
    if value.strip().lower() in _INVALID_NUMERIC_STRINGS:
        raise ComputabilityContractError(f"measurement {field} contains prohibited sentinel/non-finite value")
    _decimal(value, field)


def _source_rejection_reason(source: Mapping[str, Any]) -> str | None:
    role = source.get("research_role")
    if role == "VALIDATION":
        return "VALIDATION_LOCKED"
    if role not in ALLOWED_ROLES:
        return "SOURCE_BAR_INADMISSIBLE"
    if source.get("clock_id") not in ALLOWED_CLOCKS:
        return "CONTROL_CLOCK_NOT_AUTHORISED"
    if source.get("price_side") not in ALLOWED_SIDES:
        return "SOURCE_BAR_INADMISSIBLE"
    if source.get("admissibility") != "HANDOFF_ELIGIBLE":
        return "SOURCE_BAR_INADMISSIBLE"
    if not source.get("lineage_resolved", True):
        return "UPSTREAM_IDENTITY_UNRESOLVED"
    required_identity = ("release_id", "manifest_id", "instrument_id", "source_bar_id")
    if any(not source.get(field) for field in required_identity):
        return "UPSTREAM_IDENTITY_UNRESOLVED"
    return None


def _prior_status(source: Mapping[str, Any], prior: Mapping[str, Any] | None) -> tuple[str, str | None]:
    if prior is None:
        return "NOT_COMPUTABLE", "NO_PRIOR_BAR"
    identity_fields = ("release_id", "manifest_id", "instrument_id", "clock_id", "price_side")
    if any(source.get(field) != prior.get(field) for field in identity_fields):
        return "NOT_COMPUTABLE", "PRIOR_IDENTITY_MISMATCH"
    if prior.get("admissibility") != "HANDOFF_ELIGIBLE":
        return "NOT_COMPUTABLE", "NO_CONTIGUOUS_PRIOR_BAR"
    current_open = _parse_time(source.get("open_time"), "open_time")
    prior_close = _parse_time(prior.get("close_time"), "prior.close_time")
    if prior_close != current_open:
        return "NOT_COMPUTABLE", "NO_CONTIGUOUS_PRIOR_BAR"
    prior_first_valid = _parse_time(prior.get("first_valid_time"), "prior.first_valid_time")
    current_close = _parse_time(source.get("close_time"), "close_time")
    if prior_first_valid > current_close:
        return "NOT_COMPUTABLE", "PRIOR_NOT_FIRST_VALID"
    return "COMPUTABLE", None


def _validate_record_identity(record: Mapping[str, Any], source: Mapping[str, Any]) -> None:
    pairs = {
        "source_bar_id": "source_bar_id",
        "release_id": "release_id",
        "manifest_id": "manifest_id",
        "research_role": "research_role",
        "instrument_id": "instrument_id",
        "clock_id": "clock_id",
        "price_side": "price_side",
        "close_time": "close_time",
        "first_valid_time": "first_valid_time",
    }
    mismatches = [
        record_key for record_key, source_key in pairs.items()
        if record.get(record_key) != source.get(source_key)
    ]
    if mismatches:
        raise ComputabilityContractError(f"record/source identity mismatch: {sorted(mismatches)}")


def build_computability_profile(
    record: Mapping[str, Any] | None,
    source: Mapping[str, Any],
    prior: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build deterministic source-bound C1 computability evidence without mutation."""

    rejection = _source_rejection_reason(source)
    if rejection:
        if rejection == "VALIDATION_LOCKED" and any(
            key in source for key in {"path", "records", "rows", "objects"}
        ):
            raise ComputabilityAccessDenied("VALIDATION_DENY_BEFORE_CONTENT_RESOLUTION")
        if record is not None:
            raise ComputabilityContractError(f"{rejection} source must emit no C1 record")
        profile = {
            "schema": "ovc-ro3-c1-computability-profile/v1",
            "role": source.get("research_role"),
            "release_id": source.get("release_id"),
            "manifest_id": source.get("manifest_id"),
            "instrument_id": source.get("instrument_id"),
            "clock_id": source.get("clock_id"),
            "price_side": source.get("price_side"),
            "source_bar_id": source.get("source_bar_id"),
            "record_emission": "NO_RECORD",
            "record_emission_reason": rejection,
            "current_bar_admissibility": "REJECTED",
            "range_computability": "NOT_EVALUATED",
            "prior_close_computability": "NOT_EVALUATED",
            "price_increment_computability": "NOT_EVALUATED",
            "chronology": "NOT_EVALUATED",
            "field_null_consistency": "NOT_APPLICABLE",
            "null_reason_counts": {},
            "writes": "NONE",
        }
        return {**profile, "profile_id": f"ro3-c1-computability:{_digest(profile)}"}

    if record is None:
        raise ComputabilityContractError("admissible source requires one C1 record")
    _validate_record_identity(record, source)

    source_first_valid = _parse_time(source.get("first_valid_time"), "first_valid_time")
    source_close = _parse_time(source.get("close_time"), "close_time")
    if source_first_valid > source_close:
        raise ComputabilityContractError("source first_valid_time exceeds source close_time")

    measurements = record.get("measurements")
    categorical = record.get("categorical")
    null_reasons = record.get("null_reasons")
    if not isinstance(measurements, Mapping) or not isinstance(categorical, Mapping) or not isinstance(null_reasons, Mapping):
        raise ComputabilityContractError("record measurements, categorical and null_reasons must be mappings")

    unknown_reasons = sorted({str(reason) for reason in null_reasons.values()} - ALLOWED_NULL_REASONS)
    if unknown_reasons:
        raise ComputabilityContractError(f"unknown null reasons: {unknown_reasons}")

    for field, value in measurements.items():
        _validate_measurement_value(str(field), value)
        has_reason = field in null_reasons
        if value is None and not has_reason:
            raise ComputabilityContractError(f"null measurement {field} has no registered reason")
        if value is not None and has_reason:
            raise ComputabilityContractError(f"non-null measurement {field} has a null reason")
    extra_reason_fields = sorted(set(null_reasons) - set(measurements))
    if extra_reason_fields:
        raise ComputabilityContractError(f"null reasons reference unknown fields: {extra_reason_fields}")
    if any(value in (None, "") for value in categorical.values()):
        raise ComputabilityContractError("categorical values cannot be null or empty")

    high = _decimal(source.get("high"), "high")
    low = _decimal(source.get("low"), "low")
    zero_range = high == low
    if zero_range:
        for field in ZERO_RANGE_NULL_FIELDS:
            if measurements.get(field) is not None or null_reasons.get(field) != "ZERO_RANGE":
                raise ComputabilityContractError(f"zero-range field {field} must be null with ZERO_RANGE")
        for field in ZERO_RANGE_ABSOLUTE_FIELDS:
            if measurements.get(field) != "0":
                raise ComputabilityContractError(f"zero-range absolute field {field} must equal canonical zero")
        if categorical.get("direction") != "FLAT":
            raise ComputabilityContractError("zero-range direction must be FLAT")

    price_increment = source.get("price_increment")
    price_increment_available = False
    if price_increment is not None:
        price_increment_available = _decimal(price_increment, "price_increment") > 0
    if not price_increment_available:
        if measurements.get("range_ticks") is not None or null_reasons.get("range_ticks") != "PRICE_INCREMENT_UNAVAILABLE":
            raise ComputabilityContractError("range_ticks must be null with PRICE_INCREMENT_UNAVAILABLE")

    prior_state, prior_reason = _prior_status(source, prior)
    if prior_state == "NOT_COMPUTABLE":
        for field in PRIOR_FIELDS:
            if measurements.get(field) is not None or null_reasons.get(field) != prior_reason:
                raise ComputabilityContractError(f"prior-dependent field {field} must be null with {prior_reason}")
    else:
        for field in PRIOR_FIELDS - {"true_range_ticks"}:
            if measurements.get(field) is None:
                raise ComputabilityContractError(f"lawful prior must compute {field}")
        if price_increment_available and measurements.get("true_range_ticks") is None:
            raise ComputabilityContractError("lawful prior and price increment must compute true_range_ticks")
        if not price_increment_available:
            if measurements.get("true_range_ticks") is not None or null_reasons.get("true_range_ticks") != "PRICE_INCREMENT_UNAVAILABLE":
                raise ComputabilityContractError("true_range_ticks must be null with PRICE_INCREMENT_UNAVAILABLE")

    reason_counts = dict(sorted(Counter(str(reason) for reason in null_reasons.values()).items()))
    profile = {
        "schema": "ovc-ro3-c1-computability-profile/v1",
        "role": record.get("research_role"),
        "release_id": record.get("release_id"),
        "manifest_id": record.get("manifest_id"),
        "instrument_id": record.get("instrument_id"),
        "clock_id": record.get("clock_id"),
        "price_side": record.get("price_side"),
        "source_bar_id": record.get("source_bar_id"),
        "record_id": record.get("record_id"),
        "record_emission": "ONE_RECORD",
        "record_emission_reason": None,
        "current_bar_admissibility": "PASS",
        "range_computability": "ZERO_RANGE" if zero_range else "COMPUTABLE",
        "prior_close_computability": prior_state,
        "prior_close_reason": prior_reason,
        "price_increment_computability": "COMPUTABLE" if price_increment_available else "NOT_COMPUTABLE",
        "chronology": "PASS",
        "field_null_consistency": "PASS",
        "null_reason_counts": reason_counts,
        "measurement_count": len(measurements),
        "categorical_count": len(categorical),
        "writes": "NONE",
    }
    return {**profile, "profile_id": f"ro3-c1-computability:{_digest(profile)}"}


def build_null_reason_profile(profiles: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    rows = sorted((dict(profile) for profile in profiles), key=lambda item: str(item.get("profile_id", "")))
    counts: Counter[tuple[str, str, str, str, str]] = Counter()
    emission: Counter[str] = Counter()
    for profile in rows:
        emission[str(profile.get("record_emission_reason") or "EMITTED")] += 1
        for reason, count in dict(profile.get("null_reason_counts", {})).items():
            key = (
                str(profile.get("role")),
                str(profile.get("release_id")),
                str(profile.get("clock_id")),
                str(profile.get("price_side")),
                str(reason),
            )
            counts[key] += int(count)
    entries = [
        {
            "role": key[0],
            "release_id": key[1],
            "clock_id": key[2],
            "price_side": key[3],
            "reason": key[4],
            "count": count,
        }
        for key, count in sorted(counts.items())
    ]
    result = {
        "schema": "ovc-ro3-c1-null-reason-profile/v1",
        "profile_count": len(rows),
        "entries": entries,
        "record_emission_counts": dict(sorted(emission.items())),
        "writes": "NONE",
    }
    return {**result, "profile_id": f"ro3-c1-null-profile:{_digest(result)}"}
