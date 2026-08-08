from __future__ import annotations

import json
from pathlib import Path
import unittest

from ovc.opt_b.srfd import june_authority_v04
from ovc.opt_b.srfd.serialization import logical_sha256

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "docs/releases/srfd-benchmark-v0-1/srfdi-june-auth-v0-4"
DECISION = BASE / "SRFDI_G_JUNE_AUTH_OPERATOR_DECISION_v0_4.json"
MANIFEST = BASE / "SRFD_JUNE_AUTHORIZED_MANIFEST_v0_4.json"
TOKEN = BASE / "SRFD_JUNE_AUTHORITY_TOKEN_v0_4.json"
STATE = ROOT / "registries/implementation/srfd/OVC_SRFDI_STATE_v0_11_APPROVED_PENDING_MERGE.json"
PREDECISION = ROOT / "registries/implementation/srfd/OVC_SRFDI_STATE_v0_11_CANDIDATE.json"
POINTER = ROOT / "registries/implementation/srfd/CURRENT_STATE_POINTER.json"


class SRFDIJuneAuthOperatorDecisionV04Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.decision = json.loads(DECISION.read_text())
        cls.manifest = json.loads(MANIFEST.read_text())
        cls.token = json.loads(TOKEN.read_text())
        cls.state = json.loads(STATE.read_text())
        cls.predecision = json.loads(PREDECISION.read_text())
        cls.pointer = json.loads(POINTER.read_text())

    def test_operator_decision_is_exact_and_bounded(self) -> None:
        self.assertEqual("SRFDI-G-JUNE-AUTH", self.decision["gate_id"])
        self.assertEqual("AUTHORIZE_JUNE", self.decision["decision"])
        self.assertEqual("OPERATOR", self.decision["decision_authority"])
        self.assertEqual("OVC APPROVE SRFDI-G-JUNE-AUTH AUTHORIZE_JUNE", self.decision["operator_command"])
        self.assertEqual("79e47109303ff24b9d5036059cb13eef75d1ed65", self.decision["approved_candidate"]["predecision_head"])
        self.assertEqual("2c34a663201adc612cb452467ad61d694a8bb74a528cb858186a06a029381e29", self.decision["authorized_manifest_sha256"])
        self.assertEqual("AUTHORIZED_BOUNDED_JUNE_BENCHMARK", self.decision["authority_effect"]["june_execution"])
        self.assertEqual("DENIED", self.decision["authority_effect"]["provider_fetch"])
        self.assertEqual("LOCKED_UNCONSUMED", self.decision["authority_effect"]["validation_2025"])
        self.assertEqual("NONE", self.decision["authority_effect"]["scientific_promotion"])
        self.assertEqual("NONE", self.decision["authority_effect"]["probability_risk_exposure_execution"])

    def test_authorized_manifest_and_token_reconstruct_exactly(self) -> None:
        self.assertEqual("fccbffc7678ceabcfafe337e58d51a3f8ea1ee1a1cdc75b93563397ebabbd120", logical_sha256(self.decision))
        self.assertEqual("6ba46d446d799d7686ee038c80fb21fa899e8dbe0875ddd12779068b38e30cbb", logical_sha256(self.manifest))
        self.assertEqual("2c34a663201adc612cb452467ad61d694a8bb74a528cb858186a06a029381e29", june_authority_v04.manifest_binding_sha256(self.manifest))
        reconstructed = june_authority_v04.verify_june_run_authority(
            self.decision,
            self.manifest,
            expected_implementation_commit="0e94bf4d61272b685a8e972e695e88b6ca4cb3c7",
        )
        self.assertEqual(self.token, reconstructed.to_dict())
        self.assertEqual("SRFD.JUNE.AUTH.52bcae6e0b748a0c49d578b3b2b529f16754438793cbd261670d91ed0d2a5686", reconstructed.token_id)
        self.assertNotEqual(june_authority_v04.PRIOR_V03_TOKEN_ID, reconstructed.token_id)
        june_authority_v04.guard_bounded_june_run(reconstructed, self.manifest)

    def test_state_advances_only_to_wp10_authorized_unconsumed_pending_merge(self) -> None:
        self.assertEqual("READY", self.state["status"])
        self.assertEqual("SRFDI-WP10-v0.4", self.state["active_packet"])
        self.assertEqual("SRFDI-G10", self.state["current_gate"])
        self.assertFalse(self.state["operator_decision_required"])
        self.assertEqual("AUTHORIZED_ONE_EXACT_BOUND_RUN_UNCONSUMED", self.state["authority"]["market_benchmark"])
        self.assertFalse(self.state["exact_bindings"]["authority_token_consumed"])
        self.assertEqual(self.token["token_id"], self.state["exact_bindings"]["authority_token_id"])
        self.assertFalse(self.state["exact_bindings"]["prior_v0_3_authority_token_consumed"])
        self.assertEqual("DENIED", self.state["authority"]["provider_fetch"])
        self.assertEqual("LOCKED_UNCONSUMED", self.state["authority"]["validation_2025"])
        self.assertEqual("NONE", self.state["authority"]["probability_risk_exposure_execution"])

    def test_predecision_candidate_and_main_pointer_remain_preserved_until_merge_closeout(self) -> None:
        self.assertEqual("GATE_READY_SUBJECT_TO_EXACT_HEAD_CI", self.predecision["status"])
        self.assertTrue(self.predecision["operator_decision_required"])
        self.assertEqual("registries/implementation/srfd/OVC_SRFDI_STATE_v0_10.json", self.pointer["authoritative_state"])
        self.assertEqual("DENIED_PENDING_NEW_EXACT_SRFDI_G_JUNE_AUTH", self.pointer["june_execution"])
        self.assertFalse(self.pointer["authority_token_consumed"])

    def test_exact_scientific_and_population_bindings_remain_unchanged(self) -> None:
        bindings = self.state["exact_bindings"]
        self.assertEqual("f0da6203124a6aeaa83f89e3f27b2fc980754f874ae96e631009dfc9048f2fa3", bindings["preregistration_v0_4_logical_sha256"])
        self.assertEqual("371a058e26c05a351a99689ad23b7f844fbc956a6d81449fd237a2f420bf564b", bindings["stability_metric_registry_v0_4_logical_sha256"])
        self.assertEqual("6c2451fb5b766d2ae25a13a311ba17c8dede342757d607219e62881be4ac31c0", bindings["segmentation_registry_v0_3_logical_sha256"])
        self.assertEqual("4d13c3ee8ae2ad25e30088f4f2de48f8320e3633c2e4ea6a5c2c9a7fdc2a62b7", bindings["source_binding_sha256"])
        self.assertEqual("SRFD.POP.6efa7dd55636d036c12e580e0793abacf8c805bcf6d77bb6e2edf7cffbc113bd", bindings["population_id"])
        self.assertEqual(8598, bindings["eligible_record_count"])


if __name__ == "__main__":
    unittest.main()
