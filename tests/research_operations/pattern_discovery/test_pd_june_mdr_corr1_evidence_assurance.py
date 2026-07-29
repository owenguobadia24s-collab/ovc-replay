from __future__ import annotations

import base64
import gzip
import hashlib
import json
import unittest
from pathlib import Path

from ovc.research_operations.pattern_discovery.clustering import build_partition_cluster_version
from ovc.research_operations.pattern_discovery.fingerprints import build_pattern_fingerprint
from ovc.research_operations.pattern_discovery.market_description_assurance import (
    ChronologySafeCandidateWindowManager,
    chronological_timeline,
    project_candidate_chronology,
    recompute_structural_comparison,
    trigger_history_requirement,
)
from ovc.research_operations.pattern_discovery.review import build_candidate_detail
from ovc.research_operations.pattern_discovery.transitions import extract_transitions
from ovc.research_operations.pattern_discovery.triggers import build_trigger_event


ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / "docs" / "releases" / "pattern-discovery-v0-3" / "pd-june-mdr-corr1"
BINDING = BASE / "PD_JUNE_MDR_CORR1_SOURCE_TO_C2_V2_BINDING_RECEIPT.json"
CHRONOLOGY = BASE / "PD_JUNE_MDR_CORR1_CHRONOLOGY_PROJECTION.json"
STRUCTURAL = BASE / "PD_JUNE_MDR_CORR1_REVIEWED_STRUCTURAL_ASSURANCE.json"
STRUCTURAL_LEDGER = BASE / "PD_JUNE_MDR_CORR1_REVIEWED_STRUCTURAL_ASSURANCE.json.gz.b64"
DRIVE = BASE / "PD_JUNE_MDR_CORR1_DRIVE_EVIDENCE_INVENTORY.json"
REPRO = BASE / "PD_JUNE_MDR_CORR1_CLAIM_TRIGGER_REPRODUCTION_SUMMARY.json"
DIGEST = BASE / "PD_JUNE_MDR_CORR1_CLAIM_TRIGGER_DIGEST.json.gz.b64"
GAPS = BASE / "PD_JUNE_MDR_CORR1_EVIDENCE_GAP_MANIFEST.json"
QA = BASE / "PD_JUNE_MDR_CORR1_QA_PACKET.json"
GATE = BASE / "PD_JUNE_MDR_G1_RETURN_GATE_PACKET.json"
STATE = ROOT / "registries" / "research_operations" / "pattern_discovery" / "PD_JUNE_2026_REVIEW_ASSURANCE_STATE_v0_1.json"
SCHEMA = ROOT / "schemas" / "research_operations" / "pattern_discovery" / "pd_june_mdr_corr1_return_gate_v0_1.schema.json"
FIXTURE = ROOT / "fixtures" / "research_operations" / "pattern_discovery" / "pd_wp1" / "c2_state_stream.json"


def _state(location: str, motion: str) -> dict:
    return {
        "axes": {
            "LOCATION": {"status": "EVALUATED", "value": location},
            "MOTION": {"status": "EVALUATED", "value": motion},
            "ORGANISATION": {"status": "EVALUATED", "value": "ORDERED"},
            "INTERACTION": {"status": "EVALUATED", "value": "TESTING"},
            "QUALITY": {"status": "EVALUATED", "value": "COMPLETE"},
        }
    }


def _fingerprint(index: int, duration: int) -> dict:
    candidate = {
        "window_id": f"PDW-CORR1-{index:04d}",
        "status": "READY_FOR_REVIEW",
        "source_release_id": "OPT-B.C2.GBPUSD.DISCOVERY.2021_2023.v2",
        "source_manifest_id": "MANIFEST.C2.OPT-B.C2.GBPUSD.DISCOVERY.2021_2023.v2.r1",
        "source_lineage_status": "RESOLVED",
        "window_start_utc": f"2026-06-22T0{index}:00:00Z",
        "window_end_utc": f"2026-06-22T0{index}:45:00Z",
        "clock": "15M",
        "price_side": "BID",
        "scope_id": "GBPUSD-15M-LOCAL-v0.1",
        "primary_transition_grammar": "STRUCTURAL_TRANSITION",
        "boundary_interaction_class": "BOUNDARY_INTERACTION",
        "parent_containment_class": "WITH_2H_PARENT",
        "closure_class": "PILOT_FIXED_HORIZON_4_RECORDS",
        "closure_reason": "PILOT_FIXED_HORIZON_4_RECORDS",
        "duration_records": duration,
        "trigger_event_ids": [f"PDTE-CORR1-{index:04d}"],
        "control_class": "NONE",
    }
    return build_pattern_fingerprint(
        candidate,
        state_sequence=[
            _state("MID_REGION", "UP_PROGRESS"),
            _state("UPPER_REGION", "UP_PROGRESS"),
            _state("UPPER_REGION", "UP_STALL"),
        ],
        transition_sequence=["AXIS.LOCATION", "AXIS.MOTION"],
        interaction_events=["BOUNDARY_ZONE_ENTRY"],
        cross_scale_context={"containment_class": "WITH_2H_PARENT"},
    )


