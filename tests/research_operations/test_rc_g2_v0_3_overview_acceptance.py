from __future__ import annotations

import json
import unittest
from pathlib import Path

from ovc.research_operations.console_overview import (
    HEALTH_DOMAIN_ORDER,
    OverviewProjectionBuilder,
    normalize_health_status,
)
from ovc.research_operations.console_overview_candidate import load_read_model


ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "fixtures" / "research_operations" / "research_console_v0_3" / "RC_WP2_OVERVIEW_SOURCE_READ_MODEL.json"
PACKET = ROOT / "docs" / "releases" / "research-console-v0-3" / "rc-g2" / "RC_G2_GATE_PACKET.json"
OVERVIEW_REGISTRY = ROOT / "registries" / "research_operations" / "RESEARCH_CONSOLE_OVERVIEW_PROJECTION_REGISTRY_v0_3.yaml"
IMPLEMENTATION_REGISTRY = ROOT / "registries" / "research_operations" / "RESEARCH_OPERATIONS_IMPLEMENTATION_REGISTRY_v0_1.yaml"
HOME = ROOT / "apps" / "research_console" / "Home.py"
SHELL = ROOT / "apps" / "research_console" / "shell.py"


class RCG2V03OverviewAcceptanceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.model = load_read_model(FIXTURE)
        self.builder = OverviewProjectionBuilder()
        self.projection = self.builder.build(self.model)

    def test_projection_is_deterministic_and_source_bound(self) -> None:
        repeated = self.builder.build(self.model)
        self.assertEqual(self.projection.to_dict(), repeated.to_dict())
        self.assertEqual(self.projection.logical_sha256, repeated.logical_sha256)
        self.assertEqual(self.projection.source_commit, self.model.source_commit)
        self.assertEqual(self.projection.read_model_sha256, self.model.logical_sha256)
        self.assertIn(f"read-model:{self.model.logical_sha256}", self.projection.source_refs)

    def test_required_health_domains_and_truth_rules_are_accepted(self) -> None:
        self.assertEqual(tuple(item.domain for item in self.projection.health_domains), HEALTH_DOMAIN_ORDER)
        domains = {item.domain: item for item in self.projection.health_domains}
        research = domains["RESEARCH_RECORDS"]
        self.assertEqual(research.status, "NOT_EVALUATED")
        self.assertEqual(research.progress, 0.0)
        self.assertNotEqual(self.projection.summary_status, "PASS")
        self.assertEqual(normalize_health_status("UNREGISTERED_STATUS"), "BLOCK")

    def test_domain_consequence_and_sources_remain_visible(self) -> None:
        for domain in self.projection.health_domains:
            self.assertTrue(domain.detail)
            self.assertTrue(domain.consequence)
            self.assertTrue(domain.affected_surfaces)
        for row in (*self.projection.releases, *self.projection.gates, *self.projection.sessions):
            self.assertIn("source_refs", row)

    def test_gate_packet_and_authority_are_exact(self) -> None:
        packet = json.loads(PACKET.read_text(encoding="utf-8"))
        self.assertEqual(packet["gate_id"], "RC-G2-v0.3")
        self.assertEqual(packet["review"]["implementation_pull_request"], 63)
        self.assertEqual(packet["review"]["implementation_merge_commit"], "6701ec00469898b12f17b294610d839d4082d94b")
        self.assertEqual(packet["decision"], "PASS_OVERVIEW_AND_AMBIENT_HEALTH_CONTRACT_ACCEPTED")
        self.assertEqual(packet["disposition"], "RC_G2_PASS_RC_WP3_V0_3_AUTHORISED")
        self.assertEqual(packet["blocking_issues"], 0)
        self.assertTrue(all(check["status"] == "PASS" for check in packet["checks"]))
        self.assertFalse(packet["activation_boundary"]["automatic_activation_by_gate_files"])
        self.assertTrue(packet["activation_boundary"]["research_workspace_remains_fixture_only"])

    def test_registries_record_bounded_overview_acceptance(self) -> None:
        overview = OVERVIEW_REGISTRY.read_text(encoding="utf-8")
        implementation = IMPLEMENTATION_REGISTRY.read_text(encoding="utf-8")
        self.assertIn("status: ACCEPTED_BY_RC_G2_V0_3", overview)
        self.assertIn("active_live_projection: APPROVED_OVERVIEW_ONLY_BOUNDED_LOCAL_READ_ONLY", overview)
        self.assertIn("automatic_activation_by_gate_record: false", overview)
        self.assertIn("stage: RC_G2_PASS_RC_WP3_V0_3_AUTHORISED", implementation)
        self.assertIn("rc_wp2_merge_commit: 6701ec00469898b12f17b294610d839d4082d94b", implementation)
        self.assertIn("active_live_projection_authority: APPROVED_OVERVIEW_ONLY_BOUNDED_LOCAL_READ_ONLY", implementation)
        self.assertIn("live_research_surface_authority: DENIED_PENDING_RC_G3", implementation)
        self.assertIn("research_write_authority: DENIED_PENDING_SEPARATE_GATE", implementation)

    def test_gate_does_not_silently_wire_runtime_or_expand_authority(self) -> None:
        home = HOME.read_text(encoding="utf-8")
        shell = SHELL.read_text(encoding="utf-8")
        self.assertNotIn("overview_candidate.json", home)
        self.assertNotIn("console_overview_candidate", shell)
        self.assertNotIn("repository_mutation\": \"WRITE", shell)
        self.assertNotIn("market_classification\": \"ACTIVE", shell)


if __name__ == "__main__":
    unittest.main()
