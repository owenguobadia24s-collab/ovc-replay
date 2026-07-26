from __future__ import annotations

import json
import unittest
from pathlib import Path

from apps.research_console.components import normalize_status
from apps.research_console.fixtures import fixture_bundle
from apps.research_console.state import (
    GLOBAL_CONTEXT_DEFAULTS,
    WORKSPACES,
    context_fingerprint,
    initialise_mapping,
    select_object,
    switch_workspace,
    update_context,
)

ROOT = Path(__file__).resolve().parents[2]
GATE = ROOT / "docs" / "releases" / "research-console-v0-3" / "rc-g1"
REG = ROOT / "registries" / "research_operations"


class RCG1V03ShellAcceptanceTests(unittest.TestCase):
    def test_gate_packet_and_decision_are_exact(self) -> None:
        packet = json.loads((GATE / "RC_G1_GATE_PACKET.json").read_text(encoding="utf-8"))
        self.assertEqual(packet["decision"], "PASS_SHELL_CONTEXT_AND_RESPONSIVE_CONTRACT_ACCEPTED")
        self.assertEqual(packet["review"]["implementation_pull_request"], 61)
        self.assertEqual(packet["review"]["reviewed_head"], "4f2450ded381945a088d1f0b21c0a2745c172577")
        self.assertEqual(packet["review"]["implementation_merge_commit"], "fa210386378db684419fe6a38b89870dbf72de2d")
        self.assertEqual(packet["blocking_issues"], 0)
        self.assertEqual(packet["disposition"], "RC_G1_PASS_RC_WP2_V0_3_AUTHORISED")
        self.assertTrue(all(check["status"] == "PASS" for check in packet["checks"]))
        self.assertTrue((GATE / "RC_G1_OPERATOR_DECISION.md").is_file())

    def test_three_workspace_context_contract_is_accepted(self) -> None:
        self.assertEqual(WORKSPACES, ("OVERVIEW", "RESEARCH", "SYSTEM"))
        state: dict[str, object] = {}
        initialise_mapping(state, {"source_commit": "fa210386", "read_model_sha256": "fixture-sha"})
        update_context(state, "release_id", "FIXTURE.RELEASE.DEVELOPMENT.v0.3")
        update_context(state, "clock", "15M / 2H_A_L")
        update_context(state, "price_side", "BID")
        update_context(state, "cutoff_mode", "PROSPECTIVE")
        before = context_fingerprint(state["global_context"])
        for workspace in WORKSPACES:
            switch_workspace(state, workspace)
            self.assertEqual(before, context_fingerprint(state["global_context"]))
        self.assertEqual(set(state["global_context"]), set(GLOBAL_CONTEXT_DEFAULTS))

    def test_drawer_selection_is_presentational_only(self) -> None:
        state: dict[str, object] = {}
        initialise_mapping(state)
        before = context_fingerprint(state["global_context"])
        select_object(state, "HEALTH.RESEARCH_RECORDS")
        self.assertTrue(state["drawer_open"])
        self.assertEqual(before, context_fingerprint(state["global_context"]))
        select_object(state, None)
        self.assertFalse(state["drawer_open"])
        self.assertEqual(before, context_fingerprint(state["global_context"]))

    def test_health_truth_and_fixture_conditions_remain_fail_closed(self) -> None:
        expected = {"VALID": "PASS", "EMPTY": "NOT_EVALUATED", "WARN": "WARN", "BLOCK": "BLOCK"}
        for mode, summary_status in expected.items():
            bundle = fixture_bundle(mode)
            self.assertEqual(bundle["summary_status"], summary_status)
            health = {item["object_id"]: item for item in bundle["health"]}
            research = health["HEALTH.RESEARCH_RECORDS"]
            self.assertEqual(research["status"], "NOT_EVALUATED")
            self.assertEqual(research["progress"], 0.0)
        self.assertEqual(normalize_status("UNREGISTERED_STATUS"), "BLOCK")
        self.assertEqual(normalize_status("EXPECTED_EMPTY"), "EXPECTED_EMPTY")

    def test_responsive_contract_is_registered_and_present(self) -> None:
        design = (REG / "RESEARCH_CONSOLE_DESIGN_TOKEN_REGISTRY_v0_3.yaml").read_text(encoding="utf-8")
        css = (ROOT / "apps" / "research_console" / "assets" / "console.css").read_text(encoding="utf-8")
        shell = (ROOT / "apps" / "research_console" / "shell.py").read_text(encoding="utf-8")
        self.assertIn("status: ACCEPTED_BY_RC_G1_V0_3", design)
        self.assertIn("target_widths: [1280, 1440, 1920]", design)
        self.assertIn("narrow_screen_fallback: 1100", design)
        self.assertIn("@media (max-width: 1100px)", css)
        self.assertIn("st.columns([0.32, 4.7, 1.55]", shell)
        self.assertNotIn("st.sidebar", shell)

    def test_authority_registry_advances_only_to_rc_wp2_implementation(self) -> None:
        registry = (REG / "RESEARCH_OPERATIONS_IMPLEMENTATION_REGISTRY_v0_1.yaml").read_text(encoding="utf-8")
        components = (REG / "RESEARCH_CONSOLE_COMPONENT_REGISTRY_v0_3.yaml").read_text(encoding="utf-8")
        self.assertIn("stage: RC_G1_PASS_RC_WP2_V0_3_AUTHORISED", registry)
        self.assertIn("rc_wp1_merge_commit: fa210386378db684419fe6a38b89870dbf72de2d", registry)
        self.assertIn("rc_g1: PASS", registry)
        self.assertIn("rc_wp2_authority: AUTHORISED_IMPLEMENTATION_PENDING_RC_G2", registry)
        self.assertIn("active_live_projection_authority: DENIED_PENDING_RC_G2", registry)
        self.assertIn("live_research_surface_authority: DENIED_PENDING_RC_G3", registry)
        self.assertIn("research_write_authority: DENIED_PENDING_SEPARATE_GATE", registry)
        for token in (
            "repository_mutation: NONE",
            "selector_mutation: NONE",
            "threshold_mutation: NONE",
            "market_authority: NONE",
            "probability_authority: NONE",
            "exposure_authority: NONE",
            "execution_authority: NONE",
            "agent_authority: NONE",
        ):
            self.assertIn(token, registry)
        self.assertIn("status: ACCEPTED_BY_RC_G1_V0_3", components)
        self.assertIn("command_mutation: NONE", components)
        self.assertIn("remote_deployment: DENIED", components)


if __name__ == "__main__":
    unittest.main()
