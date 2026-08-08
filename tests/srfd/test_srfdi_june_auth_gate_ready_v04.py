from __future__ import annotations

import copy
import json
from pathlib import Path
import unittest

from ovc.opt_b.srfd import june_authority_v04
from ovc.opt_b.srfd.june_authority import AUTHORIZED_RUN_STATE, JuneAuthorityError
from ovc.opt_b.srfd.serialization import logical_sha256

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "docs/releases/srfd-benchmark-v0-1"
V04 = BASE / "srfdi-june-auth-v0-4"
MANIFEST = V04 / "SRFD_JUNE_AUTHORITY_MANIFEST_CANDIDATE_v0_4.json"
BINDING = V04 / "SRFD_JUNE_SOURCE_POPULATION_BINDING_v0_4.json"
QA = V04 / "SRFDI_G_JUNE_AUTH_QA_PACKET_v0_4.json"
PACKET = V04 / "SRFDI_G_JUNE_AUTH_OPERATOR_PACKET_v0_4.json"
FREEZE = BASE / "srfdi-wp9d/SRFDI_G9D_FREEZE_MERGE_RECEIPT.json"
STATE = ROOT / "registries/implementation/srfd/OVC_SRFDI_STATE_v0_11_CANDIDATE.json"
POINTER = ROOT / "registries/implementation/srfd/CURRENT_STATE_POINTER.json"
PREREG = ROOT / "registries/research/srfd/SRFD_PREREGISTRATION_CANDIDATE_v0_4.json"
METRICS = ROOT / "registries/research/srfd/stability_metric_specs_v0_4.json"


