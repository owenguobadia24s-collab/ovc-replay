from __future__ import annotations

import unittest

from ovc.development.skills.vit_completion_policy import (
    validate_non_churning_completion_transition,
)
from ovc.development.skills.vit_core import VitContractError


class VitCompletionPolicyTests(unittest.TestCase):
    def test_substantive_successor_is_allowed(self) -> None:
        validate_non_churning_completion_transition(
            packet_id="P2CTII-WP1",
            completion_transition={"status": "COMPLETED", "next_packet": "P2CTII-WP2"},
        )

    def test_terminal_completion_is_allowed(self) -> None:
        validate_non_churning_completion_transition(
            packet_id="PROGRAMME-WP9",
            completion_transition={"status": "COMPLETED", "next_packet": None},
        )

    def test_operator_gate_ready_state_is_not_auto_approved(self) -> None:
        validate_non_churning_completion_transition(
            packet_id="PROGRAMME-WP4",
            completion_transition={"status": "GATE_READY", "next_packet": None},
        )

    def test_closeout_next_packet_is_rejected(self) -> None:
        with self.assertRaisesRegex(
            VitContractError,
            "VIT_ADMINISTRATIVE_CLOSEOUT_PR_PROHIBITED_USE_RECEIPT_PATH",
        ):
            validate_non_churning_completion_transition(
                packet_id="P2CTII-WP1",
                completion_transition={
                    "status": "QA_REVIEW",
                    "next_packet": "P2CTII-WP1-CLOSEOUT-AFTER-PASS",
                },
            )

    def test_closeout_packet_itself_is_rejected(self) -> None:
        with self.assertRaisesRegex(
            VitContractError,
            "VIT_ADMINISTRATIVE_CLOSEOUT_PR_PROHIBITED_USE_RECEIPT_PATH",
        ):
            validate_non_churning_completion_transition(
                packet_id="CERS-PLAN-RATIFICATION-CLOSEOUT",
                completion_transition={"status": "COMPLETED"},
            )


if __name__ == "__main__":
    unittest.main()
