from __future__ import annotations

import json
import unittest

from ovc.opt_b.c2p_v0_2.rs0_capacity import run_rs0_capacity_dry_run


class C2P2RS0CapacityDryRunTests(unittest.TestCase):
    def test_capacity_dry_run_is_non_evidentiary_and_emits_measured_envelope(self):
        record = run_rs0_capacity_dry_run(sample_assertions=256)
        self.assertEqual(record["schema"], "ovc-c2p2-rs0-capacity-dry-run/v1")
        self.assertEqual(record["source_mode"], "SYNTHETIC_ONLY_NONEMPIRICAL")
        self.assertFalse(record["real_source_consumed"])
        measured = record["measured"]
        envelope = record["recommended_execution_envelope"]
        self.assertGreater(measured["peak_rss_bytes"], 0)
        self.assertGreater(measured["artifact_bytes"], 0)
        self.assertGreater(measured["wall_clock_seconds"], 0)
        self.assertGreaterEqual(envelope["peak_memory_limit_bytes"], measured["peak_rss_bytes"])
        self.assertGreaterEqual(envelope["external_storage_limit_bytes"], measured["artifact_bytes"])
        self.assertEqual(envelope["concurrency_limit"], 1)
        self.assertEqual(envelope["checkpoint_cadence_assertions"], 256)
        self.assertEqual(envelope["capacity_exceeded_disposition"], "FAIL_CLOSED_RETURN_TO_OPERATOR")
        self.assertTrue(all(value == "FORBIDDEN" for value in record["semantic_firewall"].values()))
        # Measurement phase only: fail once so the exact hosted-runner receipt is
        # retained in CI logs. The packet replaces this sentinel with a normal PASS
        # after materialising the measured receipt in repository evidence.
        self.fail("C2P2_RS0_CAPACITY_MEASUREMENT_SENTINEL=" + json.dumps(record, sort_keys=True, separators=(",", ":")))


if __name__ == "__main__":
    unittest.main()
