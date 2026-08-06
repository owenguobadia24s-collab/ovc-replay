from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/market_grammar/validate_mg_wp0_baseline.py"
BASE = ROOT / "docs/releases/c2e-c2g-c2p-market-grammar-v0-1/mg-wp0"
STATE = ROOT / "registries/opt_b/market_grammar/OVC_MARKET_GRAMMAR_PROGRAMME_STATE_v0_1.jsonc"


def load(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise AssertionError(f"not object: {path}")
    return value


def load_module():
    spec = importlib.util.spec_from_file_location("validate_mg_wp0_baseline", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class MarketGrammarWp0Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.module = load_module()
        cls.result = cls.module.validate()
        cls.binding = load(BASE / "MG_WP0_BASELINE_BINDING.json")
        cls.inventory = load(BASE / "MG_WP0_EXTERNAL_ARTIFACT_INVENTORY.json")
        cls.qa = load(BASE / "MG_WP0_QA_PACKET.json")
        cls.decision = load(BASE / "MG_WP0_DELEGATED_DECISION.json")
        cls.assurance = load(BASE / "MG_WP0_PREDECISION_ASSURANCE_RECEIPT.json")
        cls.state = load(STATE)

    def test_baseline_validator_passes_exact_bindings(self) -> None:
        self.assertEqual("PASS", self.result["status"])
        self.assertEqual(
            "93f56d278d4c35cf2a338a9f3dc7d6ed9e668d69",
            self.result["baseline_main"],
        )
        self.assertEqual(8, self.result["repository_artifact_count"])
        self.assertEqual(4, self.result["external_object_count"])
        self.assertEqual(33320, self.result["requested"])
        self.assertEqual(
            "3f1089e3a4eefe94147c8c2f912e77899e4ed21fe8b3b8b85993e47bf7151ee7",
            self.result["logical_population_sha256"],
        )
        self.assertEqual(
            "150de1997be8801baa59db6d0fe98b11cb21a6b70525b908537aeb31bfd00cc3",
            self.result["integrated_package_sha256"],
        )

    def test_repository_artifact_modes_are_explicit(self) -> None:
        modes = {item["mode"] for item in self.binding["exact_repository_artifacts"]}
        self.assertEqual(
            {"IMMUTABLE_INPUT", "BASELINE_OBSERVATION_SUPERSEDED_BY_PACKET_STATE"},
            modes,
        )
        immutable = [
            item for item in self.binding["exact_repository_artifacts"]
            if item["mode"] == "IMMUTABLE_INPUT"
        ]
        self.assertEqual(7, len(immutable))
        self.assertEqual([], self.binding["open_pull_request_observation"]["conflicting_mg_prs"])

    def test_external_inventory_is_complete_and_read_only(self) -> None:
        self.assertEqual("READ_ONLY_HASH_LOCK", self.inventory["authority"])
        self.assertEqual(4, len(self.inventory["external_objects"]))
        self.assertEqual(3, len(self.inventory["run_manifests"]))
        self.assertEqual(33320, self.inventory["counts"]["requested"])
        self.assertEqual(
            33320,
            self.inventory["counts"]["computable"]
            + self.inventory["counts"]["censored"]
            + self.inventory["counts"]["not_evaluable"],
        )
        self.assertEqual("PASS", self.inventory["capacity"]["status"])

    def test_delegated_pass_is_non_reserved_and_assured(self) -> None:
        self.assertEqual("PASS", self.decision["decision"])
        self.assertTrue(self.decision["delegated_authority"])
        self.assertFalse(self.decision["operator_required"])
        self.assertEqual("NONE_BASELINE_BINDING_ONLY", self.decision["authority_delta"])
        self.assertEqual(
            "ceff73f13185aa9e2dc95acf1d71ccb5a28ae78f",
            self.decision["predecision_assured_head"],
        )
        self.assertEqual("PASS", self.assurance["result"])
        for value in self.assurance["checks"].values():
            if isinstance(value, dict):
                self.assertEqual("SUCCESS", value["conclusion"])
        self.assertEqual(0, self.assurance["checks"]["unresolved_review_threads"])

    def test_qa_has_no_blocker_and_is_pending_only_final_head(self) -> None:
        self.assertEqual("PASS_PENDING_FINAL_HEAD", self.qa["status"])
        self.assertEqual([], self.qa["blockers"])
        self.assertEqual("NONE_BASELINE_BINDING_ONLY", self.qa["authority_delta"])
        self.assertEqual(
            "PASS_DELEGATED_PENDING_FINAL_DECISION_HEAD_ASSURANCE_AND_MERGE",
            self.qa["qa_recommendation"],
        )
        self.assertEqual("PASS_ZERO", self.qa["checks"]["outcome_and_validation_dependencies"])

    def test_programme_state_approves_only_wp0_pending_receipt(self) -> None:
        self.assertEqual("APPROVED", self.state["status"])
        self.assertEqual("MG-WP0-MERGE-RECEIPT", self.state["next_packet"])
        self.assertEqual("SATISFIED_DELEGATED_DECISION", self.state["authority_required"])
        self.assertEqual([], self.state["blockers"])
        self.assertIsNone(self.state["merge_commit"])
        packets = {item["packet_id"]: item for item in self.state["packets"]}
        self.assertEqual("COMPLETED", packets["MG-D0-D8"]["status"])
        self.assertEqual("APPROVED", packets["MG-WP0"]["status"])
        for index in range(1, 11):
            self.assertEqual("PLANNED", packets[f"MG-WP{index}"]["status"])
        self.assertEqual("OPERATOR_REQUIRED", packets["MG-WP10"]["authority_required"])


if __name__ == "__main__":
    unittest.main()
