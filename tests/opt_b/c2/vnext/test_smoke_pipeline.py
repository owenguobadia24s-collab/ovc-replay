from __future__ import annotations

import json
import unittest
from pathlib import Path

from ovc.opt_b.c2_vnext.smoke_pipeline import run_canonical_smoke

ROOT = Path(__file__).resolve().parents[4]
FIXTURE_PATH = ROOT / "fixtures/opt_b/c2/vnext/c2ar_wp5_5_canonical_smoke_v0_1.json"
SCHEMA_PATH = ROOT / "schemas/opt_b/c2/vnext/C2AR_WP5_5_SMOKE_MANIFEST_v0_1.schema.json"
CONTRACT_PATH = ROOT / "contracts/opt_b/c2/anatomy_redesign/C2AR_WP5_5_SYNTHETIC_PIPELINE_TOPOLOGY_CONTRACT_v0_1.md"


class SyntheticPipelineSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))

    def test_pipeline_runs_deterministically_twice(self) -> None:
        first = run_canonical_smoke(self.fixture)
        second = run_canonical_smoke(json.loads(json.dumps(self.fixture)))
        self.assertEqual(first, second)
        self.assertEqual(first["manifest_sha256"], second["manifest_sha256"])
        self.assertEqual("PASS", first["status"])
        self.assertRegex(first["manifest_sha256"], r"^[0-9a-f]{64}$")

    def test_all_five_stages_are_present_and_interface_counts_match(self) -> None:
        manifest = run_canonical_smoke(self.fixture)
        self.assertEqual({"observation", "horizon", "level", "container", "relation"}, set(manifest["stages"]))
        expected = self.fixture["expected"]
        self.assertEqual(expected["observation_count"], manifest["stages"]["observation"]["count"])
        self.assertEqual(expected["trailing_horizon_members"], manifest["stages"]["horizon"]["member_count"])
        self.assertEqual(expected["level_count"], len(manifest["stages"]["level"]["level_ids"]))
        self.assertEqual(expected["container_count"], len(manifest["stages"]["container"]["container_ids"]))
        self.assertEqual(expected["relation_scope_count"], len(manifest["stages"]["relation"]["relation_set_ids"]))
        for stage in manifest["stages"].values():
            self.assertRegex(stage["sha256"], r"^[0-9a-f]{64}$")

    def test_chronology_ambiguity_censorship_and_exclusion_are_explicit(self) -> None:
        manifest = run_canonical_smoke(self.fixture)
        chronology = manifest["chronology"]
        self.assertTrue(chronology["all_level_first_valid_by_current"])
        self.assertTrue(chronology["all_container_first_valid_by_current"])
        self.assertFalse(chronology["horizon_has_future_member"])
        evidence = manifest["ambiguity_and_exclusion"]
        self.assertGreaterEqual(evidence["level_selector_tie_count"], 1)
        self.assertIsNone(evidence["level_selector_selected"])
        self.assertGreaterEqual(evidence["explicit_relation_exclusion_count"], 1)
        self.assertGreaterEqual(evidence["censored_candidate_count"], 1)

    def test_smoke_grants_no_authority_and_uses_no_market_data(self) -> None:
        manifest = run_canonical_smoke(self.fixture)
        self.assertTrue(all(value == "NONE" for value in manifest["authority"].values()))
        self.assertFalse(manifest["raw_market_data"])
        self.assertEqual("NONE", manifest["r2_write_authority"])
        self.assertEqual(
            {"OPT_A_C1_EVIDENCE_ADAPTER", "LEVEL_POINTER_SELECTOR", "CONTAINER_ROLE_PROJECTION"},
            set(manifest["mocked_components"]),
        )

    def test_repository_contract_schema_and_fixture_close_the_smoke_boundary(self) -> None:
        contract = CONTRACT_PATH.read_text(encoding="utf-8")
        self.assertIn("observation → horizon → level → container → relation", contract)
        self.assertIn("Any missing stage, nondeterministic hash, future member", contract)
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        self.assertFalse(schema["additionalProperties"])
        self.assertEqual("C2AR.SMOKE.CANONICAL.v1", schema["properties"]["fixture_id"]["const"])
        self.assertEqual("PASS", schema["properties"]["status"]["const"])
        self.assertFalse(self.fixture["market_data"])
        self.assertTrue(self.fixture["fixture_only"])
        active = (ROOT / "registries/opt_b/c2/C2_ACTIVE_SELECTORS.yaml").read_text(encoding="utf-8")
        self.assertIn("SELECTOR.OPT-B.C2.GBPUSD.v2", active)
        self.assertIn("LOCKED_UNCONSUMED", active)


if __name__ == "__main__":
    unittest.main()
