from __future__ import annotations
import json,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'docs/releases/market-grammar-empirical-integration-june-v0-1/ei-wp3'
STATE=ROOT/'registries/opt_b/market_grammar/OVC_MG_EI_JUNE_PROGRAMME_STATE_v0_1.jsonc'
WP2=ROOT/'contracts/opt_b/market_grammar/MG_EI_WP2_C2_TO_C2G_STRUCTURAL_PROJECTION_CONTRACT_v0_1.md'
def load(path): return json.loads(path.read_text(encoding='utf-8'))
class EmpiricalIntegrationWp3BlockerTests(unittest.TestCase):
 def test_compatibility_audit_proves_missing_measurement_surface(self):
  audit=load(BASE/'EI_WP3_EMPIRICAL_SOURCE_COMPATIBILITY_AUDIT.json'); self.assertEqual('BLOCKED_MISSING_GOVERNED_NORMALIZED_AXIS_MEASUREMENT_SURFACE',audit['result']); self.assertFalse(audit['empirical_run_started']); self.assertFalse(audit['observed_empirical_surface']['normalized_measurement_key_present']); self.assertFalse(audit['observed_empirical_surface']['governed_revised_c2_state_stream_artifact_present_in_accepted_manifest'])
  self.assertEqual(33320,audit['accepted_replay_manifest_counts']['records'])
  for artifact in audit['source_artifacts']:
   self.assertEqual(0,artifact['recursive_key_counts']['measurement']); self.assertEqual(0,artifact['recursive_key_counts']['normalized']); self.assertEqual(0,artifact['recursive_key_counts']['normalised'])
 def test_wp2_contract_still_forbids_silent_fallbacks(self):
  text=WP2.read_text(encoding='utf-8').lower(); self.assertIn('no categorical rank',text); self.assertIn('hash embedding',text); self.assertIn('runtime normalization',text); self.assertIn('partial coordinate vectors are prohibited',text)
 def test_qa_marks_blocker_without_invalidating_parent_replay(self):
  qa=load(BASE/'EI_WP3_BLOCKED_QA_PACKET.json'); self.assertEqual('BLOCKED',qa['status']); self.assertEqual('BLOCK',qa['qa_recommendation']); self.assertEqual('MISSING_GOVERNED_NORMALIZED_AXIS_MEASUREMENT_SURFACE',qa['blocker_code']); self.assertEqual('PASS_ZERO',qa['checks']['reserved_authority_exercised']); self.assertIn('THE_ACCEPTED_REPLAY_REMAINS_VALID_FOR_ITS_ORIGINAL_CEAR_G10_PURPOSE',qa['warnings'])
 def test_blocker_packet_requires_governed_resolution(self):
  packet=load(BASE/'EI_WP3_BLOCKER_PACKET.json'); self.assertEqual('BLOCKED',packet['status']); self.assertEqual('BLOCK',packet['recommended_disposition']); self.assertFalse(packet['empirical_run_started']); self.assertEqual([],packet['reserved_actions_taken']); self.assertIn('axis-measurement materialization/normalization contract',packet['smallest_lawful_resolution']['recommended'])
 def test_programme_state_preserves_completed_packets_and_stops_at_wp3(self):
  state=load(STATE); packets={x['packet_id']:x for x in state['packets']}; self.assertEqual('BLOCKED',state['status']); self.assertEqual('EI-WP3',state['next_packet']); self.assertEqual(['MISSING_GOVERNED_NORMALIZED_AXIS_MEASUREMENT_SURFACE'],state['blockers']); self.assertEqual('COMPLETED',packets['EI-WP0']['status']); self.assertEqual('COMPLETED',packets['EI-WP1']['status']); self.assertEqual('COMPLETED',packets['EI-WP2']['status']); self.assertEqual('BLOCKED',packets['EI-WP3']['status']); self.assertEqual('PLANNED',packets['EI-WP4']['status']); self.assertIn('OPERATOR_REQUIRED',packets['EI-WP3']['authority_required'])
if __name__=='__main__': unittest.main()
