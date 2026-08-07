"""EI-WP1 read-only revised-C2 empirical source adapter.

This module replaces only the MG-WP8 synthetic ``c2_records`` interface.
It does not construct market states from raw prices, select a sensitivity,
promote any family/rule/grammar, publish evidence, or change a selector.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
import re
from typing import Any, Iterable, Mapping

from .episode_ledger import C2LedgerInput

ADAPTER_ID = "MG-EI-WP1-REVISED-C2-ADAPTER-v0.1"
PROGRAMME_ID = "OVC-MARKET-GRAMMAR-EMPIRICAL-INTEGRATION-JUNE-v0.1"
PACKET_ID = "EI-WP1"
SOURCE_RELEASE_ID = "C2AR.INTEGRATED.SHADOW.PACKAGE.v1"
BINDING_SHA256 = "126a703b89bf8fc60a4beb1248b20b424621334c8fff254c122555e44663f8"
LOGICAL_POPULATION_SHA256 = "3f1089e3a4eefe94147c8c2f912e77899e4ed21fe8b3b8b85993e47bf7151ee7"
INTEGRATED_PACKAGE_SHA256 = "150de1997be8801baa59db6d0fe98b11cb21a6b70525b908537aeb31bfd00cc3"
INSTRUMENT_ID = "GBPUSD"
CLOCK_ID = "15M"
PARENT_CLOCK_ID = "2H_A_L"
SCOPE_ID = "GBPUSD-15M-LOCAL-v0.1"
AXES = ("LOCATION", "MOTION", "ORGANISATION", "INTERACTION", "QUALITY")
AXIS_STATUSES = frozenset({"EVALUATED", "NOT_EVALUATED", "NOT_EVALUABLE", "CENSORED", "CONFLICT", "QUARANTINED"})
SIDES = frozenset({"BID", "ASK"})
CONTINUITY = frozenset({"CONTIGUOUS", "SEGMENT_START", "GAP_RESET", "CLOSURE_BOUNDARY", "PARTITION_BOUNDARY", "UNKNOWN_BREAK"})
RESET_CONTINUITY = frozenset({"GAP_RESET", "CLOSURE_BOUNDARY", "PARTITION_BOUNDARY", "UNKNOWN_BREAK"})
HEX64 = re.compile(r"^[0-9a-f]{64}$")

ALLOWED_TOP_LEVEL = frozenset({
    "record_id", "source_release_id", "instrument_id", "side", "evaluation_scope_id",
    "clock_id", "first_valid_time", "axes", "changed_axes", "source_sha256",
    "parent_context_record_id", "parent_clock_id", "continuity_status", "reset_reason",
    "diagnostic_metadata",
})
FORBIDDEN_TOP_LEVEL = frozenset({
    "family_id", "cluster_id", "medoid_id", "variant_id", "sensitivity_pack_id", "distance",
    "grammar_id", "parse_id", "semantic_label", "trade_label", "outcome", "outcome_id",
    "return", "returns", "mfe", "mae", "future", "future_price", "future_path",
    "probability", "risk", "exposure", "execution",
})
ALLOWED_AXIS_KEYS = frozenset({"status", "value", "reason_code", "measurement"})


class RevisedC2AdapterError(ValueError):
    """Raised when the EI-WP1 source or binding violates the frozen contract."""


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def _sha(value: Any) -> str:
    return sha256(_canonical(value)).hexdigest()


def _text(value: object, field: str) -> str:
    result = str(value).strip()
    if not result:
        raise RevisedC2AdapterError(f"EMPTY_FIELD:{field}")
    return result


def _time(value: object, field: str = "first_valid_time") -> str:
    text = _text(value, field)
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise RevisedC2AdapterError(f"INVALID_ISO_TIME:{field}") from exc
    if parsed.tzinfo is None:
        raise RevisedC2AdapterError(f"TIMEZONE_REQUIRED:{field}")
    return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _digest(value: object, field: str) -> str:
    result = _text(value, field).lower()
    if HEX64.fullmatch(result) is None:
        raise RevisedC2AdapterError(f"SHA256_REQUIRED:{field}")
    return result


@dataclass(frozen=True)
class EmpiricalBinding:
    binding_sha256: str
    logical_population_sha256: str
    integrated_package_sha256: str
    source_release_id: str = SOURCE_RELEASE_ID

    def __post_init__(self) -> None:
        object.__setattr__(self, "binding_sha256", _digest(self.binding_sha256, "binding_sha256"))
        object.__setattr__(self, "logical_population_sha256", _digest(self.logical_population_sha256, "logical_population_sha256"))
        object.__setattr__(self, "integrated_package_sha256", _digest(self.integrated_package_sha256, "integrated_package_sha256"))
        object.__setattr__(self, "source_release_id", _text(self.source_release_id, "source_release_id"))
        if self.binding_sha256 != BINDING_SHA256:
            raise RevisedC2AdapterError("BINDING_SHA256_MISMATCH")
        if self.logical_population_sha256 != LOGICAL_POPULATION_SHA256:
            raise RevisedC2AdapterError("LOGICAL_POPULATION_SHA256_MISMATCH")
        if self.integrated_package_sha256 != INTEGRATED_PACKAGE_SHA256:
            raise RevisedC2AdapterError("INTEGRATED_PACKAGE_SHA256_MISMATCH")
        if self.source_release_id != SOURCE_RELEASE_ID:
            raise RevisedC2AdapterError("SOURCE_RELEASE_ID_MISMATCH")

    @classmethod
    def accepted(cls) -> "EmpiricalBinding":
        return cls(BINDING_SHA256, LOGICAL_POPULATION_SHA256, INTEGRATED_PACKAGE_SHA256, SOURCE_RELEASE_ID)

    @classmethod
    def from_mapping(cls, value: Mapping[str, object]) -> "EmpiricalBinding":
        expected = {"binding_sha256", "logical_population_sha256", "integrated_package_sha256", "source_release_id"}
        unknown = sorted(set(value) - expected)
        missing = sorted(expected - set(value))
        if unknown:
            raise RevisedC2AdapterError("UNKNOWN_BINDING_FIELDS:" + ",".join(unknown))
        if missing:
            raise RevisedC2AdapterError("MISSING_BINDING_FIELDS:" + ",".join(missing))
        return cls(**dict(value))

    def to_dict(self) -> dict[str, str]:
        return {
            "binding_sha256": self.binding_sha256,
            "logical_population_sha256": self.logical_population_sha256,
            "integrated_package_sha256": self.integrated_package_sha256,
            "source_release_id": self.source_release_id,
        }


def _axis(axis_name: str, raw: object) -> dict[str, object]:
    if not isinstance(raw, Mapping):
        raise RevisedC2AdapterError(f"AXIS_OBJECT_REQUIRED:{axis_name}")
    keys = set(raw)
    unknown = sorted(keys - ALLOWED_AXIS_KEYS)
    missing = sorted({"status", "value"} - keys)
    if unknown:
        raise RevisedC2AdapterError(f"UNKNOWN_AXIS_FIELDS:{axis_name}:" + ",".join(unknown))
    if missing:
        raise RevisedC2AdapterError(f"MISSING_AXIS_FIELDS:{axis_name}:" + ",".join(missing))
    status = _text(raw["status"], f"axes.{axis_name}.status").upper()
    if status not in AXIS_STATUSES:
        raise RevisedC2AdapterError(f"INVALID_AXIS_STATUS:{axis_name}:{status}")
    value = raw.get("value")
    if value is not None:
        value = _text(value, f"axes.{axis_name}.value")
    reason = raw.get("reason_code")
    if reason is not None:
        reason = _text(reason, f"axes.{axis_name}.reason_code")
    measurement = raw.get("measurement")
    if measurement is not None:
        measurement = _text(measurement, f"axes.{axis_name}.measurement")
    if status == "EVALUATED" and reason is not None:
        raise RevisedC2AdapterError(f"EVALUATED_AXIS_CANNOT_HAVE_REASON:{axis_name}")
    if status != "EVALUATED" and reason is None:
        raise RevisedC2AdapterError(f"NON_EVALUATED_AXIS_REQUIRES_REASON:{axis_name}")
    return {"status": status, "value": value, "reason_code": reason, "measurement": measurement}


def _axes(raw: object) -> dict[str, dict[str, object]]:
    if not isinstance(raw, Mapping):
        raise RevisedC2AdapterError("AXES_OBJECT_REQUIRED")
    keys = set(raw)
    if keys != set(AXES):
        missing = sorted(set(AXES) - keys)
        unknown = sorted(keys - set(AXES))
        marker = []
        if missing:
            marker.append("missing=" + ",".join(missing))
        if unknown:
            marker.append("unknown=" + ",".join(unknown))
        raise RevisedC2AdapterError("AXIS_SET_MISMATCH:" + ";".join(marker))
    return {axis_name: _axis(axis_name, raw[axis_name]) for axis_name in AXES}


def _computability(axes: Mapping[str, Mapping[str, object]]) -> tuple[str, str | None]:
    precedence = (
        ("QUARANTINED", "QUARANTINED"),
        ("CONFLICT", "CONFLICT"),
        ("CENSORED", "CENSORED"),
        ("NOT_EVALUABLE", "NOT_EVALUABLE"),
        ("NOT_EVALUATED", "NOT_EVALUATED"),
    )
    aggregate = "EVALUABLE"
    for source_status, target_status in precedence:
        if any(str(axes[name]["status"]) == source_status for name in AXES):
            aggregate = target_status
            break
    if aggregate == "EVALUABLE":
        if any(str(axes[name]["status"]) != "EVALUATED" for name in AXES):
            raise RevisedC2AdapterError("UNMAPPED_AXIS_STATUS")
        return aggregate, None
    reasons = []
    for name in AXES:
        status = str(axes[name]["status"])
        if status != "EVALUATED":
            reason = str(axes[name].get("reason_code") or "UNSPECIFIED")
            reasons.append(f"{name}:{status}:{reason}")
    return aggregate, "|".join(reasons)


def _state_key(axes: Mapping[str, Mapping[str, object]]) -> str:
    parts = []
    for name in AXES:
        status = str(axes[name]["status"])
        value = axes[name].get("value")
        parts.append(f"{name}={status}:{'NULL' if value is None else value}")
    return "|".join(parts)


def adapt_revised_c2_row(row: Mapping[str, object], *, binding: EmpiricalBinding | Mapping[str, object]) -> dict[str, object]:
    bound = binding if isinstance(binding, EmpiricalBinding) else EmpiricalBinding.from_mapping(binding)
    keys = set(row)
    forbidden = sorted(keys & FORBIDDEN_TOP_LEVEL)
    unknown = sorted(keys - ALLOWED_TOP_LEVEL)
    required = {
        "record_id", "source_release_id", "instrument_id", "side", "evaluation_scope_id",
        "clock_id", "first_valid_time", "axes", "changed_axes", "source_sha256",
    }
    missing = sorted(required - keys)
    if forbidden:
        raise RevisedC2AdapterError("FORBIDDEN_SOURCE_FIELDS:" + ",".join(forbidden))
    if unknown:
        raise RevisedC2AdapterError("UNKNOWN_SOURCE_FIELDS:" + ",".join(unknown))
    if missing:
        raise RevisedC2AdapterError("MISSING_SOURCE_FIELDS:" + ",".join(missing))

    record_id = _text(row["record_id"], "record_id")
    source_release_id = _text(row["source_release_id"], "source_release_id")
    if source_release_id != bound.source_release_id:
        raise RevisedC2AdapterError("ROW_SOURCE_RELEASE_ID_MISMATCH")
    instrument = _text(row["instrument_id"], "instrument_id").upper()
    if instrument != INSTRUMENT_ID:
        raise RevisedC2AdapterError("INSTRUMENT_SCOPE_MISMATCH")
    side = _text(row["side"], "side").upper()
    if side not in SIDES:
        raise RevisedC2AdapterError("SIDE_SCOPE_MISMATCH")
    scope_id = _text(row["evaluation_scope_id"], "evaluation_scope_id")
    if scope_id != SCOPE_ID:
        raise RevisedC2AdapterError("EVALUATION_SCOPE_MISMATCH")
    clock_id = _text(row["clock_id"], "clock_id").upper()
    if clock_id != CLOCK_ID:
        raise RevisedC2AdapterError("CLOCK_SCOPE_MISMATCH")
    first_valid_time = _time(row["first_valid_time"])
    source_sha256 = _digest(row["source_sha256"], "source_sha256")

    axes = _axes(row["axes"])
    changed_raw = row["changed_axes"]
    if isinstance(changed_raw, (str, bytes)) or not isinstance(changed_raw, Iterable):
        raise RevisedC2AdapterError("CHANGED_AXES_ARRAY_REQUIRED")
    changed = [_text(item, "changed_axes").upper() for item in changed_raw]
    if len(changed) != len(set(changed)):
        raise RevisedC2AdapterError("DUPLICATE_CHANGED_AXIS")
    invalid_changed = sorted(set(changed) - set(AXES))
    if invalid_changed:
        raise RevisedC2AdapterError("INVALID_CHANGED_AXES:" + ",".join(invalid_changed))
    changed = sorted(changed, key=AXES.index)

    parent_id = row.get("parent_context_record_id")
    parent_clock = row.get("parent_clock_id")
    if parent_id is not None:
        parent_id = _text(parent_id, "parent_context_record_id")
        if _text(parent_clock, "parent_clock_id").upper() != PARENT_CLOCK_ID:
            raise RevisedC2AdapterError("PARENT_CLOCK_SCOPE_MISMATCH")
    elif parent_clock is not None:
        raise RevisedC2AdapterError("PARENT_CLOCK_WITHOUT_PARENT")

    continuity = row.get("continuity_status")
    reset_reason = row.get("reset_reason")
    if continuity is not None:
        continuity = _text(continuity, "continuity_status").upper()
        if continuity not in CONTINUITY:
            raise RevisedC2AdapterError("INVALID_CONTINUITY_STATUS")
    if continuity in RESET_CONTINUITY:
        if reset_reason is None:
            raise RevisedC2AdapterError("RESET_CONTINUITY_REQUIRES_REASON")
        reset_reason = _text(reset_reason, "reset_reason")
    else:
        if reset_reason is not None:
            raise RevisedC2AdapterError("RESET_REASON_WITHOUT_RESET_CONTINUITY")
        reset_reason = None

    computability_status, not_evaluable_reason = _computability(axes)
    adapted = {
        "record_id": record_id,
        "source_release_id": source_release_id,
        "instrument_id": instrument,
        "side": side,
        "scope_id": scope_id,
        "clock_id": clock_id,
        "first_valid_time": first_valid_time,
        "state_key": _state_key(axes),
        "transition_kind": "AXIS_CHANGE" if changed else "NONE",
        "parent_record_id": parent_id,
        "computability_status": computability_status,
        "not_evaluable_reason": not_evaluable_reason,
        "reset_reason": reset_reason,
        "source_sha256": source_sha256,
    }
    # Validate the exact downstream contract before returning the mapping.
    C2LedgerInput.from_mapping(adapted)
    return adapted


def adapt_revised_c2_rows(
    rows: Iterable[Mapping[str, object]], *, binding: EmpiricalBinding | Mapping[str, object], build_cutoff: object,
) -> dict[str, object]:
    bound = binding if isinstance(binding, EmpiricalBinding) else EmpiricalBinding.from_mapping(binding)
    cutoff = _time(build_cutoff, "build_cutoff")
    adapted = [adapt_revised_c2_row(row, binding=bound) for row in rows]
    if not adapted:
        raise RevisedC2AdapterError("SOURCE_ROWS_REQUIRED")
    if any(_time(item["first_valid_time"]) > cutoff for item in adapted):
        raise RevisedC2AdapterError("SOURCE_ROW_EXCEEDS_BUILD_CUTOFF")
    ids = [str(item["record_id"]) for item in adapted]
    if len(ids) != len(set(ids)):
        raise RevisedC2AdapterError("DUPLICATE_RECORD_ID")
    exact_times = [(str(item["side"]), str(item["scope_id"]), str(item["first_valid_time"])) for item in adapted]
    if len(exact_times) != len(set(exact_times)):
        raise RevisedC2AdapterError("DUPLICATE_FIRST_VALID_TIME_WITHIN_EXACT_SCOPE")
    adapted.sort(key=lambda item: (str(item["side"]), str(item["first_valid_time"]), str(item["record_id"])))
    body = {
        "schema": "ovc-mg-ei-wp1-adapted-c2-ledger-input/v1",
        "programme_id": PROGRAMME_ID,
        "packet_id": PACKET_ID,
        "adapter_id": ADAPTER_ID,
        "authority_state": "SHADOW_EXPERIMENT",
        "canonical": False,
        "published": False,
        "promotion_authority": "NONE",
        "build_cutoff": cutoff,
        "binding": bound.to_dict(),
        "record_count": len(adapted),
        "records": adapted,
    }
    body["logical_sha256"] = _sha(body)
    return body
