from __future__ import annotations

from datetime import timedelta
from decimal import Decimal
import unittest

from test_contracts import START, bar
from ovc_opt_b import (
    CompoundTrigger,
    PersistentState,
    StateEvidence,
    apply_trigger,
    make_neutral_exit,
    neutral_exit_predicate,
    resolve_compound_trigger,
)


class CompoundStateTests(unittest.TestCase):
    def test_same_label_levels_become_one_compound_state(self) -> None:
        trigger = resolve_compound_trigger([
            StateEvidence(2, "ACCEPTED_BELOW", "DOWN", "L2", "R2"),
            StateEvidence(2, "ACCEPTED_BELOW", "DOWN", "L1", "R1"),
        ])
        self.assertIsNotNone(trigger)
        self.assertEqual(trigger.semantic_state, "ACCEPTED_BELOW")
        self.assertEqual(trigger.support_level_ids, ("L1", "L2"))

    def test_conflicting_labels_remain_ambiguous(self) -> None:
        trigger = resolve_compound_trigger([
            StateEvidence(2, "ACCEPTED_BELOW", "DOWN", "L1", "R1"),
            StateEvidence(2, "ACCEPTED_ABOVE", "UP", "L2", "R2"),
        ])
        self.assertEqual(trigger.semantic_state, "AMBIGUOUS")
        self.assertEqual(trigger.conflicting_semantic_states, ("ACCEPTED_ABOVE", "ACCEPTED_BELOW"))

    def test_lower_precedence_trigger_does_not_replace_active_state(self) -> None:
        current = PersistentState("ACCEPTED_ABOVE", 2, ("L1",), ("R1",), START)
        trigger = CompoundTrigger("RECLAIMED_ABOVE", 3, ("L2",), ("R2",))
        resolved, reason = apply_trigger(current, trigger, START + timedelta(hours=1))
        self.assertEqual(resolved, current)
        self.assertEqual(reason, "LOWER_PRECEDENCE_TRIGGER_SUPPRESSED")

    def test_level_state_exit_uses_control_level_and_two_bar_record(self) -> None:
        current = PersistentState("ACCEPTED_ABOVE", 2, ("L1", "L2"), ("R1",), START)
        first = bar(0, "100", "100.2", "99.5", "99.7")
        second = bar(1, "99.7", "99.8", "99.4", "99.6")
        predicate, reason = neutral_exit_predicate(
            current,
            bar=first,
            previous_bar=None,
            atr=Decimal("1"),
            level_prices={"L1": Decimal("99.8"), "L2": Decimal("100")},
            compression_failed=False,
            coherent_trigger_present=False,
        )
        self.assertTrue(predicate)
        exit_record = make_neutral_exit(current, first, second, reason)
        self.assertEqual(exit_record.reason, "LEVEL_STATE_INVALIDATED")
        self.assertEqual(exit_record.confirmed_at, second.close_time)
        self.assertEqual(exit_record, make_neutral_exit(current, first, second, reason))


if __name__ == "__main__":
    unittest.main()
