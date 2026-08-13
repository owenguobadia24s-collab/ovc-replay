from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PACKET = ROOT / "artifacts/research_console_vnext/pvs3/RCN_RN_G4_GATE_PACKET.json"
DECISION = ROOT / "artifacts/research_console_vnext/pvs3/RCN_RN_G4_OPERATOR_DECISION.json"
RECON = ROOT / "artifacts/research_console_vnext/pvs3/RCN_RN_G4_POST_APPROVAL_RECONCILIATION.json"
POST_G4_DECISION = ROOT / "artifacts/research_console_vnext/pvs3/RCN_RN_POST_G4_SOURCE_BINDING_DECISION.json"
STATE = ROOT / "registries/implementation/research_console_vnext/OVC_RCN_RN_STATE_v0_2.json"
CAND = ROOT / "registries/research_console_vnext/research_native/wp4a_investigate_binding_candidates_v1.json"
INV = ROOT / "registries/research_console_vnext/research_native/source_adapter_inventory_v2.json"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class RcnRnG4GateReady(unittest.TestCase):
    def test_consolidated_operator_packet_is_preserved_and_pass_recorded(self):
        gate = load(PACKET)
        decision = load(DECISION)
        recon = load(RECON)
        self.assertEqual(gate["gate_id"], "RCN-RN-G4")
        self.assertEqual(gate["gate_class"], "OPERATOR_REQUIRED")
        self.assertEqual(gate["recommended_decision"], "PASS")
        self.assertEqual(gate["decision_record"], "PENDING_OPERATOR_DECISION")
        self.assertEqual(decision["decision"], "PASS")
        self.assertEqual(decision["operator_instruction"], "OVC APPROVE RCN-RN-G4 PASS")
        self.assertEqual(
            decision["approved_gate_packet_blob_sha"],
            "374e1816d9b7ed243a54130cb24f5a128d8a6e41",
        )
        self.assertFalse(decision["post_assurance_main_delta"]["g4_candidate_set_changed"])
        self.assertEqual(
            decision["granted_authority"]["candidates"],
            ["MARKET", "C1", "C2", "C2E"],
        )
        self.assertEqual(
            recon["current_main"],
            "8f35ff9ee76eeb122eb1af66e9c166b0c45437cf",
        )
        self.assertFalse(recon["main_advance"]["g4_candidate_set_changed"])
        self.assertEqual(recon["main_advance"]["c2p_runtime_authority"], "NONE")
        self.assertEqual(
            recon["main_advance"]["c2p_real_source_replay"],
            "DENIED_FUTURE_C2P2_RS0",
        )

    def test_proposed_delta_matches_predeclared_owner_candidates_only(self):
        gate = load(PACKET)
        candidates = load(CAND)
        inventory = load(INV)
        proposed = {
            row["capability_id"]
            for row in gate["proposed_authority_delta"]["candidates"]
        }
        declared = {row["capability_id"] for row in candidates["candidates"]}
        self.assertEqual(proposed, declared)
        self.assertEqual(proposed, {"MARKET", "C1", "C2", "C2E"})
        excluded = {
            row["capability_id"]
            for row in gate["proposed_authority_delta"]["excluded"]
        }
        self.assertEqual(excluded, {"C2P", "C2_5", "C3"})
        census = {row["capability_id"]: row for row in inventory["sources"]}
        self.assertEqual(
            {
                key
                for key, value in census.items()
                if value["real_route"] == "BOUND_G4_EXPLICIT_REAL_MODE"
            },
            {"opt_a", "c1", "c2", "c2e"},
        )
        self.assertEqual("DENIED", census["c2p"]["real_route"])
        self.assertEqual("DENIED", census["c2_5"]["real_route"])
        self.assertEqual("DENIED", census["c3"]["real_route"])
        self.assertFalse(census["c2p"]["runtime_owner_materialized"])
        self.assertFalse(census["c3"]["runtime_owner_materialized"])
        self.assertEqual("INACTIVE_REFERENCE", census["c3"]["maturity"])

    def test_historical_post_g4_pass_and_current_wp5a_state_are_both_exact(self):
        historical = load(POST_G4_DECISION)
        state = load(STATE)

        self.assertEqual(
            historical["packet_id"],
            "RCN-RN-POST-G4-SOURCE-BINDING",
        )
        self.assertEqual(historical["decision"], "PASS")
        self.assertEqual(
            historical["decision_class"],
            "DELEGATED_AUTO_RATIFICATION",
        )
        self.assertEqual(historical["authority_delta"], "NONE")
        self.assertEqual(historical["next_packet"], "RCN-RN-WP5A")

        self.assertEqual(state["packet_id"], "RCN-RN-WP5A")
        self.assertEqual(state["status"], "READY")
        self.assertEqual(
            state["authority_required"],
            "DELEGATED_AUTO_RATIFICATION_IF_NO_FIRST_NEW_REAL_RESEARCH_SOURCE_EXPOSURE; OPERATOR_G5_OTHERWISE",
        )
        self.assertEqual(state["authority_delta"], "NONE")
        self.assertEqual(
            state["decision"],
            "GOVERNING_ARTIFACT_MATERIALISATION_COMPLETED_AUTHORITY_UNCHANGED",
        )
        self.assertEqual(
            state["current_authority"],
            "G4_APPROVED_READ_ONLY_REAL_SOURCE_INVESTIGATE_PRESENTATION_MARKET_C1_C2_C2E",
        )
        self.assertEqual(
            state["real_source_routes"],
            "BOUND_EXPLICIT_REAL_MODE_MARKET_C1_C2_C2E__NO_FIXTURE_FALLBACK__OTHERS_DENIED",
        )
        self.assertEqual(
            state["operator_decision_record"],
            "artifacts/research_console_vnext/pvs3/RCN_RN_G4_OPERATOR_DECISION.json",
        )
        self.assertEqual(
            state["baseline_commit"],
            "4691cc683c0adfa473a1197c1d0c4c2dc6036605",
        )
        self.assertEqual(state["implementation_generation"], "v0.3")
        self.assertEqual(state["blockers"], [])

    def test_scientific_and_upper_layer_firewalls_are_explicit(self):
        text = PACKET.read_text(encoding="utf-8") + DECISION.read_text(
            encoding="utf-8"
        )
        for marker in [
            "NO_NEW_PROVIDER_INTAKE",
            "NO_NEW_INSTRUMENT_MARKET_CLOCK_SIDE_OR_UNDECLARED_DEPENDENCY",
            "NO_SELECTOR_THRESHOLD_MODEL_FAMILY_CANDIDATE_THEORY_SEMANTIC_ACTIVATION",
            "NO_VALIDATION",
            "NO_PUBLICATION",
            "NO_PROBABILITY_RISK_EXPOSURE_TRADING_EXECUTION",
            "C2.5 Candidate != EventOccurrence",
            "C3 connectivity != entailment",
            "C2P conformance namespace presence does not grant runtime or source authority",
        ]:
            self.assertIn(marker, text)


if __name__ == "__main__":
    unittest.main()
