from __future__ import annotations

import json
from pathlib import Path
import unittest

from srfd._current_pointer_compat import assert_lawful_v10_pointer

ROOT = Path(__file__).resolve().parents[2]
BLOCKER = ROOT / "docs/releases/srfd-benchmark-v0-1/srfdi-wp10-v1-1/SRFDI_WP10_V11_PREFLIGHT_ENVIRONMENT_BLOCKER.json"
STATE = ROOT / "registries/implementation/srfd/OVC_SRFDI_STATE_v0_49_WP10_V11_PREFLIGHT_ENV_BLOCKED.json"
POINTER = ROOT / "registries/implementation/srfd/CURRENT_STATE_POINTER.json"
TOKEN = "SRFD.JUNE.AUTH.7b52e77176fa43d246891ec61d3d0130afe8cb7b5e296f3a705dc83e7fe95b9f"
BINDING = "3029d32692f20e724d95ed0b63acf79b1709769f4b8603e9371acee50cd642b5"


class SRFDIWP10V11PreflightEnvironmentBlockerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.b = json.loads(BLOCKER.read_text())
        cls.s = json.loads(STATE.read_text())
        cls.p = json.loads(POINTER.read_text())

    def test_preflight_failed_closed_before_token_consumption_or_science(self):
        self.assertEqual("BLOCKED_PREFLIGHT_ENVIRONMENT_DRIFT", self.b["status"])
        self.assertEqual("EXECUTION_ENVIRONMENT_MISMATCH", self.b["reason_code"])
        self.assertEqual(
            ["dependency_inventory.pip_freeze_line_count", "dependency_inventory.pip_freeze_sha256"],
            self.b["reason_detail"],
        )
        self.assertFalse(self.b["token_consumed"])
        self.assertFalse(self.b["science_execution_started"])
        self.assertEqual(TOKEN, self.b["token_id"])
        self.assertEqual(BINDING, self.b["attempted_run_binding_sha256"])

    def test_dependency_drift_is_exact_and_relevant_versions_remain_visible(self):
        self.assertEqual(506, self.b["frozen_dependency_inventory"]["pip_freeze_line_count"])
        self.assertEqual(507, self.b["observed_dependency_inventory"]["pip_freeze_line_count"])
        self.assertEqual(
            "c605675736ce321c8262bed98b1b47857b0d3e57cc96df1251bc5d4044c44866",
            self.b["frozen_dependency_inventory"]["pip_freeze_sha256"],
        )
        self.assertEqual(
            "c7e66045f5f4393b29bb7a0e28628ae6c3607dc50ea0ef77eb5523216898e99a",
            self.b["observed_dependency_inventory"]["pip_freeze_sha256"],
        )
        self.assertEqual("2.3.5", self.b["relevant_dependency_versions_match"]["numpy"])
        self.assertEqual("1.17.0", self.b["relevant_dependency_versions_match"]["scipy"])

    def test_state_and_pointer_preserve_unconsumed_authority_and_hard_stop(self):
        self.assertEqual("BLOCKED", self.s["status"])
        self.assertFalse(self.s["authority"]["token_consumed"])
        self.assertEqual("HARD_BLOCKER", self.s["stop_condition"])
        self.assertTrue(self.s["operator_decision_required"])
        self.assertTrue(assert_lawful_v10_pointer(self, self.p))
        self.assertEqual("BLOCKED", self.p["status"])
        self.assertEqual("HARD_BLOCKER", self.p["stop_at"])
        self.assertFalse(self.p["fresh_authority_token_consumed"])

    def test_reserved_boundaries_remain_closed(self):
        self.assertEqual("DENIED", self.b["provider_fetch"])
        self.assertEqual("LOCKED_UNCONSUMED", self.b["validation_2025"])
        self.assertEqual("NONE", self.b["scientific_delta"])
        self.assertEqual("NONE", self.b["selector_family_semantic_publication"])
        self.assertEqual("NONE", self.b["probability_risk_exposure_execution"])


if __name__ == "__main__":
    unittest.main()
