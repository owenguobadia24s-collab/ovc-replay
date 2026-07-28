from __future__ import annotations

import json
import unittest
from pathlib import Path

from ovc.opt_b.c1 import AUTHORITY_STATE


ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / "docs/releases/opt-b-c1-v2/b1-g5"
GATE = BASE / "B1_G5_GATE_PACKET.json"
COMPARISON = BASE / "B1_G5_COMPARISON_PACKET.json"
HANDOFF = BASE / "B1_G5_C1_TO_C2_HANDOFF_VALIDATION.json"
DECISION = BASE / "B1_G5_OPERATOR_DECISION.md"
SELECTORS = ROOT / "registries/opt_b/c1/C1_ACTIVE_SELECTORS.yaml"
RELEASES = ROOT / "registries/opt_b/c1/C1_RELEASE_REGISTRY.yaml"
AUTHORITY = ROOT / "registries/authority/ACTIVE_AUTHORITY.yaml"
SUCCESSOR_AUTHORITY = ROOT / "registries/authority/C1_TO_C2_ACTIVE_HANDOFF_AUTHORITY.yaml"
CORRECTIVE = ROOT / "docs/releases/opt-b-c1-v2/corrective/c1c-g5/C1C_G4_G5_COORDINATED_SELECTOR_TRANSACTION.json"
CONTRACT = ROOT / "contracts/opt_b/c1/C1_TO_C2_HANDOFF_CONTRACT_v0_1.md"


