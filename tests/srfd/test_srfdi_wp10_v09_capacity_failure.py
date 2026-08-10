from __future__ import annotations
import json
from pathlib import Path
import unittest
from srfd._current_pointer_compat import assert_lawful_v10_pointer
ROOT=Path(__file__).resolve().parents[2]
F=ROOT/'docs/releases/srfd-benchmark-v0-1/srfdi-wp10-v0-9/SRFDI_WP10_V09_CAPACITY_EXCEEDED_EXTERNAL_BYTES.json'
Q=ROOT/'docs/releases/srfd-benchmark-v0-1/srfdi-wp10-v0-9/SRFDI_WP10_V09_CAPACITY_FAILURE_QA_PACKET.json'
S=ROOT/'registries/implementation/srfd/OVC_SRFDI_STATE_v0_43_WP10_V09_CAPACITY_BLOCKED.json'
P=ROOT/'registries/implementation/srfd/CURRENT_STATE_POINTER.json'
RUN='SRFD.RUN.25ca319a998d72fb01e0dceff2d455f7abf71a4e6419987246529407467e51e5'
TOKEN='SRFD.JUNE.AUTH.a5311fbade60d87553ad76b9085e1bd2ba62fe60c6d9654a2d338b624b5498c3'
class SRFDIWP10V09CapacityFailureTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls): cls.f=json.loads(F.read_text()); cls.q=json.loads(Q.read_text()); cls.s=json.loads(S.read_text()); cls.p=json.loads(P.read_text())
 def test_v09_is_blocked_not_completed(self):
  self.assertEqual('BLOCKED_PRESERVED_NOT_COMPLETED',self.f['status']); self.assertEqual('BLOCKED',self.s['status']); self.assertEqual(RUN,self.f['run_id'])
  if assert_lawful_v10_pointer(self,self.p): return
  self.assertEqual('BLOCKED',self.p['status'])
 def test_exact_progress_and_capacity_failure_are_visible(self):
  self.assertEqual(1626,self.f['work_units']['completed_unit_count']); self.assertEqual(394,self.f['work_units']['remaining_unit_count']); self.assertEqual(10737418240,self.f['capacity']['max_external_output_bytes']); self.assertEqual(10620989538,self.f['capacity']['committed_external_bytes_before_blocked_write']); self.assertEqual(10921694766,self.f['capacity']['blocked_projected_external_bytes']); self.assertEqual('CAPACITY_EXTERNAL_BYTES_EXCEEDED',self.f['runtime_reason_code'])
 def test_token_and_checkpoint_history_fail_closed(self):
  self.assertEqual(TOKEN,self.f['authority']['token_id']); self.assertEqual('CONSUMED_FOR_RUN_NOT_REUSABLE_FOR_NEW_RUN',self.f['authority']['token_state']); self.assertIn('MUST_NOT_BE_RELABELED',self.f['checkpoint_lineage']['preservation_rule']); self.assertEqual(1626,self.f['checkpoint_lineage']['last_known_committed_sequence'])
 def test_blocker_artifact_is_failure_evidence_only(self):
  b=self.f['blocked_artifact_evidence']; self.assertEqual('1W1TQV0A1epj5BdrfWTJiInr8zTWqZuKA',b['drive_file_id']); self.assertEqual(72497804,b['compressed_bytes']); self.assertEqual(300704713,b['raw_json_bytes']); self.assertEqual('8f84f8ed966db8d5ced5bfda32eb02f5da2fcc0f006a945e9886b83afac9eaa7',b['raw_json_sha256']); self.assertEqual('c8ff0d7956e5692e08bcb3a91007f76e886ca402199cd959d2168f055f9339e6',b['output_logical_hash']); self.assertEqual('FAILURE_EVIDENCE_ONLY_NOT_COMMITTED_AS_V0_9_RUN_OUTPUT',b['admission_status'])
 def test_pointer_routes_only_to_remediation(self):
  if assert_lawful_v10_pointer(self,self.p):
   self.assertEqual('PASS_EVIDENCE_PRESERVATION',self.q['status']); return
  self.assertEqual('SRFDI-WP10-v1.0-CAPACITY-REMEDIATION',self.p['next_packet']); self.assertEqual('DENIED',self.p['provider_fetch']); self.assertEqual('LOCKED_UNCONSUMED',self.p['validation_2025']); self.assertEqual('NONE',self.p['scientific_promotion']); self.assertEqual('NONE',self.p['selector_family_semantic_publication']); self.assertEqual('NONE',self.p['probability_risk_exposure_execution']); self.assertEqual('PASS_EVIDENCE_PRESERVATION',self.q['status'])
if __name__=='__main__': unittest.main()
