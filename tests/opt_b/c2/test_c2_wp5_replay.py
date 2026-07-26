from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from ovc.opt_b.c2.replay import DISCOVERY_RELEASE, ReplayError, run_role_replay


def fixture(record_id: str, close: str, open_: str) -> dict:
    measurements = {
        "open": open_, "high": "1.2510", "low": "1.2480", "close": close,
        "range_low": "1.2400", "range_high": "1.2600",
        "swing_low": "1.2300", "swing_high": "1.2700", "prior_range": "0.0020",
    }
    for index in range(9, 18):
        measurements[f"m{index}"] = str(index)
    return {
        "c1_record_id": record_id,
        "c1_release_id": DISCOVERY_RELEASE,
        "c1_manifest_id": "MANIFEST.C1.TEST",
        "opt_a_release_id": "OPT-A.TEST",
        "opt_a_manifest_id": "MANIFEST.A.TEST",
        "role": "DISCOVERY",
        "authority_state": "ACTIVE_DISCOVERY",
        "instrument": "GBPUSD",
        "clock": "15M",
        "side": "BID",
        "close_time": "2026-01-01T00:15:00Z",
        "first_valid_time": "2026-01-01T00:15:00Z",
        "measurements": measurements,
        "quality_state": "VALID",
    }


class WP5ReplayTests(unittest.TestCase):
    def test_replay_is_deterministic_and_bounded(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "input.jsonl"
            source.write_text("\n".join(json.dumps(x) for x in [fixture("C1.1", "1.2500", "1.2490"), fixture("C1.2", "1.2485", "1.2495")]) + "\n", encoding="utf-8")
            first = run_role_replay(role="DISCOVERY", release_id=DISCOVERY_RELEASE, input_path=source, output_dir=root / "a")
            second = run_role_replay(role="DISCOVERY", release_id=DISCOVERY_RELEASE, input_path=source, output_dir=root / "b")
            self.assertEqual(first, second)
            self.assertEqual((root / "a" / "discovery_states.jsonl").read_bytes(), (root / "b" / "discovery_states.jsonl").read_bytes())
            self.assertEqual(first.state_records, 2)
            self.assertEqual(first.transition_records, 1)

    def test_wrong_release_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "input.jsonl"
            path.write_text(json.dumps(fixture("C1.1", "1.2500", "1.2490")) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(ReplayError, "WRONG_RELEASE_ID"):
                run_role_replay(role="DISCOVERY", release_id="WRONG", input_path=path, output_dir=Path(tmp) / "out")


if __name__ == "__main__":
    unittest.main()
