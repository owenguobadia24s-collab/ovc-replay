from __future__ import annotations

import json
from pathlib import Path
import unittest

from ovc.opt_b.srfd import june_authority_v05
from ovc.opt_b.srfd.serialization import logical_sha256

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "docs/releases/srfd-benchmark-v0-1/srfdi-june-auth-v0-5"
DECISION = BASE / "SRFDI_G_JUNE_AUTH_DELEGATED_DECISION_v0_5.json"
ENVELOPE = BASE / "SRFD_JUNE_AUTHORITY_ENVELOPE_v0_5.json"
TOKEN = BASE / "SRFD_JUNE_AUTHORITY_TOKEN_v0_5.json"
QA = BASE / "SRFDI_G_JUNE_AUTH_QA_v0_5.json"
OLD_MANIFEST = ROOT / "docs/releases/srfd-benchmark-v0-1/srfdi-june-auth-v0-4/SRFD_JUNE_AUTHORIZED_MANIFEST_v0_4.json"
PREREG = ROOT / "registries/research/srfd/SRFD_PREREGISTRATION_CANDIDATE_v0_4.json"
REP = ROOT / "registries/research/srfd/real_source_representation_packs_v0_2.json"
SEG = ROOT / "registries/research/srfd/segmentation_boundary_packs_v0_3.json"
STABILITY = ROOT / "registries/research/srfd/stability_metric_specs_v0_4.json"
STATE = ROOT / "registries/implementation/srfd/OVC_SRFDI_STATE_v0_20_JUNE_AUTH_V0_5_AUTHORIZED.json"
POINTER = ROOT / "registries/implementation/srfd/CURRENT_STATE_POINTER.json"
DELEGATION = ROOT / "registries/implementation/srfd/SRFDI_REMAINING_SEQUENCE_DELEGATION_v0_1.json"


class SRFDIJuneAuthV05DelegatedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.decision = json.loads(DECISION.read_text())
        cls.envelope = json.loads(ENVELOPE.read_text())
        cls.token = json.loads(TOKEN.read_text())
        cls.qa = json.loads(QA.read_text())
        cls.state = json.loads(STATE.read_text())
        cls.pointer = json.loads(POINTER.read_text())
        cls.delegation = json.loads(DELEGATION.read_text())

    def test_standing_delegation_authorizes_auto_continue_without_widening(self):
        self.assertEqual([], self.delegation["remaining_operator_stops"])
        self.assertEqual("682fdbf6893d37446926011d461157fbce5cf8f2", self.decision["standing_delegation"]["merge_commit"])
        self.assertEqual("DELEGATED_STANDING_OPERATOR_AUTHORITY", self.decision["decision_authority"])
        self.assertEqual("AUTHORIZE_JUNE", self.decision["decision"])

    def test_all_frozen_scientific_hashes_are_exact(self):
        self.assertEqual(june_authority_v05.SCIENTIFIC_MANIFEST_HASH, logical_sha256(json.loads(OLD_MANIFEST.read_text())))
        self.assertEqual(june_authority_v05.PREREG_V04_HASH, logical_sha256(json.loads(PREREG.read_text())))
        self.assertEqual(june_authority_v05.REP_PACK_HASH, logical_sha256(json.loads(REP.read_text())))
        self.assertEqual(june_authority_v05.SEGMENTATION_HASH, logical_sha256(json.loads(SEG.read_text())))
        self.assertEqual(june_authority_v05.STABILITY_HASH, logical_sha256(json.loads(STABILITY.read_text())))

    def test_new_token_reconstructs_and_consumed_v04_token_is_not_reused(self):
        reconstructed = june_authority_v05.verify_fresh_june_authority(self.decision, self.envelope, self.token)
        self.assertEqual(self.token, reconstructed)
        self.assertEqual("SRFD.JUNE.AUTH.eaa5a6e46365f673b796d4a966e600833f7528659b8528dc5f1ed27fd7cb5a1a", self.token["token_id"])
        self.assertNotEqual(june_authority_v05.PRIOR_V04_TOKEN, self.token["token_id"])
        self.assertEqual("CONSUMED_NOT_REUSABLE", self.envelope["prior_authority"]["v0_4_token_state"])

    def test_source_population_and_capacity_are_exact_and_fail_closed(self):
        source = self.envelope["source_population_binding"]
        self.assertEqual(9420, source["source_record_count"])
        self.assertEqual(8598, source["eligible_record_count"])
        self.assertEqual(june_authority_v05.SOURCE_RECORD_HASHES, source["source_record_hashes_sha256"])
        self.assertEqual(june_authority_v05.ELIGIBLE_IDS_HASH, source["eligible_record_ids_sha256"])
        self.assertEqual("FORBIDDEN", source["provider_fetch"])
        self.assertEqual("FORBIDDEN", source["upstream_mutation"])
        self.assertEqual(june_authority_v05.CAPACITY_GRID_HASH, self.envelope["implementation_binding"]["capacity_catalog_grid_hash"])
        self.assertTrue(self.envelope["capacity_binding"]["stop_on_capacity_exceeded"])

    def test_qa_and_state_open_only_one_exact_bound_run(self):
        self.assertEqual("PASS", self.qa["qa_result"])
        self.assertEqual([], self.qa["blocking_warnings"])
        self.assertEqual([], self.qa["unresolved_issues"])
        self.assertEqual("AUTHORIZED_ONE_EXACT_BOUND_RUN_UNCONSUMED", self.state["authority"]["market_benchmark"])
        self.assertFalse(self.state["authority"]["authority_token_consumed"])
        self.assertEqual(self.token["token_id"], self.pointer["authority_token_id"])
        self.assertEqual("SRFDI-WP10-v0.5", self.pointer["next_packet"])
        self.assertFalse(self.pointer["operator_decision_required"])
        self.assertEqual("DENIED", self.pointer["provider_fetch"])
        self.assertEqual("LOCKED_UNCONSUMED", self.pointer["validation_2025"])
        self.assertEqual("NONE", self.pointer["scientific_promotion"])
        self.assertEqual("NONE", self.pointer["probability_risk_exposure_execution"])


if __name__ == "__main__":
    unittest.main()
