from __future__ import annotations

import json
from pathlib import Path
import unittest

from srfd._current_pointer_compat import assert_lawful_v10_pointer

ROOT = Path(__file__).resolve().parents[2]
BLOCKER = ROOT / "docs/releases/srfd-benchmark-v0-1/srfdi-wp10-v1-1/SRFDI_WP10_V11_PREFLIGHT_ENVIRONMENT_BLOCKER.json"
STATE = ROOT / "registries/implementation/srfd/OVC_SRFDI_STATE_v0_49_WP10_V11_PREFLIGHT_ENV_BLOCKED.json"
SUPERSESSION = ROOT / "docs/releases/srfd-benchmark-v0-1/srfdi-wp10-v1-1/SRFDI_WP10_V11_ENVIRONMENT_PROFILE_SUPERSESSION.json"
POINTER = ROOT / "registries/implementation/srfd/CURRENT_STATE_POINTER.json"
TOKEN = "SRFD.JUNE.AUTH.7b52e77176fa43d246891ec61d3d0130afe8cb7b5e296f3a705dc83e7fe95b9f"
BINDING = "3029d32692f20e724d95ed0b63acf79b1709769f4b8603e9371acee50cd642b5"


class SRFDIWP10V11PreflightEnvironmentBlockerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.b = json.loads(BLOCKER.read_text())
        cls.s = json.loads(STATE.read_text())
        cls.x = json.loads(SUPERSESSION.read_text())
        cls.p = json.loads(POINTER.read_text())

    def test_preflight_failure_remains_immutable_historical_evidence(self):
        self.assertEqual("BLOCKED_PREFLIGHT_ENVIRONMENT_DRIFT", self.b["status"])
        self.assertEqual("EXECUTION_ENVIRONMENT_MISMATCH", self.b["reason_code"])
        self.assertFalse(self.b["token_consumed"])
        self.assertFalse(self.b["science_execution_started"])
        self.assertEqual(TOKEN, self.b["token_id"])
        self.assertEqual(BINDING, self.b["attempted_run_binding_sha256"])
        self.assertEqual("BLOCKED", self.s["status"])
        self.assertEqual("HARD_BLOCKER", self.s["stop_condition"])

    def test_route1_forensics_explain_exact_capture_contract_mismatch(self):
        f = self.x["cause"]["frozen_profile"]
        r = self.x["cause"]["runtime_verifier"]
        self.assertEqual(506, f["line_count"])
        self.assertEqual("c605675736ce321c8262bed98b1b47857b0d3e57cc96df1251bc5d4044c44866", f["inventory_sha256"])
        self.assertEqual(507, r["line_count"])
        self.assertEqual("c7e66045f5f4393b29bb7a0e28628ae6c3607dc50ea0ef77eb5523216898e99a", r["inventory_sha256"])
        self.assertEqual("pip==25.1.1", r["additional_line"])
        self.assertFalse(self.x["cause"]["relevant_dependency_versions_changed"])
        self.assertEqual("NONE", self.x["cause"]["scientific_delta"])

    def test_current_pointer_progression_preserves_historical_supersession(self):
        self.assertTrue(assert_lawful_v10_pointer(self, self.p))
        self.assertEqual(TOKEN, self.p["superseded_v1_1_authority_token_id"])
        self.assertEqual(BINDING, self.p["superseded_v1_1_run_binding_sha256"])
        self.assertFalse(self.p["superseded_v1_1_authority_token_consumed"])
        self.assertEqual("SUPERSEDED_UNUSED_UNCONSUMED_DO_NOT_REUSE", self.p["superseded_v1_1_authority_token_state"])

    def test_reserved_boundaries_remain_closed(self):
        self.assertEqual("DENIED", self.p["provider_fetch"])
        self.assertEqual("LOCKED_UNCONSUMED", self.p["validation_2025"])
        self.assertEqual("NONE", self.p["scientific_promotion"])
        self.assertEqual("NONE", self.p["selector_family_semantic_publication"])
        self.assertEqual("NONE", self.p["probability_risk_exposure_execution"])


if __name__ == "__main__":
    unittest.main()
