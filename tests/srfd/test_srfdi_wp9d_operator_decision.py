from __future__ import annotations

import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
DECISION = ROOT / "docs/releases/srfd-benchmark-v0-1/srfdi-wp9d/SRFDI_G9D_FREEZE_OPERATOR_DECISION.json"
STATE = ROOT / "registries/implementation/srfd/OVC_SRFDI_STATE_v0_9_APPROVED_PENDING_MERGE.json"
PREDECISION = ROOT / "registries/implementation/srfd/OVC_SRFDI_STATE_v0_9_CANDIDATE.json"


class SRFDIWP9DOperatorDecisionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.decision = json.loads(DECISION.read_text(encoding="utf-8"))
        self.state = json.loads(STATE.read_text(encoding="utf-8"))
        self.predecision = json.loads(PREDECISION.read_text(encoding="utf-8"))

    def test_operator_command_and_decision_are_exact(self) -> None:
        self.assertEqual(self.decision["gate_id"], "SRFDI-G9D-FREEZE")
        self.assertEqual(self.decision["decision"], "PREREGISTRATION_FREEZE")
        self.assertEqual(
            self.decision["operator_command"],
            "OVC APPROVE SRFDI-G9D-FREEZE PREREGISTRATION_FREEZE",
        )
        self.assertEqual(self.decision["decision_authority"], "OPERATOR")
        self.assertEqual(
            self.decision["approved_candidate"]["predecision_head"],
            "bf2550a88dc154476d2ab83e8b5e47e511836eaa",
        )

    def test_exact_v04_scientific_hashes_are_frozen(self) -> None:
        approved = self.decision["approved_candidate"]
        self.assertEqual(
            approved["v0_4_preregistration_logical_sha256"],
            "f0da6203124a6aeaa83f89e3f27b2fc980754f874ae96e631009dfc9048f2fa3",
        )
        self.assertEqual(
            approved["stability_metric_registry_v0_4_logical_sha256"],
            "371a058e26c05a351a99689ad23b7f844fbc956a6d81449fd237a2f420bf564b",
        )
        self.assertEqual(
            approved["run_manifest_v0_4_candidate_logical_sha256"],
            "70763e69281b3980eebf0ed7a2008c78ef29e5e463a5694110eec5ca027fb529",
        )

    def test_freeze_supersedes_old_authority_without_consumption(self) -> None:
        effect = self.decision["authority_effect"]
        self.assertEqual(effect["june_execution"], "DENIED_PENDING_NEW_EXACT_SRFDI_G_JUNE_AUTH")
        self.assertEqual(effect["prior_v0_3_authority_token"], "SUPERSEDED_UNUSED_UNCONSUMED")
        self.assertEqual(effect["provider_fetch"], "DENIED")
        self.assertEqual(effect["validation_2025"], "LOCKED_UNCONSUMED")
        self.assertEqual(effect["selector_change"], "NONE")
        self.assertEqual(effect["family_promotion"], "NONE")
        self.assertEqual(effect["semantic_promotion"], "NONE")
        self.assertEqual(effect["publication"], "NONE")
        self.assertEqual(effect["probability_risk_exposure_execution"], "NONE")
        self.assertFalse(self.state["exact_bindings"]["v0_3_authority_token_consumed"])

    def test_approved_state_preserves_source_population_and_segmentation(self) -> None:
        bindings = self.state["exact_bindings"]
        self.assertEqual(
            bindings["v0_3_segmentation_registry_logical_sha256"],
            "6c2451fb5b766d2ae25a13a311ba17c8dede342757d607219e62881be4ac31c0",
        )
        self.assertEqual(
            bindings["source_binding_sha256"],
            "4d13c3ee8ae2ad25e30088f4f2de48f8320e3633c2e4ea6a5c2c9a7fdc2a62b7",
        )
        self.assertEqual(
            bindings["population_id"],
            "SRFD.POP.6efa7dd55636d036c12e580e0793abacf8c805bcf6d77bb6e2edf7cffbc113bd",
        )
        self.assertEqual(bindings["eligible_record_count"], 8598)
        self.assertEqual(
            bindings["eligible_record_ids_sha256"],
            "fbb03d1db6cfa91f63330433e835c2bd659d1128b682817083d6f7af9f2aca4e",
        )

    def test_chronological_metric_warning_is_not_refit_claim(self) -> None:
        disposition = self.decision["metric_execution_dispositions"]["CHRONOLOGICAL_STABILITY_WITH_DENOMINATOR"]
        self.assertIn("DESCRIPTIVE", disposition)
        self.assertIn("NOT_REFIT", disposition)
        self.assertTrue(any("must not be represented as independent refit stability" in item for item in self.decision["warnings"]))

    def test_predecision_candidate_is_preserved_not_mutated(self) -> None:
        self.assertEqual(self.predecision["state_role"], "CANDIDATE_NONAUTHORITATIVE_PENDING_OPERATOR_FREEZE")
        self.assertEqual(self.predecision["current_pointer_mutation"], "FORBIDDEN_BEFORE_OPERATOR_FREEZE")
        self.assertEqual(self.predecision["authority"]["v0_3_authority_token"], "UNCONSUMED")


if __name__ == "__main__":
    unittest.main()
