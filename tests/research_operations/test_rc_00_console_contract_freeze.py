from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


class RC00ResearchConsoleContractFreezeTests(unittest.TestCase):
    def test_required_rc00_outputs_exist(self) -> None:
        required = (
            "contracts/research_operations/console/OVC_RESEARCH_CONSOLE_UI_AUTHORITY_CONTRACT_v0_2.md",
            "registries/research_operations/RESEARCH_CONSOLE_ROUTE_REGISTRY_v0_2.yaml",
            "registries/research_operations/RESEARCH_CONSOLE_CARD_REGISTRY_v0_2.yaml",
            "registries/research_operations/RESEARCH_CONSOLE_STATUS_REGISTRY_v0_2.yaml",
            "registries/research_operations/RESEARCH_CONSOLE_EMPTY_STATE_REGISTRY_v0_2.yaml",
            "registries/research_operations/RESEARCH_CONSOLE_ACTION_REGISTRY_v0_2.yaml",
            "docs/releases/research-console-v0-2/rc-00/RC_00_PREFLIGHT_PACKET.json",
            "docs/releases/research-console-v0-2/rc-00/RC_00_IMPLEMENTATION_SUMMARY.md",
        )
        for rel in required:
            self.assertTrue((ROOT / rel).is_file(), rel)

    def test_preflight_packet_is_complete_and_ready_for_rc_g0(self) -> None:
        packet = json.loads((ROOT / "docs/releases/research-console-v0-2/rc-00/RC_00_PREFLIGHT_PACKET.json").read_text())
        self.assertEqual(packet["baseline"]["commit"], "4cc23b0f746feaa3fc91d1b6a956a0d4961a88dc")
        self.assertEqual(packet["baseline"]["test_execution_state"], "PASS")
        self.assertEqual(packet["baseline"]["github_tests_workflow_run_id"], 30192017977)
        self.assertEqual(packet["authority_delta"], "DESIGN_RECORDS_ONLY")
        self.assertEqual(packet["rc00_disposition"], "COMPLETE_RC_G0_REVIEW_READY")
        self.assertEqual(packet["rc_g0_recommendation"], "READY_FOR_OPERATOR_REVIEW")

    def test_route_registry_freezes_planned_routes_read_only(self) -> None:
        registry = (ROOT / "registries/research_operations/RESEARCH_CONSOLE_ROUTE_REGISTRY_v0_2.yaml").read_text()
        for route_id in ("OVERVIEW", "RESEARCH_DESK", "REPLAY", "EVIDENCE", "SESSIONS", "QUEUE", "HEALTH", "LINEAGE", "CATALOGUE", "RELEASES", "QA_GATES", "AUDIT", "CONFIG", "ABOUT"):
            self.assertIn(f"route_id: {route_id}", registry)
        self.assertNotIn("authority: WRITE", registry)
        self.assertNotIn("authority: MUTATE", registry)

    def test_action_registry_prohibits_mutation_and_deployment(self) -> None:
        registry = (ROOT / "registries/research_operations/RESEARCH_CONSOLE_ACTION_REGISTRY_v0_2.yaml").read_text()
        for action_id in ("CHANGE_SELECTOR", "CHANGE_THRESHOLD", "ACTIVATE_RELEASE", "EDIT_REPOSITORY", "DEPLOY_CONSOLE", "CREATE_MARKET_CLASSIFICATION", "CREATE_PROBABILITY_OR_EXPOSURE_OBJECT"):
            self.assertIn(f"action_id: {action_id}", registry)
        self.assertIn("ui_treatment: REPLACE_WITH_NON_CLICKABLE_LOCAL_BADGE", registry)
        self.assertIn("unregistered_action: PROHIBITED", registry)

    def test_health_truth_and_empty_state_rules_are_fail_closed(self) -> None:
        status = (ROOT / "registries/research_operations/RESEARCH_CONSOLE_STATUS_REGISTRY_v0_2.yaml").read_text()
        empty = (ROOT / "registries/research_operations/RESEARCH_CONSOLE_EMPTY_STATE_REGISTRY_v0_2.yaml").read_text()
        self.assertIn("no_signal_is_pass: false", status)
        self.assertIn("unknown_status_fallback: BLOCK", status)
        self.assertIn("empty_cannot_imply_pass: true", empty)
        self.assertIn("message_must_include_next_action: true", empty)

    def test_existing_authority_remains_bounded(self) -> None:
        authority = (ROOT / "registries/research_operations/RESEARCH_OPERATIONS_IMPLEMENTATION_REGISTRY_v0_1.yaml").read_text()
        self.assertIn("console: APPROVED_LOCAL_READ_ONLY_OPERATION", authority)
        for token in ("market: NONE", "probability: NONE", "exposure: NONE", "execution: NONE", "agent: NONE"):
            self.assertIn(token, authority)


if __name__ == "__main__":
    unittest.main()
