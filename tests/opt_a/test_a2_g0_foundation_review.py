from __future__ import annotations

import json
import unittest
from pathlib import Path

from ovc_evidence_store.external_root import resolve_external_root
from ovc_evidence_store.lifecycle import (
    freeze_release,
    init_workspace,
    validate_publication_approval,
)
from ovc_evidence_store.readiness import publication_readiness


ROOT = Path(__file__).resolve().parents[2]
GOVERNANCE = ROOT / "docs" / "releases" / "opt-a-v2" / "governance"
RELEASES = ROOT / "registries" / "releases"
IMPLEMENTATION = ROOT / "registries" / "implementation"
CONTRACTS = ROOT / "contracts" / "opt_a"
SCHEMAS = ROOT / "schemas" / "opt_a"
FIXTURES = ROOT / "fixtures" / "opt_a" / "wp3"

PROGRAMME = "OVC-OPT-A-V2-IMPLEMENTATION-PLAN-0.2"
MAIN_COMMIT = "087cfe47c2dceffc89d43f2795ebd28dd35d3d3d"
PREDECESSORS = {
    "R0": "a9902c97e21131b1882b4c11ca3a2a79273e7c77",
    "WP1": "5c567c1ba7de57d83079200c006f991d41642310",
    "WP2": "91d57980be84239de69de00c43649d20a2acd7fe",
    "WP3": MAIN_COMMIT,
}
ROLE_IDS = {
    "OPT-A.GBPUSD.DISCOVERY.2021_2023.v2",
    "OPT-A.GBPUSD.DEVELOPMENT.2024.v2",
    "OPT-A.GBPUSD.VALIDATION.2025.v2",
}


