from __future__ import annotations

import json
import unittest
from pathlib import Path

from ovc.development.skills.orch345 import build_packet_descriptor
from ovc.development.skills.orch345_active import (
    DEFAULT_MAX_PARALLEL_BUILDS,
    DEFAULT_MAX_REQUEUE_ATTEMPTS,
    DEFAULT_MAX_TRAIN_PACKETS,
    build_authorized_packet_train,
    build_authorized_portfolio_schedule,
    build_authorized_requeue_reconciliation,
)


ROOT = Path(__file__).resolve().parents[2]
CAPACITY = ROOT / "registries/development/skills/orch345_operational_capacity_v0_2.json"


def active_authority() -> dict:
    return {"status": "ACTIVE_AUTHORIZED", "record_present_on_main": True}


class DSAIThroughputExpansionTests(unittest.TestCase):
    def test_capacity_profile_preserves_governance_boundaries(self) -> None:
        profile = json.loads(CAPACITY.read_text(encoding="utf-8"))
        self.assertTrue(profile["effective"])
        self.assertEqual(profile["authority_delta"], "NONE")
        self.assertEqual(profile["packet_class_allowlist"], ["LOW_RISK_IMPLEMENTATION"])
        self.assertEqual(profile["capacity"]["max_parallel_builds"], 4)
        self.assertEqual(profile["capacity"]["max_train_packets"], 8)
        self.assertEqual(profile["capacity"]["max_auto_requeue_attempts"], 2)
        self.assertFalse(profile["integration_policy"]["parallel_merge"])
        self.assertTrue(profile["integration_policy"]["serialized_final_integration_window"])
        self.assertFalse(profile["integration_policy"]["force_push"])
        self.assertFalse(profile["auto_requeue"]["history_rewrite"])
        self.assertEqual(profile["operator_required_gate_behavior"], "STOP")
        self.assertEqual(profile["non_none_authority_delta_behavior"], "STOP")
        self.assertEqual(profile["validation"], "DENIED")
        self.assertEqual(profile["reserved_scientific_execution_authority"], "NONE")

    def test_active_defaults_match_bounded_capacity_profile(self) -> None:
        self.assertEqual(DEFAULT_MAX_PARALLEL_BUILDS, 4)
        self.assertEqual(DEFAULT_MAX_TRAIN_PACKETS, 8)
        self.assertEqual(DEFAULT_MAX_REQUEUE_ATTEMPTS, 2)

    def test_orch3_default_train_depth_is_eight_and_cap_fails_closed(self) -> None:
        packets = []
        for index in range(1, 11):
            packet_id = f"P{index}"
            prerequisites = () if index == 1 else (f"P{index - 1}",)
            packets.append(build_packet_descriptor(programme_id="PROGRAMME-A", packet_id=packet_id, prerequisites=prerequisites, write_paths=(f"src/a/{index}.py",), semantic_owners=(f"owner-{index}",)))
        result = build_authorized_packet_train(authority_resolution=active_authority(), programme_id="PROGRAMME-A", packets=packets)
        self.assertEqual(result["selected_packet_ids"], [f"P{i}" for i in range(1, 9)])
        self.assertEqual(result["max_train_packets"], 8)
        self.assertFalse(result["parallel_merge"])
        with self.assertRaises(PermissionError):
            build_authorized_packet_train(authority_resolution=active_authority(), programme_id="PROGRAMME-A", packets=packets, max_packets=9)

    def test_orch5_default_fills_four_disjoint_parallel_build_slots(self) -> None:
        packets = [build_packet_descriptor(programme_id=f"PROGRAMME-{index}", packet_id=f"Q{index}", write_paths=(f"src/q{index}/",), semantic_owners=(f"owner-q{index}",), priority=index) for index in range(1, 7)]
        result = build_authorized_portfolio_schedule(authority_resolution=active_authority(), packets=packets)
        self.assertEqual(result["selected_packet_ids"], ["Q1", "Q2", "Q3", "Q4"])
        self.assertEqual(result["max_parallel_builds"], 4)
        self.assertEqual(len(result["waiting"]), 2)
        self.assertFalse(result["parallel_merge"])
        with self.assertRaises(PermissionError):
            build_authorized_portfolio_schedule(authority_resolution=active_authority(), packets=packets, max_parallel=5)

    def test_main_movement_recomposes_same_pip_and_never_creates_replacement_pr(self) -> None:
        packet = build_packet_descriptor(programme_id="PROGRAMME-A", packet_id="R1", write_paths=("src/r1/",), semantic_owners=("owner-r1",))
        allowed = build_authorized_requeue_reconciliation(
            authority_resolution=active_authority(),
            packet=packet,
            failure_reason="PREDECESSOR_MOVED",
            attempt=7,
            previous_base="a" * 40,
            current_main="b" * 40,
        )
        self.assertEqual(allowed["action"], "RECOMPOSE_SAME_PIP_CURRENT_FRONTIER")
        self.assertTrue(allowed["same_pr_required"])
        self.assertTrue(allowed["same_source_head_required"])
        self.assertTrue(allowed["same_pip_required"])
        self.assertTrue(allowed["a0_reuse_required"])
        self.assertTrue(allowed["a1_recomposition_required"])
        self.assertTrue(allowed["a2_prospective_assurance_required"])
        self.assertFalse(allowed["fresh_branch_required"])
        self.assertFalse(allowed["fresh_exact_head_assurance_required"])
        self.assertEqual(allowed["blockers"], [])
        self.assertFalse(allowed["force_push"])
        self.assertFalse(allowed["history_rewrite"])

        drift = build_authorized_requeue_reconciliation(
            authority_resolution=active_authority(),
            packet=packet,
            failure_reason="PREDECESSOR_MOVED",
            attempt=1,
            previous_base="a" * 40,
            current_main="b" * 40,
            semantic_owner_changed=True,
        )
        self.assertEqual(drift["action"], "STOP_SERIAL_REQUIRED")
        self.assertIn("SEMANTIC_OWNER_DRIFT", drift["blockers"])

    def test_recomposition_never_crosses_operator_or_authority_boundaries(self) -> None:
        operator_packet = build_packet_descriptor(programme_id="PROGRAMME-A", packet_id="R2", write_paths=("src/r2/",), semantic_owners=("owner-r2",), gate_class="OPERATOR_REQUIRED")
        result = build_authorized_requeue_reconciliation(
            authority_resolution=active_authority(),
            packet=operator_packet,
            failure_reason="PREDECESSOR_MOVED",
            attempt=1,
            previous_base="a" * 40,
            current_main="b" * 40,
        )
        self.assertEqual(result["action"], "STOP_SERIAL_REQUIRED")
        self.assertIn("OPERATOR_GATE_BOUNDARY", result["blockers"])


if __name__ == "__main__":
    unittest.main()
