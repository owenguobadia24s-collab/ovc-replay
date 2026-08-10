from __future__ import annotations

import copy
from pathlib import Path
import tempfile
import unittest

from ovc.opt_b.srfd.wp10_v11_environment import (
    ExecutionEnvironmentError,
    load_frozen_profile,
    verify_frozen_execution_environment,
)
from ovc.opt_b.srfd.wp10_v11_hardening import (
    SYNTHETIC_WORK_UNIT_COUNT,
    WorkUnitContractError,
    classify_work_unit,
    run_restart_torture,
    synthetic_work_units,
    synthetic_worker,
    validate_work_unit_output,
)

ROOT = Path(__file__).resolve().parents[2]
PROFILE = ROOT / "docs/releases/srfd-benchmark-v0-1/srfdi-wp10-v1-1-hardening/SRFDI_EXECUTION_ENVIRONMENT_PROFILE_v1.json"


class SRFDIWP10V11HardeningTests(unittest.TestCase):
    def test_frozen_execution_environment_profile_is_hash_bound_and_complete(self):
        profile = load_frozen_profile(PROFILE)
        self.assertEqual("SRFDI.EXECUTION.ENV.CAAS.20260810.v1", profile["profile_id"])
        self.assertEqual(4294967296, profile["memory"]["cgroup_memory_max_bytes"])
        self.assertEqual(0, profile["memory"]["swap_total_bytes"])
        self.assertEqual(4.0, profile["concurrency"]["effective_cpu_quota_cores"])
        self.assertEqual("ext4", profile["storage"]["working_root"]["filesystem_type"])
        self.assertEqual(25769803776, profile["execution_constraints"]["t1_external_artifact_limit_bytes"])
        self.assertEqual(1, profile["execution_constraints"]["max_worker_concurrency"])
        self.assertEqual("3.13.5", profile["python"]["version"])
        self.assertEqual("2.3.5", profile["dependencies"]["numpy"])
        self.assertEqual("1.17.0", profile["dependencies"]["scipy"])
        self.assertEqual(506, profile["dependency_inventory"]["pip_freeze_line_count"])
        self.assertEqual("c605675736ce321c8262bed98b1b47857b0d3e57cc96df1251bc5d4044c44866", profile["dependency_inventory"]["pip_freeze_sha256"])

    def test_environment_verifier_fails_closed_on_memory_or_dependency_drift(self):
        frozen = load_frozen_profile(PROFILE)
        observed = copy.deepcopy(frozen)
        observed["storage"]["working_root"]["available_bytes"] = 40 * 1024**3
        observed["storage"]["temp_root"]["available_bytes"] = 40 * 1024**3
        receipt = verify_frozen_execution_environment(observed, frozen)
        self.assertEqual("PASS", receipt["status"])
        drift = copy.deepcopy(observed)
        drift["memory"]["cgroup_memory_max_bytes"] = 8 * 1024**3
        with self.assertRaises(ExecutionEnvironmentError) as ctx:
            verify_frozen_execution_environment(drift, frozen)
        self.assertEqual("EXECUTION_ENVIRONMENT_MISMATCH", ctx.exception.reason_code)

    def test_every_work_unit_class_has_a_strict_output_contract(self):
        samples = {
            "population": "POPULATION",
            "segmentation/RUN_CHANGE_SEGMENTATION": "SEGMENTATION",
            "domain/SYNTH.DOMAIN.00/prepare": "DOMAIN_PREPARE",
            "domain/SYNTH.DOMAIN.00/configuration/SYNTH.CONFIG.00": "DOMAIN_CONFIGURATION",
            "domain/SYNTH.DOMAIN.00/analysis": "DOMAIN_ANALYSIS",
            "packet": "PACKET",
        }
        for unit, expected_kind in samples.items():
            self.assertEqual(expected_kind, classify_work_unit(unit))
            validate_work_unit_output(unit, synthetic_worker(unit))

    def test_configuration_unit_cannot_accept_domain_prepare_payload(self):
        bad_unit = "domain/SYNTH.DOMAIN.00/configuration/SYNTH.CONFIG.00"
        prepare = synthetic_worker("domain/SYNTH.DOMAIN.00/prepare")
        with self.assertRaises(WorkUnitContractError) as ctx:
            validate_work_unit_output(bad_unit, prepare)
        self.assertEqual("WORK_UNIT_OUTPUT_SCHEMA_MISMATCH", ctx.exception.reason_code)

    def test_full_synthetic_plan_is_exactly_2020_units(self):
        plan = synthetic_work_units()
        self.assertEqual(SYNTHETIC_WORK_UNIT_COUNT, len(plan))
        self.assertEqual(len(plan), len(set(plan)))
        self.assertEqual("population", plan[0])
        self.assertEqual("packet", plan[-1])
        self.assertEqual(36, sum(1 for unit in plan if unit.endswith("/prepare")))
        self.assertEqual(1944, sum(1 for unit in plan if "/configuration/" in unit))
        self.assertEqual(36, sum(1 for unit in plan if unit.endswith("/analysis")))

    def test_restart_torture_crosses_all_unit_type_transitions_without_divergence(self):
        with tempfile.TemporaryDirectory(prefix="srfd_v11_restart_") as tmp:
            receipt = run_restart_torture(Path(tmp))
        self.assertEqual("PASS", receipt["status"])
        self.assertEqual(receipt["reference_result_logical_hash"], receipt["torture_result_logical_hash"])
        self.assertIn("ANALYSIS_TO_NEXT_DOMAIN_PREPARE", receipt["transition_classes"])
        self.assertIn("FINAL_ANALYSIS_TO_PACKET", receipt["transition_classes"])


if __name__ == "__main__":
    unittest.main()
