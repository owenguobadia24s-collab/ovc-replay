from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest

from ovc.development.skills.vit_core import ContinuousExecutionMandate, DevelopmentLane
from ovc.development.skills.vit_runtime import DurableExecutionStore, PersistentExecutionState, RecoveryState, drain_state, recovery_transition

class DsaiVitV03Wp4Tests(unittest.TestCase):
    def test_state_drainage_reconstructs_without_chat_or_process_memory(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            mandate = ContinuousExecutionMandate("P","WP4","RUN","CONTINUE_UNTIL_MANDATORY_STOP","plan",None)
            lane = DevelopmentLane("lane:P","P","WP4","build@1","pip:1","vit:2","main:0")
            recovery = RecoveryState("RECOVERING",("PREDECESSOR_MOVED",),"RECOMPOSE",1,3,("main-advance",),"pmt:open","WP5")
            state = PersistentExecutionState(mandate,lane,recovery)
            path = DurableExecutionStore(td).write(state)
            direct = drain_state(path)
            self.assertEqual(direct.chat_dependency_count,0)
            self.assertEqual(direct.next_packet,"WP5")
            self.assertEqual(direct.open_materialisation_transaction,"pmt:open")
            code = "from ovc.development.skills.vit_runtime import drain_state; import sys; m=drain_state(sys.argv[1]); print(m.manifest_id, m.current_packet, m.chat_dependency_count, m.recovery_state)"
            proc = subprocess.run([sys.executable,"-c",code,str(path)],check=True,text=True,capture_output=True)
            manifest_id,current_packet,chat_count,recovery_state = proc.stdout.strip().split()
            self.assertEqual(manifest_id,direct.manifest_id)
            self.assertEqual(current_packet,"WP4")
            self.assertEqual(chat_count,"0")
            self.assertEqual(recovery_state,"RECOVERING")

    def test_corrupted_durable_state_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            state = PersistentExecutionState(ContinuousExecutionMandate("P","WP4","CONTINUE","CONTINUE_UNTIL_MANDATORY_STOP","plan"),DevelopmentLane("lane","P","WP4","build"),RecoveryState("RUNNING",next_packet="WP5"))
            path = DurableExecutionStore(td).write(state)
            raw = path.read_text(encoding="utf-8").replace('"current_packet":"WP4"','"current_packet":"OTHER"')
            path.write_text(raw,encoding="utf-8")
            with self.assertRaises(Exception):
                drain_state(path)

    def test_recoverable_failure_uses_budget_and_operator_wait_is_immutable(self) -> None:
        state = RecoveryState("RECOVERING",("PREDECESSOR_MOVED",),"RECOMPOSE",0,2,next_packet="WP5")
        once = recovery_transition(state,"FAIL")
        self.assertEqual(once.state,"RECOVERING")
        twice = recovery_transition(once,"FAIL")
        self.assertEqual(twice.state,"BLOCKED")
        self.assertIn("RECOVERY_BUDGET_EXHAUSTED",twice.blocker_codes)
        waiting = recovery_transition(state,"AUTHORITY_REQUIRED")
        self.assertEqual(waiting.state,"WAITING_OPERATOR_AUTHORITY")
        self.assertEqual(recovery_transition(waiting,"SUCCESS"),waiting)

if __name__ == "__main__":
    unittest.main()
