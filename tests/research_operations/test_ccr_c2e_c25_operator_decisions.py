from __future__ import annotations
import json
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
class OperatorDispositionTests(unittest.TestCase):
 def load(self,path:str): return json.loads((ROOT/path).read_text(encoding="utf-8"))
 def test_ccr_pass_is_plan_preparation_only(self):
  decision=self.load("docs/releases/clock-continuity-review-v0-1/ccr-g5/CCR_G5_OPERATOR_DECISION.json")
  self.assertEqual(decision["decision"],"PASS"); self.assertEqual(decision["activation"],"DENIED")
  self.assertEqual(decision["approved_delta"],"PREPARE_SEPARATE_OPERATOR_GATED_PLANNED_CLOSURE_CONTINUITY_REMEDIATION_PLAN_ONLY")
  state=self.load("registries/research_operations/clock_continuity/OVC_CCR_PROGRAMME_STATE_v0_1.json")
  self.assertEqual(state["status"],"COMPLETED"); self.assertEqual(state["next_packet"],"PCCR-00_PLAN_PREPARATION")
 def test_c2e_is_blocked_before_wp1(self):
  decision=self.load("docs/releases/c2e-neutral-episode-v0-1/c2e-g1/C2E_G1_OPERATOR_BLOCK_DECISION.json")
  state=self.load("registries/research_operations/c2e/OVC_C2E_PROGRAMME_STATE_v0_1.json")
  self.assertEqual(decision["decision"],"BLOCK"); self.assertEqual(state["status"],"BLOCKED"); self.assertEqual(state["packets"][1]["status"],"BLOCKED"); self.assertIsNone(state["next_packet"])
 def test_c25_is_blocked_before_wp1(self):
  decision=self.load("docs/releases/c2-5-bounded-event-contract-v0-1/c25-g1/C25_G1_OPERATOR_BLOCK_DECISION.json")
  state=self.load("registries/research_operations/c2_5/OVC_C25_PROGRAMME_STATE_v0_1.json")
  self.assertEqual(decision["decision"],"BLOCK"); self.assertEqual(state["status"],"BLOCKED"); self.assertEqual(state["packets"][1]["status"],"BLOCKED"); self.assertIsNone(state["next_packet"])
 def test_multipart_decision_has_no_activation(self):
  value=self.load("docs/releases/research-operations-governance/CCR_C2E_C25_OPERATOR_DECISION_20260803T194600+0100.json")
  self.assertEqual(value["decisions"]["CCR-G5"]["decision"],"PASS"); self.assertEqual(value["decisions"]["C2E-G1"]["decision"],"BLOCK"); self.assertEqual(value["decisions"]["C25-G1"]["decision"],"BLOCK"); self.assertIn("CLOCK_OR_CONTINUITY_ACTIVATION",value["shared_denials"])
if __name__=="__main__": unittest.main()
