import json
from pathlib import Path
import unittest

from ovc.opt_b.c2e_v2.legacy import run_legacy_fixture_conformance
from ovc.opt_b.c2e_v2.remap import build_legacy_remap

ROOT = Path(__file__).resolve().parents[4]
FIXTURE = ROOT / "fixtures/market_grammar/wp2/c2e_ledger_cases.json"
RO_STATE = ROOT / "registries/research_operations/c2e/OVC_C2E_PROGRAMME_STATE_v0_1.json"
REGISTRY = ROOT / "registries/opt_b/c2e/v0_2/C2E_LEGACY_CONFORMANCE_REGISTRY_v0_1.json"


class C2E2WP4LegacyConformanceTests(unittest.TestCase):
    def test_historical_market_grammar_fixtures_reproduce_exact_expectations(self) -> None:
        fixture = json.loads(FIXTURE.read_text())
        receipt = run_legacy_fixture_conformance()
        self.assertTrue(receipt["comparison_only"])
        self.assertFalse(receipt["runtime_selectable_by_c2e2"])
        actual = {item["case_id"]: item for item in receipt["valid_results"]}
        for case in fixture["valid_cases"]:
            for key, expected in case["expected"].items():
                self.assertEqual(actual[case["case_id"]][key], expected, f"{case['case_id']}:{key}")
            self.assertTrue(all(item.startswith("C2E.EP.") for item in actual[case["case_id"]]["episode_ids"]))
            self.assertTrue(actual[case["case_id"]]["ledger_id"].startswith("C2E.LD."))
        invalid = {item["case_id"]: item["error"] for item in receipt["invalid_results"]}
        for case in fixture["invalid_cases"]:
            self.assertIn(case["expected_error"], invalid[case["case_id"]])
        self.assertEqual(receipt, run_legacy_fixture_conformance())
        self.assertEqual(9, len(receipt["artifact_sha256"]))
        self.assertTrue(all(len(value) == 64 for value in receipt["artifact_sha256"].values()))

    def test_research_operations_block_is_immutable(self) -> None:
        state = json.loads(RO_STATE.read_text())
        self.assertEqual(state["programme_id"], "OVC-C2E-NEUTRAL-EPISODE-v0.1")
        self.assertEqual(state["status"], "BLOCKED")
        self.assertEqual(state["current_gate"], "C2E-G1")
        self.assertEqual(state["next_action"], "STOP_UNTIL_NEW_IMMUTABLE_OPERATOR_SUPERSESSION")

    def test_legacy_registry_deprecates_runtime_without_rewriting_history(self) -> None:
        registry = json.loads(REGISTRY.read_text())
        mg = registry["market_grammar_v0_1"]
        self.assertEqual(mg["disposition"], "PRESERVE_HISTORICAL_COMPARISON_ONLY")
        self.assertFalse(mg["runtime_selectable_by_c2e2"])
        self.assertFalse(registry["active"])
        self.assertFalse(registry["canonical"])

    def test_remap_is_comparison_only_and_preserves_distinct_namespaces(self) -> None:
        receipt = run_legacy_fixture_conformance()
        legacy_id = receipt["valid_results"][0]["episode_ids"][0]
        record = build_legacy_remap(
            legacy_episode_ids=[legacy_id],
            v2_episode_ids=["C2E.EPISODE.aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"],
            to_boundary_pack_id="C2E.BOUNDARY.PACK.synthetic",
            mapping_type="ONE_TO_ONE",
            first_valid_time="2026-06-22T12:00:00Z",
        )
        self.assertTrue(record["comparison_only"])
        self.assertEqual(record["authority"], "COMPARISON_ONLY")
        self.assertEqual(record["from_episode_ids"], [legacy_id])
        self.assertNotEqual(record["from_episode_ids"][0], record["to_episode_ids"][0])

    def test_legacy_id_cannot_be_relabelled_as_v2(self) -> None:
        with self.assertRaisesRegex(ValueError, "LEGACY_ID_RELABEL_AS_V2_DENIED"):
            build_legacy_remap(
                legacy_episode_ids=["C2E.EP." + "a" * 64],
                v2_episode_ids=["C2E.EP." + "b" * 64],
                to_boundary_pack_id="PACK.V2",
                mapping_type="ONE_TO_ONE",
                first_valid_time="2026-06-22T12:00:00Z",
            )


if __name__ == "__main__":
    unittest.main()
