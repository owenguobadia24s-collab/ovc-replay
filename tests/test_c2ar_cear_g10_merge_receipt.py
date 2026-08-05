import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
RECEIPT = ROOT / "docs/releases/c2-anatomy-observation-redesign-v0-2/c2ar-wp10/CEAR_G10_MERGE_RECEIPT.json"
STATE = ROOT / "registries/opt_b/c2/anatomy_redesign/OVC_C2AR_WP10_COMPLETED_STATE_v0_3.jsonc"

class CEARG10MergeReceiptTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.receipt = json.loads(RECEIPT.read_text())
        cls.state = json.loads(STATE.read_text())

    def test_receipt_binds_operator_decision_assurance_and_merge(self):
        self.assertEqual(cls := self.receipt["decision_id"], "CEAR-G10.OPERATOR.MULTIPART.20260805T151900+0100")
        self.assertEqual(self.receipt["decision_head"], "76cb85efae7e54887ee37c922b1b7ad11297116c")
        self.assertEqual(self.receipt["squash_merge_commit"], "29af8b6334be0c7993747fe359f62e2f5ad32dcd")
        self.assertEqual(self.receipt["assurance"]["complete_suite"]["test_count"], 300)
        self.assertEqual(self.receipt["assurance"]["unresolved_review_threads"], 0)

    def test_completed_authority_is_inactive_and_active_c2_is_unchanged(self):
        authority = self.receipt["completed_authority"]
        self.assertIn("INACTIVE_NONCANONICAL", authority["discovery_method"])
        self.assertEqual(authority["legacy_mappings"], "2_DEFERRED_NO_LAWFUL_CROSSWALK")
        self.assertEqual(authority["research_consumer"], "READ_ONLY_SHADOW_RESEARCH_ONLY")
        self.assertEqual(authority["active_c2"], "UNCHANGED_READ_ONLY")
        self.assertEqual(self.receipt["reserved_authority_effect"], "NONE")

    def test_state_completes_wp10_and_exposes_only_wp11_closeout(self):
        self.assertEqual(self.state["status"], "COMPLETED")
        self.assertEqual(self.state["completed_packet"], "C2AR-WP10")
        self.assertEqual(self.state["next_packet"], "C2AR-WP11")
        self.assertEqual(self.state["next_gate"], "C2AR-G11")
        self.assertEqual(self.state["next_packet_status"], "READY")
        self.assertFalse(self.state["operator_decision_required"])
        self.assertEqual(self.state["authority"]["active_c2"], "UNCHANGED_READ_ONLY")

if __name__ == "__main__":
    unittest.main()
