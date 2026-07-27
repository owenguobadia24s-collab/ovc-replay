from __future__ import annotations

import copy
import unittest

from ovc.research_operations.pattern_discovery import (
    ControlSamplingPack,
    LatencyObservation,
    NoveltyBaseline,
    PatternDiscoveryError,
    QueuePolicy,
    assess_control_representation,
    canonical_signature,
    degradation_states,
    evaluate_persistence_trigger,
    evaluate_switching_trigger,
    evaluate_transition_triggers,
    extract_transitions,
    project_review_queue,
    required_control_counts,
    select_matched_control,
    select_population_control,
)


def snapshot(
    number: int,
    *,
    location: str = "MID_REGION",
    motion: str = "BALANCED",
    organisation: str = "FORMING",
    interaction: str = "APPROACHING",
    quality: str = "COMPLETE",
    parent: str = "CTR-PARENT-1",
) -> dict:
    minute = number * 15
    hour, minute = divmod(minute, 60)
    return {
        "c2_state_id": f"C2S-WP2-{number:04d}",
        "c2_release_id": "OPT-B.C2.GBPUSD.DISCOVERY.2021_2023.v1",
        "c2_manifest_id": "MANIFEST-OPT-B-C2-DISCOVERY-v1",
        "first_valid_time": f"2026-07-27T{hour:02d}:{minute:02d}:00Z",
        "clock": "15M",
        "side": "BID",
        "evaluation_scope_id": "GBPUSD-15M-LOCAL-v0.1",
        "parameter_pack_id": "C2.PARAMS.GBPUSD.DISCOVERY.v0.1",
        "selector_id": "OPT-B.C2.GBPUSD.DISCOVERY.ACTIVE",
        "authority_state": "FIXTURE",
        "relation_set_id": f"REL-{number:04d}",
        "level_ids": ["LVL-1", "LVL-2"],
        "container_ids": ["CTR-LOCAL-1", parent],
        "parent_container_id": parent,
        "boundary_or_relation_id": "LVL-2",
        "axes": {
            "LOCATION": {"status": "EVALUATED", "value": location},
            "MOTION": {"status": "EVALUATED", "value": motion},
            "ORGANISATION": {"status": "EVALUATED", "value": organisation},
            "INTERACTION": {"status": "EVALUATED", "value": interaction},
            "QUALITY": {"status": "EVALUATED", "value": quality},
        },
    }


