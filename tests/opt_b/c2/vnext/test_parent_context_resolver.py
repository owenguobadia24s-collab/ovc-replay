from __future__ import annotations

import unittest

from ovc.opt_b.c2_vnext.parent_context import (
    AUTHORITY,
    ParentContextError,
    expected_parent_slot,
    resolve_parent_context,
)


def local(time: str = "2026-06-22T10:15:00Z") -> dict:
    return {
        "observation_id": "LOCAL.15M.001",
        "first_valid_time": time,
        "instrument_id": "GBPUSD",
        "side": "BID",
        "release_id": "R.TEST.v1",
        "calendar_id": "FX.UTC.v1",
        "parent_lattice_id": "2H_A_L.UTC_0000.v1",
        "parent_scope_id": "GBPUSD.BID.2H",
    }


def slot(
    observation_id: str = "PARENT.2H.08_10",
    *,
    start: str = "2026-06-22T08:00:00Z",
    end: str = "2026-06-22T10:00:00Z",
    first_valid: str = "2026-06-22T10:00:00Z",
    status: str = "COMPLETE",
) -> dict:
    return {
        "observation_id": observation_id,
        "interval_start": start,
        "interval_end": end,
        "first_valid_time": first_valid,
        "instrument_id": "GBPUSD",
        "side": "BID",
        "release_id": "R.TEST.v1",
        "calendar_id": "FX.UTC.v1",
        "parent_lattice_id": "2H_A_L.UTC_0000.v1",
        "source_id": f"SOURCE.{observation_id}",
        "status": status,
    }


def parent_object(
    object_id: str,
    role: str,
    *,
    depth: int | None = None,
    parent_observation_id: str = "PARENT.2H.08_10",
) -> dict:
    value = {
        "object_id": object_id,
        "role": role,
        "parent_observation_id": parent_observation_id,
        "definition_hash": f"sha256:{object_id.lower()}",
        "first_valid_time": "2026-06-22T10:00:00Z",
        "instrument_id": "GBPUSD",
        "side": "BID",
        "release_id": "R.TEST.v1",
        "calendar_id": "FX.UTC.v1",
        "parent_lattice_id": "2H_A_L.UTC_0000.v1",
        "status": "VALID",
    }
    if depth is not None:
        value["depth"] = depth
    return value


