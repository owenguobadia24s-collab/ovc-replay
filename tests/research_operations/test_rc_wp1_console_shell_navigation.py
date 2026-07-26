from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

from apps.research_console.fixtures import FIXTURE_MODES, fixture_for_route
from apps.research_console.navigation import GROUP_ORDER, ROUTES, route_ids
from apps.research_console.shell import AUTHORITY_BOUNDARY
from apps.research_console.theme import DESIGN_TOKENS, load_css_text

ROOT = Path(__file__).resolve().parents[2]


class RCWP1ConsoleShellNavigationTests(unittest.TestCase):
    def test_frozen_route_registry_matches_shell_navigation(self) -> None:
        registry = (
            ROOT
            / "registries/research_operations/RESEARCH_CONSOLE_ROUTE_REGISTRY_v0_2.yaml"
        ).read_text(encoding="utf-8")
        registered = tuple(re.findall(r"^\s*- route_id: ([A-Z0-9_]+)$", registry, re.MULTILINE))
        self.assertEqual(registered, route_ids())
        self.assertEqual(GROUP_ORDER, ("HOME", "RESEARCH", "SYSTEM", "SETTINGS"))
        self.assertEqual(len(ROUTES), 14)

    def test_every_route_has_valid_empty_warn_and_block_fixture(self) -> None:
        for route in ROUTES:
            for mode in FIXTURE_MODES:
                with self.subTest(route=route.route_id, mode=mode):
                    fixture = fixture_for_route(route.route_id, mode)
                    self.assertEqual(fixture["route_id"], route.route_id)
                    self.assertEqual(fixture["fixture_mode"], mode)
                    self.assertEqual(fixture["authority"], route.authority)
                    self.assertTrue(fixture["source_refs"])
                    if mode in {"EMPTY", "BLOCK"}:
                        empty = fixture["empty_state"]
                        self.assertTrue(empty["reason"])
                        self.assertTrue(empty["consequence"])
                        self.assertTrue(empty["next_action"])
                        self.assertNotEqual(empty["status"], "PASS")

    def test_authority_boundary_remains_local_and_non_mutating(self) -> None:
        self.assertEqual(AUTHORITY_BOUNDARY["mode"], "READ_ONLY")
        self.assertEqual(AUTHORITY_BOUNDARY["deployment"], "LOCAL_ONLY")
        for field in (
            "repository_mutation",
            "selector_mutation",
            "threshold_mutation",
            "market_classification",
            "probability",
            "exposure",
            "execution",
            "agent",
        ):
            self.assertEqual(AUTHORITY_BOUNDARY[field], "NONE", field)

    def test_design_tokens_and_stylesheet_are_complete(self) -> None:
        for token in (
            "background",
            "panel",
            "panel_border",
            "primary_text",
            "muted_text",
            "blue",
            "green",
            "amber",
            "red",
            "purple",
            "cyan",
        ):
            self.assertIn(token, DESIGN_TOKENS)
        css = load_css_text()
        for selector in (
            ".ovc-context-bar",
            ".ovc-authority-strip",
            ".ovc-card",
            ".ovc-empty-state",
            ".ovc-local-badge",
        ):
            self.assertIn(selector, css)
        self.assertNotIn("Deploy", css)

    def test_home_uses_shell_and_does_not_build_live_v02_projections(self) -> None:
        home = (ROOT / "apps/research_console/Home.py").read_text(encoding="utf-8")
        self.assertIn("render_navigation", home)
        self.assertIn("render_active_route", home)
        self.assertIn("RC-WP1 route contents remain fixtures", home)
        self.assertNotIn("st.dataframe(list(model.health)", home)
        self.assertNotIn("selector_mutation", home)
        self.assertNotIn("threshold_mutation", home)

    def test_rc_wp1_packet_and_v03_deferral_are_recorded(self) -> None:
        packet_path = (
            ROOT
            / "docs/releases/research-console-v0-2/rc-wp1/RC_WP1_IMPLEMENTATION_PACKET.json"
        )
        deferral_path = (
            ROOT
            / "docs/releases/research-console-v0-2/rc-wp1/OVC_RESEARCH_CONSOLE_V0_3_DEFERRAL.md"
        )
        self.assertTrue(packet_path.is_file())
        self.assertTrue(deferral_path.is_file())
        packet = json.loads(packet_path.read_text(encoding="utf-8"))
        self.assertEqual(packet["disposition"], "COMPLETE_RC_G1_REVIEW_READY")
        self.assertEqual(packet["authority_delta"], "FIXTURE_ONLY_LOCAL_PRESENTATION")
        self.assertEqual(packet["v0_3_plan"], "DEFERRED_NOT_ADOPTED")
        self.assertEqual(packet["route_count"], 14)

    def test_implementation_registry_preserves_rc_g0_and_records_wp1(self) -> None:
        registry = (
            ROOT
            / "registries/research_operations/RESEARCH_OPERATIONS_IMPLEMENTATION_REGISTRY_v0_1.yaml"
        ).read_text(encoding="utf-8")
        self.assertIn("stage: RC_G0_PASS_RC_WP1_AUTHORISED", registry)
        self.assertIn("rc_wp1_stage: COMPLETE_RC_G1_REVIEW_READY", registry)
        self.assertIn("v0_3_plan: DEFERRED_NOT_ADOPTED", registry)
        self.assertIn("rc_g1: PENDING_OPERATOR_REVIEW", registry)


if __name__ == "__main__":
    unittest.main()
