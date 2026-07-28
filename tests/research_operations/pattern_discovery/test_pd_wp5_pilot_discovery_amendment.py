from __future__ import annotations

import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[3]
PD_STATE = ROOT / "registries/research_operations/pattern_discovery/PD_WP5_STATE_v0_1.json"
PD_G4B_STATE = ROOT / "registries/research_operations/pattern_discovery/PD_G4B_PILOT_DISCOVERY_GATE_STATE_v0_1.json"
PD_G4B_SCHEMA = ROOT / "schemas/research_operations/pattern_discovery/pd_g4b_pilot_discovery_gate_state_v0_1.schema.json"
PD_G5P_STATE = ROOT / "registries/research_operations/pattern_discovery/PD_G5P_PILOT_OPERATIONS_ACCEPTANCE_STATE_v0_1.json"
RPS_G4A_STATE = ROOT / "registries/research_operations/prospective_source/RPS_G4A_GATE_STATE_v0_1.json"
RPS_G4_ACTIVE = ROOT / "registries/research_operations/prospective_source/RPS_G4_ACTIVE_AUTHORITY_v0_1.json"
CONTRACT = ROOT / "contracts/research_operations/pattern_discovery/PD_WP5_PILOT_DISCOVERY_OPERATION_CONTRACT_v0_1.md"
HISTORICAL_LIVE_CONTRACT = ROOT / "contracts/research_operations/pattern_discovery/PD_WP5_FIRST_LIVE_PROSPECTIVE_OPERATION_CONTRACT_v0_1.md"
GATE_PACKET = ROOT / "docs/releases/pattern-discovery-v0-3/pd-wp5/PD_G4B_PILOT_DISCOVERY_AMENDMENT_GATE_PACKET.md"
QA_PACKET = ROOT / "docs/releases/pattern-discovery-v0-3/pd-wp5/PD_G4B_PILOT_DISCOVERY_QA_PACKET.md"
DECISION = ROOT / "docs/releases/pattern-discovery-v0-3/pd-wp5/PD_G4B_OPERATOR_DECISION.md"
SUPERSESSION = ROOT / "docs/releases/pattern-discovery-v0-3/pd-wp5/RPS_G4A_PILOT_DISCOVERY_SUPERSESSION_RECORD.md"
PD_G5P_DECISION = ROOT / "docs/releases/pattern-discovery-v0-3/pd-g5p/PD_G5P_OPERATOR_DECISION.md"


