from __future__ import annotations

import copy
import unittest

from ovc.research_operations.pattern_discovery.clustering import build_partition_cluster_version
from ovc.research_operations.pattern_discovery.fingerprints import build_pattern_fingerprint
from ovc.research_operations.pattern_discovery.market_description_assurance import recompute_structural_comparison
from ovc.research_operations.pattern_discovery.models import PatternDiscoveryError
from ovc.research_operations.pattern_discovery.review import build_candidate_detail


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


def _fingerprint(index: int) -> dict:
    candidate = {
        "window_id": f"PDW-CORR1-EDGE-{index:04d}",
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
        "duration_records": 3 + index,
        "trigger_event_ids": [f"PDTE-CORR1-EDGE-{index:04d}"],
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


class PDJuneMDRCorr1FailClosedEdgeTests(unittest.TestCase):
    def test_nonchronological_legacy_display_rows_without_identities_are_rejected(self) -> None:
        candidate = {
            "window_id": "PDW-CORR1-LEGACY-BAD",
            "status": "READY_FOR_REVIEW",
            "clock": "15M",
            "price_side": "BID",
            "source_release_id": "OPT-B.C2.GBPUSD.DISCOVERY.2021_2023.v1",
            "source_manifest_id": "MANIFEST-C2-v1",
            "source_c2_record_ids": ["C2-A", "C2-B"],
            "timeline": [
                {"time": "2026-06-22T00:15:00Z", "location": "UPPER_REGION"},
                {"time": "2026-06-22T00:00:00Z", "location": "MID_REGION"},
            ],
        }
        fingerprint = {"fingerprint_id": "PDFP-CORR1-LEGACY-BAD", "fingerprint_version": "PD.FINGERPRINT.v0.1"}
        with self.assertRaisesRegex(PatternDiscoveryError, "lacks exact C2 identities"):
            build_candidate_detail(candidate, fingerprint=fingerprint)

    def test_duplicate_partition_fingerprint_identities_are_rejected(self) -> None:
        population = [_fingerprint(index) for index in range(5)]
        version = build_partition_cluster_version(population)
        fingerprint = population[0]
        medoid_id = version["assignments"][fingerprint["fingerprint_id"]]
        medoid = next(item for item in population if item["fingerprint_id"] == medoid_id)
        duplicate_population = population + [copy.deepcopy(population[-1])]
        with self.assertRaisesRegex(PatternDiscoveryError, "duplicate partition fingerprint identities"):
            recompute_structural_comparison(fingerprint, medoid, version, duplicate_population)


if __name__ == "__main__":
    unittest.main()
