from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


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

    def test_operator_pass_is_preserved_while_merge_is_blocked(self) -> None:
        gate = load("docs/releases/market-translation-audit-v0-2/mta-g0/MTA_G0_GATE_PACKET.json")
        state = load("registries/research_operations/mta/OVC_MTA_PROGRAMME_STATE_v0_2.json")
        decision = load("docs/releases/market-translation-audit-v0-2/mta-g0/MTA_G0_OPERATOR_DECISION.json")
        blocker = load("docs/releases/market-translation-audit-v0-2/mta-g0/MTA_G0_RULESET_MERGE_BLOCKER.json")
        self.assertEqual(gate["status"], "APPROVED_MERGE_BLOCKED_EXTERNAL_RULESET")
        self.assertEqual(state["programme_status"], "BLOCKED")
        self.assertFalse(state["operator_decision_required"])
        self.assertEqual(state["operator_gate"]["recorded_decision"], "PASS")
        self.assertEqual(decision["operator_command"], "OVC APPROVE MTA-G0 PASS")
        self.assertIn(blocker["blocker_id"], state["packets"][0]["blockers"])

    def test_required_checks_pass_but_external_rule_blocks_merge(self) -> None:
        blocker = load("docs/releases/market-translation-audit-v0-2/mta-g0/MTA_G0_RULESET_MERGE_BLOCKER.json")
        self.assertEqual(blocker["status"], "BLOCKED_EXTERNAL_REPOSITORY_RULESET")
        self.assertTrue(blocker["main_unchanged_at_block"])
        self.assertEqual(blocker["merge_attempt"]["result"], "HTTP_405_REPOSITORY_RULE_VIOLATION")
        self.assertEqual(blocker["merge_attempt"]["message"], "2 of 2 required status checks are expected")
        self.assertEqual(len(blocker["passing_final_head_checks"]), 3)
        self.assertTrue(all(item["result"] == "PASS" for item in blocker["passing_final_head_checks"]))
        self.assertEqual(blocker["review_state"]["unresolved_review_threads"], 0)
        self.assertIn("MERGE_WITH_EXPECTED_CHECKS_UNSATISFIED", blocker["prohibited_resolutions"])

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

    def test_no_activation_or_validation_authority(self) -> None:
        state = load("registries/research_operations/mta/OVC_MTA_PROGRAMME_STATE_v0_2.json")
        decision = load("docs/releases/market-translation-audit-v0-2/mta-g0/MTA_G0_OPERATOR_DECISION.json")
        self.assertEqual(state["authority"]["selectors"], "UNCHANGED")
        self.assertEqual(state["authority"]["c2e_c2_5_c3"], "DENIED")
        self.assertEqual(state["authority"]["validation"], "LOCKED_UNCONSUMED")
        self.assertEqual(state["authority"]["r2"], "DENIED")
        self.assertFalse(decision["downstream_authority_created"])

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
