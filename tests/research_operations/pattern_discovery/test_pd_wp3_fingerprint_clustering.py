from __future__ import annotations

import copy
import unittest

from ovc.research_operations.pattern_discovery import (
    DistancePack,
    PatternDiscoveryError,
    ScalePack,
    build_cluster_versions,
    build_partition_cluster_version,
    build_pattern_fingerprint,
    build_scale_pack,
    composite_distance,
    deterministic_pam,
    eligible_clustering_population,
    map_cluster_lineage,
)
from ovc.research_operations.pattern_discovery.distance import ScaleStat


def state(location: str, motion: str, organisation: str = "ORDERED", interaction: str = "TESTING", quality: str = "COMPLETE") -> dict:
    return {
        "axes": {
            "LOCATION": {"status": "EVALUATED", "value": location},
            "MOTION": {"status": "EVALUATED", "value": motion},
            "ORGANISATION": {"status": "EVALUATED", "value": organisation},
            "INTERACTION": {"status": "EVALUATED", "value": interaction},
            "QUALITY": {"status": "EVALUATED", "value": quality},
        }
    }


def fingerprint(index: int, *, group: str = "A", duration: int = 4) -> dict:
    candidate = {
        "window_id": f"PDW-FP-{index:04d}",
        "status": "READY_FOR_REVIEW",
        "source_release_id": "OPT-B.C2.GBPUSD.DISCOVERY.2021_2023.v1",
        "source_manifest_id": "MANIFEST-C2-v1",
        "source_lineage_status": "RESOLVED",
        "window_start_utc": f"2026-07-{1 + (index % 20):02d}T00:00:00Z",
        "window_end_utc": f"2026-07-{1 + (index % 20):02d}T01:00:00Z",
        "clock": "15M",
        "price_side": "BID",
        "scope_id": "GBPUSD-15M-LOCAL-v0.1",
        "primary_transition_grammar": "BOUNDARY_TEST",
        "boundary_interaction_class": "BREACH_RETURN",
        "parent_containment_class": "CONTAINED",
        "closure_class": "STABLE_RESOLUTION",
        "closure_reason": "STABLE_RESOLUTION",
        "duration_records": duration,
        "trigger_event_ids": [f"PDTE-{index:04d}"],
        "control_class": "NONE",
    }
    if group == "A":
        states = [state("MID_REGION", "UP_PROGRESS"), state("UPPER_REGION", "UP_PROGRESS"), state("UPPER_REGION", "UP_STALL")]
        transitions = ["AXIS.LOCATION", "AXIS.MOTION"]
        interactions = ["APPROACH", "BREACH"]
        cross = {"alignment": "ALIGNED", "parent_containment": "CONTAINED"}
    else:
        states = [state("MID_REGION", "DOWN_PROGRESS"), state("LOWER_REGION", "DOWN_PROGRESS"), state("LOWER_REGION", "DOWN_STALL")]
        transitions = ["AXIS.MOTION", "AXIS.LOCATION", "AXIS.INTERACTION"]
        interactions = ["APPROACH", "REJECTION"]
        cross = {"alignment": "CONFLICT", "parent_containment": "CONTAINED"}
    return build_pattern_fingerprint(
        candidate,
        state_sequence=states,
        transition_sequence=transitions,
        interaction_events=interactions,
        cross_scale_context=cross,
    )


