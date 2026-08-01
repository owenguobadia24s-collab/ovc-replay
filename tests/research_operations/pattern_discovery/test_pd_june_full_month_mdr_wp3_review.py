from __future__ import annotations

import json
import unittest
from pathlib import Path

from ovc.research_operations.pattern_discovery import full_month_wp3_review as subject

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / "docs" / "releases" / "pattern-discovery-v0-3" / "pd-june-full-month-mdr" / "wp3-review"
INDEX = BASE / "PD_JUNE_FM_WP3_EXTERNAL_ARTIFACT_INDEX.json"
QA = BASE / "PD_JUNE_FM_WP3_SELECTION_AND_COMPLETENESS_QA.json"
STATE = ROOT / "registries" / "research_operations" / "pattern_discovery" / "PD_JUNE_FULL_MONTH_MDR_PROGRAMME_STATE_v0_1.json"


def state(timestamp: str, *, location: str | None = "MID_REGION", motion: str | None = "BALANCED", interaction: str | None = "TESTING", organisation: str | None = "DISORDERED", suffix: str = "x") -> dict:
    def axis(value: str | None) -> dict:
        return {"status": "EVALUATED" if value is not None else "NOT_EVALUATED", "value": value, "reason_code": None if value is not None else "WINDOW_NOT_COMPLETE"}
    return {
        "c2_state_id": f"c2-state:{suffix}",
        "first_valid_time": timestamp,
        "axes": {
            "LOCATION": axis(location),
            "MOTION": axis(motion),
            "ORGANISATION": axis(organisation),
            "INTERACTION": axis(interaction),
            "QUALITY": axis("DEGRADED"),
        },
    }


class PDJuneFullMonthMDRWP3ReviewTests(unittest.TestCase):
    def test_week_and_session_classification(self) -> None:
        self.assertEqual(subject.week_bucket("2026-06-01T00:00:00Z"), "W1_2026-06-01_07")
        self.assertEqual(subject.week_bucket("2026-06-14T12:00:00Z"), "W2_2026-06-08_14")
        self.assertEqual(subject.week_bucket("2026-06-30T23:45:00Z"), "W5_2026-06-29_30")
        self.assertEqual(subject.utc_session("2026-06-01T07:59:00Z"), "ASIA_00_08")
        self.assertEqual(subject.utc_session("2026-06-01T08:00:00Z"), "LONDON_08_13")
        self.assertEqual(subject.utc_session("2026-06-01T13:00:00Z"), "NEW_YORK_13_21")
        self.assertEqual(subject.utc_session("2026-06-01T21:00:00Z"), "LATE_21_24")

    def test_transition_identity_and_boundary_trigger_are_deterministic(self) -> None:
        previous = state("2026-06-01T10:00:00Z", location="MID_REGION", suffix="a")
        current = state("2026-06-01T10:15:00Z", location="UPPER_REGION", suffix="b")
        transition = subject.build_transition(previous, current)
        self.assertIsNotNone(transition)
        self.assertEqual(transition["changed_axes"], ["LOCATION"])
        result = subject.evaluate_trigger_rules([previous, current])
        self.assertEqual(result["BOUNDARY_ZONE_ENTRY"]["status"], "FIRED")
        self.assertEqual(result["BREACH_ACTIVE"]["status"], "NOT_FIRED")

    def test_long_persistence_and_repeated_switching_threshold_crossing(self) -> None:
        persistence = [
            state(f"2026-06-01T0{index}:00:00Z", motion="BALANCED", suffix=f"p{index}")
            for index in range(4)
        ]
        result = subject.evaluate_trigger_rules(persistence)
        self.assertEqual(result["LONG_PERSISTENCE"]["status"], "FIRED")
        switching_values = ["BALANCED", "BALANCED", "UP_STALL", "UP_STALL", "BALANCED", "UP_STALL"]
        switching = [
            state(f"2026-06-02T0{index}:00:00Z", motion=value, suffix=f"s{index}")
            for index, value in enumerate(switching_values)
        ]
        result = subject.evaluate_trigger_rules(switching)
        self.assertEqual(result["REPEATED_SWITCHING"]["status"], "FIRED")
        self.assertEqual(result["REPEATED_SWITCHING"]["switches"], 3)

    def test_external_index_and_selection_qa_are_exact_and_non_activating(self) -> None:
        index = json.loads(INDEX.read_text(encoding="utf-8"))
        qa = json.loads(QA.read_text(encoding="utf-8"))
        state_value = json.loads(STATE.read_text(encoding="utf-8"))
        self.assertEqual(index["reviewer_package"]["sha256"], "1b68c2c58e895c700152b697ceb1cdc1bf9cf5ef9807c9f69893512c0104bd46")
        self.assertEqual(index["sealed_evidence"]["answer_key_sha256"], "48ddb7ff6689c60ef4ce24703119f6557959828e886e02213ae1804c3001ed97")
        self.assertEqual(qa["selected_card_count"], 40)
        self.assertEqual(qa["observation_count"], 360)
        self.assertEqual(qa["selection"]["trigger"], 20)
        self.assertEqual(qa["selection"]["matched_nontrigger_control"], 10)
        self.assertEqual(qa["selection"]["algorithmic_not_evaluable_control"], 10)
        self.assertEqual(qa["source_completeness"]["source_boundary_insufficiency"], 0)
        self.assertEqual(qa["card_content"]["review_card_presentation_omission_count"], 0)
        self.assertEqual(index["release_status"], "NOT_A_RELEASE")
        self.assertEqual(index["selector_eligibility"], "NONE")
        self.assertEqual(index["r2_publication"], "DENIED")
        self.assertEqual(index["validation_consumption"], "DENIED")
        self.assertFalse(index["write_authority"])
        self.assertEqual(state_value["packet_id"], "PD-JUNE-FM-WP3")
        self.assertEqual(state_value["status"], "QA_REVIEW")
        self.assertEqual(state_value["next_packet"], "PD-JUNE-FM-G2")
        self.assertEqual(state_value["next_packet_status"], "BLOCKED_PENDING_WP3_FINAL_HEAD_CI_AND_SQUASH_MERGE")


if __name__ == "__main__":
    unittest.main()
