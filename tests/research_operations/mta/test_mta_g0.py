from __future__ import annotations

import hashlib
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

    def test_gate_retains_operator_pass_and_is_merge_eligible(self) -> None:
        gate = load("docs/releases/market-translation-audit-v0-2/mta-g0/MTA_G0_GATE_PACKET.json")
        state = load("registries/research_operations/mta/OVC_MTA_PROGRAMME_STATE_v0_2.json")
        decision = load("docs/releases/market-translation-audit-v0-2/mta-g0/MTA_G0_OPERATOR_DECISION.json")
        eligibility = load("docs/releases/market-translation-audit-v0-2/mta-g0/MTA_G0_MERGE_ELIGIBILITY.json")
        self.assertEqual(gate["decision"], "PASS")
        self.assertEqual(gate["status"], "APPROVED_PENDING_SQUASH_MERGE")
        self.assertEqual(state["programme_status"], "APPROVED")
        self.assertFalse(state["operator_decision_required"])
        self.assertEqual(state["operator_gate"]["recorded_decision"], "PASS")
        self.assertEqual(decision["operator_command"], "OVC APPROVE MTA-G0 PASS")
        self.assertEqual(eligibility["status"], "ELIGIBLE")
        self.assertEqual(state["packets"][0]["blockers"], [])

    def test_ruleset_blocker_is_reproducibly_resolved(self) -> None:
        blocker = load("docs/releases/market-translation-audit-v0-2/mta-g0/MTA_G0_RULESET_MERGE_BLOCKER.json")
        resolution = load("docs/releases/market-translation-audit-v0-2/mta-g0/MTA_G0_RULESET_MERGE_RESOLUTION.json")
        ruleset_path = ROOT / resolution["resolution_source"]["ruleset_path"]
        ruleset = json.loads(ruleset_path.read_text(encoding="utf-8"))
        digest = hashlib.sha256(ruleset_path.read_bytes()).hexdigest()
        self.assertEqual(blocker["status"], "RESOLVED")
        self.assertEqual(digest, resolution["resolution_source"]["ruleset_sha256"])
        required = next(rule for rule in ruleset["rules"] if rule["type"] == "required_status_checks")
        contexts = [entry["context"] for entry in required["parameters"]["required_status_checks"]]
        self.assertEqual(contexts, ["tests", "OVC tiered test selection shadow"])
        self.assertEqual(ruleset["bypass_actors"], [])
        self.assertEqual(ruleset["current_user_can_bypass"], "never")

    def test_replacement_branch_and_current_pr_base_are_distinguished(self) -> None:
        state = load("registries/research_operations/mta/OVC_MTA_PROGRAMME_STATE_v0_2.json")
        gate = load("docs/releases/market-translation-audit-v0-2/mta-g0/MTA_G0_GATE_PACKET.json")
        resolution = load("docs/releases/market-translation-audit-v0-2/mta-g0/MTA_G0_RULESET_MERGE_RESOLUTION.json")
        eligibility = load("docs/releases/market-translation-audit-v0-2/mta-g0/MTA_G0_MERGE_ELIGIBILITY.json")
        branch_creation_base = "544dc2f6477ce415321f9419a62586fcffa0d02c"
        current_pr_base = "eaefbf55d1702d689d59765558af65e87c0b37fc"
        self.assertEqual(state["branch_creation_base_commit"], branch_creation_base)
        self.assertEqual(gate["branch_creation_base_commit"], branch_creation_base)
        self.assertEqual(eligibility["branch_creation_base_main"], branch_creation_base)
        self.assertEqual(resolution["branch_creation_base_main"], branch_creation_base)
        self.assertEqual(state["baseline_commit"], current_pr_base)
        self.assertEqual(gate["baseline_commit"], current_pr_base)
        self.assertEqual(eligibility["base_main"], current_pr_base)
        self.assertEqual(resolution["current_pull_request_base_main"], current_pr_base)
        self.assertEqual(state["branch"], "gate/mta-g0-ratification-resume")
        self.assertEqual(state["pull_request"], 216)
        self.assertEqual(resolution["base_change_review"]["result"], "PASS")
        self.assertEqual(resolution["base_change_review"]["conflicts"], [])

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
        decision = load("docs/releases/market-translation-audit-v0-2/mta-g0/MTA_G0_OPERATOR_DECISION.json")
        self.assertEqual(state["authority"]["selectors"], "UNCHANGED")
        self.assertEqual(state["authority"]["formula_threshold_reset_clock"], "UNCHANGED")
        self.assertEqual(state["authority"]["c2e_c2_5_c3"], "DENIED")
        self.assertEqual(state["authority"]["validation"], "LOCKED_UNCONSUMED")
        self.assertEqual(state["authority"]["r2"], "DENIED")
        self.assertFalse(decision["downstream_authority_created"])

    def test_schemas_match_ratified_court_records(self) -> None:
        decision_schema = load("schemas/research_operations/mta/mta_g0_operator_decision_v0_1.schema.json")
        state_schema = load("schemas/research_operations/mta/mta_programme_state_v0_2.schema.json")
        self.assertTrue(decision_schema["properties"]["authority_active"]["const"])
        self.assertFalse(decision_schema["properties"]["downstream_authority_created"]["const"])
        self.assertIn("tested_candidate_commit", state_schema["properties"])
        self.assertTrue(decision_schema["additionalProperties"])
        self.assertTrue(state_schema["additionalProperties"])

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
