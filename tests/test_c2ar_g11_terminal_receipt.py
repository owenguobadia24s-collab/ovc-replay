import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "docs/releases/c2-anatomy-observation-redesign-v0-2/c2ar-wp11"
STATE_PATH = ROOT / "registries/opt_b/c2/anatomy_redesign/OVC_C2AR_PROGRAMME_TERMINAL_STATE_v0_3.jsonc"


class C2ARG11TerminalReceiptTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.receipt = json.loads((BASE / "C2AR_G11_TERMINAL_MERGE_RECEIPT.json").read_text())
        cls.state = json.loads(STATE_PATH.read_text())

    def test_receipt_binds_exact_gate_decision_head_runs_and_merge(self):
        self.assertEqual(self.receipt["decision_id"], "C2AR-G11.DELEGATED.PASS.20260805T160500+0100")
        self.assertEqual(self.receipt["final_feature_head"], "dc5727ed5181f34e90030a6a78dd68a015ecfc0e")
        self.assertEqual(self.receipt["assured_synthetic_merge_commit"], "8749210eae1eb177c318dfc4c2261e5952652c7d")
        self.assertEqual(self.receipt["squash_merge_commit"], "427beb2f9d85394f2352f00ebd68d1464fecc266")
        self.assertEqual(self.receipt["assurance"]["complete_suite"]["run_id"], 31020172505)
        self.assertEqual(self.receipt["assurance"]["complete_suite"]["test_count"], 327)
        self.assertEqual(self.receipt["assurance"]["final_head"]["result"], "PASS")
        self.assertEqual(self.receipt["assurance"]["merge_readiness"]["result"], "PASS")
        self.assertEqual(self.receipt["assurance"]["unresolved_review_threads"], 0)

    def test_package_is_complete_but_inactive_noncanonical_and_unpublished(self):
        package = self.receipt["package"]
        self.assertEqual(package["package_id"], "C2AR.INTEGRATED.SHADOW.PACKAGE.v1")
        self.assertEqual(package["package_sha256"], "150de1997be8801baa59db6d0fe98b11cb21a6b70525b908537aeb31bfd00cc3")
        self.assertEqual(package["status"], "IMPLEMENTED_SHADOW_COMPLETE")
        self.assertFalse(package["active"])
        self.assertFalse(package["canonical"])
        self.assertFalse(package["publication"])

    def test_terminal_authority_preserves_active_c2_and_all_reserved_denials(self):
        authority = self.receipt["terminal_authority"]
        self.assertEqual(authority["active_c2"], "UNCHANGED_READ_ONLY")
        self.assertEqual(authority["reserved_authority_effect"], "NONE")
        self.assertEqual(authority["research_consumer_permission"], "READ_ONLY_SHADOW_RESEARCH_ONLY")
        self.assertEqual(authority["crosswalk"], "MAINTAINED_SHADOW")
        self.assertEqual(authority["legacy_mappings"], "2_DEFERRED_NO_LAWFUL_CROSSWALK")

    def test_terminal_state_has_no_remaining_packet_or_gate(self):
        self.assertEqual(self.state["status"], "IMPLEMENTED_SHADOW_COMPLETE")
        self.assertTrue(self.state["programme_complete"])
        self.assertFalse(self.state["operator_decision_required"])
        self.assertIsNone(self.state["next_packet"])
        self.assertIsNone(self.state["next_gate"])
        self.assertEqual(self.state["next_action"], "SEPARATE_OPERATOR_APPROVED_ACTIVATION_PLAN_ONLY")
        self.assertEqual(self.state["merge_commit"], "427beb2f9d85394f2352f00ebd68d1464fecc266")
        self.assertEqual(self.state["authority"]["active_c2"], "UNCHANGED_READ_ONLY")
        self.assertEqual(self.state["authority"]["active_discovery_development_validation"], "NONE")
        self.assertEqual(self.state["authority"]["canonical_r2_publication"], "NONE")

    def test_warnings_and_external_evidence_remain_visible(self):
        self.assertEqual(len(self.receipt["warnings"]), 3)
        self.assertEqual(len(self.state["warnings"]), 3)
        evidence = self.receipt["external_evidence"]
        self.assertEqual(evidence["logical_population_sha256"], "3f1089e3a4eefe94147c8c2f912e77899e4ed21fe8b3b8b85993e47bf7151ee7")
        self.assertEqual(evidence["disposition_content_sha256"], "4a21f3db44f8a6587ff863bb24fc6fe213f73ea9cf47d9d6cd69ba2e82b16fc2")


if __name__ == "__main__":
    unittest.main()
