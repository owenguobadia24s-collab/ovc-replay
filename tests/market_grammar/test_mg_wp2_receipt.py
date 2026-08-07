from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RELEASE = ROOT / "docs/releases/c2e-c2g-c2p-market-grammar-v0-1/mg-wp2"
STATE = ROOT / "registries/opt_b/market_grammar/OVC_MARKET_GRAMMAR_PROGRAMME_STATE_v0_1.jsonc"
REGISTRY = ROOT / "registries/opt_b/market_grammar/MG_WP2_IMPLEMENTATION_REGISTRY_v0_1.json"


def load(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise AssertionError(f"not object: {path}")
    return value


class MarketGrammarWp2ReceiptTests(unittest.TestCase):
    def test_receipt_binds_exact_head_merge_and_assurance(self) -> None:
        receipt = load(RELEASE / "MG_WP2_POST_MERGE_RECEIPT.json")
        self.assertEqual("3aeaa3fcc060dfee5130404a81ce7e8f8886e437", receipt["final_head"])
        self.assertEqual("bd2d6e01c1c0b228ad40e457170e14effed0c409", receipt["merge_commit"])
        self.assertEqual(347, receipt["pull_request"])
        self.assertEqual(0, receipt["exact_final_head_assurance"]["unresolved_review_threads"])
        for key in ("repository_tests", "ovc_final_head", "compatibility", "merge_readiness"):
            self.assertEqual("SUCCESS", receipt["exact_final_head_assurance"][key]["conclusion"])

    def test_decision_is_delegated_pass_without_reserved_delta(self) -> None:
        decision = load(RELEASE / "MG_WP2_DELEGATED_DECISION.json")
        self.assertEqual("PASS", decision["decision"])
        self.assertTrue(decision["delegated_authority"])
        self.assertFalse(decision["operator_required"])
        self.assertEqual(
            "INACTIVE_NONCANONICAL_SHADOW_EXPERIMENT_IMPLEMENTATION_ONLY",
            decision["authority_delta"],
        )

    def test_qa_manifest_registry_and_state_preserve_wp2_completion(self) -> None:
        qa = load(RELEASE / "MG_WP2_QA_PACKET.json")
        manifest = load(RELEASE / "MG_WP2_IMPLEMENTATION_MANIFEST.json")
        registry = load(REGISTRY)
        state = load(STATE)
        self.assertEqual("COMPLETED", qa["status"])
        self.assertEqual("PASS", qa["qa_recommendation"])
        self.assertEqual("COMPLETED", manifest["status"])
        self.assertEqual("COMPLETED", registry["status"])
        packets = {item["packet_id"]: item for item in state["packets"]}
        self.assertEqual("COMPLETED", packets["MG-WP2"]["status"])
        self.assertNotEqual("MG-WP2", state["next_packet"])
        self.assertIn(
            packets["MG-WP3"]["status"],
            {"READY", "RUNNING", "IMPLEMENTED", "QA_REVIEW", "APPROVED", "COMPLETED"},
        )
        self.assertEqual("OPERATOR_REQUIRED", packets["MG-WP10"]["authority_required"])
        self.assertNotIn(state["status"], {"BLOCKED", "QUARANTINED"})


if __name__ == "__main__":
    unittest.main()
