from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import random
import unittest
from unittest.mock import patch

from ovc.opt_b.srfd.segmentation_prereg import null_boundary_control_from_c2_ledger, run_change_from_c2_ledger, validate_boundary_pack_registry
from ovc.opt_b.srfd.wp10_v07_contract import FROZEN_SEGMENTATION_PACK_SHA256, WP10RunnerError
from ovc.opt_b.srfd.wp10_v07_runner import execute_segmentation
from ovc.opt_b.srfd.wp10b_segmentation_reference import SegmentationReferenceError, assert_structural_invariants, reference_null_boundary_control_from_c2_ledger, reference_run_change_from_c2_ledger

ROOT=Path(__file__).resolve().parents[2]
RUNNER=ROOT/"src/ovc/opt_b/srfd/wp10_v07_runner.py"; REFERENCE=ROOT/"src/ovc/opt_b/srfd/wp10b_segmentation_reference.py"; SEGMENTATION_REGISTRY=ROOT/"registries/research/srfd/segmentation_boundary_packs_v0_3.json"; POINTER=ROOT/"registries/implementation/srfd/CURRENT_STATE_POINTER.json"
FRESH_V09="SRFD.JUNE.AUTH.a5311fbade60d87553ad76b9085e1bd2ba62fe60c6d9654a2d338b624b5498c3"; V09_BINDING="ca25077124a49a02808ed0c855906456d19415df5371266ebc1e90448d022d9a"

def row(record_id:str,first_valid_time:str,state_key:str,*,side:str="BID",scope_id:str="LOCAL",clock_id:str="15M",reset_reason:str|None=None)->dict[str,object]: return {"source_release_id":"PD-JUNE-FM.RUN.TEST","instrument_id":"GBPUSD","side":side,"scope_id":scope_id,"clock_id":clock_id,"record_id":record_id,"first_valid_time":first_valid_time,"state_key":state_key,"reset_reason":reset_reason}
def adversarial_ledger()->list[dict[str,object]]: return [row("B03","2026-06-01T00:30:00Z","S2"),row("B01","2026-06-01T00:00:00Z","S1"),row("B02","2026-06-01T00:15:00Z","S1"),row("B04","2026-06-01T00:45:00Z","S2",reset_reason="SOURCE_GAP"),row("B05","2026-06-01T01:00:00Z","S3"),row("A02","2026-06-01T00:15:00Z","Q2",side="ASK"),row("A01B","2026-06-01T00:00:00Z","Q1",side="ASK"),row("A01A","2026-06-01T00:00:00Z","Q1",side="ASK"),row("P01","2026-06-01T00:00:00Z","P1",scope_id="PARENT",clock_id="2H"),row("P02","2026-06-01T02:00:00Z","P1",scope_id="PARENT",clock_id="2H")]

