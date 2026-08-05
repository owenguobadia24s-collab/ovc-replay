from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
RECEIPT = ROOT / "docs/releases/c2-anatomy-observation-redesign-v0-2/c2ar-wp8/C2AR_G8A_MERGE_RECEIPT.json"
STATE = ROOT / "registries/opt_b/c2/anatomy_redesign/OVC_C2AR_WP8_MERGED_STATE_v0_2.jsonc"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class C2ARG8AMergeReceiptTests(unittest.TestCase):
    def test_receipt_binds_exact_head_merge_and_assurance(self) -> None:
        receipt = load(RECEIPT)
        self.assertEqual(313, receipt["pull_request"])
        self.assertEqual("79da235d330174adbd2784b9a98c8f5a7b231031", receipt["final_head_commit"])
        self.assertEqual("502870c7c61d4e72f2ce1679bdc2a3edf55d550f", receipt["squash_merge_commit"])
        self.assertTrue(all(item["result"] == "PASS" for item in receipt["assurance"]))
        self.assertEqual([], receipt["blockers"])
        self.assertEqual([], receipt["external_artifacts"])
        authority = receipt["implemented_authority"]
        self.assertEqual("SHADOW_FROZEN_READ_ONLY_INACTIVE_NONCANONICAL", authority["parent_context_resolver"])
        self.assertEqual("NONE", authority["active_parent_selection"])
        self.assertEqual("NONE", authority["semantic_event_episode"])
        self.assertEqual("NONE", authority["consumer_denominator_overlap"])
        self.assertEqual("UNCHANGED_READ_ONLY", authority["active_c2"])

    def test_completed_state_routes_only_to_cear_g9_preparation(self) -> None:
        state = load(STATE)
        self.assertEqual("COMPLETED", state["status"])
        self.assertFalse(state["operator_decision_required"])
        self.assertEqual("502870c7c61d4e72f2ce1679bdc2a3edf55d550f", state["merge_commit"])
        self.assertEqual("C2AR-WP9-PREPARATION", state["next_packet"])
        self.assertEqual("CEAR-G9", state["next_gate"])
        self.assertEqual([], state["blockers"])
        for key in (
            "active_parent_selection",
            "hidden_selection",
            "universal_staleness_threshold",
            "semantic_event_episode",
            "c2e_c2_5",
            "consumer_denominator_overlap",
            "rule_theory",
            "release_publication_validation",
            "probability_risk_exposure_execution",
        ):
            self.assertEqual("NONE", state["authority"][key])
        self.assertEqual("UNCHANGED_READ_ONLY", state["authority"]["active_c2"])


if __name__ == "__main__":
    unittest.main()
