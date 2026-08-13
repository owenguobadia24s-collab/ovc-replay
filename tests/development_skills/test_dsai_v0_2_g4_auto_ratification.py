from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
RELEASE = ROOT / "docs/releases/development-skills-architecture-v0-2/dsai2-wp4"
STATE_ROOT = ROOT / "registries/implementation/dsai_v0_2"
TERMINAL_TARGET = "IMPLEMENTED_ORCH345_BOUNDED_PARALLEL_BUILD_SERIAL_INTEGRATION_PORTFOLIO_DISPATCH"


class DSAI2G4AutoRatificationTests(unittest.TestCase):
    def _load(self, path: Path) -> dict:
        return json.loads(path.read_text(encoding="utf-8"))

    def test_wp4_qa_passes_all_bounded_pilot_acceptance_conditions(self) -> None:
        qa = self._load(RELEASE / "DSAI2_WP4_QA_PACKET.json")
        self.assertEqual(qa["status"], "PASS")
        self.assertEqual(qa["gate_id"], "DSAI2-G4")
        self.assertEqual(qa["gate_class"], "AUTO_RATIFIABLE")
        self.assertEqual(qa["authority_delta"], "NONE")
        self.assertEqual(qa["checks"]["false_parallel_allows"], 0)
        self.assertEqual(qa["checks"]["unresolved_conflict_classifications"], 0)
        self.assertEqual(qa["checks"]["parallel_merges"], 0)
        self.assertEqual(qa["checks"]["recorded_unresolved_s3"], 0)
        self.assertEqual(qa["checks"]["recorded_unresolved_s4"], 0)
        self.assertFalse(qa["checks"]["reserved_authority_crossed"])
        self.assertEqual(qa["workflow_evidence"]["tests"]["run_number"], 3932)
        self.assertEqual(qa["workflow_evidence"]["tiered"]["run_number"], 2276)
        self.assertEqual(qa["workflow_evidence"]["tiered"]["merge_readiness"], "success")
        self.assertEqual(qa["blocking_warnings"], [])
        self.assertEqual(qa["unresolved_issues"], [])
        self.assertEqual(qa["recommendation"], "PASS_AUTO_RATIFY_DSAI2_G4")

    def test_g4_delegated_pass_has_no_authority_effect(self) -> None:
        decision = self._load(RELEASE / "DSAI2_G4_DECISION.json")
        self.assertEqual(decision["decision"], "PASS")
        self.assertEqual(decision["status"], "APPROVED")
        self.assertEqual(decision["authority_required"], "DELEGATED_AUTO_RATIFICATION")
        self.assertEqual(decision["authority_delta"], "NONE")
        self.assertEqual(decision["authority_effect"], "NONE")
        self.assertEqual(decision["acceptance"]["false_parallel_allows"], 0)
        self.assertEqual(decision["acceptance"]["unresolved_conflict_classifications"], 0)
        self.assertEqual(decision["acceptance"]["parallel_merges"], 0)
        self.assertTrue(decision["acceptance"]["operator_wait_respected"])
        self.assertTrue(decision["acceptance"]["cross_programme_dependency_respected"])
        self.assertTrue(decision["acceptance"]["missing_prerequisite_blocked"])
        self.assertTrue(decision["acceptance"]["serialized_final_integration"])
        self.assertFalse(decision["acceptance"]["reserved_authority_crossed"])
        self.assertFalse(decision["authority_after_decision"]["parallel_merge"])
        self.assertEqual(decision["authority_after_decision"]["validation"], "DENIED")
        self.assertEqual(decision["authority_after_decision"]["reserved_scientific_execution_authority"], "NONE")

    def test_historical_g4_state_remains_immutable_while_live_pointer_may_advance(self) -> None:
        state = self._load(STATE_ROOT / "OVC_DSAI_V0_2_STATE_v0_6.json")
        self.assertEqual(state["status"], "APPROVED")
        self.assertEqual(state["packet_id"], "DSAI2-WP4")
        self.assertEqual(state["gate_id"], "DSAI2-G4")
        self.assertEqual(state["authority_delta"], "NONE")
        self.assertEqual(state["decision"], "PASS_DELEGATED_AUTO_RATIFIED")
        self.assertEqual(state["g4_acceptance"]["false_parallel_allows"], 0)
        self.assertEqual(state["g4_acceptance"]["unresolved_conflict_classifications"], 0)
        self.assertEqual(state["g4_acceptance"]["parallel_merges"], 0)
        self.assertIsNone(state["next_packet"])
        self.assertFalse(state["mandatory_stop"])
        self.assertEqual(state["target_terminal_state"], TERMINAL_TARGET)

        pointer = self._load(STATE_ROOT / "CURRENT_STATE_POINTER.json")
        self.assertIn(
            pointer["current_state"],
            {"OVC_DSAI_V0_2_STATE_v0_6.json", "OVC_DSAI_V0_2_STATE_v0_7.json"},
        )
        self.assertIsNone(pointer["next_packet"])
        if pointer["current_state"] == "OVC_DSAI_V0_2_STATE_v0_6.json":
            self.assertEqual(pointer["status"], "APPROVED")
        else:
            self.assertEqual(pointer["status"], "COMPLETED")
            terminal = self._load(STATE_ROOT / pointer["current_state"])
            self.assertEqual(terminal["status"], "COMPLETED")
            self.assertEqual(terminal["terminal"]["target_terminal_state"], TERMINAL_TARGET)
            self.assertTrue(terminal["terminal"]["programme_complete"])


if __name__ == "__main__":
    unittest.main()
