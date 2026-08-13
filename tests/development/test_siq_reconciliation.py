from __future__ import annotations
import unittest
from ovc.development.skills.siq_reconciliation import build_automatic_requeue, plan_selective_assurance
A="a"*40; B="b"*40; C="c"*40

def fp():
    return {"schema":"ovc-parallel-development-dependency-footprint/v1","programme_id":"P","packet_id":"WP","plan_id":"PLAN","baseline_main_sha":B,"dependency_paths":["contracts/domain/**"],"semantic_authority_paths":["registries/authority/**"],"shared_integration_paths":[".github/workflows/**"],"candidate_owned_paths":["src/feature/**"],"identity_bindings":[],"external_identity_bindings":[]}
AUTH={"status":"ACTIVE_AUTHORIZED","record_present_on_main":True}
PACKET={"packet_id":"WP","packet_class":"LOW_RISK_IMPLEMENTATION","gate_class":"AUTO_EXECUTABLE","authority_delta":"NONE","write_set_identity":"W","previous_write_set_identity":"W","semantic_owner_identity":"S","previous_semantic_owner_identity":"S","authority_surface_identity":"A","previous_authority_surface_identity":"A","frozen_surface_identity":"F","previous_frozen_surface_identity":"F"}

class SIQReconciliationTests(unittest.TestCase):
    def test_irrelevant_movement_reuses_unaffected_evidence(self):
        plan=plan_selective_assurance(baseline_main_sha=B,current_main_sha=C,changed_main_paths=["docs/unrelated.md"],dependency_footprint=fp(),pdc_policy=None,completed_assurance=["PACKET_LOCAL_TESTS","QA_EVIDENCE_GENERATION","MANDATORY_FINAL_HEAD_ASSURANCE"])
        self.assertEqual(plan["classification"],"IRRELEVANT")
        self.assertIn("PACKET_LOCAL_TESTS",plan["assurance_reused"])
        self.assertIn("MANDATORY_FINAL_HEAD_ASSURANCE",plan["assurance_rerun"])
    def test_integration_relevant_reruns_impacted_and_final(self):
        plan=plan_selective_assurance(baseline_main_sha=B,current_main_sha=C,changed_main_paths=[".github/workflows/tests.yml"],dependency_footprint=fp(),pdc_policy=None,completed_assurance=["PACKET_LOCAL_TESTS","QA_EVIDENCE_GENERATION","MANDATORY_FINAL_HEAD_ASSURANCE"],impacted_assurance=["PACKET_LOCAL_TESTS"])
        self.assertEqual(plan["classification"],"INTEGRATION_RELEVANT")
        self.assertIn("PACKET_LOCAL_TESTS",plan["assurance_rerun"])
        self.assertIn("QA_EVIDENCE_GENERATION",plan["assurance_reused"])
    def test_semantic_movement_requires_full_repreflight(self):
        plan=plan_selective_assurance(baseline_main_sha=B,current_main_sha=C,changed_main_paths=["contracts/domain/core.md"],dependency_footprint=fp(),pdc_policy=None,completed_assurance=["PACKET_LOCAL_TESTS"])
        self.assertEqual(plan["classification"],"SEMANTIC_AUTHORITY_RELEVANT")
        self.assertEqual(plan["status"],"BLOCK_FULL_REPREFLIGHT_REQUIRED")
        self.assertIn("perform_full_semantic_repreflight",plan["pdc_movement_receipt"]["required_actions"])
        stopped=build_automatic_requeue(authority_resolution=AUTH,packet=PACKET,movement_plan=plan,attempt=1,previous_base=B,current_main=C)
        self.assertEqual(stopped["action"],"STOP_FAIL_CLOSED")
    def test_lawful_requeue_uses_existing_orch_guard(self):
        result=build_automatic_requeue(authority_resolution=AUTH,packet=PACKET,movement_plan={"status":"REQUEUE_ELIGIBLE","record_id":"SIQ-P"},attempt=1,previous_base=B,current_main=C)
        self.assertEqual(result["action"],"REQUEUE_RECONCILE_FROM_CURRENT_MAIN")
        self.assertTrue(result["fresh_branch_required"])
        self.assertTrue(result["fresh_exact_head_assurance_required"])
        self.assertFalse(result["parallel_merge"])
if __name__=="__main__": unittest.main()
