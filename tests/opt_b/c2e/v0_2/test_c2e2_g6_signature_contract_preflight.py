from __future__ import annotations

import unittest

from ovc.opt_b.c2_vnext.formula_profiles import evaluate_location_profile
from ovc.opt_b.c2_vnext.parent_context import resolve_parent_context
from ovc.opt_b.c2e_v2.empirical_boundary_rules import evaluate_boundary_predicates


C1_RELEASE = "RPS.C1SET.GBPUSD.PD-JUNE-FM.20260530_20260703.v1"
CALENDAR = "OVC.CALENDAR.GBPUSD.NY_1700.v1"
PARENT_LATTICE = "LATTICE.2H.UTC_0000.v1"


def _local(observation_id: str, first_valid_time: str) -> dict:
    return {
        "observation_id": observation_id,
        "first_valid_time": first_valid_time,
        "instrument_id": "GBPUSD",
        "side": "BID",
        "release_id": C1_RELEASE,
        "calendar_id": CALENDAR,
        "parent_lattice_id": PARENT_LATTICE,
        "parent_scope_id": "GBPUSD.BID.2H",
    }


def _parent_slot() -> dict:
    return {
        "observation_id": "PARENT.STABLE.22_00",
        "interval_start": "2026-05-31T22:00:00Z",
        "interval_end": "2026-06-01T00:00:00Z",
        "first_valid_time": "2026-06-01T00:00:00Z",
        "instrument_id": "GBPUSD",
        "side": "BID",
        "release_id": C1_RELEASE,
        "calendar_id": CALENDAR,
        "parent_lattice_id": PARENT_LATTICE,
        "source_id": "C1.PARENT.STABLE",
        "status": "COMPLETE",
    }


def _stable_location(as_of_time: str) -> dict:
    relation_set = {
        "relation_set_id": "RELSET.STABLE.1",
        "complete_scoped_inventory": True,
        "selected_object_id": None,
        "fallback_object_id": None,
        "candidate_object_ids": ["LEVEL.STABLE.1"],
        "relation_ids": ["REL.STABLE.1"],
        "exclusions": [],
        "first_valid_time": "2026-06-01T00:15:00Z",
    }
    relation = {
        "relation_id": "REL.STABLE.1",
        "object_id": "LEVEL.STABLE.1",
        "object_kind": "LEVEL",
        "subject_probe_id": "PROBE.STABLE.1",
        "topology": "ABOVE",
        "signed_distance": "0.00100",
        "absolute_distance": "0.00100",
        "first_valid_time": "2026-06-01T00:15:00Z",
    }
    return evaluate_location_profile([relation_set], [relation], as_of_time=as_of_time)


def _boundary_frame(*, observation_id: str, first_valid_time: str, location_id: str,
                    context_bundle_id: str, fixed_parent_link_id: str) -> dict:
    return {
        "identity": {
            "instrument_id": "GBPUSD",
            "side": "BID",
            "scope_id": "LOCAL_15M",
            "scale_id": "15M",
            "clock_id": "UTC_15M",
            "observation_id": observation_id,
        },
        "chronology": {
            "continuity_segment_id": "SEG.STABLE",
            "first_valid_time": first_valid_time,
            "evaluation_cutoff": first_valid_time,
        },
        "structural": {
            "location_record_ids": [location_id],
            "motion_record_ids": [],
            "organisation_record_ids": [],
            "interaction_record_ids": [],
            "level_record_ids": [],
            "container_record_ids": [],
            "relation_set_id": None,
            "transition_record_ids": [],
            "run_record_ids": [],
        },
        "context": {
            "context_resolution_bundle_id": context_bundle_id,
            "fixed_parent_links": [fixed_parent_link_id],
            "structural_object_links": [],
            "parent_axis_links": [],
        },
        "evidence": {
            "dependency_results": [],
            "availability_status": "AVAILABLE",
            "technical_status": "COMPUTABLE",
            "authority_state": "UNAUTHORIZED_ACTIVE_C2E",
            "reason_codes": [],
        },
        "lineage": {
            "parent_record_ids": [],
            "artifact_hashes": {"probe": "stable-facts"},
            "source_build_commit": "signature-preflight",
        },
    }


