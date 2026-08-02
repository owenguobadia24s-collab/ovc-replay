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

    def test_gate_is_operator_approved_pending_merge(self) -> None:
        gate = load("docs/releases/market-translation-audit-v0-2/mta-g0/MTA_G0_GATE_PACKET.json")
        state = load("registries/research_operations/mta/OVC_MTA_PROGRAMME_STATE_v0_2.json")
        decision = load("docs/releases/market-translation-audit-v0-2/mta-g0/MTA_G0_OPERATOR_DECISION.json")
        self.assertEqual(gate["status"], "APPROVED_PENDING_SQUASH_MERGE")
        self.assertFalse(state["operator_decision_required"])
        self.assertEqual(state["operator_gate"]["recorded_decision"], "PASS")
        self.assertEqual(decision["operator_command"], "OVC APPROVE MTA-G0 PASS")
        self.assertEqual(state["packets"][0]["blockers"], [])

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