class PDJuneMDRCorr1EvidenceAssuranceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.states = json.loads(FIXTURE.read_text(encoding="utf-8"))
        cls.binding = json.loads(BINDING.read_text(encoding="utf-8"))
        cls.chronology = json.loads(CHRONOLOGY.read_text(encoding="utf-8"))
        cls.structural = json.loads(STRUCTURAL.read_text(encoding="utf-8"))
        cls.drive = json.loads(DRIVE.read_text(encoding="utf-8"))
        cls.repro = json.loads(REPRO.read_text(encoding="utf-8"))
        cls.gaps = json.loads(GAPS.read_text(encoding="utf-8"))
        cls.qa = json.loads(QA.read_text(encoding="utf-8"))
        cls.gate = json.loads(GATE.read_text(encoding="utf-8"))
        cls.state = json.loads(STATE.read_text(encoding="utf-8"))

    def test_return_packet_files_exist(self) -> None:
        for path in (BINDING, CHRONOLOGY, STRUCTURAL, STRUCTURAL_LEDGER, DRIVE, REPRO, DIGEST, GAPS, QA, GATE, STATE, SCHEMA):
            self.assertTrue(path.is_file(), path)

    def test_carry_forward_binding_is_non_replaying(self) -> None:
        self.assertEqual(
            self.binding["status"],
            "PASS_SOURCE_BYTES_AND_REPLAY_ACCEPTANCE_CARRIED_FORWARD_TO_EXPLICIT_C2_V2_PILOT_IDENTITY",
        )
        self.assertEqual(self.binding["corrective_c2_release_id"], "OPT-B.C2.GBPUSD.DISCOVERY.2021_2023.v2")
        self.assertFalse(self.binding["interpretation"]["replay_performed_by_corr1"])
        self.assertFalse(self.binding["interpretation"]["source_bytes_changed"])

    def test_drive_inventory_verifies_every_source_manifest_member(self) -> None:
        self.assertEqual(self.drive["status"], "PASS_ALL_REQUIRED_EXISTING_SOURCE_AND_CORRECTIVE_PILOT_ARTIFACTS_LOCATED")
        self.assertEqual(self.drive["source_compute_manifest"]["verification"], "PASS_21_OF_21_HASH_AND_SIZE")
        self.assertEqual(len(self.drive["source_manifest_members"]), 21)
        self.assertTrue(all(item["hash_match"] and item["size_match"] for item in self.drive["source_manifest_members"]))
        self.assertEqual(self.drive["coverage"]["c1_record_count"], 602)
        self.assertEqual(self.drive["coverage"]["c2_state_count"], 1144)

    def test_claim_trigger_digest_is_exact_and_parseable(self) -> None:
        compressed = base64.b64decode(DIGEST.read_text(encoding="utf-8").strip(), validate=True)
        self.assertEqual(hashlib.sha256(compressed).hexdigest(), self.repro["ledger"]["compressed_sha256"])
        uncompressed = gzip.decompress(compressed)
        self.assertEqual(hashlib.sha256(uncompressed).hexdigest(), self.repro["ledger"]["uncompressed_sha256"])
        ledger = json.loads(uncompressed.decode("utf-8"))
        self.assertEqual(len(ledger["state_claim_digests"]), 48)
        self.assertEqual(len(ledger["trigger_reproduction"]), 26)
        self.assertTrue(all(item["exact_core_match"] for item in ledger["state_claim_digests"]))
        self.assertTrue(all(item["recomputed_fired"] and item["recorded_event_match"] == "PASS" for item in ledger["trigger_reproduction"]))

    def test_population_and_review_reproduction_are_exact(self) -> None:
        population = self.repro["population_state_reproduction"]
        review = self.repro["review_claim_evidence"]
        self.assertEqual(population["stored_state_count"], 1144)
        self.assertEqual(population["recomputed_state_count"], 1144)
        self.assertEqual(population["exact_core_match_count"], 1144)
        self.assertEqual(population["mismatch_count"], 0)
        self.assertEqual(population["axis_payload_count"], 5720)
        self.assertEqual(population["axis_payload_mismatch_count"], 0)
        self.assertEqual(review["state_claim_exact_match_count"], 48)
        self.assertEqual(review["trigger_reproduction_count"], 26)
        self.assertEqual(review["history_dependent_count"], 11)
        self.assertEqual(review["history_dependent_exact_reproduction_count"], 11)
        self.assertEqual(review["trigger_mismatch_count"], 0)

    def test_wick_balance_defect_is_preserved_but_not_a_c2_dependency(self) -> None:
        assurance = self.repro["c1_formula_assurance"]
        self.assertEqual(assurance["record_count"], 602)
        self.assertEqual(assurance["opposite_sign_count"], 589)
        self.assertEqual(assurance["zero_balance_match_count"], 13)
        self.assertEqual(assurance["c2_semantic_dependency"], "NONE")
        self.assertEqual(assurance["c2_state_exact_reproduction_despite_defect"], "PASS_1144_OF_1144")

    def test_chronology_and_structural_comparison_remain_exact(self) -> None:
        self.assertEqual(self.chronology["candidate_count"], 208)
        self.assertEqual(self.chronology["nonchronological_input_count"], 44)
        self.assertEqual(self.chronology["corrected_projection_nonchronological_count"], 0)
        compressed = base64.b64decode(STRUCTURAL_LEDGER.read_text(encoding="utf-8").strip(), validate=True)
        self.assertEqual(hashlib.sha256(compressed).hexdigest(), self.structural["ledger"]["compressed_sha256"])
        ledger = json.loads(gzip.decompress(compressed).decode("utf-8"))
        self.assertEqual(len(ledger["records"]), 26)
        self.assertEqual(self.structural["exact_distance_recomputation_count"], 24)
        self.assertEqual(self.structural["unassigned_small_sample_count"], 2)

    def test_return_gate_is_fail_closed_on_controls_and_agreement(self) -> None:
        self.assertEqual(self.gaps["status"], "GATE_READY_CONTROL_AND_AGREEMENT_EVIDENCE_REQUIRED")
        self.assertEqual({item["code"] for item in self.gaps["open_blockers"]}, {"PD-JUNE-MDR-006"})
        self.assertEqual(self.gate["gate_status"], "GATE_READY_OPERATOR_DECISION_REQUIRED")
        self.assertEqual(self.gate["recommended_decision"], "DEFER")
        self.assertEqual(self.gate["overall_answer"]["verdict"], "NOT_ESTABLISHED")
        self.assertEqual(self.state["status"], "GATE_READY")
        self.assertEqual(self.state["next_packet_on_defer"], "PD-JUNE-MDR-CORR2-CONTROL-AND-AGREEMENT-ASSURANCE")
        self.assertEqual(self.qa["recommendation"], "DEFER_TO_OPERATOR_REQUIRED_READ_ONLY_CONTROL_AND_AGREEMENT_ASSURANCE")

    def test_runtime_chronology_and_distance_controls_remain_enforced(self) -> None:
        candidate = {
            "timeline": [
                {"c2_state_id": "C2-B", "first_valid_time": "2026-06-22T00:15:00Z", "axes": {}},
                {"c2_state_id": "C2-A", "first_valid_time": "2026-06-22T00:00:00Z", "axes": {}},
            ],
            "source_c2_record_ids": ["C2-B", "C2-A"],
        }
        projection = project_candidate_chronology(candidate)
        self.assertEqual([row["c2_state_id"] for row in projection["timeline"]], ["C2-A", "C2-B"])
        self.assertEqual([row["c2_state_id"] for row in chronological_timeline(candidate["timeline"])], ["C2-A", "C2-B"])

        transitions = extract_transitions(self.states[0], self.states[1])
        trigger = build_trigger_event(
            trigger_id="TR-LOC-001",
            reason_code="BOUNDARY_ZONE_ENTRY",
            source_transitions=[item for item in transitions if item["axis_or_relation"] == "AXIS.LOCATION"],
            operation_mode="NON_EVIDENTIARY_REPLAY",
            closure_profile_id="CP-BOUNDARY-RESOLUTION",
            rate_limit_group="BOUNDARY_INTERACTION",
        )
        manager = ChronologySafeCandidateWindowManager()
        window = manager.open_from_trigger(self.states[1], trigger, trigger_family="STRUCTURAL_TRANSITION")
        window = manager.accumulate(window["window_id"], self.states[2])
        time_by_id = {item["c2_state_id"]: item["first_valid_time"] for item in self.states}
        self.assertEqual([time_by_id[item] for item in window["source_c2_record_ids"]], sorted(time_by_id[item] for item in window["source_c2_record_ids"]))

        population = [_fingerprint(index, 3 + index) for index in range(5)]
        version = build_partition_cluster_version(population)
        fingerprint = population[0]
        medoid_id = version["assignments"][fingerprint["fingerprint_id"]]
        medoid = next(item for item in population if item["fingerprint_id"] == medoid_id)
        comparison = recompute_structural_comparison(fingerprint, medoid, version, population)
        self.assertEqual(comparison["recorded_total_distance"], comparison["recomputed_total_distance"])

    def test_trigger_history_contract_and_authority_remain_frozen(self) -> None:
        self.assertEqual(trigger_history_requirement("LONG_PERSISTENCE")["minimum_records"], 4)
        self.assertEqual(trigger_history_requirement("REPEATED_SWITCHING")["minimum_records"], 6)
        authority = self.gate["current_authority"]
        self.assertEqual(authority["provider_intake"], "DENIED")
        self.assertEqual(authority["machine_replay"], "DENIED")
        self.assertEqual(authority["canonical_discovery_processing_or_append"], "DENIED")
        self.assertEqual(authority["selector_or_release_mutation"], "DENIED")
        self.assertEqual(authority["r2_publication"], "DENIED")
        self.assertEqual(authority["validation_consumption"], "LOCKED_UNCONSUMED")


if __name__ == "__main__":
    unittest.main()
