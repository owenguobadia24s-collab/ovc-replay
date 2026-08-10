from __future__ import annotations
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from ovc.opt_b.srfd.serialization import logical_sha256
from ovc.opt_b.srfd.wp10_durable_execution import RunArtifactStore
from ovc.opt_b.srfd.wp10_execution_resilience import RunAuthorityStore, RunCheckpointStore, RunStartReceipt
from ovc.opt_b.srfd.wp10_v10_interface import (
    SCIENCE_IDENTITY_SHA256, V09_RUN_BINDING_SHA256, V09_RUN_ID, V09_TOKEN_ID,
    RunBindingV10, binding_from_manifest,
)
from ovc.opt_b.srfd.wp10_v10_runner import _seed_verified_v09_prefix
from ovc.opt_b.srfd.wp10_v10_storage import ContentAddressedArtifactStoreV10

ROOT=Path(__file__).resolve().parents[2]
CAP=ROOT/'registries/research/srfd/wp10_v10_external_artifact_capacity_t1.json'
MAN=ROOT/'docs/releases/srfd-benchmark-v0-1/srfdi-june-auth-v1-0/SRFD_JUNE_AUTHORITY_MANIFEST_CANDIDATE_v1_0.json'
TOK=ROOT/'docs/releases/srfd-benchmark-v0-1/srfdi-june-auth-v1-0/SRFD_JUNE_AUTHORITY_TOKEN_v1_0.json'
DEC=ROOT/'docs/releases/srfd-benchmark-v0-1/srfdi-june-auth-v1-0/SRFD_JUNE_AUTHORITY_OPERATOR_DECISION_v1_0.json'
QA=ROOT/'docs/releases/srfd-benchmark-v0-1/srfdi-wp10-v1-0/SRFDI_WP10_V10_CAPACITY_REMEDIATION_QA.json'
STATE=ROOT/'registries/implementation/srfd/OVC_SRFDI_STATE_v0_44_WP10_V10_READY.json'
POINTER=ROOT/'registries/implementation/srfd/CURRENT_STATE_POINTER.json'

