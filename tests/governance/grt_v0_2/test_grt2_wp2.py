from __future__ import annotations
import json, unittest
from pathlib import Path
from ovc.programme_genesis.grt_v0_2.debt import *
ROOT=Path(__file__).resolve().parents[3]; BASE=ROOT/"registries/governance/grt_v0_2/baseline"; DOCS=ROOT/"docs/programmes/grt-v0-2/wp2"
def rows(): return [json.loads(x) for x in (BASE/"GRT_B0_BASELINE_MEMBERS_v0_1.jsonl").read_text(encoding="utf-8").splitlines() if x]
class GRT2WP2Tests(unittest.TestCase):
 def test_b0_exact(self):
  data=rows(); self.assertEqual(len(data),569); validate_baseline_members(data); self.assertEqual(baseline_membership_sha256(data),B0_MEMBERSHIP_SHA256); self.assertEqual([r["ordinal"] for r in data],list(range(1,570))); self.assertTrue(all(r["mapping_status"]=="PENDING_WP3_ARTIFACT_GRAPH" and r["mapped_finding_id"] is None and r["disposition"] is None for r in data))
 def test_finding_identity_and_extent(self):
  a=finding_id("GRT-R001","repo://A","PRIMARY",None); b=finding_id("GRT-R001","repo://A","PRIMARY",None); self.assertEqual(a,b); self.assertEqual(compare_debt_extent({"x":1},{"x":1}),"UNCHANGED"); self.assertEqual(compare_debt_extent({"x":2},{"x":1}),"REDUCED"); self.assertEqual(compare_debt_extent({"x":1},{"x":2}),"EXPANDED"); self.assertEqual(compare_debt_extent({"x":2,"y":1},{"x":1,"y":2}),"MATERIAL_CHANGED")
 def test_admission_and_lineage(self):
  self.assertEqual(classify_debt_transition(predecessor_state="ABSENT",candidate_state="ACTIONABLE"),("NEW_ACTIONABLE","FAIL")); self.assertEqual(classify_debt_transition(predecessor_state="GRANDFATHERED",candidate_state="ACTIONABLE",extent_result="REDUCED"),("BASELINE_REDUCED","PASS")); f1=finding_id("GRT-R001","repo://A","PRIMARY"); f2=finding_id("GRT-R001","repo://B","PRIMARY"); line=make_lineage([f1],[f2],"MOVE",["proof"]); validate_lineage(line)
 def test_floor_mechanics_without_gen0_activation(self):
  c=json.loads((ROOT/"registries/governance/grt_v0_2/GRT_REPOSITORY_CONSTITUTION_v0_2.json").read_text()); f=propose_debt_floor(generation=0,predecessor_commit="1"*40,predecessor_tree="2"*40,constitution_hash=c["canonical_hash"],open_grandfathered_findings=["F1"]); validate_debt_floor(f); self.assertFalse((BASE/"GRT_DEBT_FLOOR_G0.json").exists())
 def test_current_classification_does_not_overclaim(self):
  s=json.loads((DOCS/"GRT2_WP2_CURRENT_CLASSIFICATION_STATUS.json").read_text()); self.assertFalse(s["classification_complete"]); self.assertTrue(s["zero_transition_debt_claim_prohibited"]); self.assertEqual((BASE/"GRT_LATE_PREEXISTING_FINDINGS.jsonl").read_text(),""); self.assertEqual((BASE/"GRT_PRE_G3_TRANSITION_DEBT.jsonl").read_text(),"")
if __name__=="__main__": unittest.main()