class C2E2G6SignatureContractPreflightTests(unittest.TestCase):
    def test_formula_output_identity_changes_when_only_as_of_time_changes(self) -> None:
        first = _stable_location("2026-06-01T00:15:00Z")
        second = _stable_location("2026-06-01T00:30:00Z")
        self.assertEqual(first["facts"], second["facts"])
        self.assertNotEqual(first["profile_output_id"], second["profile_output_id"])
        self.assertTrue(first["profile_output_id"].startswith("C2.FORMULA.OUTPUT."))
        self.assertTrue(second["profile_output_id"].startswith("C2.FORMULA.OUTPUT."))
        self.assertEqual(first["as_of_time"], "2026-06-01T00:15:00Z")
        self.assertEqual(second["as_of_time"], "2026-06-01T00:30:00Z")
        self.assertFalse(first["active"])
        self.assertFalse(second["active"])
        self.assertFalse(first["canonical"])
        self.assertFalse(second["canonical"])

    def test_parent_context_record_identity_changes_with_same_selected_parent(self) -> None:
        first = resolve_parent_context(
            local_observation=_local("LOCAL.001", "2026-06-01T00:15:00Z"),
            parent_slots=[_parent_slot()],
            parent_objects=[],
        )
        second = resolve_parent_context(
            local_observation=_local("LOCAL.002", "2026-06-01T00:30:00Z"),
            parent_slots=[_parent_slot()],
            parent_objects=[],
        )
        first_link = first["fixed_parent_observation_link"]
        second_link = second["fixed_parent_observation_link"]
        self.assertEqual(first_link["selected_id"], second_link["selected_id"])
        self.assertNotEqual(first_link["link_id"], second_link["link_id"])
        self.assertNotEqual(first["bundle_id"], second["bundle_id"])
        self.assertEqual(first_link["link_id"], "C2.PARENT.LINK.a04fa41a118cfea63430b31e")
        self.assertEqual(second_link["link_id"], "C2.PARENT.LINK.3a58c48f4eadcf192b7a7ebb")

    def test_current_boundary_signatures_false_positive_on_stable_facts_and_parent(self) -> None:
        loc1 = _stable_location("2026-06-01T00:15:00Z")
        loc2 = _stable_location("2026-06-01T00:30:00Z")
        ctx1 = resolve_parent_context(
            local_observation=_local("LOCAL.001", "2026-06-01T00:15:00Z"),
            parent_slots=[_parent_slot()],
            parent_objects=[],
        )
        ctx2 = resolve_parent_context(
            local_observation=_local("LOCAL.002", "2026-06-01T00:30:00Z"),
            parent_slots=[_parent_slot()],
            parent_objects=[],
        )
        previous = _boundary_frame(
            observation_id="LOCAL.001",
            first_valid_time="2026-06-01T00:15:00Z",
            location_id=loc1["profile_output_id"],
            context_bundle_id=ctx1["bundle_id"],
            fixed_parent_link_id=ctx1["fixed_parent_observation_link"]["link_id"],
        )
        current = _boundary_frame(
            observation_id="LOCAL.002",
            first_valid_time="2026-06-01T00:30:00Z",
            location_id=loc2["profile_output_id"],
            context_bundle_id=ctx2["bundle_id"],
            fixed_parent_link_id=ctx2["fixed_parent_observation_link"]["link_id"],
        )
        result = evaluate_boundary_predicates(current, previous)
        self.assertEqual(
            result["matched_rules"],
            [
                "C2E.RULE.JUNE.BASELINE.RE_PARENT.v1",
                "C2E.RULE.JUNE.BASELINE.PHASE_MUTATION.v1",
                "C2E.RULE.JUNE.BASELINE.CONTINUATION.v1",
            ],
        )
        self.assertTrue(result["matched"]["C2E.RULE.JUNE.BASELINE.RE_PARENT.v1"])
        self.assertTrue(result["matched"]["C2E.RULE.JUNE.BASELINE.PHASE_MUTATION.v1"])
        self.assertFalse(result["segment_changed"])


if __name__ == "__main__":
    unittest.main()
