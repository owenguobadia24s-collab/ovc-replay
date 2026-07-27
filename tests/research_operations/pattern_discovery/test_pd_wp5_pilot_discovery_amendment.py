from __future__ import annotations

import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[3]
PD_STATE = ROOT / "registries/research_operations/pattern_discovery/PD_WP5_STATE_v0_1.json"
PD_G4B_STATE = ROOT / "registries/research_operations/pattern_discovery/PD_G4B_PILOT_DISCOVERY_GATE_STATE_v0_1.json"
PD_G5P_STATE = ROOT / "registries/research_operations/pattern_discovery/PD_G5P_PILOT_OPERATIONS_ACCEPTANCE_STATE_v0_1.json"
RPS_G4A_STATE = ROOT / "registries/research_operations/prospective_source/RPS_G4A_GATE_STATE_v0_1.json"
RPS_G4_ACTIVE = ROOT / "registries/research_operations/prospective_source/RPS_G4_ACTIVE_AUTHORITY_v0_1.json"
CONTRACT = ROOT / "contracts/research_operations/pattern_discovery/PD_WP5_PILOT_DISCOVERY_OPERATION_CONTRACT_v0_1.md"
HISTORICAL_LIVE_CONTRACT = ROOT / "contracts/research_operations/pattern_discovery/PD_WP5_FIRST_LIVE_PROSPECTIVE_OPERATION_CONTRACT_v0_1.md"
GATE_PACKET = ROOT / "docs/releases/pattern-discovery-v0-3/pd-wp5/PD_G4B_PILOT_DISCOVERY_AMENDMENT_GATE_PACKET.md"
QA_PACKET = ROOT / "docs/releases/pattern-discovery-v0-3/pd-wp5/PD_G4B_PILOT_DISCOVERY_QA_PACKET.md"
SUPERSESSION = ROOT / "docs/releases/pattern-discovery-v0-3/pd-wp5/RPS_G4A_PILOT_DISCOVERY_SUPERSESSION_RECORD.md"


