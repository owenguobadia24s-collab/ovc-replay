from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
WP1 = ROOT / "docs/programmes/grt-v0-2/wp1"
STATE_ROOT = ROOT / "registries/implementation/grt_v0_2"
REGISTRIES = ROOT / "registries/governance/grt_v0_2"


class GRT2WP1StateTests(unittest.TestCase):
    def test_wp0_merge_receipt_and_wp1_preflight_are_source_bound(self) -> None:
        merge = json.loads((WP1 / "GRT2_WP0_MERGE_RECEIPT.json").read_text(encoding="utf-8"))
        preflight = json.loads((WP1 / "GRT2_WP1_PREFLIGHT.json").read_text(encoding="utf-8"))
        self.assertEqual(merge["pull_request"], 726)
        self.assertEqual(merge["merge_commit"], "d41a29f9895482de0d1515efc2ca0aebf8016b45")
        self.assertEqual(merge["merge_tree"], "7f4fba22eec37ab7c257334fb6ac1624bd4bf23f")
        self.assertEqual(merge["authority_effect"], "NONE_PRE_ENFORCEMENT")
        self.assertEqual(preflight["baseline_commit"], merge["merge_commit"])
        self.assertEqual(preflight["baseline_tree"], merge["merge_tree"])
        self.assertEqual(preflight["constitution_status"], "PROPOSED_UNADMITTED")
        self.assertEqual(preflight["activation"], "INACTIVE")
        self.assertEqual(preflight["authority_effect"], "NONE_PRE_ENFORCEMENT")

    def test_programme_state_records_wp1_closeout_without_enforcement(self) -> None:
        pointer = json.loads((STATE_ROOT / "CURRENT_STATE_POINTER.json").read_text(encoding="utf-8"))
        state = json.loads((ROOT / pointer["current_state"]).read_text(encoding="utf-8"))
        constitution = json.loads(
            (REGISTRIES / "GRT_REPOSITORY_CONSTITUTION_v0_2.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(pointer["current_state"], "registries/implementation/grt_v0_2/OVC_GRT2_STATE_v0_3.json")
        self.assertEqual(pointer["status"], "RUNNING")
        self.assertEqual(pointer["next_packet"], "GRT2-WP2")
        self.assertEqual(state["status"], "APPROVED")
        self.assertEqual(state["packet_id"], "GRT2-WP1")
        self.assertEqual(state["gate_id"], "GRT2-G1")
        self.assertEqual(state["active_enforcement"], "NONE")
        self.assertIsNone(state["debt_floor_generation"])
        self.assertIsNone(state["debt_floor_hash"])
        self.assertEqual(state["constitution_hash"], constitution["canonical_hash"])
        self.assertEqual(state["constitution_status"], "PROPOSED_UNADMITTED")
        self.assertEqual(state["blockers"], [])
        self.assertEqual(state["qa_packet"], "docs/programmes/grt-v0-2/wp1/GRT2_WP1_QA_PACKET.json")
        self.assertEqual(state["decision_record"], "docs/programmes/grt-v0-2/wp1/GRT2_G1_DECISION.json")

    def test_wp1_closeout_does_not_claim_g2_g2_5_or_g3_completion(self) -> None:
        pointer = json.loads((STATE_ROOT / "CURRENT_STATE_POINTER.json").read_text(encoding="utf-8"))
        state = json.loads((ROOT / pointer["current_state"]).read_text(encoding="utf-8"))
        self.assertEqual(state["status"], "APPROVED")
        self.assertNotIn("GRT2-G2 PASS", state["prerequisites"])
        self.assertEqual(state["active_enforcement"], "NONE")
        self.assertIn("GRT2-G2.5 and GRT2-G3 remain reserved.", state["warnings"])


if __name__ == "__main__":
    unittest.main()
