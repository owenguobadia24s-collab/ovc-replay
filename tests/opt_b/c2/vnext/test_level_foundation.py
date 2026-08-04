from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from ovc.opt_b.c2_vnext.levels import (
    LevelContractError,
    PivotPolicy,
    assert_relation_cannot_mutate_level,
    baseline_pivot_policies,
    build_confirmed_pivot_level,
    build_context_reference,
    build_legacy_level_crosswalk,
    build_pivot_of_pivots,
    build_swing_graph,
    build_trailing_range_snapshot,
    detect_pivot_candidates,
    evaluate_selector,
    make_lifecycle_event,
    project_lifecycle,
)

ROOT = Path(__file__).resolve().parents[4]


def observation(
    index: int,
    *,
    high: float,
    low: float,
    side: str = "BID",
    segment_id: str | None = "SEGMENT.1",
    eligible: bool = True,
    release_id: str = "OPT-A.SYNTHETIC.v1",
) -> dict:
    start_minutes = index * 15
    end_minutes = (index + 1) * 15
    sh, sm = divmod(start_minutes, 60)
    eh, em = divmod(end_minutes, 60)
    start = f"2026-01-05T{sh:02d}:{sm:02d}:00Z"
    end = f"2026-01-05T{eh:02d}:{em:02d}:00Z"
    return {
        "observation_id": f"OBS.{side}.{index:03d}",
        "first_valid_time": end,
        "interval_start": start,
        "interval_end": end,
        "instrument": "GBPUSD",
        "side": side,
        "high": high,
        "low": low,
        "projection_eligibility": {"eligible": eligible},
        "continuity": {"status": "CONTIGUOUS", "segment_id": segment_id},
        "lineage": {"opt_a_release_id": release_id},
    }


def sequence(highs: list[float], lows: list[float] | None = None, **kwargs) -> list[dict]:
    lows = lows or [value - 0.5 for value in highs]
    return [observation(index, high=high, low=low, **kwargs) for index, (high, low) in enumerate(zip(highs, lows))]


def confirmed_level(*, value: float, first_valid_time: str, level_type: str, family: str = "CONFIRMED_PIVOT", side: str = "BID", clock_id: str = "LATTICE.15M.UTC_0000.v1", suffix: str = "A") -> dict:
    polarity = "HIGH" if level_type.endswith("HIGH") else "LOW"
    candidate = {
        "candidate_id": f"CANDIDATE.{suffix}",
        "policy_id": "PIVOT.15M.2L2R.S0.r1",
        "polarity": polarity,
        "anchor_observation_id": f"ANCHOR.{suffix}",
        "anchor_time": first_valid_time,
        "anchor_price": value,
        "clock_id": clock_id,
        "structural_depth": "S0",
        "generation_method": "RAW_OBSERVATION_PIVOT",
        "instrument": "GBPUSD",
        "side": side,
        "source_release_id": "OPT-A.SYNTHETIC.v1",
        "first_valid_time": first_valid_time,
        "status": "UNIQUE_CONFIRMED",
        "reason": "REGISTERED_LEFT_RIGHT_RULE_PASSED",
        "member_observation_ids": [f"OBS.{suffix}.1", f"OBS.{suffix}.2"],
        "tie_observation_ids": [f"ANCHOR.{suffix}"],
        "maturity": "SHADOW_EXPERIMENT",
        "authority": "CANDIDATE_EVIDENCE_ONLY",
    }
    result = build_confirmed_pivot_level(candidate)
    if family != "CONFIRMED_PIVOT":
        result["family"] = family
    return result