class SRFDIJuneAuthGateReadyV04Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.manifest = json.loads(MANIFEST.read_text())
        cls.binding = json.loads(BINDING.read_text())
        cls.qa = json.loads(QA.read_text())
        cls.packet = json.loads(PACKET.read_text())
        cls.freeze = json.loads(FREEZE.read_text())
        cls.state = json.loads(STATE.read_text())
        cls.pointer = json.loads(POINTER.read_text())
        cls.prereg = json.loads(PREREG.read_text())
        cls.metrics = json.loads(METRICS.read_text())

    def _authorized_pair(self) -> tuple[dict, dict]:
        manifest = copy.deepcopy(self.manifest)
        manifest["run_authority"] = AUTHORIZED_RUN_STATE
        decision = {
            "gate_id": "SRFDI-G-JUNE-AUTH",
            "decision": "AUTHORIZE_JUNE",
            "decision_id": "SYNTHETIC.TEST.V04.AUTH",
            "authorized_manifest_sha256": june_authority_v04.manifest_binding_sha256(manifest),
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

    def test_g9d_freeze_closeout_and_v04_scientific_hashes_are_exact(self) -> None:
        self.assertEqual("SRFDI-G9D-FREEZE", self.freeze["gate_id"])
        self.assertEqual("PREREGISTRATION_FREEZE", self.freeze["decision"])
        self.assertEqual(june_authority_v04.PREREG_FREEZE_MERGE_COMMIT, self.freeze["merge_commit"])
        self.assertEqual(june_authority_v04.PREREG_LOGICAL_SHA256, logical_sha256(self.prereg))
        self.assertEqual(june_authority_v04.STABILITY_METRIC_REGISTRY_LOGICAL_SHA256, logical_sha256(self.metrics))
        self.assertEqual("7609f0476e21708c95fa7d61554e96fe1082b072", self.state["exact_bindings"]["g9d_closeout_merge_commit"])

    def test_manifest_is_inert_hash_bound_and_operator_reserved(self) -> None:
        self.assertEqual(june_authority_v04.MANIFEST_SCHEMA, self.manifest["schema"])
        self.assertEqual(june_authority_v04.PENDING_RUN_STATE, self.manifest["run_authority"])
        self.assertEqual("SRFDI-G-JUNE-AUTH", self.manifest["run_authority_gate"])
        self.assertNotIn("authority_binding", self.manifest)
        self.assertEqual(
            "2c34a663201adc612cb452467ad61d694a8bb74a528cb858186a06a029381e29",
            june_authority_v04.manifest_binding_sha256(self.manifest),
        )
        with self.assertRaisesRegex(JuneAuthorityError, "operator decision is required"):
            june_authority_v04.verify_june_run_authority(
                None,
                self.manifest,
                expected_implementation_commit="0e94bf4d61272b685a8e972e695e88b6ca4cb3c7",
            )

    def test_source_population_binding_is_exact_and_unchanged(self) -> None:
        self.assertEqual(
            "576608343486e6fe5e0992b2e165491f7fea1c6401c202e0056a10447992ae99",
            logical_sha256(self.binding),
        )
        self.assertEqual(self.binding["source_binding"], self.manifest["source_binding"])
        self.assertEqual(self.binding["population_binding"], self.manifest["population_binding"])
        self.assertEqual(8598, self.manifest["population_binding"]["eligible_record_count"])
        self.assertEqual(
            "fbb03d1db6cfa91f63330433e835c2bd659d1128b682817083d6f7af9f2aca4e",
            self.manifest["population_binding"]["eligible_record_ids_sha256"],
        )
        self.assertEqual(0, self.manifest["population_binding"]["exclusion_count"])
        self.assertEqual("FORBIDDEN", self.manifest["source_binding"]["provider_fetch"])
        self.assertEqual("FORBIDDEN", self.manifest["source_binding"]["upstream_mutation"])

    def test_stability_and_segmentation_execution_sets_are_exact(self) -> None:
        self.assertEqual(june_authority_v04.EXPECTED_STABILITY_METRICS, self.manifest["candidate_sets"]["stability_metrics"])
        self.assertEqual(self.metrics["metric_order"], self.manifest["candidate_sets"]["stability_metrics"])
        self.assertEqual(june_authority_v04.EXPECTED_SEGMENTATION_METHODS, self.manifest["candidate_sets"]["segmentation"])
        self.assertEqual(june_authority_v04.EXPECTED_SEGMENTATION_EXECUTE, self.manifest["candidate_sets"]["segmentation_execute"])
        self.assertEqual(june_authority_v04.EXPECTED_SEGMENTATION_NONEXECUTED, self.manifest["candidate_sets"]["segmentation_visible_nonexecuted"])
        self.assertEqual("RUN_CHANGE_AND_NULL_LINEAR_ONLY", self.manifest["capacity_binding"]["segmentation_execution"])
        self.assertEqual("VISIBLE_NOT_EXECUTED_CAPACITY_UNRESOLVED_AT_T0", self.manifest["capacity_binding"]["pelt"])

    def test_prior_v03_token_is_superseded_unused_and_never_reused(self) -> None:
        self.assertFalse(self.manifest["prior_authority"]["v0_3_token_consumed"])
        self.assertEqual("SUPERSEDED_UNUSED_UNCONSUMED", self.manifest["prior_authority"]["v0_3_token_disposition"])
        self.assertFalse(self.binding["prior_v0_3_authority"]["consumed"])
        self.assertEqual(june_authority_v04.PRIOR_V03_TOKEN_ID, self.binding["prior_v0_3_authority"]["token_id"])
        self.assertEqual("SUPERSEDED_UNUSED_UNCONSUMED", self.state["authority"]["prior_june_authority_token_v0_3"])

    def test_synthetic_exact_authority_pair_generates_new_v04_token(self) -> None:
        decision, manifest = self._authorized_pair()
        token = june_authority_v04.verify_june_run_authority(
            decision,
            manifest,
            expected_implementation_commit="0e94bf4d61272b685a8e972e695e88b6ca4cb3c7",
        )
        self.assertEqual(AUTHORIZED_RUN_STATE, token.authority_state)
        self.assertNotEqual(june_authority_v04.PRIOR_V03_TOKEN_ID, token.token_id)
        self.assertEqual(self.manifest["population_binding"]["population_id"], token.population_id)
        self.assertEqual(self.manifest["source_binding"]["source_release_id"], token.source_release_id)
        june_authority_v04.guard_bounded_june_run(token, manifest)

    def test_scientific_population_and_metric_tampering_fail_closed(self) -> None:
        mutations = []

        prereg = copy.deepcopy(self.manifest)
        prereg["preregistration"]["logical_sha256"] = "0" * 64
        mutations.append(prereg)

        metric = copy.deepcopy(self.manifest)
        metric["stability_metric_registry"]["logical_sha256"] = "0" * 64
        mutations.append(metric)

        population = copy.deepcopy(self.manifest)
        population["population_binding"]["eligible_record_count"] = 8597
        mutations.append(population)

        stability = copy.deepcopy(self.manifest)
        stability["candidate_sets"]["stability_metrics"] = list(reversed(stability["candidate_sets"]["stability_metrics"]))
        mutations.append(stability)

        segmentation = copy.deepcopy(self.manifest)
        segmentation["candidate_sets"]["segmentation_execute"] = ["NULL_BOUNDARY_CONTROL"]
        mutations.append(segmentation)

        for tampered in mutations:
            decision, authorized = self._authorized_pair()
            tampered["run_authority"] = AUTHORIZED_RUN_STATE
            tampered["authority_binding"] = authorized["authority_binding"]
            with self.assertRaises(JuneAuthorityError):
                june_authority_v04.verify_june_run_authority(
                    decision,
                    tampered,
                    expected_implementation_commit="0e94bf4d61272b685a8e972e695e88b6ca4cb3c7",
                )

    def test_candidate_gate_does_not_mutate_authoritative_pointer_or_grant_june(self) -> None:
        self.assertEqual("GATE_READY_SUBJECT_TO_EXACT_HEAD_CI", self.state["status"])
        self.assertEqual("SRFDI-G-JUNE-AUTH", self.state["current_gate"])
        self.assertTrue(self.state["operator_decision_required"])
        self.assertEqual("DENIED_PENDING_OPERATOR_SRFDI_G_JUNE_AUTH", self.state["authority"]["june"])
        self.assertEqual("FORBIDDEN_ON_GATE_CANDIDATE_BEFORE_OPERATOR_AUTHORITY", self.state["current_pointer_mutation"])

        self.assertEqual("registries/implementation/srfd/OVC_SRFDI_STATE_v0_10.json", self.pointer["authoritative_state"])
        self.assertEqual("FROZEN_AWAITING_NEW_JUNE_AUTH_PREPARATION", self.pointer["status"])
        self.assertEqual("DENIED_PENDING_NEW_EXACT_SRFDI_G_JUNE_AUTH", self.pointer["june_execution"])
        self.assertFalse(self.pointer["authority_token_consumed"])

    def test_operator_packet_is_one_exact_reserved_decision(self) -> None:
        self.assertEqual("SRFDI-G-JUNE-AUTH", self.packet["gate_id"])
        self.assertEqual("AUTHORIZE_JUNE", self.packet["recommended_decision"])
        self.assertEqual("OVC APPROVE SRFDI-G-JUNE-AUTH AUTHORIZE_JUNE", self.packet["exact_operator_command"])
        self.assertEqual(
            "2c34a663201adc612cb452467ad61d694a8bb74a528cb858186a06a029381e29",
            self.packet["exact_run_binding"]["manifest_binding_sha256"],
        )
        self.assertEqual(
            "576608343486e6fe5e0992b2e165491f7fea1c6401c202e0056a10447992ae99",
            self.packet["exact_run_binding"]["source_population_binding_logical_sha256"],
        )
        self.assertEqual("PASS_GATE_READY_SUBJECT_TO_EXACT_HEAD_CI", self.qa["qa_conclusion"])
        self.assertEqual("DENIED_PENDING_NEW_EXACT_SRFDI_G_JUNE_AUTH", self.packet["current_authority"]["june_execution"])
        self.assertEqual("NONE", self.packet["proposed_authority_delta"]["scope_expansion"])


if __name__ == "__main__":
    unittest.main()
