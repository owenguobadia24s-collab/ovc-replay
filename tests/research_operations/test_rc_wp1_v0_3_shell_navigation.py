from __future__ import annotations

import json
import py_compile
import unittest
from pathlib import Path

from apps.research_console.components import normalize_status
from apps.research_console.fixtures import fixture_bundle, object_index, search_objects
from apps.research_console.state import (
    GLOBAL_CONTEXT_DEFAULTS,
    SYSTEM_SECTIONS,
    WORKSPACES,
    build_global_context,
    context_fingerprint,
    initialise_mapping,
    select_object,
    switch_workspace,
    update_context,
)

ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "apps" / "research_console"
REG = ROOT / "registries" / "research_operations"
PACKET = ROOT / "docs" / "releases" / "research-console-v0-3" / "rc-wp1" / "RC_WP1_IMPLEMENTATION_PACKET.json"


class RCWP1V03ShellNavigationTests(unittest.TestCase):
    def test_exact_three_workspace_shell_and_system_sections(self) -> None:
        self.assertEqual(WORKSPACES, ("OVERVIEW", "RESEARCH", "SYSTEM"))
        self.assertEqual(len(WORKSPACES), 3)
        self.assertEqual(
            SYSTEM_SECTIONS,
            ("HEALTH", "LINEAGE", "CATALOGUE", "RELEASES", "QA_GATES", "AUDIT", "CONFIGURATION", "ABOUT"),
        )

    def test_workspace_switch_preserves_global_context(self) -> None:
        state: dict[str, object] = {}
        initialise_mapping(state, {"source_commit": "abc123", "read_model_sha256": "def456"})
        update_context(state, "release_id", "FIXTURE.RELEASE.X")
        update_context(state, "cutoff_mode", "PROSPECTIVE")
        before = context_fingerprint(state["global_context"])
        switch_workspace(state, "RESEARCH")
        switch_workspace(state, "SYSTEM")
        self.assertEqual(before, context_fingerprint(state["global_context"]))
        self.assertEqual(state["active_workspace"], "SYSTEM")
        with self.assertRaises(ValueError):
            switch_workspace(state, "FOURTH_WORKSPACE")

    def test_context_update_is_allowlisted_and_selection_is_presentational(self) -> None:
        state: dict[str, object] = {}
        initialise_mapping(state)
        self.assertEqual(set(state["global_context"]), set(GLOBAL_CONTEXT_DEFAULTS))
        select_object(state, "GATE.RC_A1")
        self.assertEqual(state["selected_object_id"], "GATE.RC_A1")
        self.assertTrue(state["drawer_open"])
        select_object(state, None)
        self.assertFalse(state["drawer_open"])
        with self.assertRaises(ValueError):
            update_context(state, "threshold", 0.5)

    def test_fixture_pack_covers_valid_empty_warn_and_block(self) -> None:
        for mode in ("VALID", "EMPTY", "WARN", "BLOCK"):
            bundle = fixture_bundle(mode)
            self.assertEqual(bundle["fixture_mode"], mode)
            self.assertEqual(len(bundle["health"]), 6)
        self.assertEqual(fixture_bundle("VALID")["summary_status"], "PASS")
        self.assertEqual(fixture_bundle("EMPTY")["summary_status"], "NOT_EVALUATED")
        self.assertEqual(fixture_bundle("WARN")["summary_status"], "WARN")
        self.assertEqual(fixture_bundle("BLOCK")["summary_status"], "BLOCK")

    def test_health_truth_preserves_not_evaluated_empty_bar(self) -> None:
        for mode in ("VALID", "EMPTY", "WARN", "BLOCK"):
            health = {item["object_id"]: item for item in fixture_bundle(mode)["health"]}
            research = health["HEALTH.RESEARCH_RECORDS"]
            self.assertEqual(research["status"], "NOT_EVALUATED")
            self.assertEqual(research["progress"], 0.0)
        self.assertNotEqual(fixture_bundle("EMPTY")["summary_status"], "PASS")
        self.assertEqual(normalize_status("UNKNOWN_NEW_STATUS"), "BLOCK")
        self.assertEqual(normalize_status("EXPECTED_EMPTY"), "EXPECTED_EMPTY")

    def test_drawer_and_command_search_resolve_registered_fixture_objects(self) -> None:
        bundle = fixture_bundle("VALID")
        index = object_index(bundle)
        self.assertIn("GATE.RC_A1", index)
        self.assertIn("HEALTH.RESEARCH_RECORDS", index)
        matches = search_objects(bundle, "contradiction")
        self.assertEqual([item["object_id"] for item in matches], ["EVIDENCE.CONTRADICTION.001"])
        self.assertEqual(search_objects(bundle, "deploy"), [])

    def test_shell_sources_compile_without_importing_live_projection_dependencies(self) -> None:
        for relative in ("Home.py", "state.py", "fixtures.py", "theme.py", "components.py", "shell.py"):
            py_compile.compile(str(APP / relative), doraise=True)
        home = (APP / "Home.py").read_text(encoding="utf-8")
        shell = (APP / "shell.py").read_text(encoding="utf-8")
        self.assertNotIn("ReadModelNode", home)
        self.assertNotIn("model.nodes", home)
        self.assertIn("FIXTURE_ONLY_LOCAL", shell)
        self.assertIn("LOCAL · NO DEPLOY", shell)
        self.assertIn("PROSPECTIVE", shell)
        self.assertNotIn("st.sidebar", shell)

    def test_component_and_design_registries_preserve_authority(self) -> None:
        components = (REG / "RESEARCH_CONSOLE_COMPONENT_REGISTRY_v0_3.yaml").read_text(encoding="utf-8")
        design = (REG / "RESEARCH_CONSOLE_DESIGN_TOKEN_REGISTRY_v0_3.yaml").read_text(encoding="utf-8")
        for token in ("APP_SHELL", "ICON_RAIL", "CONTEXTUAL_DETAIL_DRAWER", "COMMAND_PALETTE", "AMBIENT_HEALTH", "ACTIVITY_STREAM"):
            self.assertIn(f"id: {token}", components)
        self.assertIn("command_mutation: NONE", components)
        self.assertIn("remote_deployment: DENIED", components)
        self.assertIn("no_signal_is_pass: false", design)
        self.assertIn("research_records_status", json.dumps(json.loads((ROOT / "fixtures" / "research_operations" / "research_console_v0_3" / "RC_WP1_SHELL_FIXTURES.json").read_text(encoding="utf-8"))))

    def test_work_package_packet_is_complete_and_gate_ready(self) -> None:
        packet = json.loads(PACKET.read_text(encoding="utf-8"))
        self.assertEqual(packet["work_package"], "RC-WP1-v0.3")
        self.assertEqual(packet["baseline_commit"], "f93a84e9bfdf36b28ba79f84da8163c3ae4e3b10")
        self.assertEqual(packet["authority"], "FIXTURE_ONLY_LOCAL_PRESENTATION")
        self.assertEqual(packet["disposition"], "COMPLETE_RC_G1_V0_3_REVIEW_READY")
        self.assertEqual(packet["blocking_issues"], 0)
        self.assertTrue(all(check["status"] == "PASS" for check in packet["checks"]))
        denied = packet["denied_authority"]
        for key in ("live_projection", "live_research_surface", "research_write", "repository_mutation", "selector_mutation", "threshold_mutation", "market", "probability", "exposure", "execution", "agent", "remote_deployment"):
            self.assertIn(key, denied)


if __name__ == "__main__":
    unittest.main()
