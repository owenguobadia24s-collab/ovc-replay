from __future__ import annotations
from decimal import Decimal
from .models import AuxiliaryMeasurement, PriceBar

AL_VERSION = "mcarb-al-v0.1"
_ALLOWED = {"AL-01","AL-05","AL-07","AL-08","AL-09"}

def _measurement(bar: PriceBar, candidate: str, value: Decimal | None, *, comparability: str,
                 missing: str = "AVAILABLE", reasons: tuple[str,...]=()) -> AuxiliaryMeasurement:
    return AuxiliaryMeasurement(
        domain="AL", candidate_id=candidate, side=bar.side,
        interval_start=bar.start_utc, interval_end=bar.end_utc, first_valid_time=bar.end_utc,
        admissible_cutoff=bar.end_utc, parent_ids=(bar.object_id,), calculation_version=AL_VERSION,
        variant_id=None, comparability_domain_id=comparability, missingness_state=missing,
        value=value, reason_codes=reasons,
    )

def _admit(candidate: str, bar: PriceBar) -> None:
    if candidate not in _ALLOWED:
        raise ValueError(f"AL candidate not admitted by G1: {candidate}")
    if candidate == "AL-08" and bar.side != "BID":
        raise ValueError("AL-08 is BID-only")
    if candidate == "AL-09" and bar.side != "ASK":
        raise ValueError("AL-09 is ASK-only")

def raw_activity(bar: PriceBar, *, candidate_id: str = "AL-01") -> AuxiliaryMeasurement:
    _admit(candidate_id, bar)
    if bar.volume is None:
        return _measurement(bar, candidate_id, None, comparability="AL.M1.SIDE",
                            missing="SOURCE_FIELD_ABSENT", reasons=("SOURCE_FIELD_ABSENT",))
    return _measurement(bar, candidate_id, bar.volume, comparability="AL.M1.SIDE")

def side_activity(bar: PriceBar) -> AuxiliaryMeasurement:
    candidate = "AL-08" if bar.side == "BID" else "AL-09"
    return raw_activity(bar, candidate_id=candidate)

def clock_slot_percentile(bar: PriceBar, frozen_reference: tuple[Decimal,...]) -> AuxiliaryMeasurement:
    _admit("AL-05", bar)
    if bar.volume is None:
        return _measurement(bar, "AL-05", None, comparability="AL.M1.SIDE.SLOT",
                            missing="SOURCE_FIELD_ABSENT", reasons=("SOURCE_FIELD_ABSENT",))
    if not frozen_reference:
        return _measurement(bar, "AL-05", None, comparability="AL.M1.SIDE.SLOT",
                            missing="INSUFFICIENT_HISTORY", reasons=("INSUFFICIENT_HISTORY",))
    if any(v < 0 for v in frozen_reference):
        raise ValueError("reference activity must be non-negative")
    rank = sum(1 for value in frozen_reference if value <= bar.volume)
    percentile = (Decimal(rank) / Decimal(len(frozen_reference))) * Decimal(100)
    return _measurement(bar, "AL-05", percentile, comparability="AL.M1.SIDE.SLOT.FROZEN_REF")

def activity_acceleration(previous: PriceBar, current: PriceBar) -> AuxiliaryMeasurement:
    _admit("AL-07", current)
    if previous.side != current.side:
        raise ValueError("activity acceleration is side-specific")
    if previous.volume is None or current.volume is None:
        return _measurement(current, "AL-07", None, comparability="AL.M1.SIDE",
                            missing="SOURCE_FIELD_ABSENT", reasons=("SOURCE_FIELD_ABSENT",))
    return _measurement(current, "AL-07", current.volume - previous.volume, comparability="AL.M1.SIDE")
