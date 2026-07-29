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
SUMMARY = BASE / "PD_JUNE_MDR_WP1_REVIEW_SUMMARY.md"
QA = BASE / "PD_JUNE_MDR_WP1_QA_PACKET.json"
GATE = BASE / "PD_JUNE_MDR_G1_OPERATOR_GATE_PACKET.json"
DECISION = BASE / "PD_JUNE_MDR_G1_OPERATOR_DECISION.json"
STATE = ROOT / "registries" / "research_operations" / "pattern_discovery" / "PD_JUNE_2026_REVIEW_ASSURANCE_STATE_v0_1.json"
SCHEMA = ROOT / "schemas" / "research_operations" / "pattern_discovery" / "pd_june_mdr_wp1_claim_level_review_v0_1.schema.json"


class PDJuneMDRWP1ClaimLevelReviewTests(unittest.TestCase):
    def setUp(self) -> None:
        self.report = json.loads(REPORT.read_text(encoding="utf-8"))
        compressed = base64.b64decode(LEDGER.read_text(encoding="utf-8").strip(), validate=True)
        self.assertEqual(hashlib.sha256(compressed).hexdigest(), self.report["ledger"]["compressed_sha256"])
        uncompressed = gzip.decompress(compressed)
        self.assertEqual(hashlib.sha256(uncompressed).hexdigest(), self.report["ledger"]["uncompressed_sha256"])
        self.ledger = json.loads(uncompressed.decode("utf-8"))
        self.inventory = json.loads(INVENTORY.read_text(encoding="utf-8"))
        self.qa = json.loads(QA.read_text(encoding="utf-8"))
        self.gate = json.loads(GATE.read_text(encoding="utf-8"))
        self.decision = json.loads(DECISION.read_text(encoding="utf-8"))
        self.state = json.loads(STATE.read_text(encoding="utf-8"))

    def test_packet_files_exist(self) -> None:
        for path in (REPORT, LEDGER, INVENTORY, SUMMARY, QA, GATE, DECISION, STATE, SCHEMA):
            self.assertTrue(path.is_file(), path)

    def test_exact_governed_hashes_match(self) -> None:
        artifacts = {item["role"]: item for item in self.inventory["artifacts"]}
        expected = {
            "CANDIDATES": "2a2c2fe2afa28c3f1c0311eef054359b3198c829ee2b0679aa1331ee50044664",
            "CLUSTER_VERSIONS": "ea70287833897597f498414f1647b09866ce9fabe9155a8c665f01eb16072e1c",
            "FINGERPRINTS": "86c098d5d724cfe640baf9c5403dacc91ca702999ad0c1e40f8ef3125b3b0cf9",
            "TRANSITIONS": "9906949d25ac47278bb8b51a08d500bd9ca110ba7daa0e827ba8e53ce375f2a9",
            "TRIGGER_EVENTS": "727ee8e273725366f4345715d2993f9d23d19da2aa8c4925528b17d6f377d0c1",
            "CONSOLE_BUNDLE": "bfe5e3aa99b1c14166a57235e0da3a466f200f1ddd56a4654e7345c70c5cc98c",
            "QUEUE_ITEMS": "f00e4bc5b725d51f7a24ce7126c33bd98362b274e7a430eb9f3c8e32669d88f7",
        }
        for role, digest in expected.items():
            self.assertEqual(artifacts[role]["sha256"], digest)
            self.assertTrue(artifacts[role]["expected_hash_match"])
        self.assertEqual(self.inventory["verification"]["expected_governed_hashes"], "PASS_7_OF_7")

    def test_review_population_and_sample_are_exact(self) -> None:
        sample = self.report["sample_construction"]
        aggregate = self.report["aggregate_claim_results"]
        self.assertEqual(sample["queue_promoted_reviewed"], 6)
        self.assertEqual(sample["nonqueue_population"], 202)
        self.assertEqual(sample["available_nonqueue_strata"], 20)
        self.assertEqual(sample["sampled_nonqueue_strata"], 20)
        self.assertEqual(sample["sample_size"], 20)
        self.assertEqual(sample["negative_control_count_in_population"], 0)
        self.assertEqual(len(self.ledger["review_units"]), 26)
        self.assertEqual(aggregate["all_reviewed_units"]["reviewed"], 26)
        self.assertEqual(aggregate["all_reviewed_units"]["fully_supported"], 0)
        self.assertEqual(aggregate["all_reviewed_units"]["semantic_description_not_evaluated"], 26)

    def test_price_joins_pass_but_model_binding_conflicts(self) -> None:
        verification = self.report["artifact_verification"]
        population = self.report["population_mechanical_findings"]
        self.assertTrue(verification["all_candidate_timeline_price_rows_available"])
        self.assertTrue(verification["all_candidate_timeline_price_rows_complete"])
        self.assertEqual(population["candidate_timeline_record_count"], 328)
        self.assertEqual(population["candidate_timeline_records_with_complete_price_bars"], 328)
        self.assertEqual(verification["source_binding_payload_c2_release_id"], "OPT-B.C2.GBPUSD.DISCOVERY.2021_2023.v1")
        self.assertEqual(verification["candidate_payload_c2_release_id"], "OPT-B.C2.GBPUSD.DISCOVERY.2021_2023.v2")
        self.assertEqual(verification["source_to_model_binding_status"], "CONFLICT_V1_BINDING_PAYLOAD_VS_V2_CANDIDATES")

    def test_chronology_failure_is_exact_and_preserves_prior_rejection(self) -> None:
        population = self.report["population_mechanical_findings"]
        self.assertEqual(population["serialized_nonchronological_candidate_count"], 44)
        self.assertEqual(population["serialized_nonchronological_queue_promoted_count"], 4)
        promoted = [unit for unit in self.ledger["review_units"] if unit["cohort"] == "QUEUE_PROMOTED"]
        rejected = next(unit for unit in promoted if unit["candidate_window_id"].endswith("4f41e21b6cd075e0fdbc40e4"))
        self.assertEqual(rejected["overall_claim_level_verdict"], "CONTRADICTED")
        self.assertEqual(rejected["prior_operator_review"]["final"], "REJECT_PILOT_OBJECT")
        timeline_claim = next(claim for claim in rejected["claims"] if claim["claim_id"].endswith(".TIMELINE"))
        self.assertEqual(timeline_claim["chronology_status"], "FAIL_SERIALIZED_ORDER")
        self.assertEqual(timeline_claim["factual_status"], "CONTRADICTED")

    def test_reliability_fails_closed(self) -> None:
        dimensions = self.report["reliability_dimensions"]
        self.assertEqual(dimensions["artifact_hash_and_identity_integrity"], "PASS")
        self.assertEqual(dimensions["serialized_timeline_chronology"], "FAIL_44_OF_208_AND_4_OF_6_PROMOTED_NONCHRONOLOGICAL")
        self.assertEqual(dimensions["source_to_c2_v2_binding"], "FAIL_BINDING_PAYLOAD_NAMES_C2_V1")
        self.assertEqual(dimensions["external_market_description_validity"], "NOT_ESTABLISHED")
        self.assertEqual(dimensions["population_level_consistency"], "NOT_ESTABLISHED")
        self.assertEqual(self.report["overall_answer"]["verdict"], "NOT_ESTABLISHED")
        self.assertEqual(self.report["overall_answer"]["recommended_gate_decision"], "DEFER")

    def test_operator_defer_is_recorded_and_bounded_through_corr1(self) -> None:
        self.assertEqual(self.gate["gate_id"], "PD-JUNE-MDR-G1")
        self.assertTrue(self.gate["operator_approval_required"])
        self.assertEqual(self.gate["recommended_decision"], "DEFER")
        self.assertEqual(self.decision["decision"], "DEFER")
        self.assertEqual(self.decision["decision_authority"], "OPERATOR")
        self.assertEqual(self.decision["authority_delta"]["next_packet"], "PD-JUNE-MDR-CORR1")
        self.assertEqual(self.state["status"], "BLOCKED")
        self.assertEqual(self.state["packet_id"], "PD-JUNE-MDR-CORR1")
        self.assertEqual(self.state["next_packet"], "PD-JUNE-MDR-CORR1-EVIDENCE-BINDING-CONTINUATION")
        self.assertEqual(self.state["next_packet_status"], "BLOCKED_EXACT_EXTERNAL_EVIDENCE_REQUIRED")
        self.assertEqual(self.state["source_to_c2_v2_binding"], "PASS_CARRY_FORWARD_RECEIPT")
        self.assertEqual(self.qa["recommendation"], "DEFER")

    def test_authority_boundary_is_unchanged(self) -> None:
        authority = self.report["authority"]
        for key in (
            "provider_intake", "machine_replay", "canonical_discovery_processing",
            "canonical_append", "selector_or_release_mutation", "r2_publication",
        ):
            self.assertEqual(authority[key], "DENIED")
        for key in (
            "formula_or_trigger_change", "distance_cluster_threshold_or_model_change",
            "semantic_family_candidate_or_novelty_promotion", "probability", "risk",
            "exposure", "trading", "execution", "agent_write",
        ):
            self.assertEqual(authority[key], "NONE")
        self.assertEqual(authority["validation_consumption"], "LOCKED_UNCONSUMED")
        self.assertEqual(self.report["scope"]["canonical_2021_2023_discovery"], "DENIED")
        self.assertEqual(self.report["scope"]["second_replay"], "DENIED")
        self.assertIn("MACHINE_REPLAY", self.state["retained_prohibitions"])
        self.assertIn("CANONICAL_2021_2023_DISCOVERY_PROCESSING_OR_APPEND", self.state["retained_prohibitions"])


if __name__ == "__main__":
    unittest.main()