class PatternDiscoveryWP2Tests(unittest.TestCase):
    def test_structural_triggers_have_fired_negative_and_not_evaluable_results(self) -> None:
        before = snapshot(1, organisation="COMPRESSION")
        after = snapshot(2, location="UPPER_REGION", motion="UP_DISPLACEMENT", organisation="ORDERED", interaction="CROSSING")
        transitions = extract_transitions(before, after)
        results = {item.trigger_id: item for item in evaluate_transition_triggers(before, after, transitions)}
        self.assertEqual(results["TR-LOC-001"].status, "FIRED")
        self.assertEqual(results["TR-INT-001"].status, "FIRED")
        self.assertEqual(results["TR-INT-002"].status, "NOT_FIRED")
        self.assertEqual(results["TR-ORG-001"].status, "FIRED")
        self.assertTrue(results["TR-LOC-001"].source_transition_ids)

        unavailable = copy.deepcopy(after)
        unavailable["c2_state_id"] = "C2S-WP2-0003"
        unavailable["first_valid_time"] = "2026-07-27T00:45:00Z"
        unavailable["axes"]["LOCATION"] = {"status": "NOT_EVALUABLE", "value": None, "reason_code": "SOURCE_GAP"}
        unavailable_transitions = extract_transitions(after, unavailable)
        unavailable_results = {item.trigger_id: item for item in evaluate_transition_triggers(after, unavailable, unavailable_transitions)}
        self.assertEqual(unavailable_results["TR-LOC-001"].status, "NOT_EVALUABLE")
        self.assertEqual(unavailable_results["TR-LOC-001"].not_evaluable_reason, "LOCATION_NOT_EVALUABLE")

    def test_return_inside_persistence_and_switching_are_first_crossing_only(self) -> None:
        breached = snapshot(1, interaction="BREACH_ACTIVE")
        inside = snapshot(2, interaction="RETURNED_INSIDE")
        results = {item.trigger_id: item for item in evaluate_transition_triggers(breached, inside, extract_transitions(breached, inside))}
        self.assertEqual(results["TR-INT-002"].status, "FIRED")

        persistent = [snapshot(index, motion="UP_PROGRESS") for index in range(1, 5)]
        persistence = evaluate_persistence_trigger(persistent, [], threshold=4)
        self.assertEqual(persistence.status, "FIRED")
        later = evaluate_persistence_trigger(persistent + [snapshot(5, motion="UP_PROGRESS")], [], threshold=4)
        self.assertEqual(later.status, "NOT_FIRED")

        switching = [
            snapshot(1, motion="UP_PROGRESS"),
            snapshot(2, motion="DOWN_PROGRESS"),
            snapshot(3, motion="UP_PROGRESS"),
            snapshot(4, motion="DOWN_PROGRESS"),
        ]
        result = evaluate_switching_trigger(switching, [], lookback=4, switch_threshold=3)
        self.assertEqual(result.status, "FIRED")

    def test_control_selection_and_representation_are_deterministic(self) -> None:
        source = snapshot(8)
        pack = ControlSamplingPack(seed="TEST", population_denominator=1, matched_denominator=1)
        first = select_population_control(source, pack=pack)
        second = select_population_control(source, pack=pack)
        self.assertEqual(first, second)
        self.assertTrue(first["selected"])

        target = {
            "window_id": "PDW-TARGET",
            "instrument": "GBPUSD",
            "price_side": "BID",
            "clock": "15M",
            "scope_id": "GBPUSD-15M-LOCAL-v0.1",
            "parent_container_id": "CTR-PARENT-1",
            "broad_structural_regime": "BALANCED",
        }
        matched = select_matched_control(source, target, broad_structural_regime="BALANCED", pack=pack)
        self.assertTrue(matched["selected"])
        self.assertEqual(matched["control_class"], "MATCHED_CONTROL")

        requirements = required_control_counts(50)
        self.assertEqual(requirements, {"total_controls": 10, "matched_controls": 5, "population_controls": 3})
        controls = ([{"selected": True, "control_class": "MATCHED_CONTROL"}] * 6) + ([{"selected": True, "control_class": "POPULATION_CONTROL"}] * 4)
        self.assertEqual(assess_control_representation(50, controls)["status"], "PASS")

    def test_novelty_baseline_and_shadow_never_change_queue_authority(self) -> None:
        baseline = NoveltyBaseline()
        first_signature = canonical_signature(transition_grammar=["AXIS.LOCATION"], parent_context="CONTAINED", closure_class="STABLE")
        assessment = baseline.assess(first_signature)
        self.assertTrue(assessment["unseen_signature"])
        self.assertIsNone(assessment["badge"])
        self.assertEqual(assessment["queue_ranking_weight"], 0.0)
        self.assertFalse(assessment["independent_promotion_permitted"])

        for index in range(60):
            signature = canonical_signature(
                transition_grammar=["AXIS.LOCATION", f"SEQ-{index % 4}"],
                parent_context="CONTAINED" if index % 2 == 0 else "ALIGNED",
                closure_class="STABLE",
            )
            baseline.record(
                signature,
                candidate_id=f"PDW-{index:04d}",
                eligible_day=f"2026-07-{1 + (index % 10):02d}",
                market_condition="TREND" if index % 2 == 0 else "RANGE",
                is_control=index < 12,
            )
        self.assertTrue(baseline.readiness()["ready_for_calibrated_shadow"])
        baseline.enter_calibrated_shadow(calibration_transition_id="PDCAL-001")
        shadow = baseline.assess(first_signature)
        self.assertTrue(str(shadow["badge"]).startswith("SHADOW_"))
        self.assertEqual(shadow["queue_ranking_weight"], 0.0)
        self.assertFalse(shadow["independent_promotion_permitted"])
        with self.assertRaisesRegex(PatternDiscoveryError, "OPERATOR_GATE_REQUIRED"):
            baseline.activate_ranking()

    def test_queue_projection_enforces_caps_and_control_reservation(self) -> None:
        candidates = []
        for index in range(20):
            family = "STRUCTURAL_TRANSITION" if index < 10 else "CROSS_SCALE_CONFLICT"
            control = "NONE"
            if index in {10, 11}:
                control = "MATCHED_CONTROL"
                family = "CONTROL"
            if index == 12:
                control = "POPULATION_CONTROL"
                family = "CONTROL"
            candidates.append({
                "window_id": f"PDW-{index:03d}",
                "trigger_family": family,
                "trigger_first_valid_at": f"2026-07-27T{index:02d}:00:00Z",
                "control_class": control,
            })
        candidates.append({
            "window_id": "PDW-INCIDENT",
            "trigger_family": "QUALITY_OR_INCIDENT",
            "trigger_first_valid_at": "2026-07-27T23:00:00Z",
            "control_class": "NONE",
        })
        result = project_review_queue(candidates, unresolved_queue_depth=38, policy=QueuePolicy())
        self.assertEqual(len(result["promoted"]), 12)
        self.assertLessEqual(result["metrics"]["family_counts"].get("STRUCTURAL_TRANSITION", 0), 3)
        self.assertIn("PDW-INCIDENT", {item["window_id"] for item in result["promoted"]})
        self.assertGreaterEqual(result["metrics"]["control_promotions"], 3)
        self.assertTrue(all(str(item["suppression_reason"]).startswith("SUPPRESSED_") for item in result["suppressed"]))

    def test_latency_degradation_is_explicit(self) -> None:
        states = degradation_states(LatencyObservation(6.0, 11.0, 16.0, consecutive_index_late_cycles=3))
        names = {item["state"] for item in states}
        self.assertEqual(names, {"DEGRADED_INDEX_LATENCY", "DEGRADED_TRIGGER_LATENCY", "STALE_QUEUE_PROJECTION"})
        index_state = next(item for item in states if item["state"] == "DEGRADED_INDEX_LATENCY")
        self.assertTrue(index_state["candidate_creation_paused"])


if __name__ == "__main__":
    unittest.main()
