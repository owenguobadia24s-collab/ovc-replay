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
CORRECTIVE = ROOT / "docs/releases/opt-b-c1-v2/corrective/c1c-g5/C1C_G4_G5_COORDINATED_SELECTOR_TRANSACTION.json"


class C2ActiveDiscoveryActivationTests(unittest.TestCase):
    def test_historical_gate_activates_exact_remote_verified_discovery_release(self) -> None:
        gate = json.loads(GATE.read_text(encoding="utf-8"))
        self.assertEqual(gate["decision"], "PASS_ACTIVE_DISCOVERY_SELECTOR_AND_LEGACY_RETIREMENT")
        self.assertEqual(gate["blocking_issues"], 0)
        self.assertEqual(gate["activation"]["authority_state"], "ACTIVE_DISCOVERY")
        self.assertEqual(gate["activation"]["manifest_sha256"], "c5723e9e6837816c9ff0ed023112890aee6589e22518fe8365cbff2653169a33")
        self.assertEqual(gate["prerequisites"]["c2_r2_remote_verification"], "PASS_FULL_REMOTE_BYTE_VERIFICATION")

    def test_current_selector_transaction_is_atomic_and_development_unselected(self) -> None:
        text = SELECTORS.read_text(encoding="utf-8")
        self.assertIn("atomic: true", text)
        self.assertIn("authority_state: ACTIVE_DISCOVERY", text)
        self.assertEqual(text.count("selector_state: ACTIVE"), 1)
        self.assertGreaterEqual(text.count("selector_state: NONE"), 2)
        self.assertIn("authority_state: REMOTE_VERIFIED_REFERENCE_ONLY", text)
        if CORRECTIVE.exists():
            transaction = json.loads(CORRECTIVE.read_text(encoding="utf-8"))
            self.assertTrue(transaction["atomic_on_main_merge"])
            self.assertIn("OPT-B.C2.GBPUSD.DISCOVERY.2021_2023.v2", text)
            self.assertIn("OPT-B.C2.GBPUSD.DEVELOPMENT.2024.v2", text)
            self.assertIn("C1C-G4-G5-COORDINATED-SELECTOR-TRANSACTION-2026-07-28", text)
        else:
            self.assertIn("OPT-B.C2.GBPUSD.DISCOVERY.2021_2023.v1", text)

    def test_legacy_b_state_is_not_a_rollback_target(self) -> None:
        text = RETIREMENT.read_text(encoding="utf-8")
        self.assertIn("state: HISTORICAL_SUPERSEDED", text)
        self.assertIn("rollback_target: DENIED", text)
        self.assertIn("legacy_reactivation: PROHIBITED", text)
        self.assertIn("target: C1_ONLY_OPERATION", text)

    def test_current_authority_retains_non_trading_boundaries(self) -> None:
        text = AUTHORITY.read_text(encoding="utf-8")
        if CORRECTIVE.exists():
            self.assertIn("state: C2_V2_ACTIVE_DISCOVERY_C1_V2_PARENT_BSTATE_HISTORICAL_SUPERSEDED", text)
            self.assertIn("OPT-B.C2.GBPUSD.DISCOVERY.2021_2023.v2", text)
            self.assertIn("semantic_equivalence: PASS_ZERO_STATE_OR_TRANSITION_VALUE_DRIFT", text)
            for field in (
                "probability_authority", "risk_authority", "exposure_authority",
                "trading_authority", "execution_authority", "agent_write_authority",
            ):
                self.assertIn(f"{field}: NONE", text)
        else:
            self.assertIn("state: C2_ACTIVE_DISCOVERY_BSTATE_HISTORICAL_SUPERSEDED", text)
            for field in ("probability_authority", "exposure_authority", "trading_authority", "execution_authority"):
                self.assertIn(f"{field}: NONE", text)
        self.assertIn("validation_consumption: LOCKED_UNCONSUMED", text)

    def test_historical_operator_decision_is_explicit(self) -> None:
        text = DECISION.read_text(encoding="utf-8")
        self.assertIn("activate the exact remote-verified C2 Discovery release", text)
        self.assertIn("returns operation to the existing C1-only boundary", text)
        self.assertIn("grants no trading or execution authority", text)


if __name__ == "__main__":
    unittest.main()
