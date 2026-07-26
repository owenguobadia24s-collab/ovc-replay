from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


class RCG0ConsolePreflightReviewTests(unittest.TestCase):
    def test_gate_outputs_exist(self) -> None:
        for rel in (
            "docs/releases/research-console-v0-2/rc-g0/RC_G0_GATE_PACKET.json",
            "docs/releases/research-console-v0-2/rc-g0/RC_G0_OPERATOR_DECISION.md",
        ):
            self.assertTrue((ROOT / rel).is_file(), rel)

    def test_gate_packet_passes_and_authorises_only_rc_wp1(self) -> None:
        packet = json.loads((ROOT / "docs/releases/research-console-v0-2/rc-g0/RC_G0_GATE_PACKET.json").read_text())
        self.assertEqual(packet["disposition"], "PASS")
        self.assertEqual(packet["rc00_merge_commit"], "2e7f88e2a42e3feba4b4c1c7a2ea448e0a6b5b01")
        self.assertEqual(packet["verification"]["tests_conclusion"], "success")
        self.assertEqual(packet["authorised_next_workstream"], "RC-WP1_DESIGN_SYSTEM_SHELL_AND_NAVIGATION")
        self.assertEqual(packet["authority_delta"], "AUTHORISE_RC_WP1_LOCAL_PRESENTATION_BUILD_ONLY")

    def test_restrictions_remain_fail_closed(self) -> None:
        packet = json.loads((ROOT / "docs/releases/research-console-v0-2/rc-g0/RC_G0_GATE_PACKET.json").read_text())
        restrictions = packet["restrictions"]
        self.assertEqual(restrictions["repository_mutation_from_ui"], "NONE")
        self.assertEqual(restrictions["selector_mutation"], "NONE")
        self.assertEqual(restrictions["threshold_mutation"], "NONE")
        self.assertEqual(restrictions["market_authority"], "NONE")
        self.assertEqual(restrictions["probability_authority"], "NONE")
        self.assertEqual(restrictions["exposure_authority"], "NONE")
        self.assertEqual(restrictions["execution_authority"], "NONE")
        self.assertEqual(restrictions["agent_authority"], "NONE")
        self.assertEqual(restrictions["remote_deployment"], "DENIED")

    def test_registry_records_rc_g0_pass_and_blocks_later_authority(self) -> None:
        registry = (ROOT / "registries/research_operations/RESEARCH_OPERATIONS_IMPLEMENTATION_REGISTRY_v0_1.yaml").read_text()
        self.assertIn("stage: RC_G0_PASS_RC_WP1_AUTHORISED", registry)
        self.assertIn("rc_g0: PASS", registry)
        self.assertIn("rc_wp1_authority: AUTHORISED_FIXTURE_ONLY_LOCAL_PRESENTATION", registry)
        self.assertIn("live_projection_authority: DENIED_PENDING_RC_G2", registry)
        self.assertIn("live_research_surface_authority: DENIED_PENDING_RC_G3", registry)
        self.assertIn("research_write_authority: DENIED_PENDING_SEPARATE_GATE", registry)


if __name__ == "__main__":
    unittest.main()
