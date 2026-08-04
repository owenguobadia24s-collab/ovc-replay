from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
RECEIPT = ROOT / "docs/releases/c2-anatomy-observation-redesign-v0-2/c2ar-wp7/C2AR_WP7_G7A_MERGE_RECEIPT.json"
STATE = ROOT / "registries/opt_b/c2/anatomy_redesign/OVC_C2AR_WP7_MERGED_STATE_v0_2.jsonc"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class C2ARWP7MergeReceiptTests(unittest.TestCase):
    def test_receipt_binds_exact_decisions_head_checks_and_merge(self) -> None:
        receipt = load(RECEIPT)
        self.assertEqual("CEAR-G7.OPERATOR.PASS.20260804T234400+0100", receipt["operator_decision_id"])
        self.assertEqual("C2AR-G7A.DELEGATED.PASS.20260804T235600+0100", receipt["delegated_decision_id"])
        self.assertEqual(310, receipt["pull_request"])
        self.assertEqual("3112214ad67faea755d51514da9a82bddb0bb105", receipt["final_head"])
        self.assertEqual("91557968809f89f2bb37210e3b91654093e4b807", receipt["merge_commit"])
        self.assertEqual("COMPLETED", receipt["status"])
        self.assertEqual(235, receipt["assurance"][0]["test_count"])
        self.assertTrue(all(item["result"] in {"PASS", "ZERO"} for item in receipt["assurance"]))

    def test_state_stops_at_operator_required_parent_context_gate(self) -> None:
        state = load(STATE)
        self.assertEqual("COMPLETED", state["status"])
        self.assertEqual("C2AR-WP8-GATE-PREPARATION", state["active_packet"])
        self.assertEqual("CEAR-G8", state["active_gate"])
        self.assertTrue(state["operator_decision_required"])
        self.assertEqual("OPERATOR_REQUIRED_PARENT_CONTEXT_RESOLVER_POLICY_FREEZE", state["authority_required"])
        self.assertEqual("NOT_GRANTED", state["authority"]["parent_context_resolver"])
        self.assertEqual("NONE", state["authority"]["semantic_event_episode"])
        self.assertEqual("NONE", state["authority"]["release_publication_validation"])
        self.assertEqual([], state["blockers"])


if __name__ == "__main__":
    unittest.main()
