from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from ovc.opt_b.srfd.wp10_execution_resilience import ExecutionResilienceError, RunAuthorityStore, RunBinding
from ovc.opt_b.srfd.wp10_v07_contract import WP10RunnerError, verify_frozen_run_binding
from ovc.opt_b.srfd.wp10_v07_runner import _binding_from_json

ROOT = Path(__file__).resolve().parents[2]
V09 = ROOT / "docs/releases/srfd-benchmark-v0-1/srfdi-june-auth-v0-9"
MANIFEST = V09 / "SRFD_JUNE_AUTHORITY_MANIFEST_CANDIDATE_v0_9.json"
TOKEN = V09 / "SRFD_JUNE_AUTHORITY_TOKEN_v0_9.json"
EFFECT = V09 / "SRFD_JUNE_AUTHORITY_EFFECT_v0_9.json"
V08_ENVELOPE = ROOT / "docs/releases/srfd-benchmark-v0-1/srfdi-june-auth-v0-8/SRFD_JUNE_AUTHORITY_ENVELOPE_v0_8.json"
BLOCKER = ROOT / "docs/releases/srfd-benchmark-v0-1/srfdi-wp10-v0-9/SRFDI_WP10_V09_PREFLIGHT_EXECUTION_INTERFACE_BLOCKER.json"
RUNNER = ROOT / "src/ovc/opt_b/srfd/wp10_v07_runner.py"
POINTER = ROOT / "registries/implementation/srfd/CURRENT_STATE_POINTER.json"

V09_BINDING = "ca25077124a49a02808ed0c855906456d19415df5371266ebc1e90448d022d9a"
FRESH_TOKEN = "SRFD.JUNE.AUTH.a5311fbade60d87553ad76b9085e1bd2ba62fe60c6d9654a2d338b624b5498c3"


class SRFDIWP10V09PreflightBlockerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads(MANIFEST.read_text())
        cls.token = json.loads(TOKEN.read_text())
        cls.effect = json.loads(EFFECT.read_text())
        cls.v08 = json.loads(V08_ENVELOPE.read_text())
        cls.blocker = json.loads(BLOCKER.read_text())
        cls.pointer = json.loads(POINTER.read_text())

    def _diagnostic_projection(self) -> RunBinding:
        source = self.manifest["run_binding"]
        payload = {key: source[key] for key in RunBinding.__dataclass_fields__ if key != "implementation_commit"}
        payload["implementation_commit"] = self.v08["run_binding"]["implementation_commit"]
        return RunBinding(**payload)

    def test_exact_v09_binding_is_not_representable_by_current_runner_shape(self):
        self.assertEqual(V09_BINDING, self.manifest["run_binding_sha256"])
        self.assertNotIn("implementation_commit", self.manifest["run_binding"])
        self.assertEqual("eefd860af86aea38e80ec211dd5ea34160171b6f", self.manifest["run_binding"]["execution_binding_merge"])
        self.assertEqual("2ffe195b509a22884942b50509448a5731903abb4b794c432df69a034e12fcc1", self.manifest["run_binding"]["execution_binding_sha256"])
        with self.assertRaises(KeyError) as ctx:
            _binding_from_json(self.manifest["run_binding"])
        self.assertEqual("'implementation_commit'", str(ctx.exception))

    def test_even_diagnostic_shape_projection_is_rejected_by_frozen_v07_contract(self):
        binding = self._diagnostic_projection()
        self.assertNotEqual(V09_BINDING, binding.logical_hash)
        self.assertEqual("SRFDI-WP10-v0.9", binding.packet_id)
        with self.assertRaises(WP10RunnerError) as ctx:
            verify_frozen_run_binding(binding)
        self.assertEqual("RUN_BINDING_SCIENCE_DRIFT", ctx.exception.reason_code)
        self.assertEqual("packet_id:SRFDI-WP10-v0.9", ctx.exception.detail)

    def test_raw_token_fails_before_consumption_and_effect_overlay_is_separate(self):
        self.assertEqual(FRESH_TOKEN, self.token["token_id"])
        self.assertEqual("AUTHORIZED_UNCONSUMED_PENDING_MAIN_MERGE", self.token["state"])
        self.assertEqual("AUTHORIZED_UNCONSUMED", self.effect["fresh_token"]["state"])
        self.assertFalse(self.effect["fresh_token"]["consumed"])
        self.assertEqual(FRESH_TOKEN, self.effect["fresh_token"]["token_id"])
        binding = self._diagnostic_projection()
        with TemporaryDirectory() as td:
            store = RunAuthorityStore(Path(td))
            with self.assertRaises(ExecutionResilienceError) as ctx:
                store.consume(self.token, binding)
            self.assertEqual("TOKEN_NOT_STARTABLE", ctx.exception.reason_code)
            self.assertFalse((Path(td) / "consumption").exists())

    def test_current_runner_has_no_v09_authority_effect_adapter(self):
        runner = RUNNER.read_text(encoding="utf-8")
        self.assertIn('token=_load_json(Path(args.token_json))', runner)
        self.assertNotIn("SRFD_JUNE_AUTHORITY_EFFECT_v0_9", runner)
        self.assertNotIn("authority_effect_receipt", runner)

    def test_blocker_is_preconsumption_non_scientific_and_preserves_firewalls(self):
        self.assertEqual("BLOCKED_BEFORE_TOKEN_CONSUMPTION", self.blocker["status"])
        self.assertEqual("NONE_PREFLIGHT_DIAGNOSTIC_ONLY", self.blocker["authority_effect"])
        self.assertFalse(self.blocker["market_records_read"])
        self.assertFalse(self.blocker["provider_fetch_attempted"])
        self.assertFalse(self.blocker["validation_access_attempted"])
        self.assertFalse(self.blocker["exact_authority"]["fresh_token_consumed"])
        self.assertEqual(FRESH_TOKEN, self.blocker["exact_authority"]["fresh_token_id"])
        self.assertEqual("DENIED", self.blocker["exact_authority"]["provider_fetch"])
        self.assertEqual("LOCKED_UNCONSUMED", self.blocker["exact_authority"]["validation_2025"])
        self.assertTrue(self.blocker["required_resolution"]["material_frozen_contract_change"])
        self.assertEqual("NONE", self.blocker["required_resolution"]["scientific_delta"])
        self.assertEqual("FORBIDDEN", self.blocker["required_resolution"]["new_token"])

    def test_pointer_fails_closed_at_operator_gate_without_consuming_fresh_token(self):
        self.assertEqual("SRFDI-G10C", self.pointer["current_gate"])
        self.assertEqual("GATE_READY", self.pointer["status"])
        self.assertTrue(self.pointer["operator_decision_required"])
        self.assertIsNone(self.pointer["next_packet"])
        self.assertEqual(FRESH_TOKEN, self.pointer["fresh_authority_token_id"])
        self.assertEqual("AUTHORIZED_UNCONSUMED", self.pointer["fresh_authority_token_state"])
        self.assertFalse(self.pointer["fresh_authority_token_consumed"])
        self.assertEqual(V09_BINDING, self.pointer["run_binding_sha256"])
        self.assertEqual("DENIED", self.pointer["provider_fetch"])
        self.assertEqual("LOCKED_UNCONSUMED", self.pointer["validation_2025"])
        self.assertEqual("NONE", self.pointer["scientific_promotion"])
        self.assertEqual("NONE", self.pointer["selector_family_semantic_publication"])
        self.assertEqual("NONE", self.pointer["probability_risk_exposure_execution"])


if __name__ == "__main__":
    unittest.main()
