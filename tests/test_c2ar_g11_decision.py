import json
from pathlib import Path
import unittest

from ovc.opt_b.c2_vnext.integrated_shadow import build_integrated_manifest

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "docs/releases/c2-anatomy-observation-redesign-v0-2/c2ar-wp11"
STATE = ROOT / "registries/opt_b/c2/anatomy_redesign/OVC_C2AR_PROGRAMME_COMPLETED_STATE_v0_3.jsonc"
OVERLAY = ROOT / "registries/opt_b/c2/vnext/C2_INTEGRATED_SHADOW_PACKAGE_APPROVED_v1.jsonc"

class C2ARG11DecisionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.decision = json.loads((BASE / "C2AR_G11_DELEGATED_DECISION.json").read_text())
        cls.assurance = json.loads((BASE / "C2AR_WP11_PREDECISION_ASSURANCE_RECEIPT.json").read_text())
        cls.qa = json.loads((BASE / "C2AR_WP11_FINAL_QA_PACKET.json").read_text())
        cls.smoke = json.loads((BASE / "C2AR_WP11_REAL_COMPONENT_SMOKE_ASSURANCE_RECEIPT.json").read_text())
        cls.state = json.loads(STATE.read_text())
        cls.overlay = json.loads(OVERLAY.read_text())

    def test_delegated_pass_is_inside_plan_and_has_no_reserved_delta(self):
        self.assertEqual(self.decision["decision"], "PASS")
        self.assertEqual(self.decision["authority_basis"], "APPROVED_PLAN_DELEGATION_AUTO_IF_NO_RESERVED_DELTA")
        self.assertEqual(self.decision["authority_delta"], "INTEGRATED_SHADOW_CLOSEOUT_ONLY")
        self.assertEqual(self.decision["reserved_authority_delta"], "NONE")
        self.assertEqual(self.decision["active_c2"], "UNCHANGED_READ_ONLY")

    def test_assurance_binds_exact_predecision_head_and_311_tests(self):
        self.assertEqual(self.assurance["head"], "d9b657544361e054aa7ca9c52557b9a57923ebef")
        self.assertEqual(self.assurance["complete_suite"]["test_count"], 311)
        self.assertEqual(self.assurance["complete_suite"]["result"], "PASS")
        self.assertEqual(self.assurance["final_head"]["result"], "PASS")
        self.assertEqual(self.assurance["merge_readiness"]["result"], "PASS")
        self.assertEqual(self.assurance["review_threads"]["count"], 0)

    def test_smoke_is_assured_and_keeps_fixture_bound_mocks_explicit(self):
        self.assertEqual(self.smoke["status"], "PASS")
        self.assertTrue(self.smoke["two_logical_executions_identical"])
        self.assertEqual(len(self.smoke["fixture_bound_mocked_boundaries"]), 3)
        self.assertEqual(self.smoke["exact_head_ci_binding"]["complete_suite_run"], 31018296057)

    def test_approval_overlay_completes_package_without_mutating_predecision_manifest(self):
        manifest = build_integrated_manifest()
        self.assertEqual(manifest["status"], "QA_REVIEW")
        self.assertEqual(self.overlay["package_sha256"], manifest["package_sha256"])
        self.assertEqual(self.overlay["status"], "IMPLEMENTED_SHADOW_COMPLETE")
        self.assertFalse(self.overlay["active"])
        self.assertFalse(self.overlay["canonical"])
        self.assertEqual(self.overlay["active_c2"], "UNCHANGED_READ_ONLY")
        self.assertEqual(self.state["status"], "IMPLEMENTED_SHADOW_COMPLETE")
        self.assertIsNone(self.state["next_packet"])
        self.assertEqual(self.state["next_action"], "SEPARATE_OPERATOR_APPROVED_ACTIVATION_PLAN_ONLY")

    def test_final_qa_passes_without_hiding_warnings(self):
        self.assertEqual(self.qa["status"], "PASS")
        self.assertEqual(self.qa["recommendation"], "PASS")
        self.assertEqual(self.qa["blocking_warnings"], [])
        self.assertEqual(len(self.qa["nonblocking_warnings"]), 3)
        self.assertEqual(self.qa["reserved_authority_delta"], "NONE")

if __name__ == "__main__":
    unittest.main()
