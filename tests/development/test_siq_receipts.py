from __future__ import annotations
from tempfile import TemporaryDirectory
from pathlib import Path
import unittest
from ovc.development.skills.siq_core import build_queue_state
from ovc.development.skills.siq_receipts import build_siq_receipt, load_siq_receipt, persist_siq_receipt
A="a"*40; B="b"*40
ITEM={"packet_id":"WP","plan_id":"PLAN","candidate_head_sha":A,"baseline_main_sha":B,"ready_sequence":1,"implementation_complete":True,"qa_status":"PASS","authority_delta":"NONE","gate_class":"AUTO_EXECUTABLE","preliminary_assurance_pass":True,"rollback_defined":True,"dependency_footprint_pinned":True}
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
