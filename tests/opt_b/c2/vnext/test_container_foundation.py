from __future__ import annotations

import copy
import hashlib
import json
import unittest
from pathlib import Path

from ovc.opt_b.c2_vnext.containers import (
    ContainerContractError,
    PairingPolicy,
    assert_relation_cannot_mutate_container,
    build_container_graph,
    build_context_link,
    build_legacy_container_crosswalk,
    build_swing_envelope,
    build_trailing_range_container,
    classify_geometry,
    evaluate_boundary_pair,
    evaluate_role_projection,
    make_lifecycle_event,
    project_lifecycle,
    shadow_pairing_policies,
)

ROOT = Path(__file__).resolve().parents[4]


def level(
    *,
    level_id: str,
    level_type: str,
    value: float,
    first_valid_time: str = "2026-01-05T02:00:00Z",
    side: str = "BID",
    clock_id: str = "LATTICE.15M.UTC_0000.v1",
    release_id: str = "OPT-A.SYNTHETIC.v1",
    structural_depth: str = "NA",
    family: str | None = None,
    horizon_id: str | None = "HORIZON.TEST.4",
    source_ids: list[str] | None = None,
) -> dict:
    if family is None:
        family = "WINDOW_BOUNDARY" if level_type.startswith("TRAILING") else "CONFIRMED_PIVOT"
    body = {
        "schema": "c2_reference_level/vnext-r1",
        "level_id": level_id,
        "family": family,
        "level_type": level_type,
        "value": value,
        "first_valid_time": first_valid_time,
        "anchor_time": first_valid_time,
        "instrument": "GBPUSD",
        "side": side,
        "clock_id": clock_id,
        "structural_depth": structural_depth,
        "origin": "SYNTHETIC_TEST",
        "source_ids": source_ids or ["OBS.1", "OBS.2", "OBS.3", "OBS.4"],
        "source_release_id": release_id,
        "lineage_id": f"LINEAGE.{level_id}",
        "parent_level_ids": [],
        "immutable": True,
        "maturity": "SHADOW_EXPERIMENT",
        "authority": {"active_selector": "NONE", "parameter_activation": "NONE", "release": "NONE"},
        "horizon_id": horizon_id,
        "snapshot_version": f"SNAPSHOT.{level_id}",
    }
    body["content_sha256"] = hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()
    return body


def trailing_levels(*, low: float = 1.0, high: float = 2.0, first_valid_time: str = "2026-01-05T02:00:00Z") -> list[dict]:
    source_ids = ["OBS.1", "OBS.2", "OBS.3", "OBS.4"]
    return [
        level(level_id=f"LEVEL.LOW.{first_valid_time}", level_type="TRAILING_RANGE_LOW", value=low, first_valid_time=first_valid_time, source_ids=source_ids),
        level(level_id=f"LEVEL.HIGH.{first_valid_time}", level_type="TRAILING_RANGE_HIGH", value=high, first_valid_time=first_valid_time, source_ids=source_ids),
    ]


def swing_pair(*, low: float = 1.0, high: float = 2.0, first_valid_time: str = "2026-01-05T02:00:00Z", depth: str = "S0") -> tuple[dict, dict]:
    return (
        level(level_id=f"SWING.LOW.{depth}.{first_valid_time}", level_type="CONFIRMED_SWING_LOW", value=low, first_valid_time=first_valid_time, structural_depth=depth, horizon_id=None),
        level(level_id=f"SWING.HIGH.{depth}.{first_valid_time}", level_type="CONFIRMED_SWING_HIGH", value=high, first_valid_time=first_valid_time, structural_depth=depth, horizon_id=None),
    )


