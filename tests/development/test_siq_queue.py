from __future__ import annotations
import unittest
from ovc.development.skills.siq_core import BASE_INDEPENDENT, BASE_SENSITIVE, READY, WAIT, acquire_final_integration_lease, build_queue_state, classify_assurance, mark_integrated, queue_head
A="a"*40; B="b"*40; C="c"*40; D="d"*40
PIP="d"*64; GEN="e"*64; PLACEMENT="f"*64

def item(packet,seq,head=A):
    return {"packet_id":packet,"plan_id":"PLAN","candidate_head_sha":head,"baseline_main_sha":B,"ready_sequence":seq,"implementation_complete":True,"qa_status":"PASS","authority_delta":"NONE","gate_class":"AUTO_EXECUTABLE","preliminary_assurance_pass":True,"rollback_defined":True,"dependency_footprint_pinned":True,"vit_pip_id":PIP,"vit_generation_id":GEN,"vit_placement_id":PLACEMENT,"vit_lineage_ref":"records/test/vit-lineage.json"}
class SIQQueueTests(unittest.TestCase):
    def test_concurrent_ready_but_base_independent_cannot_hold_lease(self):
        state=build_queue_state([item("A",1),item("B",2,C)])
        self.assertEqual([x.packet_id for x in state.candidates if x.queue_state==READY],["A","B"])
        self.assertEqual(classify_assurance("PACKET_LOCAL_TESTS"),BASE_INDEPENDENT)
        with self.assertRaises(PermissionError): acquire_final_integration_lease(state,packet_id="A",assurance_class=BASE_INDEPENDENT)
    def test_one_lease_and_successor(self):
        state=build_queue_state([item("A",1),item("B",2,C)])
        held=acquire_final_integration_lease(state,packet_id="A",assurance_class=BASE_SENSITIVE)
        self.assertEqual(held.as_dict()["final_integration_lease_count"],1)
        with self.assertRaises(PermissionError): acquire_final_integration_lease(held,packet_id="B",assurance_class=BASE_SENSITIVE)
        done=mark_integrated(held,packet_id="A",merge_sha=D)
        self.assertIsNone(done.lease_holder_packet_id)
        self.assertEqual(queue_head(done).packet_id,"B")
    def test_direct_candidate_without_vit_lineage_never_becomes_ready(self):
        candidate=item("NO-VIT",1)
        for key in ("vit_pip_id","vit_generation_id","vit_placement_id","vit_lineage_ref"):
            candidate.pop(key)
        state=build_queue_state([candidate])
        row=state.candidates[0]
        self.assertEqual(row.queue_state,WAIT)
        self.assertIn("VIT_LINEAGE_REQUIRED",row.reason_codes)
        self.assertIsNone(queue_head(state))
if __name__=="__main__": unittest.main()
