from __future__ import annotations

import base64
import gzip
import hashlib
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / "docs" / "releases" / "pattern-discovery-v0-3" / "pd-june-mdr-wp1"
REPORT = BASE / "PD_JUNE_MDR_WP1_CLAIM_LEVEL_REVIEW.json"
LEDGER = BASE / "PD_JUNE_MDR_WP1_CLAIM_LEVEL_REVIEW.json.gz.b64"
INVENTORY = BASE / "PD_JUNE_MDR_WP1_EXTERNAL_ARTIFACT_INVENTORY.json"
GATE = BASE / "PD_JUNE_MDR_G1_OPERATOR_GATE_PACKET.json"
WP1_DECISION = BASE / "PD_JUNE_MDR_G1_OPERATOR_DECISION.json"
CORR1_DECISION = ROOT / "docs" / "releases" / "pattern-discovery-v0-3" / "pd-june-mdr-corr1" / "PD_JUNE_MDR_G1_CORR1_OPERATOR_DECISION.json"
CORR2_DECISION = ROOT / "docs" / "releases" / "pattern-discovery-v0-3" / "pd-june-mdr-corr2" / "PD_JUNE_MDR_G1_CORR2_OPERATOR_DECISION.json"
STATE = ROOT / "registries" / "research_operations" / "pattern_discovery" / "PD_JUNE_2026_REVIEW_ASSURANCE_STATE_v0_1.json"


class PDJuneMDRWP1ClaimLevelReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.report = json.loads(REPORT.read_text(encoding="utf-8"))
        compressed = base64.b64decode(LEDGER.read_text(encoding="utf-8").strip(), validate=True)
        cls.ledger = json.loads(gzip.decompress(compressed).decode("utf-8"))
        cls.inventory = json.loads(INVENTORY.read_text(encoding="utf-8"))
        cls.gate = json.loads(GATE.read_text(encoding="utf-8"))
        cls.wp1_decision = json.loads(WP1_DECISION.read_text(encoding="utf-8"))
        cls.corr1_decision = json.loads(CORR1_DECISION.read_text(encoding="utf-8"))
        cls.corr2_decision = json.loads(CORR2_DECISION.read_text(encoding="utf-8"))
        cls.state = json.loads(STATE.read_text(encoding="utf-8"))

    def test_exact_governed_hashes_and_sample_remain_preserved(self) -> None:
        self.assertEqual(self.inventory["verification"]["expected_governed_hashes"], "PASS_7_OF_7")
        self.assertEqual(len(self.ledger["review_units"]), 26)
        self.assertEqual(self.report["sample_construction"]["queue_promoted_reviewed"], 6)
        self.assertEqual(self.report["sample_construction"]["sample_size"], 20)

    def test_historical_binding_and_chronology_failures_remain_court_record(self) -> None:
        verification = self.report["artifact_verification"]
        population = self.report["population_mechanical_findings"]
        self.assertEqual(verification["source_to_model_binding_status"], "CONFLICT_V1_BINDING_PAYLOAD_VS_V2_CANDIDATES")
        self.assertEqual(population["serialized_nonchronological_candidate_count"], 44)
        self.assertEqual(population["serialized_nonchronological_queue_promoted_count"], 4)
        self.assertEqual(self.report["overall_answer"]["verdict"], "NOT_ESTABLISHED")

    def test_operator_decision_chain_is_complete(self) -> None:
        self.assertTrue(self.gate["operator_approval_required"])
        self.assertEqual(self.wp1_decision["decision"], "DEFER")
        self.assertEqual(self.wp1_decision["authority_delta"]["next_packet"], "PD-JUNE-MDR-CORR1")
        self.assertEqual(self.corr1_decision["decision"], "DEFER")
        self.assertEqual(self.corr1_decision["authority_delta"]["next_packet"], "PD-JUNE-MDR-CORR2-CONTROL-AND-AGREEMENT-ASSURANCE")
        self.assertEqual(self.corr2_decision["decision"], "DEFER")
        self.assertIsNone(self.corr2_decision["next_packet"])
        self.assertEqual(self.state["status"], "APPROVED")
        self.assertEqual(self.state["review_status"], "COMPLETED")
        self.assertIsNone(self.state["next_gate"])
        self.assertIsNone(self.state["next_packet"])

    def test_authority_boundary_is_unchanged(self) -> None:
        self.assertEqual(self.state["canonical_2021_2023_discovery"], "DEFERRED_NOT_AUTHORISED")
        self.assertEqual(self.state["second_june_replay"], "DENIED_NOT_REQUIRED")
        for prohibited in ("MACHINE_REPLAY", "CANONICAL_2021_2023_DISCOVERY_PROCESSING_OR_APPEND", "R2_PUBLICATION"):
            self.assertIn(prohibited, self.state["retained_prohibitions"])


if __name__ == "__main__":
    unittest.main()
