from __future__ import annotations

import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
PACKET = ROOT / "docs/releases/srfd-benchmark-v0-1/srfdi-g10a/SRFDI_G10A_OPERATOR_PACKET.json"
QA = ROOT / "docs/releases/srfd-benchmark-v0-1/srfdi-g10a/SRFDI_G10A_QA_PACKET.json"
PREP = ROOT / "docs/releases/srfd-benchmark-v0-1/srfdi-g10a/SRFDI_WP10A_PREPARATION_RECORD.json"
DECISION = ROOT / "docs/releases/srfd-benchmark-v0-1/srfdi-g10a/SRFDI_G10A_OPERATOR_DECISION.json"
STATE = ROOT / "registries/implementation/srfd/OVC_SRFDI_STATE_v0_14_SUPERSESSION_GATE_READY_CANDIDATE.json"
POST_DECISION = ROOT / "registries/implementation/srfd/OVC_SRFDI_STATE_v0_15.json"
PREREG = ROOT / "registries/research/srfd/SRFD_PREREGISTRATION_CANDIDATE_v0_2.json"
CONTRACT = ROOT / "contracts/opt_b/srfd/SRFDI_WP10A_REAL_DATA_FAMILY_GRID_CAPACITY_REMEDIATION_SUPERSESSION_CONTRACT_v0_1.md"


