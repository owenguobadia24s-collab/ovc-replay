import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "registries/implementation/c2e_v0_2"
RA = BASE / "run_authority"
REL = ROOT / "docs/releases/c2e-causal-episode-v0-2/c2e-ag1-gap-001"

R2 = "C2E2.G6.R2.TOKEN.bafe14574ee86332a2249715"
R3 = "C2E2.G6.R3.TOKEN.88ae5eba91c0daecaffa9bcc"
R4 = "C2E2.G6.R4.TOKEN.107511621acc919cb26a4cb6"
POP = "46f02ed89c9c4a3d4b3ef2046b7aa32489c5b63a526dbb8151896331d0ae896d"
PACK = "C2E.BOUNDARY.PACK.043c628a3a29372ae478026db307d0d8"
HARNESS = "c5dd709841c6dc20290e5182d955f3c6363586a4"

def j(path):
    return json.loads(path.read_text())

class C2EAG1CorrectiveR3AuthorityTests(unittest.TestCase):
    def test_failed_r2_attempt_is_preserved_and_token_cannot_be_reused(self):
        failure = j(REL / "C2E_AG1_RESTART_R2_FAILED_ATTEMPT.json")
        consumed = j(RA / "C2E2_G6_RUN_AUTH_R2_TOKEN_CONSUMED_ATTEMPT1.json")
        self.assertEqual(failure["token_id"], R2)
        self.assertEqual(failure["failure_class"], "CORRECTABLE_EXECUTION_DRIVER_INVOCATION_DEFECT")
        self.assertFalse(failure["scientific_evidence_accepted"])
        self.assertEqual(consumed["status"], "CONSUMED_FAILED_ATTEMPT")
        self.assertTrue(consumed["consumed"])
        self.assertTrue(consumed["reuse_prohibited"])

    def test_r3_authority_record_remains_historical_and_failed_attempt_is_append_only(self):
        gate = j(REL / "C2E2_G6_RUN_AUTH_R3_GATE_PACKET.json")
        token = j(RA / "C2E2_G6_RUN_AUTH_R3_TOKEN_AUTHORIZED.json")
        decision = j(REL / "C2E2_G6_RUN_AUTH_R3_OPERATOR_DECISION.json")
        failure = j(REL / "C2E_AG1_RESTART_R3_FAILED_ATTEMPT.json")
        consumed = j(RA / "C2E2_G6_RUN_AUTH_R3_TOKEN_CONSUMED_ATTEMPT1.json")
        self.assertEqual(gate["recommended_decision"], "PASS")
        self.assertEqual(decision["decision"], "PASS")
        self.assertEqual(token["token_id"], R3)
        self.assertEqual(token["logical_population_sha256"], POP)
        self.assertEqual(token["boundary_pack_id"], PACK)
        self.assertEqual(failure["token_id"], R3)
        self.assertEqual(failure["failure_class"], "PRE_EXECUTION_BINDING_DRIFT_NOT_ENFORCED_BEFORE_START")
        self.assertFalse(failure["scientific_evidence_accepted"])
        self.assertEqual(consumed["status"], "CONSUMED_FAILED_ATTEMPT")
        self.assertTrue(consumed["reuse_prohibited"])

    def test_r4_is_exact_second_corrective_retry_and_uses_bound_harness(self):
        gate = j(REL / "C2E2_G6_RUN_AUTH_R4_GATE_PACKET.json")
        token = j(RA / "C2E2_G6_RUN_AUTH_R4_TOKEN_AUTHORIZED.json")
        decision = j(REL / "C2E2_G6_RUN_AUTH_R4_OPERATOR_DECISION.json")
        self.assertEqual(gate["recommended_decision"], "PASS")
        self.assertEqual(decision["decision"], "PASS")
        self.assertEqual(token["token_id"], R4)
        self.assertEqual(token["status"], "AUTHORIZED_UNCONSUMED")
        self.assertEqual(token["logical_population_sha256"], POP)
        self.assertEqual(token["boundary_pack_id"], PACK)
        self.assertEqual(token["restart_harness_git_blob_sha"], HARNESS)
        self.assertEqual(gate["corrective_basis"]["repository_science_change"], "NONE")
        self.assertEqual(gate["corrective_basis"]["source_population_change"], "NONE")
        self.assertEqual(gate["corrective_basis"]["boundary_pack_change"], "NONE")

    def test_parent_ag1_pointer_remains_lawful_as_r4_and_later_gates_progress(self):
        p = j(BASE / "CURRENT_STATE_POINTER.json")
        self.assertEqual(p["failed_restart_token_status"], "CONSUMED_FAILED_ATTEMPT_REUSE_PROHIBITED")
        self.assertEqual(p["failed_restart_r3_token_status"], "CONSUMED_FAILED_ATTEMPT_REUSE_PROHIBITED")
        if p["authoritative_state"].endswith("OVC_C2E2_STATE_v0_33.json"):
            self.assertEqual(p["active_c2e"], "NONE")
            self.assertEqual(p["active_boundary_pack"], "NONE")
            self.assertEqual(p["current_gate"], "C2E-AG1")
            self.assertEqual(p["status"], "GATE_READY")
            self.assertTrue(p["operator_decision_required"])
            self.assertEqual(p["blocking_operator_subgate"], "C2E2-G6-RUN-AUTH-R4")
            self.assertFalse(p["blocking_operator_subgate_decision_required"])
            self.assertEqual(p["blocking_operator_subgate_decision"], "PASS")
            self.assertEqual(p["restart_token_proposal_id"], R4)
            self.assertEqual(p["restart_token_proposal_status"], "AUTHORIZED_UNCONSUMED")
        elif p["authoritative_state"].endswith("OVC_C2E2_STATE_v0_38.json"):
            self.assertEqual(p["active_c2e"], "NONE")
            self.assertEqual(p["active_boundary_pack"], "NONE")
            self.assertEqual(p["status"], "APPROVED")
            self.assertEqual(p["current_gate"], "C2E-AG1")
            self.assertFalse(p["operator_decision_required"])
            self.assertEqual(p["operator_decision"], "PASS")
            self.assertEqual(p["restart_token_id"], R4)
            self.assertEqual(p["restart_token_status"], "CONSUMED_SUCCESS_REUSE_PROHIBITED")
            self.assertEqual(p["ag1_replay_adequacy"], "PASS")
            self.assertEqual(p["next_gate"], "C2E-AG2")
        elif p["authoritative_state"].endswith("OVC_C2E2_STATE_v0_42_AG2_COMPLETED.json"):
            self.assertEqual(p["active_c2e"], "NONE")
            self.assertEqual(p["active_boundary_pack"], "NONE")
            self.assertEqual(p["status"], "COMPLETED")
            self.assertEqual(p["current_gate"], "C2E-AG2")
            self.assertFalse(p["operator_decision_required"])
            self.assertEqual(p["operator_decision"], "PASS")
            self.assertEqual(p["restart_token_id"], R4)
            self.assertEqual(p["restart_token_status"], "CONSUMED_SUCCESS_REUSE_PROHIBITED")
            self.assertEqual(p["ag1_replay_adequacy"], "PASS")
            self.assertEqual(p["ag2_progression"], "COMPLETED_PASS")
            self.assertEqual(p["next_gate"], "C2E-AG3")
            self.assertEqual(p["ag3"], "NOT_EXECUTED")
        elif p["authoritative_state"].endswith("OVC_C2E2_STATE_v0_43_AG3_GATE_READY.json"):
            self.assertEqual(p["active_c2e"], "NONE")
            self.assertEqual(p["active_boundary_pack"], "NONE")
            self.assertEqual(p["status"], "GATE_READY")
            self.assertEqual(p["current_gate"], "C2E-AG3")
            self.assertTrue(p["operator_decision_required"])
            self.assertEqual(p["restart_token_id"], R4)
            self.assertEqual(p["restart_token_status"], "CONSUMED_SUCCESS_REUSE_PROHIBITED")
            self.assertEqual(p["ag1_replay_adequacy"], "PASS")
            self.assertEqual(p["ag2_progression"], "COMPLETED_PASS")
            self.assertEqual(p["next_gate"], "C2E-AG3")
            self.assertEqual(p["ag3"], "NOT_EXECUTED")
        else:
            self.assertEqual(p["authoritative_state"], "registries/implementation/c2e_v0_2/OVC_C2E2_STATE_v0_44_AG3_COMPLETED.json")
            self.assertEqual(p["status"], "COMPLETED")
            self.assertEqual(p["current_gate"], "C2E-AG3")
            self.assertFalse(p["operator_decision_required"])
            self.assertEqual(p["operator_decision"], "ACTIVATE_NAMED_PACK")
            self.assertEqual(p["restart_token_id"], R4)
            self.assertEqual(p["restart_token_status"], "CONSUMED_SUCCESS_REUSE_PROHIBITED")
            self.assertEqual(p["ag1_replay_adequacy"], "PASS")
            self.assertEqual(p["ag2_progression"], "COMPLETED_PASS")
            self.assertEqual(p["ag3"], "EXECUTED_PASS_ACTIVATE_NAMED_PACK")
            self.assertEqual(p["active_c2e"], "ACTIVE_EXACT_NAMED_PACK_SCOPE_BOUND")
            self.assertEqual(p["active_boundary_pack"], PACK)
            self.assertIsNone(p["next_gate"])

if __name__ == "__main__":
    unittest.main()
