from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
CONTRACT = ROOT / "contracts/opt_b/c2/C2_PARENT_CONTEXT_RESOLVER_CONTRACT_vNext.md"
LINK_SCHEMA = ROOT / "schemas/opt_b/c2/vnext/c2_parent_context_link.schema.json"
BUNDLE_SCHEMA = ROOT / "schemas/opt_b/c2/vnext/c2_parent_context_bundle.schema.json"
REGISTRY = ROOT / "registries/opt_b/c2/vnext/C2_PARENT_CONTEXT_RESOLVER_REGISTRY_v1.jsonc"
FIXTURES = ROOT / "fixtures/opt_b/c2/vnext/parent_context_resolver_cases_v1.json"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class ParentContextContractTests(unittest.TestCase):
    def test_contract_freezes_typed_bundle_expected_slot_and_no_fallback(self) -> None:
        text = CONTRACT.read_text(encoding="utf-8")
        self.assertIn("typed bundle", text)
        self.assertIn("resolve that exact expected slot before applying completeness filters", text)
        self.assertIn("shall not carry an older observed parent forward", text)
        self.assertIn("MULTIPLE_ELIGIBLE_NO_GOVERNED_SELECTION", text)
        self.assertIn("reserved for CEAR-G9", text)
        self.assertIn("SHADOW_FROZEN_READ_ONLY", text)

    def test_schemas_are_closed_and_preserve_null_fallback(self) -> None:
        link = load(LINK_SCHEMA)
        bundle = load(BUNDLE_SCHEMA)
        self.assertFalse(link["additionalProperties"])
        self.assertFalse(bundle["additionalProperties"])
        self.assertEqual("null", link["properties"]["fallback_id"]["type"])
        self.assertEqual("null", bundle["properties"]["fallback_parent_id"]["type"])
        self.assertEqual(False, link["properties"]["active"]["const"])
        self.assertEqual(False, bundle["properties"]["canonical"]["const"])
        self.assertEqual("SHADOW_FROZEN_READ_ONLY", bundle["properties"]["authority"]["const"])

    def test_registry_has_one_inactive_resolver_and_no_threshold(self) -> None:
        registry = load(REGISTRY)
        self.assertEqual("SHADOW_FROZEN_READ_ONLY", registry["status"])
        self.assertFalse(registry["active"])
        self.assertFalse(registry["canonical"])
        self.assertEqual("C2.PARENT.CONTEXT.RESOLVER.v1", registry["resolver"]["resolver_id"])
        self.assertEqual("BEFORE_COMPLETENESS_FILTERING", registry["resolver"]["expected_slot_resolution"])
        self.assertFalse(registry["resolver"]["older_parent_fallback"])
        self.assertIsNone(registry["selection"]["fallback_id"])
        self.assertIsNone(registry["universal_staleness_threshold"])
        self.assertEqual("NONE", registry["episode_authority"])
        self.assertEqual("NONE", registry["consumer_denominator_authority"])

    def test_fixture_pack_is_synthetic_complete_and_non_authoritative(self) -> None:
        fixtures = load(FIXTURES)
        self.assertTrue(fixtures["synthetic"])
        self.assertFalse(fixtures["authoritative_market_data"])
        self.assertFalse(fixtures["active"])
        self.assertFalse(fixtures["canonical"])
        ids = [item["case_id"] for item in fixtures["cases"]]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(7, len(ids))
        self.assertIn("WP8.MISSING_EXPECTED_WITH_OLDER_AVAILABLE", ids)
        self.assertIn("WP8.MULTIPLE_STRUCTURAL_OBJECTS", ids)
        self.assertIn("WP8.EPISODE_SEPARATION", ids)

    def test_explicit_denials_preserve_active_and_downstream_boundaries(self) -> None:
        denied = set(load(REGISTRY)["explicitly_not_granted"])
        required = {
            "ACTIVE_OR_CANONICAL_PARENT_SELECTION",
            "NUMERIC_STALENESS_FRESHNESS_THRESHOLD",
            "SEMANTIC_EVENT_OR_EPISODE_PROMOTION",
            "C2E_OR_C2_5_ACTIVATION",
            "CONSUMER_DENOMINATOR_OR_OVERLAP_POLICY",
            "RULE_OR_THEORY_PROMOTION",
            "CANONICAL_OR_R2_PUBLICATION",
            "VALIDATION_CONSUMPTION",
            "ACTIVE_C2_SELECTOR_OR_RELEASE_CHANGE",
            "PROBABILITY_RISK_EXPOSURE_TRADING_EXECUTION",
            "AGENT_WRITE_AUTHORITY",
        }
        self.assertTrue(required.issubset(denied))


if __name__ == "__main__":
    unittest.main()
