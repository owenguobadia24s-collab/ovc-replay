from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ART = ROOT / "artifacts" / "research_console_vnext" / "research_native"
STATE = ROOT / "registries" / "implementation" / "research_console_vnext" / "OVC_RCN_RN_STATE_v0_2.json"


def load(name: str):
    return json.loads((ART / name).read_text(encoding="utf-8"))


class ResearchNativeWP0Tests(unittest.TestCase):
    def test_ratification_identity_and_authority(self):
        r = load("RCN_RN_G0_RATIFICATION_RECORD.json")
        self.assertEqual(r["plan_id"], "OVC-RCN-RESEARCH-NATIVE-IMPLEMENTATION-PLAN-0.2-RATIFIED")
        self.assertEqual(r["plan_sha256"], "c6d5d433b11582ceacaa4bbc2ab63109b3f8a40baab2f18ca13002a7fb65a930")
        self.assertEqual(r["governing_design_sha256"], "d147c1df4ab92cdadec265126a12313f314566dbea72d451abb2fa7fbd1fc013")
        self.assertEqual(r["operator_decision"], "PASS")
        self.assertNotIn("REAL_SOURCE", r["repository_effect"])

    def test_admission_is_complete(self):
        c = load("RCN_RN_ADMISSION_CHECKLIST.json")
        self.assertEqual(c["overall"], "PASS")
        self.assertEqual(len(c["items"]), 11)
        self.assertTrue(all(x["result"] == "PASS" for x in c["items"]))

    def test_supersession_preserves_history_and_blocks_legacy_gate_merge(self):
        s = load("RCN_RN_SUPERSESSION_LEDGER.json")
        self.assertTrue(s["pr_545"]["merge_prohibited"])
        self.assertIn("PRESERV", s["forward_rule"].upper())
        self.assertGreaterEqual(len(s["retained_foundations"]), 3)

    def test_chart_census_performs_no_removal(self):
        c = load("RCN_RN_CHART_DEPENDENCY_CENSUS.json")
        self.assertFalse(c["removal_performed"])
        self.assertEqual(c["acceptance"], "PASS_NO_REMOVAL")

    def test_state_preserves_wp3e_g3v_boundary_and_keeps_real_sources_denied(self):
        s = json.loads(STATE.read_text(encoding="utf-8"))
        self.assertEqual(s["schema"], "ovc-rcn-rn-programme-state/v2")
        self.assertEqual(s["real_source_routes"], "DENIED_UNTIL_RCN_RN_G4")
        self.assertEqual(s["current_authority"], "FIXTURE_ONLY_LOCAL_READ_ONLY")
        self.assertEqual(s["blockers"], [])

        if s["packet_id"] == "RCN-RN-WP3E":
            self.assertEqual(s["status"], "WP3E_ADMITTED_READY")
            self.assertEqual(s["next_packet"], "RCN-RN-G3V_FINAL_ONLY_AFTER_WP3E_CONVERGENCE")
            self.assertEqual(s["stop_boundary"], "TYPED_WP3E_STOP_OR_FINAL_G3V_READY")
            self.assertEqual(s["g3v"], "DEFERRED")
            self.assertEqual(s["wp4_g4"], "NOT_ADMITTED_WHILE_WP3E_OPEN")
            self.assertEqual(s["authority_delta"], "NONE")
            return

        self.assertEqual(s["packet_id"], "RCN-RN-G3V")
        if s["status"] == "GATE_READY":
            self.assertEqual(s["next_packet"], "RCN-RN-G3V_OPERATOR_DECISION")
            self.assertEqual(s["stop_boundary"], "RCN-RN-G3V_OPERATOR_DECISION")
            self.assertEqual(s["g3v"], "READY_FOR_FINAL_OPERATOR_ACCEPTANCE")
            self.assertEqual(s["wp4_g4"], "NOT_ADMITTED_PENDING_G3V_OPERATOR_DECISION")
            self.assertEqual(s["authority_required"], "OPERATOR_REQUIRED")
            self.assertIn("NO_REAL_SOURCE_AUTHORITY", s["authority_delta"])
        else:
            self.assertEqual(s["status"], "APPROVED")
            self.assertEqual(s["g3v"], "PASS")
            self.assertEqual(s["next_packet"], "RCN-RN-WP4A_PREPARATION")
            self.assertEqual(s["stop_boundary"], "RCN-RN-G4_BEFORE_FIRST_REAL_SOURCE_PRESENTATION")
            self.assertEqual(s["preparation_authority"], "RCN-RN-WP4A_D_PREPARATION_PERMITTED")
            self.assertEqual(s["authority_required"], "OPERATOR_REQUIRED_SATISFIED")
            self.assertIn("NO_REAL_SOURCE_AUTHORITY", s["authority_delta"])
            self.assertIn("REAL_SOURCE_PRESENTATION_DENIED_PENDING_G4", s["wp4_g4"])
            decision = load("RCN_RN_G3V_OPERATOR_PASS_DECISION.json")
            self.assertEqual(decision["decision"], "PASS")
            self.assertEqual(decision["operator_command"], "OVC APPROVE RCN-RN-G3V PASS")
            self.assertEqual(decision["real_source_routes"], "DENIED_UNTIL_SEPARATE_RCN_RN_G4_OPERATOR_PASS")


if __name__ == "__main__":
    unittest.main()
