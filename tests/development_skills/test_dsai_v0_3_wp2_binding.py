from __future__ import annotations

import unittest

from ovc.development.skills.dsai3_binding import build_orch_to_siq_binding_plan


SHA1 = "1" * 40
SHA2 = "2" * 40
SHA3 = "3" * 40
MAIN = "a" * 40


def packet(packet_id: str, head: str, **overrides: object) -> dict[str, object]:
    value: dict[str, object] = {
        "packet_id": packet_id,
        "plan_id": "PLAN-1",
        "packet_class": "LOW_RISK_IMPLEMENTATION",
        "candidate_head_sha": head,
        "baseline_main_sha": MAIN,
        "implementation_complete": True,
        "qa_status": "PASS",
        "authority_delta": "NONE",
        "gate_class": "AUTO_RATIFIABLE",
        "preliminary_assurance_pass": True,
        "rollback_defined": True,
        "dependency_footprint_pinned": True,
    }
    value.update(overrides)
    return value


def orch(*selected: str, parallel_merge: bool = False) -> dict[str, object]:
    return {
        "record_id": "ORCH5-EXEC-1",
        "selected_packet_ids": list(selected),
        "parallel_merge": parallel_merge,
    }


class DsaiV03Wp2BindingTests(unittest.TestCase):
    def test_reuses_existing_siq_and_only_head_gets_final_assurance(self) -> None:
        result = build_orch_to_siq_binding_plan(
            source_orch_execution_record=orch("A", "B", "C"),
            packets=[packet("A", SHA1), packet("B", SHA2), packet("C", SHA3)],
        )
        self.assertEqual(result["queue_owner"], "OVC.SIQ.RUNTIME.v0.1")
        self.assertEqual(result["queue_id"], "OVC.SIQ.v0.1")
        self.assertFalse(result["creates_new_queue"])
        self.assertFalse(result["side_effect_performed"])
        self.assertFalse(result["parallel_merge"])
        self.assertEqual(result["queue_head_packet_id"], "A")
        self.assertEqual(result["base_sensitive_final_assurance_eligible_packet_id"], "A")
        self.assertEqual(result["waiting_base_sensitive_packet_ids"], ["B", "C"])
        eligible = [row["packet_id"] for row in result["bindings"] if row["queue_head_eligible"]]
        self.assertEqual(eligible, ["A"])

    def test_orch_selection_order_determines_ready_sequence_not_input_order(self) -> None:
        left = build_orch_to_siq_binding_plan(
            source_orch_execution_record=orch("A", "B", "C"),
            packets=[packet("C", SHA3), packet("A", SHA1), packet("B", SHA2)],
        )
        right = build_orch_to_siq_binding_plan(
            source_orch_execution_record=orch("A", "B", "C"),
            packets=[packet("A", SHA1), packet("B", SHA2), packet("C", SHA3)],
        )
        self.assertEqual(left["record_id"], right["record_id"])
        self.assertEqual(left["bindings"], right["bindings"])
        self.assertEqual([row["ready_sequence"] for row in left["bindings"]], [1, 2, 3])

    def test_not_ready_earlier_candidate_does_not_block_later_ready_head(self) -> None:
        result = build_orch_to_siq_binding_plan(
            source_orch_execution_record=orch("A", "B"),
            packets=[packet("A", SHA1, qa_status="PENDING"), packet("B", SHA2)],
        )
        self.assertEqual(result["not_ready_packet_ids"], ["A"])
        self.assertEqual(result["queue_head_packet_id"], "B")
        self.assertEqual(result["base_sensitive_final_assurance_eligible_packet_id"], "B")

    def test_operator_boundary_never_enters_automatic_final_assurance(self) -> None:
        result = build_orch_to_siq_binding_plan(
            source_orch_execution_record=orch("A", "B"),
            packets=[
                packet("A", SHA1, gate_class="OPERATOR_REQUIRED"),
                packet("B", SHA2),
            ],
        )
        self.assertEqual(result["operator_required_packet_ids"], ["A"])
        self.assertEqual(result["queue_head_packet_id"], "B")
        binding = next(row for row in result["bindings"] if row["packet_id"] == "A")
        self.assertEqual(binding["queue_state"], "OPERATOR_REQUIRED")
        self.assertFalse(binding["queue_head_eligible"])

    def test_non_none_authority_delta_is_operator_required(self) -> None:
        result = build_orch_to_siq_binding_plan(
            source_orch_execution_record=orch("A"),
            packets=[packet("A", SHA1, authority_delta="ACTIVATE")],
        )
        self.assertEqual(result["operator_required_packet_ids"], ["A"])
        self.assertIsNone(result["queue_head_packet_id"])
        self.assertIsNone(result["base_sensitive_final_assurance_eligible_packet_id"])

    def test_non_low_risk_packet_fails_closed(self) -> None:
        with self.assertRaises(PermissionError):
            build_orch_to_siq_binding_plan(
                source_orch_execution_record=orch("A"),
                packets=[packet("A", SHA1, packet_class="HIGH_RISK")],
            )

    def test_parallel_merge_source_fails_closed(self) -> None:
        with self.assertRaises(PermissionError):
            build_orch_to_siq_binding_plan(
                source_orch_execution_record=orch("A", parallel_merge=True),
                packets=[packet("A", SHA1)],
            )

    def test_selected_packet_without_mapping_fails_closed(self) -> None:
        with self.assertRaises(ValueError):
            build_orch_to_siq_binding_plan(
                source_orch_execution_record=orch("A", "B"),
                packets=[packet("A", SHA1)],
            )


if __name__ == "__main__":
    unittest.main()
