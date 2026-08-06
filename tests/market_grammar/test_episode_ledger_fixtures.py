from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "fixtures/market_grammar/wp2/c2e_ledger_cases.json"
RUNNER = ROOT / "scripts/market_grammar/run_mg_wp2_fixture.py"
BOUNDARY = ROOT / "registries/opt_b/market_grammar/MG_C2E_BOUNDARY_POLICY_v0_1.json"
LIFECYCLE = ROOT / "registries/opt_b/market_grammar/MG_C2E_LIFECYCLE_REGISTRY_v0_1.json"
SCHEMAS = ROOT / "schemas/opt_b/market_grammar"


def load(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise AssertionError(f"not object: {path}")
    return value


def load_runner():
    spec = importlib.util.spec_from_file_location("run_mg_wp2_fixture", RUNNER)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class EpisodeLedgerFixtureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.fixture = load(FIXTURE)
        cls.result = load_runner().run(FIXTURE)

    def test_fixture_pack_is_synthetic_and_complete(self) -> None:
        self.assertEqual("SYNTHETIC_NON_AUTHORITATIVE", self.fixture["authority"])
        self.assertEqual("MG-C2E-BOUNDARY-v0.1", self.fixture["policy_id"])
        self.assertEqual(4, len(self.fixture["valid_cases"]))
        self.assertEqual(5, len(self.fixture["invalid_cases"]))
        ids = [item["case_id"] for group in ("valid_cases", "invalid_cases") for item in self.fixture[group]]
        self.assertEqual(len(ids), len(set(ids)))

    def test_valid_results_match_frozen_expectations(self) -> None:
        by_id = {item["case_id"]: item for item in self.result["valid_results"]}
        for case in self.fixture["valid_cases"]:
            actual = by_id[case["case_id"]]
            for key, expected in case["expected"].items():
                self.assertEqual(expected, actual[key], f"{case['case_id']}:{key}")
            self.assertRegex(actual["ledger_id"], r"^C2E\.LD\.[0-9a-f]{64}$")

    def test_invalid_results_fail_for_expected_reason(self) -> None:
        by_id = {item["case_id"]: item for item in self.result["invalid_results"]}
        for case in self.fixture["invalid_cases"]:
            self.assertIn(case["expected_error"], by_id[case["case_id"]]["error"])

    def test_runner_is_logically_deterministic(self) -> None:
        runner = load_runner()
        self.assertEqual(runner.run(FIXTURE), runner.run(FIXTURE))

    def test_registries_and_schemas_freeze_exact_vocabulary(self) -> None:
        boundary = load(BOUNDARY)
        lifecycle = load(LIFECYCLE)
        self.assertTrue(boundary["threshold_free"])
        self.assertFalse(boundary["canonical"])
        self.assertEqual(list(range(1, 8)), [item["ordinal"] for item in boundary["ordered_rules"]])
        self.assertEqual("CONFLICT", lifecycle["ambiguity_state"])
        required = {
            "c2e_binding_v0_1.schema.json",
            "c2e_episode_record_v0_1.schema.json",
            "c2e_ledger_v0_1.schema.json",
            "c2e_phase_record_v0_1.schema.json",
        }
        self.assertEqual(required, {path.name for path in SCHEMAS.glob("c2e*_v0_1.schema.json")})
        for path in sorted(SCHEMAS.glob("c2e*_v0_1.schema.json")):
            schema = load(path)
            self.assertFalse(schema["additionalProperties"])
            self.assertEqual("https://json-schema.org/draft/2020-12/schema", schema["$schema"])


if __name__ == "__main__":
    unittest.main()