class SRFDIWP10V10CapacityRemediationTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.cap=json.loads(CAP.read_text()); cls.man=json.loads(MAN.read_text()); cls.tok=json.loads(TOK.read_text()); cls.dec=json.loads(DEC.read_text()); cls.qa=json.loads(QA.read_text()); cls.state=json.loads(STATE.read_text()); cls.pointer=json.loads(POINTER.read_text()); cls.binding=binding_from_manifest(cls.man)
 def test_t1_is_evidence_derived_and_has_reserve(self):
  s=self.cap['sizing']; self.assertEqual(1626,s['completed_v09_unit_count']); self.assertEqual(394,s['remaining_unit_count']); self.assertEqual(25769803776,s['frozen_max_external_bytes']); self.assertGreaterEqual(s['frozen_max_external_bytes'],s['minimum_30pct_operational_reserve_bound_bytes']); self.assertEqual('EVIDENCE_DERIVED_CONSERVATIVE_BOUND',s['measurement_class']); self.assertEqual('V0_9_FAILURE_WAS_EXTERNAL_BYTES_ONLY',self.cap['unchanged_bounds']['rationale'])
 def test_science_identity_is_unchanged_and_token_is_fresh_single_use(self):
  self.assertEqual(SCIENCE_IDENTITY_SHA256,self.man['science']['science_identity_sha256']); self.assertEqual('NONE_EXACT_SAME_EXPERIMENT',self.man['science']['delta']); self.assertNotEqual(V09_TOKEN_ID,self.tok['token_id']); self.assertEqual('AUTHORIZED_UNCONSUMED',self.tok['state']); self.assertTrue(self.tok['single_use']); self.assertEqual('ONE_EXACT_BOUND_RUN',self.tok['run_cardinality']); self.assertEqual(self.binding.logical_hash,self.tok['run_binding_sha256'])
 def test_storage_and_authority_firewalls(self):
  self.assertEqual('CONTENT_ADDRESSED_CHUNKED_COMPRESSED',self.cap['storage']['layout']); self.assertEqual('EXTERNAL_ONLY',self.cap['storage']['large_payload_location']); self.assertEqual('NONE',self.dec['authority_delta']['science_delta']); self.assertEqual('NONE',self.dec['authority_delta']['active_selector']); self.assertEqual('DENIED',self.tok['provider_fetch']); self.assertEqual('LOCKED_UNCONSUMED',self.tok['validation_2025']); self.assertEqual('PASS_READY_FOR_EXACT_SINGLE_USE_RUN',self.qa['status'])
 def test_programme_state_is_ready_but_scope_stops_before_token_consumption(self):
  self.assertEqual('READY',self.state['status']); self.assertEqual('SRFDI-WP10-v1.0',self.state['active_packet']); self.assertFalse(self.state['operator_decision_required']); self.assertEqual(self.tok['token_id'],self.state['authority']['fresh_authority_token_id']); self.assertFalse(self.state['authority']['fresh_authority_token_consumed']); self.assertEqual('AUTHORIZED_UNCONSUMED',self.state['authority']['fresh_authority_token_state']); self.assertEqual('STOP_SCOPE_COMPLETE_V10_RUN_AUTHORITY_READY_UNCONSUMED',self.state['next_action'])
  self.assertEqual('READY',self.pointer['status']); self.assertEqual('SRFDI-WP10-v1.0',self.pointer['active_packet']); self.assertEqual(self.tok['token_id'],self.pointer['fresh_authority_token_id']); self.assertFalse(self.pointer['fresh_authority_token_consumed']); self.assertEqual(self.binding.logical_hash,self.pointer['run_binding_sha256']); self.assertEqual('T1_EXTERNAL_ARTIFACT',self.pointer['capacity_tier']); self.assertEqual(25769803776,self.pointer['max_external_output_bytes']); self.assertEqual(1626,self.pointer['reuse_candidate_v09_prefix_count']); self.assertEqual(0,self.pointer['verified_reused_v09_unit_count']); self.assertEqual('FORBIDDEN',self.pointer['v09_checkpoint_relabel']); self.assertEqual('STOP_SCOPE_COMPLETE_V10_RUN_AUTHORITY_READY_UNCONSUMED',self.pointer['next_action'])
  self.assertEqual('DENIED',self.pointer['provider_fetch']); self.assertEqual('LOCKED_UNCONSUMED',self.pointer['validation_2025']); self.assertEqual('NONE',self.pointer['scientific_promotion']); self.assertEqual('NONE',self.pointer['selector_family_semantic_publication']); self.assertEqual('NONE',self.pointer['probability_risk_exposure_execution'])
 def test_content_addressed_store_round_trip_preserves_logical_output(self):
  with TemporaryDirectory() as td:
   start=RunStartReceipt('RUN.NEW','TOKEN.NEW',self.binding.logical_hash,'CONSUMPTION.NEW')
   store=ContentAddressedArtifactStoreV10(Path(td),max_external_bytes=50_000_000)
   output={'schema':'fixture/v1','values':list(range(1000)),'logical_hash':'fixture-not-identity'}
   r=store.commit_output(start,self.binding,'unit/1',output); loaded=store.load_output(start,self.binding,'unit/1')
   self.assertEqual(output,loaded); self.assertEqual(logical_sha256(output),r.output_logical_hash)
   manifests=list((Path(td)/'runs'/'RUN.NEW'/'artifacts_v10'/'manifests').glob('*.json')); chunks=list((Path(td)/'runs'/'RUN.NEW'/'artifacts_v10'/'cas').rglob('*.gz'))
   self.assertEqual(1,len(manifests)); self.assertGreaterEqual(len(chunks),1)
 def test_v09_output_reuse_creates_new_checkpoint_not_relabel(self):
  with TemporaryDirectory() as old_td, TemporaryDirectory() as new_td:
   class OldBinding: logical_hash=V09_RUN_BINDING_SHA256
   old_binding=OldBinding(); old_auth=RunAuthorityStore(Path(old_td)); old_start=old_auth.consume({'token_id':V09_TOKEN_ID,'state':'AUTHORIZED_UNCONSUMED','run_binding_sha256':V09_RUN_BINDING_SHA256},old_binding)
   self.assertEqual(V09_RUN_ID,old_start.run_id)
   old_store=RunArtifactStore(Path(old_td),max_external_bytes=10_000_000); output={'schema':'reuse-fixture/v1','value':7}; old_receipt=old_store.commit_output(old_start,old_binding,'population',output); old_cp=RunCheckpointStore(Path(old_td)).commit(old_start,old_binding,[old_receipt])
   new_auth=RunAuthorityStore(Path(new_td)); new_start=new_auth.consume(self.tok,self.binding); new_store=ContentAddressedArtifactStoreV10(Path(new_td),max_external_bytes=50_000_000); new_cpstore=RunCheckpointStore(Path(new_td))
   reuse=_seed_verified_v09_prefix(new_start=new_start,binding=self.binding,v09_root=Path(old_td),checkpoint_store=new_cpstore,artifact_store=new_store,ordered_units=('population',),max_units=1)
   self.assertEqual(1,reuse['verified_reused_prefix_count']); self.assertEqual(old_cp.checkpoint_id,reuse['source_checkpoint_id']); self.assertNotEqual(old_cp.checkpoint_id,reuse['new_checkpoint_id']); self.assertFalse(reuse['old_checkpoint_relabelled']); self.assertEqual(output,new_store.load_output(new_start,self.binding,'population'))

if __name__=='__main__': unittest.main()
