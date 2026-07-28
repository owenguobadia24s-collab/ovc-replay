from __future__ import annotations

import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[3]
RETURN_STATE = ROOT / "registries/research_operations/pattern_discovery/PD_G5P_CORRECTION_RETURN_STATE_v0_1.json"
PARENT_STATE = ROOT / "registries/research_operations/pattern_discovery/PD_WP5_STATE_v0_1.json"
CORR1_STATE = ROOT / "registries/research_operations/pattern_discovery/PD_WP5_CORR1_STATE_v0_1.json"
C1C_STATE = ROOT / "registries/research_operations/pattern_discovery/PD_C1C_G5_PILOT_CORRECTIVE_STATE_v0_1.json"
QA_PACKET = ROOT / "docs/releases/pattern-discovery-v0-3/pd-wp5-corr1/PD_G5P_CORRECTION_RETURN_QA_PACKET.json"
GATE_PACKET = ROOT / "docs/releases/pattern-discovery-v0-3/pd-wp5-corr1/PD_G5P_CORRECTION_RETURN_OPERATOR_GATE_PACKET.json"
DECISION = ROOT / "docs/releases/pattern-discovery-v0-3/pd-wp5-corr1/PD_G5P_CORRECTION_RETURN_OPERATOR_DECISION.md"
BLOCKER = ROOT / "docs/releases/pattern-discovery-v0-3/pd-wp5-corr1/PD_G5P_PASS_UPSTREAM_RECONCILIATION_BLOCKER.json"
CONTRACT = ROOT / "contracts/research_operations/pattern_discovery/PD_WP5_FINAL_CANONICAL_DISCOVERY_CONTRACT_CANDIDATE_v0_2.md"
IDENTITY = ROOT / "docs/releases/pattern-discovery-v0-3/pd-wp5-corr1/PD_WP5_CANONICAL_IDENTITY_RESET_PROCEDURE_CANDIDATE.json"


