from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

from ovc.opt_b.c1 import AUTHORITY_STATE, FORMULA_COUNT, FORMULA_REGISTRY_ID

ROOT = Path(__file__).resolve().parents[3]
C1_CONTRACTS = ROOT / "contracts" / "opt_b" / "c1"
C1_SCHEMAS = ROOT / "schemas" / "opt_b" / "c1"
C1_REGISTRIES = ROOT / "registries" / "opt_b" / "c1"
C1_FIXTURES = ROOT / "fixtures" / "c1" / "wp2" / "WP2_HANDOFF_FIXTURES.json"
AUTHORITY = ROOT / "registries" / "authority" / "ACTIVE_AUTHORITY.yaml"

FORMULA_FIELDS = (
    "field_name:", "definition:", "formula:", "required_inputs:", "unit:", "domain:",
    "null_rule:", "lookback_bars:", "first_valid_rule:", "symmetry_rule:", "authority:",
)

EXPECTED_SCHEMAS = {
    "c1_bar_primitives_v0_1.schema.json": "ovc.local/schemas/opt_b/c1/c1_bar_primitives_v0_1.schema.json",
    "c1_release_descriptor_v0_1.schema.json": "ovc.local/schemas/opt_b/c1/c1_release_descriptor_v0_1.schema.json",
    "c1_release_manifest_v0_1.schema.json": "ovc.local/schemas/opt_b/c1/c1_release_manifest_v0_1.schema.json",
    "c1_publication_approval_v0_1.schema.json": "ovc.local/schemas/opt_b/c1/c1_publication_approval_v0_1.schema.json",
    "c1_shadow_selector_v0_1.schema.json": "ovc.local/schemas/opt_b/c1/c1_shadow_selector_v0_1.schema.json",
    "c1_supersession_record_v0_1.schema.json": "ovc.local/schemas/opt_b/c1/c1_supersession_record_v0_1.schema.json",
}