class A2G0FoundationReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.wp1 = json.loads((GOVERNANCE / "WP1_GATE_PACKET.json").read_text(encoding="utf-8"))
        cls.wp2 = json.loads((GOVERNANCE / "WP2_GATE_PACKET.json").read_text(encoding="utf-8"))
        cls.wp3 = json.loads((GOVERNANCE / "WP3_GATE_PACKET.json").read_text(encoding="utf-8"))
        cls.g0 = json.loads((GOVERNANCE / "A2_G0_GATE_PACKET.json").read_text(encoding="utf-8"))

    def test_all_predecessor_gate_packets_are_pass(self) -> None:
        for packet in (self.wp1, self.wp2, self.wp3):
            self.assertEqual(PROGRAMME, packet["programme_id"])
            self.assertEqual("PASS", packet["result"])
            self.assertEqual("NONE", packet["market_authority"])

    def test_review_pins_exact_merged_predecessors(self) -> None:
        self.assertEqual(MAIN_COMMIT, self.g0["reviewed_main_commit"])
        for name, commit in PREDECESSORS.items():
            self.assertEqual(commit, self.g0["predecessors"][name]["merge_commit"])
            self.assertEqual("PASS", self.g0["predecessors"][name]["result"])

    def test_gate_checks_are_pass_except_canonical_ci_transition(self) -> None:
        self.assertIn(self.g0["result"], {"PENDING_CI", "PASS"})
        for name, result in self.g0["checks"].items():
            if name == "G0_11_integrated_canonical_ci":
                self.assertIn(result, {"PENDING", "PASS"})
            else:
                self.assertEqual("PASS", result, name)

    def test_programme_scope_is_exact(self) -> None:
        scope = self.g0["programme_scope"]
        self.assertEqual("DUKASCOPY", scope["provider"])
        self.assertEqual("GBPUSD", scope["instrument"])
        self.assertEqual("2021-01-01T00:00:00Z", scope["start_inclusive"])
        self.assertEqual("2026-01-01T00:00:00Z", scope["end_exclusive"])
        self.assertEqual(["M1", "H1"], scope["native_timeframes"])
        self.assertEqual(["BID", "ASK"], scope["price_sides"])
        self.assertEqual("H2_M1_CHAIN_DERIVED_A_L_UTC", scope["primary_operational_spine"])
        self.assertEqual(ROLE_IDS, set(self.g0["role_releases"].values()))

    def test_release_registry_preserves_v1_and_exact_v2_roles(self) -> None:
        registry = (RELEASES / "OPT_A_RELEASE_REGISTRY.yaml").read_text(encoding="utf-8")
        self.assertIn("state: SUPERSEDED", registry)
        self.assertIn("publication_status: NEVER_PUBLISHED", registry)
        self.assertIn("replacement_policy: NEW_BYTES_REQUIRE_NEW_RELEASE_ID", registry)
        for release_id in ROLE_IDS:
            self.assertEqual(1, registry.count(f"release_id: {release_id}"), release_id)

    def test_selectors_and_validation_remain_inactive(self) -> None:
        selectors = (RELEASES / "OPT_A_ACTIVE_SELECTORS.yaml").read_text(encoding="utf-8")
        self.assertIn("state: NONE", selectors)
        self.assertEqual(3, selectors.count("selector_state: NONE"))
        self.assertNotIn("selector_state: ACTIVE", selectors)
        access = (RELEASES / "OPT_A_VALIDATION_ACCESS_REGISTRY.yaml").read_text(encoding="utf-8")
        self.assertIn("consumption_state: LOCKED_UNCONSUMED", access)
        self.assertIn("default_access: DENIED", access)
        self.assertIn("active_approval_id: null", access)

    def test_wp2_lifecycle_controls_are_importable(self) -> None:
        self.assertTrue(callable(resolve_external_root))
        self.assertTrue(callable(init_workspace))
        self.assertTrue(callable(freeze_release))
        self.assertTrue(callable(validate_publication_approval))
        self.assertTrue(callable(publication_readiness))

    def test_wp3_contracts_and_schemas_are_present(self) -> None:
        contract_names = {
            "OPT_A_PROVIDER_INTAKE_AND_SOURCE_OBJECT_CONTRACT_v0_2.md",
            "OPT_A_CLOCK_AGGREGATION_GAP_VOLUME_RECONCILIATION_CONTRACT_v0_2.md",
            "OPT_A_TO_OPT_B_HANDOFF_CONTRACT_v0_2.md",
        }
        for name in contract_names:
            self.assertTrue((CONTRACTS / name).is_file(), name)
        schema_names = {
            "opt_a_provider_intake_record_v0_2.json",
            "opt_a_source_object_identity_v0_2.json",
            "opt_a_observation_bar_v0_2.json",
            "opt_a_reconciliation_record_v0_2.json",
            "opt_a_to_opt_b_handoff_v0_2.json",
        }
        for name in schema_names:
            payload = json.loads((SCHEMAS / name).read_text(encoding="utf-8"))
            self.assertEqual("object", payload["type"], name)
            self.assertFalse(payload["additionalProperties"], name)

    def test_clock_registry_has_exact_parent_counts_and_no_h1_substitution(self) -> None:
        registry = (IMPLEMENTATION / "OPT_A_WP3_CONTRACT_REGISTRY.yaml").read_text(encoding="utf-8")
        for line in (
            "M15_M1_DERIVED: 15",
            "H1_M1_DERIVED: 60",
            "H2_M1_CHAIN_DERIVED: 120",
            "H4_M1_CHAIN_DERIVED: 240",
            "D1_M1_CHAIN_DERIVED: 1440",
            "provider_native_h1_substitution: DENIED",
            "validation_default_access: DENIED",
            "active_handoff: NONE",
        ):
            self.assertIn(line, registry)
        self.assertIn("A: '[00:00,02:00)'", registry)
        self.assertIn("L: '[22:00,00:00_next_day)'", registry)

    def test_contracts_enforce_no_fill_and_one_way_handoff(self) -> None:
        clock = (CONTRACTS / "OPT_A_CLOCK_AGGREGATION_GAP_VOLUME_RECONCILIATION_CONTRACT_v0_2.md").read_text(encoding="utf-8")
        handoff = (CONTRACTS / "OPT_A_TO_OPT_B_HANDOFF_CONTRACT_v0_2.md").read_text(encoding="utf-8")
        for token in (
            "No-fill is absolute",
            "Provider-native H1 may corroborate",
            "may never replace missing M1 rows",
            "H1_PROVIDER_NATIVE",
            "H1_M1_DERIVED",
        ):
            self.assertIn(token, clock)
        self.assertIn("provider objects -> OPT-A role release -> sealed handoff -> OPT-B.C1 -> OPT-B.C2", handoff)
        self.assertIn("consume validation by default", handoff)
        self.assertIn("write corrections back into OPT-A release bytes", handoff)

    def test_wp3_fixtures_are_synthetic_and_non_authoritative(self) -> None:
        fixture = json.loads((FIXTURES / "FIXTURE_MANIFEST.json").read_text(encoding="utf-8"))
        self.assertIs(fixture["synthetic"], True)
        self.assertEqual("NONE", fixture["market_authority"])
        self.assertEqual("DENIED", fixture["release_parent"])
        self.assertEqual("DENIED", fixture["selector_input"])
        self.assertEqual("DENIED", fixture["discovery_seed"])
        self.assertEqual(
            {
                "provider_intake_records": 4,
                "source_object_records": 4,
                "clock_cases": 3,
                "reconciliation_records": 2,
                "handoff_records": 1,
            },
            fixture["case_counts"],
        )

    def test_gate_does_not_overclaim_external_state(self) -> None:
        external = self.g0["external_evaluation_state"]
        self.assertTrue(external)
        self.assertTrue(all(value == "NOT_EVALUATED_BY_GITHUB_RUNNER" for value in external.values()))
        self.assertTrue(self.g0["operator_local_preflight_required"])
        self.assertTrue(self.g0["remote_checks_before_publication"])

    def test_gate_authority_is_bounded_to_next_intake_packet(self) -> None:
        self.assertEqual("NONE", self.g0["market_authority"])
        self.assertIs(self.g0["provider_download_performed"], False)
        self.assertIs(self.g0["market_release_constructed"], False)
        self.assertEqual("NONE", self.g0["r2_mutation"])
        self.assertEqual("NONE", self.g0["selector_activation"])
        self.assertEqual("NONE", self.g0["active_handoff"])
        self.assertEqual("LOCKED_UNCONSUMED", self.g0["validation_consumption"])
        self.assertIn("WP4_PROVIDER_INTAKE_IMPLEMENTATION", self.g0["permitted_after_merge"])
        self.assertIn("OPT_A_SELECTOR_ACTIVATION", self.g0["still_prohibited"])
        self.assertIn("R2_PUBLICATION_WITHOUT_EXACT_APPROVAL_AND_READINESS", self.g0["still_prohibited"])


if __name__ == "__main__":
    unittest.main()
