from copy import deepcopy
import unittest

from ovc.context.occurrence_context.builder import OccurrenceContextError
from ovc.context.occurrence_context.c2_adapter import c2_anchor_from_state, c2_dependency, c2_source_context
from ovc.context.occurrence_context.c2e_adapter import c2e_anchor, episode_relative_context
from ovc.context.occurrence_context.calendar_adapter import assert_session_not_guessed, calendar_context_for_interval, session_context_for_interval
from ovc.context.occurrence_context.clock_adapter import clock_scale_context
from ovc.opt_b.c2e_v2.models import build_record


def c2_state(clock="15M", side="BID", scope="GBPUSD-15M-LOCAL-v0.1"):
    return {
        "c2_state_id": "C2.STATE.001",
        "first_valid_time": "2026-01-01T00:15:00Z",
        "clock": clock,
        "side": side,
        "evaluation_scope_id": scope,
        "c1_release_id": "C1.R1",
        "c1_manifest_id": "C1.M1",
        "opt_a_release_id": "OA.R1",
        "opt_a_manifest_id": "OA.M1",
        "axes": {"LOCATION": {"status": "EVALUATED", "value": "MID_REGION"}},
    }


def c2e_records(status="OPEN"):
    genesis = build_record("episode_genesis", {
        "boundary_pack_id":"C2E.BOUNDARY.FIXTURE","source_release_id":"R1","instrument_id":"GBPUSD","side":"BID","scope_id":"GBPUSD-15M-LOCAL-v0.1","scale_id":"15M","birth_frame_id":"F1","birth_boundary_rule_id":"BIRTH","birth_effective_time":"2026-01-01T00:00:00Z","first_valid_time":"2026-01-01T00:15:00Z","authority":"INACTIVE_NONCANONICAL_SHADOW"
    })
    phase = build_record("phase_segment", {
        "episode_id":genesis["episode_id"],"phase_type":"PERSISTENCE","start_time":"2026-01-01T00:00:00Z","end_time":None,"first_valid_time":"2026-01-01T00:30:00Z","source_record_ids":["F1","F2"],"authority":"INACTIVE_NONCANONICAL_SHADOW"
    })
    snapshot = build_record("episode_snapshot", {
        "episode_id":genesis["episode_id"],"as_of_time":"2026-01-01T00:30:00Z","first_valid_time":"2026-01-01T00:30:00Z","status":status,"member_ids":["F1","F2"],"phase_segment_ids":[phase["phase_segment_id"]],"boundary_event_ids":[],"authority":"INACTIVE_NONCANONICAL_SHADOW"
    })
    return genesis, snapshot, phase


class OCWP3AdapterTests(unittest.TestCase):
    def test_c2_adapter_is_read_only_and_bounded(self):
        state = c2_state()
        original = deepcopy(state)
        anchor = c2_anchor_from_state(state)
        source = c2_source_context(state)
        dep = c2_dependency(state)
        self.assertEqual(anchor.anchor_kind, "C2_OBSERVATION")
        self.assertEqual(source["instrument_id"], "GBPUSD")
        self.assertEqual(dep.record_id, state["c2_state_id"])
        self.assertEqual(state, original)

    def test_c2_adapter_rejects_new_market_side_or_clock(self):
        with self.assertRaises(OccurrenceContextError) as instrument:
            c2_anchor_from_state(c2_state(scope="XAUUSD-15M-LOCAL-v0.1"))
        self.assertEqual(instrument.exception.reason_code, "OC_AUTH_NEW_INSTRUMENT_DENIED")
        with self.assertRaises(OccurrenceContextError) as side:
            c2_anchor_from_state(c2_state(side="MID"))
        self.assertEqual(side.exception.reason_code, "OC_AUTH_NEW_SIDE_DENIED")
        with self.assertRaises(OccurrenceContextError) as clock:
            c2_anchor_from_state(c2_state(clock="4H"))
        self.assertEqual(clock.exception.reason_code, "OC_AUTH_NEW_CLOCK_DENIED")

    def test_calendar_derives_only_lawful_utc_partitions(self):
        context = calendar_context_for_interval("2026-07-15T12:00:00Z")
        self.assertEqual((context["calendar_year"], context["calendar_month"], context["calendar_quarter"]), (2026, 7, 3))
        session = session_context_for_interval("2026-07-15T12:00:00Z")
        self.assertEqual(session["status"], "UNAVAILABLE")
        self.assertEqual(session["session_membership_ids"], [])
        self.assertIsNone(session["a_l_block_id"])
        self.assertIn("OC_SESSION_UNRESOLVED", session["reason_codes"])
        assert_session_not_guessed(session)

    def test_session_guess_is_rejected(self):
        with self.assertRaises(OccurrenceContextError) as caught:
            assert_session_not_guessed({"session_membership_ids":["LONDON"],"a_l_block_id":None})
        self.assertEqual(caught.exception.reason_code, "OC_SESSION_UNRESOLVED")

    def test_clock_adapter_references_existing_only(self):
        context = clock_scale_context(clock_id="2H_A_L", lattice_id="LATTICE.2H.UTC_0000.v1")
        self.assertEqual(context["lattice_authority"], "REFERENCE_ONLY_NO_ACTIVATION")
        with self.assertRaises(OccurrenceContextError) as caught:
            clock_scale_context(clock_id="4H")
        self.assertEqual(caught.exception.reason_code, "OC_AUTH_NEW_CLOCK_DENIED")

    def test_c2e_adapter_validates_exact_records_and_elapsed_context(self):
        genesis, snapshot, phase = c2e_records()
        anchor = c2e_anchor("episode_snapshot", snapshot)
        relative = episode_relative_context(genesis, snapshot, [phase])
        self.assertEqual(anchor.anchor_kind, "C2E_EPISODE_SNAPSHOT")
        self.assertEqual(relative["elapsed_duration"], "PT1800S")
        self.assertEqual(relative["elapsed_eligible_observation_count"], 2)
        self.assertEqual(relative["current_phase_ref"]["record_id"], phase["phase_segment_id"])
        self.assertIsNone(relative["completion_context"])
        self.assertIsNone(relative["censoring_context"])

    def test_censoring_is_not_completion(self):
        genesis, snapshot, phase = c2e_records(status="CENSORED")
        relative = episode_relative_context(genesis, snapshot, [phase])
        self.assertIsNotNone(relative["censoring_context"])
        self.assertIsNone(relative["completion_context"])

    def test_terminal_status_is_separate_from_censoring(self):
        genesis, snapshot, phase = c2e_records(status="TERMINATED")
        relative = episode_relative_context(genesis, snapshot, [phase])
        self.assertIsNone(relative["censoring_context"])
        self.assertEqual(relative["completion_context"]["status"], "TERMINATED")


if __name__ == "__main__":
    unittest.main()
