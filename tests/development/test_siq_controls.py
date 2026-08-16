from __future__ import annotations
import unittest
from ovc.development.skills.siq_core import BASE_SENSITIVE, BLOCKED, OPERATOR_REQUIRED, PARALLEL_MERGE, FORCE_PUSH, HISTORY_REWRITE, acquire_final_integration_lease, build_queue_state, handle_lease_elapsed, queue_head, terminate_lease
A="a"*40; B="b"*40; C="c"*40
PIP="d"*64; GEN="e"*64; PLACEMENT="f"*64

def item(packet,seq,head=A,gate="AUTO_EXECUTABLE",delta="NONE",state="BUILD"):
    return {"packet_id":packet,"plan_id":"PLAN","candidate_head_sha":head,"baseline_main_sha":B,"ready_sequence":seq,"queue_state":state,"implementation_complete":True,"qa_status":"PASS","authority_delta":delta,"gate_class":gate,"preliminary_assurance_pass":True,"rollback_defined":True,"dependency_footprint_pinned":True,"vit_pip_id":PIP,"vit_generation_id":GEN,"vit_placement_id":PLACEMENT,"vit_lineage_ref":"records/test/vit-lineage.json"}
class SIQControlTests(unittest.TestCase):
    def test_timeout_releases_and_requeues(self):
        state=build_queue_state([item("A",1)])
        held=acquire_final_integration_lease(state,packet_id="A",assurance_class=BASE_SENSITIVE)
        released,decision=handle_lease_elapsed(held,packet_id="A",elapsed_seconds=901,admitted_base_sensitive_check_active=False)
        self.assertIsNone(released.lease_holder_packet_id)
        self.assertEqual(queue_head(released).packet_id,"A")
        self.assertEqual(decision["disposition"],"RELEASE_AND_REQUEUE")
    def test_active_base_sensitive_work_preserves_lease_past_threshold(self):
        state=build_queue_state([item("A",1)])
        held=acquire_final_integration_lease(state,packet_id="A",assurance_class=BASE_SENSITIVE)
        retained,decision=handle_lease_elapsed(held,packet_id="A",elapsed_seconds=901,admitted_base_sensitive_check_active=True)
        self.assertEqual(retained.lease_holder_packet_id,"A")
        self.assertEqual(decision["disposition"],"WARNING_ACTIVE_CHECK")
    def test_operator_wait_does_not_block_unrelated_ready_packet(self):
        state=build_queue_state([item("OP",1,gate="OPERATOR_REQUIRED",delta="RESERVED"),item("A",2,C)])
        self.assertEqual(next(x.queue_state for x in state.candidates if x.packet_id=="OP"),OPERATOR_REQUIRED)
        self.assertEqual(queue_head(state).packet_id,"A")
    def test_blocked_candidate_never_owns_queue_head(self):
        state=build_queue_state([item("BLOCK",1,state=BLOCKED),item("A",2,C)])
        self.assertEqual(queue_head(state).packet_id,"A")
    def test_failed_base_sensitive_work_releases_lease(self):
        state=build_queue_state([item("A",1)])
        held=acquire_final_integration_lease(state,packet_id="A",assurance_class=BASE_SENSITIVE)
        failed=terminate_lease(held,packet_id="A",disposition=BLOCKED,reason_code="BASE_SENSITIVE_CHECK_FAILED")
        self.assertIsNone(failed.lease_holder_packet_id)
        self.assertEqual(next(x.queue_state for x in failed.candidates if x.packet_id=="A"),BLOCKED)
    def test_no_parallel_merge_or_history_rewrite_path_is_exposed(self):
        self.assertFalse(PARALLEL_MERGE)
        self.assertFalse(FORCE_PUSH)
        self.assertFalse(HISTORY_REWRITE)
if __name__=="__main__": unittest.main()
