from __future__ import annotations

import unittest

from ovc.development.skills.orch345 import build_packet_descriptor
from ovc.development.skills.orch345_active import (
    authorize_parallel_build_pair,
    build_authorized_packet_train,
    build_authorized_portfolio_schedule,
)
from ovc.development.skills.orch345_diagnostics import (
    DIAGNOSTIC_AUTHORITY_EFFECT,
    DIAGNOSTIC_RECEIPT_CLASS,
)


def active_authority() -> dict:
    return {
        "status": "ACTIVE_AUTHORIZED",
        "record_present_on_main": True,
    }


class ORCH345DiagnosticObservabilityTests(unittest.TestCase):
    def assert_diagnostic_only(self, result: dict, orchestrator: str) -> dict:
        self.assertEqual(result["authority_effect"], "BOUNDED_ORCH345_EXECUTION")
        receipt = result["diagnostic_receipt"]
        self.assertEqual(receipt["receipt_class"], DIAGNOSTIC_RECEIPT_CLASS)
        self.assertEqual(receipt["orchestrator"], orchestrator)
        self.assertEqual(receipt["authority_effect"], DIAGNOSTIC_AUTHORITY_EFFECT)
        self.assertTrue(receipt["observability_only"])
        self.assertTrue(receipt["temporary"])
        self.assertFalse(receipt["governance_expansion"])
        self.assertFalse(receipt["new_operator_gate"])
        self.assertEqual(receipt["merge_authority"], "NONE")
        self.assertFalse(receipt["parallel_merge"])
        self.assertEqual(receipt["source_execution_record_id"], result["record_id"])
        self.assertTrue(receipt["observed_at_utc"].endswith("Z"))
        return receipt

    def test_orch3_receipt_records_train_depth_without_changing_execution_authority(self) -> None:
        p1 = build_packet_descriptor(
            programme_id="P",
            packet_id="P-WP1",
            write_paths=("src/p/1.py",),
            semantic_owners=("p1",),
        )
        p2 = build_packet_descriptor(
            programme_id="P",
            packet_id="P-WP2",
            prerequisites=("P-WP1",),
            write_paths=("src/p/2.py",),
            semantic_owners=("p2",),
        )
        result = build_authorized_packet_train(
            authority_resolution=active_authority(),
            programme_id="P",
            packets=(p1, p2),
        )
        receipt = self.assert_diagnostic_only(result, "ORCH-3")
        self.assertEqual(receipt["decision"], "TRAIN_AUTHORIZED")
        self.assertEqual(receipt["candidate_packet_count"], 2)
        self.assertEqual(receipt["selected_packet_ids"], ["P-WP1", "P-WP2"])
        self.assertEqual(receipt["selected_train_depth"], 2)
        self.assertEqual(receipt["max_train_packets"], 8)

    def test_orch4_receipts_distinguish_parallel_allow_and_serial_fallback(self) -> None:
        left = build_packet_descriptor(
            programme_id="A",
            packet_id="A-WP1",
            write_paths=("src/a",),
            semantic_owners=("A",),
        )
        disjoint = build_packet_descriptor(
            programme_id="B",
            packet_id="B-WP1",
            write_paths=("src/b",),
            semantic_owners=("B",),
        )
        parallel = authorize_parallel_build_pair(
            authority_resolution=active_authority(),
            left=left,
            right=disjoint,
        )
        parallel_receipt = self.assert_diagnostic_only(parallel, "ORCH-4")
        self.assertEqual(parallel_receipt["decision"], "PARALLEL_ALLOW")
        self.assertEqual(parallel_receipt["reason_codes"], [])

        overlapping = build_packet_descriptor(
            programme_id="B",
            packet_id="B-WP2",
            write_paths=("src/a/file.py",),
            semantic_owners=("B2",),
        )
        serial = authorize_parallel_build_pair(
            authority_resolution=active_authority(),
            left=left,
            right=overlapping,
        )
        serial_receipt = self.assert_diagnostic_only(serial, "ORCH-4")
        self.assertEqual(serial_receipt["decision"], "SERIAL_FALLBACK")
        self.assertIn("WRITE_SET_OVERLAP", serial_receipt["reason_codes"])
        self.assertTrue(serial_receipt["overlaps"]["write_paths"])

    def test_orch5_receipt_records_slots_waits_and_explicit_dependency_wakeup(self) -> None:
        ready = build_packet_descriptor(
            programme_id="A",
            packet_id="A-WP1",
            write_paths=("src/a",),
            semantic_owners=("A",),
            priority=1,
        )
        cross_programme = build_packet_descriptor(
            programme_id="B",
            packet_id="B-WP1",
            cross_programme_dependencies=("A-DONE",),
            write_paths=("src/b",),
            semantic_owners=("B",),
            priority=2,
        )
        slot_wait = build_packet_descriptor(
            programme_id="C",
            packet_id="C-WP1",
            write_paths=("src/c",),
            semantic_owners=("C",),
            priority=3,
        )
        operator_wait = build_packet_descriptor(
            programme_id="D",
            packet_id="D-G1",
            gate_class="OPERATOR_REQUIRED",
            write_paths=("src/d",),
            semantic_owners=("D",),
            priority=4,
        )
        result = build_authorized_portfolio_schedule(
            authority_resolution=active_authority(),
            packets=(ready, cross_programme, slot_wait, operator_wait),
            completed_packet_ids=("A-DONE",),
            newly_completed_packet_ids=("A-DONE",),
            max_parallel=2,
        )
        receipt = self.assert_diagnostic_only(result, "ORCH-5")
        self.assertEqual(receipt["decision"], "PORTFOLIO_DISPATCH")
        self.assertEqual(receipt["occupied_slots"], 2)
        self.assertEqual(receipt["available_slots"], 0)
        self.assertTrue(receipt["capacity_saturated"])
        self.assertEqual(receipt["slot_limit_wait_count"], 1)
        self.assertEqual(receipt["operator_wait_count"], 1)
        self.assertEqual(receipt["dependency_wakeup_count"], 1)
        self.assertEqual(
            receipt["cross_programme_dependency_wakeups"],
            [
                {
                    "packet_id": "B-WP1",
                    "satisfied_dependencies": ["A-DONE"],
                    "newly_satisfied_by": ["A-DONE"],
                }
            ],
        )

    def test_diagnostics_do_not_change_authorized_execution_identity(self) -> None:
        left = build_packet_descriptor(
            programme_id="A",
            packet_id="A-WP1",
            write_paths=("src/a",),
            semantic_owners=("A",),
        )
        right = build_packet_descriptor(
            programme_id="B",
            packet_id="B-WP1",
            write_paths=("src/b",),
            semantic_owners=("B",),
        )
        first = authorize_parallel_build_pair(
            authority_resolution=active_authority(),
            left=left,
            right=right,
        )
        second = authorize_parallel_build_pair(
            authority_resolution=active_authority(),
            left=left,
            right=right,
        )
        self.assertEqual(first["record_id"], second["record_id"])
        self.assertEqual(first["source_classification_id"], second["source_classification_id"])


if __name__ == "__main__":
    unittest.main()
