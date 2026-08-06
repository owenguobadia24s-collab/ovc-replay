from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RELEASE = ROOT / "docs/releases/c2e-c2g-c2p-market-grammar-v0-1/mg-wp1"
STATE = ROOT / "registries/opt_b/market_grammar/OVC_MARKET_GRAMMAR_PROGRAMME_STATE_v0_1.jsonc"


def load(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise AssertionError(f"not object: {path}")
    return value


class MarketGrammarWp1ReceiptTests(unittest.TestCase):
    def test_receipt_binds_exact_head_merge_and_assurance(self) -> None:
        receipt = load(RELEASE / "MG_WP1_POST_MERGE_RECEIPT.json")
        self.assertEqual("7f3eb4391378309f26209f1370fd6ddbe23a1993", receipt["final_head"])
        self.assertEqual("3686e3eca363d7ed88066b3cdd67210ea85937b2", receipt["merge_commit"])
        self.assertEqual(345, receipt["pull_request"])
        self.assertEqual(0, receipt["exact_final_head_assurance"]["unresolved_review_threads"])
        for key in ("repository_tests", "ovc_final_head", "compatibility", "merge_readiness"):
            self.assertEqual("SUCCESS", receipt["exact_final_head_assurance"][key]["conclusion"])

    def test_decision_is_delegated_pass_without_reserved_delta(self) -> None:
        decision = load(RELEASE / "MG_WP1_DELEGATED_DECISION.json")
        self.assertEqual("PASS", decision["decision"])
        self.assertTrue(decision["delegated_authority"])
        self.assertFalse(decision["operator_required"])
        self.assertEqual(
            "INACTIVE_NONCANONICAL_SHADOW_EXPERIMENT_IMPLEMENTATION_ONLY",
            decision["authority_delta"],
        )

    def test_qa_manifest_and_state_complete_wp1_and_unlock_only_wp2(self) -> None:
        qa = load(RELEASE / "MG_WP1_QA_PACKET.json")
        manifest = load(RELEASE / "MG_WP1_IMPLEMENTATION_MANIFEST.json")
        state = load(STATE)
        self.assertEqual("COMPLETED", qa["status"])
        self.assertEqual("PASS", qa["qa_recommendation"])
        self.assertEqual("COMPLETED", manifest["status"])
        packets = {item["packet_id"]: item for item in state["packets"]}
        self.assertEqual("COMPLETED", packets["MG-WP1"]["status"])
        self.assertEqual("READY", packets["MG-WP2"]["status"])
        self.assertEqual("PLANNED", packets["MG-WP3"]["status"])
        self.assertEqual("MG-WP2", state["next_packet"])
        self.assertEqual("READY", state["status"])


if __name__ == "__main__":
    unittest.main()
