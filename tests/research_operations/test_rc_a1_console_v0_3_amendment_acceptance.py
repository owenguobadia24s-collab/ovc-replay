from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REG = ROOT / "registries" / "research_operations"
RC_A1 = ROOT / "docs" / "releases" / "research-console-v0-3" / "rc-a1"


class RCA1ConsoleV03AmendmentAcceptanceTests(unittest.TestCase):
    def test_gate_packet_passes_without_blockers(self) -> None:
        packet = json.loads((RC_A1 / "RC_A1_GATE_PACKET.json").read_text(encoding="utf-8"))
        self.assertEqual(packet["decision"], "PASS_V0_3_INFORMATION_ARCHITECTURE_ACCEPTED")
        self.assertEqual(packet["blocking_issues"], 0)
        self.assertEqual(packet["disposition"], "RC_A1_PASS_RC_WP1_V0_3_AUTHORISED")
        self.assertEqual(len(packet["checks"]), 10)
        self.assertTrue(all(item["status"] == "PASS" for item in packet["checks"]))
        self.assertEqual(packet["review"]["rc_a0_reviewed_head"], "8373a0129e482e7b1a27dc574f236e804a703ef0")
        self.assertEqual(packet["review"]["integration_baseline_main"], "2a1b22dc248ebe0f0c1b360062e9e6c1402a5b1a")

    def test_exact_workspace_and_migration_contract_is_accepted(self) -> None:
        workspace = (REG / "RESEARCH_CONSOLE_WORKSPACE_REGISTRY_v0_3.yaml").read_text(encoding="utf-8")
        migration = (REG / "RESEARCH_CONSOLE_ROUTE_MIGRATION_REGISTRY_v0_3.yaml").read_text(encoding="utf-8")
        self.assertIn("status: ACCEPTED_BY_RC_A1", workspace)
        self.assertEqual(workspace.count("workspace_id:"), 3)
        self.assertEqual(migration.count("v0_2_route_id:"), 14)
        self.assertIn("migration_accepted_at_gate: RC_A1", migration)
        self.assertIn("duplicate_active_information_architecture: PROHIBITED", migration)

    def test_context_and_cutoff_laws_are_accepted(self) -> None:
        context = (REG / "RESEARCH_CONSOLE_CONTEXT_STATE_REGISTRY_v0_3.yaml").read_text(encoding="utf-8")
        self.assertIn("status: ACCEPTED_BY_RC_A1", context)
        self.assertIn("post_cutoff_access: DENIED", context)
        self.assertIn("review_surface: EXPLICITLY_LABELLED_POST_CUTOFF", context)
        self.assertIn("workspace_navigation: PRESERVE_GLOBAL_CONTEXT", context)
        self.assertIn("read_model_change: REQUIRE_EXPLICIT_REBIND", context)
        self.assertIn("inferred_release_switch: PROHIBITED", context)

    def test_global_surfaces_are_bounded_read_only(self) -> None:
        surfaces = (REG / "RESEARCH_CONSOLE_GLOBAL_SURFACE_REGISTRY_v0_3.yaml").read_text(encoding="utf-8")
        for surface_id in (
            "ICON_RAIL", "WORKSPACE_TABS", "CONTEXT_BAR", "CONTEXTUAL_DETAIL_DRAWER",
            "COMMAND_PALETTE", "AMBIENT_HEALTH", "ACTIVITY_STREAM", "LOCAL_BADGE",
        ):
            self.assertIn(f"surface_id: {surface_id}", surfaces)
        for token in (
            "WRITE_RECORD", "EDIT_REPOSITORY", "ACTIVATE_RELEASE", "CHANGE_SELECTOR",
            "CHANGE_THRESHOLD", "DEPLOY_CONSOLE",
        ):
            self.assertIn(token, surfaces)
        self.assertIn("command_palette_cannot_bypass_action_registry: true", surfaces)
        self.assertIn("activity_projection_cannot_replace_audit_source: true", surfaces)

    def test_rc_wp1_authority_is_fixture_only(self) -> None:
        packet = json.loads((RC_A1 / "RC_A1_GATE_PACKET.json").read_text(encoding="utf-8"))
        authority = packet["authority_delta"]
        self.assertEqual(authority["rc_wp1_v0_3"], "AUTHORISED_FIXTURE_ONLY_LOCAL_PRESENTATION")
        self.assertEqual(authority["live_projection_authority"], "DENIED_PENDING_LATER_GATE")
        self.assertEqual(authority["research_write_authority"], "DENIED_PENDING_SEPARATE_GATE")
        for key in (
            "repository_mutation", "selector_mutation", "threshold_mutation", "release_activation",
            "market_authority", "probability_authority", "exposure_authority", "execution_authority",
            "agent_authority",
        ):
            self.assertEqual(authority[key], "NONE")
        self.assertEqual(authority["deployment_authority"], "LOCAL_ONLY_NO_REMOTE_DEPLOY")

    def test_implementation_registry_points_to_next_workstream(self) -> None:
        registry = (REG / "RESEARCH_OPERATIONS_IMPLEMENTATION_REGISTRY_v0_1.yaml").read_text(encoding="utf-8")
        self.assertIn("stage: RC_A1_PASS_RC_WP1_V0_3_AUTHORISED", registry)
        self.assertIn("rc_a1: PASS", registry)
        self.assertIn("shell_implementation_authority: AUTHORISED_FIXTURE_ONLY_LOCAL_PRESENTATION", registry)
        self.assertIn("next_workstream: RC_WP1_V0_3_DESIGN_SYSTEM_UNIFIED_SHELL_AND_NAVIGATION", registry)
        self.assertIn("rc_wp1_authority: REVOKED_SUPERSEDED_BEFORE_MERGE", registry)


if __name__ == "__main__":
    unittest.main()
