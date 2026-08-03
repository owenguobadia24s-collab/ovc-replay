from __future__ import annotations
import copy, json, unittest
from pathlib import Path
from ovc.research_operations.mta.g8_gate import MTAG8GateError, validate_packet
ROOT=Path(__file__).resolve().parents[3]
PACKET=json.loads((ROOT/"docs/releases/market-translation-audit-v0-2/mta-g8/MTA_G8_CONSOLIDATED_OPERATOR_DECISION_PACKET.json").read_text())
class MTAG8Tests(unittest.TestCase):
 def test_packet_passes(self): self.assertEqual(validate_packet(PACKET)["status"],"PASS")
 def test_premature_decision_blocks(self):
  value=copy.deepcopy(PACKET); value["decisions"]["MTA-G8-CLOCK"]["recorded_decision"]="PASS"
  with self.assertRaises(MTAG8GateError): validate_packet(value)
 def test_c3_promotion_blocks(self):
  value=copy.deepcopy(PACKET); value["recommended_consolidated_decision"]["MTA-G8-C3"]="PASS"
  with self.assertRaises(MTAG8GateError): validate_packet(value)
 def test_cross_scale_rule_escape_blocks(self):
  value=copy.deepcopy(PACKET); value["decisions"]["MTA-G8-C2.5"]["bounded_rule_set"].append("LOCAL_PARENT_CONFLICT")
  with self.assertRaises(MTAG8GateError): validate_packet(value)
 def test_authority_escape_blocks(self):
  value=copy.deepcopy(PACKET); value["authority_boundary"]["c2e_activation"]="APPROVED"
  with self.assertRaises(MTAG8GateError): validate_packet(value)
if __name__=="__main__": unittest.main()
