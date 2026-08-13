from __future__ import annotations

import json
import unittest
from pathlib import Path

from ovc.development.skills.orch345_diagnostics import (
    DIAGNOSTIC_AUTHORITY_EFFECT,
    DIAGNOSTIC_RECEIPT_CLASS,
)


ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = ROOT / "registries/development/skills/orch345_diagnostic_observability_v0_1.json"


class ORCH345DiagnosticPolicyTests(unittest.TestCase):
    def test_policy_is_temporary_observability_only(self) -> None:
        policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
        self.assertEqual(policy["status"], "TEMPORARY_ACTIVE")
        self.assertTrue(policy["effective"])
        self.assertEqual(policy["scope"], ["ORCH-3", "ORCH-4", "ORCH-5"])
        self.assertEqual(policy["receipt_class"], DIAGNOSTIC_RECEIPT_CLASS)
        self.assertEqual(policy["authority_effect"], DIAGNOSTIC_AUTHORITY_EFFECT)
        self.assertFalse(policy["governance_expansion"])
        self.assertFalse(policy["new_operator_gate"])
        self.assertEqual(policy["merge_authority"], "NONE")
        self.assertFalse(policy["parallel_merge"])
        self.assertEqual(
            policy["activation_mode"],
            "PASSIVE_COMPANION_RECEIPT_ON_EXISTING_ACTIVE_HELPER_INVOCATION",
        )
        self.assertEqual(
            policy["capacity_profile_unchanged"],
            {
                "max_parallel_builds": 4,
                "max_train_packets": 8,
                "max_auto_requeue_attempts": 2,
            },
        )
        self.assertEqual(policy["validation"], "DENIED")
        self.assertEqual(policy["reserved_scientific_execution_authority"], "NONE")


if __name__ == "__main__":
    unittest.main()
