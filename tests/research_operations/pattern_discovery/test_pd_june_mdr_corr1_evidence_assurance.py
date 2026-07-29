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
GAPS = BASE / "PD_JUNE_MDR_CORR1_EVIDENCE_GAP_MANIFEST.json"
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
        cls.gaps = json.loads(GAPS.read_text(encoding="utf-8"))

    def test_carry_forward_binding_resolves_v1_v2_interpretation_without_replay(self) -> None:
        self.assertEqual(
            self.binding["status"],
            "PASS_SOURCE_BYTES_AND_REPLAY_ACCEPTANCE_CARRIED_FORWARD_TO_EXPLICIT_C2_V2_PILOT_IDENTITY",
        )
        self.assertEqual(self.binding["source_binding_id"], "RPS.BINDING.32fb3003efa072916c11e907")
        self.assertEqual(self.binding["corrective_c2_release_id"], "OPT-B.C2.GBPUSD.DISCOVERY.2021_2023.v2")
        self.assertEqual(self.binding["evidence_chain"]["semantic_state_drift_count"], 0)
        self.assertEqual(self.binding["evidence_chain"]["semantic_transition_drift_count"], 0)
        self.assertFalse(self.binding["interpretation"]["replay_performed_by_corr1"])
        self.assertFalse(self.binding["interpretation"]["source_bytes_changed"])

    def test_exact_june_chronology_projection_is_fail_closed_and_complete(self) -> None:
        self.assertEqual(self.chronology["candidate_count"], 208)
        self.assertEqual(self.chronology["nonchronological_input_count"], 44)
        self.assertEqual(self.chronology["queue_promoted_nonchronological_input_count"], 4)
        self.assertEqual(self.chronology["corrected_projection_nonchronological_count"], 0)
        self.assertEqual(self.chronology["ledger"]["record_count"], 208)
        self.assertEqual(
            self.chronology["ledger"]["uncompressed_sha256"],
            "899e19d0038373a04365ac9715958a7934e7b09338902a9d2792ae547345202f",
        )
        self.assertEqual(self.chronology["mutation"], "NONE_READ_ONLY_PROJECTION_ONLY")

    def test_structural_ledger_hash_and_exact_review_counts(self) -> None:
        compressed = base64.b64decode(STRUCTURAL_LEDGER.read_text(encoding="utf-8").strip(), validate=True)
        self.assertEqual(hashlib.sha256(compressed).hexdigest(), self.structural["ledger"]["compressed_sha256"])
        uncompressed = gzip.decompress(compressed)
        self.assertEqual(hashlib.sha256(uncompressed).hexdigest(), self.structural["ledger"]["uncompressed_sha256"])
        ledger = json.loads(uncompressed.decode("utf-8"))
        self.assertEqual(len(ledger["records"]), 26)
        self.assertEqual(self.structural["reviewed_count"], 26)
        self.assertEqual(self.structural["queue_promoted_count"], 6)
        self.assertEqual(self.structural["nonqueue_stratified_count"], 20)
        self.assertEqual(self.structural["exact_distance_recomputation_count"], 24)
        self.assertEqual(self.structural["unassigned_small_sample_count"], 2)
        self.assertEqual(self.structural["source_price_join_status"], "PASS_ALL_REVIEWED_TIMELINE_RECORDS")
        self.assertEqual(self.structural["market_description_verdict"], "NOT_ESTABLISHED")

    def test_read_only_projection_orders_and_aligns_timeline(self) -> None:
        candidate = {
            "timeline": [
                {"c2_state_id": "C2-B", "first_valid_time": "2026-06-22T00:15:00Z", "axes": {}},
                {"c2_state_id": "C2-A", "first_valid_time": "2026-06-22T00:00:00Z", "axes": {}},
            ],
            "source_c2_record_ids": ["C2-B", "C2-A"],
        }
        projection = project_candidate_chronology(candidate)
        self.assertFalse(projection["original_is_chronological"])
        self.assertEqual([row["c2_state_id"] for row in projection["timeline"]], ["C2-A", "C2-B"])
        self.assertEqual(projection["source_c2_record_ids"], ["C2-A", "C2-B"])
        self.assertEqual(
            [row["c2_state_id"] for row in chronological_timeline(candidate["timeline"])],
            ["C2-A", "C2-B"],
        )

    def test_corrective_materializer_preserves_first_valid_order(self) -> None:
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
        times = [time_by_id[item] for item in window["source_c2_record_ids"]]
        self.assertEqual(times, sorted(times))

    def test_candidate_detail_defensively_projects_chronology(self) -> None:
        candidate = {
            "window_id": "PDW-REVIEW-CORR1",
            "status": "READY_FOR_REVIEW",
            "instrument": "GBPUSD",
            "clock": "15M",
            "price_side": "BID",
            "scope_id": "GBPUSD-15M-LOCAL-v0.1",
            "window_start_utc": "2026-06-22T00:00:00Z",
            "window_end_utc": "2026-06-22T00:15:00Z",
            "trigger_first_valid_at": "2026-06-22T00:00:00Z",
            "source_release_id": "OPT-B.C2.GBPUSD.DISCOVERY.2021_2023.v2",
            "source_manifest_id": "MANIFEST.C2.OPT-B.C2.GBPUSD.DISCOVERY.2021_2023.v2.r1",
            "source_c2_record_ids": ["C2-B", "C2-A"],
            "timeline": [
                {"c2_state_id": "C2-B", "first_valid_time": "2026-06-22T00:15:00Z", "axes": {}},
                {"c2_state_id": "C2-A", "first_valid_time": "2026-06-22T00:00:00Z", "axes": {}},
            ],
        }
        detail = build_candidate_detail(
            candidate,
            fingerprint={"fingerprint_id": "PDFP-CORR1", "fingerprint_version": "PD.FINGERPRINT.v0.1"},
        )
        self.assertEqual([row["c2_state_id"] for row in detail["timeline"]], ["C2-A", "C2-B"])
        self.assertEqual(detail["source_lineage"]["c2_record_ids"], ["C2-A", "C2-B"])
        self.assertFalse(detail["chronology_projection"]["original_is_chronological"])

    def test_frozen_distance_components_recompute_exactly(self) -> None:
        population = [_fingerprint(index, 3 + index) for index in range(5)]
        version = build_partition_cluster_version(population)
        self.assertEqual(version["build_status"], "PASS")
        fingerprint = population[0]
        medoid_id = version["assignments"][fingerprint["fingerprint_id"]]
        medoid = next(item for item in population if item["fingerprint_id"] == medoid_id)
        comparison = recompute_structural_comparison(fingerprint, medoid, version, population)
        self.assertEqual(comparison["recorded_total_distance"], comparison["recomputed_total_distance"])
        self.assertEqual(comparison["recorded_outlier"], comparison["recomputed_outlier"])
        self.assertEqual(
            set(comparison["raw_domain_distances"]),
            {"state_path", "transition_sequence", "interaction", "cross_scale", "duration_persistence", "quality"},
        )
        self.assertEqual(
            round(sum(comparison["weighted_domain_contributions"].values()), 12),
            comparison["recomputed_total_distance"],
        )

    def test_trigger_history_and_remaining_blockers_fail_closed(self) -> None:
        self.assertTrue(trigger_history_requirement("LONG_PERSISTENCE")["required"])
        self.assertEqual(trigger_history_requirement("LONG_PERSISTENCE")["minimum_records"], 4)
        self.assertTrue(trigger_history_requirement("REPEATED_SWITCHING")["required"])
        self.assertEqual(trigger_history_requirement("REPEATED_SWITCHING")["minimum_records"], 6)
        self.assertFalse(trigger_history_requirement("BOUNDARY_ZONE_ENTRY")["required"])
        self.assertEqual(self.gaps["status"], "BLOCKED_EXTERNAL_EVIDENCE_REQUIRED")
        open_codes = {item["code"] for item in self.gaps["open_blockers"]}
        self.assertEqual(open_codes, {"PD-JUNE-MDR-003", "PD-JUNE-MDR-004", "PD-JUNE-MDR-006"})
        self.assertEqual(self.structural["c1_claim_evidence_available_count"], 0)
        self.assertEqual(self.structural["trigger_history_required_missing_count"], 11)

    def test_authority_boundaries_remain_denied(self) -> None:
        authority = self.binding["authority"]
        for key in (
            "provider_intake",
            "machine_replay",
            "canonical_discovery_processing",
            "canonical_append",
            "selector_or_release_mutation",
            "r2_publication",
        ):
            self.assertEqual(authority[key], "DENIED")
        for key in ("semantic_promotion", "probability", "risk", "exposure", "trading", "execution", "agent_write"):
            self.assertEqual(authority[key], "NONE")
        self.assertEqual(authority["validation_consumption"], "LOCKED_UNCONSUMED")


if __name__ == "__main__":
    unittest.main()
