from __future__ import annotations
import copy, json, unittest
from pathlib import Path
from ovc.research_operations.mta.clock_parent_audit import MTAWP4AuditError, validate_fixture, validate_reference
ROOT=Path(__file__).resolve().parents[3]
REF=json.loads((ROOT/"docs/releases/market-translation-audit-v0-2/mta-g4/MTA_WP4_CLOCK_PARENT_AUDIT_REFERENCE.json").read_text())
FIX=json.loads((ROOT/"fixtures/research_operations/mta/MTA_WP4_PARENT_EVENT_FIXTURE_v0_1.json").read_text())
class MTAWP4Tests(unittest.TestCase):
 def test_reference_passes(self): self.assertEqual(validate_reference(REF)["status"],"PASS")
 def test_fixture_passes(self): self.assertEqual(validate_fixture(FIX)["status"],"PASS")
 def test_future_parent_usage_blocks(self):
  value=copy.deepcopy(REF); value["sides"]["BID"]["fifteen_minute_resolutions"]["future_parent_usage"]=1
  with self.assertRaises(MTAWP4AuditError): validate_reference(value)
 def test_unknown_reset_blocks(self):
  value=copy.deepcopy(REF); value["sides"]["ASK"]["reset_census"]["unknown_count"]=1
  with self.assertRaises(MTAWP4AuditError): validate_reference(value)
 def test_clock_authority_escape_blocks(self):
  value=copy.deepcopy(REF); value["clock_change"]="APPROVED"
  with self.assertRaises(MTAWP4AuditError): validate_reference(value)
 def test_mapping_mutation_blocks(self):
  value=copy.deepcopy(REF); value["a_l_mapping"][0]["start_hour_utc"]=1
  with self.assertRaises(MTAWP4AuditError): validate_reference(value)
if __name__=="__main__": unittest.main()
