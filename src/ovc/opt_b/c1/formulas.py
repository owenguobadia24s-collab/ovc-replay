from __future__ import annotations

from decimal import Decimal

from .models import SourceBar

FORMULA_REGISTRY_ID = "C1.FORMULAS.v0.1"
C1_IMPLEMENTATION_ID = "C1.IMPLEMENTATION.v0.2"
PRIOR_FIELDS = ("true_range_abs", "true_range_ticks", "close_change", "open_gap")
ZERO_RANGE_NULL_FIELDS = (
    "body_utilisation", "upper_wick_share", "lower_wick_share", "wick_balance",
    "open_location", "close_location", "signed_efficiency",
)


def _s(value: Decimal) -> str:
    if value == 0:
        return "0"
    return format(value.normalize(), "f")


def calculate_wick_balance(
    upper_wick_abs: Decimal,
    lower_wick_abs: Decimal,
    range_abs: Decimal,
) -> Decimal | None:
    """Return the frozen C1 wick-balance formula.

    The formula registry defines wick balance as upper-wick share minus
    lower-wick share.  Keeping this as one callable prevents the fixture,
    replay and prospective-compute paths from acquiring independent signs.
    """

    if range_abs == 0:
        return None
    return (upper_wick_abs - lower_wick_abs) / range_abs


def calculate(current: SourceBar, prior: SourceBar | None, prior_reason: str | None) -> tuple[dict[str, str | None], dict[str, str], dict[str, str]]:
    o, h, l, c = current.open, current.high, current.low, current.close
    r = h - l
    body = c - o
    upper = h - max(o, c)
    lower = min(o, c) - l
    values: dict[str, str | None] = {
        "range_abs": _s(r),
        "range_ticks": _s(r / current.price_increment) if current.price_increment else None,
        "body_signed": _s(body),
        "body_abs": _s(abs(body)),
        "body_utilisation": _s(abs(body) / r) if r else None,
        "upper_wick_abs": _s(upper),
        "lower_wick_abs": _s(lower),
        "upper_wick_share": _s(upper / r) if r else None,
        "lower_wick_share": _s(lower / r) if r else None,
        "wick_balance": None if (balance := calculate_wick_balance(upper, lower, r)) is None else _s(balance),
        "open_location": _s((o - l) / r) if r else None,
        "close_location": _s((c - l) / r) if r else None,
        "signed_efficiency": _s(body / r) if r else None,
        "true_range_abs": None,
        "true_range_ticks": None,
        "close_change": None,
        "open_gap": None,
    }
    nulls: dict[str, str] = {}
    if current.price_increment is None:
        nulls["range_ticks"] = "PRICE_INCREMENT_UNAVAILABLE"
    if not r:
        for field in ZERO_RANGE_NULL_FIELDS:
            nulls[field] = "ZERO_RANGE"
    if prior is None:
        reason = prior_reason or "NO_PRIOR_BAR"
        for field in PRIOR_FIELDS:
            nulls[field] = reason
    else:
        pc = prior.close
        tr = max(r, abs(h - pc), abs(l - pc))
        values["true_range_abs"] = _s(tr)
        values["true_range_ticks"] = _s(tr / current.price_increment) if current.price_increment else None
        values["close_change"] = _s(c - pc)
        values["open_gap"] = _s(o - pc)
        if current.price_increment is None:
            nulls["true_range_ticks"] = "PRICE_INCREMENT_UNAVAILABLE"
    categorical = {"direction": "UP" if body > 0 else "DOWN" if body < 0 else "FLAT"}
    return values, categorical, nulls
