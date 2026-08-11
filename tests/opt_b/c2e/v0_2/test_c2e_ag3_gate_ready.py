import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[4]
AG3 = ROOT / "docs/releases/c2e-causal-episode-v0-2/c2e-ag3"
BASE = ROOT / "registries/implementation/c2e_v0_2"
PACK = ROOT / "registries/opt_b/c2e/v0_2/C2E_EMPIRICAL_BOUNDARY_PACK_JUNE_STABLE_v0_2.json"
PACK_REGISTRY = ROOT / "registries/opt_b/c2e/v0_2/C2E_BOUNDARY_PACK_REGISTRY_v0_2.json"
AUTH_REGISTRY = ROOT / "registries/opt_b/c2e/v0_2/C2E_AUTHORITY_REGISTRY_v0_2.json"
AG2_DECISION = ROOT / "docs/releases/c2e-causal-episode-v0-2/c2e-ag2-r2/C2E_AG2_OPERATOR_PASS_DECISION.json"

PACK_ID = "C2E.BOUNDARY.PACK.043c628a3a29372ae478026db307d0d8"
PACK_HASH = "043c628a3a29372ae478026db307d0d8b2347fcbbc7b06dbb1a3cc345c86e313"


def load(path):
    return json.loads(path.read_text())


class C2EAG3GateReadyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.assessment = load(AG3 / "C2E_AG3_SELECTOR_TRANSACTION_ASSESSMENT.json")
        cls.proposal = load(AG3 / "C2E_AG3_ACTIVATION_PROPOSAL.json")
        cls.gate = load(AG3 / "C2E_AG3_GATE_PACKET.json")
        cls.qa = load(AG3 / "C2E_AG3_QA_PACKET.json")
        cls.state = load(BASE / "OVC_C2E2_STATE_v0_43_AG3_GATE_READY.json")
        cls.pointer = load(BASE / "CURRENT_STATE_POINTER.json")
        cls.pack = load(PACK)
        cls.pack_registry = load(PACK_REGISTRY)
        cls.auth_registry = load(AUTH_REGISTRY)
        cls.ag2 = load(AG2_DECISION)

    def test_ag3_is_operator_reserved_and_not_executed(self):
        self.assertEqual(self.gate["gate_id"], "C2E-AG3")
        self.assertEqual(self.gate["gate_classification"], "OPERATOR_RESERVED")
        self.assertEqual(self.gate["decision_status"], "PENDING_OPERATOR")
        self.assertEqual(self.gate["allowed_decisions"], ["ACTIVATE_NAMED_PACK", "REPLACE", "DEFER", "BLOCK"])
        self.assertEqual(self.gate["recommended_decision"], "ACTIVATE_NAMED_PACK")
        self.assertEqual(self.proposal["status"], "PROPOSED_NOT_EXECUTED")
        self.assertEqual(self.proposal["execution"], "NOT_EXECUTED_STOP_FOR_OPERATOR")

    def test_exact_pack_is_bound_and_immutable(self):
        self.assertEqual(self.pack["boundary_pack_id"], PACK_ID)
        self.assertEqual(self.pack["logical_sha256"], PACK_HASH)
        self.assertEqual(self.pack["authority"], "CANDIDATE")
        self.assertFalse(self.pack["active"])
        self.assertFalse(self.pack["canonical"])
        subject = self.gate["review_subject"]
        self.assertEqual(subject["boundary_pack_id"], PACK_ID)
        self.assertEqual(subject["logical_sha256"], PACK_HASH)
        self.assertEqual(subject["source_blob_sha"], "dc12ed68d55b14579bcd0050a3f102979781656b")
        self.assertEqual(subject["population_scope"]["target_frame_count"], 4072)

    def test_current_selector_and_authority_are_still_inactive(self):
        self.assertIsNone(self.pack_registry["active_boundary_pack_id"])
        self.assertFalse(self.pack_registry["production_pack_selected"])
        self.assertFalse(self.pack_registry["active"])
        self.assertFalse(self.auth_registry["active_c2e"])
        self.assertIsNone(self.auth_registry["active_boundary_pack_id"])
        self.assertEqual(self.pointer["active_c2e"], "NONE")
        self.assertEqual(self.pointer["active_boundary_pack"], "NONE")
        self.assertEqual(self.pointer["ag3"], "NOT_EXECUTED")

    def test_ag0_ag1_ag2_prerequisites_are_pass(self):
        self.assertEqual(self.pointer["ag0_admissibility"], "PASS")
        self.assertEqual(self.pointer["ag1_replay_adequacy"], "PASS")
        self.assertEqual(self.pointer["ag2_progression"], "COMPLETED_PASS")
        self.assertEqual(self.ag2["decision"], "PASS")
        self.assertIn("C2E-AG2.OPERATOR.PASS.20260811T191400+0100", self.pointer["operator_decision_history"])

    def test_selector_surface_is_existing_registry_not_pack_mutation(self):
        self.assertEqual(self.assessment["assessment"], "PASS_SELECTOR_AND_ACTIVE_PACK_REGISTRY_SURFACES_MATERIALIZED")
        self.assertFalse(self.assessment["candidate_pack"]["immutable_pack_mutation_required"])
        tx = self.proposal["proposed_operator_transaction_if_activated"]
        self.assertEqual(tx["candidate_pack_file_mutation"], "NONE")
        self.assertEqual(tx["runtime_code_mutation"], "NONE")
        self.assertEqual(tx["boundary_pack_registry"]["after"]["active_boundary_pack_id"], PACK_ID)
        self.assertTrue(tx["boundary_pack_registry"]["after"]["production_pack_selected"])
        self.assertTrue(tx["authority_registry"]["after"]["active_c2e"])
        self.assertEqual(tx["authority_registry"]["after"]["active_boundary_pack_id"], PACK_ID)
        self.assertEqual(self.gate["gate_classification"], "OPERATOR_RESERVED")
        self.assertEqual(self.gate["decision_status"], "PENDING_OPERATOR")
        self.assertIsNone(self.pack_registry["active_boundary_pack_id"])
        self.assertFalse(self.auth_registry["active_c2e"])

    def test_rollback_disables_selection_without_erasing_evidence(self):
        rb = self.proposal["rollback_if_activated"]
        self.assertIsNone(rb["boundary_pack_registry_target"]["active_boundary_pack_id"])
        self.assertFalse(rb["boundary_pack_registry_target"]["production_pack_selected"])
        self.assertFalse(rb["authority_registry_target"]["active_c2e"])
        self.assertIsNone(rb["authority_registry_target"]["active_boundary_pack_id"])
        self.assertEqual(rb["authority_registry_target"]["real_source_replay"], "COMPLETED_EXACT_AG_EVIDENCE")
        self.assertEqual(rb["deletion_or_history_rewrite"], "PROHIBITED")
        self.assertIn("AG0/AG1/AG2 decisions", rb["preserve"])

    def test_gate_ready_pointer_stops_at_ag3(self):
        self.assertEqual(self.state["status"], "GATE_READY")
        self.assertEqual(self.state["current_gate"], "C2E-AG3")
        self.assertTrue(self.state["operator_decision_required"])
        self.assertEqual(self.state["recommended_operator_decision"], "ACTIVATE_NAMED_PACK")
        self.assertEqual(self.state["active_c2e"], "NONE")
        self.assertEqual(self.state["active_boundary_pack"], "NONE")
        self.assertEqual(self.pointer["authoritative_state"], "registries/implementation/c2e_v0_2/OVC_C2E2_STATE_v0_43_AG3_GATE_READY.json")
        self.assertEqual(self.pointer["status"], "GATE_READY")
        self.assertEqual(self.pointer["current_packet"], "C2E-AG3-PREP")
        self.assertEqual(self.pointer["current_gate"], "C2E-AG3")
        self.assertTrue(self.pointer["operator_decision_required"])
        self.assertEqual(self.pointer["recommended_operator_decision"], "ACTIVATE_NAMED_PACK")
        self.assertEqual(self.pointer["next_action"], "STOP_FOR_OPERATOR_C2E_AG3")

    def test_no_downstream_authority_is_bundled(self):
        delta = self.gate["proposed_delta_if_activate_named_pack"]
        self.assertEqual(delta["canonical_or_r2_publication"], "NONE")
        self.assertEqual(delta["validation_consumption"], "NONE")
        self.assertEqual(delta["family_semantic_candidate_theory_promotion"], "NONE")
        self.assertEqual(delta["probability_risk_exposure_execution_agent_write"], "NONE")
        self.assertEqual(delta["scope_expansion"], "NONE")


if __name__ == "__main__":
    unittest.main()
