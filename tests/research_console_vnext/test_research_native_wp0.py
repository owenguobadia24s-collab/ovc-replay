from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ART = ROOT / "artifacts/research_console_vnext/research_native"
STATE = ROOT / "registries/implementation/research_console_vnext/OVC_RCN_RN_STATE_v0_2.json"
G4 = ROOT / "artifacts/research_console_vnext/pvs3/RCN_RN_G4_GATE_PACKET.json"
G4_DECISION = ROOT / "artifacts/research_console_vnext/pvs3/RCN_RN_G4_OPERATOR_DECISION.json"
POST_G4_RECEIPT = ROOT / "artifacts/research_console_vnext/pvs3/RCN_RN_POST_G4_SOURCE_BINDING_MERGE_RECEIPT.json"


def load_artifact(name: str):
    return json.loads((ART / name).read_text(encoding="utf-8"))


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


class ResearchNativeWP0Tests(unittest.TestCase):
    def test_ratification_identity_and_authority(self):
        record = load_artifact("RCN_RN_G0_RATIFICATION_RECORD.json")
        self.assertEqual(record["plan_id"], "OVC-RCN-RESEARCH-NATIVE-IMPLEMENTATION-PLAN-0.2-RATIFIED")
        self.assertEqual(record["plan_sha256"], "c6d5d433b11582ceacaa4bbc2ab63109b3f8a40baab2f18ca13002a7fb65a930")
        self.assertEqual(record["operator_decision"], "PASS")
        self.assertNotIn("REAL_SOURCE", record["repository_effect"])

    def test_admission_is_complete(self):
        checklist = load_artifact("RCN_RN_ADMISSION_CHECKLIST.json")
        self.assertEqual(checklist["overall"], "PASS")
        self.assertEqual(len(checklist["items"]), 11)
        self.assertTrue(all(item["result"] == "PASS" for item in checklist["items"]))

    def test_supersession_preserves_history_and_blocks_legacy_gate_merge(self):
        ledger = load_artifact("RCN_RN_SUPERSESSION_LEDGER.json")
        self.assertTrue(ledger["pr_545"]["merge_prohibited"])
        self.assertIn("PRESERV", ledger["forward_rule"].upper())

    def test_chart_census_performs_no_removal(self):
        census = load_artifact("RCN_RN_CHART_DEPENDENCY_CENSUS.json")
        self.assertFalse(census["removal_performed"])
        self.assertEqual(census["acceptance"], "PASS_NO_REMOVAL")

    def test_programme_state_preserves_bounded_g4_authority_across_generations(self):
        current = load(STATE)
        post_g4 = load(POST_G4_RECEIPT)
        operator_decision = load(G4_DECISION)

        self.assertEqual("ovc-rcn-rn-programme-state/v2", current["schema"])
        self.assertEqual([], current["blockers"])
        self.assertEqual("NONE", current["authority_delta"])
        self.assertEqual(
            "G4_APPROVED_READ_ONLY_REAL_SOURCE_INVESTIGATE_PRESENTATION_MARKET_C1_C2_C2E",
            current["current_authority"],
        )
        self.assertIn("OTHERS_DENIED", current["real_source_routes"])
        self.assertEqual(
            "artifacts/research_console_vnext/pvs3/RCN_RN_G4_OPERATOR_DECISION.json",
            current["operator_decision_record"],
        )
        self.assertTrue(current["packet_id"].startswith("RCN-RN-"))
        self.assertTrue(G4.exists())
        self.assertEqual("PASS", operator_decision["decision"])

        self.assertEqual("RCN-RN-POST-G4-SOURCE-BINDING", post_g4["packet_id"])
        self.assertEqual("COMPLETED", post_g4["status"])
        self.assertEqual("NONE", post_g4["authority_delta"])
        self.assertEqual("RCN-RN-WP5A", post_g4["next_packet_named"])
        self.assertEqual(
            post_g4["authority_after_merge"],
            current["current_authority"],
        )
        self.assertEqual(post_g4["real_source_routes"], current["real_source_routes"])


if __name__ == "__main__":
    unittest.main()