class ParentContextResolverTests(unittest.TestCase):
    def test_expected_slot_is_latest_completed_utc_two_hour_interval(self) -> None:
        self.assertEqual(
            ("2026-06-22T08:00:00Z", "2026-06-22T10:00:00Z"),
            expected_parent_slot("2026-06-22T10:15:00Z"),
        )
        self.assertEqual(
            ("2026-06-21T22:00:00Z", "2026-06-22T00:00:00Z"),
            expected_parent_slot("2026-06-22T00:30:00Z"),
        )
        self.assertEqual(
            ("2026-06-22T08:00:00Z", "2026-06-22T10:00:00Z"),
            expected_parent_slot("2026-06-22T10:00:00Z"),
        )

    def test_exact_expected_parent_and_separate_objects_link(self) -> None:
        objects = [
            parent_object("OBJ.MEASURE.1", "PARENT_MEASUREMENT"),
            parent_object("OBJ.STRUCT.S0", "PARENT_STRUCTURAL", depth=0),
            parent_object("OBJ.AXIS.1", "PARENT_AXIS_CONTEXT"),
        ]
        result = resolve_parent_context(
            local_observation=local(),
            parent_slots=[slot()],
            parent_objects=objects,
            structural_depths=[0, 1],
            higher_order_local_objects=[{
                "object_id": "LOCAL.S1.1",
                "local_clock": "15M",
                "depth": 1,
                "local_observation_id": "LOCAL.15M.001",
            }],
            eligible_local_observation_count=41,
            registered_closure_count=2,
        )
        self.assertEqual("PARENT.2H.08_10", result["fixed_parent_observation_link"]["selected_id"])
        self.assertEqual("OBJ.MEASURE.1", result["parent_measurement_link"]["selected_id"])
        self.assertEqual("OBJ.AXIS.1", result["parent_axis_context_link"]["selected_id"])
        by_depth = {item["structural_depth"]: item for item in result["parent_structural_links_by_depth"]}
        self.assertEqual("OBJ.STRUCT.S0", by_depth[0]["selected_id"])
        self.assertIsNone(by_depth[1]["selected_id"])
        self.assertEqual("NO_ELIGIBLE_PARENT_OBJECT", by_depth[1]["selection_reason"])
        self.assertEqual(["LOCAL.S1.1"], result["higher_order_local_clock_projection"]["eligible_ids"])
        self.assertFalse(result["higher_order_local_clock_projection"]["links"][0]["parent_equivalence"])
        self.assertEqual(AUTHORITY, result["authority"])
        self.assertFalse(result["active"])
        self.assertFalse(result["canonical"])
        self.assertIsNone(result["global_degraded_state"])
        self.assertIsNone(result["universal_staleness_threshold"])
        self.assertIsNone(result["fallback_parent_id"])

    def test_missing_expected_slot_does_not_carry_older_parent_forward(self) -> None:
        older = slot(
            "PARENT.2H.06_08",
            start="2026-06-22T06:00:00Z",
            end="2026-06-22T08:00:00Z",
            first_valid="2026-06-22T08:00:00Z",
        )
        result = resolve_parent_context(
            local_observation=local(),
            parent_slots=[older],
            parent_objects=[parent_object("OBJ.MEASURE.OLD", "PARENT_MEASUREMENT", parent_observation_id="PARENT.2H.06_08")],
        )
        fixed = result["fixed_parent_observation_link"]
        self.assertIsNone(fixed["selected_id"])
        self.assertIsNone(fixed["fallback_id"])
        self.assertEqual("EXPECTED_PARENT_SLOT_MISSING", fixed["selection_reason"])
        self.assertEqual("NOT_COMPUTABLE", result["parent_measurement_link"]["computability"])
        self.assertEqual("DEPENDENCY_NOT_COMPUTABLE", result["parent_measurement_link"]["selection_reason"])

    def test_failed_expected_slot_clears_dependents(self) -> None:
        result = resolve_parent_context(
            local_observation=local(),
            parent_slots=[slot(status="GAPPED")],
            parent_objects=[parent_object("OBJ.MEASURE.1", "PARENT_MEASUREMENT")],
        )
        fixed = result["fixed_parent_observation_link"]
        self.assertIsNone(fixed["selected_id"])
        self.assertIn("EXPECTED_PARENT_SLOT_GAPPED", fixed["reason_codes"])
        self.assertIsNone(result["parent_measurement_link"]["selected_id"])

    def test_unresolved_multiple_objects_produce_null_not_hidden_selection(self) -> None:
        result = resolve_parent_context(
            local_observation=local(),
            parent_slots=[slot()],
            parent_objects=[
                parent_object("OBJ.STRUCT.A", "PARENT_STRUCTURAL", depth=0),
                parent_object("OBJ.STRUCT.B", "PARENT_STRUCTURAL", depth=0),
            ],
            structural_depths=[0],
        )
        link = result["parent_structural_links_by_depth"][0]
        self.assertIsNone(link["selected_id"])
        self.assertIsNone(link["fallback_id"])
        self.assertEqual("MULTIPLE_ELIGIBLE_NO_GOVERNED_SELECTION", link["selection_reason"])
        self.assertEqual([], link["eligible_ids"])
        self.assertEqual({"OBJ.STRUCT.A", "OBJ.STRUCT.B"}, set(link["candidate_ids"]))

    def test_identity_and_future_parent_fail_closed(self) -> None:
        wrong = slot(first_valid="2026-06-22T10:16:00Z")
        wrong["side"] = "ASK"
        result = resolve_parent_context(local_observation=local(), parent_slots=[wrong])
        reasons = set(result["fixed_parent_observation_link"]["reason_codes"])
        self.assertIn("SIDE_MISMATCH", reasons)
        self.assertIn("PARENT_NOT_FIRST_VALID", reasons)
        self.assertIsNone(result["fixed_parent_observation_link"]["selected_id"])

    def test_equal_parent_and_local_first_valid_time_is_allowed(self) -> None:
        result = resolve_parent_context(
            local_observation=local("2026-06-22T10:00:00Z"),
            parent_slots=[slot(first_valid="2026-06-22T10:00:00Z")],
        )
        self.assertEqual("PARENT.2H.08_10", result["fixed_parent_observation_link"]["selected_id"])
        self.assertEqual(0, result["fixed_parent_observation_link"]["age_evidence"]["parent_observation_age_seconds"])

    def test_episode_candidates_remain_separate_and_unavailable(self) -> None:
        result = resolve_parent_context(
            local_observation=local(),
            parent_slots=[slot()],
            episode_candidates=[{"episode_id": "EPISODE.CANDIDATE.1"}],
        )
        episode = result["higher_scale_episode_link"]
        self.assertEqual(["EPISODE.CANDIDATE.1"], episode["candidate_ids"])
        self.assertEqual([], episode["eligible_ids"])
        self.assertIsNone(episode["selected_id"])
        self.assertEqual("EPISODE_AUTHORITY_UNAVAILABLE", episode["selection_reason"])
        with self.assertRaisesRegex(ParentContextError, "EPISODE_AUTHORITY_NOT_AVAILABLE"):
            resolve_parent_context(local_observation=local(), parent_slots=[slot()], episode_authority=True)

    def test_refresh_is_context_lifecycle_not_market_transition(self) -> None:
        first = resolve_parent_context(local_observation=local(), parent_slots=[slot()])
        second = resolve_parent_context(
            local_observation=local(),
            parent_slots=[slot()],
            previous_bundle=first,
        )
        link = second["fixed_parent_observation_link"]
        self.assertEqual("UNCHANGED", link["refresh_status"])
        self.assertEqual(first["fixed_parent_observation_link"]["link_id"], link["previous_link_id"])
        self.assertNotIn("transition", link)

    def test_prohibited_authority_fields_are_rejected(self) -> None:
        contaminated = local()
        contaminated["probability"] = 0.8
        with self.assertRaisesRegex(ParentContextError, "PROHIBITED_FIELD"):
            resolve_parent_context(local_observation=contaminated, parent_slots=[slot()])


if __name__ == "__main__":
    unittest.main()
