from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SELECTORS = ROOT / "registries/opt_b/c2/C2_ACTIVE_SELECTORS.yaml"
RETIREMENT = ROOT / "registries/opt_b/c2/C2_LEGACY_RETIREMENT.yaml"
AUTHORITY = ROOT / "registries/authority/C2_ACTIVE_DISCOVERY_AUTHORITY.yaml"
GATE = ROOT / "docs/releases/opt-b-c2-v2/activation/C2_ACTIVE_DISCOVERY_GATE_PACKET.json"
DECISION = ROOT / "docs/releases/opt-b-c2-v2/activation/C2_ACTIVE_DISCOVERY_OPERATOR_DECISION.md"


class C2ActiveDiscoveryActivationTests(unittest.TestCase):
    def test_gate_activates_exact_remote_verified_discovery_release(self) -> None:
        gate = json.loads(GATE.read_text(encoding="utf-8"))
        self.assertEqual(gate["decision"], "PASS_ACTIVE_DISCOVERY_SELECTOR_AND_LEGACY_RETIREMENT")
        self.assertEqual(gate["blocking_issues"], 0)
        self.assertEqual(gate["activation"]["authority_state"], "ACTIVE_DISCOVERY")
        self.assertEqual(gate["activation"]["manifest_sha256"], "c5723e9e6837816c9ff0ed023112890aee6589e22518fe8365cbff2653169a33")
        self.assertEqual(gate["prerequisites"]["c2_r2_remote_verification"], "PASS_FULL_REMOTE_BYTE_VERIFICATION")

    def test_selector_transaction_is_atomic_and_development_unselected(self) -> None:
        text = SELECTORS.read_text(encoding="utf-8")
        self.assertIn("atomic: true", text)
        self.assertIn("authority_state: ACTIVE_DISCOVERY", text)
        self.assertEqual(text.count("selector_state: ACTIVE"), 1)
        self.assertGreaterEqual(text.count("selector_state: NONE"), 2)
        self.assertIn("authority_state: REMOTE_VERIFIED_REFERENCE_ONLY", text)

    def test_legacy_b_state_is_not_a_rollback_target(self) -> None:
        text = RETIREMENT.read_text(encoding="utf-8")
        self.assertIn("state: HISTORICAL_SUPERSEDED", text)
        self.assertIn("rollback_target: DENIED", text)
        self.assertIn("legacy_reactivation: PROHIBITED", text)
        self.assertIn("target: C1_ONLY_OPERATION", text)

    def test_authority_amendment_retains_non_trading_boundaries(self) -> None:
        text = AUTHORITY.read_text(encoding="utf-8")
        self.assertIn("state: C2_ACTIVE_DISCOVERY_BSTATE_HISTORICAL_SUPERSEDED", text)
        self.assertIn("validation_consumption: LOCKED_UNCONSUMED", text)
        for field in ("probability_authority", "exposure_authority", "trading_authority", "execution_authority"):
            self.assertIn(f"{field}: NONE", text)

    def test_operator_decision_is_explicit(self) -> None:
        text = DECISION.read_text(encoding="utf-8")
        self.assertIn("activate the exact remote-verified C2 Discovery release", text)
        self.assertIn("returns operation to the existing C1-only boundary", text)
        self.assertIn("grants no trading or execution authority", text)


if __name__ == "__main__":
    unittest.main()
