from __future__ import annotations

import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
PROGRAMME_STATE = ROOT / "records" / "development" / "dsai3v" / "DSAI3V_REMOTE_POST_MERGE_PROGRAMME_STATE_v0_1.json"
PASS_PROOF = ROOT / "docs" / "programmes" / "dsai3v-remote-post-merge" / "DSAI3V_REMOTE_LIVE_CUTOVER_PROOF_PASS_v0_1.json"
DECISION = ROOT / "docs" / "programmes" / "dsai3v-remote-post-merge" / "DSAI3V_REMOTE_LIVE_CUTOVER_PROOF_DECISION_v0_1.json"
RECOVERY = ROOT / "registries" / "development" / "skills" / "VIT_POST_MERGE_RECOVERY_REQUESTS_v0_1.json"


class Dsai3vRemotePostMergeTerminalCloseoutTests(unittest.TestCase):
    def test_programme_state_is_terminal_and_authority_inert(self) -> None:
        state = json.loads(PROGRAMME_STATE.read_text(encoding="utf-8"))
        self.assertEqual(state["programme_id"], "OVC-DSAI3V-REMOTE-POST-MERGE-0001")
        self.assertEqual(state["packet_id"], "DSAI3V-REMOTE-LIVE-CUTOVER-PROOF")
        self.assertEqual(state["status"], "COMPLETED")
        self.assertEqual(state["authority_delta"], "NONE")
        self.assertEqual(state["blockers"], [])
        self.assertIsNone(state["next_packet"])
        self.assertEqual(state["candidate_commit"], "9ba634e7c3c45bf6ebe8c344e8a276aa492685ae")
        self.assertEqual(state["candidate_tree"], "e657a807bd2bb12db85f0832f52e493a4b032080")

    def test_live_proof_satisfies_remote_cutover_acceptance(self) -> None:
        proof = json.loads(PASS_PROOF.read_text(encoding="utf-8"))
        self.assertEqual(proof["status"], "PASS")
        self.assertEqual(proof["observed_main_commit"], "9ba634e7c3c45bf6ebe8c344e8a276aa492685ae")
        self.assertEqual(proof["observed_main_tree"], "e657a807bd2bb12db85f0832f52e493a4b032080")
        self.assertEqual(proof["live_remote_workflow"]["run_id"], 33929736378)
        self.assertEqual(proof["live_remote_workflow"]["job_id"], 101205729214)
        self.assertEqual(proof["live_remote_workflow"]["conclusion"], "success")
        self.assertEqual(proof["live_remote_workflow"]["runner_class"], "GITHUB_HOSTED")
        self.assertIs(proof["live_remote_workflow"]["operator_device_required"], False)
        current = proof["current_main_completion_proof"]
        self.assertIs(current["exact_tree_equal"], True)
        self.assertIs(current["four_content_addressed_receipts_present"], True)
        self.assertEqual(current["authority_effect"], "NONE")
        remote = proof["remote_publication"]
        self.assertEqual(remote["report_id"], "e50d40a93eddf347e4a63317ea4a346e1f8f6bb15e28804deff3986e5cae67e0")
        self.assertEqual(remote["object_count"], 102)
        self.assertIs(remote["readback_verified"], True)
        self.assertIs(remote["delete"], False)
        self.assertIs(remote["overwrite"], False)
        self.assertEqual(proof["qa"]["recommendation"], "PASS")
        self.assertEqual(proof["qa"]["blockers"], [])
        self.assertIsNone(proof["next_packet"])

    def test_cutover_recovery_row_is_retired_but_historical_row_remains(self) -> None:
        manifest = json.loads(RECOVERY.read_text(encoding="utf-8"))
        rows = {row["merge_sha"]: row for row in manifest["requests"]}
        self.assertIn("b22ea057ddef98acc2e43dfff689b7fa56934385", rows)
        self.assertEqual(rows["b22ea057ddef98acc2e43dfff689b7fa56934385"]["authority_effect"], "NONE")
        self.assertNotIn("49d2bc7a36e3e8754eb9d26eed750d2d481a2eb2", rows)

    def test_delegated_terminal_decision_is_pass_without_reserved_delta(self) -> None:
        decision = json.loads(DECISION.read_text(encoding="utf-8"))
        self.assertEqual(decision["decision"], "PASS")
        self.assertEqual(decision["operator_gate_decision"], "PASS")
        self.assertEqual(decision["authority_delta"], "NONE")
        self.assertEqual(decision["authority_effect"], "NONE")
        self.assertIs(decision["terminal"], True)
        self.assertIsNone(decision["next_packet"])
        self.assertEqual(decision["unresolved_issues"], [])


if __name__ == "__main__":
    unittest.main()
