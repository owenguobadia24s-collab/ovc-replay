from __future__ import annotations

import json
from pathlib import Path
import unittest

from ovc.opt_b.srfd import june_authority_v06
from ovc.opt_b.srfd.serialization import logical_sha256

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "docs/releases/srfd-benchmark-v0-1/srfdi-june-auth-v0-6"
DECISION = BASE / "SRFDI_G_JUNE_AUTH_DELEGATED_DECISION_v0_6.json"
ENVELOPE = BASE / "SRFD_JUNE_AUTHORITY_ENVELOPE_v0_6.json"
TOKEN = BASE / "SRFD_JUNE_AUTHORITY_TOKEN_v0_6.json"
QA = BASE / "SRFDI_G_JUNE_AUTH_QA_v0_6.json"
SOURCE_REVERIFY = BASE / "SRFD_SOURCE_ARTIFACT_REVERIFICATION_v0_6.json"
OLD_MANIFEST = ROOT / "docs/releases/srfd-benchmark-v0-1/srfdi-june-auth-v0-4/SRFD_JUNE_AUTHORIZED_MANIFEST_v0_4.json"
PREREG = ROOT / "registries/research/srfd/SRFD_PREREGISTRATION_CANDIDATE_v0_4.json"
REP = ROOT / "registries/research/srfd/real_source_representation_packs_v0_2.json"
SEG = ROOT / "registries/research/srfd/segmentation_boundary_packs_v0_3.json"
STABILITY = ROOT / "registries/research/srfd/stability_metric_specs_v0_4.json"
STATE = ROOT / "registries/implementation/srfd/OVC_SRFDI_STATE_v0_21_JUNE_AUTH_V0_6_AUTHORIZED.json"
POINTER = ROOT / "registries/implementation/srfd/CURRENT_STATE_POINTER.json"
DELEGATION = ROOT / "registries/implementation/srfd/SRFDI_REMAINING_SEQUENCE_DELEGATION_v0_1.json"
SFC_POINTER = ROOT / "registries/implementation/sfc/CURRENT_STATE_POINTER.json"


