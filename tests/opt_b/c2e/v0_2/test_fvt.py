import json
from pathlib import Path
import unittest

from ovc.opt_b.c2e_v2.handoff import C2EHandoffError, build_input_frame

ROOT = Path(__file__).resolve().parents[4]
FIXTURE = ROOT / "fixtures/opt_b/c2e/v0_2/wp1/ordinary_frame.json"


class C2E2FirstValidTimeTests(unittest.TestCase):
    def test_future_parent_is_rejected(self) -> None:
        payload = json.loads(FIXTURE.read_text())
        payload["parent_records"][0]["first_valid_time"] = "2026-06-22T10:30:00Z"
        with self.assertRaisesRegex(C2EHandoffError, "TIME_PARENT_NOT_FIRST_VALID"):
            build_input_frame(payload)

    def test_frame_fvt_must_not_exceed_cutoff(self) -> None:
        payload = json.loads(FIXTURE.read_text())
        payload["chronology"]["evaluation_cutoff"] = "2026-06-22T10:14:59Z"
        with self.assertRaisesRegex(C2EHandoffError, "FRAME_NOT_FIRST_VALID_AT_CUTOFF"):
            build_input_frame(payload)


if __name__ == "__main__":
    unittest.main()
