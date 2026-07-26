from __future__ import annotations

from datetime import datetime

from .adapter import adapt
from .formulas import FORMULA_REGISTRY_ID, calculate
from .identity import record_id
from .models import C1Result, SourceBar


def _dt(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def resolve_prior(current: SourceBar, prior: SourceBar | None) -> tuple[SourceBar | None, str | None]:
    if prior is None:
        return None, "NO_PRIOR_BAR"
    identity = ("release_id", "manifest_id", "instrument_id", "clock_id", "price_side")
    if any(getattr(current, name) != getattr(prior, name) for name in identity):
        return None, "PRIOR_IDENTITY_MISMATCH"
    if prior.admissibility != "HANDOFF_ELIGIBLE":
        return None, "NO_CONTIGUOUS_PRIOR_BAR"
    if _dt(prior.close_time) != _dt(current.open_time):
        return None, "NO_CONTIGUOUS_PRIOR_BAR"
    if _dt(prior.first_valid_time) > _dt(current.close_time):
        return None, "PRIOR_NOT_FIRST_VALID"
    return prior, None


def build(current_payload: dict, prior_payload: dict | None = None) -> C1Result:
    current = adapt(current_payload)
    prior = adapt(prior_payload) if prior_payload is not None else None
    lawful_prior, reason = resolve_prior(current, prior)
    measurements, categorical, null_reasons = calculate(current, lawful_prior, reason)
    identity = {
        "source_bar_id": current.source_bar_id,
        "release_id": current.release_id,
        "manifest_id": current.manifest_id,
        "clock_id": current.clock_id,
        "price_side": current.price_side,
        "formula_registry_id": FORMULA_REGISTRY_ID,
        "measurements": measurements,
        "categorical": categorical,
        "null_reasons": null_reasons,
    }
    return C1Result(
        record_id=record_id(identity), source_bar_id=current.source_bar_id, release_id=current.release_id,
        manifest_id=current.manifest_id, research_role=current.research_role, instrument_id=current.instrument_id,
        clock_id=current.clock_id, price_side=current.price_side, open_time=current.open_time,
        close_time=current.close_time, first_valid_time=current.first_valid_time,
        formula_registry_id=FORMULA_REGISTRY_ID, measurements=measurements, categorical=categorical,
        null_reasons=null_reasons, source_quality_state=current.quality_state, synthetic=current.synthetic,
    )