def load(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


class PdG5pCorrectionReturnTests(unittest.TestCase):
    def test_operator_pass_is_recorded_but_stale_v1_delta_is_blocked(self) -> None:
        state = load(RETURN_STATE)
        self.assertEqual(state["gate_id"], "PD-G5P")
        self.assertEqual(state["gate_iteration"], 2)
        self.assertEqual(state["status"], "BLOCKED")
        self.assertEqual(state["decision_authority"], "OPERATOR")
        self.assertFalse(state["operator_approval_required"])
        self.assertEqual(state["decision"], "PASS")
        self.assertEqual(state["operator_command"], "OVC APPROVE PD-G5P PASS")
        self.assertIn("NOT_EFFECTIVE", state["decision_effect"])
        self.assertEqual(state["blockers"][0]["blocker_id"], "C1C-G5-BLOCK-001")
        self.assertTrue(DECISION.is_file())
        self.assertTrue(BLOCKER.is_file())

    def test_current_authority_remains_fail_closed(self) -> None:
        current = load(RETURN_STATE)["current_authority"]
        self.assertEqual(current["research_role"], "PILOT_DISCOVERY")
        self.assertTrue(current["pilot_only"])
        self.assertEqual(current["promotion_eligibility"], "NON_PROMOTABLE")
        for key in (
            "second_pilot_replay",
            "canonical_discovery_processing",
            "canonical_append",
            "contract_activation",
            "identity_reset_activation",
            "semantic_promotion",
            "family_promotion",
            "candidate_promotion",
            "threshold_or_model_change",
            "active_novelty_ranking",
            "selector_mutation",
            "release_mutation",
            "r2_publication",
        ):
            self.assertEqual(current[key], "DENIED", (key, current[key]))
        self.assertEqual(current["validation_consumption"], "LOCKED_UNCONSUMED")
        for key in (
            "probability_authority",
            "risk_authority",
            "exposure_authority",
            "trading_authority",
            "execution_authority",
            "agent_write_authority",
        ):
            self.assertEqual(current[key], "NONE", (key, current[key]))

    def test_reviewed_v1_delta_conflicts_with_current_v2_authority(self) -> None:
        state = load(RETURN_STATE)
        delta = state["proposed_authority_delta_on_pass"]
        reconciliation = state["upstream_reconciliation"]
        self.assertEqual(delta["authorise_source"], "OPT-B.C2.GBPUSD.DISCOVERY.2021_2023.v1")
        self.assertEqual(reconciliation["active_c2_release_id"], "OPT-B.C2.GBPUSD.DISCOVERY.2021_2023.v2")
        self.assertEqual(reconciliation["active_c2_selector_id"], "SELECTOR.OPT-B.C2.GBPUSD.v2")
        self.assertEqual(reconciliation["blocker_id"], "C1C-G5-BLOCK-001")
        blocker = load(BLOCKER)
        self.assertTrue(blocker["decision_effect"]["operator_pass_recorded"])
        self.assertFalse(blocker["decision_effect"]["reviewed_delta_effective"])
        self.assertEqual(blocker["decision_effect"]["pd_wp5_canonical_packet"], "NOT_AUTHORISED")

    def test_c1c_corrective_state_is_the_lawful_continuation(self) -> None:
        c1c = load(C1C_STATE)
        self.assertEqual(c1c["status"], "BLOCKED_OPERATOR_LOCAL_CORRECTIVE_RERUN_REQUIRED")
        self.assertEqual(c1c["blocker_id"], "C1C-G5-BLOCK-001")
        self.assertEqual(c1c["corrective_rerun"]["active_c2_release_id"], "OPT-B.C2.GBPUSD.DISCOVERY.2021_2023.v2")
        self.assertEqual(c1c["corrective_rerun"]["namespace"], "PD.PILOT.GBPUSD.20260622_20260625.v2")
        self.assertEqual(c1c["source_pilot"]["disposition"], "SUPERSEDED_NONCANONICAL_LINEAGE_IDENTITY")

    def test_corr1_and_reviewed_gate_snapshot_remain_immutable_evidence(self) -> None:
        corr1 = load(CORR1_STATE)
        gate = load(GATE_PACKET)
        qa = load(QA_PACKET)
        self.assertEqual(corr1["status"], "COMPLETED")
        self.assertEqual(corr1["decision"], "PASS")
        self.assertEqual(corr1["merge_commit"], "3e6f9f3f7f5dc2441d1c8c211bc5e5347e8e1d96")
        self.assertEqual(gate["gate_status"], "GATE_READY")
        self.assertEqual(gate["recommended_decision"], "PASS")
        self.assertIsNone(gate["decision_record"])
        self.assertEqual(qa["qa_status"], "PASS")
        self.assertEqual(qa["qa_recommendation"], "PASS")

    def test_contract_and_identity_reset_remain_candidates(self) -> None:
        identity = load(IDENTITY)
        self.assertEqual(identity["status"], "CANDIDATE_ONLY_NOT_AUTHORISED")
        self.assertEqual(identity["pilot_identity_reuse"], "DENIED")
        self.assertFalse(identity["canonical_run_authorised"])
        contract = CONTRACT.read_text(encoding="utf-8")
        self.assertIn("CANDIDATE_ONLY_NOT_AUTHORISED", contract)
        self.assertIn("Activation requires a new explicit operator decision", contract)

    def test_parent_state_stops_at_operator_local_corrective_rerun(self) -> None:
        parent = load(PARENT_STATE)
        self.assertEqual(parent["packet_status"], "BLOCKED")
        self.assertEqual(parent["decision"], "PASS")
        self.assertFalse(parent["operator_approval_required"])
        self.assertEqual(parent["active_c2_model_release_id"], "OPT-B.C2.GBPUSD.DISCOVERY.2021_2023.v2")
        self.assertEqual(parent["pilot_lineage_disposition"], "SUPERSEDED_NONCANONICAL_LINEAGE_IDENTITY")
        self.assertEqual(parent["next_packet"], "C1C-G5-CORRECTIVE-PILOT-RERUN")
        self.assertEqual(parent["next_gate"], "C1C-G5-CORRECTIVE-PILOT-REVIEW")
        self.assertEqual(parent["canonical_append"], "DENIED")


if __name__ == "__main__":
    unittest.main()
