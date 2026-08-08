import copy
import json
from pathlib import Path
import unittest

from ovc.opt_b.c2e_v2.handoff import build_input_frame

ROOT = Path(__file__).resolve().parents[4]
FIXTURE = ROOT / "fixtures/opt_b/c2e/v0_2/wp1/ordinary_frame.json"


class C2E2HandoffTests(unittest.TestCase):
    def test_handoff_is_deterministic_and_identity_rich(self) -> None:
        payload = json.loads(FIXTURE.read_text())
        first = build_input_frame(payload)
        second = build_input_frame(copy.deepcopy(payload))
        self.assertEqual(first, second)
        self.assertTrue(first["frame_id"].startswith("C2E.FRAME."))
        self.assertEqual(first["logical_hash"], second["logical_hash"])
        self.assertEqual(first["identity"]["observation_id"], first["identity"]["c2_record_id"])
        self.assertEqual(first["source_binding"]["binding_status"], "EXACT_READ_ONLY_SHADOW")
        self.assertEqual(first["authority"], "INACTIVE_NONCANONICAL_BUILD_TEST_ONLY")


if __name__ == "__main__":
    unittest.main()
