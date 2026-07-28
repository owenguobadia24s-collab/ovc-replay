from __future__ import annotations

import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[3]
RETURN_STATE = ROOT / "registries/research_operations/pattern_discovery/PD_G5P_CORRECTION_RETURN_STATE_v0_1.json"
PARENT_STATE = ROOT / "registries/research_operations/pattern_discovery/PD_WP5_STATE_v0_1.json"
CORR1_STATE = ROOT / "registries/research_operations/pattern_discovery/PD_WP5_CORR1_STATE_v0_1.json"
QA_PACKET = ROOT / "docs/releases/pattern-discovery-v0-3/pd-wp5-corr1/PD_G5P_CORRECTION_RETURN_QA_PACKET.json"
GATE_PACKET = ROOT / "docs/releases/pattern-discovery-v0-3/pd-wp5-corr1/PD_G5P_CORRECTION_RETURN_OPERATOR_GATE_PACKET.json"
CONTRACT = ROOT / "contracts/research_operations/pattern_discovery/PD_WP5_FINAL_CANONICAL_DISCOVERY_CONTRACT_CANDIDATE_v0_2.md"
IDENTITY = ROOT / "docs/releases/pattern-discovery-v0-3/pd-wp5-corr1/PD_WP5_CANONICAL_IDENTITY_RESET_PROCEDURE_CANDIDATE.json"
REGISTRY = ROOT / "registries/research_operations/pattern_discovery/PATTERN_DISCOVERY_IMPLEMENTATION_REGISTRY_v0_3.yaml"


