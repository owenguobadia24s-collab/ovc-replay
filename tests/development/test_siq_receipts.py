from __future__ import annotations
from tempfile import TemporaryDirectory
from pathlib import Path
import unittest
from ovc.development.skills.siq_core import build_queue_state
from ovc.development.skills.siq_receipts import build_siq_receipt, load_siq_receipt, persist_siq_receipt
from ovc.development.skills.vit_routing import build_vit_lineage_record
A="a"*40; B="b"*40
PIP={"schema_version":"packet-integration-payload/v0.1","programme_id":"PROGRAMME","packet_id":"WP","logical_changes":[{"op":"ADD","path":"records/WP.json","blob_sha":"1"*40,"mode":"100644"}],"authority_manifest_id":"2"*64,"dependency_frontier_id":"3"*64,"completion_transition":{"status":"COMPLETED"}}
LINEAGE=build_vit_lineage_record(programme_id="PROGRAMME",packet_id="WP",pip_identity_payload=PIP,train_generation_id="TRAIN-1",ordinal=1,predecessor_tree_sha="a"*40,result_tree_sha="b"*40,apply_profile="REFERENCE_APPLY")
ITEM={"packet_id":"WP","plan_id":"PLAN","candidate_head_sha":A,"baseline_main_sha":B,"ready_sequence":1,"implementation_complete":True,"qa_status":"PASS","authority_delta":"NONE","gate_class":"AUTO_EXECUTABLE","preliminary_assurance_pass":True,"rollback_defined":True,"dependency_footprint_pinned":True,"vit_pip_id":LINEAGE["pip_id"],"vit_generation_id":LINEAGE["generation_id"],"vit_placement_id":LINEAGE["placement_id"],"vit_lineage_ref":"records/test/WP.json","vit_lineage_record":LINEAGE}
class SIQReceiptTests(unittest.TestCase):
    def test_receipt_is_observability_only_and_round_trips(self):
        state=build_queue_state([ITEM])
        receipt=build_siq_receipt(state=state,event="READY_ADMITTED",packet_id="WP",decision="OBSERVED",observed_at_utc="2026-08-14T00:00:00Z")
        self.assertTrue(receipt["observability_only"])
        self.assertEqual(receipt["merge_authority"],"NONE")
        self.assertEqual(receipt["scientific_governance_authority"],"NONE")
        self.assertFalse(receipt["ready_status_is_authority"])
        self.assertFalse(receipt["queue_position_is_authority"])
        self.assertFalse(receipt["lease_ownership_is_authority"])
        self.assertFalse(receipt["successful_assurance_is_authority"])
        self.assertFalse(receipt["orchestration_selection_is_authority"])
        self.assertFalse(receipt["execution_started_observed"])
        self.assertFalse(receipt["execution_completed_observed"])
        with TemporaryDirectory() as tmp:
            path=persist_siq_receipt(receipt,Path(tmp))
            self.assertEqual(load_siq_receipt(path),receipt)
            self.assertEqual(persist_siq_receipt(receipt,Path(tmp)),path)
if __name__=="__main__": unittest.main()
