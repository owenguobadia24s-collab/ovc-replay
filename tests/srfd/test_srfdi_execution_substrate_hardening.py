from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from ovc.opt_b.srfd.wp10_execution_substrate_hardening import (
    ExecutionSubstrateHardeningError,
    capture_execution_environment_profile,
    classify_work_unit_id,
    synthetic_minimal_worker,
    synthetic_rehearsal_unit_ids,
    validate_work_unit_output_contract,
)


class ExecutionSubstrateHardeningTests(unittest.TestCase):
    def test_exact_synthetic_plan_has_all_work_unit_classes_and_2020_units(self):
        units = synthetic_rehearsal_unit_ids()
        self.assertEqual(len(units), 2020)
        classes = {classify_work_unit_id(unit) for unit in units}
        self.assertEqual(
            classes,
            {
                "POPULATION",
                "SEGMENTATION",
                "DOMAIN_PREPARATION",
                "CONFIGURATION",
                "DOMAIN_ANALYSIS",
                "TERMINAL_AGGREGATION",
            },
        )
        self.assertEqual(sum("/configuration/" in unit for unit in units), 1944)
        self.assertEqual(sum(unit.endswith("/prepare") for unit in units), 36)
        self.assertEqual(sum(unit.endswith("/analysis") for unit in units), 36)

    def test_every_synthetic_dispatch_output_matches_its_unit_contract(self):
        for unit in synthetic_rehearsal_unit_ids():
            output = synthetic_minimal_worker(unit)
            self.assertEqual(validate_work_unit_output_contract(unit, output), output)

    def test_configuration_unit_rejects_domain_preparation_payload_immediately(self):
        unit = "domain/SYNTH-DOMAIN-00/configuration/SYNTH-CONFIG-00"
        wrong = {
            "schema": "ovc-srfdi-wp10-v07-domain-preparation/v1",
            "domain_id": "SYNTH-DOMAIN-00",
            "preparation": {"synthetic": True},
        }
        with self.assertRaises(ExecutionSubstrateHardeningError) as caught:
            validate_work_unit_output_contract(unit, wrong)
        self.assertEqual(caught.exception.reason_code, "WORK_UNIT_OUTPUT_SCHEMA_MISMATCH")

    def test_configuration_unit_requires_catalog(self):
        unit = "domain/SYNTH-DOMAIN-00/configuration/SYNTH-CONFIG-00"
        wrong = {
            "schema": "ovc-srfdi-wp10-v07-family-configuration/v1",
            "domain_id": "SYNTH-DOMAIN-00",
            "configuration": {"configuration_id": "SYNTH-CONFIG-00"},
        }
        with self.assertRaises(ExecutionSubstrateHardeningError) as caught:
            validate_work_unit_output_contract(unit, wrong)
        self.assertEqual(caught.exception.reason_code, "WORK_UNIT_OUTPUT_CONTRACT_MISMATCH")

    def test_environment_profile_captures_real_host_limits_and_storage(self):
        with tempfile.TemporaryDirectory() as directory:
            profile = capture_execution_environment_profile(artifact_root=Path(directory))
        self.assertEqual(profile["schema"], "ovc-srfdi-execution-environment-profile/v1")
        self.assertEqual(profile["scientific_delta"], "NONE")
        self.assertEqual(profile["authority_effect"], "EXECUTION_GOVERNANCE_ONLY")
        self.assertTrue(profile["platform"]["python_version"])
        self.assertGreater(profile["artifact_storage"]["total_bytes"], 0)
        self.assertGreater(profile["temporary_storage"]["total_bytes"], 0)
        self.assertGreater(profile["concurrency"]["logical_cpu_count"], 0)
        self.assertIsNotNone(profile["memory"]["effective_detected_ceiling_bytes"])
        self.assertTrue(profile["logical_sha256"])


if __name__ == "__main__":
    unittest.main()
