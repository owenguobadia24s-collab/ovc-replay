from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
GATE = ROOT / "docs/releases/opt-b-c1-v2/c1-c2-handoff/C1_C2_HANDOFF_GATE_PACKET.json"
SELECTORS = ROOT / "registries/opt_b/c1/C1_ACTIVE_SELECTORS.yaml"
RELEASES = ROOT / "registries/opt_b/c1/C1_RELEASE_REGISTRY.yaml"
AUTHORITY = ROOT / "registries/authority/C1_TO_C2_ACTIVE_HANDOFF_AUTHORITY.yaml"


class C1C2HandoffActiveTests(unittest.TestCase):
    def test_gate_passes_without_open_blockers(self) -> None:
        gate = json.loads(GATE.read_text(encoding="utf-8"))
        self.assertEqual(gate["decision"], "PASS_C1_ACTIVE_C2_BUILD_AND_REPLAY_SCOPE_AUTHORISED")
        self.assertEqual(gate["blocking_issues"], 0)
        self.assertTrue(all(check["status"] == "PASS" for check in gate["checks"]))

    def test_exact_c1_roles_are_active_and_validation_is_locked(self) -> None:
        selectors = SELECTORS.read_text(encoding="utf-8")
        self.assertIn("state: ACTIVE", selectors)
        self.assertEqual(selectors.count("selector_state: ACTIVE"), 2)
        self.assertIn("authority_state: ACTIVE_DISCOVERY", selectors)
        self.assertIn("authority_state: ACTIVE_DEVELOPMENT", selectors)
        self.assertEqual(selectors.count("selector_state: NONE"), 1)
        self.assertIn("validation_consumption_state: LOCKED_UNCONSUMED", selectors)

    def test_c2_scope_is_bounded_and_not_active(self) -> None:
        gate = json.loads(GATE.read_text(encoding="utf-8"))
        authority = AUTHORITY.read_text(encoding="utf-8")
        self.assertEqual(
            gate["c2_scope"]["consumption"],
            "AUTHORISED_FOR_C2_BUILD_AND_REPLAY_SCOPE_PENDING_C2_GATE",
        )
        self.assertEqual(gate["c2_scope"]["selector"], "NONE")
        self.assertIn("c2_activation: DENIED_PENDING_C2_GATES", authority)
        self.assertIn("c2_writeback_to_c1: PROHIBITED", authority)

    def test_release_registry_binds_active_exact_releases(self) -> None:
        releases = RELEASES.read_text(encoding="utf-8")
        self.assertIn("status: C1_TO_C2_HANDOFF_PASS_C1_ACTIVE_C2_SCOPE_AUTHORISED", releases)
        self.assertEqual(releases.count("selector_state: ACTIVE"), 2)
        self.assertIn("authority_state: ACTIVE_DISCOVERY", releases)
        self.assertIn("authority_state: ACTIVE_DEVELOPMENT", releases)
        self.assertIn("c2_handoff: AUTHORISED_FOR_C2_BUILD_AND_REPLAY_SCOPE_PENDING_C2_GATE", releases)

    def test_rollback_and_non_market_authority_remain_exact(self) -> None:
        gate = json.loads(GATE.read_text(encoding="utf-8"))
        self.assertEqual(gate["rollback"], "RETURN_ALL_C1_ROLE_SELECTORS_TO_NONE")
        for key in ("probability", "exposure", "trading", "execution"):
            self.assertEqual(gate[key], "NONE")


if __name__ == "__main__":
    unittest.main()