class LevelFoundationTests(unittest.TestCase):
    def test_unique_pivot_first_valid_is_right_confirmation_close(self) -> None:
        observations = sequence([1.0, 2.0, 5.0, 3.0, 2.0])
        policy = baseline_pivot_policies()[0]
        candidates = detect_pivot_candidates(observations, policy=policy, polarity="HIGH")
        anchor = next(item for item in candidates if item["anchor_observation_id"] == "OBS.BID.002")
        self.assertEqual("UNIQUE_CONFIRMED", anchor["status"])
        self.assertEqual(observations[4]["first_valid_time"], anchor["first_valid_time"])
        self.assertNotEqual(anchor["anchor_time"], anchor["first_valid_time"])
        level = build_confirmed_pivot_level(anchor)
        self.assertEqual("CONFIRMED_SWING_HIGH", level["level_type"])
        self.assertEqual(anchor["first_valid_time"], level["first_valid_time"])
        self.assertTrue(level["immutable"])
        self.assertEqual("NONE", level["authority"]["active_selector"])

    def test_plateau_rejection_and_censoring_never_create_level(self) -> None:
        policy = baseline_pivot_policies()[0]
        plateau = sequence([1.0, 5.0, 5.0, 3.0, 2.0])
        candidates = detect_pivot_candidates(plateau, policy=policy, polarity="HIGH")
        anchor = next(item for item in candidates if item["anchor_observation_id"] == "OBS.BID.002")
        self.assertEqual("AMBIGUOUS_PLATEAU", anchor["status"])
        self.assertGreater(len(anchor["tie_observation_ids"]), 1)
        with self.assertRaisesRegex(LevelContractError, "CANDIDATE_NOT_CONFIRMED"):
            build_confirmed_pivot_level(anchor)

        rejected = sequence([1.0, 4.0, 3.0, 5.0, 2.0])
        rejected_candidate = next(item for item in detect_pivot_candidates(rejected, policy=policy, polarity="HIGH") if item["anchor_observation_id"] == "OBS.BID.002")
        self.assertEqual("REJECTED_NOT_EXTREME", rejected_candidate["status"])

        censored = sequence([1.0, 2.0, 5.0, 3.0])
        censored_candidate = next(item for item in detect_pivot_candidates(censored, policy=policy, polarity="HIGH") if item["anchor_observation_id"] == "OBS.BID.002")
        self.assertEqual("CENSORED_CONFIRMATION", censored_candidate["status"])
        self.assertEqual("RIGHT_CONFIRMATION_UNAVAILABLE", censored_candidate["reason"])

    def test_gap_or_reset_in_confirmation_window_fails_closed(self) -> None:
        observations = sequence([1.0, 2.0, 5.0, 3.0, 2.0])
        observations[3]["projection_eligibility"]["eligible"] = False
        candidate = next(item for item in detect_pivot_candidates(observations, policy=baseline_pivot_policies()[0], polarity="HIGH") if item["anchor_observation_id"] == "OBS.BID.002")
        self.assertEqual("CENSORED_CONFIRMATION", candidate["status"])
        self.assertEqual("INELIGIBLE_OR_CENSORED_MEMBER", candidate["reason"])

        observations = sequence([1.0, 2.0, 5.0, 3.0, 2.0])
        observations[4]["continuity"]["segment_id"] = "SEGMENT.2"
        candidate = next(item for item in detect_pivot_candidates(observations, policy=baseline_pivot_policies()[0], polarity="HIGH") if item["anchor_observation_id"] == "OBS.BID.002")
        self.assertEqual("DISCONTINUITY_OR_RESET", candidate["reason"])

    def test_trailing_range_midpoint_is_parent_bound_and_refresh_is_versioned(self) -> None:
        observations = sequence([2.0, 5.0, 4.0], [1.0, 2.0, 2.5])
        first = build_trailing_range_snapshot(observations, horizon_id="HORIZON.TEST.3", clock_id="LATTICE.15M.UTC_0000.v1")
        extended = observations + [observation(3, high=4.5, low=2.2)]
        second = build_trailing_range_snapshot(extended, horizon_id="HORIZON.TEST.3", clock_id="LATTICE.15M.UTC_0000.v1")
        first_by_type = {item["level_type"]: item for item in first}
        second_by_type = {item["level_type"]: item for item in second}
        self.assertEqual(5.0, first_by_type["TRAILING_RANGE_HIGH"]["value"])
        self.assertEqual(1.0, first_by_type["TRAILING_RANGE_LOW"]["value"])
        midpoint = first_by_type["TRAILING_RANGE_MIDPOINT"]
        self.assertEqual(3.0, midpoint["value"])
        self.assertEqual(2, len(midpoint["parent_level_ids"]))
        self.assertEqual("DERIVED_REFERENCE", midpoint["family"])
        self.assertEqual(first_by_type["TRAILING_RANGE_HIGH"]["lineage_id"], second_by_type["TRAILING_RANGE_HIGH"]["lineage_id"])
        self.assertNotEqual(first_by_type["TRAILING_RANGE_HIGH"]["snapshot_version"], second_by_type["TRAILING_RANGE_HIGH"]["snapshot_version"])
        self.assertNotEqual(first_by_type["TRAILING_RANGE_HIGH"]["level_id"], second_by_type["TRAILING_RANGE_HIGH"]["level_id"])

    def test_same_price_different_family_clock_side_or_release_is_not_same_identity(self) -> None:
        pivot = confirmed_level(value=1.25, first_valid_time="2026-01-05T01:00:00Z", level_type="CONFIRMED_SWING_HIGH", suffix="P")
        window = build_trailing_range_snapshot(sequence([1.1, 1.25, 1.2]), horizon_id="HORIZON.TEST", clock_id="LATTICE.15M.UTC_0000.v1")[0]
        self.assertEqual(pivot["value"], window["value"])
        self.assertNotEqual(pivot["level_id"], window["level_id"])
        ask = confirmed_level(value=1.25, first_valid_time="2026-01-05T01:00:00Z", level_type="CONFIRMED_SWING_HIGH", side="ASK", suffix="ASK")
        two_hour = confirmed_level(value=1.25, first_valid_time="2026-01-05T01:00:00Z", level_type="CONFIRMED_SWING_HIGH", clock_id="LATTICE.2H.UTC_0000.v1", suffix="2H")
        self.assertNotEqual(pivot["level_id"], ask["level_id"])
        self.assertNotEqual(pivot["level_id"], two_hour["level_id"])

    def test_lifecycle_is_append_only_consumer_specific_and_preserves_definition(self) -> None:
        old = confirmed_level(value=1.2, first_valid_time="2026-01-05T01:00:00Z", level_type="CONFIRMED_SWING_LOW", suffix="OLD")
        new = confirmed_level(value=1.3, first_valid_time="2026-01-05T02:00:00Z", level_type="CONFIRMED_SWING_LOW", suffix="NEW")
        before = copy.deepcopy(old)
        events = [
            make_lifecycle_event(old, event_type="STALE_FOR_CONSUMER", event_time="2026-01-05T02:15:00Z", reason="AGE_POLICY", consumer_id="CONSUMER.A"),
            make_lifecycle_event(old, event_type="SUPERSEDED", event_time="2026-01-05T02:30:00Z", reason="NEW_POINTER", superseding_level_id=new["level_id"]),
        ]
        for_a = project_lifecycle([old, new], events, as_of_time="2026-01-05T03:00:00Z", consumer_id="CONSUMER.A")
        for_b = project_lifecycle([old, new], events, as_of_time="2026-01-05T03:00:00Z", consumer_id="CONSUMER.B")
        old_a = next(item for item in for_a if item["level_id"] == old["level_id"])
        old_b = next(item for item in for_b if item["level_id"] == old["level_id"])
        self.assertTrue(old_a["stale_for_consumer"])
        self.assertFalse(old_b["stale_for_consumer"])
        self.assertEqual("SUPERSEDED", old_a["state"])
        self.assertEqual(new["level_id"], old_a["superseded_by"])
        self.assertEqual(before, old)

    def test_crossing_or_relation_cannot_mutate_level(self) -> None:
        level = confirmed_level(value=1.2, first_valid_time="2026-01-05T01:00:00Z", level_type="CONFIRMED_SWING_HIGH", suffix="REL")
        assert_relation_cannot_mutate_level(level, copy.deepcopy(level))
        changed = copy.deepcopy(level)
        changed["value"] = 1.21
        with self.assertRaisesRegex(LevelContractError, "RELATION_MUTATED_LEVEL_DEFINITION"):
            assert_relation_cannot_mutate_level(level, changed)

    def test_complete_swing_graph_retains_all_nodes_and_legs(self) -> None:
        levels = [
            confirmed_level(value=1.3, first_valid_time="2026-01-05T01:00:00Z", level_type="CONFIRMED_SWING_HIGH", suffix="A"),
            confirmed_level(value=1.1, first_valid_time="2026-01-05T02:00:00Z", level_type="CONFIRMED_SWING_LOW", suffix="B"),
            confirmed_level(value=1.4, first_valid_time="2026-01-05T03:00:00Z", level_type="CONFIRMED_SWING_HIGH", suffix="C"),
        ]
        graph = build_swing_graph(levels)
        self.assertEqual(3, len(graph["nodes"]))
        self.assertEqual(2, len(graph["legs"]))
        self.assertTrue(graph["complete_history"])
        self.assertTrue(graph["current_pointer_is_derived"])
        self.assertEqual({item["level_id"] for item in levels}, {node["level_id"] for node in graph["nodes"]})

    def test_pivot_of_pivots_creates_explicit_hierarchy_without_cross_clock_equivalence(self) -> None:
        child_nodes = []
        for index, value in enumerate([1.0, 2.0, 5.0, 3.0, 2.0]):
            child_nodes.append({
                "swing_node_id": f"NODE.{index}", "value": value,
                "anchor_time": observation(index, high=value, low=value)["interval_end"],
                "first_valid_time": observation(index, high=value, low=value)["first_valid_time"],
            })
        child_graph = {"swing_graph_id": "GRAPH.S0", "nodes": child_nodes}
        policy = PivotPolicy("PIVOT.15M.S1.2L2R.POP.r1", 2, 2, "LATTICE.15M.UTC_0000.v1", structural_depth="S1", generation_method="PIVOT_OF_PIVOTS")
        result = build_pivot_of_pivots(child_graph, policy=policy, polarity="HIGH")
        self.assertEqual(1, len(result["parent_nodes"]))
        self.assertEqual("S1", result["parent_nodes"][0]["structural_depth"])
        self.assertGreaterEqual(len(result["hierarchy_edges"]), 5)
        self.assertEqual("SHADOW_ONLY", result["authority"])

    def test_selector_exposes_complete_candidates_ties_exclusions_and_null_fallback(self) -> None:
        first = confirmed_level(value=1.2, first_valid_time="2026-01-05T01:00:00Z", level_type="CONFIRMED_SWING_HIGH", suffix="SEL1")
        latest = confirmed_level(value=1.3, first_valid_time="2026-01-05T02:00:00Z", level_type="CONFIRMED_SWING_HIGH", suffix="SEL2")
        unique = evaluate_selector([first, latest], selector_id="SELECTOR.C2.LEVEL.LATEST_FIRST_VALID.r1", as_of_time="2026-01-05T03:00:00Z")
        self.assertEqual(latest["level_id"], unique["selected_level_id"])
        self.assertEqual(2, len(unique["candidate_ids"]))
        self.assertFalse(unique["active"])
        self.assertIsNone(unique["fallback_level_id"])

        tied = confirmed_level(value=1.1, first_valid_time="2026-01-05T02:00:00Z", level_type="CONFIRMED_SWING_LOW", suffix="SEL3")
        tie = evaluate_selector([latest, tied], selector_id="SELECTOR.C2.LEVEL.LATEST_FIRST_VALID.r1", as_of_time="2026-01-05T03:00:00Z")
        self.assertEqual("TIED_CANDIDATES", tie["reason"])
        self.assertIsNone(tie["selected_level_id"])
        self.assertEqual(2, len(tie["tie_ids"]))

        none = evaluate_selector([latest], selector_id="SELECTOR.C2.LEVEL.LATEST_FIRST_VALID.r1", as_of_time="2026-01-05T03:00:00Z", allowed_families=("WINDOW_BOUNDARY",))
        self.assertEqual("NO_ELIGIBLE_CANDIDATE", none["reason"])
        self.assertEqual([{"level_id": latest["level_id"], "reason": "EXCLUDED_FAMILY"}], none["exclusions"])

    def test_context_reference_links_parent_without_recreating_parent_authority(self) -> None:
        parent = confirmed_level(value=1.25, first_valid_time="2026-01-05T01:00:00Z", level_type="CONFIRMED_SWING_HIGH", clock_id="LATTICE.2H.UTC_0000.v1", suffix="PARENT")
        linked = build_context_reference(parent, local_scope_id="SCOPE.15M.LOCAL", as_of_time="2026-01-05T02:00:00Z")
        self.assertEqual("CONTEXT_REFERENCE", linked["family"])
        self.assertEqual([parent["level_id"]], linked["parent_level_ids"])
        self.assertTrue(linked["parent_authority_preserved"])
        self.assertNotEqual(parent["level_id"], linked["level_id"])
        with self.assertRaisesRegex(LevelContractError, "PARENT_LEVEL_NOT_FIRST_VALID"):
            build_context_reference(parent, local_scope_id="SCOPE.EARLY", as_of_time="2026-01-05T00:30:00Z")

    def test_legacy_crosswalk_is_non_mutating_and_explicit(self) -> None:
        level = confirmed_level(value=1.25, first_valid_time="2026-01-05T01:00:00Z", level_type="CONFIRMED_SWING_HIGH", suffix="XW")
        legacy = [
            {"legacy_level_id": "LEGACY.1", "legacy_type": "SWING_HIGH", "side": "BID", "value": 1.25},
            {"legacy_level_id": "LEGACY.2", "legacy_type": "RANGE_LOW", "side": "BID", "value": 1.10},
        ]
        before = copy.deepcopy(legacy)
        first = build_legacy_level_crosswalk(legacy, [level])
        second = build_legacy_level_crosswalk(list(reversed(legacy)), [level])
        self.assertEqual(before, legacy)
        self.assertEqual(first, second)
        self.assertEqual("MATCHED_UNIQUE", first[0]["match_status"])
        self.assertEqual("UNMATCHED", first[1]["match_status"])
        self.assertTrue(all(item["legacy_mutated"] is False for item in first))
        self.assertTrue(all(item["historical_name_preserved"] is True for item in first))

    def test_active_or_canonical_pivot_policy_is_denied(self) -> None:
        with self.assertRaisesRegex(LevelContractError, "PIVOT_POLICY_ACTIVATION_DENIED"):
            PivotPolicy("PIVOT.BAD.ACTIVE", 2, 2, "LATTICE.15M.UTC_0000.v1", active=True)
        with self.assertRaisesRegex(LevelContractError, "CANONICAL_PIVOT_POLICY_DENIED"):
            PivotPolicy("PIVOT.BAD.CANONICAL", 2, 2, "LATTICE.15M.UTC_0000.v1", canonical=True)

    def test_repository_contract_registry_schema_fixture_and_active_selector_boundary(self) -> None:
        contract = (ROOT / "contracts/opt_b/c2/C2_LEVEL_CONTRACT_vNext.md").read_text(encoding="utf-8")
        for item in [f"P3-D{number}" for number in range(1, 16)] + [f"P3-R{number}" for number in range(1, 10)] + [f"P3-Q{number}" for number in range(1, 6)]:
            self.assertIn(item, contract)
        self.assertIn("No numeric pivot policy or current selector is activated", contract)

        registry = json.loads((ROOT / "registries/opt_b/c2/vnext/C2_LEVEL_FOUNDATION_REGISTRY_v0_1.jsonc").read_text(encoding="utf-8"))
        self.assertEqual(5, len(registry["families"]))
        self.assertTrue(all(policy["active"] is False and policy["canonical"] is False for policy in registry["pivot_policies"]))
        self.assertEqual("REGISTERED_AS_OPTION_INACTIVE", next(item for item in registry["origins"] if item["origin"] == "EXOGENOUS_CONVENTION")["status"])
        self.assertEqual("NONE", registry["authority"]["active_selector"])

        schema = json.loads((ROOT / "schemas/opt_b/c2/vnext/C2_LEVEL_SCHEMA_BUNDLE_vNext_r1.json").read_text(encoding="utf-8"))
        self.assertEqual(9, len(schema["schemas"]))
        self.assertIn("winning_level", schema["prohibited_fields"])
        self.assertFalse(schema["schemas"]["c2_level_selector_result_vnext_r1"]["additionalProperties"])

        fixture = json.loads((ROOT / "fixtures/opt_b/c2/vnext/level_foundation_cases_v0_1.json").read_text(encoding="utf-8"))
        required = {"PLATEAU_HIGH", "CENSORED_RIGHT_CONFIRMATION", "GAP_IN_CONFIRMATION_WINDOW", "TRAILING_RANGE_SNAPSHOT_REFRESH", "RELATION_CROSSING_NO_MUTATION", "PIVOT_OF_PIVOTS_S1", "SELECTOR_TIE", "PARENT_LEVEL_LINK", "LEGACY_CROSSWALK_UNMATCHED"}
        self.assertTrue(required.issubset({item["case_id"] for item in fixture["cases"]}))
        self.assertFalse(fixture["market_data"])

        active = (ROOT / "registries/opt_b/c2/C2_ACTIVE_SELECTORS.yaml").read_text(encoding="utf-8")
        self.assertIn("SELECTOR.OPT-B.C2.GBPUSD.v2", active)
        self.assertIn("LOCKED_UNCONSUMED", active)


if __name__ == "__main__":
    unittest.main()
