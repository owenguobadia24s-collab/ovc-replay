from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from ovc.research_operations.pattern_discovery import (
    CandidateWindowManager,
    ChronologyError,
    DuplicateDerivedRecordError,
    PatternDiscoveryEngine,
    SourceBindingError,
    build_trigger_event,
    extract_transitions,
    mark_display_primary,
)


ROOT = Path(__file__).resolve().parents[3]
FIXTURE = ROOT / "fixtures" / "research_operations" / "pattern_discovery" / "pd_wp1" / "c2_state_stream.json"


class PatternDiscoveryWP1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.states = json.loads(FIXTURE.read_text(encoding="utf-8"))

    def _location_trigger(self, transitions, *, closure_profile="CP-BOUNDARY-RESOLUTION"):
        location = [item for item in transitions if item["axis_or_relation"] == "AXIS.LOCATION"]
        return build_trigger_event(
            trigger_id="TR-LOC-001",
            reason_code="BOUNDARY_ZONE_ENTRY",
            source_transitions=location,
            operation_mode="NON_EVIDENTIARY_REPLAY",
            closure_profile_id=closure_profile,
            rate_limit_group="BOUNDARY_INTERACTION",
        )

    def test_transition_extraction_is_deterministic_and_complete(self) -> None:
        first = extract_transitions(self.states[0], self.states[1])
        second = extract_transitions(self.states[0], self.states[1])
        self.assertEqual(first, second)
        self.assertEqual(len(first), 5)
        self.assertEqual(
            [item["axis_or_relation"] for item in first],
            [
                "AXIS.INTERACTION",
                "AXIS.LOCATION",
                "AXIS.MOTION",
                "AXIS.ORGANISATION",
                "RELATION_SET",
            ],
        )
        self.assertTrue(all(item["transition_id"].startswith("PDTR-") for item in first))
        self.assertTrue(all(item["source_after"]["record_id"] == "C2S-FIX-0002" for item in first))

    def test_transition_extraction_rejects_chronology_and_source_rebinding(self) -> None:
        with self.assertRaises(ChronologyError):
            extract_transitions(self.states[1], self.states[0])
        rebound = dict(self.states[1])
        rebound["selector_id"] = "OTHER_SELECTOR"
        with self.assertRaises(SourceBindingError):
            extract_transitions(self.states[0], rebound)

    def test_trigger_events_are_append_only_and_precedence_is_display_only(self) -> None:
        transitions = extract_transitions(self.states[0], self.states[1])
        structural = self._location_trigger(transitions)
        quality = build_trigger_event(
            trigger_id="TR-QA-001",
            reason_code="QUALITY_INCIDENT",
            source_transitions=transitions[:1],
            operation_mode="NON_EVIDENTIARY_REPLAY",
            closure_profile_id="CP-QUALITY-INCIDENT",
            rate_limit_group="QUALITY",
        )
        marked = mark_display_primary(
            [structural, quality],
            trigger_families={"TR-QA-001": "QUALITY_OR_INCIDENT"},
        )
        self.assertEqual(len(marked), 2)
        self.assertEqual(sum(1 for item in marked if item["primary"]), 1)
        self.assertEqual(next(item for item in marked if item["primary"])["trigger_id"], "TR-QA-001")
        self.assertFalse(structural["primary"])
        self.assertFalse(quality["primary"])

        with tempfile.TemporaryDirectory() as directory:
            engine = PatternDiscoveryEngine(ledger_root=directory)
            event = engine.record_trigger(
                trigger_id="TR-LOC-001",
                reason_code="BOUNDARY_ZONE_ENTRY",
                source_transitions=[item for item in transitions if item["axis_or_relation"] == "AXIS.LOCATION"],
                operation_mode="NON_EVIDENTIARY_REPLAY",
                closure_profile_id="CP-BOUNDARY-RESOLUTION",
                rate_limit_group="BOUNDARY_INTERACTION",
            )
            self.assertEqual(engine.ledger.triggers.read_all(), [event])
            with self.assertRaises(DuplicateDerivedRecordError):
                engine.ledger.triggers.append(event)

    def test_compatible_duplicate_attaches_trigger_to_existing_window(self) -> None:
        transitions = extract_transitions(self.states[0], self.states[1])
        trigger = self._location_trigger(transitions)
        manager = CandidateWindowManager()
        opened = manager.open_from_trigger(
            self.states[1], trigger, trigger_family="STRUCTURAL_TRANSITION"
        )
        repeated = manager.open_from_trigger(
            self.states[1], trigger, trigger_family="STRUCTURAL_TRANSITION"
        )
        self.assertEqual(opened["window_id"], repeated["window_id"])
        self.assertEqual(repeated["status"], "ACCUMULATING")
        self.assertEqual(repeated["trigger_event_ids"], [trigger["trigger_event_id"]])
        self.assertEqual(len(manager.all_windows()), 1)

    def test_incompatible_closure_profile_creates_separate_candidate_when_cap_allows(self) -> None:
        transitions = extract_transitions(self.states[0], self.states[1])
        first_trigger = self._location_trigger(transitions, closure_profile="CP-BOUNDARY-RESOLUTION")
        second_trigger = self._location_trigger(transitions, closure_profile="CP-STABLE-RESOLUTION")
        manager = CandidateWindowManager(max_open_per_family_scope=2)
        first = manager.open_from_trigger(
            self.states[1], first_trigger, trigger_family="STRUCTURAL_TRANSITION"
        )
        second = manager.open_from_trigger(
            self.states[1], second_trigger, trigger_family="STRUCTURAL_TRANSITION"
        )
        self.assertNotEqual(first["window_id"], second["window_id"])
        self.assertEqual(len(manager.all_windows()), 2)
        self.assertIn("CP-STABLE-RESOLUTION", second["candidate_dedup_key"])

    def test_per_family_cap_is_explicit_and_never_silent(self) -> None:
        transitions = extract_transitions(self.states[0], self.states[1])
        trigger = self._location_trigger(transitions)
        manager = CandidateWindowManager(max_open_per_family_scope=1)
        manager.open_from_trigger(
            self.states[1], trigger, trigger_family="STRUCTURAL_TRANSITION"
        )
        alternate_state = dict(self.states[1])
        alternate_state["boundary_or_relation_id"] = "LVL-ALT"
        alternate_trigger = dict(trigger)
        alternate_trigger["trigger_event_id"] = "PDTE-ALTERNATE"
        suppressed = manager.open_from_trigger(
            alternate_state,
            alternate_trigger,
            trigger_family="STRUCTURAL_TRANSITION",
        )
        self.assertEqual(suppressed["status"], "SUPPRESSED_QUEUE_CAP")
        self.assertEqual(suppressed["suppression_reason"], "PER_FAMILY_SCOPE_OPEN_CAP")
        self.assertEqual(len(manager.all_windows()), 2)

    def test_gap_quarantine_pending_and_selector_failure_transitions(self) -> None:
        transitions = extract_transitions(self.states[0], self.states[1])
        trigger = self._location_trigger(transitions)

        gap_manager = CandidateWindowManager()
        gap_window = gap_manager.open_from_trigger(
            self.states[1], trigger, trigger_family="STRUCTURAL_TRANSITION"
        )
        trigger_hash = gap_window["trigger_snapshot_hash"]
        gap_manager.accumulate(gap_window["window_id"], self.states[2])
        closed = gap_manager.accumulate(gap_window["window_id"], self.states[3])
        self.assertEqual(closed["status"], "READY_FOR_REVIEW")
        self.assertEqual(closed["closure_reason"], "CENSORED_GAP")
        self.assertEqual(closed["trigger_snapshot_hash"], trigger_hash)

        quarantine_manager = CandidateWindowManager()
        quarantine_window = quarantine_manager.open_from_trigger(
            self.states[1], trigger, trigger_family="STRUCTURAL_TRANSITION"
        )
        quarantine_manager.accumulate(quarantine_window["window_id"], self.states[2])
        invalid = quarantine_manager.accumulate(quarantine_window["window_id"], self.states[4])
        self.assertEqual(invalid["status"], "INVALID")
        self.assertEqual(invalid["closure_reason"], "INVALID_SOURCE_QUARANTINED")

        pending_manager = CandidateWindowManager()
        pending_window = pending_manager.open_from_trigger(
            self.states[1], trigger, trigger_family="STRUCTURAL_TRANSITION"
        )
        pending = pending_manager.mark_pending_input(pending_window["window_id"])
        self.assertEqual(pending["status"], "OPEN_PENDING_INPUT")
        resumed = pending_manager.resume_after_validated_input(pending_window["window_id"])
        self.assertEqual(resumed["status"], "ACCUMULATING")
        stopped = pending_manager.stop_for_selector_change("2026-07-27T00:45:00Z")
        self.assertEqual(stopped[0]["closure_reason"], "SOURCE_SELECTOR_CHANGED")
        with self.assertRaises(SourceBindingError):
            pending_manager.open_from_trigger(
                self.states[1], trigger, trigger_family="STRUCTURAL_TRANSITION"
            )

    def test_public_candidate_shape_contains_no_outcome_or_trade_fields(self) -> None:
        transitions = extract_transitions(self.states[0], self.states[1])
        trigger = self._location_trigger(transitions)
        candidate = CandidateWindowManager().open_from_trigger(
            self.states[1], trigger, trigger_family="STRUCTURAL_TRANSITION"
        )
        serialized = json.dumps(candidate, sort_keys=True).lower()
        for prohibited in ("probability", "trade_direction", "mfe", "mae", "future_outcome"):
            self.assertNotIn(prohibited, serialized)
        self.assertEqual(candidate["operation_mode"], "NON_EVIDENTIARY_REPLAY")
        self.assertEqual(candidate["source_release_id"], self.states[1]["c2_release_id"])


if __name__ == "__main__":
    unittest.main()