class B1G5ShadowActivationTests(unittest.TestCase):
    def test_gate_passes_exact_shadow_activation(self) -> None:
        gate = json.loads(GATE.read_text(encoding="utf-8"))
        self.assertEqual(gate["gate_id"], "B1-G5")
        self.assertEqual(
            gate["decision"],
            "PASS_SHADOW_ACTIVATION_EXACT_REMOTE_VERIFIED_RELEASES",
        )
        self.assertEqual(gate["publication_evidence"]["wp5_verification_run_id"], 30190733324)
        self.assertEqual(gate["publication_evidence"]["remote_object_count"], 194)
        self.assertEqual(gate["unexplained_differences"], 0)
        self.assertEqual(gate["blocking_issues"], 0)
        self.assertTrue(gate["selector_transaction"]["atomic"])
        self.assertEqual(gate["selector_transaction"]["rollback_target"], "ALL_C1_ROLE_SELECTORS_NONE")

    def test_exact_historical_release_and_parent_identities_remain_auditable(self) -> None:
        gate = json.loads(GATE.read_text(encoding="utf-8"))
        discovery = gate["releases"]["DISCOVERY"]
        development = gate["releases"]["DEVELOPMENT"]
        self.assertEqual(discovery["selector_state"], "SHADOW")
        self.assertEqual(development["selector_state"], "SHADOW")
        self.assertEqual(
            discovery["manifest_sha256"],
            "6abd6d1fb74e7f3797e9add2435eaa5e487b612efd2f4b5f4f4c59679820d5d2",
        )
        self.assertEqual(
            development["manifest_sha256"],
            "ca83f2d9d948be426f3d80ebc91cc981f92546dfdd07268d71938d618c51f017",
        )
        self.assertEqual(
            discovery["parent_opt_a_manifest_sha256"],
            "0cbcafa9421449574b61bfeec24f634de99cbbbc6e7a53d09ace8f702182ab8c",
        )
        self.assertEqual(
            development["parent_opt_a_manifest_sha256"],
            "25e1be8a7edb0e96017c45bf35f4e788345f94b22a8ed9bb0874c86338ba64cc",
        )

    def test_comparison_is_complete_and_does_not_relabel_history(self) -> None:
        packet = json.loads(COMPARISON.read_text(encoding="utf-8"))
        self.assertEqual(packet["status"], "PASS_COMPLETE_NO_UNEXPLAINED_DIFFERENCES")
        self.assertFalse(packet["historical_relabelling"])
        self.assertFalse(packet["historical_artifacts_mutated"])
        self.assertEqual(packet["unexplained_difference_count"], 0)
        dispositions = {item["disposition"] for item in packet["comparisons"]}
        self.assertIn("EXACT_EQUIVALENCE", dispositions)
        self.assertIn("NOT_COMPARABLE", dispositions)
        self.assertIn("DESCRIPTIVE_QA_ONLY", dispositions)

    def test_historical_c1_to_c2_interface_pass_remains_unchanged(self) -> None:
        packet = json.loads(HANDOFF.read_text(encoding="utf-8"))
        self.assertEqual(packet["status"], "PASS_INTERFACE_VALIDATED_CONSUMPTION_NOT_AUTHORISED")
        self.assertEqual(packet["blocking_issues"], 0)
        self.assertEqual(
            packet["c2_consumption"],
            "DENIED_PENDING_SEPARATE_HANDOFF_REVIEW",
        )
        self.assertEqual(packet["c2_authority"], "NONE")
        self.assertTrue(all(check["status"] == "PASS" for check in packet["checks"]))
        contract = CONTRACT.read_text(encoding="utf-8")
        self.assertIn("One-way dependency law", contract)
        self.assertIn("Shadow selection permits inspection and comparison only", contract)
        self.assertIn("Rollback atomically returns", contract)

    def test_current_selectors_record_historical_or_corrective_lawful_state(self) -> None:
        selectors = SELECTORS.read_text(encoding="utf-8")
        releases = RELEASES.read_text(encoding="utf-8")
        if CORRECTIVE.exists():
            transaction = json.loads(CORRECTIVE.read_text(encoding="utf-8"))
            self.assertTrue(transaction["atomic_on_main_merge"])
            self.assertEqual(selectors.count("selector_state: ACTIVE"), 2)
            self.assertEqual(selectors.count("selector_state: NONE"), 1)
            self.assertIn("OPT-B.C1.GBPUSD.DISCOVERY.2021_2023.v2", selectors)
            self.assertIn("OPT-B.C1.GBPUSD.DEVELOPMENT.2024.v2", selectors)
            self.assertIn("C1.IMPLEMENTATION.v0.2", selectors)
            self.assertIn("ATOMICALLY_RESTORE_EXACT_C1_V1_AND_C2_V1_SELECTOR_IDENTITIES", selectors)
            # Historical release registry remains immutable and continues to prove the
            # original shadow-to-active path; the corrective selector record supersedes it.
            self.assertIn("status: C1_TO_C2_HANDOFF_PASS_C1_ACTIVE_C2_SCOPE_AUTHORISED", releases)
        else:
            self.assertIn("state: SHADOW", selectors)
            self.assertEqual(selectors.count("selector_state: SHADOW"), 2)
            self.assertEqual(selectors.count("selector_state: NONE"), 1)
            self.assertEqual(selectors.count("authority_state: SHADOW"), 2)
            self.assertEqual(selectors.count("c2_consumption: DENIED_PENDING_SEPARATE_HANDOFF_REVIEW"), 3)
            self.assertIn("rollback_action: RETURN_ALL_C1_ROLE_SELECTORS_TO_NONE", selectors)
            self.assertIn("status: B1_G5_PASS_SHADOW_SELECTED_C2_DENIED", releases)
            self.assertEqual(releases.count("authority_state: SHADOW"), 2)
            self.assertEqual(releases.count("active_selector: true"), 2)
            self.assertEqual(releases.count("active_selector: false"), 1)
            self.assertIn("validation_consumption_state: LOCKED_UNCONSUMED", releases)

    def test_repository_authority_has_a_lawful_successor_without_rewriting_history(self) -> None:
        authority = AUTHORITY.read_text(encoding="utf-8")
        self.assertEqual(AUTHORITY_STATE, "B1_G5_SHADOW_SELECTED_C2_DENIED")
        self.assertIn("state: C1_B1_G5_PASS_SHADOW_ACTIVE_C2_DENIED", authority)
        if CORRECTIVE.exists():
            successor = SUCCESSOR_AUTHORITY.read_text(encoding="utf-8")
            self.assertIn("status: PASS_C1_V2_ACTIVE_C2_V2_ACTIVE_DISCOVERY", successor)
            self.assertIn("c2_activation: ACTIVE_DISCOVERY", successor)
            self.assertIn("validation_consumption: LOCKED_UNCONSUMED", successor)
            for forbidden in ("PROBABILITY", "RISK", "EXPOSURE", "TRADING", "EXECUTION", "AGENT_WRITE"):
                self.assertIn(forbidden, successor)
        else:
            self.assertIn("  opt_a: ACTIVE", authority)
            self.assertIn("  opt_b_c1: SHADOW", authority)
            for selector in ("opt_b_c2", "c2e", "c2_5", "c3", "opt_c", "opt_d"):
                self.assertIn(f"  {selector}: NONE", authority)
            self.assertIn("validation_consumption: LOCKED_UNCONSUMED", authority)
            self.assertIn("c2_consumption: DENIED_PENDING_SEPARATE_HANDOFF_REVIEW", authority)
            self.assertIn("probability_authority: NONE", authority)
            self.assertIn("exposure_authority: NONE", authority)
            self.assertIn("trading_authority: NONE", authority)
            self.assertIn("execution_authority: NONE", authority)

    def test_operator_decision_is_explicit_and_rollback_safe(self) -> None:
        decision = DECISION.read_text(encoding="utf-8")
        self.assertIn("PASS — activate the exact remote-verified", decision)
        self.assertIn("returning Discovery and Development to `NONE` atomically", decision)
        self.assertIn("C1_B1_G5_PASS_SHADOW_ACTIVE_C2_DENIED", decision)
        if CORRECTIVE.exists():
            transaction = json.loads(CORRECTIVE.read_text(encoding="utf-8"))
            self.assertEqual(
                transaction["rollback"]["action"],
                "ATOMICALLY_RESTORE_EXACT_C1_V1_AND_C2_V1_SELECTOR_IDENTITIES",
            )
            self.assertTrue(transaction["rollback"]["preserve_v2_releases_immutable_inactive"])


if __name__ == "__main__":
    unittest.main()