def load(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


class PdWp5PilotDiscoveryAmendmentTests(unittest.TestCase):
    def test_exact_existing_replay_chain_is_bound(self) -> None:
        gate = load(PD_G4B_STATE)
        self.assertEqual(gate["gate_id"], "PD-G4B")
        self.assertEqual(gate["gate_status"], "GATE_READY")
        self.assertEqual(gate["decision_authority"], "OPERATOR")
        self.assertTrue(gate["operator_approval_required"])
        self.assertEqual(gate["research_role"], "PILOT_DISCOVERY")
        self.assertEqual(gate["operation_mode"], "TIME_GATED_REPLAY")
        self.assertEqual(gate["source_slice_id"], "RPS.DUKASCOPY.GBPUSD.20260622_20260625.v1")
        self.assertEqual(gate["source_coverage_state"], "GAPPED")
        self.assertEqual(gate["compute_run_id"], "RPS.RUN.7aeb551335d766ee3bf503e6")
        self.assertEqual(gate["source_binding_id"], "RPS.BINDING.32fb3003efa072916c11e907")
        self.assertEqual(gate["signed_replay_acceptance_id"], "RPS.REPLAY-ACCEPT.0844eddf74e144ced487cc48")
        self.assertEqual(gate["signing_binding_id"], "RPS.SIGNING.50092c28981fef08f53a6cb5")
        self.assertEqual(gate["operator_id"], "OVC.OPERATOR.PRIMARY.LOCAL.V1")

    def test_pilot_outputs_are_non_promotable_and_noncanonical(self) -> None:
        gate = load(PD_G4B_STATE)
        state = load(PD_STATE)
        for record in (gate, state):
            self.assertTrue(record["pilot_only"])
            self.assertEqual(record["promotion_eligibility"], "NON_PROMOTABLE")
            self.assertFalse(record["canonical_discovery_population"])
            self.assertEqual(record["canonical_append"], "DENIED")
            self.assertEqual(record["live_prospective_relabelling"], "DENIED")
            self.assertEqual(record["identity_reset_before_canonical"], "REQUIRED")
        self.assertIn("PILOT", gate["pilot_identity_namespace"])
        self.assertEqual(gate["canonical_identity_namespace_reuse"], "DENIED")

    def test_all_broader_authorities_remain_denied(self) -> None:
        gate = load(PD_G4B_STATE)
        required = {
            "CANONICAL_DISCOVERY_POPULATION_COUNTING",
            "FINAL_TRAJECTORY_FAMILY_DEFINITION",
            "PILOT_IDENTITY_REUSE",
            "SEMANTIC_PROMOTION",
            "FAMILY_PROMOTION",
            "OUTCOME_SELECTED_THRESHOLD_TUNING",
            "ACTIVE_NOVELTY_RANKING",
            "SELECTOR_MUTATION",
            "RELEASE_MUTATION",
            "DIRECT_R2_WRITE",
            "VALIDATION_CONSUMPTION",
            "PROBABILITY",
            "RISK",
            "EXPOSURE",
            "TRADING",
            "EXECUTION",
            "AGENT_WRITE",
            "LIVE_PROSPECTIVE_RELABEL",
        }
        self.assertTrue(required.issubset(set(gate["retained_prohibitions"])))

    def test_rps_g4a_is_superseded_only_for_pilot_and_live_is_deferred(self) -> None:
        rps = load(RPS_G4A_STATE)
        self.assertEqual(rps["gate_status"], "SUPERSEDED_FOR_PILOT_DISCOVERY")
        self.assertEqual(rps["superseded_by_gate"], "PD-G4B")
        self.assertEqual(rps["supersession_scope"], "INITIAL_PD_WP5_OPERATION_ONLY")
        self.assertEqual(rps["provider_request_authority"], "DENIED")
        self.assertEqual(rps["future_live_gate"], "RPS-LIVE-G1")
        self.assertIn("DEFERRED", rps["future_live_gate_status"])
        self.assertTrue(rps["future_live_requirement_retained"])

    def test_current_active_authority_is_not_silently_mutated_before_approval(self) -> None:
        active = load(RPS_G4_ACTIVE)
        self.assertEqual(active["status"], "ACTIVE_RESEARCH_TRIAGE_APPROVED")
        self.assertEqual(active["operation_mode"], "LIVE_PROSPECTIVE")
        self.assertFalse(active["candidate_source_resolved"])
        self.assertFalse(active["live_append_enabled"])
        self.assertEqual(active["time_gated_replay_backfill"], "DENIED")

    def test_pilot_acceptance_precedes_canonical_discovery(self) -> None:
        gate = load(PD_G4B_STATE)
        acceptance = load(PD_G5P_STATE)
        self.assertEqual(gate["next_gate"], "PD-G5P")
        self.assertEqual(acceptance["gate_status"], "PLANNED")
        self.assertFalse(acceptance["canonical_discovery_available"])
        self.assertEqual(acceptance["next_packet_on_pass"], "PD-WP5-CANONICAL")
        self.assertEqual(acceptance["next_source_on_pass"], "OPT-B.C2.GBPUSD.DISCOVERY.2021_2023.v1")
        self.assertIn("RESET_ALL", acceptance["required_identity_action_on_pass"])

    def test_contract_and_gate_records_are_complete(self) -> None:
        for path in (CONTRACT, HISTORICAL_LIVE_CONTRACT, GATE_PACKET, QA_PACKET, SUPERSESSION):
            self.assertTrue(path.is_file(), path)
        contract = CONTRACT.read_text(encoding="utf-8")
        for phrase in (
            "PILOT_DISCOVERY",
            "TIME_GATED_REPLAY",
            "PILOT_ONLY",
            "NON_PROMOTABLE",
            "PD-G5P",
            "reset candidate",
            "LIVE_PROSPECTIVE",
        ):
            self.assertIn(phrase, contract)
        self.assertIn("PASS_RECOMMEND_OPERATOR_AMENDMENT", QA_PACKET.read_text(encoding="utf-8"))
        self.assertIn("Recommended decision", GATE_PACKET.read_text(encoding="utf-8"))

    def test_state_precedence_over_historical_ready_entries_is_explicit(self) -> None:
        state = load(PD_STATE)
        self.assertEqual(state["packet_status"], "GATE_READY")
        self.assertEqual(state["next_gate"], "PD-G4B")
        self.assertTrue(state["supersedes_prior_ready_state"])
        self.assertGreaterEqual(len(state["superseded_ready_sources"]), 2)
        self.assertEqual(state["decision"], None)
        self.assertEqual(state["decision_authority"], "OPERATOR")


if __name__ == "__main__":
    unittest.main()