def load(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


class PdWp5PilotDiscoveryAmendmentTests(unittest.TestCase):
    def test_exact_existing_replay_chain_is_bound_and_approved(self) -> None:
        gate = load(PD_G4B_STATE)
        self.assertEqual(gate["gate_id"], "PD-G4B")
        self.assertEqual(gate["gate_status"], "APPROVED")
        self.assertEqual(gate["decision"], "PASS")
        self.assertEqual(gate["decision_authority"], "OPERATOR")
        self.assertFalse(gate["operator_approval_required"])
        self.assertEqual(gate["operator_approval_command"], "OVC APPROVE PD-G4B")
        self.assertEqual(gate["research_role"], "PILOT_DISCOVERY")
        self.assertEqual(gate["operation_mode"], "TIME_GATED_REPLAY")
        self.assertEqual(gate["source_slice_id"], "RPS.DUKASCOPY.GBPUSD.20260622_20260625.v1")
        self.assertEqual(gate["source_coverage_state"], "GAPPED")
        self.assertEqual(gate["compute_run_id"], "RPS.RUN.7aeb551335d766ee3bf503e6")
        self.assertEqual(gate["source_binding_id"], "RPS.BINDING.32fb3003efa072916c11e907")
        self.assertEqual(gate["signed_replay_acceptance_id"], "RPS.REPLAY-ACCEPT.0844eddf74e144ced487cc48")
        self.assertEqual(gate["signing_binding_id"], "RPS.SIGNING.50092c28981fef08f53a6cb5")
        self.assertEqual(gate["operator_id"], "OVC.OPERATOR.PRIMARY.LOCAL.V1")

    def test_pilot_packet_completed_and_corr1_authorised_after_defer(self) -> None:
        state = load(PD_STATE)
        self.assertEqual(state["packet_status"], "COMPLETED")
        self.assertEqual(state["packet_phase"], "PD_G5P_DEFERRED_PD_WP5_CORR1_AUTHORISED")
        self.assertEqual(state["authority_required"], "NONE_FOR_PD_WP5_CORR1_NON_ACTIVATING_SPECIFICATION")
        self.assertFalse(state["operator_approval_required"])
        self.assertEqual(state["decision"], "DEFER")
        self.assertEqual(state["next_packet"], "PD-WP5-CORR1")
        self.assertEqual(state["next_gate"], "PD-G5P")
        self.assertEqual(state["decision_record"], "docs/releases/pattern-discovery-v0-3/pd-g5p/PD_G5P_OPERATOR_DECISION.md")
        self.assertEqual(state["second_pilot_replay"], "DENIED")

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

    def test_current_live_authority_is_not_relabelled_by_pilot_approval(self) -> None:
        active = load(RPS_G4_ACTIVE)
        self.assertEqual(active["status"], "ACTIVE_RESEARCH_TRIAGE_APPROVED")
        self.assertEqual(active["operation_mode"], "LIVE_PROSPECTIVE")
        self.assertFalse(active["candidate_source_resolved"])
        self.assertFalse(active["live_append_enabled"])
        self.assertEqual(active["time_gated_replay_backfill"], "DENIED")

    def test_pd_g5p_defer_still_precedes_canonical_discovery(self) -> None:
        gate = load(PD_G4B_STATE)
        acceptance = load(PD_G5P_STATE)
        self.assertEqual(gate["next_gate"], "PD-G5P")
        self.assertEqual(acceptance["gate_status"], "COMPLETED")
        self.assertEqual(acceptance["decision"], "DEFER")
        self.assertFalse(acceptance["canonical_discovery_available"])
        self.assertEqual(acceptance["next_packet"], "PD-WP5-CORR1")
        self.assertEqual(acceptance["next_source_on_pass"], "OPT-B.C2.GBPUSD.DISCOVERY.2021_2023.v1")
        self.assertIn("RESET_ALL", acceptance["required_identity_action_on_pass"])
        self.assertEqual(acceptance["second_pilot_replay"], "DENIED")

    def test_gate_schema_covers_full_machine_record(self) -> None:
        gate = load(PD_G4B_STATE)
        schema = load(PD_G4B_SCHEMA)
        allowed = set(schema["properties"])
        required = set(schema["required"])
        self.assertFalse(set(gate) - allowed)
        self.assertFalse(required - set(gate))
        self.assertFalse(schema["additionalProperties"])

    def test_historical_and_current_test_evidence_are_pinned(self) -> None:
        gate = load(PD_G4B_STATE)
        state = load(PD_STATE)
        self.assertEqual(gate["tested_candidate_head"], "1c55524754d6cd457ea8e60a6478206bb89aa886")
        self.assertEqual(gate["pull_request"], 117)
        self.assertEqual(len(gate["tests"]), 3)
        self.assertEqual(gate["pilot_amendment_job"], 90114384840)
        self.assertEqual(gate["historical_supersession_job"], 90114385057)
        self.assertEqual(gate["canonical_test_job"], 90114384730)
        self.assertEqual(state["tested_candidate_head"], "06b0a4604b1afc72b130f3dc2eab1dd8be4f9fc5")
        self.assertEqual(state["implementation_pull_request"], 121)
        self.assertEqual(state["implementation_tests"][0]["workflow_run"], 30353957840)
        self.assertEqual(state["gate_tests"][0]["workflow_run"], 30368743532)

    def test_contract_and_gate_records_are_complete(self) -> None:
        for path in (CONTRACT, HISTORICAL_LIVE_CONTRACT, GATE_PACKET, QA_PACKET, DECISION, SUPERSESSION, PD_G5P_DECISION):
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
        self.assertIn("Decision: `PASS`", DECISION.read_text(encoding="utf-8"))
        self.assertIn("OVC APPROVE PD-G5P DEFER", PD_G5P_DECISION.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
