from __future__ import annotations

import hashlib
import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BLOCKER_ID = "MTA-G0-BLOCK-002-CHECKS-PASS-RULESET-STILL-EXPECTED"


def load(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


class MTAG0Tests(unittest.TestCase):
    def test_validator_passes(self) -> None:
        path = ROOT / "scripts/research_operations/validate_mta_g0.py"
        spec = importlib.util.spec_from_file_location("validate_mta_g0", path)
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.assertEqual(module.main(), 0)

    def test_operator_pass_and_merge_receipt_are_preserved(self) -> None:
        state = load("registries/research_operations/mta/OVC_MTA_PROGRAMME_STATE_v0_2.json")
        decision = load("docs/releases/market-translation-audit-v0-2/mta-g0/MTA_G0_OPERATOR_DECISION.json")
        receipt = load("docs/releases/market-translation-audit-v0-2/mta-g0/MTA_G0_MERGE_RECEIPT.json")
        packet0 = next(item for item in state["packets"] if item["packet_id"] == "MTA-00")
        self.assertEqual(decision["operator_command"], "OVC APPROVE MTA-G0 PASS")
        self.assertFalse(decision["downstream_authority_created"])
        self.assertEqual(receipt["decision"], "COMPLETED")
        self.assertEqual(receipt["merge_commit"], "eacf7a71e6242ee9adf5206b5e21e7ed66e1d85d")
        self.assertEqual(packet0["status"], "COMPLETED")
        self.assertEqual(packet0["merge_commit"], receipt["merge_commit"])
        self.assertEqual(packet0["blockers"], [])
        self.assertNotEqual(state["current_packet"], "MTA-00")

    def test_historical_blocker_is_retained_without_remaining_current(self) -> None:
        blocker = load("docs/releases/market-translation-audit-v0-2/mta-g0/MTA_G0_REQUIRED_CHECK_ENFORCEMENT_BLOCKER.json")
        state = load("registries/research_operations/mta/OVC_MTA_PROGRAMME_STATE_v0_2.json")
        self.assertEqual(blocker["blocker_id"], BLOCKER_ID)
        self.assertEqual(blocker["status"], "BLOCKED_EXTERNAL_REPOSITORY_RULESET_ENFORCEMENT")
        self.assertEqual(len(blocker["passing_assurance"]), 2)
        self.assertNotEqual(state["programme_status"], "BLOCKED")
        packet0 = next(item for item in state["packets"] if item["packet_id"] == "MTA-00")
        self.assertNotIn(BLOCKER_ID, packet0["blockers"])

    def test_final_required_checks_and_squash_merge(self) -> None:
        receipt = load("docs/releases/market-translation-audit-v0-2/mta-g0/MTA_G0_MERGE_RECEIPT.json")
        self.assertEqual(receipt["transport_history"]["final_pull_request"], 219)
        self.assertEqual(receipt["transport_history"]["final_head_sha"], "da6e33f67a5b978e57c3ff99e35b29335823115f")
        self.assertEqual(receipt["merge_method"], "SQUASH")
        self.assertEqual([item["context"] for item in receipt["required_checks"]], [
            "tests",
            "OVC tiered test selection shadow",
            "Market Translation Audit MTA-G0 gate readiness",
        ])
        self.assertTrue(all(item["result"] == "PASS" for item in receipt["required_checks"]))

    def test_ruleset_bytes_and_contexts_remain_reproducible(self) -> None:
        blocker = load("docs/releases/market-translation-audit-v0-2/mta-g0/MTA_G0_REQUIRED_CHECK_ENFORCEMENT_BLOCKER.json")
        ruleset_path = ROOT / "docs/releases/development-acceleration-v0-1/da-wp4b/main-ruleset.json"
        ruleset = json.loads(ruleset_path.read_text(encoding="utf-8"))
        digest = hashlib.sha256(ruleset_path.read_bytes()).hexdigest()
        self.assertEqual(digest, blocker["ruleset"]["sha256"])
        required = next(rule for rule in ruleset["rules"] if rule["type"] == "required_status_checks")
        contexts = [entry["context"] for entry in required["parameters"]["required_status_checks"]]
        self.assertEqual(contexts, ["tests", "OVC tiered test selection shadow"])
        self.assertEqual(ruleset["bypass_actors"], [])
        self.assertEqual(ruleset["current_user_can_bypass"], "never")

    def test_capacity_is_bounded_and_recoverable(self) -> None:
        fixture = load("fixtures/research_operations/mta/MTA_G0_CAPACITY_FIXTURES_v0_1.json")
        self.assertEqual(fixture["valid"]["max_runtime_s"], 4 * 60 * 60)
        self.assertEqual(fixture["valid"]["max_retained_bytes"], 10 * 1024**3)
        self.assertEqual(len(fixture["recovery"]), 7)

    def test_exact_three_cluster_variants(self) -> None:
        text = (ROOT / "registries/research_operations/mta/OVC_MTA_CLUSTER_VARIANT_PROFILE_v0_1.yaml").read_text(encoding="utf-8")
        self.assertEqual(text.count("  - id:"), 3)
        self.assertIn("PRIMARY_OVERLAP_PLUS_1", text)
        self.assertIn("authority: AUTHORITATIVE_FOR_MTA_G6_FINAL_POPULATION_AND_G8", text)
        self.assertIn("parameter_search: PROHIBITED", text)

    def test_no_activation_or_validation_authority(self) -> None:
        state = load("registries/research_operations/mta/OVC_MTA_PROGRAMME_STATE_v0_2.json")
        self.assertEqual(state["authority"]["selectors"], "UNCHANGED")
        self.assertEqual(state["authority"]["formula_threshold_reset_clock"], "UNCHANGED")
        self.assertEqual(state["authority"]["c2e_c2_5_c3"], "DENIED")
        self.assertEqual(state["authority"]["validation"], "LOCKED_UNCONSUMED")
        self.assertEqual(state["authority"]["r2"], "DENIED")

    def test_ro4_and_mta_are_separate(self) -> None:
        text = (ROOT / "contracts/research_operations/mta/OVC_MTA_RO4_INTEGRATION_CONTRACT_v0_1.md").read_text(encoding="utf-8")
        self.assertIn("separate analytical objects", text)
        self.assertIn("No RO4 sequence candidate may be promoted through MTA", text)
        self.assertIn("CROSS_PROGRAMME_INCONSISTENCY", text)

    def test_june_review_is_deferred_without_outcome(self) -> None:
        decision = load("docs/releases/market-translation-audit-v0-2/mta-g0/PD_JUNE_FM_G2_DISPOSITION_DECISION.json")
        self.assertEqual(decision["decision"], "DEFER")
        self.assertEqual(decision["review_outcome"], "NONE")
        self.assertEqual(decision["pull_request_202_disposition"], "PRESERVE_OPEN_UNMERGED")
        self.assertIn("WHOLESALE_MERGE_PR_202", decision["prohibited"])


if __name__ == "__main__":
    unittest.main()
