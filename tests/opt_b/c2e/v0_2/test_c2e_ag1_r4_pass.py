import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[4]
BASE=ROOT/"registries/implementation/c2e_v0_2"
REL=ROOT/"docs/releases/c2e-causal-episode-v0-2"

def j(p): return json.loads(p.read_text())

class C2EAG1R4PassTests(unittest.TestCase):
    def test_r4_restart_equivalence_resolves_gap(self):
        r=j(REL/"c2e-ag1-gap-001/C2E_AG1_GAP_001_RESOLUTION.json")
        self.assertEqual(r["status"],"RESOLVED_PASS")
        self.assertEqual(r["scientific_artifact_equivalence"],"PASS_BYTE_IDENTICAL_TO_WP6_RUN_A_AND_RUN_B")
        self.assertEqual(r["frame_count"],4072)
        self.assertEqual(r["stream_record_count"],16550)
        self.assertEqual(r["checkpoint_semantic_prefix_hash"],"4dc0af22d802272ced022cb4e8d7769b4a5e06cf268bb872cb90dbf1276f4f5e")
    def test_r4_token_consumed_and_external_evidence_persisted(self):
        t=j(BASE/"run_authority/C2E2_G6_RUN_AUTH_R4_TOKEN_CONSUMED_SUCCESS.json")
        e=j(REL/"c2e-ag1-gap-001/C2E_AG1_RESTART_R4_EXTERNAL_ARTIFACT_MANIFEST.json")
        self.assertEqual(t["status"],"CONSUMED_SUCCESS")
        self.assertTrue(t["reuse_prohibited"])
        self.assertEqual(e["drive_file_id"],"1HqFnXU2AkI0NZZF87WSn4OrCBcQwQNUS")
        self.assertEqual(e["sha256"],"0d9ada4b409345c143d10d015d1db4820c9ee89bf2904d0251c5a30f00284214")
    def test_ag1_pass_only_allows_later_ag_progression_without_activation(self):
        d=j(REL/"c2e-ag1/C2E_AG1_OPERATOR_PASS_DECISION.json")
        p=j(BASE/"CURRENT_STATE_POINTER.json")
        self.assertEqual(d["decision"],"PASS")
        self.assertEqual(d["authority_delta"]["ag2_progression"],"AUTHORIZED_FOR_GATE_PREPARATION_ONLY")
        self.assertEqual(d["authority_delta"]["active_c2e"],"NONE")
        self.assertEqual(p["ag1_replay_adequacy"],"PASS")
        self.assertIn(p["next_gate"],{"C2E-AG2","C2E-AG3"})
        if p["next_gate"] == "C2E-AG3":
            self.assertEqual(p["ag2_progression"],"COMPLETED_PASS")
            self.assertEqual(p["ag3"],"NOT_EXECUTED")
        self.assertEqual(p["active_c2e"],"NONE")
        self.assertEqual(p["active_boundary_pack"],"NONE")

if __name__=="__main__": unittest.main()
