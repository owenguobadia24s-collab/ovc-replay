from __future__ import annotations

from .formulas import PRIOR_FIELDS, ZERO_RANGE_NULL_FIELDS
from .models import C1Result

ALLOWED_NULL_REASONS = {
    "ZERO_RANGE", "NO_PRIOR_BAR", "NO_CONTIGUOUS_PRIOR_BAR", "PRIOR_IDENTITY_MISMATCH",
    "PRIOR_NOT_FIRST_VALID", "PRICE_INCREMENT_UNAVAILABLE",
}


def validate(result: C1Result) -> None:
    if not result.record_id.startswith("c1:") or len(result.record_id) != 67:
        raise ValueError("INVALID_RECORD_ID")
    if result.formula_registry_id != "C1.FORMULAS.v0.1":
        raise ValueError("FORMULA_REGISTRY_MISMATCH")
    if result.clock_id not in {"15M", "2H_A_L"}:
        raise ValueError("CLOCK_NOT_AUTHORISED")
    if result.price_side not in {"BID", "ASK"}:
        raise ValueError("SIDE_NOT_AUTHORISED")
    if any(reason not in ALLOWED_NULL_REASONS for reason in result.null_reasons.values()):
        raise ValueError("UNKNOWN_NULL_REASON")
    for field, value in result.measurements.items():
        has_reason = field in result.null_reasons
        if (value is None) != has_reason:
            raise ValueError(f"NULL_REASON_MISMATCH:{field}")
    if result.categorical.get("direction") not in {"UP", "DOWN", "FLAT"}:
        raise ValueError("INVALID_DIRECTION")
    for forbidden in ("threshold", "semantic", "outcome", "probability", "trade"):
        if forbidden in str(result).lower():
            raise ValueError("FORBIDDEN_SEMANTIC_FIELD")
