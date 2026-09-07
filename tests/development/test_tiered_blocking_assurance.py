from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from ovc.development.test_selection import load_test_profile_registry, select_test_manifest
from tools.ci import prvitr_rac_ready as ready
from tools.ci.tiered_profile_runner import TieredProfileError, build_plan


ROOT = Path(__file__).resolve().parents[2]
REGISTRY = ROOT / "registries/development/OVC_DEVELOPMENT_ACCELERATION_TEST_PROFILE_REGISTRY_v0_2.json"


class TieredBlockingAssuranceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = load_test_profile_registry(REGISTRY)

    def test_ordinary_profiles_block_without_complete_sweep_or_legacy_parity(self) -> None:
        fast = select_test_manifest(["docs/design/example.md"], self.registry)
        packet = select_test_manifest(
            ["src/ovc/example.py", "tests/example/test_example.py"], self.registry
        )
        for manifest, profile in ((fast, "FAST"), (packet, "PACKET")):
            self.assertEqual(manifest["schema"], "ovc-test-selection-manifest/v2")
            self.assertEqual(manifest["selected_profile"], profile)
            self.assertEqual(manifest["blocking_assurance_profile"], profile)
            self.assertFalse(manifest["complete_sweep_required"])
            self.assertFalse(manifest["pytest_unittest_parity_required"])
            self.assertFalse(manifest["final_assurance_required"])

    def test_harness_and_unknown_paths_fail_closed_to_complete_sweep(self) -> None:
        for path in ("tools/ci/pytest_unittest_parity.py", "unmapped/new_surface.bin"):
            with self.subTest(path=path):
                manifest = select_test_manifest([path], self.registry)
                self.assertEqual(manifest["selected_profile"], "FINAL_HEAD")
                self.assertTrue(manifest["complete_sweep_required"])
                self.assertTrue(manifest["pytest_unittest_parity_required"])

    def test_packet_runner_requires_changed_test_for_executable_mutation(self) -> None:
        with self.assertRaisesRegex(
            TieredProfileError, "PACKET_EXECUTABLE_CHANGE_REQUIRES_CHANGED_PACKET_TEST"
        ):
            build_plan("PACKET", ("src/ovc/development/test_selection.py",))

    def test_packet_runner_executes_only_changed_packet_tests_plus_authority(self) -> None:
        plan = build_plan(
            "PACKET",
            (
                "src/ovc/development/test_selection.py",
                "tests/development/test_tiered_blocking_assurance.py",
            ),
        )
        self.assertEqual(
            plan["pytest_targets"],
            ["tests/authority", "tests/development/test_tiered_blocking_assurance.py"],
        )
        self.assertFalse(plan["complete_sweep_executed"])
        self.assertFalse(plan["pytest_unittest_parity_executed"])

    def test_workflows_make_tiered_profile_normal_and_full_sweep_triggered(self) -> None:
        tiered = (ROOT / ".github/workflows/ovc-tiered-tests.yml").read_text(encoding="utf-8")
        complete = (ROOT / ".github/workflows/tests.yml").read_text(encoding="utf-8")
        self.assertIn("name: VIT routing preflight", tiered)
        self.assertIn("OVC_SELECTED_PROFILE: ${{ needs.profile.outputs.selected_profile }}", tiered)
        self.assertIn("OVC_COMPLETE_SWEEP_REQUIRED: ${{ needs.profile.outputs.complete_sweep_required }}", tiered)
        self.assertIn("Re-select profile against the late-bound physical base", tiered)
        self.assertIn("OVC_LATE_BOUND_PROFILE_CHANGED", tiered)
        self.assertIn("complete assurance sweep trigger", complete)
        self.assertIn('cron: "17 3 * * 1"', complete)
        parity = complete.split("\n  pytest-unittest-parity:\n", 1)[1].split("\n  runner-parity:\n", 1)[0]
        self.assertIn("needs.complete-sweep-trigger.outputs.full_sweep_required == 'true'", parity)

    def test_ready_selector_routes_ordinary_to_tiered_and_final_to_complete(self) -> None:
        with patch.dict(
            os.environ,
            {"OVC_SELECTED_PROFILE": "PACKET", "OVC_COMPLETE_SWEEP_REQUIRED": "false"},
            clear=False,
        ), patch.object(ready, "_command_tiered_ready", return_value=17) as tiered, patch.object(
            ready.live, "command_ready", return_value=23
        ) as complete:
            self.assertEqual(ready.command_ready(), 17)
            tiered.assert_called_once_with("PACKET")
            complete.assert_not_called()

        with patch.dict(
            os.environ,
            {"OVC_SELECTED_PROFILE": "FINAL_HEAD", "OVC_COMPLETE_SWEEP_REQUIRED": "true"},
            clear=False,
        ), patch.object(ready, "_command_tiered_ready", return_value=17) as tiered, patch.object(
            ready.live, "command_ready", return_value=23
        ) as complete:
            self.assertEqual(ready.command_ready(), 23)
            tiered.assert_not_called()
            complete.assert_called_once_with()

    def test_tiered_ready_waits_for_both_exact_run_jobs(self) -> None:
        run = {"id": 101}
        jobs = ({"id": 201, "name": "VIT routing preflight"}, {"id": 202, "name": "OVC profile assurance"})
        with patch.object(ready.live, "_exact_run", return_value=run), patch.object(
            ready.live, "_run_job_state", return_value=("PASS", jobs)
        ) as state:
            actual_run, actual_jobs = ready._wait_required_jobs(
                "ovc-tiered-tests.yml",
                7,
                "a" * 40,
                ready.TIERED_REQUIRED_JOB_NAMES,
            )
        self.assertEqual(actual_run, run)
        self.assertEqual(actual_jobs, jobs)
        state.assert_called_once_with(run, ready.TIERED_REQUIRED_JOB_NAMES)

    def test_active_assurance_profile_retains_parity_only_in_complete_sweep(self) -> None:
        profile = json.loads(
            (
                ROOT
                / "registries/development/skills/async_assurance/REQUIRED_ASSURANCE_PROFILE_v0_2.json"
            ).read_text(encoding="utf-8")
        )
        self.assertFalse(profile["pytest_unittest_parity_ordinary_blocking"])
        self.assertTrue(profile["pytest_unittest_parity_retained"])
        ordinary = {row["check_name"] for row in profile["ordinary_blocking_members"]}
        complete = {row["check_name"] for row in profile["complete_sweep_members"]}
        self.assertNotIn("pytest-unittest-parity", ordinary)
        self.assertIn("pytest-unittest-parity", complete)


if __name__ == "__main__":
    unittest.main()
