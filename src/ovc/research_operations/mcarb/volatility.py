from __future__ import annotations
from decimal import Decimal
from .models import AuxiliaryMeasurement, PriceBar

VS_VERSION = "mcarb-vs-v0.1"

def _m(bar: PriceBar, candidate: str, value: Decimal, parent_ids: tuple[str,...], variant: str) -> AuxiliaryMeasurement:
    return AuxiliaryMeasurement(
        domain="VS", candidate_id=candidate, side=bar.side,
        interval_start=bar.start_utc, interval_end=bar.end_utc, first_valid_time=bar.end_utc,
        admissible_cutoff=bar.end_utc, parent_ids=parent_ids, calculation_version=VS_VERSION,
        variant_id=variant, comparability_domain_id="VS.PRICE.SIDE", missingness_state="AVAILABLE", value=value,
    )

def abs_return_variation(previous: PriceBar, current: PriceBar) -> AuxiliaryMeasurement:
    if previous.side != current.side:
        raise ValueError("VS series must be one side")
    if previous.close == 0:
        raise ValueError("previous close cannot be zero")
    value = abs((current.close - previous.close) / previous.close)
    return _m(current,"VS-01",value,(previous.object_id,current.object_id),"VS-01.simple-return")

def squared_return_variation(previous: PriceBar, current: PriceBar) -> AuxiliaryMeasurement:
    if previous.side != current.side:
        raise ValueError("VS series must be one side")
    if previous.close == 0:
        raise ValueError("previous close cannot be zero")
    r=(current.close-previous.close)/previous.close
    return _m(current,"VS-02",r*r,(previous.object_id,current.object_id),"VS-02.simple-return-squared")

def high_low_range(bar: PriceBar) -> AuxiliaryMeasurement:
    return _m(bar,"VS-03",bar.high-bar.low,(bar.object_id,),"VS-03.raw-range")
