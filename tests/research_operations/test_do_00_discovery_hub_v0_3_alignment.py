from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "registries" / "research_operations"
PACKET = ROOT / "docs" / "releases" / "discovery-operating-hub-v0-1" / "do-00" / "DO_00_PREFLIGHT_PACKET.json"


class DO00DiscoveryHubV03AlignmentTests(unittest.TestCase):
    def test_required_outputs_exist(self) -> None:
        required = (
            "contracts/research_operations/discovery_hub/OVC_DISCOVERY_OPERATING_HUB_AUTHORITY_CONTRACT_v0_1.md",
            "registries/research_operations/DISCOVERY_OPERATING_HUB_PROGRAMME_REGISTRY_v0_1.yaml",
            "registries/research_operations/DISCOVERY_OPERATING_HUB_WORKSPACE_ALIGNMENT_v0_1.yaml",
            "registries/research_operations/DISCOVERY_OPERATING_HUB_CONTEXT_ALIGNMENT_v0_1.yaml",
            "registries/research_operations/DISCOVERY_OPERATING_HUB_DEFERRED_CAPABILITIES_v0_1.yaml",
            "docs/releases/discovery-operating-hub-v0-1/do-00/DO_00_PREFLIGHT_PACKET.json",
            "docs/releases/discovery-operating-hub-v0-1/do-00/DO_00_IMPLEMENTATION_SUMMARY.md",
        )
        for rel in required:
            self.assertTrue((ROOT / rel).is_file(), rel)

    def test_preflight_records_v0_3_realignment(self) -> None:
        packet = json.loads(PACKET.read_text(encoding="utf-8"))
        self.assertEqual(packet["baseline"]["commit"], "f704f33e4d5fc19f5807d0a92156b99afa8bce84")
        self.assertEqual(packet["console_alignment"]["operative_target"], "OVC Research Console v0.3")
        self.assertEqual(packet["console_alignment"]["primary_workspaces"], ["OVERVIEW", "RESEARCH", "SYSTEM"])
        self.assertEqual(packet["console_alignment"]["v0_2_information_architecture"], "SUPERSEDED_AS_PRIMARY_NAVIGATION")
        self.assertEqual(packet["authority_delta"], "DESIGN_RECORDS_ONLY")
        self.assertEqual(packet["do_00_disposition"], "COMPLETE_V0_3_REALIGNMENT")
        self.assertEqual(packet["pending_prerequisites"], ["RC-A0", "RC-G0A"])
        self.assertEqual(packet["blocking_issues"], 0)
        self.assertTrue(all(check["status"] == "PASS" for check in packet["checks"]))

    def test_three_workspaces_account_for_all_v0_2_routes(self) -> None:
        text = (BASE / "DISCOVERY_OPERATING_HUB_WORKSPACE_ALIGNMENT_v0_1.yaml").read_text(encoding="utf-8")
        for workspace in ("workspace_id: OVERVIEW", "workspace_id: RESEARCH", "workspace_id: SYSTEM"):
            self.assertIn(workspace, text)
        former_routes = (
            "OVERVIEW",
            "RESEARCH_DESK",
            "REPLAY",
            "EVIDENCE",
            "SESSIONS",
            "QUEUE",
            "HEALTH",
            "LINEAGE",
            "CATALOGUE",
            "RELEASES",
            "QA_GATES",
            "AUDIT",
            "CONFIG",
            "ABOUT",
        )
        for route_id in former_routes:
            self.assertIn(f"  {route_id}:\n", text)
        self.assertIn("former_v0_2_routes_are_primary_navigation: false", text)
        self.assertIn("repository_scans_during_streamlit_rerun: PROHIBITED", text)

    def test_context_contract_is_presentation_only_and_cutoff_safe(self) -> None:
        text = (BASE / "DISCOVERY_OPERATING_HUB_CONTEXT_ALIGNMENT_v0_1.yaml").read_text(encoding="utf-8")
        self.assertIn("authority: PRESENTATION_ONLY_EXCLUDED_FROM_LOGICAL_AUTHORITY", text)
        self.assertIn("allowed: [OVERVIEW, RESEARCH, SYSTEM]", text)
        self.assertIn("rule: HARD_QUERY_BOUNDARY_IN_PROSPECTIVE_MODE", text)
        self.assertIn("post_cutoff_rendering: PROHIBITED", text)
        self.assertIn("result_action: FOCUS_OWNING_WORKSPACE_AND_OPEN_DRAWER", text)
        self.assertIn("ARBITRARY_FILESYSTEM_SEARCH", text)
        self.assertIn("REPOSITORY_MUTATION", text)
        self.assertIn("ordinary_page_views", text)

    def test_v0_2_safety_is_inherited_and_v0_3_is_not_deferred(self) -> None:
        programme = (BASE / "DISCOVERY_OPERATING_HUB_PROGRAMME_REGISTRY_v0_1.yaml").read_text(encoding="utf-8")
        deferred = (BASE / "DISCOVERY_OPERATING_HUB_DEFERRED_CAPABILITIES_v0_1.yaml").read_text(encoding="utf-8")
        self.assertIn("operative_target: v0.3", programme)
        for token in (
            "READ_ONLY_AUTHORITY",
            "HEALTH_TRUTH",
            "EXPLICIT_EMPTY_STATES",
            "CUTOFF_SAFETY",
            "DETERMINISTIC_READ_MODEL",
            "LOCAL_ONLY",
            "NO_MUTATION",
        ):
            self.assertIn(token, programme)
        self.assertIn("Research Console v0.3 unified workspaces are the operative target", deferred)
        self.assertNotIn("name: Research Console v0.3 unified workspaces\n    state: DEFERRED", deferred)
        self.assertIn("RESEARCH_CONSOLE_V0_2_FOURTEEN_ROUTE_PRIMARY_NAVIGATION", deferred)
        self.assertIn("SUPERSEDED_AS_PRIMARY_INFORMATION_ARCHITECTURE", deferred)

    def test_authority_remains_bounded(self) -> None:
        contract = (ROOT / "contracts" / "research_operations" / "discovery_hub" / "OVC_DISCOVERY_OPERATING_HUB_AUTHORITY_CONTRACT_v0_1.md").read_text(encoding="utf-8")
        programme = (BASE / "DISCOVERY_OPERATING_HUB_PROGRAMME_REGISTRY_v0_1.yaml").read_text(encoding="utf-8")
        self.assertIn("Research-record creation remains outside the v0.3 UI", contract)
        self.assertIn("console_research_writes: DENIED_PENDING_RC_WP7_OR_SEPARATE_ACTION_GATE", programme)
        self.assertIn("validation_consumption: LOCKED_UNCONSUMED", programme)
        for token in ("market: NONE", "probability: NONE", "exposure: NONE", "trading: NONE", "execution: NONE", "agents: NONE", "remote_deployment: NONE"):
            self.assertIn(token, programme)


if __name__ == "__main__":
    unittest.main()
