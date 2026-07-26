from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCOPE = ROOT / "registries/opt_b/c1/C1_WP4_REPLAY_SCOPE.yaml"
GATE = ROOT / "docs/releases/opt-b-c1-v2/b1-g0/B1_G0_GATE_PACKET.json"
DECISION = ROOT / "docs/releases/opt-b-c1-v2/b1-g0/B1_G0_OPERATOR_DECISION.md"
IMPLEMENTATION = ROOT / "registries/opt_b/c1/C1_IMPLEMENTATION_REGISTRY.yaml"


class C1B1G0ReplayScopeTests(unittest.TestCase):
    def test_gate_artifacts_exist(self) -> None:
        for path in (SCOPE, GATE, DECISION, IMPLEMENTATION):
            self.assertTrue(path.is_file(), path)

    def test_scope_binds_exact_discovery_and_development_parents(self) -> None:
        text = SCOPE.read_text(encoding="utf-8")
        for token in (
            "C1.WP4.GBPUSD.DISCOVERY_DEVELOPMENT.v1",
            "OPT-A.GBPUSD.DISCOVERY.2021_2023.v2",
            "0cbcafa9421449574b61bfeec24f634de99cbbbc6e7a53d09ace8f702182ab8c",
            "OPT-A.GBPUSD.DEVELOPMENT.2024.v2",
            "25e1be8a7edb0e96017c45bf35f4e788345f94b22a8ed9bb0874c86338ba64cc",
            "canonical_clocks: [15M, 2H_A_L]",
            "price_sides: [BID, ASK]",
        ):
            self.assertIn(token, text)

    def test_validation_is_locked_and_excluded(self) -> None:
        text = SCOPE.read_text(encoding="utf-8")
        self.assertIn("consumption_state: LOCKED_UNCONSUMED", text)
        self.assertIn("replay_authority: DENIED", text)
        self.assertIn("no_validation_consumption", text)

    def test_scope_does_not_grant_release_or_downstream_authority(self) -> None:
        text = SCOPE.read_text(encoding="utf-8")
        for token in (
            "release_freeze_without_wp4_qa",
            "r2_publication",
            "selector_activation",
            "c2_consumption",
            "probability_or_exposure_authority",
        ):
            self.assertIn(token, text)

    def test_gate_packet_is_bounded_pass(self) -> None:
        packet = json.loads(GATE.read_text(encoding="utf-8"))
        self.assertEqual(packet["decision"], "PASS")
        self.assertEqual(packet["approved_roles"], ["DISCOVERY", "DEVELOPMENT"])
        self.assertEqual(packet["validation_consumption"], "LOCKED_UNCONSUMED")
        self.assertEqual(packet["authority_delta"]["wp4_market_replay"], "AUTHORISED_EXACT_SCOPE_ONLY")
        self.assertEqual(packet["authority_delta"]["r2_publication"], "DENIED")
        self.assertIs(packet["side_effects_performed"], False)

    def test_implementation_registry_authorises_only_wp4_scope(self) -> None:
        text = IMPLEMENTATION.read_text(encoding="utf-8")
        self.assertIn("market_replay: AUTHORISED_EXACT_WP4_SCOPE_ONLY", text)
        self.assertIn("local_release_freeze: DENIED_PENDING_WP4_QA_AND_OPERATOR_DECISION", text)
        self.assertIn("validation_consumption: LOCKED_UNCONSUMED", text)
        self.assertIn("c1_selectors_return_to_none: true", text)


if __name__ == "__main__":
    unittest.main()
