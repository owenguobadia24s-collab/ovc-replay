import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[3]
BASE=ROOT/"docs/releases/sri-fdi-conformance-v0-1/sfc-wp7"
STATE=ROOT/"registries/implementation/sfc/OVC_SFC_STATE_v0_10.json"
POINTER=ROOT/"registries/implementation/sfc/CURRENT_STATE_POINTER.json"

class SFCWP7CloseoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pre=json.loads((BASE/"SFC_WP7_CLOSEOUT_PREFLIGHT.json").read_text())
        cls.matrix=json.loads((BASE/"SFC_FINAL_CONFORMANCE_MATRIX.json").read_text())
        cls.gate=json.loads((BASE/"SFC_G7_GATE_PACKET.json").read_text())
        cls.decision=json.loads((BASE/"SFC_G7_STANDING_DELEGATED_DECISION.json").read_text())
        cls.report=json.loads((BASE/"SFC_FINAL_CLOSEOUT_REPORT.json").read_text())
        cls.state=json.loads(STATE.read_text())
        cls.pointer=json.loads(POINTER.read_text())

    def test_all_prior_packets_are_merged_and_f40_passed(self):
        self.assertEqual(self.pre["programme_evidence"]["SFC-WP6"]["merge_commit"],"8dc9eb104dc1a30ce31aadb573ff02a4071c6b30")
        self.assertIn("31281941139 SUCCESS",self.pre["programme_evidence"]["SFC-WP6"]["tests"])
        self.assertEqual(self.matrix["fixture_coverage"]["F40"],"PASS_WP6_COMPLETE_REPOSITORY_SUITE_31281941139")

    def test_frozen_v04_route_is_preserved(self):
        self.assertEqual(self.decision["route"],"PRESERVED")
        self.assertEqual(self.decision["frozen_v04"]["git_blob_sha"],"e4f5ce02a103000a48ed98e2110b8f1a7d497fcd")
        self.assertEqual(self.decision["frozen_v04"]["mutation"],"NONE")

    def test_interlock_violation_was_denied_without_authority(self):
        incident=self.pre["interlock_enforcement"]
        self.assertEqual(incident["attempted_pr"],470)
        self.assertEqual(incident["reason_code"],"SFC_SRFD_JUNE_INTERLOCK_ACTIVE")
        self.assertFalse(incident["authority_reached_main"])
        self.assertFalse(incident["token_authoritative"])

    def test_g7_release_only_allows_future_preparation_not_run(self):
        delta=self.decision["authority_delta"]
        self.assertEqual(delta["srfd_june_authority_interlock"],"ALLOW_FUTURE_PREPARATION_ONLY")
        self.assertEqual(delta["june_execution"],"DENIED_PENDING_SEPARATE_SRFDI_G_JUNE_AUTH")
        self.assertEqual(delta["validation_2025"],"LOCKED_UNCONSUMED")
        self.assertEqual(delta["selector_family_semantic_publication"],"NONE")
        self.assertEqual(delta["probability_risk_exposure_execution"],"NONE")

    def test_state_is_terminal_candidate_pending_exact_head_and_pointer_does_not_grant_run(self):
        self.assertEqual(self.state["current_gate"],"SFC-G7")
        self.assertEqual(self.state["route_candidate"],"PRESERVED")
        self.assertEqual(self.pointer["srfd_june_authority_interlock"],"ALLOW_AFTER_THIS_EXACT_G7_HEAD_MERGES")
        self.assertEqual(self.pointer["june_execution"],"DENIED_SEPARATE_SRFDI_G_JUNE_AUTH_REQUIRED")

if __name__=="__main__": unittest.main()
