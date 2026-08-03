from __future__ import annotations
import copy, json, unittest
from pathlib import Path
from ovc.research_operations.mta.readiness_synthesis import MTAWP7SynthesisError, ROUTES, route_payload, validate_fixture, validate_reference
ROOT=Path(__file__).resolve().parents[3]
REF=json.loads((ROOT/"docs/releases/market-translation-audit-v0-2/mta-g7/MTA_WP7_READINESS_SYNTHESIS_REFERENCE.json").read_text())
FIX=json.loads((ROOT/"fixtures/research_operations/mta/MTA_WP7_ROUTE_FIXTURES_v0_1.json").read_text())
class MTAWP7Tests(unittest.TestCase):
 def test_reference_passes(self): self.assertEqual(validate_reference(REF)["status"],"PASS")
 def test_fixture_passes(self): self.assertEqual(validate_fixture(FIX)["routes"],9)
 def test_every_route_resolves(self):
  for route in ROUTES: self.assertEqual(route_payload(REF,route)["status"],"AVAILABLE_LOCAL_READ_ONLY")
 def test_unknown_route_blocks(self):
  with self.assertRaises(MTAWP7SynthesisError): route_payload(REF,"/execute")
 def test_authority_escape_blocks(self):
  value=copy.deepcopy(REF); value["authority"]["c2e_c2_5_c3_activation"]="APPROVED"
  with self.assertRaises(MTAWP7SynthesisError): validate_reference(value)
 def test_cross_scale_promotion_blocks(self):
  value=copy.deepcopy(REF); value["readiness"]["c2_5"]["rule_assessments"]["LOCAL_PARENT_CONFLICT"]["disposition"]="PLAN_ELIGIBLE"
  with self.assertRaises(MTAWP7SynthesisError): validate_reference(value)
 def test_ro4_overclaim_blocks(self):
  value=copy.deepcopy(REF); value["ro4_comparison"]["direct_comparison_status"]="AGREEMENT"
  with self.assertRaises(MTAWP7SynthesisError): validate_reference(value)
if __name__=="__main__": unittest.main()
