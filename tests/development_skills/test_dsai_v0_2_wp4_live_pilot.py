from __future__ import annotations

import json
import unittest
from pathlib import Path

from ovc.development.skills.orch345 import (
    PARALLEL_BUILD_CLASS,
    SERIAL_CLASS,
    SERIAL_INTEGRATION_POLICY,
    resolve_orch345_authority,
)
from ovc.development.skills.orch345_pilot import build_wp4_live_pilot


ROOT = Path(__file__).resolve().parents[2]
AUTHORITY_PATH = ROOT / "registries/development/skills/orch345_bounded_authority_v0_1.json"
RELEASE = ROOT / "docs/releases/development-skills-architecture-v0-2/dsai2-wp4"
C2P_STATE = ROOT / "registries/implementation/c2p_v0_2/OVC_C2P2_STATE_v0_1.json"


class DSAI2WP4LivePilotTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.authority = json.loads(AUTHORITY_PATH.read_text(encoding="utf-8"))
        cls.pack = build_wp4_live_pilot(cls.authority)

    def _load(self, path: Path) -> dict:
        return json.loads(path.read_text(encoding="utf-8"))

    def test_active_authority_is_exact_and_reserved_boundaries_remain_closed(self) -> None:
        resolution = resolve_orch345_authority(authority=self.authority, record_present_on_main=True)
        self.assertEqual(resolution["status"], "ACTIVE_AUTHORIZED")
        self.assertEqual(
            resolution["reason_codes"],
            ["EXACT_DSAI2_G3_BOUNDED_ORCH345_AUTHORITY_ACTIVE"],
        )
        self.assertEqual(self.authority["enabled_packet_classes"], ["LOW_RISK_IMPLEMENTATION"])
        self.assertFalse(self.authority["integration_policy"]["parallel_merge"])
        self.assertTrue(self.authority["integration_policy"]["serialized_final_integration_window"])
        self.assertEqual(self.authority["integration_policy"]["target_branch"], "main")
        self.assertEqual(self.authority["integration_policy"]["merge_method"], "squash")
        self.assertFalse(self.authority["integration_policy"]["direct_main_mutation"])
        self.assertFalse(self.authority["integration_policy"]["force_push"])
        self.assertFalse(self.authority["integration_policy"]["history_rewrite"])
        self.assertEqual(self.authority["validation"], "DENIED")
        self.assertEqual(self.authority["reserved_scientific_execution_authority"], "NONE")

    def test_orch3_executes_bounded_same_programme_serial_packet_train(self) -> None:
        result = self.pack["orch3"]["result"]
        self.assertEqual(
            result["selected_packet_ids"],
            ["DSAI2-WP4-ORCH3-A", "DSAI2-WP4-ORCH3-B"],
        )
        self.assertEqual(result["waiting"], [])
        self.assertEqual(result["operator_boundaries"], [])
        self.assertEqual(result["execution_mode"], "ACTIVE_BOUNDED")
        self.assertEqual(result["integration_policy"], SERIAL_INTEGRATION_POLICY)
        self.assertFalse(result["parallel_merge"])

        receipt = self._load(RELEASE / "DSAI2_WP4_LIVE_PILOT_RECEIPT.json")
        self.assertEqual(
            receipt["orch3_live_train"]["execution_order"],
            ["DSAI2-WP4-ORCH3-A", "DSAI2-WP4-ORCH3-B"],
        )
        self.assertEqual(
            receipt["orch3_live_train"]["packet_b"]["observed_predecessor_commit"],
            receipt["orch3_live_train"]["packet_a"]["commit"],
        )
        self.assertFalse(receipt["orch3_live_train"]["parallel_merge"])

    def test_orch4_admits_disjoint_parallel_build_but_forces_serial_integration(self) -> None:
        admitted = self.pack["orch4"]["parallel_admission"]
        self.assertEqual(admitted["classification"], PARALLEL_BUILD_CLASS)
        self.assertEqual(admitted["reason_codes"], [])
        self.assertEqual(admitted["admission"], "PARALLEL_BUILD_ADMITTED_SERIAL_INTEGRATION_ONLY")
        self.assertEqual(admitted["integration_policy"], SERIAL_INTEGRATION_POLICY)
        self.assertFalse(admitted["parallel_merge"])

        a = self._load(RELEASE / "pilot/orch4-a-integrated.json")
        b = self._load(RELEASE / "pilot/orch4-b-integrated.json")
        self.assertEqual(a["construction_base"], b["construction_base"])
        self.assertNotEqual(a["isolated_branch"], b["isolated_branch"])
        self.assertNotEqual(a["isolated_commit"], b["isolated_commit"])
        self.assertNotEqual(a["isolated_write_path"], b["isolated_write_path"])
        self.assertEqual(a["integration_sequence"], 1)
        self.assertEqual(b["integration_sequence"], 2)
        self.assertEqual(b["preceding_serial_integration_commit"], "a5b4b1034f8993a7c882cfd04728d28ba3c01f44")
        self.assertFalse(a["merge_of_isolated_branch_performed"])
        self.assertFalse(b["merge_of_isolated_branch_performed"])
        self.assertFalse(a["parallel_merge"])
        self.assertFalse(b["parallel_merge"])

    def test_orch4_ambiguous_or_overlapping_write_set_fails_closed_to_serial(self) -> None:
        fallback = self.pack["orch4"]["serial_fallback"]
        self.assertEqual(fallback["classification"], SERIAL_CLASS)
        self.assertEqual(fallback["admission"], "SERIAL_REQUIRED")
        self.assertIn("WRITE_SET_OVERLAP", fallback["reason_codes"])
        self.assertEqual(fallback["integration_policy"], SERIAL_INTEGRATION_POLICY)
        self.assertFalse(fallback["parallel_merge"])
        self.assertEqual(self.pack["acceptance_metrics"]["false_parallel_allows"], 0)
        self.assertEqual(self.pack["acceptance_metrics"]["unresolved_conflict_classifications"], 0)

    def test_orch5_dispatches_eligible_work_while_respecting_dependency_and_operator_wait(self) -> None:
        result = self.pack["orch5"]["result"]
        self.assertEqual(
            result["selected_packet_ids"],
            ["DSAI2-WP4-PORTFOLIO-READY", "DSAI2-WP4-PORTFOLIO-CROSS-PROGRAMME"],
        )
        self.assertEqual(result["operator_wait"], ["RCN-RN-G4"])
        blocked = {item["packet_id"]: item for item in result["blocked"]}
        self.assertIn("DSAI2-WP4-PORTFOLIO-BLOCKED", blocked)
        self.assertEqual(blocked["DSAI2-WP4-PORTFOLIO-BLOCKED"]["reason"], "MISSING_PREREQUISITE")
        self.assertIn("DSAI2-MISSING-PREREQUISITE", blocked["DSAI2-WP4-PORTFOLIO-BLOCKED"]["missing"])
        self.assertEqual(result["dispatch_authority"], "ALREADY_AUTHORIZED_LOW_RISK_PACKETS_ONLY")
        self.assertEqual(result["integration_policy"], SERIAL_INTEGRATION_POLICY)
        self.assertFalse(result["parallel_merge"])

        metrics = self.pack["acceptance_metrics"]
        self.assertTrue(metrics["operator_wait_respected"])
        self.assertTrue(metrics["cross_programme_dependency_respected"])
        self.assertTrue(metrics["missing_prerequisite_blocked"])
        self.assertEqual(metrics["parallel_merges"], 0)

    def test_cross_programme_dependency_is_grounded_in_completed_c2p_packet(self) -> None:
        state = self._load(C2P_STATE)
        wp0 = next(item for item in state["packet_register"] if item["packet_id"] == "C2P2-WP0")
        self.assertEqual(wp0["status"], "COMPLETED")
        self.assertEqual(wp0["merge_commit"], "fdf64e0df76c5f75b21de357bac05ec965b9f0f7")
        self.assertEqual(self.pack["orch5"]["cross_programme_dependency"], "C2P2-WP0")
        self.assertEqual(self.pack["orch5"]["operator_wait_source"], "RCN-RN-G4 / PR #678")

    def test_incident_sweep_is_repository_scoped_and_has_no_recorded_unresolved_s3_s4(self) -> None:
        sweep = self._load(RELEASE / "DSAI2_WP4_INCIDENT_AND_CONTAINMENT_SWEEP.json")
        self.assertEqual(sweep["dsai2_incident_search"]["recorded_unresolved_s3"], 0)
        self.assertEqual(sweep["dsai2_incident_search"]["recorded_unresolved_s4"], 0)
        self.assertIn("Repository court record only", sweep["record_scope"])
        self.assertFalse(sweep["pilot_containment_checks"]["parallel_merge_performed"])
        self.assertFalse(sweep["pilot_containment_checks"]["operator_required_packet_dispatched"])
        self.assertFalse(sweep["pilot_containment_checks"]["missing_prerequisite_packet_dispatched"])
        self.assertEqual(sweep["blocking_warnings"], [])
        self.assertEqual(sweep["unresolved_issues"], [])

    def test_pilot_receipt_is_non_promotional_and_pending_assurance_only(self) -> None:
        receipt = self._load(RELEASE / "DSAI2_WP4_LIVE_PILOT_RECEIPT.json")
        self.assertEqual(receipt["authority_delta"], "NONE")
        self.assertEqual(receipt["status"], "IMPLEMENTED_PENDING_ASSURANCE")
        self.assertEqual(receipt["g4_acceptance_observations"]["parallel_merges_observed"], 0)
        self.assertTrue(receipt["g4_acceptance_observations"]["serialized_integration_observed"])
        self.assertFalse(receipt["g4_acceptance_observations"]["reserved_authority_crossed"])
        self.assertEqual(receipt["performance_claims"], "NONE; this pilot evaluates conformance and containment, not causal speed improvement.")
        self.assertFalse(self.pack["parallel_merge"])
        self.assertEqual(self.pack["authority_delta"], "NONE")


if __name__ == "__main__":
    unittest.main()
