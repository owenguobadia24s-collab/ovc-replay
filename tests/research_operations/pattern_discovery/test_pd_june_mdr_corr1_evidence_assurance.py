from __future__ import annotations

import base64
import gzip
import hashlib
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / "docs" / "releases" / "pattern-discovery-v0-3" / "pd-june-mdr-corr1"
BINDING = BASE / "PD_JUNE_MDR_CORR1_SOURCE_TO_C2_V2_BINDING_RECEIPT.json"
CHRONOLOGY = BASE / "PD_JUNE_MDR_CORR1_CHRONOLOGY_PROJECTION.json"
STRUCTURAL = BASE / "PD_JUNE_MDR_CORR1_REVIEWED_STRUCTURAL_ASSURANCE.json"
STRUCTURAL_LEDGER = BASE / "PD_JUNE_MDR_CORR1_REVIEWED_STRUCTURAL_ASSURANCE.json.gz.b64"
DRIVE = BASE / "PD_JUNE_MDR_CORR1_DRIVE_EVIDENCE_INVENTORY.json"
REPRO = BASE / "PD_JUNE_MDR_CORR1_CLAIM_TRIGGER_REPRODUCTION_SUMMARY.json"
DIGEST = BASE / "PD_JUNE_MDR_CORR1_CLAIM_TRIGGER_DIGEST.json"
GAPS = BASE / "PD_JUNE_MDR_CORR1_EVIDENCE_GAP_MANIFEST.json"
CORR1_DECISION = BASE / "PD_JUNE_MDR_G1_CORR1_OPERATOR_DECISION.json"
CORR2_DECISION = ROOT / "docs" / "releases" / "pattern-discovery-v0-3" / "pd-june-mdr-corr2" / "PD_JUNE_MDR_G1_CORR2_OPERATOR_DECISION.json"
MERGE_RECEIPT = ROOT / "docs" / "releases" / "pattern-discovery-v0-3" / "pd-june-mdr-corr2" / "PD_JUNE_MDR_G1_CORR2_MERGE_RECEIPT.json"
STATE = ROOT / "registries" / "research_operations" / "pattern_discovery" / "PD_JUNE_2026_REVIEW_ASSURANCE_STATE_v0_1.json"


class PDJuneMDRCorr1EvidenceAssuranceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.binding = json.loads(BINDING.read_text(encoding="utf-8"))
        cls.chronology = json.loads(CHRONOLOGY.read_text(encoding="utf-8"))
        cls.structural = json.loads(STRUCTURAL.read_text(encoding="utf-8"))
        cls.drive = json.loads(DRIVE.read_text(encoding="utf-8"))
        cls.repro = json.loads(REPRO.read_text(encoding="utf-8"))
        cls.digest = json.loads(DIGEST.read_text(encoding="utf-8"))
        cls.gaps = json.loads(GAPS.read_text(encoding="utf-8"))
        cls.corr1_decision = json.loads(CORR1_DECISION.read_text(encoding="utf-8"))
        cls.corr2_decision = json.loads(CORR2_DECISION.read_text(encoding="utf-8"))
        cls.merge_receipt = json.loads(MERGE_RECEIPT.read_text(encoding="utf-8"))
        cls.state = json.loads(STATE.read_text(encoding="utf-8"))

    def test_binding_and_drive_inventory_are_exact(self) -> None:
        self.assertEqual(self.binding["status"], "PASS_SOURCE_BYTES_AND_REPLAY_ACCEPTANCE_CARRIED_FORWARD_TO_EXPLICIT_C2_V2_PILOT_IDENTITY")
        self.assertFalse(self.binding["interpretation"]["replay_performed_by_corr1"])
        self.assertEqual(self.drive["source_compute_manifest"]["verification"], "PASS_21_OF_21_HASH_AND_SIZE")
        self.assertEqual(len(self.drive["source_manifest_members"]), 21)

    def test_reproduction_and_digest_remain_exact(self) -> None:
        self.assertEqual(self.digest["status"], "PASS_EXACT_EVIDENCE_DIGESTS_BOUND")
        self.assertEqual(self.repro["population_state_reproduction"]["exact_core_match_count"], 1144)
        self.assertEqual(self.repro["population_state_reproduction"]["mismatch_count"], 0)
        self.assertEqual(self.repro["review_claim_evidence"]["state_claim_exact_match_count"], 48)
        self.assertEqual(self.repro["review_claim_evidence"]["trigger_reproduction_count"], 26)
        self.assertEqual(self.repro["review_claim_evidence"]["history_dependent_exact_reproduction_count"], 11)

    def test_chronology_and_structural_assurance_remain_exact(self) -> None:
        self.assertEqual(self.chronology["candidate_count"], 208)
        self.assertEqual(self.chronology["corrected_projection_nonchronological_count"], 0)
        compressed = base64.b64decode(STRUCTURAL_LEDGER.read_text(encoding="utf-8").strip(), validate=True)
        self.assertEqual(hashlib.sha256(compressed).hexdigest(), self.structural["ledger"]["compressed_sha256"])
        self.assertEqual(len(json.loads(gzip.decompress(compressed).decode("utf-8"))["records"]), 26)

    def test_operator_decision_chain_and_merge_are_complete(self) -> None:
        self.assertEqual(self.corr1_decision["decision"], "DEFER")
        self.assertEqual(self.corr1_decision["authority_delta"]["next_packet"], "PD-JUNE-MDR-CORR2-CONTROL-AND-AGREEMENT-ASSURANCE")
        self.assertEqual(self.corr2_decision["decision"], "DEFER")
        self.assertIsNone(self.corr2_decision["next_packet"])
        self.assertEqual(self.merge_receipt["merge_result"], "PASS_SQUASH_MERGED_TO_MAIN")
        self.assertEqual(self.state["status"], "COMPLETED")
        self.assertEqual(self.state["review_status"], "COMPLETED")
        self.assertIsNone(self.state["next_packet"])

    def test_authority_remains_frozen(self) -> None:
        self.assertEqual(self.state["canonical_2021_2023_discovery"], "DEFERRED_NOT_AUTHORISED")
        self.assertEqual(self.state["second_june_replay"], "DENIED_NOT_REQUIRED")
        for prohibited in ("PROVIDER_INTAKE", "MACHINE_REPLAY", "CANONICAL_2021_2023_DISCOVERY_PROCESSING_OR_APPEND", "R2_PUBLICATION", "VALIDATION_CONSUMPTION"):
            self.assertIn(prohibited, self.state["retained_prohibitions"])


if __name__ == "__main__":
    unittest.main()
