import json
import unittest
from pathlib import Path
from ovc.research_operations.populations import PopulationRegisterError, eligibility, record_allocation, record_exposure, validate_register

REG=Path("registries/research_operations/populations/OVC_POPULATION_ALLOCATION_EXPOSURE_REGISTER_v0_1.json")

class TestPopulationRegister(unittest.TestCase):
    def setUp(self): self.r=json.loads(REG.read_text())
    def test_seed_inventory(self):
        validate_register(self.r); self.assertEqual(len(self.r["resources"]),32); self.assertTrue(all(len(x["clock_views"])==2 for x in self.r["resources"]))
    def test_unknown_fails_closed_for_validation(self):
        pid=self.r["resources"][0]["population_id"]; self.assertEqual(eligibility(self.r,pid,"VALIDATION")["disposition"],"BLOCKED_EXPOSURE_CENSUS_REQUIRED")
    def test_discovery_reusable(self):
        pid=self.r["resources"][0]["population_id"]; self.assertEqual(eligibility(self.r,pid,"DISCOVERY")["disposition"],"REUSABLE_WITH_DISCLOSURE")
    def test_protected_requires_authority(self):
        pid=self.r["resources"][0]["population_id"]
        with self.assertRaises(PopulationRegisterError): record_allocation(self.r,{"allocation_id":"A1","population_id":pid,"programme_id":"X","role":"VALIDATION","state":"RESERVED_UNCONSUMED"})
    def test_validation_reservation_rejects_locator(self):
        pid=self.r["resources"][0]["population_id"]
        with self.assertRaises(PopulationRegisterError): record_allocation(self.r,{"allocation_id":"A1","population_id":pid,"programme_id":"X","role":"VALIDATION","state":"RESERVED_UNCONSUMED","authority_ref":"G0:PASS","read_path":"secret"})
    def test_exposure_irreversible_and_blocks_untouched_validation(self):
        pid=self.r["resources"][0]["population_id"]
        r2=record_exposure(self.r,{"event_id":"E1","population_id":pid,"programme_id":"X","study_id":"S1","channel":"HUMAN","observed_at":"2026-09-22T00:00:00Z","source_ref":"RESULT:1"})
        self.assertEqual(eligibility(r2,pid,"VALIDATION")["disposition"],"NOT_UNTOUCHED_FOR_INDEPENDENT_VALIDATION")
        with self.assertRaises(PopulationRegisterError): record_exposure(r2,{"event_id":"E1","population_id":pid,"programme_id":"X","channel":"SUMMARY","observed_at":"2026-09-22T00:00:01Z","source_ref":"RESULT:2"})

if __name__=="__main__": unittest.main()
