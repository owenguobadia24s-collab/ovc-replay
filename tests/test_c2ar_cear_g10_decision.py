import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "docs/releases/c2-anatomy-observation-redesign-v0-2/c2ar-wp10"
REG = ROOT / "registries/opt_b/c2"

class CEARG10OperatorDecisionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.decision = json.loads((BASE / "CEAR_G10_OPERATOR_DECISION.json").read_text())
        cls.ledger = json.loads((REG / "vnext/C2_CEAR_G10_RESEARCH_CANDIDATE_DISPOSITIONS_v1.jsonc").read_text())
        cls.state = json.loads((REG / "anatomy_redesign/OVC_C2AR_CEAR_G10_APPROVED_STATE_v0_3.jsonc").read_text())

    def test_operator_command_and_multipart_decision_are_exact(self):
        self.assertEqual(
            self.decision["operator_command"],
            "OVC APPROVE CEAR-G10 METHOD=PASS FUNCTIONAL_CANDIDATES=PASS_ALL RULE_CANDIDATES=PASS_ALL LEGACY_MAPPINGS=DEFER RESEARCH_CONSUMER=PASS_READ_ONLY_SHADOW",
        )
        self.assertEqual(self.decision["decision"]["method"], "PASS")
        self.assertEqual(self.decision["decision"]["functional_candidates"], "PASS_ALL_14")
        self.assertEqual(self.decision["decision"]["rule_candidates"], "PASS_ALL_14")
        self.assertEqual(self.decision["decision"]["legacy_mappings"], "DEFER_BOTH")
        self.assertEqual(self.decision["decision"]["research_consumer"], "PASS_READ_ONLY_SHADOW")

    def test_all_candidate_dispositions_are_explicit_inactive_and_noncanonical(self):
        rows = self.decision["candidate_dispositions"]
        self.assertEqual(len(rows), 14)
        self.assertEqual(len({row["functional_candidate_id"] for row in rows}), 14)
        self.assertEqual(len({row["rule_candidate_id"] for row in rows}), 14)
        self.assertTrue(all(row["functional_decision"].startswith("PASS_INACTIVE") for row in rows))
        self.assertTrue(all(row["rule_decision"].startswith("PASS_INACTIVE") for row in rows))
        self.assertFalse(self.ledger["active"])
        self.assertFalse(self.ledger["canonical"])

    def test_legacy_mappings_are_deferred_without_inference(self):
        mappings = self.decision["legacy_mapping_dispositions"]
        self.assertEqual(len(mappings), 2)
        self.assertTrue(all(row["decision"] == "DEFER" for row in mappings))
        self.assertTrue(all(row["reason"] == "NO_LAWFUL_VNEXT_OPPORTUNITY_ID_CROSSWALK" for row in mappings))

    def test_authority_ledger_grants_read_only_shadow_research_only(self):
        self.assertEqual(self.ledger["research_consumer_permission"], "READ_ONLY_SHADOW_RESEARCH_ONLY")
        self.assertEqual(len(self.ledger["candidate_dispositions"]), 14)
        denied = set(self.ledger["denied_authorities"])
        self.assertIn("SELECTOR_ACTIVATION_OR_REPLACEMENT", denied)
        self.assertIn("ACTIVE_DISCOVERY_ACTIVE_DEVELOPMENT_ACTIVE_VALIDATION", denied)
        self.assertIn("CANONICAL_OR_R2_PUBLICATION", denied)

    def test_state_approves_g10_but_requires_merge_receipt_before_wp11(self):
        self.assertEqual(self.state["status"], "APPROVED")
        self.assertFalse(self.state["operator_decision_required"])
        self.assertEqual(self.state["current_gate"], "CEAR-G10")
        self.assertEqual(self.state["main_merge_status"], "ELIGIBLE_AFTER_EXACT_HEAD_ASSURANCE")
        self.assertEqual(self.state["wp11_status"], "READY_AFTER_WP10_MERGE_RECEIPT")
        self.assertEqual(self.state["authority"]["active_c2"], "UNCHANGED_READ_ONLY")

if __name__ == "__main__":
    unittest.main()
