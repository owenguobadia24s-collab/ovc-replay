import json
import unittest
from datetime import datetime,timezone,timedelta
from ovc.research_operations.mcarb.population import enumerate_paired_2h_coverage, stage_a_floor, exact_pair_count
from ovc.research_operations.mcarb.capacity import capacity_profile

class MCARBIWP6CapacityPopulationTest(unittest.TestCase):
    def test_exact_coverage_enumerator_and_floor(self):
        start=datetime(2024,1,1,tzinfo=timezone.utc)
        stamps=[]
        for day in range(20):
            for slot in range(12):
                stamps.append(int((start+timedelta(days=day,hours=2*slot)).timestamp()*1000))
        coverage=enumerate_paired_2h_coverage(stamps,stamps)
        self.assertEqual(coverage["paired_count"],240)
        self.assertEqual(coverage["minimum_slot_day_count"],20)
        self.assertTrue(stage_a_floor(coverage)["overall_pass"])
        self.assertEqual(exact_pair_count(240),28680)

    def test_pair_set_difference_is_visible(self):
        coverage=enumerate_paired_2h_coverage([0,7200000],[0])
        self.assertFalse(coverage["pair_sets_equal"])
        self.assertEqual(coverage["paired_count"],1)

    def test_capacity_profile_is_measured_and_bounded(self):
        profile=capacity_profile(c0_n=16,c1_n=32)
        for key in ("C0","C1"):
            self.assertGreater(profile[key]["wall_seconds"],0)
            self.assertGreater(profile[key]["peak_python_tracemalloc_bytes"],0)
            self.assertEqual(profile[key]["measurement_class"],"MEASURED_SYNTHETIC_LOCAL_PROCESS")

    def test_emit_ci_capacity_receipt(self):
        profile=capacity_profile(c0_n=64,c1_n=449)
        print("MCARBI_CAPACITY_RECEIPT="+json.dumps(profile,sort_keys=True,separators=(",",":")))
        self.assertEqual(profile["C1"]["n_per_side"],449)
        self.assertEqual(profile["C1"]["input_bar_count"],898)

if __name__=="__main__": unittest.main()
