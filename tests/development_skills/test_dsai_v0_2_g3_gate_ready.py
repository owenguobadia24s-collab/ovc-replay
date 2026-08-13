from __future__ import annotations

import json
import unittest
from pathlib import Path

from ovc.development.skills.orch345 import resolve_orch345_authority


ROOT = Path(__file__).resolve().parents[2]
RELEASE = ROOT / "docs/releases/development-skills-architecture-v0-2"
STATE_ROOT = ROOT / "registries/implementation/dsai_v0_2"


class DsaiV02G3GateReadyTests(unittest.TestCase):
    def _load(self, path: Path) -> dict:
        return json.loads(path.read_text(encoding="utf-8"))

    def test_g2_merge_receipt_is_exact_and_non_authorising(self) -> None:
        receipt = self._load(RELEASE / "dsai2-wp2/DSAI2_G2_SQUASH_MERGE_RECEIPT.json")
        self.assertEqual(receipt["pull_request"], 688)
        self.assertEqual(receipt["baseline_main"], "788dd4ea04b8df53f51369de84fff348de7c61d9")
        self.assertEqual(receipt["approved_head"], "93bd46715c50ffc725f8b4ea89765a699b5ea026")
        self.assertEqual(receipt["result_main_sha"], "28ef05024d3bd12d9917eecc17e3b5dece4a2613")
        self.assertEqual(receipt["authority_delta"], "NONE")
        self.assertEqual(receipt["authority_after_merge"]["ORCH-3"], "INACTIVE_SHADOW_ONLY")
        self.assertEqual(receipt["authority_after_merge"]["ORCH-4"], "INACTIVE_SHADOW_ONLY")
        self.assertEqual(receipt["authority_after_merge"]["ORCH-5"], "INACTIVE_SHADOW_ONLY")
        self.assertFalse(receipt["authority_after_merge"]["parallel_merge"])

    def test_g3_gate_packet_is_operator_required_and_does_not_activate(self) -> None:
        packet = self._load(RELEASE / "dsai2-g3/DSAI2_G3_GATE_PACKET.json")
        pending = self._load(RELEASE / "dsai2-g3/DSAI2_G3_DECISION_PENDING.json")

        self.assertEqual(packet["gate_id"], "DSAI2-G3")
        self.assertEqual(packet["gate_class"], "OPERATOR_REQUIRED")
        self.assertEqual(packet["recommended_decision"], "PASS")
        self.assertEqual(packet["operator_decision"], "PENDING")
        self.assertFalse(packet["activation_performed"])
        self.assertEqual(packet["proposed_authority_delta"]["packet_class_allowlist"], ["LOW_RISK_IMPLEMENTATION"])
        self.assertFalse(packet["proposed_authority_delta"]["parallel_merge"])
        self.assertEqual(packet["proposed_authority_delta"]["integration_policy"], "PDC_SERIAL_FINAL_INTEGRATION_WINDOW_REQUIRED")
        self.assertEqual(packet["proposed_authority_delta"]["operator_required_gate_behavior"], "STOP")
        self.assertEqual(packet["proposed_authority_delta"]["validation"], "DENIED")

        self.assertEqual(pending["status"], "PENDING_OPERATOR")
        self.assertIsNone(pending["decision"])
        self.assertFalse(pending["activation_performed"])

    def test_activation_readiness_and_gate_qa_are_bounded_and_empirically_supported(self) -> None:
        readiness = self._load(RELEASE / "dsai2-g3/DSAI2_G3_ACTIVATION_READINESS.json")
        qa = self._load(RELEASE / "dsai2-g3/DSAI2_G3_QA_PACKET.json")
        self.assertEqual(readiness["status"], "GATE_READY_OPERATOR_REQUIRED")
        self.assertEqual(readiness["recommendation"], "PASS")
        self.assertEqual(readiness["empirical_corpus"]["event_count"], 28)
        self.assertEqual(readiness["empirical_corpus"]["main_head_churn_pressure_events"], 18)
        self.assertTrue(readiness["empirical_corpus"]["packet_train_progress_observed"])
        self.assertTrue(readiness["empirical_corpus"]["parallel_build_observed"])
        self.assertTrue(readiness["empirical_corpus"]["cross_programme_dependency_observed"])
        self.assertTrue(readiness["empirical_corpus"]["serialized_final_integration_observed"])
        self.assertEqual(readiness["qualification"]["orch3_packet_train_conformance"], "PASS")
        self.assertEqual(readiness["qualification"]["orch4_conflict_detector_conformance"], "PASS")
        self.assertEqual(readiness["qualification"]["orch5_portfolio_scheduler_conformance"], "PASS")
        self.assertEqual(readiness["qualification"]["recorded_unresolved_s3"], 0)
        self.assertEqual(readiness["qualification"]["recorded_unresolved_s4"], 0)
        self.assertFalse(readiness["activation_performed"])
        self.assertTrue(readiness["self_grant_prohibited"])
        self.assertEqual(readiness["blocking_warnings"], [])

        self.assertEqual(qa["status"], "PASS_GATE_READY")
        self.assertEqual(qa["tested_gate_evidence_head"], "5feb6bfd0430a7d9aab2afa483088ac2a4cbec19")
        self.assertEqual(qa["workflow_evidence"]["tests"]["run_number"], 3910)
        self.assertEqual(qa["workflow_evidence"]["tiered"]["run_number"], 2256)
        self.assertEqual(qa["recommendation"], "PASS_OPERATOR_REQUIRED_DSAI2_G3")
        self.assertFalse(qa["activation_performed"])

    def test_historical_g3_gate_state_remains_immutable_while_live_pointer_may_advance_after_operator_pass(self) -> None:
        historical = self._load(STATE_ROOT / "OVC_DSAI_V0_2_STATE_v0_3.json")
        self.assertEqual(historical["status"], "GATE_READY")
        self.assertEqual(historical["packet_id"], "DSAI2-G3")
        self.assertEqual(historical["candidate_commit"], "5feb6bfd0430a7d9aab2afa483088ac2a4cbec19")
        self.assertEqual(historical["qa"], "PASS_GATE_READY")
        self.assertTrue(historical["mandatory_stop"])
        self.assertFalse(historical["activation_performed"])
        self.assertEqual(historical["current_authority"]["ORCH-2"], "ACTIVE_BOUNDED_SINGLE_PACKET_SERIAL_REQUIRED")
        self.assertEqual(historical["current_authority"]["ORCH-3"], "INACTIVE_SHADOW_ONLY")
        self.assertEqual(historical["current_authority"]["ORCH-4"], "INACTIVE_SHADOW_ONLY")
        self.assertEqual(historical["current_authority"]["ORCH-5"], "INACTIVE_SHADOW_ONLY")

        pointer = self._load(STATE_ROOT / "CURRENT_STATE_POINTER.json")
        self.assertIn(
            pointer["current_state"],
            {
                "OVC_DSAI_V0_2_STATE_v0_3.json",
                "OVC_DSAI_V0_2_STATE_v0_4.json",
                "OVC_DSAI_V0_2_STATE_v0_5.json",
            },
        )
        if pointer["current_state"] == "OVC_DSAI_V0_2_STATE_v0_3.json":
            self.assertEqual(pointer["status"], "GATE_READY")
            self.assertEqual(pointer["next_packet"], "DSAI2-G3")
        elif pointer["current_state"] == "OVC_DSAI_V0_2_STATE_v0_4.json":
            self.assertEqual(pointer["status"], "APPROVED")
            self.assertEqual(pointer["next_packet"], "DSAI2-WP4")
            approved = self._load(STATE_ROOT / pointer["current_state"])
            self.assertEqual(approved["packet_id"], "DSAI2-WP3")
            self.assertFalse(approved["authority_effective_on_main"])
            self.assertEqual(approved["decision_record"], "docs/releases/development-skills-architecture-v0-2/dsai2-g3/DSAI2_G3_OPERATOR_PASS.json")

            authority = self._load(ROOT / "registries/development/skills/orch345_bounded_authority_v0_1.json")
            premerge_resolution = resolve_orch345_authority(authority=authority, record_present_on_main=False)
            self.assertEqual(premerge_resolution["status"], "BLOCK")
            self.assertIn("AUTHORITY_RECORD_NOT_PRESENT_ON_MAIN", premerge_resolution["reason_codes"])
        else:
            self.assertEqual(pointer["status"], "COMPLETED")
            self.assertEqual(pointer["next_packet"], "DSAI2-WP4")
            completed = self._load(STATE_ROOT / pointer["current_state"])
            self.assertEqual(completed["packet_id"], "DSAI2-WP3")
            self.assertTrue(completed["authority_effective_on_main"])
            self.assertEqual(completed["merge_commit"], "1db66a2ca48be27930395073e842638ad8f7f216")
            self.assertEqual(completed["authority_resolution"], "ACTIVE_AUTHORIZED")

            authority = self._load(ROOT / "registries/development/skills/orch345_bounded_authority_v0_1.json")
            active_resolution = resolve_orch345_authority(authority=authority, record_present_on_main=True)
            self.assertEqual(active_resolution["status"], "ACTIVE_AUTHORIZED")
            self.assertEqual(
                active_resolution["reason_codes"],
                ["EXACT_DSAI2_G3_BOUNDED_ORCH345_AUTHORITY_ACTIVE"],
            )
            self.assertFalse(authority["integration_policy"]["parallel_merge"])
            self.assertTrue(authority["integration_policy"]["serialized_final_integration_window"])
            self.assertEqual(authority["integration_policy"]["target_branch"], "main")
            self.assertEqual(authority["integration_policy"]["merge_method"], "squash")


if __name__ == "__main__":
    unittest.main()
