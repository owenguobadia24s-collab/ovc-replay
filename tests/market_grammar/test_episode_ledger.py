from __future__ import annotations

import json
import unittest

from ovc.opt_b.market_grammar.episode_ledger import (
    BoundaryCause,
    C2LedgerInput,
    EpisodeBindingRequest,
    EpisodeStatus,
    NestingRelation,
    build_episode_ledger,
    build_nesting_ledger,
)

HASH = "a" * 64


def record(record_id: str, when: str, *, state: str = "STATE_A", transition: str = "NONE", parent: str | None = "PARENT_A", computability: str = "EVALUABLE", reason: str | None = None, reset: str | None = None, clock: str = "15M") -> dict[str, object]:
    return {
        "record_id": record_id,
        "source_release_id": "REL.TEST.v1",
        "instrument_id": "GBPUSD",
        "side": "BID",
        "scope_id": "LOCAL",
        "clock_id": clock,
        "first_valid_time": when,
        "state_key": state,
        "transition_kind": transition,
        "parent_record_id": parent,
        "computability_status": computability,
        "not_evaluable_reason": reason,
        "reset_reason": reset,
        "source_sha256": HASH,
    }


class EpisodeLedgerTests(unittest.TestCase):
    def test_order_independent_deterministic_ids_and_completion(self) -> None:
        values = [
            record("R1", "2026-06-01T00:15:00Z"),
            record("R2", "2026-06-01T00:30:00Z", state="STATE_B"),
            record("R3", "2026-06-01T00:45:00Z", transition="COMPLETION"),
        ]
        first = build_episode_ledger(values, build_cutoff="2026-06-01T01:00:00Z")
        second = build_episode_ledger(reversed(values), build_cutoff="2026-06-01T01:00:00Z")
        self.assertEqual(first.to_dict(), second.to_dict())
        self.assertEqual(1, len(first.episodes))
        episode = first.episodes[0]
        self.assertEqual(EpisodeStatus.COMPLETED, episode.status)
        self.assertEqual(BoundaryCause.COMPLETION, episode.boundary_cause)
        self.assertEqual(("R1", "R2", "R3"), episode.member_record_ids)
        self.assertEqual((HASH, HASH, HASH), episode.member_source_sha256)
        self.assertEqual((HASH, HASH, HASH), first.input_source_sha256)
        self.assertEqual(3, len(episode.phases))
        self.assertTrue(episode.episode_id.startswith("C2E.EP."))
        self.assertNotIn("/tmp", json.dumps(first.to_dict()))

    def test_parent_change_interrupts_and_starts_new_episode(self) -> None:
        ledger = build_episode_ledger(
            [record("R1", "2026-06-01T00:15:00Z", parent="P1"), record("R2", "2026-06-01T00:30:00Z", parent="P2")],
            build_cutoff="2026-06-01T00:30:00Z",
        )
        self.assertEqual(2, len(ledger.episodes))
        self.assertEqual(EpisodeStatus.INTERRUPTED, ledger.episodes[0].status)
        self.assertEqual(BoundaryCause.PARENT_CHANGE, ledger.episodes[0].boundary_cause)
        self.assertEqual(EpisodeStatus.OPEN_AT_CUTOFF, ledger.episodes[1].status)

    def test_non_evaluable_is_explicit_and_censors_active_episode(self) -> None:
        ledger = build_episode_ledger(
            [record("R1", "2026-06-01T00:15:00Z"), record("R2", "2026-06-01T00:30:00Z", computability="NOT_EVALUABLE", reason="MISSING_AXIS"), record("R3", "2026-06-01T00:45:00Z")],
            build_cutoff="2026-06-01T00:45:00Z",
        )
        self.assertEqual(2, len(ledger.episodes))
        self.assertEqual(EpisodeStatus.CENSORED, ledger.episodes[0].status)
        self.assertEqual(BoundaryCause.COMPUTABILITY_BREAK, ledger.episodes[0].boundary_cause)
        self.assertEqual("MISSING_AXIS", ledger.not_evaluable[0].reason)

    def test_reset_censors_prior_episode_without_inferred_continuity(self) -> None:
        ledger = build_episode_ledger(
            [record("R1", "2026-06-01T00:15:00Z"), record("R2", "2026-06-01T00:30:00Z", reset="SOURCE_GAP")],
            build_cutoff="2026-06-01T00:30:00Z",
        )
        self.assertEqual(2, len(ledger.episodes))
        self.assertEqual(BoundaryCause.RESET, ledger.episodes[0].boundary_cause)
        self.assertEqual("SOURCE_GAP", ledger.episodes[0].censoring_reason)

    def test_future_outcome_and_c2g_fields_are_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "future/outcome"):
            C2LedgerInput.from_mapping({**record("R1", "2026-06-01T00:15:00Z"), "mfe": 1.0})
        with self.assertRaisesRegex(ValueError, "future/outcome"):
            C2LedgerInput.from_mapping({**record("R1", "2026-06-01T00:15:00Z"), "family_id": "F1"})
        with self.assertRaisesRegex(ValueError, "future"):
            build_episode_ledger([record("R1", "2026-06-01T00:30:00Z")], build_cutoff="2026-06-01T00:15:00Z")

    def test_scope_mismatch_and_duplicate_identity_fail_closed(self) -> None:
        with self.assertRaisesRegex(ValueError, "share release"):
            build_episode_ledger([record("R1", "2026-06-01T00:15:00Z"), record("R2", "2026-06-01T00:30:00Z", clock="2H_A_L")], build_cutoff="2026-06-01T02:00:00Z")
        with self.assertRaisesRegex(ValueError, "duplicate record_id"):
            build_episode_ledger([record("R1", "2026-06-01T00:15:00Z"), record("R1", "2026-06-01T00:30:00Z")], build_cutoff="2026-06-01T01:00:00Z")
        with self.assertRaisesRegex(ValueError, "duplicate first_valid_time"):
            build_episode_ledger([record("R1", "2026-06-01T00:15:00Z"), record("R2", "2026-06-01T00:15:00Z")], build_cutoff="2026-06-01T01:00:00Z")

    def test_nesting_validates_chronology_interval_and_cycles(self) -> None:
        parent = build_episode_ledger(
            [record("P1", "2026-06-01T00:00:00Z", clock="2H_A_L"), record("P2", "2026-06-01T02:00:00Z", transition="COMPLETION", clock="2H_A_L")],
            build_cutoff="2026-06-01T02:00:00Z",
        ).episodes[0]
        child = build_episode_ledger(
            [record("C1", "2026-06-01T00:15:00Z"), record("C2", "2026-06-01T00:30:00Z", transition="COMPLETION")],
            build_cutoff="2026-06-01T00:30:00Z",
        ).episodes[0]
        bindings = build_nesting_ledger([parent, child], [EpisodeBindingRequest(child.episode_id, parent.episode_id, NestingRelation.CONTEXT_PARENT, child.start_first_valid_time)])
        self.assertEqual(1, len(bindings))
        too_long = build_episode_ledger(
            [record("L1", "2026-06-01T00:15:00Z"), record("L2", "2026-06-01T02:15:00Z", transition="COMPLETION")],
            build_cutoff="2026-06-01T02:15:00Z",
        ).episodes[0]
        with self.assertRaisesRegex(ValueError, "extends beyond parent"):
            build_nesting_ledger([parent, too_long], [EpisodeBindingRequest(too_long.episode_id, parent.episode_id, NestingRelation.NESTED_WITHIN, too_long.start_first_valid_time)])
        peer = build_episode_ledger(
            [record("X1", "2026-06-01T00:00:00Z"), record("X2", "2026-06-01T00:15:00Z", transition="COMPLETION")],
            build_cutoff="2026-06-01T00:15:00Z",
        ).episodes[0]
        with self.assertRaisesRegex(ValueError, "cycle"):
            build_nesting_ledger(
                [parent, peer],
                [EpisodeBindingRequest(peer.episode_id, parent.episode_id, NestingRelation.CONTEXT_PARENT, peer.start_first_valid_time), EpisodeBindingRequest(parent.episode_id, peer.episode_id, NestingRelation.DERIVED_FROM, parent.start_first_valid_time)],
            )


if __name__ == "__main__":
    unittest.main()
