from __future__ import annotations

import json
from pathlib import Path
import unittest

from ovc.opt_b.srfd import june_authority_v03
from ovc.opt_b.srfd.serialization import logical_sha256

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "docs/releases/srfd-benchmark-v0-1/srfdi-june-auth-v0-3"
DECISION = BASE / "SRFDI_G_JUNE_AUTH_OPERATOR_DECISION_v0_3.json"
MANIFEST = BASE / "SRFD_JUNE_AUTHORIZED_MANIFEST_v0_3.json"
TOKEN = BASE / "SRFD_JUNE_AUTHORITY_TOKEN_v0_3.json"
STATE = ROOT / "registries/implementation/srfd/OVC_SRFDI_STATE_v0_6.json"
POINTER = ROOT / "registries/implementation/srfd/CURRENT_STATE_POINTER.json"


class SRFDIJuneAuthOperatorDecisionV03Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.decision = json.loads(DECISION.read_text())
        cls.manifest = json.loads(MANIFEST.read_text())
        cls.token = json.loads(TOKEN.read_text())
        cls.state = json.loads(STATE.read_text())
        cls.pointer = json.loads(POINTER.read_text())

    def test_operator_decision_is_exact_and_bounded(self) -> None:
        self.assertEqual("SRFDI-G-JUNE-AUTH", self.decision["gate_id"])
        self.assertEqual("AUTHORIZE_JUNE", self.decision["decision"])
        self.assertEqual("OPERATOR", self.decision["decision_authority"])
        self.assertEqual("OVC APPROVE SRFDI-G-JUNE-AUTH AUTHORIZE_JUNE", self.decision["operator_command"])
        self.assertEqual("148cf9c6958ffc737a3b5fd1800c48c1544bf34e835a97c884e77d4b49904067", self.decision["authorized_manifest_sha256"])
        self.assertEqual("AUTHORIZED_BOUNDED_JUNE_BENCHMARK", self.decision["authority_effect"]["june_execution"])
        self.assertEqual("DENIED", self.decision["authority_effect"]["provider_fetch"])
        self.assertEqual("LOCKED_UNCONSUMED", self.decision["authority_effect"]["validation_2025"])
        self.assertEqual("NONE", self.decision["authority_effect"]["scientific_promotion"])

    def test_authorized_manifest_and_token_reconstruct_exactly(self) -> None:
        self.assertEqual("6a112f9b80ecbfe509805574945c0aaedc84aec552a74198b3e749d82b034322", logical_sha256(self.manifest))
        self.assertEqual("f7f6be787b9e2540d243426894096a66f62a2c0945f3adfa3f9fa00df6656da7", logical_sha256(self.decision))
        self.assertEqual("148cf9c6958ffc737a3b5fd1800c48c1544bf34e835a97c884e77d4b49904067", june_authority_v03.manifest_binding_sha256(self.manifest))
        reconstructed = june_authority_v03.verify_june_run_authority(
            self.decision,
            self.manifest,
            expected_implementation_commit="7e234e52a95dcc7c1d136d7566d271a2c216e137",
        )
        self.assertEqual(self.token, reconstructed.to_dict())
        self.assertEqual("SRFD.JUNE.AUTH.8e07a6f1ce7a1c6a37faa23ec7eb227f3e45dba1aeb53c970960d7ff9bbf9722", reconstructed.token_id)
        june_authority_v03.guard_bounded_june_run(reconstructed, self.manifest)

    def test_historical_state_advances_only_to_wp10_authorized_unconsumed(self) -> None:
        self.assertEqual("READY", self.state["status"])
        self.assertEqual("SRFDI-WP10-v0.3", self.state["active_packet"])
        self.assertEqual("SRFDI-G10", self.state["current_gate"])
        self.assertFalse(self.state["operator_decision_required"])
        self.assertEqual("AUTHORIZED_ONE_EXACT_BOUND_RUN_UNCONSUMED", self.state["authority"]["market_benchmark"])
        self.assertFalse(self.state["exact_bindings"]["authority_token_consumed"])
        self.assertEqual("DENIED", self.state["authority"]["provider_fetch"])
        self.assertEqual("LOCKED_UNCONSUMED", self.state["authority"]["validation_2025"])
        self.assertEqual("NONE", self.state["authority"]["probability_risk_exposure_execution"])

        self.assertTrue(self.pointer["authoritative_state"].startswith("registries/implementation/srfd/OVC_SRFDI_STATE_v0_"))
        self.assertIn("authority_token_consumed", self.pointer)
        self.assertFalse(self.pointer["superseded_authority_token_consumed"])
        self.assertEqual("PRESERVE_CLOSED_UNMERGED_HISTORICAL_EVIDENCE", self.pointer["pr_371"])


if __name__ == "__main__":
    unittest.main()
