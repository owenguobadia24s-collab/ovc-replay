from __future__ import annotations
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'docs/releases/srfd-benchmark-v0-1/srfdi-wp10-v0-7'
BLOCKER = BASE / 'SRFDI_WP10_V07_EXECUTION_BLOCKER.json'
START = BASE / 'SRFDI_WP10_V07_RUN_START_RECEIPT.json'
PREFLIGHT = BASE / 'SRFDI_WP10_V07_PREFLIGHT_RECEIPT.json'
CHECKPOINT = BASE / 'SRFDI_WP10_V07_CHECKPOINT_00000001.json'
POPULATION = BASE / 'SRFDI_WP10_V07_POPULATION_ARTIFACT.json'
CAPACITY = BASE / 'SRFDI_WP10_V07_CAPACITY_TELEMETRY_AT_BLOCKER.json'
STATE = ROOT / 'registries/implementation/srfd/OVC_SRFDI_STATE_v0_27_WP10_V07_SEGMENTATION_BINDING_BLOCKED.json'
RUN_ID = 'SRFD.RUN.be74524955a4168484d21d91aee067e084e64be0178ed976bc4824369f7d8513'
TOKEN_ID = 'SRFD.JUNE.AUTH.7b9799d46cb6b3953fa9e96fb8309fbdeb0afe6dd53bfdcd16dec9cb85728ad0'
RUN_BINDING = '25f1c18d39898b5f2b5e9511245ecfd2615eb420205e68f9f1e8c7fe7f929fb9'

class SRFDIWP10V07SegmentationBindingBlockerTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.blocker=json.loads(BLOCKER.read_text()); cls.start=json.loads(START.read_text()); cls.preflight=json.loads(PREFLIGHT.read_text()); cls.checkpoint=json.loads(CHECKPOINT.read_text()); cls.population=json.loads(POPULATION.read_text()); cls.capacity=json.loads(CAPACITY.read_text()); cls.state=json.loads(STATE.read_text())
 def test_external_receipt_metadata_and_semantic_copies_are_preserved(self):
  receipts=self.blocker['receipts']; self.assertEqual('c70cbf50f2f7ec10a41eb65f94510bee66ab52f31ba56713ad21b7296b77b991',receipts['run_start']['file_sha256']); self.assertEqual('f38dd025b7903c3b4cdb3adc7324b6b97409bcac8c4cbdd4759882b75115b932',receipts['preflight']['file_sha256']); self.assertEqual(receipts['run_start']['consumption_id'],self.start['consumption_id']); self.assertEqual(receipts['checkpoint_00000001']['checkpoint_id'],self.checkpoint['checkpoint_id']); self.assertEqual(receipts['population_artifact']['output_logical_hash'],self.population['output_logical_hash']); self.assertEqual(receipts['capacity_telemetry']['accounted_unit_count'],self.capacity['accounted_unit_count']); self.assertEqual(receipts['preflight']['logical_hash'],self.preflight['logical_hash'])
 def test_token_is_consumed_exactly_for_preserved_run(self):
  self.assertEqual(TOKEN_ID,self.start['token_id']); self.assertEqual(RUN_ID,self.start['run_id']); self.assertEqual(RUN_BINDING,self.start['run_binding_sha256']); self.assertEqual('CONSUMED_FOR_RUN',self.start['state'])
 def test_population_only_committed_before_segmentation_block(self):
  self.assertEqual(['population'],self.checkpoint['completed_units']); self.assertEqual(1,self.checkpoint['sequence']); self.assertEqual('COMMITTED',self.checkpoint['state']); self.assertEqual(8598,self.population['output']['eligible_record_count']); self.assertEqual(36,self.population['output']['comparability_domain_count']); self.assertEqual(1944,self.population['output']['family_configuration_count']); self.assertEqual('WITHIN_T0',self.capacity['capacity_status']); self.assertEqual(1,self.capacity['accounted_unit_count'])
 def test_segmentation_mismatch_is_exact_and_fail_closed(self):
  failure=self.blocker['failure']; self.assertEqual('SEGMENTATION_BINDING_MISMATCH',failure['reason_code']); self.assertEqual('segmentation/RUN_CHANGE_SEGMENTATION',failure['stage']); self.assertEqual({'stream_count':264,'segment_count':7609,'boundary_count':7345},failure['expected']); self.assertEqual({'stream_count':232,'segment_count':7013,'boundary_count':6781},failure['actual']); self.assertFalse(failure['segmentation_artifact_committed']); self.assertEqual('BLOCKED_CONSUMED_RUN_PRESERVED',self.blocker['status'])
 def test_historical_blocker_state_is_pointer_independent(self):
  self.assertEqual('BLOCKED',self.state['status']); self.assertEqual('NONE_UNDER_CURRENT_STANDING_DELEGATION_AFTER_HARD_STOP',self.state['remediation_authority']); self.assertEqual('PRESERVE_EVIDENCE_AND_STOP_FAIL_CLOSED_NO_ROUTINE_OPERATOR_APPROVAL_REQUEST',self.state['next_action'])
if __name__ == '__main__': unittest.main()
