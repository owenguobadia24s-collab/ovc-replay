from __future__ import annotations
import json, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
PACKET=ROOT/'artifacts/research_console_vnext/pvs3/RCN_RN_G4_GATE_PACKET.json'; STATE=ROOT/'registries/implementation/research_console_vnext/OVC_RCN_RN_STATE_v0_2.json'; CAND=ROOT/'registries/research_console_vnext/research_native/wp4a_investigate_binding_candidates_v1.json'; INV=ROOT/'registries/research_console_vnext/research_native/source_adapter_inventory_v2.json'
def load(p): return json.loads(p.read_text(encoding='utf-8'))
class RcnRnG4GateReady(unittest.TestCase):
 def test_consolidated_operator_packet_is_complete_and_pending(self):
  g=load(PACKET); self.assertEqual(g['gate_id'],'RCN-RN-G4'); self.assertEqual(g['gate_class'],'OPERATOR_REQUIRED'); self.assertEqual(g['allowed_decisions'],['PASS','DEFER','BLOCK','QUARANTINE','SUPERSEDE']); self.assertEqual(g['recommended_decision'],'PASS'); self.assertEqual(g['decision_record'],'PENDING_OPERATOR_DECISION'); self.assertEqual(g['blockers'],[]); self.assertEqual(g['unresolved_issues'],[]); self.assertIn('rollback',g); self.assertTrue(g['exact_work_after_pass']); self.assertEqual(g['external_artifacts'],[])
 def test_proposed_delta_matches_predeclared_owner_candidates_only(self):
  g=load(PACKET); c=load(CAND); inv=load(INV); proposed={x['capability_id'] for x in g['proposed_authority_delta']['candidates']}; declared={x['capability_id'] for x in c['candidates']}; self.assertEqual(proposed,declared); self.assertEqual(proposed,{'MARKET','C1','C2','C2E'}); excluded={x['capability_id'] for x in g['proposed_authority_delta']['excluded']}; self.assertEqual(excluded,{'C2P','C2_5','C3'}); census={x['capability_id']:x for x in inv['sources']}; self.assertTrue(census['opt_a']['repository_materialized']); self.assertTrue(census['c1']['repository_materialized']); self.assertTrue(census['c2']['repository_materialized']); self.assertTrue(census['c2e']['repository_materialized']); self.assertTrue(census['c2p']['repository_materialized']); self.assertFalse(census['c2p']['runtime_owner_materialized']); self.assertEqual('NONE',census['c2p']['active_source_authority']); self.assertEqual('DENIED',census['c2p']['real_route']); self.assertFalse(census['c2_5']['repository_materialized']); self.assertFalse(census['c3']['repository_materialized'])
 def test_gate_ready_state_does_not_grant_authority(self):
  s=load(STATE); self.assertEqual(s['packet_id'],'RCN-RN-G4'); self.assertEqual(s['status'],'GATE_READY'); self.assertEqual(s['current_authority'],'FIXTURE_ONLY_LOCAL_READ_ONLY'); self.assertEqual(s['real_source_routes'],'DENIED_UNTIL_RCN_RN_G4'); self.assertEqual(s['authority_required'],'OPERATOR_REQUIRED'); self.assertIsNone(s['decision_record']); self.assertEqual(s['blockers'],[])
 def test_scientific_and_upper_layer_firewalls_are_explicit(self):
  text=PACKET.read_text(encoding='utf-8');
  for marker in ['NO_NEW_PROVIDER_INTAKE','NO_NEW_INSTRUMENT_MARKET_CLOCK_SIDE_OR_UNDECLARED_DEPENDENCY','NO_SELECTOR_THRESHOLD_MODEL_FAMILY_CANDIDATE_THEORY_SEMANTIC_ACTIVATION','NO_VALIDATION','NO_PUBLICATION','NO_PROBABILITY_RISK_EXPOSURE_TRADING_EXECUTION','C2.5 Candidate != EventOccurrence','C3 connectivity != entailment','C2P conformance namespace presence does not grant runtime or source authority']:
   self.assertIn(marker,text)
if __name__=='__main__': unittest.main()
