from __future__ import annotations

import json
from pathlib import Path
import unittest

from ovc.development.skills.fault_closure import FULL_E6_FAULT_SCENARIOS, run_full_fault_injection


ROOT = Path(__file__).resolve().parents[2]


class DSAIG7FullE6FaultClosureTests(unittest.TestCase):
    def setUp(self) -> None:
        self.environment = json.loads((ROOT / "fixtures/development_skills/wp2_windows_environment_v0_1.json").read_text())
        self.plan = json.loads((ROOT / "docs/releases/development-skills-architecture-v0-1/dsai-wp7/DSAI_G7_ALL_SKILL_E6_FULL_FAULT_PLAN.json").read_text())
        self.releases = []
        for path in (
            "registries/development/skills/governance_candidates_v0_1.json",
            "registries/development/skills/first_generation_candidates_v0_1.json",
        ):
            registry = json.loads((ROOT / path).read_text())
            self.releases.extend(registry["entries"])

    def test_full_e6_catalogue_matches_ratified_design_plus_plan_specific_denied_tool(self) -> None:
        self.assertEqual(set(FULL_E6_FAULT_SCENARIOS), set(self.plan["effective_scenarios"]))
        self.assertEqual(len(FULL_E6_FAULT_SCENARIOS), 9)
        self.assertEqual(set(self.plan["design_fault_scenarios"]), {
            "MISSING_MANIFEST", "CORRUPT_MANIFEST", "UNAVAILABLE_REMOTE", "KILLED_TEST",
            "STALE_HASH", "DISK_PRESSURE", "REVOKED_DEPENDENCY", "INVALID_CACHE",
        })
        self.assertEqual(self.plan["implementation_additional_scenarios"], ["DENIED_TOOL"])

    def test_every_release_capability_environment_tuple_passes_all_full_e6_fail_closed_scenarios(self) -> None:
        tuple_count = 0
        binding_count = 0
        for release in self.releases:
            for capability_id in release["capability_ids"]:
                tuple_count += 1
                for scenario in FULL_E6_FAULT_SCENARIOS:
                    with self.subTest(skill=release["skill_id"], capability=capability_id, scenario=scenario):
                        result = run_full_fault_injection(
                            scenario=scenario,
                            skill_release_id=release["release_id"],
                            capability_id=capability_id,
                            environment_id=self.environment["base_environment_id"],
                        )
                        self.assertEqual(result["observed_status"], "BLOCK")
                        self.assertTrue(result["fail_closed"])
                        self.assertTrue(result["evidence_preserved"])
                        self.assertFalse(result["scope_mutated"])
                        self.assertFalse(result["authority_escalated"])
                        self.assertEqual(result["authority_effect"], "NONE")
                        binding_count += 1
        self.assertEqual(len(self.releases), 14)
        self.assertEqual(tuple_count, 15)
        self.assertEqual(binding_count, 135)
        self.assertEqual(self.plan["implemented_release_capability_tuples"], 15)
        self.assertEqual(self.plan["minimum_release_capability_environment_scenario_bindings"], 135)

    def test_unsupported_fault_scenario_refuses_to_claim_evidence(self) -> None:
        with self.assertRaisesRegex(ValueError, "unsupported full E6"):
            run_full_fault_injection(
                scenario="UNKNOWN_FAULT",
                skill_release_id="OVC-SKILL-X@0.1.0+sha256:" + "a" * 64,
                capability_id="X",
                environment_id=self.environment["base_environment_id"],
            )


if __name__ == "__main__":
    unittest.main()
