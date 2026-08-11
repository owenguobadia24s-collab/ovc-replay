import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[4]
AG3 = ROOT / "docs/releases/c2e-causal-episode-v0-2/c2e-ag3"
BASE = ROOT / "registries/implementation/c2e_v0_2"
PACK = ROOT / "registries/opt_b/c2e/v0_2/C2E_EMPIRICAL_BOUNDARY_PACK_JUNE_STABLE_v0_2.json"
AG2_DECISION = ROOT / "docs/releases/c2e-causal-episode-v0-2/c2e-ag2-r2/C2E_AG2_OPERATOR_PASS_DECISION.json"

PACK_ID = "C2E.BOUNDARY.PACK.043c628a3a29372ae478026db307d0d8"
PACK_HASH = "043c628a3a29372ae478026db307d0d8b2347fcbbc7b06dbb1a3cc345c86e313"


def load(path):
    return json.loads(path.read_text())


class C2EAG3GateReadyHistoricalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.assessment = load(AG3 / "C2E_AG3_SELECTOR_TRANSACTION_ASSESSMENT.json")
        cls.proposal = load(AG3 / "C2E_AG3_ACTIVATION_PROPOSAL.json")
        cls.gate = load(AG3 / "C2E_AG3_GATE_PACKET.json")
        cls.state = load(BASE / "OVC_C2E2_STATE_v0_43_AG3_GATE_READY.json")
        cls.pack = load(PACK)
        cls.ag2 = load(AG2_DECISION)

    def test_gate_ready_record_remains_operator_reserved_historical_evidence(self):
        self.assertEqual(self.gate["gate_id"], "C2E-AG3")
        self.assertEqual(self.gate["gate_classification"], "OPERATOR_RESERVED")
        self.assertEqual(self.gate["decision_status"], "PENDING_OPERATOR")
        self.assertEqual(self.proposal["status"], "PROPOSED_NOT_EXECUTED")
        self.assertEqual(self.proposal["execution"], "NOT_EXECUTED_STOP_FOR_OPERATOR")
        self.assertEqual(self.state["status"], "GATE_READY")
        self.assertEqual(self.state["ag3"], "NOT_EXECUTED")
        self.assertEqual(self.state["active_c2e"], "NONE")
        self.assertEqual(self.state["active_boundary_pack"], "NONE")

    def test_exact_pack_identity_and_pack_bytes_remain_immutable(self):
        self.assertEqual(self.pack["boundary_pack_id"], PACK_ID)
        self.assertEqual(self.pack["logical_sha256"], PACK_HASH)
        self.assertEqual(self.pack["authority"], "CANDIDATE")
        self.assertFalse(self.pack["active"])
        self.assertFalse(self.pack["canonical"])
        subject = self.gate["review_subject"]
        self.assertEqual(subject["boundary_pack_id"], PACK_ID)
        self.assertEqual(subject["logical_sha256"], PACK_HASH)
        self.assertEqual(subject["population_scope"]["target_frame_count"], 4072)

    def test_gate_ready_before_state_is_pinned_in_activation_proposal(self):
        tx = self.proposal["proposed_operator_transaction_if_activated"]
        self.assertIsNone(tx["boundary_pack_registry"]["before"]["active_boundary_pack_id"])
        self.assertFalse(tx["boundary_pack_registry"]["before"]["production_pack_selected"])
        self.assertFalse(tx["boundary_pack_registry"]["before"]["active"])
        self.assertFalse(tx["authority_registry"]["before"]["active_c2e"])
        self.assertIsNone(tx["authority_registry"]["before"]["active_boundary_pack_id"])
        self.assertEqual(tx["candidate_pack_file_mutation"], "NONE")
        self.assertEqual(tx["runtime_code_mutation"], "NONE")

    def test_prerequisite_evidence_and_rollback_remain_preserved(self):
        self.assertEqual(self.ag2["decision"], "PASS")
        self.assertEqual(self.state["ag0_admissibility"], "PASS")
        self.assertEqual(self.state["ag1_replay_adequacy"], "PASS")
        self.assertEqual(self.state["ag2_comparative_review"], "PASS_FOR_EXACT_AG0_AG1_ADMITTED_PACK_AND_SCOPE_ONLY")
        rb = self.proposal["rollback_if_activated"]
        self.assertFalse(rb["authority_registry_target"]["active_c2e"])
        self.assertIsNone(rb["authority_registry_target"]["active_boundary_pack_id"])
        self.assertEqual(rb["deletion_or_history_rewrite"], "PROHIBITED")

    def test_no_downstream_authority_was_bundled_in_gate_ready_proposal(self):
        delta = self.gate["proposed_delta_if_activate_named_pack"]
        self.assertEqual(delta["canonical_or_r2_publication"], "NONE")
        self.assertEqual(delta["validation_consumption"], "NONE")
        self.assertEqual(delta["family_semantic_candidate_theory_promotion"], "NONE")
        self.assertEqual(delta["probability_risk_exposure_execution_agent_write"], "NONE")
        self.assertEqual(delta["scope_expansion"], "NONE")


if __name__ == "__main__":
    unittest.main()
