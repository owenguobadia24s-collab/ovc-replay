from __future__ import annotations

import json
from pathlib import Path
import unittest

from ovc.opt_b.c2p_v0_2.rs0_capacity import run_rs0_capacity_dry_run


ROOT = Path(__file__).resolve().parents[4]
RECEIPT = ROOT / "docs/releases/c2p-persistent-structural-objects-v0-2/c2p2-rs0/C2P2_RS0_CAPACITY_MEASUREMENT_RECEIPT_v0_1.json"
BINDING = ROOT / "registries/implementation/c2p_v0_2/C2P2_RS0_EXTERNAL_ARTIFACT_ROOT_BINDING_v0_1.json"


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

    def test_exact_hosted_runner_measurement_is_materialized_and_frozen(self):
        receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
        self.assertEqual(receipt["measurement_source"]["workflow_run_id"], 31965538212)
        self.assertEqual(receipt["measurement_source"]["job_id"], 95210050005)
        self.assertEqual(receipt["measurement_source"]["head_sha"], "0ad1eef4fca2986bc459c652e2c176c55038a563")
        self.assertEqual(receipt["suite_context"]["deliberate_measurement_sentinel_failures"], 1)
        output = receipt["measurement_output"]
        self.assertFalse(output["real_source_consumed"])
        self.assertEqual(output["measured"]["artifact_bytes"], 782707)
        self.assertEqual(output["measured"]["peak_rss_bytes"], 290148352)
        self.assertEqual(output["measured"]["wall_clock_seconds"], 1.977437)
        self.assertEqual(receipt["frozen_execution_envelope"]["peak_memory_limit_bytes"], 1160593408)
        self.assertEqual(receipt["frozen_execution_envelope"]["external_storage_limit_bytes"], 6411935744)
        self.assertEqual(receipt["frozen_execution_envelope"]["concurrency_limit"], 1)
        self.assertEqual(receipt["frozen_execution_envelope"]["checkpoint_cadence_assertions"], 256)
        self.assertEqual(receipt["frozen_execution_envelope"]["capacity_exceeded_disposition"], "FAIL_CLOSED_RETURN_TO_OPERATOR")

    def test_exact_rs0_external_artifact_root_is_bound(self):
        binding = json.loads(BINDING.read_text(encoding="utf-8"))
        self.assertEqual(binding["source_registry_blob_sha"], "ba8bfc2d862f0bb51f56c7acc95b15f3517e53b1")
        self.assertEqual(binding["rs0_run_root"]["folder_id"], "1AkfK95_GB5Oz7U_PC5wA7rUWZAfcGhvv")
        self.assertEqual(binding["rs0_run_root"]["title"], "c2p2-rs0-shadow-evidence-v0-1")
        self.assertEqual(binding["rs0_run_root"]["binding_status"], "EXACT_BOUND")
        self.assertIn("NO_REAL_SOURCE_EXECUTION_BEFORE_C2P2_RS0_GRUN_PASS", binding["prohibitions"])


if __name__ == "__main__":
    unittest.main()
