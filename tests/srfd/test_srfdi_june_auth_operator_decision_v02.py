from __future__ import annotations

import json
from pathlib import Path
import unittest

from ovc.opt_b.srfd import june_authority_v02
from ovc.opt_b.srfd.serialization import logical_sha256

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "docs/releases/srfd-benchmark-v0-1/srfdi-june-auth"
DECISION = BASE / "SRFDI_G_JUNE_AUTH_OPERATOR_DECISION.json"
MANIFEST = BASE / "SRFD_JUNE_AUTHORIZED_MANIFEST_v0_2.json"
TOKEN = BASE / "SRFD_JUNE_AUTHORITY_TOKEN_v0_2.json"
CANDIDATE = BASE / "SRFD_JUNE_AUTHORITY_MANIFEST_CANDIDATE_v0_2.json"
STATE = ROOT / "registries/implementation/srfd/OVC_SRFDI_STATE_v0_3.json"
POINTER = ROOT / "registries/implementation/srfd/CURRENT_STATE_POINTER.json"


class SRFDIJuneAuthOperatorDecisionV02Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.decision = json.loads(DECISION.read_text())
        cls.manifest = json.loads(MANIFEST.read_text())
        cls.token = json.loads(TOKEN.read_text())
        cls.candidate = json.loads(CANDIDATE.read_text())
        cls.state = json.loads(STATE.read_text())
        cls.pointer = json.loads(POINTER.read_text())

    def test_operator_decision_is_exact_and_bounded(self) -> None:
        self.assertEqual("SRFDI-G-JUNE-AUTH", self.decision["gate_id"])
        self.assertEqual("AUTHORIZE_JUNE", self.decision["decision"])
        self.assertEqual("OPERATOR", self.decision["decision_authority"])
        self.assertEqual(
            "2a0d3c529ea5aca6a1d8c67adc29d3f6dd55a3efcd75992661a69e205cea010c",
            self.decision["authorized_manifest_sha256"],
        )
        effect = self.decision["authority_effect"]
        self.assertEqual("AUTHORIZED_BOUNDED_JUNE_BENCHMARK", effect["june_execution"])
        self.assertEqual("DENIED", effect["provider_fetch"])
        self.assertEqual("LOCKED_UNCONSUMED", effect["validation_2025"])
        self.assertEqual("NONE", effect["scientific_promotion"])
        self.assertEqual("NONE", effect["selector_change"])
        self.assertEqual("NONE", effect["publication"])
        self.assertEqual("NONE", effect["probability_risk_exposure_execution"])

    def test_authorized_manifest_is_the_exact_candidate_binding(self) -> None:
        expected = json.loads(json.dumps(self.candidate))
        expected["run_authority"] = june_authority_v02.AUTHORIZED_RUN_STATE
        expected["authority_binding"] = self.manifest["authority_binding"]
        self.assertEqual(expected, self.manifest)
        self.assertEqual(
            "2a0d3c529ea5aca6a1d8c67adc29d3f6dd55a3efcd75992661a69e205cea010c",
            june_authority_v02.manifest_binding_sha256(self.manifest),
        )
        self.assertEqual(
            "94ab89e27d10dabaa99e68687b90974f3b6ee182bcceffed7587ca7b27e44dac",
            logical_sha256(self.decision),
        )
        self.assertEqual(
            "811514cef8a24dc1078cbf231105cb7d79af75c3899ed90a210d1d7bc3d898ac",
            logical_sha256(self.manifest),
        )

    def test_fail_closed_verifier_reconstructs_exact_token(self) -> None:
        token = june_authority_v02.verify_june_run_authority(
            self.decision,
            self.manifest,
            expected_implementation_commit="fca974ef48e4178be299bf65e520e2268e8b67c3",
        )
        self.assertEqual(self.token, token.to_dict())
        self.assertEqual(
            "SRFD.JUNE.AUTH.5fd1ed170fac6994b8ac65db05b7907bda8dad7ec49084572dad1e9040e7bf81",
            token.token_id,
        )
        june_authority_v02.guard_bounded_june_run(token, self.manifest)

    def test_programme_state_advances_only_to_authorized_wp10(self) -> None:
        self.assertEqual("READY", self.state["status"])
        self.assertEqual("SRFDI-WP10", self.state["active_packet"])
        self.assertFalse(self.state["operator_decision_required"])
        self.assertEqual("AUTHORIZED_ONE_EXACT_BOUND_RUN_UNCONSUMED", self.state["authority"]["market_benchmark"])
        self.assertEqual("LOCKED_UNCONSUMED", self.state["authority"]["validation_2025"])
        self.assertEqual("NONE", self.state["authority"]["selector_family_semantic_publication"])
        self.assertEqual("NONE", self.state["authority"]["probability_risk_exposure_execution"])
        self.assertEqual("registries/implementation/srfd/OVC_SRFDI_STATE_v0_3.json", self.pointer["authoritative_state"])
        self.assertEqual("SRFDI-WP10", self.pointer["next_packet"])
        self.assertEqual("SRFDI-G11", self.pointer["stop_at"])


if __name__ == "__main__":
    unittest.main()