class C1WP2ContractTests(unittest.TestCase):
    def test_wp2_design_remains_frozen_after_later_progression(self) -> None:
        self.assertIn(AUTHORITY_STATE, {
            "WP2_CONTRACTS_FROZEN_WP3_SYNTHETIC_ENGINE_AUTHORISED",
            "WP3_REFERENCE_ENGINE_FIXTURE_TRUST_PASS",
            "WP4_REPLAY_QA_PASS_LOCAL_CANDIDATE",
            "B1_G1_CANDIDATE_INVENTORY_ACCEPTED_FREEZE_AUTHORISED",
            "B1_G2_PUBLICATION_READY_WP5_AUTHORISED",
        })
        self.assertEqual(FORMULA_REGISTRY_ID, "C1.FORMULAS.v0.1")
        self.assertEqual(FORMULA_COUNT, 18)
        authority = AUTHORITY.read_text(encoding="utf-8")
        self.assertIn("state: C1_B1_G2_PASS_PUBLICATION_READY_WP5_AUTHORISED_NO_SELECTOR", authority)
        self.assertIn("selector: NONE", authority)
        self.assertIn("fixture_trust: PASS", authority)
        self.assertIn("market_replay: COMPLETE_WP4_PASS", authority)
        self.assertIn("release_freeze: COMPLETE_WP4F_PASS", authority)
        self.assertIn("r2_publication: AUTHORISED_EXACT_RELEASES_ONLY_PENDING_WP5_EXECUTION", authority)
        self.assertIn("validation_consumption: LOCKED_UNCONSUMED", authority)
        self.assertIn("c2_consumption: DENIED_PENDING_SEPARATE_HANDOFF_REVIEW", authority)

    def test_required_contracts_and_registries_exist(self) -> None:
        required = (
            C1_CONTRACTS / "OVC_OPT_B_C1_PRIMITIVE_CONTRACT_v0_1.md",
            C1_CONTRACTS / "C1_NULL_AND_NONCOMPUTABLE_POLICY_v0_1.md",
            C1_CONTRACTS / "C1_RELEASE_LIFECYCLE_CONTRACT_v0_1.md",
            C1_CONTRACTS / "OPT_A_V2_TO_C1_INPUT_PROFILE_v0_1.md",
            C1_REGISTRIES / "C1_FORMULA_REGISTRY_v0_1.yaml",
            C1_REGISTRIES / "C1_QA_CHECK_REGISTRY_v0_1.yaml",
            C1_REGISTRIES / "C1_RELEASE_REGISTRY.yaml",
            C1_REGISTRIES / "C1_ACTIVE_SELECTORS.yaml",
            C1_FIXTURES,
        )
        for path in required:
            self.assertTrue(path.is_file(), path)

    def test_formula_registry_has_18_complete_unique_entries(self) -> None:
        text = (C1_REGISTRIES / "C1_FORMULA_REGISTRY_v0_1.yaml").read_text(encoding="utf-8")
        self.assertIn("registry_id: C1.FORMULAS.v0.1", text)
        self.assertIn("formula_count: 18", text)
        blocks = re.split(r"\n  - primitive_id: ", text.split("formulas:\n", 1)[1].split("\nversioning:", 1)[0])[1:]
        self.assertEqual(len(blocks), 18)
        ids = []
        for block in blocks:
            primitive_id = block.splitlines()[0].strip()
            ids.append(primitive_id)
            for field in FORMULA_FIELDS:
                self.assertIn(field, block, (primitive_id, field))
            self.assertIn("authority: DERIVED_ATOMIC_FACT", block)
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(sum("lookback_bars: 1" in block for block in blocks), 4)
        self.assertEqual(sum("lookback_bars: 0" in block for block in blocks), 14)

    def test_formula_registry_contains_no_semantic_or_outcome_formula(self) -> None:
        text = (C1_REGISTRIES / "C1_FORMULA_REGISTRY_v0_1.yaml").read_text(encoding="utf-8")
        formula_section = text.split("formulas:\n", 1)[1].split("\nversioning:", 1)[0].lower()
        for forbidden in (
            "hammer", "doji", "compression", "displacement", "reclaim", "rejection",
            "future_return", "outcome", "probability", "trade", "overall_state",
        ):
            self.assertNotIn(forbidden, formula_section)

    def test_json_schemas_are_closed_and_parseable(self) -> None:
        for name, expected_id_fragment in EXPECTED_SCHEMAS.items():
            schema = json.loads((C1_SCHEMAS / name).read_text(encoding="utf-8"))
            self.assertEqual(schema["$schema"], "https://json-schema.org/draft/2020-12/schema")
            self.assertIn(expected_id_fragment, schema["$id"])
            self.assertIs(schema["additionalProperties"], False)
            self.assertTrue(schema["required"])

    def test_record_schema_freezes_full_18_field_shape(self) -> None:
        schema = json.loads((C1_SCHEMAS / "c1_bar_primitives_v0_1.schema.json").read_text(encoding="utf-8"))
        measurements = schema["properties"]["measurements"]
        self.assertIs(measurements["additionalProperties"], False)
        self.assertEqual(len(measurements["required"]), 18)
        self.assertEqual(set(measurements["required"]), set(measurements["properties"]))
        self.assertEqual(schema["properties"]["clock"]["enum"], ["15M", "2H_A_L"])
        self.assertEqual(schema["properties"]["price_side"]["enum"], ["BID", "ASK"])
        self.assertNotIn("OPT-A.GBPUSD.2026H1.v1", json.dumps(schema, sort_keys=True))

    def test_null_policy_names_all_required_failure_modes(self) -> None:
        text = (C1_CONTRACTS / "C1_NULL_AND_NONCOMPUTABLE_POLICY_v0_1.md").read_text(encoding="utf-8")
        for reason in (
            "ZERO_RANGE", "NO_PRIOR_BAR", "NO_CONTIGUOUS_PRIOR_BAR", "PRIOR_IDENTITY_MISMATCH",
            "PRIOR_NOT_FIRST_VALID", "PRICE_INCREMENT_UNAVAILABLE", "SOURCE_BAR_INADMISSIBLE",
            "CONTROL_CLOCK_NOT_AUTHORISED", "VALIDATION_LOCKED", "UPSTREAM_IDENTITY_UNRESOLVED",
        ):
            self.assertIn(reason, text)
        self.assertIn("must not search farther backward", text.lower())

    def test_input_profile_preserves_clean_source_and_no_repair(self) -> None:
        text = (C1_CONTRACTS / "OPT_A_V2_TO_C1_INPUT_PROFILE_v0_1.md").read_text(encoding="utf-8")
        for release_id in (
            "OPT-A.GBPUSD.DISCOVERY.2021_2023.v2",
            "OPT-A.GBPUSD.DEVELOPMENT.2024.v2",
            "OPT-A.GBPUSD.VALIDATION.2025.v2",
        ):
            self.assertIn(release_id, text)
        self.assertIn("OPT-A.GBPUSD.2026H1.v1", text)
        self.assertIn("LOCKED_UNCONSUMED", text)
        self.assertIn("H1_PROVIDER_NATIVE", text)
        self.assertIn("No-repair law", text)

    def test_release_candidates_remain_unselected_after_freeze_readiness(self) -> None:
        releases = (C1_REGISTRIES / "C1_RELEASE_REGISTRY.yaml").read_text(encoding="utf-8")
        selectors = (C1_REGISTRIES / "C1_ACTIVE_SELECTORS.yaml").read_text(encoding="utf-8")
        self.assertIn("status: B1_G2_PASS_PUBLICATION_READY", releases)
        self.assertEqual(releases.count("authority_state: CANDIDATE"), 2)
        self.assertIn("authority_state: NONE", releases)
        self.assertEqual(releases.count("active_selector: false"), 3)
        self.assertEqual(releases.count("freeze_state: COMPLETE_WP4F_PASS"), 2)
        self.assertEqual(releases.count("publication_readiness: PASS_B1_G2"), 2)
        self.assertIn("validation_consumption_state: LOCKED_UNCONSUMED", releases)
        self.assertIn("state: NONE", selectors)
        self.assertEqual(selectors.count("selector_state: NONE"), 3)
        self.assertEqual(selectors.count("release_id: null"), 3)
        self.assertIn("initial_activation_role: SHADOW_ONLY", selectors)
        self.assertIn("legacy_opt_b_reactivation: PROHIBITED", selectors)

    def test_wp2_fixtures_cover_valid_null_gap_and_rejection_cases(self) -> None:
        fixtures = json.loads(C1_FIXTURES.read_text(encoding="utf-8"))
        self.assertIs(fixtures["synthetic"], True)
        self.assertEqual(fixtures["market_authority"], "NONE")
        self.assertEqual(fixtures["fixture_count"], 8)
        self.assertEqual(fixtures["fixture_count"], len(fixtures["cases"]))
        ids = [case["case_id"] for case in fixtures["cases"]]
        self.assertEqual(len(ids), len(set(ids)))
        reasons = {case["expected"]["reason"] for case in fixtures["cases"]}
        self.assertTrue({
            None, "NO_PRIOR_BAR", "ZERO_RANGE", "NO_CONTIGUOUS_PRIOR_BAR",
            "UPSTREAM_IDENTITY_UNRESOLVED", "CONTROL_CLOCK_NOT_AUTHORISED",
            "PRIOR_IDENTITY_MISMATCH", "SOURCE_BAR_INADMISSIBLE",
        } <= reasons)
        self.assertEqual(fixtures["base_handoff"]["authority_state"], "NONE")
        self.assertEqual(fixtures["base_handoff"]["selector_state"], "NONE")

    def test_qa_registry_is_blocking_and_non_mutating(self) -> None:
        text = (C1_REGISTRIES / "C1_QA_CHECK_REGISTRY_v0_1.yaml").read_text(encoding="utf-8")
        ids = re.findall(r"check_id: (C1-QA-[A-Z0-9-]+)", text)
        self.assertEqual(len(ids), 20)
        self.assertEqual(len(set(ids)), 10)
        self.assertIn("may_rewrite_market_facts: false", text)
        self.assertIn("may_repair_outputs: false", text)
        self.assertIn("may_suppress_failure: false", text)


if __name__ == "__main__":
    unittest.main()
