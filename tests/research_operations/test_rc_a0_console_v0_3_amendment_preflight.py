from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RC_A0 = ROOT / "docs" / "releases" / "research-console-v0-3" / "rc-a0"
REG = ROOT / "registries" / "research_operations"


class RCA0ConsoleV03AmendmentPreflightTests(unittest.TestCase):
    def test_required_amendment_outputs_exist(self) -> None:
        required = (
            "docs/plans/research_operations/OVC_RESEARCH_CONSOLE_V0_3_INFORMATION_ARCHITECTURE_AMENDMENT_v0_1.md",
            "contracts/research_operations/console/OVC_RESEARCH_CONSOLE_INFORMATION_ARCHITECTURE_CONTRACT_v0_3.md",
            "registries/research_operations/RESEARCH_CONSOLE_WORKSPACE_REGISTRY_v0_3.yaml",
            "registries/research_operations/RESEARCH_CONSOLE_PANEL_REGISTRY_v0_3.yaml",
            "registries/research_operations/RESEARCH_CONSOLE_ROUTE_MIGRATION_REGISTRY_v0_3.yaml",
            "registries/research_operations/RESEARCH_CONSOLE_CONTEXT_STATE_REGISTRY_v0_3.yaml",
            "registries/research_operations/RESEARCH_CONSOLE_GLOBAL_SURFACE_REGISTRY_v0_3.yaml",
            "docs/releases/research-console-v0-3/rc-a0/RC_A0_AMENDMENT_PREFLIGHT_PACKET.json",
            "docs/releases/research-console-v0-3/rc-a0/RC_A0_V0_2_SUPERSESSION_RECORD.md",
            "docs/releases/research-console-v0-3/rc-a0/RC_A0_IMPLEMENTATION_SUMMARY.md",
        )
        for rel in required:
            self.assertTrue((ROOT / rel).is_file(), rel)

    def test_preflight_packet_is_complete(self) -> None:
        packet = json.loads((RC_A0 / "RC_A0_AMENDMENT_PREFLIGHT_PACKET.json").read_text(encoding="utf-8"))
        self.assertEqual(packet["baseline"]["commit"], "f704f33e4d5fc19f5807d0a92156b99afa8bce84")
        self.assertEqual(packet["supersession"]["v0_2_rc_wp1_pr"], 53)
        self.assertEqual(packet["supersession"]["v0_2_rc_wp1_pr_state"], "CLOSED_UNMERGED_SUPERSEDED")
        self.assertEqual(packet["blocking_issues"], 0)
        self.assertEqual(packet["rc_a0_disposition"], "COMPLETE_RC_A1_REVIEW_READY")
        self.assertEqual(len(packet["checks"]), 8)
        self.assertTrue(all(item["status"] == "PASS" for item in packet["checks"]))

    def test_exact_three_workspace_architecture(self) -> None:
        text = (REG / "RESEARCH_CONSOLE_WORKSPACE_REGISTRY_v0_3.yaml").read_text(encoding="utf-8")
        self.assertIn("primary_workspace_count: 3", text)
        self.assertEqual(text.count("workspace_id:"), 3)
        for workspace in ("OVERVIEW", "RESEARCH", "SYSTEM"):
            self.assertIn(f"workspace_id: {workspace}", text)
        self.assertIn("fourth_primary_workspace: PROHIBITED_WITHOUT_NEW_CONTRACT", text)

    def test_all_v0_2_routes_have_v0_3_destinations(self) -> None:
        text = (REG / "RESEARCH_CONSOLE_ROUTE_MIGRATION_REGISTRY_v0_3.yaml").read_text(encoding="utf-8")
        route_ids = (
            "OVERVIEW", "RESEARCH_DESK", "REPLAY", "EVIDENCE", "SESSIONS", "QUEUE",
            "HEALTH", "LINEAGE", "CATALOGUE", "RELEASES", "QA_GATES", "AUDIT", "CONFIG", "ABOUT",
        )
        self.assertEqual(text.count("v0_2_route_id:"), len(route_ids))
        for route_id in route_ids:
            self.assertIn(f"v0_2_route_id: {route_id}", text)
        self.assertIn("no_route_silently_deleted: true", text)
        self.assertIn("duplicate_active_information_architecture: PROHIBITED", text)

    def test_context_cutoff_and_global_surfaces_fail_closed(self) -> None:
        context = (REG / "RESEARCH_CONSOLE_CONTEXT_STATE_REGISTRY_v0_3.yaml").read_text(encoding="utf-8")
        surfaces = (REG / "RESEARCH_CONSOLE_GLOBAL_SURFACE_REGISTRY_v0_3.yaml").read_text(encoding="utf-8")
        self.assertIn("post_cutoff_access: DENIED", context)
        self.assertIn("workspace_navigation: PRESERVE_GLOBAL_CONTEXT", context)
        self.assertIn("inferred_release_switch: PROHIBITED", context)
        for surface_id in ("CONTEXTUAL_DETAIL_DRAWER", "COMMAND_PALETTE", "AMBIENT_HEALTH", "ACTIVITY_STREAM", "LOCAL_BADGE"):
            self.assertIn(f"surface_id: {surface_id}", surfaces)
        self.assertIn("command_palette_cannot_bypass_action_registry: true", surfaces)
        self.assertIn("activity_projection_cannot_replace_audit_source: true", surfaces)

    def test_v0_2_is_historical_and_rc_a1_is_lawful_successor(self) -> None:
        registry = (REG / "RESEARCH_OPERATIONS_IMPLEMENTATION_REGISTRY_v0_1.yaml").read_text(encoding="utf-8")
        self.assertIn("stage: SUPERSEDED_BY_RC_A0_V0_3_INFORMATION_ARCHITECTURE", registry)
        self.assertIn("rc_wp1_authority: REVOKED_SUPERSEDED_BEFORE_MERGE", registry)
        self.assertIn("stage: RC_A1_PASS_RC_WP1_V0_3_AUTHORISED", registry)
        self.assertIn("shell_implementation_authority: AUTHORISED_FIXTURE_ONLY_LOCAL_PRESENTATION", registry)
        for token in (
            "repository_mutation: NONE", "selector_mutation: NONE", "threshold_mutation: NONE",
            "market_authority: NONE", "probability_authority: NONE", "exposure_authority: NONE",
            "execution_authority: NONE", "agent_authority: NONE",
        ):
            self.assertIn(token, registry)


if __name__ == "__main__":
    unittest.main()
