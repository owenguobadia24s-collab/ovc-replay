from __future__ import annotations
import copy,json,unittest
from pathlib import Path
from ovc.research_operations.clock_continuity.review import CCRAuditError,build_read_model,validate_reference
ROOT=Path(__file__).resolve().parents[3]
REF=json.loads((ROOT/"docs/releases/clock-continuity-review-v0-1/ccr-wp1/CCR_FULL_AUDIT_REFERENCE.json").read_text())
class CCRReviewTests(unittest.TestCase):
 def test_reference_passes(self): self.assertEqual(validate_reference(REF)["status"],"PASS")
 def test_read_model_is_read_only(self):
  value=build_read_model(REF); self.assertTrue(value["read_only"]); self.assertEqual(value["activation"],"DENIED")
 def test_fourth_variant_blocks(self):
  value=copy.deepcopy(REF); value["variants"]["V3"]={}
  with self.assertRaises(CCRAuditError): validate_reference(value)
 def test_created_bar_blocks(self):
  value=copy.deepcopy(REF); value["variants"]["V1_PLANNED_CLOSURE_CLASSIFIED_CONTINUITY_SHADOW_ONLY"]["bars_created"]=1
  with self.assertRaises(CCRAuditError): validate_reference(value)
 def test_activation_blocks(self):
  value=copy.deepcopy(REF); value["recommendation"]["activation"]="APPROVED"
  with self.assertRaises(CCRAuditError): validate_reference(value)
 def test_gate_is_operator_required(self):
  gate=json.loads((ROOT/"docs/releases/clock-continuity-review-v0-1/ccr-g5/CCR_G5_OPERATOR_GATE_PACKET.json").read_text())
  self.assertTrue(gate["operator_decision_required"]); self.assertEqual(gate["status"],"GATE_READY")
  self.assertEqual(gate["authority_boundary"]["continuity_change_or_activation"],"DENIED")
if __name__=="__main__": unittest.main()