class SRFDIJuneAuthV06DelegatedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.decision = json.loads(DECISION.read_text())
        cls.envelope = json.loads(ENVELOPE.read_text())
        cls.token = json.loads(TOKEN.read_text())
        cls.qa = json.loads(QA.read_text())
        cls.source_reverify = json.loads(SOURCE_REVERIFY.read_text())
        cls.state = json.loads(STATE.read_text())
        cls.pointer = json.loads(POINTER.read_text())
        cls.delegation = json.loads(DELEGATION.read_text())
        cls.sfc_pointer = json.loads(SFC_POINTER.read_text())

    def test_sfc_terminal_release_and_standing_delegation_are_exact(self):
        self.assertEqual("COMPLETED", self.sfc_pointer["status"])
        self.assertEqual("PRESERVED", self.sfc_pointer["programme_disposition"])
        self.assertEqual(june_authority_v06.SFC_INTERLOCK_RELEASE, self.sfc_pointer["srfd_june_authority_interlock"])
        self.assertEqual([], self.delegation["remaining_operator_stops"])
        self.assertEqual(june_authority_v06.STANDING_DELEGATION_MERGE, self.decision["standing_delegation"]["merge_commit"])
        self.assertEqual("DELEGATED_STANDING_OPERATOR_AUTHORITY", self.decision["decision_authority"])

    def test_all_frozen_scientific_hashes_are_exact(self):
        self.assertEqual(june_authority_v06.SCIENTIFIC_MANIFEST_HASH, logical_sha256(json.loads(OLD_MANIFEST.read_text())))
        self.assertEqual(june_authority_v06.PREREG_V04_HASH, logical_sha256(json.loads(PREREG.read_text())))
        self.assertEqual(june_authority_v06.REP_PACK_HASH, logical_sha256(json.loads(REP.read_text())))
        self.assertEqual(june_authority_v06.SEGMENTATION_HASH, logical_sha256(json.loads(SEG.read_text())))
        self.assertEqual(june_authority_v06.STABILITY_HASH, logical_sha256(json.loads(STABILITY.read_text())))

    def test_source_artifact_reverification_is_exact_and_read_only(self):
        self.assertEqual(june_authority_v06.SOURCE_ARTIFACT_REVERIFICATION_HASH, logical_sha256(self.source_reverify))
        self.assertTrue(self.source_reverify["all_exact"])
        self.assertEqual(6, len(self.source_reverify["artifacts"]))
        self.assertEqual("DENIED", self.source_reverify["provider_fetch"])
        self.assertEqual("LOCKED_UNCONSUMED", self.source_reverify["validation_2025"])

    def test_new_token_reconstructs_and_neither_prior_identity_is_reused(self):
        reconstructed = june_authority_v06.verify_fresh_june_authority(self.decision, self.envelope, self.token, self.source_reverify, self.sfc_pointer)
        self.assertEqual(self.token, reconstructed)
        self.assertEqual(june_authority_v06.EXPECTED_TOKEN, self.token["token_id"])
        self.assertNotEqual(june_authority_v06.PRIOR_V04_TOKEN, self.token["token_id"])
        self.assertNotEqual(june_authority_v06.ATTEMPTED_V05_TOKEN, self.token["token_id"])
        self.assertEqual("CONSUMED_NOT_REUSABLE", self.envelope["prior_authority"]["v0_4_token_state"])
        self.assertEqual("NON_AUTHORITATIVE_UNMERGED_DO_NOT_REUSE", self.envelope["prior_authority"]["attempted_v0_5_token_state"])

    def test_exact_population_capacity_and_firewalls(self):
        source = self.envelope["source_population_binding"]
        self.assertEqual(9420, source["source_record_count"])
        self.assertEqual(8598, source["eligible_record_count"])
        self.assertEqual(june_authority_v06.SOURCE_RECORD_HASHES, source["source_record_hashes_sha256"])
        self.assertEqual(june_authority_v06.ELIGIBLE_IDS_HASH, source["eligible_record_ids_sha256"])
        self.assertEqual(36, self.decision["prerequisites"]["comparability_domain_count"])
        self.assertEqual(35380668, self.decision["prerequisites"]["exact_pair_opportunity_count"])
        self.assertEqual(1944, self.decision["prerequisites"]["family_configuration_count"])
        self.assertEqual(june_authority_v06.CAPACITY_GRID_HASH, self.envelope["implementation_binding"]["capacity_catalog_grid_hash"])
        self.assertTrue(self.envelope["capacity_binding"]["stop_on_capacity_exceeded"])
        self.assertEqual("FORBIDDEN", source["provider_fetch"])
        self.assertEqual("DENIED", self.pointer["provider_fetch"])
        self.assertEqual("LOCKED_UNCONSUMED", self.pointer["validation_2025"])

    def test_qa_and_state_open_only_one_exact_bound_run(self):
        self.assertEqual("PASS_PENDING_EXACT_HEAD_REPOSITORY_ASSURANCE", self.qa["qa_result"])
        self.assertEqual([], self.qa["blocking_warnings"])
        self.assertEqual([], self.qa["unresolved_issues"])
        self.assertEqual("AUTHORIZED_ONE_EXACT_BOUND_RUN_UNCONSUMED", self.state["authority"]["market_benchmark"])
        self.assertFalse(self.state["authority"]["authority_token_consumed"])
        self.assertEqual(self.token["token_id"], self.pointer["authority_token_id"])
        self.assertFalse(self.pointer["operator_decision_required"])
        self.assertEqual("NONE", self.pointer["scientific_promotion"])
        self.assertEqual("NONE", self.pointer["selector_family_semantic_publication"])
        self.assertEqual("NONE", self.pointer["probability_risk_exposure_execution"])
        if self.pointer["status"] == "BLOCKED":
            self.assertIsNone(self.pointer["next_packet"])
            self.assertTrue(self.pointer["authority_token_consumed"])
            self.assertEqual("CONSUMED_NOT_REUSABLE", self.pointer["authority_token_state"])
            self.assertEqual("SRFDI-G10", self.pointer["current_gate"])
        else:
            self.assertEqual("SRFDI-WP10-v0.6", self.pointer["next_packet"])


if __name__ == "__main__":
    unittest.main()
