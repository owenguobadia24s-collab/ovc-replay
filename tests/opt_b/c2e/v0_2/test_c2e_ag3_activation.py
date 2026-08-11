import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[4]
AG3 = ROOT / "docs/releases/c2e-causal-episode-v0-2/c2e-ag3"
BASE = ROOT / "registries/implementation/c2e_v0_2"
PACK = ROOT / "registries/opt_b/c2e/v0_2/C2E_EMPIRICAL_BOUNDARY_PACK_JUNE_STABLE_v0_2.json"
PACK_REGISTRY = ROOT / "registries/opt_b/c2e/v0_2/C2E_BOUNDARY_PACK_REGISTRY_v0_2.json"
AUTH_REGISTRY = ROOT / "registries/opt_b/c2e/v0_2/C2E_AUTHORITY_REGISTRY_v0_2.json"

PACK_ID = "C2E.BOUNDARY.PACK.043c628a3a29372ae478026db307d0d8"
PACK_HASH = "043c628a3a29372ae478026db307d0d8b2347fcbbc7b06dbb1a3cc345c86e313"
DECISION_ID = "C2E-AG3.OPERATOR.ACTIVATE_NAMED_PACK.20260811T220500+0100"


def load(path):
    return json.loads(path.read_text())


class C2EAG3ActivationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.decision = load(AG3 / "C2E_AG3_OPERATOR_ACTIVATE_NAMED_PACK_DECISION.json")
        cls.receipt = load(AG3 / "C2E_AG3_ACTIVATION_RECEIPT.json")
        cls.state = load(BASE / "OVC_C2E2_STATE_v0_44_AG3_COMPLETED.json")
        cls.pointer = load(BASE / "CURRENT_STATE_POINTER.json")
        cls.pack = load(PACK)
        cls.pack_registry = load(PACK_REGISTRY)
        cls.auth_registry = load(AUTH_REGISTRY)

    def test_operator_decision_is_exact_and_scope_bound(self):
        self.assertEqual(self.decision["decision_id"], DECISION_ID)
        self.assertEqual(self.decision["decision"], "ACTIVATE_NAMED_PACK")
        self.assertEqual(self.decision["operator_instruction"], "OVC APPROVE C2E-AG3 ACTIVATE_NAMED_PACK")
        self.assertEqual(self.decision["boundary_pack_id"], PACK_ID)
        self.assertEqual(self.decision["boundary_pack_logical_sha256"], PACK_HASH)
        self.assertEqual(self.decision["scope"]["target_frame_count"], 4072)
        self.assertEqual(self.decision["scope"]["instrument_id"], "GBPUSD")

    def test_selector_and_authority_registries_apply_exact_transaction(self):
        self.assertEqual(self.pack_registry["active_boundary_pack_id"], PACK_ID)
        self.assertTrue(self.pack_registry["production_pack_selected"])
        self.assertTrue(self.pack_registry["active"])
        self.assertFalse(self.pack_registry["canonical"])
        self.assertTrue(self.auth_registry["active_c2e"])
        self.assertEqual(self.auth_registry["active_boundary_pack_id"], PACK_ID)
        self.assertEqual(self.auth_registry["implementation_state"], "ACTIVE_C2E_NAMED_PACK_OPERATOR_SELECTED_AG3")
        self.assertEqual(self.auth_registry["real_source_replay"], "COMPLETED_EXACT_AG_EVIDENCE")

    def test_candidate_pack_bytes_and_internal_authority_remain_unchanged(self):
        self.assertEqual(self.pack["boundary_pack_id"], PACK_ID)
        self.assertEqual(self.pack["logical_sha256"], PACK_HASH)
        self.assertEqual(self.pack["authority"], "CANDIDATE")
        self.assertFalse(self.pack["active"])
        self.assertFalse(self.pack["canonical"])
        self.assertEqual(self.receipt["candidate_pack_file_mutation"], "NONE")
        self.assertEqual(self.receipt["runtime_code_mutation"], "NONE")

    def test_programme_state_is_completed_and_pointer_is_active(self):
        self.assertEqual(self.state["status"], "COMPLETED")
        self.assertEqual(self.state["operator_decision"], "ACTIVATE_NAMED_PACK")
        self.assertEqual(self.state["ag3"], "EXECUTED_PASS_ACTIVATE_NAMED_PACK")
        self.assertEqual(self.state["active_boundary_pack"], PACK_ID)
        self.assertEqual(self.pointer["authoritative_state"], "registries/implementation/c2e_v0_2/OVC_C2E2_STATE_v0_44_AG3_COMPLETED.json")
        self.assertEqual(self.pointer["status"], "COMPLETED")
        self.assertEqual(self.pointer["operator_decision"], "ACTIVATE_NAMED_PACK")
        self.assertEqual(self.pointer["ag3"], "EXECUTED_PASS_ACTIVATE_NAMED_PACK")
        self.assertEqual(self.pointer["active_boundary_pack"], PACK_ID)
        self.assertIn(DECISION_ID, self.pointer["operator_decision_history"])

    def test_downstream_authority_remains_denied_or_none(self):
        self.assertEqual(self.auth_registry["publication"], "DENIED")
        self.assertEqual(self.auth_registry["validation"], "DENIED")
        self.assertEqual(self.auth_registry["family_semantic_probability_risk_exposure_execution"], "NONE")
        self.assertEqual(self.auth_registry["agent_write"], "NONE")
        delta = self.decision["authority_delta"]
        self.assertEqual(delta["canonical_or_r2_publication"], "NONE")
        self.assertEqual(delta["validation_consumption"], "NONE")
        self.assertEqual(delta["family_semantic_candidate_theory_promotion"], "NONE")
        self.assertEqual(delta["probability_risk_exposure_execution_agent_write"], "NONE")
        self.assertEqual(delta["scope_expansion"], "NONE")

    def test_rollback_is_non_destructive(self):
        rb = self.receipt["rollback"]
        self.assertIsNone(rb["boundary_pack_registry"]["active_boundary_pack_id"])
        self.assertFalse(rb["boundary_pack_registry"]["production_pack_selected"])
        self.assertFalse(rb["authority_registry"]["active_c2e"])
        self.assertIsNone(rb["authority_registry"]["active_boundary_pack_id"])
        self.assertEqual(rb["evidence_preservation"], "REQUIRED")
        self.assertEqual(rb["deletion_or_history_rewrite"], "PROHIBITED")


if __name__ == "__main__":
    unittest.main()