class PatternDiscoveryWP3Tests(unittest.TestCase):
    def test_fingerprint_is_deterministic_and_outcome_free(self) -> None:
        first = fingerprint(1)
        second = fingerprint(1)
        self.assertEqual(first, second)
        self.assertTrue(first["fingerprint_id"].startswith("PDFP-"))
        prohibited_candidate = {
            "window_id": "PDW-BAD",
            "status": "READY_FOR_REVIEW",
            "source_release_id": "R",
            "source_manifest_id": "M",
            "window_start_utc": "2026-07-01T00:00:00Z",
            "window_end_utc": "2026-07-01T01:00:00Z",
            "clock": "15M",
            "price_side": "BID",
            "scope_id": "S",
            "primary_transition_grammar": "G",
            "boundary_interaction_class": "B",
            "parent_containment_class": "P",
            "closure_class": "C",
            "outcome": "WIN",
        }
        with self.assertRaisesRegex(PatternDiscoveryError, "prohibited fingerprint inputs"):
            build_pattern_fingerprint(
                prohibited_candidate,
                state_sequence=[state("MID_REGION", "BALANCED")],
                transition_sequence=[],
                interaction_events=[],
                cross_scale_context={},
            )

    def test_composite_distance_is_symmetric_and_identity_is_zero(self) -> None:
        left = fingerprint(1, group="A", duration=4)
        right = fingerprint(2, group="B", duration=8)
        scale = build_scale_pack([left, right])
        identity = composite_distance(left, left, scale_pack=scale)
        forward = composite_distance(left, right, scale_pack=scale)
        reverse = composite_distance(right, left, scale_pack=scale)
        self.assertEqual(identity["distance"], 0.0)
        self.assertEqual(forward["distance"], reverse["distance"])
        self.assertGreater(forward["distance"], 0.0)
        self.assertEqual(set(forward["domains"]), {"state_path", "transition_sequence", "interaction", "cross_scale", "duration_persistence", "quality"})

    def test_pam_is_arrival_order_invariant(self) -> None:
        population = [fingerprint(index, group="A" if index < 4 else "B", duration=3 + index) for index in range(8)]
        scale = build_scale_pack(population)
        forward = deterministic_pam(population, k=2, scale_pack=scale)
        reverse = deterministic_pam(list(reversed(population)), k=2, scale_pack=scale)
        self.assertEqual(forward["medoid_ids"], reverse["medoid_ids"])
        self.assertEqual(forward["assignments"], reverse["assignments"])
        self.assertEqual(forward["total_within_cluster_distance"], reverse["total_within_cluster_distance"])

    def test_tie_breaker_uses_lower_k_and_lexicographic_medoid(self) -> None:
        base = fingerprint(0)
        population = []
        for index in range(5):
            item = copy.deepcopy(base)
            item["fingerprint_id"] = f"PDFP-TIE-{index:02d}"
            item["candidate_window_id"] = f"PDW-TIE-{index:02d}"
            population.append(item)
        version = build_partition_cluster_version(population)
        self.assertEqual(version["build_status"], "PASS")
        self.assertEqual(version["selected_k"], 1)
        self.assertEqual(version["medoid_ids"], ["PDFP-TIE-00"])

    def test_better_late_representative_can_displace_early_medoid(self) -> None:
        base = fingerprint(0)
        fixed_scale = ScalePack(
            scale_id="TEST-SCALE",
            features={
                "duration_records": ScaleStat(0.0, 1.0),
                "transition_count": ScaleStat(0.0, 1.0),
                "switch_count": ScaleStat(0.0, 1.0),
                "max_persistence": ScaleStat(0.0, 1.0),
            },
        )

        def with_duration(identifier: str, value: float) -> dict:
            item = copy.deepcopy(base)
            item["fingerprint_id"] = identifier
            item["duration_persistence"] = {
                "duration_records": value,
                "transition_count": 2,
                "switch_count": 1,
                "max_persistence": 2,
            }
            return item

        early = [with_duration(f"PDFP-E-{index}", value) for index, value in enumerate([0.0, 0.5, 1.0, 1.5, 2.0])]
        early_medoid = deterministic_pam(early, k=1, scale_pack=fixed_scale)["medoid_ids"][0]
        expanded = early + [with_duration(f"PDFP-L-{index}", value) for index, value in enumerate([2.0, 2.1, 2.2, 2.3])]
        expanded_medoid = deterministic_pam(expanded, k=1, scale_pack=fixed_scale)["medoid_ids"][0]
        self.assertNotEqual(early_medoid, expanded_medoid)

    def test_small_sample_capacity_and_mixed_versions_fail_closed(self) -> None:
        small = build_partition_cluster_version([fingerprint(index) for index in range(4)])
        self.assertEqual(small["build_status"], "UNASSIGNED_SMALL_SAMPLE")

        base = fingerprint(0)
        over_capacity = []
        for index in range(501):
            item = copy.deepcopy(base)
            item["fingerprint_id"] = f"PDFP-CAP-{index:04d}"
            over_capacity.append(item)
        blocked = build_partition_cluster_version(over_capacity)
        self.assertEqual(blocked["build_status"], "CLUSTER_BUILD_CAPACITY_BLOCK")

        mixed = [fingerprint(index) for index in range(5)]
        mixed[-1] = copy.deepcopy(mixed[-1])
        mixed[-1]["fingerprint_version"] = "PD.FINGERPRINT.v9.9"
        with self.assertRaisesRegex(PatternDiscoveryError, "mixed fingerprint versions"):
            build_partition_cluster_version(mixed)

    def test_population_filters_and_cluster_lineage_are_explicit(self) -> None:
        valid = fingerprint(1)
        invalid = copy.deepcopy(fingerprint(2))
        invalid["candidate_status"] = "INVALID"
        replay = copy.deepcopy(fingerprint(3))
        replay["operation_mode"] = "NON_EVIDENTIARY_REPLAY"
        replay["prospective_count_requested"] = True
        population = eligible_clustering_population([valid, invalid, replay])
        self.assertEqual([item["fingerprint_id"] for item in population["included"]], [valid["fingerprint_id"]])
        self.assertEqual(len(population["excluded"]), 2)

        previous = {
            "clusters": [
                {"cluster_id": "OLD-A", "member_ids": ["1", "2", "3"]},
                {"cluster_id": "OLD-B", "member_ids": ["4", "5"]},
            ]
        }
        current = {
            "clusters": [
                {"cluster_id": "NEW-A", "member_ids": ["1", "2"]},
                {"cluster_id": "NEW-B", "member_ids": ["3", "4", "5"]},
            ]
        }
        relations = map_cluster_lineage(previous, current)
        relation_names = {item["relation"] for item in relations}
        self.assertIn("SPLIT", relation_names)
        self.assertIn("MERGED", relation_names)

    def test_multi_partition_build_never_competes_across_partitions(self) -> None:
        first_partition = [fingerprint(index, group="A") for index in range(5)]
        second_partition = []
        for index in range(5, 10):
            item = fingerprint(index, group="B")
            item = copy.deepcopy(item)
            item["partition"]["price_side"] = "ASK"
            item["fingerprint_id"] = f"PDFP-ASK-{index}"
            second_partition.append(item)
        versions = build_cluster_versions(first_partition + second_partition)
        self.assertEqual(len(versions), 2)
        self.assertNotEqual(versions[0]["partition"], versions[1]["partition"])


if __name__ == "__main__":
    unittest.main()
