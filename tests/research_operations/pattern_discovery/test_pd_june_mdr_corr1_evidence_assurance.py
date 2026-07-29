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
QA = BASE / "PD_JUNE_MDR_CORR1_QA_PACKET.json"
GATE = BASE / "PD_JUNE_MDR_G1_RETURN_GATE_PACKET.json"
STATE = ROOT / "registries" / "research_operations" / "pattern_discovery" / "PD_JUNE_2026_REVIEW_ASSURANCE_STATE_v0_1.json"
SCHEMA = ROOT / "schemas" / "research_operations" / "pattern_discovery" / "pd_june_mdr_corr1_return_gate_v0_1.schema.json"


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
        cls.qa = json.loads(QA.read_text(encoding="utf-8"))
        cls.gate = json.loads(GATE.read_text(encoding="utf-8"))
        cls.state = json.loads(STATE.read_text(encoding="utf-8"))

    def test_return_packet_files_exist(self) -> None:
        for path in (BINDING, CHRONOLOGY, STRUCTURAL, STRUCTURAL_LEDGER, DRIVE, REPRO, DIGEST, GAPS, QA, GATE, STATE, SCHEMA):
            self.assertTrue(path.is_file(), path)

    def test_binding_and_drive_inventory_are_exact(self) -> None:
        self.assertEqual(
            self.binding["status"],
            "PASS_SOURCE_BYTES_AND_REPLAY_ACCEPTANCE_CARRIED_FORWARD_TO_EXPLICIT_C2_V2_PILOT_IDENTITY",
        )
        self.assertFalse(self.binding["interpretation"]["replay_performed_by_corr1"])
        self.assertFalse(self.binding["interpretation"]["source_bytes_changed"])
        self.assertEqual(self.drive["source_compute_manifest"]["verification"], "PASS_21_OF_21_HASH_AND_SIZE")
        self.assertEqual(len(self.drive["source_manifest_members"]), 21)
        self.assertTrue(all(item["hash_match"] and item["size_match"] for item in self.drive["source_manifest_members"]))

    def test_compact_digest_receipt_matches_reproduction_summary(self) -> None:
        self.assertEqual(self.digest["status"], "PASS_EXACT_EVIDENCE_DIGESTS_BOUND")
        self.assertEqual(self.digest["state_claims"]["record_count"], 48)
        self.assertEqual(self.digest["state_claims"]["exact_core_match_count"], 48)
        self.assertEqual(self.digest["state_claims"]["mismatch_count"], 0)
        self.assertEqual(self.digest["state_claims"]["canonical_records_sha256"], self.repro["ledger"]["state_claim_records_sha256"])
        self.assertEqual(self.digest["trigger_reproduction"]["record_count"], 26)
        self.assertEqual(self.digest["trigger_reproduction"]["history_dependent_exact_match_count"], 11)
        self.assertEqual(self.digest["trigger_reproduction"]["mismatch_count"], 0)
        self.assertEqual(self.digest["trigger_reproduction"]["canonical_records_sha256"], self.repro["ledger"]["trigger_records_sha256"])
        self.assertEqual(self.digest["full_evidence"]["canonical_json_sha256"], self.repro["ledger"]["full_evidence_canonical_sha256"])
        self.assertEqual(self.digest["superseded_artifact"]["status"], "SUPERSEDED_ENCODING_DEFECT_NOT_USED_FOR_GATE")

    def test_population_review_and_formula_assurance_are_exact(self) -> None:
        population = self.repro["population_state_reproduction"]
        review = self.repro["review_claim_evidence"]
        formula = self.repro["c1_formula_assurance"]
        self.assertEqual(population["exact_core_match_count"], 1144)
        self.assertEqual(population["mismatch_count"], 0)
        self.assertEqual(population["axis_payload_mismatch_count"], 0)
        self.assertEqual(review["state_claim_exact_match_count"], 48)
        self.assertEqual(review["trigger_reproduction_count"], 26)
        self.assertEqual(review["history_dependent_exact_reproduction_count"], 11)
        self.assertEqual(review["trigger_mismatch_count"], 0)
        self.assertEqual(formula["opposite_sign_count"], 589)
        self.assertEqual(formula["zero_balance_match_count"], 13)
        self.assertEqual(formula["c2_semantic_dependency"], "NONE")

    def test_chronology_and_structural_assurance_remain_exact(self) -> None:
        self.assertEqual(self.chronology["candidate_count"], 208)
        self.assertEqual(self.chronology["nonchronological_input_count"], 44)
        self.assertEqual(self.chronology["corrected_projection_nonchronological_count"], 0)
        compressed = base64.b64decode(STRUCTURAL_LEDGER.read_text(encoding="utf-8").strip(), validate=True)
        self.assertEqual(hashlib.sha256(compressed).hexdigest(), self.structural["ledger"]["compressed_sha256"])
        ledger = json.loads(gzip.decompress(compressed).decode("utf-8"))
        self.assertEqual(len(ledger["records"]), 26)
        self.assertEqual(self.structural["exact_distance_recomputation_count"], 24)
        self.assertEqual(self.structural["unassigned_small_sample_count"], 2)

    def test_return_gate_fails_closed_on_controls_and_agreement(self) -> None:
        self.assertEqual(self.gaps["status"], "GATE_READY_CONTROL_AND_AGREEMENT_EVIDENCE_REQUIRED")
        self.assertEqual({item["code"] for item in self.gaps["open_blockers"]}, {"PD-JUNE-MDR-006"})
        self.assertEqual(self.gate["gate_status"], "GATE_READY_OPERATOR_DECISION_REQUIRED")
        self.assertEqual(self.gate["recommended_decision"], "DEFER")
        self.assertEqual(self.gate["overall_answer"]["verdict"], "NOT_ESTABLISHED")
        self.assertEqual(self.state["status"], "GATE_READY")
        self.assertEqual(self.state["next_packet_on_defer"], "PD-JUNE-MDR-CORR2-CONTROL-AND-AGREEMENT-ASSURANCE")
        self.assertEqual(self.qa["recommendation"], "DEFER_TO_OPERATOR_REQUIRED_READ_ONLY_CONTROL_AND_AGREEMENT_ASSURANCE")

    def test_authority_remains_frozen(self) -> None:
        authority = self.gate["current_authority"]
        self.assertEqual(authority["provider_intake"], "DENIED")
        self.assertEqual(authority["machine_replay"], "DENIED")
        self.assertEqual(authority["canonical_discovery_processing_or_append"], "DENIED")
        self.assertEqual(authority["selector_or_release_mutation"], "DENIED")
        self.assertEqual(authority["r2_publication"], "DENIED")
        self.assertEqual(authority["validation_consumption"], "LOCKED_UNCONSUMED")


if __name__ == "__main__":
    unittest.main()
