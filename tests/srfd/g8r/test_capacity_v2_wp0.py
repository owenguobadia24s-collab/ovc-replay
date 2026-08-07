from __future__ import annotations

import tempfile
import unittest

from ovc.opt_b.srfd.capacity_v2 import (
    CapacityV2Error,
    capture_h0_environment,
    classify_change,
    feasibility_bridge_schema,
    reference_component_profile,
    render_h0_line,
    render_reference_profile_line,
    validate_feasibility_bridge_receipt,
)


class SRFDIG8RCapacityV2WP0Tests(unittest.TestCase):
    def test_change_classification_fails_closed_on_semantic_change(self) -> None:
        self.assertEqual("COMPUTE_ONLY_EQUIVALENT", classify_change("compute_only_equivalent"))
        with self.assertRaises(CapacityV2Error) as raised:
            classify_change("POTENTIAL_SEMANTIC_CHANGE")
        self.assertEqual("G8R_POTENTIAL_SEMANTIC_CHANGE", raised.exception.reason_code)

    def test_h0_capture_is_measured_machine_path_independent_identity(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            receipt = capture_h0_environment(artifact_root=root, io_payload_bytes=64 * 1024)
        line = render_h0_line(receipt)
        print(line, flush=True)
        self.assertEqual("MEASURED", receipt["measurement_class"])
        self.assertTrue(receipt["environment_fingerprint"].startswith("SRFD.H0."))
        self.assertFalse(receipt["hostname_in_identity"])
        self.assertFalse(receipt["local_path_in_identity"])
        self.assertFalse(receipt["june_market_records_read"])
        self.assertFalse(receipt["validation_consumed"])
        self.assertEqual("CANDIDATE_UNADMITTED", receipt["candidate_backend"]["numpy"]["admission_state"])
        self.assertGreater(receipt["storage"]["io"]["payload_bytes"], 0)
        self.assertGreater(receipt["storage"]["io"]["write_seconds"], 0)
        self.assertTrue(line.startswith("SRFDI_G8R_H0="))

    def test_reference_component_profile_uses_fixture_only_oracle(self) -> None:
        receipt = reference_component_profile()
        line = render_reference_profile_line(receipt)
        print(line, flush=True)
        self.assertEqual("CURRENT_JSON_REFERENCE", receipt["reference_oracle"])
        self.assertEqual("MEASURED", receipt["measurement_class"])
        self.assertFalse(receipt["june_market_records_read"])
        self.assertFalse(receipt["validation_consumed"])
        self.assertEqual("NONE", receipt["receipt"]["sampling"])
        self.assertTrue(line.startswith("SRFDI_G8R_REFERENCE_PROFILE="))

    def test_feasibility_bridge_schema_is_operator_gated_before_wp3(self) -> None:
        schema = feasibility_bridge_schema()
        self.assertEqual("SRFDI-G8R-G2F", schema["operator_gate"])
        self.assertEqual("SRFDI-G8R-WP3", schema["mandatory_before_packet"])
        self.assertTrue(schema["no_multiplicative_speedup_claim"])
        self.assertIn("logical_equivalence", schema["required_fields"])

    def test_bridge_receipt_factor_is_derived_not_speculative(self) -> None:
        receipt = {
            "environment_fingerprint": "SRFD.H0.TEST",
            "baseline_component_id": "B0",
            "candidate_component_id": "B1",
            "population": {"n": 128, "domains": [128]},
            "backend": "BASELINE_OPTIMIZED",
            "before_wall_seconds": 4.0,
            "after_wall_seconds": 2.0,
            "before_cpu_seconds": 4.0,
            "after_cpu_seconds": 2.0,
            "before_peak_rss_bytes": 100,
            "after_peak_rss_bytes": 100,
            "before_external_bytes": 1000,
            "after_external_bytes": 500,
            "storage_read_seconds": 0.1,
            "storage_write_seconds": 0.1,
            "cache_state": "COLD",
            "logical_equivalence": True,
            "marginal_improvement_factor": 2.0,
            "remaining_bottleneck": "DISTANCE_KERNEL",
            "bounded_forecast": {"P2": "INDETERMINATE"},
            "disposition": "PLAUSIBLE",
        }
        validate_feasibility_bridge_receipt(receipt)
        receipt["marginal_improvement_factor"] = 4.0
        with self.assertRaises(CapacityV2Error) as raised:
            validate_feasibility_bridge_receipt(receipt)
        self.assertEqual("G8R_BRIDGE_FACTOR_MISMATCH", raised.exception.reason_code)


if __name__ == "__main__":
    unittest.main()
