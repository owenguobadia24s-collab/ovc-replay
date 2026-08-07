from __future__ import annotations
from decimal import Decimal
from .models import AuxiliaryMeasurement, PriceBar

ET_VERSION = "mcarb-et-v0.1"

def _event(bar: PriceBar, candidate: str, value, *, variant: str, parents: tuple[str,...],
           first_valid: str | None = None) -> AuxiliaryMeasurement:
    fv = first_valid or bar.end_utc
    return AuxiliaryMeasurement(
        domain="ET", candidate_id=candidate, side=bar.side,
        interval_start=bar.start_utc, interval_end=bar.end_utc, first_valid_time=fv,
        admissible_cutoff=fv, parent_ids=parents, calculation_version=ET_VERSION,
        variant_id=variant, comparability_domain_id="ET.PRICE.SIDE",
        missingness_state="AVAILABLE", value=value,
    )

def threshold_crossings(bars: list[PriceBar], level: Decimal, *, variant_id: str = "ET-X.raw") -> list[AuxiliaryMeasurement]:
    if len(bars) < 2:
        return []
    out=[]
    for previous,current in zip(bars,bars[1:]):
        if previous.side != current.side:
            raise ValueError("crossing series must be one side")
        direction = None
        if previous.close < level <= current.close:
            direction = "UP"
        elif previous.close > level >= current.close:
            direction = "DOWN"
        if direction:
            out.append(_event(current,"ET-X",{"direction":direction,"level":str(level)},variant=variant_id,
                              parents=(previous.object_id,current.object_id)))
    return out

def variation_clock(bars: list[PriceBar], target: Decimal, *, variant_id: str = "ET-VAR.abs-close") -> list[AuxiliaryMeasurement]:
    if target <= 0:
        raise ValueError("variation target must be positive")
    if len(bars) < 2:
        return []
    acc=Decimal(0); parents=[]; out=[]
    previous=bars[0]
    for current in bars[1:]:
        if previous.side != current.side:
            raise ValueError("variation series must be one side")
        parents.extend([previous.object_id] if not parents else [])
        parents.append(current.object_id)
        acc += abs(current.close-previous.close)
        if acc >= target:
            out.append(_event(current,"ET-VAR",{"accumulated":str(acc),"target":str(target)},variant=variant_id,
                              parents=tuple(parents)))
            acc=Decimal(0); parents=[]
        previous=current
    return out

def directional_change(bars: list[PriceBar], threshold: Decimal, *, variant_id: str = "ET-DC.abs") -> list[AuxiliaryMeasurement]:
    if threshold <= 0:
        raise ValueError("directional-change threshold must be positive")
    if not bars:
        return []
    side=bars[0].side
    if any(bar.side != side for bar in bars):
        raise ValueError("directional-change series must be one side")
    high=low=bars[0].close
    mode=None
    high_id=low_id=bars[0].object_id
    out=[]
    for bar in bars[1:]:
        if bar.close > high:
            high,high_id=bar.close,bar.object_id
        if bar.close < low:
            low,low_id=bar.close,bar.object_id
        if mode != "DOWN" and high - bar.close >= threshold:
            out.append(_event(bar,"ET-DC",{"direction":"DOWN","extreme":str(high),"threshold":str(threshold)},
                              variant=variant_id, parents=(high_id,bar.object_id)))
            mode="DOWN"; low=bar.close; low_id=bar.object_id
        elif mode != "UP" and bar.close - low >= threshold:
            out.append(_event(bar,"ET-DC",{"direction":"UP","extreme":str(low),"threshold":str(threshold)},
                              variant=variant_id, parents=(low_id,bar.object_id)))
            mode="UP"; high=bar.close; high_id=bar.object_id
    return out
