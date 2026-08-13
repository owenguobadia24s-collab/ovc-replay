from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
RELEASE = ROOT / "docs/releases/development-skills-architecture-throughput-20260813"
STATE = ROOT / "registries/implementation/dsai_throughput_20260813"


class DSAIThroughputG1Tests(unittest.TestCase):
    def _load(self, path: Path) -> dict:
        return json.loads(path.read_text(encoding="utf-8"))

    def test_g1_is_auto_ratified_without_governance_delta(self) -> None:
        qa = self._load(RELEASE / "DSAI_TE_WP1_QA_PACKET.json")
        decision = self._load(RELEASE / "DSAI_TE_G1_DECISION.json")
        self.assertEqual(qa["status"], "PASS")
        self.assertEqual(qa["gate_class"], "AUTO_RATIFIABLE")
        self.assertEqual(qa["authority_delta"], "NONE")
        self.assertEqual(qa["recommendation"], "PASS_AUTO_RATIFY_DSAI_TE_G1")
        self.assertEqual(qa["workflow_evidence"]["tests"]["run_number"], 3941)
        self.assertEqual(qa["workflow_evidence"]["tiered"]["run_number"], 2283)
        self.assertEqual(qa["workflow_evidence"]["tiered"]["merge_readiness"], "success")
        self.assertFalse(qa["checks"]["governance_broadening"])
        self.assertEqual(qa["blocking_warnings"], [])
        self.assertEqual(qa["unresolved_issues"], [])

        self.assertEqual(decision["decision"], "PASS")
        self.assertEqual(decision["status"], "APPROVED")
        self.assertEqual(decision["authority_required"], "DELEGATED_AUTO_RATIFICATION")
        self.assertEqual(decision["authority_delta"], "NONE")
        self.assertEqual(decision["authority_effect"], "NONE")
        self.assertEqual(decision["operational_capacity_after_merge"]["max_parallel_builds"], 4)
        self.assertEqual(decision["operational_capacity_after_merge"]["max_train_packets"], 8)
        self.assertEqual(decision["operational_capacity_after_merge"]["max_auto_requeue_attempts"], 2)
        self.assertFalse(decision["boundaries"]["parallel_merge"])
        self.assertEqual(decision["governance_broadening"], "DEFERRED_TO_END_OF_DAY_OPERATOR_ASSESSMENT")

    def test_programme_state_waits_only_for_integration(self) -> None:
        state = self._load(STATE / "OVC_DSAI_THROUGHPUT_STATE_v0_2.json")
        pointer = self._load(STATE / "CURRENT_STATE_POINTER.json")
        self.assertEqual(state["status"], "APPROVED")
        self.assertEqual(state["authority_delta"], "NONE")
        self.assertIsNone(state["merge_commit"])
        self.assertIsNone(state["next_packet"])
        self.assertFalse(state["mandatory_stop"])
        self.assertEqual(pointer["current_state"], "OVC_DSAI_THROUGHPUT_STATE_v0_2.json")
        self.assertEqual(pointer["status"], "APPROVED")
        self.assertIsNone(pointer["next_packet"])


if __name__ == "__main__":
    unittest.main()