class ContainerFoundationTests(unittest.TestCase):
    def test_trailing_range_requires_exact_two_compatible_boundaries(self) -> None:
        lower, upper = trailing_levels()
        container = build_trailing_range_container([lower, upper])
        self.assertEqual("TRAILING_RANGE_SNAPSHOT", container["family"])
        self.assertEqual("MEASUREMENT", container["kind"])
        self.assertEqual(1.0, container["lower_value"])
        self.assertEqual(2.0, container["upper_value"])
        self.assertEqual(1.0, container["width"])
        self.assertEqual(1.5, container["centre"])
        self.assertFalse(container["centre_is_boundary"])
        self.assertTrue(container["immutable"])
        self.assertEqual("NONE", container["authority"]["active_selector"])

        partial = evaluate_boundary_pair(lower, None, family="TRAILING_RANGE_SNAPSHOT", kind="MEASUREMENT", pairing_policy_id="PAIRING.TEST")
        self.assertEqual("PARTIAL_ONE_BOUNDARY", partial["status"])
        with self.assertRaisesRegex(ContainerContractError, "TRAILING_RANGE_PAIRING"):
            build_trailing_range_container([lower])

    def test_incompatible_and_zero_width_pairs_are_explicit_and_non_constructive(self) -> None:
        lower, upper = trailing_levels(low=1.0, high=1.0)
        zero = evaluate_boundary_pair(lower, upper, family="TRAILING_RANGE_SNAPSHOT", kind="MEASUREMENT", pairing_policy_id="PAIRING.TEST")
        self.assertEqual("REJECTED_ZERO_WIDTH", zero["status"])
        self.assertFalse(zero["compatible"])

        lower, upper = trailing_levels()
        upper["side"] = "ASK"
        incompatible = evaluate_boundary_pair(lower, upper, family="TRAILING_RANGE_SNAPSHOT", kind="MEASUREMENT", pairing_policy_id="PAIRING.TEST")
        self.assertEqual("REJECTED_INCOMPATIBLE", incompatible["status"])
        self.assertIn("MISMATCH:side", incompatible["reason_codes"])

    def test_swing_envelope_requires_explicit_pairing_policy_and_opposite_types(self) -> None:
        lower, upper = swing_pair()
        policy = shadow_pairing_policies()[0]
        pairing, container = build_swing_envelope(lower, upper, policy=policy)
        self.assertEqual("COMPLETE_COMPATIBLE", pairing["status"])
        self.assertIsNotNone(container)
        assert container is not None
        self.assertEqual("SWING_ENVELOPE", container["family"])
        self.assertEqual("STRUCTURAL", container["kind"])
        self.assertEqual(policy.policy_id, container["pairing_policy_id"])
        self.assertEqual("S0", container["structural_depth"])

        wrong_lower = copy.deepcopy(lower)
        wrong_lower["level_type"] = "CONFIRMED_SWING_HIGH"
        with self.assertRaisesRegex(ContainerContractError, "SWING_LOWER_TYPE"):
            build_swing_envelope(wrong_lower, upper, policy=policy)

    def test_depths_coexist_and_are_not_automatically_equivalent(self) -> None:
        s0_lower, s0_upper = swing_pair(depth="S0")
        s1_lower, s1_upper = swing_pair(depth="S1", first_valid_time="2026-01-05T03:00:00Z")
        _, s0 = build_swing_envelope(s0_lower, s0_upper, policy=shadow_pairing_policies()[0])
        depth_policy = shadow_pairing_policies()[2]
        _, s1 = build_swing_envelope(s1_lower, s1_upper, policy=depth_policy)
        assert s0 is not None and s1 is not None
        self.assertNotEqual(s0["container_id"], s1["container_id"])
        self.assertEqual("S0", s0["structural_depth"])
        self.assertEqual("S1", s1["structural_depth"])

    def test_container_graph_preserves_nesting_overlap_disjoint_and_equal_bounds(self) -> None:
        outer = build_trailing_range_container(trailing_levels(low=0.0, high=10.0, first_valid_time="2026-01-05T01:00:00Z"))
        inner = build_trailing_range_container(trailing_levels(low=2.0, high=4.0, first_valid_time="2026-01-05T02:00:00Z"))
        overlap = build_trailing_range_container(trailing_levels(low=3.0, high=12.0, first_valid_time="2026-01-05T03:00:00Z"))
        disjoint = build_trailing_range_container(trailing_levels(low=20.0, high=25.0, first_valid_time="2026-01-05T04:00:00Z"))
        equal = copy.deepcopy(inner)
        equal["container_id"] = "CONTAINER.EQUAL.DISTINCT"
        self.assertEqual("CONTAINS", classify_geometry(outer, inner))
        self.assertEqual("WITHIN", classify_geometry(inner, outer))
        self.assertEqual("OVERLAPS", classify_geometry(outer, overlap))
        self.assertEqual("DISJOINT", classify_geometry(outer, disjoint))
        self.assertEqual("EQUAL_BOUNDS", classify_geometry(inner, equal))
        graph = build_container_graph([outer, inner, overlap, disjoint, equal])
        self.assertTrue(graph["complete_inventory"])
        self.assertFalse(graph["width_derived_tree"])
        self.assertTrue(graph["partial_overlap_preserved"])
        self.assertIn("OVERLAPS", {edge["relation"] for edge in graph["edges"]})

    def test_lifecycle_is_append_only_consumer_specific_and_crossing_does_not_mutate(self) -> None:
        old = build_trailing_range_container(trailing_levels(low=1.0, high=2.0, first_valid_time="2026-01-05T01:00:00Z"))
        new = build_trailing_range_container(trailing_levels(low=1.1, high=2.1, first_valid_time="2026-01-05T02:00:00Z"))
        before = copy.deepcopy(old)
        events = [
            make_lifecycle_event(old, event_type="STALE_FOR_CONSUMER", event_time="2026-01-05T02:15:00Z", reason="AGE_POLICY", consumer_id="CONSUMER.A"),
            make_lifecycle_event(old, event_type="SUPERSEDED", event_time="2026-01-05T02:30:00Z", reason="NEW_SNAPSHOT", superseding_container_id=new["container_id"]),
        ]
        for_a = project_lifecycle([old, new], events, as_of_time="2026-01-05T03:00:00Z", consumer_id="CONSUMER.A")
        for_b = project_lifecycle([old, new], events, as_of_time="2026-01-05T03:00:00Z", consumer_id="CONSUMER.B")
        old_a = next(item for item in for_a if item["container_id"] == old["container_id"])
        old_b = next(item for item in for_b if item["container_id"] == old["container_id"])
        self.assertTrue(old_a["stale_for_consumer"])
        self.assertFalse(old_b["stale_for_consumer"])
        self.assertEqual("SUPERSEDED", old_a["state"])
        self.assertEqual(before, old)
        assert_relation_cannot_mutate_container(old, copy.deepcopy(old))
        changed = copy.deepcopy(old)
        changed["upper_value"] = 3.0
        with self.assertRaisesRegex(ContainerContractError, "RELATION_MUTATED_CONTAINER_DEFINITION"):
            assert_relation_cannot_mutate_container(old, changed)

    def test_role_projection_exposes_candidates_exclusions_ties_and_no_fallback(self) -> None:
        measurement = build_trailing_range_container(trailing_levels(first_valid_time="2026-01-05T01:00:00Z"))
        lower, upper = swing_pair(first_valid_time="2026-01-05T02:00:00Z")
        _, structural = build_swing_envelope(lower, upper, policy=shadow_pairing_policies()[0])
        assert structural is not None
        result = evaluate_role_projection([measurement, structural], projection_id="PROJECTION.C2.CONTAINER.LATEST_FIRST_VALID.r1", role="LOCAL_MEASUREMENT", as_of_time="2026-01-05T03:00:00Z", scope_kind="LOCAL")
        self.assertEqual(measurement["container_id"], result["selected_container_id"])
        self.assertEqual(2, len(result["candidate_ids"]))
        self.assertEqual([{"container_id": structural["container_id"], "reason": "KIND_NOT_ALLOWED_FOR_ROLE"}], result["exclusions"])
        self.assertIsNone(result["fallback_container_id"])
        self.assertFalse(result["active"])

        tied = copy.deepcopy(measurement)
        tied["container_id"] = "CONTAINER.TIED.DISTINCT"
        tie = evaluate_role_projection([measurement, tied], projection_id="PROJECTION.C2.CONTAINER.LATEST_FIRST_VALID.r1", role="LOCAL_MEASUREMENT", as_of_time="2026-01-05T03:00:00Z", scope_kind="LOCAL")
        self.assertEqual("TIED_CANDIDATES", tie["reason"])
        self.assertIsNone(tie["selected_container_id"])
        self.assertEqual(2, len(tie["tie_ids"]))

    def test_parent_measurement_and_structural_links_are_separate_and_non_recreating(self) -> None:
        measurement = build_trailing_range_container(trailing_levels(first_valid_time="2026-01-05T01:00:00Z"))
        lower, upper = swing_pair(first_valid_time="2026-01-05T01:30:00Z")
        _, structural = build_swing_envelope(lower, upper, policy=shadow_pairing_policies()[0])
        assert structural is not None
        m_link = build_context_link(measurement, local_scope_id="LOCAL.15M", role="PARENT_MEASUREMENT", as_of_time="2026-01-05T02:00:00Z")
        s_link = build_context_link(structural, local_scope_id="LOCAL.15M", role="PARENT_STRUCTURAL", as_of_time="2026-01-05T02:00:00Z")
        self.assertNotEqual(m_link["context_link_id"], s_link["context_link_id"])
        self.assertFalse(m_link["local_container_recreated"])
        self.assertTrue(s_link["parent_authority_preserved"])
        with self.assertRaisesRegex(ContainerContractError, "PARENT_CONTAINER_NOT_FIRST_VALID"):
            build_context_link(measurement, local_scope_id="LOCAL.EARLY", role="PARENT_MEASUREMENT", as_of_time="2026-01-05T00:30:00Z")

    def test_legacy_crosswalk_preserves_history_and_parent_requires_link(self) -> None:
        container = build_trailing_range_container(trailing_levels())
        legacy = [
            {"legacy_container_id": "LEGACY.1", "legacy_type": "LOCAL_RANGE", "side": "BID", "lower_value": 1.0, "upper_value": 2.0},
            {"legacy_container_id": "LEGACY.2", "legacy_type": "PARENT_RANGE", "side": "BID", "lower_value": 1.0, "upper_value": 2.0},
            {"legacy_container_id": "LEGACY.3", "legacy_type": "SWING_ENVELOPE", "side": "BID", "lower_value": 5.0, "upper_value": 6.0},
        ]
        before = copy.deepcopy(legacy)
        records = build_legacy_container_crosswalk(legacy, [container])
        self.assertEqual(before, legacy)
        by_id = {item["legacy_container_id"]: item for item in records}
        self.assertEqual("MATCHED_UNIQUE", by_id["LEGACY.1"]["match_status"])
        self.assertEqual("LINK_ONLY_REQUIRED", by_id["LEGACY.2"]["match_status"])
        self.assertEqual("UNMATCHED", by_id["LEGACY.3"]["match_status"])
        self.assertTrue(all(item["legacy_mutated"] is False for item in records))

    def test_pairing_policy_cannot_be_active_or_canonical(self) -> None:
        with self.assertRaisesRegex(ContainerContractError, "PAIRING_POLICY_ACTIVATION_DENIED"):
            PairingPolicy("PAIRING.BAD.ACTIVE", "BAD", active=True)
        with self.assertRaisesRegex(ContainerContractError, "CANONICAL_PAIRING_POLICY_DENIED"):
            PairingPolicy("PAIRING.BAD.CANONICAL", "BAD", canonical=True)

    def test_repository_contract_registry_schema_fixture_and_active_boundary(self) -> None:
        contract = (ROOT / "contracts/opt_b/c2/C2_CONTAINER_CONTRACT_vNext.md").read_text(encoding="utf-8")
        for item in [f"P4-D{number}" for number in range(1, 19)] + [f"P4-Q{number}" for number in range(1, 7)]:
            self.assertIn(item, contract)
        self.assertIn("no implicit pairing exists", contract)

        registry = json.loads((ROOT / "registries/opt_b/c2/vnext/C2_CONTAINER_FOUNDATION_REGISTRY_v0_1.jsonc").read_text(encoding="utf-8"))
        self.assertEqual(2, len(registry["families"]))
        self.assertEqual(3, len(registry["pairing_policies"]))
        self.assertTrue(all(not item["active"] and not item["canonical"] for item in registry["pairing_policies"]))
        self.assertEqual(4, len(registry["roles"]))
        self.assertEqual("NONE", registry["authority"]["active_projection"])

        schema = json.loads((ROOT / "schemas/opt_b/c2/vnext/C2_CONTAINER_SCHEMA_BUNDLE_vNext_r1.json").read_text(encoding="utf-8"))
        self.assertEqual(7, len(schema["schemas"]))
        self.assertIn("widest_container", schema["prohibited_fields"])
        self.assertTrue(all(value["additionalProperties"] is False for value in schema["schemas"].values()))

        fixture = json.loads((ROOT / "fixtures/opt_b/c2/vnext/container_foundation_cases_v0_1.json").read_text(encoding="utf-8"))
        required = {"ONE_BOUNDARY_ONLY", "ZERO_WIDTH", "SWING_ENVELOPE_EXPLICIT_PAIRING", "GRAPH_PARTIAL_OVERLAP", "ROLE_PROJECTION_TIE", "PARENT_LINK_NO_RECREATE", "LEGACY_PARENT_RANGE_LINK_ONLY"}
        self.assertTrue(required.issubset({item["case_id"] for item in fixture["cases"]}))
        self.assertFalse(fixture["market_data"])

        active = (ROOT / "registries/opt_b/c2/C2_ACTIVE_SELECTORS.yaml").read_text(encoding="utf-8")
        self.assertIn("SELECTOR.OPT-B.C2.GBPUSD.v2", active)
        self.assertIn("LOCKED_UNCONSUMED", active)


if __name__ == "__main__":
    unittest.main()
