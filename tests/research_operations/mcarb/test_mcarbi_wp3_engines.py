import json
import unittest
from decimal import Decimal
from ovc.research_operations.mcarb import (
    PriceBar, raw_activity, side_activity, clock_slot_percentile, activity_acceleration,
    directional_change, threshold_crossings, variation_clock,
    abs_return_variation, squared_return_variation, high_low_range,
)

def bar(i, close, *, side="BID", volume="10"):
    c=Decimal(close)
    return PriceBar(
        object_id=f"B{i}", side=side,
        start_utc=f"2024-01-02T0{i}:00:00Z", end_utc=f"2024-01-02T0{i}:15:00Z",
        open=c, high=c+Decimal("0.002"), low=c-Decimal("0.002"), close=c,
        volume=None if volume is None else Decimal(volume),
    )

class MCARBIWP3EnginesTest(unittest.TestCase):
    def test_al_side_specific_and_blocked_cross_side(self):
        b=bar(1,"1.20",volume="12")
        self.assertEqual(raw_activity(b).value, Decimal("12"))
        self.assertEqual(side_activity(b).candidate_id, "AL-08")
        with self.assertRaises(ValueError):
            raw_activity(b,candidate_id="AL-10")

    def test_al_missingness_and_frozen_percentile(self):
        missing=bar(1,"1.20",volume=None)
        self.assertEqual(raw_activity(missing).missingness_state,"SOURCE_FIELD_ABSENT")
        b=bar(2,"1.20",volume="20")
        p=clock_slot_percentile(b,(Decimal("10"),Decimal("20"),Decimal("30")))
        self.assertEqual(p.value, Decimal(2)/Decimal(3)*Decimal(100))

    def test_activity_acceleration(self):
        self.assertEqual(activity_acceleration(bar(1,"1.2",volume="5"),bar(2,"1.2",volume="8")).value,Decimal("3"))

    def test_et_crossing_and_variation(self):
        bars=[bar(1,"1.000"),bar(2,"1.010"),bar(3,"1.025")]
        x=threshold_crossings(bars,Decimal("1.015"))
        self.assertEqual(len(x),1)
        self.assertEqual(x[0].first_valid_time,bars[2].end_utc)
        v=variation_clock(bars,Decimal("0.020"))
        self.assertEqual(len(v),1)

    def test_directional_change_confirmation_not_backdated(self):
        bars=[bar(1,"1.000"),bar(2,"1.030"),bar(3,"1.010"),bar(4,"0.990")]
        events=directional_change(bars,Decimal("0.030"))
        self.assertTrue(events)
        down = next(event for event in events if event.value["direction"] == "DOWN")
        self.assertEqual(down.first_valid_time,bars[3].end_utc)
        self.assertGreaterEqual(down.first_valid_time,down.interval_end)

    def test_vs_core(self):
        a,b=bar(1,"1.00"),bar(2,"1.02")
        self.assertEqual(abs_return_variation(a,b).value,Decimal("0.02"))
        self.assertEqual(squared_return_variation(a,b).value,Decimal("0.0004"))
        self.assertEqual(high_low_range(b).value,Decimal("0.004"))

    def test_deterministic_serialization_identity(self):
        m=raw_activity(bar(1,"1.2",volume="12")).to_dict()
        encoded1=json.dumps(m,sort_keys=True,separators=(",",":"))
        encoded2=json.dumps(m,sort_keys=True,separators=(",",":"))
        self.assertEqual(encoded1,encoded2)
        self.assertTrue(m["record_id"].startswith("MCARB.M."))

if __name__ == "__main__":
    unittest.main()