class SRFDIWP10BSegmentationReferenceTests(unittest.TestCase):
 def test_run_change_reference_is_byte_semantically_exact(self):
  ledger=adversarial_ledger(); production=run_change_from_c2_ledger(ledger); reference=reference_run_change_from_c2_ledger(ledger); self.assertEqual(production,reference); counts=assert_structural_invariants("RUN_CHANGE_SEGMENTATION",production); self.assertEqual(counts["stream_count"]+counts["boundary_count"],counts["segment_count"])
 def test_null_control_reference_is_byte_semantically_exact(self):
  ledger=adversarial_ledger(); production=null_boundary_control_from_c2_ledger(ledger); reference=reference_null_boundary_control_from_c2_ledger(ledger); self.assertEqual(production,reference); counts=assert_structural_invariants("NULL_BOUNDARY_CONTROL",production); self.assertEqual(counts["stream_count"],counts["segment_count"]); self.assertEqual(0,counts["boundary_count"])
 def test_input_permutation_does_not_change_either_reference_output(self):
  original=adversarial_ledger(); baseline_run=reference_run_change_from_c2_ledger(original); baseline_null=reference_null_boundary_control_from_c2_ledger(original); shuffled=list(original); random.Random(9173).shuffle(shuffled); self.assertEqual(baseline_run,reference_run_change_from_c2_ledger(shuffled)); self.assertEqual(baseline_null,reference_null_boundary_control_from_c2_ledger(shuffled))
 def test_reference_path_does_not_import_production_segmentation_modules(self):
  text=REFERENCE.read_text(); self.assertNotIn("from .segmentation_prereg",text); self.assertNotIn("import segmentation_prereg",text); self.assertNotIn("from .segmentation import",text); self.assertNotIn("import segmentation",text)
 def test_runner_fails_closed_on_reference_inequivalence(self):
  ledger=adversarial_ledger(); drifted=deepcopy(run_change_from_c2_ledger(ledger)); drifted["segments"][0]["authority_state"]="DRIFT"
  with patch("ovc.opt_b.srfd.wp10_v07_runner._segmentation_inputs",return_value=ledger),patch("ovc.opt_b.srfd.wp10_v07_runner.run_change_from_c2_ledger",return_value=drifted):
   with self.assertRaises(WP10RunnerError) as ctx: execute_segmentation([],"RUN_CHANGE_SEGMENTATION")
  self.assertEqual("SEGMENTATION_REFERENCE_INEQUIVALENCE",ctx.exception.reason_code)
 def test_runner_has_no_sample_specific_segmentation_count_target(self):
  text=RUNNER.read_text(); self.assertNotIn("EXPECTED_SEGMENTATION_COUNTS",text)
  for forbidden in ("7609","7345","7013","6781"): self.assertNotIn(forbidden,text)
 def test_frozen_segmentation_registry_is_unchanged(self): self.assertEqual(FROZEN_SEGMENTATION_PACK_SHA256,validate_boundary_pack_registry(json.loads(SEGMENTATION_REGISTRY.read_text())))
 def test_invariant_failures_are_explicit(self):
  with self.assertRaises(SegmentationReferenceError) as ctx: assert_structural_invariants("RUN_CHANGE_SEGMENTATION",{"stream_count":2,"segments":[{}],"boundaries":[]})
  self.assertEqual("SEGMENTATION_STRUCTURAL_INVARIANT_FAILURE",ctx.exception.reason_code)
 def test_authority_pointer_preserves_remediation_history_and_lawful_progression(self):
  p=json.loads(POINTER.read_text()); self.assertIn(p["status"],{"GATE_READY","APPROVED","READY","RUNNING","QA_REVIEW","BLOCKED"}); self.assertIn(p["current_gate"],{"SRFDI-G10B-FREEZE","SRFDI-G-JUNE-AUTH","SRFDI-G10","SRFDI-G10C","SRFDI-G11"}); self.assertTrue(p["authority_token_consumed"]); self.assertEqual("CONSUMED_FOR_RUN_NOT_REUSABLE_FOR_NEW_RUN",p["authority_token_state"])
  if p["current_gate"]=="SRFDI-G10B-FREEZE": self.assertEqual("GATE_READY",p["status"]); self.assertIsNone(p["next_packet"]); self.assertTrue(p["operator_decision_required"]); self.assertEqual("BLOCKED_CONSUMED_RUN_PRESERVED_NO_FRESH_RUN_AUTHORITY",p["june_execution"]); self.assertEqual("COMPLETED_ASSURED_CANDIDATE_PENDING_OPERATOR_FREEZE",p["wp10b_execution"])
  elif p["current_gate"]=="SRFDI-G-JUNE-AUTH" and p["status"]=="GATE_READY": self.assertIsNone(p["next_packet"]); self.assertTrue(p["operator_decision_required"]); self.assertTrue(p["june_execution"].startswith("DENIED")); self.assertIsNone(p["fresh_authority_token_id"]); self.assertEqual("NOT_MINTED_PENDING_OPERATOR",p["fresh_authority_token_state"])
  elif p["current_gate"]=="SRFDI-G-JUNE-AUTH": self.assertFalse(p["operator_decision_required"]); self.assertIsNotNone(p["fresh_authority_token_id"]); self.assertTrue(p["june_execution"].startswith("AUTHORIZED"))
  elif p["current_gate"]=="SRFDI-G10C": self.assertEqual("GATE_READY",p["status"]); self.assertTrue(p["operator_decision_required"]); self.assertIsNone(p["next_packet"]); self.assertEqual(FRESH_V09,p["fresh_authority_token_id"]); self.assertEqual("AUTHORIZED_UNCONSUMED",p["fresh_authority_token_state"]); self.assertFalse(p["fresh_authority_token_consumed"]); self.assertEqual(V09_BINDING,p["run_binding_sha256"]); self.assertTrue(p["current_blocker_evidence"].endswith("SRFDI_WP10_V09_PREFLIGHT_EXECUTION_INTERFACE_BLOCKER.json")); self.assertEqual("BLOCKED_PRECONSUMPTION_EXECUTION_INTERFACE_MISMATCH_PENDING_SRFDI_G10C",p["june_execution"])
  self.assertEqual("DENIED",p["provider_fetch"]); self.assertEqual("LOCKED_UNCONSUMED",p["validation_2025"]); self.assertEqual("NONE",p["scientific_promotion"]); self.assertEqual("NONE",p["probability_risk_exposure_execution"])

if __name__=="__main__": unittest.main()
