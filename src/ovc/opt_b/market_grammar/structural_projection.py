"""EI-WP2 deterministic C2-to-C2G structural projection (shadow only)."""
from __future__ import annotations

from decimal import Decimal, InvalidOperation, ROUND_HALF_EVEN
from hashlib import sha256
import json
from typing import Any, Iterable, Mapping

from .family_hierarchy import StructuralRecord
from .revised_c2_adapter import AXES, EmpiricalBinding, adapt_revised_c2_row

PROGRAMME_ID = "OVC-MARKET-GRAMMAR-EMPIRICAL-INTEGRATION-JUNE-v0.1"
PACKET_ID = "EI-WP2"
PROJECTION_ID = "MG-EI-WP2-C2G-STRUCTURAL-PROJECTION-v0.1"
FEATURE_KEYS = ("location", "motion", "organisation", "interaction", "quality")
Q = Decimal("0.000000000001")


class StructuralProjectionError(ValueError):
    pass


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def _sha(value: Any) -> str:
    return sha256(_canonical(value)).hexdigest()


def _measurement(value: object, axis: str) -> tuple[Decimal | None, str | None]:
    if value is None:
        return None, f"{axis}:MISSING_NORMALIZED_MEASUREMENT"
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None, f"{axis}:INVALID_NORMALIZED_MEASUREMENT"
    if not result.is_finite():
        return None, f"{axis}:NONFINITE_NORMALIZED_MEASUREMENT"
    if result < Decimal("0") or result > Decimal("1"):
        return None, f"{axis}:NORMALIZED_MEASUREMENT_OUT_OF_RANGE"
    return result.quantize(Q, rounding=ROUND_HALF_EVEN), None


def project_revised_c2_state(
    row: Mapping[str, object], *, binding: EmpiricalBinding | Mapping[str, object]
) -> dict[str, object]:
    # EI-WP1 validation is the source authority boundary. The adapted object
    # supplies exact identity/computability semantics; projection reads only
    # the five declared axis measurements from the already validated row.
    adapted = adapt_revised_c2_row(row, binding=binding)
    raw_axes = row["axes"]
    if not isinstance(raw_axes, Mapping):
        raise StructuralProjectionError("AXES_OBJECT_REQUIRED")

    reasons: list[str] = []
    coordinates: dict[str, Decimal] = {}
    for axis, feature in zip(AXES, FEATURE_KEYS):
        raw_axis = raw_axes[axis]
        if not isinstance(raw_axis, Mapping):
            raise StructuralProjectionError(f"AXIS_OBJECT_REQUIRED:{axis}")
        status = str(raw_axis["status"]).strip().upper()
        if status != "EVALUATED":
            reason_code = str(raw_axis.get("reason_code") or "UNSPECIFIED")
            reasons.append(f"{axis}:{status}:{reason_code}")
            continue
        coordinate, error = _measurement(raw_axis.get("measurement"), axis)
        if error is not None:
            reasons.append(error)
        elif coordinate is not None:
            coordinates[feature] = coordinate

    if reasons:
        structural_features: dict[str, str] = {}
        computability = "NOT_EVALUABLE"
        not_evaluable_reason = "|".join(reasons)
    else:
        if tuple(coordinates) != FEATURE_KEYS:
            raise StructuralProjectionError("FEATURE_SET_INTERNAL_MISMATCH")
        structural_features = {
            key: format(coordinates[key], "f") for key in FEATURE_KEYS
        }
        computability = "EVALUABLE"
        not_evaluable_reason = None

    projected = {
        "record_id": adapted["record_id"],
        "record_type": "STATE",
        "source_release_id": adapted["source_release_id"],
        "instrument_id": adapted["instrument_id"],
        "side": adapted["side"],
        "scope_id": adapted["scope_id"],
        "clock_id": adapted["clock_id"],
        "first_valid_time": adapted["first_valid_time"],
        "source_sha256": adapted["source_sha256"],
        "structural_features": structural_features,
        "computability_status": computability,
        "not_evaluable_reason": not_evaluable_reason,
    }
    StructuralRecord.from_mapping(projected)
    return projected


def project_revised_c2_states(
    rows: Iterable[Mapping[str, object]], *, binding: EmpiricalBinding | Mapping[str, object]
) -> dict[str, object]:
    values = [project_revised_c2_state(row, binding=binding) for row in rows]
    if not values:
        raise StructuralProjectionError("SOURCE_ROWS_REQUIRED")
    ids = [str(item["record_id"]) for item in values]
    if len(ids) != len(set(ids)):
        raise StructuralProjectionError("DUPLICATE_RECORD_ID")
    values.sort(key=lambda item: (str(item["side"]), str(item["first_valid_time"]), str(item["record_id"])))
    feature_map = {
        str(item["record_id"]): dict(item["structural_features"])
        for item in values
        if item["computability_status"] == "EVALUABLE"
    }
    body = {
        "schema": "ovc-mg-ei-wp2-structural-projection/v1",
        "programme_id": PROGRAMME_ID,
        "packet_id": PACKET_ID,
        "projection_id": PROJECTION_ID,
        "authority_state": "SHADOW_EXPERIMENT",
        "canonical": False,
        "published": False,
        "promotion_authority": "NONE",
        "feature_keys": list(FEATURE_KEYS),
        "record_count": len(values),
        "evaluable_count": sum(item["computability_status"] == "EVALUABLE" for item in values),
        "not_evaluable_count": sum(item["computability_status"] != "EVALUABLE" for item in values),
        "records": values,
        "state_structural_features": feature_map,
    }
    body["logical_sha256"] = _sha(body)
    return body
