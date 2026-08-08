import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[3]
BASE=ROOT/"docs/releases/sri-fdi-conformance-v0-1/sfc-wp7"
STATE=ROOT/"registries/implementation/sfc/OVC_SFC_STATE_v0_11.json"
POINTER=ROOT/"registries/implementation/sfc/CURRENT_STATE_POINTER.json"

class SFCG7TerminalReceiptTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.receipt=json.loads((BASE/"SFC_G7_TERMINAL_MERGE_RECEIPT.json").read_text())
        cls.state=json.loads(STATE.read_text())
        cls.pointer=json.loads(POINTER.read_text())

    def test_receipt_binds_exact_passing_g7_head_and_merge(self):
        self.assertEqual(self.receipt["pr_number"],476)
        self.assertEqual(self.receipt["pr_head"],"c147d980ff400f23e26358980966988f7466fbb1")
        self.assertEqual(self.receipt["merge_commit"],"e7fc0925eb3598f75c4734d8dab417c972cfdf8c")
        self.assertEqual(self.receipt["final_assurance"]["repository_suite"]["run_id"],31282231555)
        self.assertEqual(self.receipt["final_assurance"]["ovc_final_head_profile_compatibility_merge_readiness"]["run_id"],31282231585)

    def test_programme_is_completed_preserved(self):
        self.assertEqual(self.state["status"],"COMPLETED")
        self.assertEqual(self.state["programme_disposition"],"COMPLETED_PRESERVED")
        self.assertEqual(self.state["route"],"PRESERVED")
        self.assertTrue(all(row["status"]=="COMPLETED" for row in self.state["packets"]))
        self.assertIsNone(self.state["next_packet"])

    def test_interlock_release_does_not_grant_june_run_or_reserved_authority(self):
        auth=self.state["authority"]
        self.assertEqual(auth["srfd_june_authority_interlock"],"ALLOW_FUTURE_PREPARATION_ONLY")
        self.assertEqual(auth["june_execution"],"DENIED_SEPARATE_SRFDI_G_JUNE_AUTH_REQUIRED")
        self.assertEqual(auth["validation_2025"],"LOCKED_UNCONSUMED")
        self.assertEqual(auth["canonical_representation_normalization_comparison_family_sensitivity"],"NONE")
        self.assertEqual(auth["selector_semantic_publication"],"NONE")
        self.assertEqual(auth["probability_risk_exposure_execution_agent_write"],"NONE")

    def test_blocked_fresh_auth_attempt_never_reached_main(self):
        incident=self.state["interlock_incidents"][0]
        self.assertEqual(incident["pr"],470)
        self.assertEqual(incident["disposition"],"CLOSED_UNMERGED")
        self.assertFalse(incident["authority_reached_main"])

    def test_pointer_is_terminal_and_forward_only(self):
        self.assertEqual(self.pointer["authoritative_state"],"registries/implementation/sfc/OVC_SFC_STATE_v0_11.json")
        self.assertEqual(self.pointer["status"],"COMPLETED")
        self.assertEqual(self.pointer["route"],"PRESERVED")
        self.assertIsNone(self.pointer["active_packet"])
        self.assertTrue(self.pointer["next_action"].startswith("STOP_SFC_COMPLETE_PRESERVED"))

if __name__=="__main__": unittest.main()
