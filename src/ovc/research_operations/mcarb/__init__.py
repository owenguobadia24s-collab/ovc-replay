"""MCARB bounded research-only auxiliary-representation machinery.

This namespace has no market-run authority, no selector authority, no Validation
consumption authority, no semantic-promotion authority, and no probability,
risk, exposure or execution authority. Capability is not authority.
"""
from .models import AuxiliaryMeasurement, PriceBar
from .activity import raw_activity, clock_slot_percentile, activity_acceleration, side_activity
from .intrinsic_time import directional_change, threshold_crossings, variation_clock
from .volatility import abs_return_variation, squared_return_variation, high_low_range

__all__ = [
    "AuxiliaryMeasurement","PriceBar","raw_activity","clock_slot_percentile",
    "activity_acceleration","side_activity","directional_change","threshold_crossings",
    "variation_clock","abs_return_variation","squared_return_variation","high_low_range",
]
