import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / "registries/implementation/c2e_v0_2"
RA = BASE / "run_authority"
REL = ROOT / "docs/releases/c2e-causal-episode-v0-2/c2e-ag1-gap-001"

R2 = "C2E2.G6.R2.TOKEN.bafe14574ee86332a2249715"
R3 = "C2E2.G6.R3.TOKEN.88ae5eba91c0daecaffa9bcc"
POP = "46f02ed89c9c4a3d4b3ef2046b7aa32489c5b63a526dbb8151896331d0ae896d"
PACK = "C2E.BOUNDARY.PACK.043c628a3a29372ae478026db307d0d8"

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

    def test_r3_is_exact_corrective_retry_with_no_science_or_scope_change(self):
        gate = j(REL / "C2E2_G6_RUN_AUTH_R3_GATE_PACKET.json")
        token = j(RA / "C2E2_G6_RUN_AUTH_R3_TOKEN_AUTHORIZED.json")
        decision = j(REL / "C2E2_G6_RUN_AUTH_R3_OPERATOR_DECISION.json")
        self.assertEqual(gate["recommended_decision"], "PASS")
        self.assertEqual(decision["decision"], "PASS")
        self.assertEqual(token["token_id"], R3)
        self.assertEqual(token["status"], "AUTHORIZED_UNCONSUMED")
        self.assertEqual(token["logical_population_sha256"], POP)
        self.assertEqual(token["boundary_pack_id"], PACK)
        self.assertEqual(gate["corrective_basis"]["repository_science_change"], "NONE")
        self.assertEqual(gate["corrective_basis"]["source_population_change"], "NONE")
        self.assertEqual(gate["corrective_basis"]["boundary_pack_change"], "NONE")

    def test_parent_ag1_pointer_remains_authoritative_while_r3_is_exposed(self):
        p = j(BASE / "CURRENT_STATE_POINTER.json")
        self.assertEqual(p["authoritative_state"], "registries/implementation/c2e_v0_2/OVC_C2E2_STATE_v0_33.json")
        self.assertEqual(p["current_gate"], "C2E-AG1")
        self.assertEqual(p["status"], "GATE_READY")
        self.assertTrue(p["operator_decision_required"])
        self.assertEqual(p["blocking_operator_subgate"], "C2E2-G6-RUN-AUTH-R3")
        self.assertFalse(p["blocking_operator_subgate_decision_required"])
        self.assertEqual(p["blocking_operator_subgate_decision"], "PASS")
        self.assertEqual(p["restart_token_proposal_id"], R3)
        self.assertEqual(p["restart_token_proposal_status"], "AUTHORIZED_UNCONSUMED")
        self.assertEqual(p["failed_restart_token_status"], "CONSUMED_FAILED_ATTEMPT_REUSE_PROHIBITED")
        self.assertEqual(p["active_c2e"], "NONE")
        self.assertEqual(p["active_boundary_pack"], "NONE")

if __name__ == "__main__":
    unittest.main()
