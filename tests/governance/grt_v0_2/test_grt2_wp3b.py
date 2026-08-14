from __future__ import annotations

import json
import unittest
from pathlib import Path

from ovc.programme_genesis.grt_v0_2.bootstrap import validate_instance
from ovc.programme_genesis.grt_v0_2.bindings import build_governance_binding_registry, resolve_claims, validate_partition_proposal

ROOT = Path(__file__).resolve().parents[3]
FIXTURE = ROOT / "fixtures/governance/grt_v0_2/wp3b/governance_binding_fixture.json"
SCHEMA = ROOT / "schemas/governance/grt_v0_2/governance_binding_registry.schema.json"


class GRT2WP3BBindingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))

    def test_owner_evidence_resolves_without_path_inference(self) -> None:
        result = resolve_claims(self.fixture["owner_claims"], binding_kind="PROGRAMME_OWNER")
        self.assertEqual(result["status"], "RESOLVED")
        self.assertEqual(result["value"], "OVC-EXAMPLE")
        self.assertEqual(result["authority_effect"], "NONE_GOVERNANCE_PROJECTION")

    def test_same_precedence_owner_conflict_is_not_selected(self) -> None:
        result = resolve_claims(self.fixture["conflicting_owner_claims"], binding_kind="PROGRAMME_OWNER")
        self.assertEqual(result["status"], "CONFLICTING")
        self.assertIsNone(result["value"])
        self.assertIn("OPERATOR_REQUIRED", result["reason_codes"])

    def test_provisional_genesis_cannot_satisfy_native_crosswalk(self) -> None:
        provisional = resolve_claims(self.fixture["provisional_genesis"], binding_kind="GENESIS_CROSSWALK")
        native = resolve_claims(self.fixture["native_genesis"], binding_kind="GENESIS_CROSSWALK")
        self.assertEqual(provisional["status"], "PGN_AUTHORITY_REQUIRED_CURRENT")
        self.assertIsNone(provisional["value"])
        self.assertEqual(native["status"], "RESOLVED")
        self.assertEqual(native["value"], "PGN.EXAMPLE")

    def test_partition_is_reviewable_but_not_materialized(self) -> None:
        result = validate_partition_proposal(self.fixture["partition"])
        self.assertEqual(result["status"], "REVIEWABLE")
        self.assertFalse(result["materialization_allowed"])
        disputed = dict(self.fixture["partition"])
        disputed["objections"] = [{"owner":"OVC-OTHER","reason":"boundary"}]
        blocked = validate_partition_proposal(disputed)
        self.assertEqual(blocked["status"], "OPERATOR_REQUIRED")
        self.assertFalse(blocked["materialization_allowed"])

    def test_registry_projection_is_deterministic_non_authoritative_and_schema_valid(self) -> None:
        entries = [
            {"registry_section":"programme_bindings","artifact_id":"OVC.EXAMPLE.A","programme_id":"OVC-EXAMPLE"},
            {"registry_section":"genesis_crosswalks","artifact_id":"OVC.EXAMPLE.A","genesis_id":"PGN.EXAMPLE"},
        ]
        a = build_governance_binding_registry(entries)
        b = build_governance_binding_registry(list(reversed(entries)))
        self.assertEqual(a, b)
        self.assertEqual(a["active_enforcement"], "NONE")
        validate_instance(a, json.loads(SCHEMA.read_text(encoding="utf-8")))


if __name__ == "__main__":
    unittest.main()
