from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "docs/releases/c2e-c2g-c2p-market-grammar-v0-1/mg-wp2"
STATE = ROOT / "registries/opt_b/market_grammar/OVC_MARKET_GRAMMAR_PROGRAMME_STATE_v0_1.jsonc"
IMPLEMENTATION = ROOT / "registries/opt_b/market_grammar/MG_WP2_IMPLEMENTATION_REGISTRY_v0_1.json"


def load(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise AssertionError(f"not object: {path}")
    return value


class MarketGrammarWp2PacketTests(unittest.TestCase):
    def test_manifest_and_registry_are_inactive_and_complete(self) -> None:
        manifest = load(BASE / "MG_WP2_IMPLEMENTATION_MANIFEST.json")
        registry = load(IMPLEMENTATION)
        self.assertIn(manifest["status"], {"IMPLEMENTED_PENDING_QA", "COMPLETED"})
        self.assertIn(registry["status"], {"IMPLEMENTED_PENDING_QA", "COMPLETED"})
        self.assertEqual("INACTIVE_NONCANONICAL_SHADOW_EXPERIMENT_IMPLEMENTATION_ONLY", manifest["authority"])
        self.assertIn("C2G", registry["forbidden_reads"])
        self.assertIn("OUTCOMES", registry["forbidden_reads"])
        self.assertTrue(set(registry["artifacts"]).issubset(set(manifest["artifacts"])))

    def test_qa_requires_exact_head_assurance_and_zero_reserved_delta(self) -> None:
        qa = load(BASE / "MG_WP2_QA_PACKET.json")
        self.assertIn(qa["status"], {"QA_REVIEW", "COMPLETED"})
        self.assertIn(qa["qa_recommendation"], {"PASS_IF_EXACT_HEAD_ASSURANCE_PASSES", "PASS"})
        self.assertEqual("PASS_ZERO", qa["checks"]["reserved_authority"])
        self.assertEqual([], qa["blockers"])
        self.assertEqual([], qa["warnings"])

    def test_programme_state_preserves_wp1_and_routes_no_further_than_wp3(self) -> None:
        state = load(STATE)
        packets = {item["packet_id"]: item for item in state["packets"]}
        self.assertEqual("COMPLETED", packets["MG-WP1"]["status"])
        self.assertIn(packets["MG-WP2"]["status"], {"RUNNING", "IMPLEMENTED", "QA_REVIEW", "APPROVED", "COMPLETED"})
        self.assertIn(packets["MG-WP3"]["status"], {"PLANNED", "READY", "RUNNING", "IMPLEMENTED", "QA_REVIEW", "APPROVED", "COMPLETED"})
        self.assertEqual("OPERATOR_REQUIRED", packets["MG-WP10"]["authority_required"])
        self.assertNotIn(state["status"], {"BLOCKED", "QUARANTINED"})


if __name__ == "__main__":
    unittest.main()
