from __future__ import annotations
import json
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4]
REL=Path("docs/releases/c2-anatomy-observation-redesign-v0-2/c2ar-wp0")
REG=Path("registries/opt_b/c2/anatomy_redesign")
SCHEMA=Path("schemas/opt_b/c2/anatomy_redesign")
def load(p): return json.loads((ROOT/p).read_text(encoding="utf-8"))
class C2ARWP0Tests(unittest.TestCase):
 def test_source_and_baseline_are_bound(self):
  packet=load(REL/"C2AR_WP0_SOURCE_AND_BASELINE_PACKET.json")
  by={x["role"]:x for x in packet["source_bindings"]["sources"]}
  self.assertEqual("b76fb70533ccba161eb9d043f393ff875a3bcf8170009dc0a380c234a04f628d",by["GOVERNING_IMPLEMENTATION_PLAN"]["sha256"])
  self.assertEqual("d51ab109481c4a4f84c5fd955c56521e1d27c853bb568168dc689bf5f5bbf1c9",by["GOVERNING_DESIGN"]["sha256"])
  self.assertFalse(by["SUPERSEDED_IMPLEMENTATION_PLAN"]["governing"]); self.assertIsNone(by["SUPERSEDED_IMPLEMENTATION_PLAN"]["sha256"])
  base=packet["baseline_manifest"]; self.assertEqual("a15301935c037b64cd459da49dd6a75a58014b25",base["lawful_main_tip"]); self.assertEqual("SATISFIED",base["prerequisite"]["status"])
 def test_active_selector_unchanged(self):
  text=(ROOT/"registries/opt_b/c2/C2_ACTIVE_SELECTORS.yaml").read_text()
  self.assertIn("release_id: OPT-B.C2.GBPUSD.DISCOVERY.2021_2023.v2",text); self.assertIn("validation_consumption: LOCKED_UNCONSUMED",text)
  snap=load(REL/"C2AR_WP0_SOURCE_AND_BASELINE_PACKET.json")["active_c2_snapshot"]; self.assertTrue(snap["read_only"]); self.assertEqual(0,snap["expected_drift_count"])
 def test_legacy_inventory_paths_exist(self):
  packet=load(REL/"C2AR_WP0_LEGACY_AND_CROSSWALK_INVENTORY.json"); legacy=packet["legacy_anatomy"]
  required={"OBSERVATION_AND_STATE","PARAMETERS_AND_AXES","LEVELS","CONTAINERS","RELATIONS","PARENT_CONTEXT","TRANSITIONS","TRIGGERS_AND_CANDIDATE_WINDOWS","QUALITY_AND_ASSURANCE","RELEASE_AND_AUTHORITY"}
  self.assertEqual(required,{x["domain"] for x in legacy["groups"]}); self.assertEqual([],legacy["missing_required_domains"])
  for group in legacy["groups"]:
   for path in group["paths"]: self.assertTrue((ROOT/path).exists(),path)
 def test_state_graph_maturity_and_crosswalk(self):
  marker=load(REG/"OVC_C2AR_PROGRAMME_STATE_v0_2.json"); self.assertNotIn("programme_id",marker); self.assertEqual("ACTIVE_POINTER",marker["status"])
  state=load(REG/"OVC_C2AR_PROGRAMME_STATE_v0_2.jsonc"); graph=state["packet_gate_registry"]; maturity=state["contract_maturity_registry"]; cross=state["crosswalk_ownership"]
  self.assertEqual("C2AR-G5.5",graph["invariants"]["synthetic_smoke_before_g6"]); self.assertEqual(["CEAR-G6","CEAR-G7","CEAR-G8","CEAR-G9","CEAR-G10"],graph["invariants"]["operator_required_gates"])
  self.assertIn("ACTIVE_SELECTOR",maturity["states"]["SHADOW_EXPERIMENT"]["prohibited"]); self.assertEqual("CEAR-G6_OPERATOR_REQUIRED",maturity["states"]["SHADOW_EXPERIMENT"]["freeze"])
  self.assertEqual("ACTIVATION_PLAN_APPROVED",cross["freeze_trigger"]); self.assertEqual("PERMANENT",cross["runtime_deprecation"]["historical_records"])
  self.assertEqual("NONE",state["authority"]["selector_release_publication"]); self.assertEqual("C2AR-G0A",state["current_gate"])
 def test_schema_capacity_and_gate_fail_closed(self):
  bundle=load(SCHEMA/"C2AR_WP0_SCHEMA_BUNDLE_v0_1.json"); self.assertEqual(3,len(bundle["schemas"]))
  for value in bundle["schemas"].values(): self.assertFalse(value["additionalProperties"]); self.assertTrue(value["required"])
  text=(ROOT/"contracts/opt_b/c2/anatomy_redesign/C2AR_AUTHORITY_CAPACITY_AND_ARTIFACT_CONTRACT_v0_1.md").read_text(); self.assertIn("CAPACITY_EXCEEDED",text); self.assertIn("Silent sampling",text); self.assertIn("R2 write authority is none",text)
  gate=load(REL/"C2AR_WP0_QA_AND_G0A_GATE_PACKET.json")["gate"]; self.assertEqual("AUTO_RATIFIABLE",gate["gate_class"]); self.assertFalse(gate["operator_decision_required"]); self.assertEqual([],gate["blocking_warnings"]); self.assertIn("NO_ACTIVE_C2_DRIFT",gate["acceptance_conditions"])
if __name__=="__main__": unittest.main()