def load(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


class PdG5pCorrectionReturnTests(unittest.TestCase):
    def test_gate_is_operator_reserved_and_fail_closed(self) -> None:
        state = load(RETURN_STATE)
        self.assertEqual(state["gate_id"], "PD-G5P")
        self.assertEqual(state["gate_iteration"], 2)
        self.assertEqual(state["status"], "GATE_READY")
        self.assertEqual(state["decision_authority"], "OPERATOR")
        self.assertTrue(state["operator_approval_required"])
        self.assertIsNone(state["decision_record"])
        self.assertEqual(
            set(state["allowed_decisions"]),
            {"PASS", "DEFER", "BLOCK", "QUARANTINE", "SUPERSEDE"},
        )

        current = state["current_authority"]
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
            "validation_consumption",
        ):
            self.assertEqual(current[key], "DENIED", (key, current[key]))
        for key in (
            "probability_authority",
            "risk_authority",
            "exposure_authority",
            "trading_authority",
            "execution_authority",
            "agent_write_authority",
        ):
            self.assertEqual(current[key], "NONE", (key, current[key]))

    def test_proposed_pass_delta_is_exact_and_bounded(self) -> None:
        state = load(RETURN_STATE)
        delta = state["proposed_authority_delta_on_pass"]
        self.assertEqual(
            delta["activate_contract"],
            "PD_WP5_FINAL_CANONICAL_DISCOVERY_CONTRACT_v0_2",
        )
        self.assertTrue(delta["activate_identity_reset_procedure"])
        self.assertEqual(delta["authorise_packet"], "PD-WP5-CANONICAL")
        self.assertEqual(delta["authorise_research_role"], "CANONICAL_DISCOVERY")
        self.assertEqual(
            delta["authorise_source"],
            "OPT-B.C2.GBPUSD.DISCOVERY.2021_2023.v1",
        )
        self.assertEqual(
            delta["authorise_processing"],
            "LOCAL_DETERMINISTIC_CANONICAL_DISCOVERY_CANDIDATE_BUILD",
        )
        self.assertTrue(delta["require_new_canonical_run_id"])
        self.assertTrue(delta["require_new_canonical_namespace"])
        self.assertTrue(delta["require_complete_pilot_identity_exclusion"])
        self.assertFalse(delta["canonical_append_to_final_evidence"])
        self.assertFalse(delta["second_pilot_replay"])
        self.assertFalse(delta["semantic_or_family_promotion"])
        self.assertFalse(delta["selector_release_or_r2_mutation"])
        self.assertFalse(delta["validation_consumption"])

    def test_corr1_is_complete_and_no_second_replay_is_required(self) -> None:
        corr1 = load(CORR1_STATE)
        self.assertEqual(corr1["status"], "COMPLETED")
        self.assertEqual(corr1["qa_result"], "PASS")
        self.assertEqual(corr1["decision"], "PASS")
        self.assertEqual(corr1["decision_authority"], "DELEGATED_AUTO_EXECUTABLE")
        self.assertEqual(
            corr1["merge_commit"],
            "3e6f9f3f7f5dc2441d1c8c211bc5e5347e8e1d96",
        )
        self.assertEqual(corr1["second_pilot_replay_recommendation"], "NOT_REQUIRED")
        self.assertFalse(corr1["second_pilot_replay_authorised"])
        self.assertFalse(corr1["canonical_discovery_authorised"])
        self.assertEqual(len(corr1["closed_objectives"]), 6)

    def test_gate_packet_is_one_consolidated_decision(self) -> None:
        gate = load(GATE_PACKET)
        qa = load(QA_PACKET)
        self.assertEqual(gate["gate_id"], "PD-G5P")
        self.assertEqual(gate["gate_iteration"], 2)
        self.assertEqual(gate["gate_status"], "GATE_READY")
        self.assertTrue(gate["operator_approval_required"])
        self.assertEqual(gate["recommended_decision"], "PASS")
        self.assertEqual(gate["qa_result"], "PASS")
        self.assertEqual(gate["unresolved_issues"], [])
        self.assertIsNone(gate["decision_record"])
        self.assertEqual(qa["qa_status"], "PASS")
        self.assertEqual(qa["qa_recommendation"], "PASS")
        self.assertEqual(qa["unresolved_issues"], [])
        self.assertEqual(len(gate["exact_work_after_pass"]), 8)
        self.assertIn("PD-WP5-CANONICAL", gate["exact_work_after_pass"][0])
        self.assertEqual(
            gate["external_artifact_hashes"]["correction_ledger_sha256"],
            "cd93fb5cc6490402449d94a433e7f74a4f12722ef2a922dd12f3236dcd0f17bd",
        )

    def test_contract_and_identity_reset_remain_candidates(self) -> None:
        self.assertTrue(CONTRACT.is_file())
        identity = load(IDENTITY)
        self.assertEqual(identity["status"], "CANDIDATE_ONLY_NOT_AUTHORISED")
        self.assertEqual(identity["pilot_identity_reuse"], "DENIED")
        self.assertFalse(identity["canonical_run_authorised"])
        contract = CONTRACT.read_text(encoding="utf-8")
        self.assertIn("CANDIDATE_ONLY_NOT_AUTHORISED", contract)
        self.assertIn("No pilot candidate, fingerprint, cluster, medoid, assignment, family or evidence identity may be reused", contract)
        self.assertIn("canonical Discovery processing", contract)
        self.assertIn("Activation requires a new explicit operator decision", contract)

    def test_parent_and_programme_state_return_to_gate(self) -> None:
        parent = load(PARENT_STATE)
        self.assertEqual(parent["packet_status"], "GATE_READY")
        self.assertTrue(parent["operator_approval_required"])
        self.assertEqual(parent["recommended_gate_decision"], "PASS")
        self.assertEqual(parent["next_gate"], "PD-G5P")
        registry = REGISTRY.read_text(encoding="utf-8")
        self.assertIn("current_authority: PD_WP5_CORR1_APPROVED_PD_G5P_RETURN_PENDING", registry)
        self.assertIn("current_packet: PD-G5P", registry)
        self.assertIn("canonical_append_enabled: false", registry)
        self.assertIn("second_pilot_replay_authorised: false", registry)


if __name__ == "__main__":
    unittest.main()
