from __future__ import annotations

import copy
import json
from pathlib import Path
import unittest

from ovc.opt_b.srfd import june_authority_v03
from ovc.opt_b.srfd.june_authority import AUTHORIZED_RUN_STATE, JuneAuthorityError
from ovc.opt_b.srfd.serialization import logical_sha256

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "docs/releases/srfd-benchmark-v0-1"
V03 = BASE / "srfdi-june-auth-v0-3"
MANIFEST = V03 / "SRFD_JUNE_AUTHORITY_MANIFEST_CANDIDATE_v0_3.json"
BINDING = V03 / "SRFD_JUNE_SOURCE_POPULATION_BINDING_v0_3.json"
QA = V03 / "SRFDI_G_JUNE_AUTH_QA_PACKET_v0_3.json"
PACKET = V03 / "SRFDI_G_JUNE_AUTH_OPERATOR_PACKET_v0_3.json"
FREEZE = BASE / "srfdi-wp9c/SRFDI_G9C_FREEZE_MERGE_RECEIPT.json"
STATE = ROOT / "registries/implementation/srfd/OVC_SRFDI_STATE_v0_5.json"
POINTER = ROOT / "registries/implementation/srfd/CURRENT_STATE_POINTER.json"


class SRFDIJuneAuthGateReadyV03Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.manifest = json.loads(MANIFEST.read_text())
        cls.binding = json.loads(BINDING.read_text())
        cls.qa = json.loads(QA.read_text())
        cls.packet = json.loads(PACKET.read_text())
        cls.freeze = json.loads(FREEZE.read_text())
        cls.state = json.loads(STATE.read_text())
        cls.pointer = json.loads(POINTER.read_text())

    def _authorized_pair(self) -> tuple[dict, dict]:
        manifest = copy.deepcopy(self.manifest)
        manifest["run_authority"] = AUTHORIZED_RUN_STATE
        decision = {
            "gate_id": "SRFDI-G-JUNE-AUTH",
            "decision": "AUTHORIZE_JUNE",
            "decision_id": "SYNTHETIC.TEST.V03.AUTH",
            "authorized_manifest_sha256": june_authority_v03.manifest_binding_sha256(manifest),
            "authority_effect": {
                "june_execution": "AUTHORIZED_BOUNDED_JUNE_BENCHMARK",
                "provider_fetch": "DENIED",
                "validation_2025": "LOCKED_UNCONSUMED",
                "scientific_promotion": "NONE",
                "selector_change": "NONE",
                "publication": "NONE",
                "probability_risk_exposure_execution": "NONE",
            },
        }
        manifest["authority_binding"] = {
            "gate_id": "SRFDI-G-JUNE-AUTH",
            "decision_id": decision["decision_id"],
            "decision_logical_sha256": logical_sha256(decision),
            "authorized_manifest_sha256": decision["authorized_manifest_sha256"],
        }
        return decision, manifest

    def test_g9c_freeze_and_v03_scientific_hashes_are_exact(self) -> None:
        self.assertEqual("SRFDI-G9C-FREEZE", self.freeze["gate_id"])
        self.assertEqual("PREREGISTRATION_FREEZE", self.freeze["decision"])
        self.assertEqual(june_authority_v03.PREREG_FREEZE_MERGE_COMMIT, self.freeze["merge_commit"])
        self.assertEqual(june_authority_v03.PREREG_LOGICAL_SHA256, self.manifest["preregistration"]["logical_sha256"])
        self.assertEqual(june_authority_v03.SEGMENTATION_REGISTRY_LOGICAL_SHA256, self.manifest["segmentation_registry"]["logical_sha256"])

    def test_manifest_is_inert_hash_bound_and_operator_reserved(self) -> None:
        self.assertEqual(june_authority_v03.MANIFEST_SCHEMA, self.manifest["schema"])
        self.assertEqual(june_authority_v03.PENDING_RUN_STATE, self.manifest["run_authority"])
        self.assertEqual("SRFDI-G-JUNE-AUTH", self.manifest["run_authority_gate"])
        self.assertNotIn("authority_binding", self.manifest)
        self.assertEqual("148cf9c6958ffc737a3b5fd1800c48c1544bf34e835a97c884e77d4b49904067", june_authority_v03.manifest_binding_sha256(self.manifest))
        with self.assertRaisesRegex(JuneAuthorityError, "operator decision is required"):
            june_authority_v03.verify_june_run_authority(
                None,
                self.manifest,
                expected_implementation_commit="7e234e52a95dcc7c1d136d7566d271a2c216e137",
            )

    def test_exact_source_population_is_unchanged_from_frozen_binding(self) -> None:
        self.assertEqual(self.binding["source_binding"], self.manifest["source_binding"])
        self.assertEqual(self.binding["population_binding"], self.manifest["population_binding"])
        self.assertEqual(8598, self.manifest["population_binding"]["eligible_record_count"])
        self.assertEqual("fbb03d1db6cfa91f63330433e835c2bd659d1128b682817083d6f7af9f2aca4e", self.manifest["population_binding"]["eligible_record_ids_sha256"])
        self.assertEqual(0, self.manifest["population_binding"]["exclusion_count"])
        self.assertEqual("FORBIDDEN", self.manifest["source_binding"]["provider_fetch"])
        self.assertEqual("FORBIDDEN", self.manifest["source_binding"]["upstream_mutation"])

    def test_segmentation_execution_set_is_exact_and_nonexecuted_methods_remain_visible(self) -> None:
        self.assertEqual(june_authority_v03.EXPECTED_SEGMENTATION_METHODS, self.manifest["candidate_sets"]["segmentation"])
        self.assertEqual(june_authority_v03.EXPECTED_SEGMENTATION_EXECUTE, self.manifest["candidate_sets"]["segmentation_execute"])
        self.assertEqual(june_authority_v03.EXPECTED_SEGMENTATION_NONEXECUTED, self.manifest["candidate_sets"]["segmentation_visible_nonexecuted"])
        self.assertEqual("RUN_CHANGE_AND_NULL_LINEAR_ONLY", self.manifest["capacity_binding"]["segmentation_execution"])
        self.assertEqual("VISIBLE_NOT_EXECUTED_CAPACITY_UNRESOLVED_AT_T0", self.manifest["capacity_binding"]["pelt"])

    def test_prior_v02_token_is_superseded_unused_and_never_reused(self) -> None:
        self.assertFalse(self.manifest["prior_authority"]["v0_2_token_consumed"])
        self.assertEqual("SUPERSEDED_UNUSED_UNCONSUMED", self.manifest["prior_authority"]["v0_2_token_disposition"])
        self.assertFalse(self.binding["prior_v0_2_authority"]["consumed"])
        self.assertEqual("SUPERSEDED_UNUSED_UNCONSUMED", self.state["authority"]["prior_june_authority_token"])

    def test_synthetic_exact_authority_pair_can_generate_new_token(self) -> None:
        decision, manifest = self._authorized_pair()
        token = june_authority_v03.verify_june_run_authority(
            decision,
            manifest,
            expected_implementation_commit="7e234e52a95dcc7c1d136d7566d271a2c216e137",
        )
        self.assertEqual(AUTHORIZED_RUN_STATE, token.authority_state)
        self.assertEqual(self.manifest["population_binding"]["population_id"], token.population_id)
        self.assertEqual(self.manifest["source_binding"]["source_release_id"], token.source_release_id)
        june_authority_v03.guard_bounded_june_run(token, manifest)

    def test_scientific_or_population_tampering_fails_closed(self) -> None:
        decision, manifest = self._authorized_pair()
        tampered = copy.deepcopy(manifest)
        tampered["candidate_sets"]["segmentation_execute"] = ["NULL_BOUNDARY_CONTROL"]
        with self.assertRaises(JuneAuthorityError):
            june_authority_v03.verify_june_run_authority(
                decision,
                tampered,
                expected_implementation_commit="7e234e52a95dcc7c1d136d7566d271a2c216e137",
            )
        tampered = copy.deepcopy(manifest)
        tampered["population_binding"]["eligible_record_count"] = 8597
        with self.assertRaises(JuneAuthorityError):
            june_authority_v03.verify_june_run_authority(
                decision,
                tampered,
                expected_implementation_commit="7e234e52a95dcc7c1d136d7566d271a2c216e137",
            )

    def test_gate_candidate_stops_before_june_and_does_not_mutate_authoritative_pointer(self) -> None:
        self.assertEqual("GATE_READY", self.state["status"])
        self.assertEqual("SRFDI-G-JUNE-AUTH", self.state["current_gate"])
        self.assertTrue(self.state["operator_decision_required"])
        self.assertEqual("DENIED_PENDING_OPERATOR_SRFDI_G_JUNE_AUTH", self.state["authority"]["june"])
        self.assertEqual("DENIED", self.state["authority"]["provider_fetch"])
        self.assertEqual("LOCKED_UNCONSUMED", self.state["authority"]["validation_2025"])
        self.assertEqual("NONE", self.state["authority"]["probability_risk_exposure_execution"])

        self.assertEqual("registries/implementation/srfd/OVC_SRFDI_STATE_v0_4.json", self.pointer["authoritative_state"])
        self.assertEqual("SRFDI-G-JUNE-AUTH-PREPARATION-v0.3", self.pointer["current_gate"])
        self.assertFalse(self.pointer["operator_decision_required"])
        self.assertEqual("DENIED_PENDING_NEW_EXACT_SRFDI_G_JUNE_AUTH", self.pointer["june_execution"])
        self.assertFalse(self.pointer["superseded_authority_token_consumed"])

    def test_operator_packet_is_one_exact_reserved_decision(self) -> None:
        self.assertEqual("SRFDI-G-JUNE-AUTH", self.packet["gate_id"])
        self.assertEqual("AUTHORIZE_JUNE", self.packet["recommended_decision"])
        self.assertEqual("OVC APPROVE SRFDI-G-JUNE-AUTH AUTHORIZE_JUNE", self.packet["exact_operator_command"])
        self.assertEqual("148cf9c6958ffc737a3b5fd1800c48c1544bf34e835a97c884e77d4b49904067", self.packet["manifest_binding_sha256"])
        self.assertEqual("PASS_GATE_READY_SUBJECT_TO_EXACT_HEAD_CI", self.qa["qa_conclusion"])
        self.assertEqual("DENIED_PENDING_OPERATOR_SRFDI_G_JUNE_AUTH", self.packet["current_authority"]["june_execution"])


if __name__ == "__main__":
    unittest.main()