class SRFDIG10ACapacitySupersessionGateReadyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.packet = json.loads(PACKET.read_text())
        cls.qa = json.loads(QA.read_text())
        cls.prep = json.loads(PREP.read_text())
        cls.decision = json.loads(DECISION.read_text())
        cls.state = json.loads(STATE.read_text())
        cls.post_decision = json.loads(POST_DECISION.read_text())
        cls.prereg = json.loads(PREREG.read_text())
        cls.contract = CONTRACT.read_text()

    def test_operator_gate_is_required_and_recommends_supersede(self) -> None:
        self.assertEqual("SRFDI-G10A", self.packet["gate_id"])
        self.assertEqual("OPERATOR_REQUIRED", self.packet["gate_class"])
        self.assertEqual("GATE_READY", self.packet["status"])
        self.assertEqual("SUPERSEDE", self.packet["recommended_decision"])
        self.assertEqual(
            ["SUPERSEDE", "DEFER", "BLOCK", "QUARANTINE"],
            self.packet["allowed_decisions"],
        )
        self.assertEqual(
            "OVC APPROVE SRFDI-G10A SUPERSEDE",
            self.packet["exact_operator_command"],
        )

    def test_preparation_divergence_is_immutable_and_operator_decision_is_recorded(self) -> None:
        divergence = self.packet["court_record_divergence"]
        self.assertEqual(
            "EXPLICIT_UNRESOLVED_UNTIL_OPERATOR_SUPERSESSION",
            divergence["status"],
        )
        self.assertEqual(433, divergence["blocker_evidence_pr"])
        self.assertTrue(self.packet["current_authority"]["blocker_pr_433_token_consumed"])
        self.assertFalse(self.packet["current_authority"]["main_pointer_token_consumed"])
        self.assertFalse(self.prep["current_state_pointer_changed"])

        self.assertEqual("SUPERSEDE", self.decision["decision"])
        self.assertEqual("OPERATOR", self.decision["decision_authority"])
        self.assertEqual("APPROVED", self.post_decision["status"])
        self.assertTrue(self.post_decision["exact_bindings"]["authority_token_consumed"])
        self.assertEqual("SRFDI-WP10A", self.post_decision["active_packet"])

    def test_capacity_blocker_and_consumed_token_are_pinned(self) -> None:
        blocker = self.packet["triggering_blocker"]
        self.assertEqual(
            "CAPACITY_UNRESOLVED_REAL_DATA_FULL_GRID",
            blocker["reason_code"],
        )
        self.assertEqual(
            "f9bbeba065cf85f5a5f5c0a88e9c9d0ea6fa96d7",
            blocker["evidence_head"],
        )
        self.assertEqual(
            "SRFD.G8R.CAP.FAIL.9b1a873009b004205d74d38010f8a00cd64d04e9ed2384e3233e871d91586121",
            blocker["capacity_failure_id"],
        )
        self.assertEqual(
            "SRFD.JUNE.AUTH.52bcae6e0b748a0c49d578b3b2b529f16754438793cbd261670d91ed0d2a5686",
            blocker["token_id"],
        )
        self.assertEqual("CONSUMED_NOT_REUSABLE", blocker["token_state_on_blocker"])

    def test_exact_1944_family_grid_is_reconstructed_from_frozen_ladders(self) -> None:
        bounds = self.prereg["configuration_bounds"]
        ladders = bounds["family_parameter_ladders"]
        support = len(ladders["shared_minimum_support"])
        medoid = len(ladders["medoid_star_radius"]) * support
        complete = len(ladders["complete_linkage_radius"]) * support
        average = len(ladders["average_linkage_radius"]) * support
        pam = (
            len(ladders["bounded_pam_k"])
            * len(ladders["bounded_pam_max_assignment_distance"])
            * len(ladders["bounded_pam_max_iterations"])
            * support
        )
        per_domain = medoid + complete + average + pam
        self.assertEqual(54, per_domain)
        self.assertEqual(36, self.packet["frozen_scientific_bindings"]["comparability_domain_count"])
        self.assertEqual(
            1944,
            per_domain * self.packet["frozen_scientific_bindings"]["comparability_domain_count"],
        )
        self.assertEqual(
            1944,
            self.packet["frozen_scientific_bindings"]["family_configuration_count"],
        )

    def test_supersession_scope_is_implementation_only_and_fresh_run_denied(self) -> None:
        delta = self.packet["proposed_authority_delta_if_SUPERSEDE"]
        self.assertEqual(
            "WP10-v0.4 EXECUTION IMPLEMENTATION ROUTE ONLY",
            delta["supersession_scope"],
        )
        self.assertEqual("UNCHANGED_V0_4", delta["scientific_preregistration"])
        self.assertEqual("SRFDI-WP10A", delta["authorize_packet"])
        self.assertEqual(
            "REAL_DATA_FAMILY_GRID_CAPACITY_REMEDIATION_ONLY",
            delta["mode"],
        )
        self.assertEqual("SRFDI-G10A-FREEZE", delta["next_operator_gate"])
        self.assertEqual(
            "REQUIRES_SEPARATE_NEW_SRFDI-G-JUNE-AUTH",
            delta["fresh_scientific_run_after_freeze"],
        )
        self.assertEqual(
            "DENIED",
            self.state["proposed_state_after_OPERATOR_SUPERSEDE"]["fresh_june_scientific_run"],
        )

    def test_all_frozen_configuration_identities_remain_required(self) -> None:
        conditions = self.packet["acceptance_conditions_for_SRFDI_WP10A"]
        self.assertTrue(
            any("1,944 frozen family configuration identities" in item for item in conditions)
        )
        prohibited = self.packet["proposed_authority_delta_if_SUPERSEDE"]["prohibited_work"]
        self.assertTrue(any("Drop, sample, approximate" in item for item in prohibited))
        self.assertIn("all 1,944 frozen family configuration instances", self.contract)

    def test_firewalls_and_preparation_authority_are_unchanged(self) -> None:
        self.assertEqual("NONE", self.prep["authority_effect"])
        self.assertFalse(self.prep["market_data_read_by_preparation"])
        self.assertFalse(self.prep["provider_fetch"])
        self.assertFalse(self.prep["validation_2025_read"])
        self.assertFalse(self.prep["implementation_code_changed"])
        self.assertFalse(self.prep["scientific_contract_changed"])
        authority = self.state["authority"]
        self.assertTrue(authority["wp10a_execution"].startswith("DENIED_PENDING"))
        self.assertEqual("DENIED", authority["provider_fetch"])
        self.assertEqual("LOCKED_UNCONSUMED", authority["validation_2025"])
        self.assertEqual("NONE", authority["scientific_promotion"])
        self.assertEqual("NONE", authority["probability_risk_exposure_execution"])

    def test_qa_is_pass_for_operator_review_not_self_approval(self) -> None:
        self.assertEqual(
            "PASS_FOR_OPERATOR_REVIEW_WITH_EXPLICIT_COURT_RECORD_DIVERGENCE",
            self.qa["qa_result"],
        )
        self.assertTrue(self.qa["operator_review_required"])
        self.assertEqual("NONE", self.qa["authority_effect_of_preparation"])
        self.assertEqual("SUPERSEDE", self.qa["recommended_decision"])
        self.assertEqual("SRFDI-G10A-FREEZE", self.qa["required_next_stop_if_approved"])


if __name__ == "__main__":
    unittest.main()
